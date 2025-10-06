# components/boq_generator.py
# PRODUCTION-READY VERSION - With complete validation and room physics

import streamlit as st
import pandas as pd
import re
import json
import time

# --- Component Imports ---
try:
    from components.gemini_handler import generate_with_retry
    from components.av_designer import calculate_avixa_recommendations, determine_equipment_requirements
    from components.data_handler import match_product_in_database
except ImportError as e:
    st.error(f"BOQ Generator failed to import a component: {e}")
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}}
    def match_product_in_database(*args): return None


# ==================== ROOM PHYSICS VALIDATION ====================
def _validate_display_size_for_room(display_size, room_length, room_type):
    """
    Validate display size using AVIXA viewing distance standards
    Returns: (is_valid, corrected_size, reason)
    """
    # AVIXA standard: viewing distance = 4x display height for detailed work
    # For 16:9 display: height = diagonal / 2.22
    display_height_ft = (display_size / 2.22) / 12
    min_viewing_distance = display_height_ft * 4  # AVIXA 4:1 ratio
    
    # Add 20% buffer for actual usable viewing distance
    required_room_length = min_viewing_distance * 1.2
    
    if room_length < required_room_length:
        # Calculate maximum recommended size
        max_height_ft = (room_length * 0.8) / 4
        max_size = int(max_height_ft * 12 * 2.22)
        # Snap to standard sizes
        standard_sizes = [43, 55, 65, 75, 85, 98]
        max_size = max([s for s in standard_sizes if s <= max_size], default=43)
        
        reason = f"Display {display_size}\" too large for {room_length:.1f}ft room (AVIXA 4:1 ratio)"
        return False, max_size, reason
    
    return True, display_size, "Valid"


def _validate_audio_coverage(speaker_count, room_area, ceiling_height):
    """
    Validate speaker count provides adequate coverage
    Returns: (is_valid, recommended_count, reason)
    """
    # AVIXA guideline: 1 ceiling speaker per 150-200 sq ft
    min_speakers = max(2, int(room_area / 200))
    recommended_speakers = max(2, int(room_area / 150))
    
    if speaker_count < min_speakers:
        return False, recommended_speakers, f"Insufficient coverage: {speaker_count} speakers for {room_area:.0f} sq ft"
    
    # Check ceiling height for ceiling speakers
    if ceiling_height > 12:
        recommended_speakers = int(recommended_speakers * 1.5)  # Need more for high ceilings
        if speaker_count < recommended_speakers:
            return False, recommended_speakers, f"High ceiling ({ceiling_height}ft) requires more speakers"
    
    return True, speaker_count, "Adequate coverage"


# ==================== ENHANCED FALLBACK LOGIC ====================
def _get_fallback_product(category, sub_category, product_df, equipment_reqs=None, budget_tier='Standard'):
    """
    Intelligent fallback product selection with comprehensive filtering
    """
    # Initial filtering - SUB-CATEGORY IS MANDATORY
    if sub_category:
        matches = product_df[
            (product_df['category'] == category) &
            (product_df['sub_category'] == sub_category)
        ].copy()
    else:
        matches = product_df[product_df['category'] == category].copy()

    if matches.empty:
        st.warning(f"No products found for {category} / {sub_category}")
        return None  # Don't try to substitute from wrong sub-category

    # === GLOBAL SERVICE CONTRACT FILTER ===
    if category not in ['Software & Services']:
        # More specific pattern - avoid matching model numbers
        service_pattern = r'\b(support.*contract|maintenance.*contract|extended.*service|con-snt|con-ecdn|smartcare.*contract|jumpstart.*service|carepack|care\s*pack|premier.*support|advanced.*replacement.*service)\b'
        matches = matches[~matches['name'].str.contains(service_pattern, case=False, na=False, regex=True)]

    if matches.empty:
        return None

    # === CATEGORY-SPECIFIC INTELLIGENT SELECTION ===

    # Displays: Match size requirement with validation
    if category == 'Displays' and equipment_reqs and 'displays' in equipment_reqs:
        req_size = equipment_reqs['displays'].get('size_inches', 65)
        size_range = range(req_size - 3, req_size + 4)
        size_pattern = '|'.join([f'{s}"' for s in size_range])

        size_matches = matches[matches['name'].str.contains(size_pattern, na=False, regex=True)]
        if not size_matches.empty:
            matches = size_matches
        else:
            # If no exact match, find closest available size
            available_sizes = []
            for _, prod in matches.iterrows():
                size_match = re.search(r'(\d{2,3})["\']', prod['name'])
                if size_match:
                    available_sizes.append((abs(int(size_match.group(1)) - req_size), prod))
            if available_sizes:
                available_sizes.sort(key=lambda x: x[0])
                matches = pd.DataFrame([available_sizes[0][1]])

    # Intelligent Mount Selection
    if category == 'Mounts' and equipment_reqs and 'displays' in equipment_reqs:
        req_size = equipment_reqs['displays'].get('size_inches', 65)
        
        # CRITICAL: Only get Display Mounts, exclude Camera Mounts
        if 'sub_category' in equipment_reqs.get('displays', {}):
            # If explicitly requesting display mount
            matches = matches[matches['sub_category'] == 'Display Mount / Cart']
        else:
            # Filter by sub_category to exclude camera/projector mounts
            matches = matches[matches['sub_category'].isin(['Display Mount / Cart', 'Component / Rack Mount'])]
        
        # Additional blacklist for known problematic mounts
        MOUNT_BLACKLIST = ['X70 VESA', 'X50 VESA', 'X30 VESA', 'Rally Mount', 'Studio Mount']
        for blacklisted in MOUNT_BLACKLIST:
            matches = matches[~matches['model_number'].str.contains(blacklisted, case=False, na=False)]
        
        # For 90"+ displays, require heavy-duty keywords
        if req_size >= 90:
            matches = matches[matches['name'].str.contains(
                r'(90"|95"|98"|100"|86"-98"|heavy.*duty|commercial|extra.*large|large.*format)',
                case=False, na=False, regex=True
            )]

    # Video Conferencing: Ecosystem-aware selection
    if category == 'Video Conferencing':
        preferred_ecosystem = equipment_reqs.get('preferred_ecosystem') if equipment_reqs else None
        base_priority = ['Poly', 'Cisco', 'Logitech', 'Yealink', 'Neat', 'Crestron']
        
        brand_priority = base_priority
        if preferred_ecosystem and preferred_ecosystem.capitalize() in base_priority:
            brand_priority = [preferred_ecosystem.capitalize()] + \
                             [b for b in base_priority if b.lower() != preferred_ecosystem.lower()]

        for brand in brand_priority:
            brand_matches = matches[matches['brand'].str.contains(brand, case=False, na=False)]
            if not brand_matches.empty:
                matches = brand_matches
                break

    # Audio DSP: Strict processor selection
    if sub_category in ['DSP / Processor', 'DSP / Audio Processor / Mixer']:
        # Exclude non-DSP products
        matches = matches[~matches['name'].str.contains(
            r'\b(amplifier|amp-|summing|quad active|wall mount power|line driver|distribution)\b',
            case=False, na=False, regex=True
        )]
        
        # Prioritize known DSP brands
        dsp_brands = ['Biamp', 'QSC', 'Shure', 'Extron', 'Crestron', 'BSS', 'Symetrix']
        for brand in dsp_brands:
            brand_matches = matches[matches['brand'].str.contains(brand, case=False, na=False)]
            if not brand_matches.empty:
                matches = brand_matches
                break
        
        # Ensure product has DSP keywords
        if not matches.empty:
            dsp_matches = matches[matches['name'].str.contains(
                r'(dsp|processor|dante|aec|matrix|tesira|core)',
                case=False, na=False, regex=True
            )]
            if not dsp_matches.empty:
                matches = dsp_matches

    # Touch Controllers: Exclude incorrect products
    if sub_category in ['Touch Controller', 'Touch Controller / Panel']:
        matches = matches[~matches['name'].str.contains(
            r'\b(room kit|ess|codec|service|camera|display)\b',
            case=False, na=False, regex=True
        )]
        # Require touch controller keywords
        matches = matches[matches['name'].str.contains(
            r'(touch|panel|controller|tap|pad|navigator|scheduler)',
            case=False, na=False, regex=True
        )]

    # PDU: Strict rackmount PDU selection
    if sub_category == 'Power (PDU/UPS)':
        matches = matches[~matches['name'].str.contains(
            r'\b(wall mount|power pack|adapter|injector|power supply)\b',
            case=False, na=False, regex=True
        )]
        pdu_matches = matches[matches['name'].str.contains(
            r'(pdu|power distribution|rack.*power|ups|rackmount)',
            case=False, na=False, regex=True
        )]
        if not pdu_matches.empty:
            matches = pdu_matches

    # Amplifiers: Strict power amplifier selection
    if sub_category == 'Amplifier':
        # PHASE 1: Exclude Audio Interface / Extender products
        # These are often miscategorized summing amps
        matches = matches[matches['sub_category'] != 'Audio Interface / Extender']
        
        # PHASE 2: Explicit blacklist
        AMP_BLACKLIST = ['60-552', '60-553', 'Summing', 'Active Summing', 'Quad Active']
        for blacklisted in AMP_BLACKLIST:
            matches = matches[~matches['name'].str.contains(blacklisted, case=False, na=False, regex=True)]
        
        # PHASE 3: Require power amp indicators
        power_amp_matches = matches[matches['name'].str.contains(
            r'(power\s*amp|70v|100v|spa\d+|xpa\d+|\d+-channel.*amp|\d+w.*amp)',
            case=False, na=False, regex=True
        )]
        
        if not power_amp_matches.empty:
            matches = power_amp_matches
        else:
            st.warning(f"⚠️ No valid power amplifiers found in database for passive speakers")
            return None
            
    # Microphone Type Validation
    if sub_category == 'Ceiling Microphone':
        matches = matches[matches['name'].str.contains(
            r'(ceiling|pendant|overhead|array.*ceiling|mxa\d+|tcc\d|vcm3[0-9])',
            case=False, na=False, regex=True
        )]
        
        # Exclude table/USB mics
        matches = matches[~matches['name'].str.contains(
            r'(wired.*video|usb|table|boundary|vcm35)',
            case=False, na=False, regex=True
        )]

    # Ceiling Speakers: Proper speaker selection
    if sub_category == 'Ceiling Loudspeaker':
        matches = matches[matches['name'].str.contains(
            r'(ceiling|in-ceiling|pendant|flush mount)',
            case=False, na=False, regex=True
        )]
        # Exclude subwoofers and line arrays
        matches = matches[~matches['name'].str.contains(
            r'\b(subwoofer|sub|line array|column)\b',
            case=False, na=False, regex=True
        )]

    # Table Connectivity: Exclude wall plates
    if sub_category == 'Wall & Table Plate Module':
        table_matches = matches[matches['name'].str.contains(
            r'(table|tbus|floor|cubby|connectivity box|retractor|cable retractor)',
            case=False, na=False, regex=True
        )]
        if not table_matches.empty:
            matches = table_matches

    if matches.empty:
        return None

    # === BUDGET-AWARE SELECTION ===
    sorted_matches = matches.sort_values('price')

    if budget_tier in ['Premium', 'Executive']:
        start_idx = int(len(sorted_matches) * 0.75)
        selection_pool = sorted_matches.iloc[start_idx:]
        if not selection_pool.empty:
            return selection_pool.iloc[len(selection_pool) // 2].to_dict()
    elif budget_tier == 'Economy':
        end_idx = int(len(sorted_matches) * 0.4)
        selection_pool = sorted_matches.iloc[:end_idx] if end_idx > 0 else sorted_matches
        return selection_pool.iloc[len(selection_pool) // 2].to_dict()

    # Standard: Middle 50%
    start_idx = int(len(sorted_matches) * 0.25)
    end_idx = int(len(sorted_matches) * 0.75)
    selection_pool = sorted_matches.iloc[start_idx:end_idx] if end_idx > start_idx else sorted_matches
    
    if selection_pool.empty:
        return sorted_matches.iloc[len(sorted_matches)//2].to_dict()

    return selection_pool.iloc[len(selection_pool) // 2].to_dict()


# ==================== ENHANCED COMPONENT BLUEPRINT ====================
def _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier='Standard', room_area=300):
    """
    Build component requirements with physics validation
    """
    blueprint = {}
    
    # Extract room dimensions
    room_length = technical_reqs.get('room_length', (room_area ** 0.5) * 1.2)
    room_width = technical_reqs.get('room_width', room_area / room_length if room_length > 0 else 15)
    ceiling_height = technical_reqs.get('ceiling_height', 10)

    # Displays with validation
    if 'displays' in equipment_reqs:
        display_reqs = equipment_reqs.get('displays', {})
        qty = display_reqs.get('quantity', 1)
        size = display_reqs.get('size_inches', 65)
        
        # Validate display size
        is_valid, corrected_size, reason = _validate_display_size_for_room(
            size, room_length, technical_reqs.get('room_type', '')
        )
        
        if not is_valid:
            st.warning(f"Display size adjusted: {reason}. Using {corrected_size}\" instead of {size}\"")
            size = corrected_size
            # Update equipment_reqs for consistency
            equipment_reqs['displays']['size_inches'] = corrected_size

        blueprint['primary_display'] = {
            'category': 'Displays',
            'sub_category': 'Professional Display',
            'quantity': qty,
            'priority': 1,
            'justification': f'{size}" professional 4K display for primary viewing',
            'size_requirement': size
        }

        blueprint['display_mount'] = {
            'category': 'Mounts',
            'sub_category': 'Display Mount / Cart',  # Explicitly request display mounts
            'quantity': qty,
            'priority': 8,
            'justification': f'Heavy-duty mount for {size}" display',
            'size_requirement': size
        }

    # Video System
    if 'video_system' in equipment_reqs:
        video_reqs = equipment_reqs.get('video_system', {})
        video_type = video_reqs.get('type', '')

        if video_type == 'All-in-one Video Bar':
            blueprint['video_conferencing_system'] = {
                'category': 'Video Conferencing',
                'sub_category': 'Video Bar',
                'quantity': 1,
                'priority': 2,
                'justification': 'All-in-one video bar with integrated camera, microphones, and speakers'
            }
        elif video_type == 'Modular Codec + PTZ Camera':
            blueprint['video_codec'] = {
                'category': 'Video Conferencing',
                'sub_category': 'Room Kit / Codec',
                'quantity': 1,
                'priority': 2,
                'justification': 'Video conferencing codec/room system'
            }
            camera_count = video_reqs.get('camera_count', 1)
            if camera_count > 0:
                blueprint['ptz_camera'] = {
                    'category': 'Video Conferencing',
                    'sub_category': 'PTZ Camera',
                    'quantity': camera_count,
                    'priority': 2.5,
                    'justification': f'{camera_count}x PTZ camera(s) for comprehensive room coverage'
                }

    # Control System
    if 'control_system' in equipment_reqs:
        control_reqs = equipment_reqs.get('control_system', {})
        control_type = control_reqs.get('type', '')
        
        # Add touch controller for any control system requirement
        if control_type and 'touch' in control_type.lower():
            blueprint['touch_control_panel'] = {
                'category': 'Video Conferencing',
                'sub_category': 'Touch Controller / Panel',
                'quantity': 1,
                'priority': 3,
                'justification': 'Touch control panel for intuitive meeting control'
            }
        elif control_type:  # Generic control system
            blueprint['control_processor'] = {
                'category': 'Control Systems',
                'sub_category': 'Control Processor',
                'quantity': 1,
                'priority': 3,
                'justification': f'{control_type} for system control and automation'
            }

    # Audio System with validation
    if 'audio_system' in equipment_reqs:
        audio_reqs = equipment_reqs.get('audio_system', {})
        audio_type = audio_reqs.get('type', '')
        needs_dsp = audio_reqs.get('dsp_required', False)
        has_integrated_audio = 'integrated' in audio_type.lower() or 'video bar' in audio_type.lower()

        # Determine if this is a large room requiring distributed audio
        is_large_room_audio = any(x in audio_type.lower() for x in 
                                      ['ceiling audio', 'pro audio', 'voice reinforcement', 'fully integrated'])
        if is_large_room_audio:
            has_integrated_audio = False
            needs_dsp = True
        
        # Voice Reinforcement Systems
        if 'voice reinforcement' in audio_type.lower() or 'voice lift' in technical_reqs.get('audio_requirements', '').lower():
            blueprint['audio_dsp'] = {
                'category': 'Audio',
                'sub_category': 'DSP / Audio Processor / Mixer',
                'quantity': 1,
                'priority': 4,
                'justification': 'Digital signal processor for voice reinforcement and audio management'
            }
            blueprint['wireless_presenter_mic'] = {
                'category': 'Audio',
                'sub_category': 'Wireless Microphone System',
                'quantity': 1,
                'priority': 4.5,
                'justification': 'Wireless microphone system for presenter mobility'
            }
            needs_dsp = False

        # Dedicated DSP for complex audio
        elif needs_dsp and not has_integrated_audio:
            blueprint['audio_dsp'] = {
                'category': 'Audio',
                'sub_category': 'DSP / Audio Processor / Mixer',
                'quantity': 1,
                'priority': 4,
                'justification': 'Digital signal processor for advanced audio control and mixing'
            }

        # Microphones
        mic_type = audio_reqs.get('microphone_type', '')
        if mic_type and not has_integrated_audio:
            mic_count = audio_reqs.get('microphone_count', 2)

            if 'ceiling' in mic_type.lower():
                blueprint['ceiling_microphones'] = {
                    'category': 'Audio',
                    'sub_category': 'Ceiling Microphone',
                    'quantity': mic_count,
                    'priority': 5,
                    'justification': f'{mic_count}x ceiling microphones for uniform audio pickup'
                }
            elif 'table' in mic_type.lower() or 'boundary' in mic_type.lower():
                blueprint['table_microphones'] = {
                    'category': 'Audio',
                    'sub_category': 'Table/Boundary Microphone',
                    'quantity': mic_count,
                    'priority': 5,
                    'justification': f'{mic_count}x table microphones for participant audio'
                }

        # Speakers with coverage validation
        speaker_type = audio_reqs.get('speaker_type', '')
        if speaker_type and not has_integrated_audio:
            speaker_count = audio_reqs.get('speaker_count', 2)
            
            # Validate speaker coverage
            is_valid, recommended_count, reason = _validate_audio_coverage(
                speaker_count, room_area, ceiling_height
            )
            
            if not is_valid:
                st.warning(f"Speaker count adjusted: {reason}. Using {recommended_count} speakers")
                speaker_count = recommended_count
                audio_reqs['speaker_count'] = recommended_count

            if 'ceiling' in speaker_type.lower():
                blueprint['ceiling_speakers'] = {
                    'category': 'Audio',
                    'sub_category': 'Ceiling Loudspeaker',
                    'quantity': speaker_count,
                    'priority': 6,
                    'justification': f'{speaker_count}x ceiling speakers for even audio distribution (1 per 150 sq ft)'
                }
            elif 'wall' in speaker_type.lower():
                blueprint['wall_speakers'] = {
                    'category': 'Audio',
                    'sub_category': 'Wall-mounted Loudspeaker',
                    'quantity': speaker_count,
                    'priority': 6,
                    'justification': f'{speaker_count}x wall-mounted speakers'
                }

            # Add amplifier for passive speakers (only if speakers exist)
            if speaker_count > 0:
                blueprint['power_amplifier'] = {
                    'category': 'Audio',
                    'sub_category': 'Amplifier',
                    'quantity': 1,
                    'priority': 7,
                    'justification': f'Power amplifier for {speaker_count}x passive speakers'
                }

    # Connectivity & Infrastructure
    if equipment_reqs.get('content_sharing') or 'wireless presentation' in technical_reqs.get('features', '').lower():
        blueprint['table_connectivity'] = {
            'category': 'Cables & Connectivity',
            'sub_category': 'Wall & Table Plate Module',
            'quantity': 1,
            'priority': 9,
            'justification': 'Table connectivity box/AAP with HDMI, USB-C, and network inputs'
        }

    # Network Cables (scale with room complexity)
    cable_count = 5 if room_area < 400 else 8
    blueprint['network_cables'] = {
        'category': 'Cables & Connectivity',
        'sub_category': 'AV Cable',
        'quantity': cable_count,
        'priority': 10,
        'justification': f'Cat6 network patch cables for equipment connections'
    }

    # Rack Infrastructure (for rooms with modular systems)
    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['equipment_rack'] = {
            'category': 'Infrastructure',
            'sub_category': 'AV Rack',
            'quantity': 1,
            'priority': 12,
            'justification': 'Professional equipment rack for AV components'
        }

    # Power Management (essential for rack-based systems)
    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['power_distribution'] = {
            'category': 'Infrastructure',
            'sub_category': 'Power (PDU/UPS)',
            'quantity': 1,
            'priority': 11,
            'justification': 'Rackmount PDU with surge protection and power management'
        }

    return blueprint


# ==================== AI PROMPT ====================
def _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features, room_length=None, room_width=None):
    """
    Generate AI prompt for product selection
    """
    def format_product_list():
        product_text = ""
        for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
            product_text += f"\n## {comp_key.replace('_', ' ').upper()}\n"
            product_text += f"**Requirement:** {comp_spec['justification']}\n"
            
            cat = comp_spec['category']
            sub_cat = comp_spec.get('sub_category')
            
            if sub_cat:
                filtered_df = product_df[
                    (product_df['category'] == cat) &
                    (product_df['sub_category'] == sub_cat)
                ].copy()
            else:
                filtered_df = product_df[product_df['category'] == cat].copy()
            
            if cat not in ['Software & Services']:
                service_pattern = r'\b(ess|con-snt|con-ecdn|smartcare|jumpstart|carepack|care pack|premier|advanced replacement|onsite|warranty|support contract|maintenance|extended service)\b'
                filtered_df = filtered_df[~filtered_df['name'].str.contains(
                    service_pattern, case=False, na=False, regex=True
                )]
            
            if cat == 'Displays':
                req_size = comp_spec.get('size_requirement')
                if req_size:
                    size_range = range(req_size - 3, req_size + 4)
                    size_pattern = '|'.join([f'{s}"' for s in size_range])
                    size_filtered = filtered_df[filtered_df['name'].str.contains(
                        size_pattern, na=False, regex=True
                    )]
                    if not size_filtered.empty:
                        filtered_df = size_filtered
                    product_text += f"    **CRITICAL:** Must be {req_size}\" display (±3 inches)\n"
            
            if sub_cat in ['DSP / Processor', 'DSP / Audio Processor / Mixer']:
                filtered_df = filtered_df[~filtered_df['name'].str.contains(
                    r'\b(amplifier|amp-|summing|quad active|line driver)\b',
                    case=False, na=False, regex=True
                )]
                product_text += "    **CRITICAL:** Must be actual DSP/processor, NOT amplifier\n"
            
            if sub_cat and 'Touch Controller' in sub_cat:
                filtered_df = filtered_df[~filtered_df['name'].str.contains(
                    r'\b(room kit|codec|ess|camera)\b',
                    case=False, na=False, regex=True
                )]
                product_text += "    **CRITICAL:** Must be touch panel/controller, NOT room kit/codec\n"
            
            if sub_cat == 'Power (PDU/UPS)':
                filtered_df = filtered_df[~filtered_df['name'].str.contains(
                    r'\b(wall mount|power pack|adapter|power supply)\b',
                    case=False, na=False, regex=True
                )]
                product_text += "    **CRITICAL:** Must be rackmount PDU, NOT wall power supply\n"
            
            if sub_cat == 'Amplifier':
                filtered_df = filtered_df[~filtered_df['name'].str.contains(
                    r'\b(processor|dsp|mixer|line driver)\b',
                    case=False, na=False, regex=True
                )]
                product_text += "    **CRITICAL:** Must be POWER AMPLIFIER, NOT DSP\n"
            
            if not filtered_df.empty:
                product_text += "    **Available Products:**\n"
                product_text += "    | Brand | Model | Product Name | Price (USD) |\n"
                product_text += "    |-------|-------|--------------|-------------|\n"
                
                for _, prod in filtered_df.head(20).iterrows():
                    safe_name = str(prod['name'])[:60].replace('|', '-')
                    product_text += f"    | {prod['brand']} | {prod['model_number']} | {safe_name} | ${prod['price']:.0f} |\n"
            else:
                product_text += "    ⚠️ **WARNING:** No matching products found after filtering\n"
        
        return product_text

    base_prompt = f"""You are a CTS-D certified AV systems designer selecting products for a professional '{room_type}' installation.

# CRITICAL SELECTION RULES (MUST FOLLOW)
1. Select ONLY products that EXACTLY match the component's sub-category
2. NEVER select service contracts, warranties, or support agreements for hardware
3. For displays: Match size requirement within ±3 inches
4. For DSPs: Select ACTUAL processors with DSP capabilities, NEVER amplifiers
5. For Amplifiers: Select POWER AMPLIFIERS only, NEVER DSPs or mixers
6. For Touch Controllers: Select touch panels ONLY, NEVER room kits
7. For PDUs: Select rackmount power distribution ONLY
8. Verify product name matches the requirement before selection

# Room Configuration
- **Room Type:** {room_type}
- **Budget Level:** {budget_tier}
- **Special Requirements:** {features if features else 'Standard professional AV configuration'}

# Required Components and Available Products
{format_product_list()}

# OUTPUT REQUIREMENTS
Return ONLY valid JSON with exact product names and models from the tables above.

JSON Format:
{{"""
    
    json_format = '\n'
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format += f'  "{comp_key}": {{"name": "EXACT product name from table", "model_number": "EXACT model from table", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format += "}\n"
    
    return base_prompt + json_format


# ==================== PARSING & BOQ CONSTRUCTION ====================
def _parse_ai_product_selection(ai_response_text):
    """Parse AI response with error handling"""
    try:
        cleaned = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
        if cleaned:
            return json.loads(cleaned.group(0))
        st.warning("Could not find valid JSON in AI response.")
        return {}
    except Exception as e:
        st.warning(f"Failed to parse AI response: {e}")
        return {}


def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs):
    """Build BOQ items from AI selection"""
    boq_items = []
    
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components:
            continue
        
        comp_spec = required_components[comp_key]
        
        matched_product = match_product_in_database(
            product_name=selection.get('name'),
            brand=None,
            model_number=selection.get('model_number'),
            product_df=product_df
        )
        
        if matched_product:
            item = {
                'category': matched_product.get('category', comp_spec['category']),
                'sub_category': matched_product.get('sub_category', comp_spec.get('sub_category', '')),
                'name': matched_product.get('name', ''),
                'brand': matched_product.get('brand', ''),
                'model_number': matched_product.get('model_number', ''),
                'quantity': selection.get('qty', comp_spec['quantity']),
                'price': float(matched_product.get('price', 0)),
                'justification': comp_spec['justification'],
                'specifications': matched_product.get('specifications', ''),
                'image_url': matched_product.get('image_url', ''),
                'gst_rate': matched_product.get('gst_rate', 18),
                'warranty': matched_product.get('warranty', 'Not Specified'),
                'lead_time_days': matched_product.get('lead_time_days', 14),
                'matched': True
            }
            boq_items.append(item)
        else:
            fallback = _get_fallback_product(
                comp_spec['category'],
                comp_spec.get('sub_category'),
                product_df,
                equipment_reqs,
                'Standard'
            )
            if fallback:
                fallback.update({
                    'quantity': comp_spec['quantity'],
                    'justification': f"{comp_spec['justification']} (Auto-selected fallback)",
                    'matched': False
                })
                boq_items.append(fallback)
    
    return boq_items


def _validate_boq_selections(boq_items, equipment_reqs):
    """Validate BOQ selections for common errors"""
    for item in boq_items:
        name_lower = item.get('name', '').lower()
        category = item.get('category', '')
        
        if category not in ['Software & Services']:
            if any(keyword in name_lower for keyword in ['ess', 'support', 'warranty', 'service contract', 'con-snt']):
                item['justification'] += " ⚠️ **VALIDATION ERROR**: Service contract detected in hardware category"
                item['matched'] = False
        
        if category == 'Displays':
            req_size = equipment_reqs.get('displays', {}).get('size_inches')
            if req_size:
                size_match = re.search(r'(\d{2,3})["\']', item['name'])
                if size_match:
                    actual_size = int(size_match.group(1))
                    if abs(actual_size - req_size) > 5:
                        item['justification'] += f" ⚠️ **SIZE MISMATCH**: Required ~{req_size}\", selected {actual_size}\""
        
        if 'DSP' in item.get('sub_category', '') or 'Processor' in item.get('sub_category', ''):
            if any(word in name_lower for word in ['amplifier', 'amp-', 'summing']):
                item['justification'] += " ⚠️ **WRONG TYPE**: Amplifier selected instead of DSP"
                item['matched'] = False
        
        if 'Touch Controller' in item.get('sub_category', ''):
            if any(word in name_lower for word in ['room kit', 'codec', 'ess']):
                item['justification'] += " ⚠️ **WRONG TYPE**: Room kit/codec selected instead of touch panel"
                item['matched'] = False
        
        if item.get('sub_category') == 'Power (PDU/UPS)':
            if any(word in name_lower for word in ['wall mount', 'power pack', 'adapter']):
                item['justification'] += " ⚠️ **WRONG TYPE**: Wall power supply selected instead of PDU"
                item['matched'] = False
    
    return boq_items


def _remove_exact_duplicates(boq_items):
    """Remove duplicate products from BOQ"""
    seen = set()
    unique_items = []
    
    for item in boq_items:
        identifier = item.get('model_number') or item.get('name')
        if identifier not in seen:
            unique_items.append(item)
            seen.add(identifier)
    
    return unique_items


def _correct_quantities(boq_items):
    """Ensure all quantities are valid positive integers"""
    for item in boq_items:
        try:
            item['quantity'] = int(float(item.get('quantity', 1)))
        except (ValueError, TypeError):
            item['quantity'] = 1
        
        if item['quantity'] == 0:
            item['quantity'] = 1
    
    return boq_items


def validate_boq_completeness(boq_items, required_components):
    """Check if BOQ has all required components"""
    missing_components = []
    present_sub_categories = {item.get('sub_category') for item in boq_items}
    
    for comp_key, comp_spec in required_components.items():
        if comp_spec.get('sub_category') not in present_sub_categories:
            missing_components.append({
                'component': comp_key,
                'category': comp_spec['category'],
                'justification': comp_spec['justification']
            })
    
    return missing_components


def validate_component_dependencies(boq_items, required_components):
    """Validate that dependent components are present together"""
    issues = []
    
    # Check: Amplifier requires speakers
    has_amplifier = any('Amplifier' in item.get('sub_category', '') for item in boq_items)
    has_speakers = any('Loudspeaker' in item.get('sub_category', '') for item in boq_items)
    
    if has_amplifier and not has_speakers:
        issues.append("Amplifier present but no speakers found - amplifier serves no purpose")
    
    # Check: Speakers require amplifier or powered speakers
    if has_speakers and not has_amplifier:
        # Verify they're powered speakers
        speaker_items = [item for item in boq_items if 'Loudspeaker' in item.get('sub_category', '')]
        if not any('powered' in item.get('name', '').lower() or 'active' in item.get('name', '').lower() 
                   for item in speaker_items):
            issues.append("Passive speakers present but no amplifier found")
    
    # Check: Rack-mount equipment requires rack
    rackmount_items = [item for item in boq_items 
                           if any(x in item.get('name', '').lower() for x in ['rack', '1u', '2u', '3u', 'rackmount'])]
    has_rack = any('Rack' in item.get('sub_category', '') for item in boq_items)
    
    if rackmount_items and not has_rack:
        issues.append(f"{len(rackmount_items)} rack-mount equipment present but no rack specified")
    
    # Check: Display requires mount
    has_display = any('Display' in item.get('category', '') for item in boq_items)
    has_mount = any('Mount' in item.get('category', '') for item in boq_items)
    
    if has_display and not has_mount:
        issues.append("Display present but no mount specified")
    
    return issues


def validate_price_reasonableness(boq_items):
    """Flag suspiciously priced items"""
    warnings = []
    
    price_expectations = {
        'Displays': {'min': 500, 'max': 50000},
        'Video Conferencing': {'min': 300, 'max': 30000},
        'Audio': {'min': 50, 'max': 10000},
        'Mounts': {'min': 50, 'max': 2000},
        'Infrastructure': {'min': 100, 'max': 5000}
    }
    
    for item in boq_items:
        category = item.get('category', '')
        price = item.get('price', 0)
        
        if category in price_expectations:
            expected = price_expectations[category]
            if price < expected['min']:
                warnings.append(f"{item.get('name', 'Unknown')}: Price ${price:.0f} unusually low for {category}")
            elif price > expected['max']:
                warnings.append(f"{item.get('name', 'Unknown')}: Price ${price:.0f} unusually high for {category}")
    
    return warnings


def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components):
    """Post-process BOQ with validation and auto-fill missing components"""
    processed_boq = _correct_quantities(boq_items)
    processed_boq = _remove_exact_duplicates(processed_boq)
    processed_boq = _validate_boq_selections(processed_boq, equipment_reqs)
    
    validation_results = {'issues': [], 'warnings': []}
    
    missing_components = validate_boq_completeness(processed_boq, required_components)
    if missing_components:
        for missing in missing_components:
            # Try to add the missing component via fallback
            comp_spec = required_components.get(missing['component'])
            if comp_spec:
                fallback_product = _get_fallback_product(
                    comp_spec['category'],
                    comp_spec.get('sub_category'),
                    product_df,
                    equipment_reqs,
                    'Standard'
                )
                if fallback_product:
                    fallback_product.update({
                        'quantity': comp_spec['quantity'],
                        'justification': f"{comp_spec['justification']} (Auto-filled missing component)",
                        'matched': False
                    })
                    processed_boq.append(fallback_product)
                    validation_results['warnings'].append(
                        f"Auto-filled missing component: {missing['component'].replace('_', ' ')}"
                    )
                else:
                    issue_text = f"Missing Component: '{missing['component'].replace('_', ' ')}' ({missing['category']}). No fallback product available."
                    validation_results['issues'].append(issue_text)
    
    # Explicit control system check
    has_control = any('Control' in item.get('category', '') or 
                      'Touch Controller' in item.get('sub_category', '') 
                      for item in processed_boq)

    if not has_control and equipment_reqs.get('control_system'):
        validation_results['warnings'].append(
            "Control system specified in requirements but not found in BOQ"
        )
        
        # Auto-add control system
        control_fallback = _get_fallback_product(
            'Video Conferencing',
            'Touch Controller / Panel',
            product_df,
            equipment_reqs,
            'Standard'
        )
        if control_fallback:
            control_fallback.update({
                'quantity': 1,
                'justification': 'Touch control panel (Auto-added missing component)',
                'matched': False
            })
            processed_boq.append(control_fallback)
            
    # Add dependency and price validation checks
    dependency_issues = validate_component_dependencies(processed_boq, required_components)
    if dependency_issues:
        validation_results['warnings'].extend(dependency_issues)
        
    price_warnings = validate_price_reasonableness(processed_boq)
    if price_warnings:
        validation_results['warnings'].extend(price_warnings)
    
    return processed_boq, validation_results


def create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs, budget_tier='Standard'):
    """Create BOQ using fallback logic"""
    st.warning("AI selection unavailable. Building BOQ with intelligent fallback logic.")
    
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier, technical_reqs.get('room_area', 300))
    fallback_items = []
    
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(
            comp_spec['category'],
            comp_spec.get('sub_category'),
            product_df,
            equipment_reqs,
            budget_tier
        )
        
        if product:
            product.update({
                'quantity': comp_spec['quantity'],
                'justification': f"{comp_spec['justification']} (Intelligent auto-selection)",
                'matched': False
            })
            fallback_items.append(product)
    
    return fallback_items, required_components


def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Main BOQ generation function"""
    length = (room_area ** 0.5) * 1.2
    width = room_area / length
    
    avixa_calcs = calculate_avixa_recommendations(
        length, width,
        technical_reqs.get('ceiling_height', 10),
        room_type
    )
    
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier, room_area)
    
    prompt = _get_prompt_for_room_type(
        room_type, equipment_reqs, required_components,
        product_df, budget_tier, features, length, width
    )
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not hasattr(response, 'text') or not response.text:
            raise Exception("AI returned empty response")
        
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse AI product selection")
        
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs)
        if not boq_items:
            raise Exception("No BOQ items generated from AI selection")
            
    except Exception as e:
        st.warning(f"AI generation failed ({str(e)}). Using intelligent fallback system.")
        boq_items, required_components = create_smart_fallback_boq(
            product_df, equipment_reqs, technical_reqs, budget_tier
        )
    
    processed_boq, validation_results = post_process_boq(
        boq_items, product_df, avixa_calcs,
        equipment_reqs, room_type, required_components
    )
    
    return processed_boq, avixa_calcs, equipment_reqs, validation_results


def boq_to_dataframe(boq_items):
    """Convert BOQ items to DataFrame"""
    if not boq_items:
        return pd.DataFrame()
    
    df = pd.DataFrame(boq_items)
    
    required_columns = [
        'category', 'sub_category', 'name', 'brand', 'model_number',
        'quantity', 'price', 'justification', 'specifications',
        'gst_rate', 'warranty', 'lead_time_days'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
    
    df['line_total'] = df['quantity'] * df['price']
    df['gst_amount'] = df['line_total'] * (df['gst_rate'] / 100)
    df['total_with_gst'] = df['line_total'] + df['gst_amount']
    
    column_order = [
        'category', 'sub_category', 'brand', 'model_number', 'name',
        'quantity', 'price', 'line_total', 'gst_rate', 'gst_amount',
        'total_with_gst', 'justification', 'specifications',
        'warranty', 'lead_time_days'
    ]
    
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]
    
    return df


def calculate_boq_summary(boq_df):
    """Calculate BOQ summary statistics"""
    if boq_df.empty:
        return {
            'total_items': 0,
            'total_quantity': 0,
            'subtotal': 0,
            'total_gst': 0,
            'grand_total': 0,
            'categories': {}
        }
    
    summary = {
        'total_items': len(boq_df),
        'total_quantity': int(boq_df['quantity'].sum()),
        'subtotal': float(boq_df['line_total'].sum()),
        'total_gst': float(boq_df['gst_amount'].sum()),
        'grand_total': float(boq_df['total_with_gst'].sum()),
        'categories': {}
    }
    
    if 'category' in boq_df.columns:
        summary['categories'] = boq_df.groupby('category').agg({
            'quantity': 'sum',
            'line_total': 'sum',
            'total_with_gst': 'sum'
        }).to_dict('index')
    
    return summary


def export_boq_to_excel(boq_df, filename="boq_export.xlsx"):
    """Export BOQ to Excel file"""
    from io import BytesIO
    
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        boq_df.to_excel(writer, sheet_name='BOQ', index=False)
        
        workbook = writer.book
        worksheet = writer.sheets['BOQ']
        
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    return output

