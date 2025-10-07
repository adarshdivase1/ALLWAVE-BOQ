# components/boq_generator.py
# PRODUCTION-READY VERSION - FULLY FIXED

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


# ==================== CLIENT PREFERENCES PARSER ====================
def parse_client_preferences(features_text):
    """
    Extract client brand/product preferences from requirements text.
    Returns dict with preferred brands for each category.
    """
    if not features_text:
        return {}
    
    text_lower = features_text.lower()
    preferences = {
        'displays': None,
        'video_conferencing': None,
        'audio': None,
        'control': None,
        'cables': None
    }
    
    # Display brands
    display_brands = ['samsung', 'lg', 'nec', 'sony', 'sharp', 'viewsonic']
    for brand in display_brands:
        if brand in text_lower and ('display' in text_lower or 'screen' in text_lower or 'monitor' in text_lower):
            preferences['displays'] = brand.capitalize()
            break
    
    # Video conferencing brands
    vc_brands = ['poly', 'cisco', 'yealink', 'logitech', 'neat', 'crestron', 'zoom']
    for brand in vc_brands:
        if brand in text_lower and any(kw in text_lower for kw in ['video', 'conferencing', 'camera', 'codec']):
            preferences['video_conferencing'] = brand.capitalize()
            break
    
    # Audio brands
    audio_brands = ['shure', 'biamp', 'qsc', 'extron', 'bose', 'sennheiser', 'audio-technica']
    for brand in audio_brands:
        if brand in text_lower and any(kw in text_lower for kw in ['audio', 'microphone', 'speaker', 'dsp']):
            preferences['audio'] = brand.capitalize()
            break
    
    # Control brands
    control_brands = ['crestron', 'extron', 'amx', 'qsc']
    for brand in control_brands:
        if brand in text_lower and any(kw in text_lower for kw in ['control', 'touch panel', 'processor']):
            preferences['control'] = brand.capitalize()
            break
    
    return preferences


# ==================== ENHANCED FALLBACK WITH CLIENT PREFERENCES ====================
def _get_fallback_product(category, sub_category, product_df, equipment_reqs=None, budget_tier='Standard', client_preferences=None):
    """
    Intelligent fallback with CLIENT BRAND PREFERENCE support
    """
    if sub_category:
        matches = product_df[
            (product_df['category'] == category) &
            (product_df['sub_category'] == sub_category)
        ].copy()
    else:
        matches = product_df[product_df['category'] == category].copy()

    if matches.empty:
        return None

    # === CRITICAL: STRICT SERVICE CONTRACT FILTER ===
    if category not in ['Software & Services']:
        # More aggressive pattern to catch all service contracts
        service_pattern = r'\b(support.*contract|maintenance.*contract|extended.*service|extended.*warranty|con-snt|con-ecdn|smartcare.*contract|jumpstart.*service|carepack|care\s*pack|premier.*support|advanced.*replacement|onsite.*support|warranty.*extension|service.*agreement)\b'
        matches = matches[~matches['name'].str.contains(service_pattern, case=False, na=False, regex=True)]
        
        # Additional check: if "warranty" or "service" in name but price < $100, likely a service contract
        matches = matches[~((matches['name'].str.contains(r'\b(warranty|service)\b', case=False, regex=True)) & 
                            (matches['price'] < 100))]

    if matches.empty:
        return None

    # === APPLY CLIENT PREFERENCES FIRST ===
    if client_preferences:
        preferred_brand = None
        
        if category == 'Displays':
            preferred_brand = client_preferences.get('displays')
        elif category == 'Video Conferencing':
            preferred_brand = client_preferences.get('video_conferencing')
        elif category == 'Audio':
            preferred_brand = client_preferences.get('audio')
        elif category in ['Control Systems', 'Signal Management']:
            preferred_brand = client_preferences.get('control')
        
        if preferred_brand:
            brand_matches = matches[matches['brand'].str.lower() == preferred_brand.lower()]
            if not brand_matches.empty:
                matches = brand_matches
                st.info(f"✅ Using client-preferred brand: {preferred_brand} for {category}")

    # === DISPLAY MOUNT FIX ===
    if category == 'Mounts' and sub_category == 'Display Mount / Cart':
        # CRITICAL: Exclude ALL non-mount items
        MOUNT_BLACKLIST = [
            'finishing ring', 'trim ring', 'bezel', 'spacer', 'adapter plate',
            'x70 vesa', 'x50 vesa', 'x30 vesa', 'rally mount', 'studio mount',
            'camera mount', 'microphone mount', 'bracket kit', 'accessory'
        ]
        
        for blacklisted in MOUNT_BLACKLIST:
            matches = matches[~matches['name'].str.contains(blacklisted, case=False, na=False)]
        
        # REQUIRE mount-specific keywords
        mount_keywords = r'(wall.*mount|ceiling.*mount|floor.*stand|mobile.*stand|tv.*mount|display.*mount|fixed.*mount|tilt.*mount|articulating.*mount|cart|trolley)'
        matches = matches[matches['name'].str.contains(mount_keywords, case=False, na=False, regex=True)]
        
        # For large displays (85"+), require heavy-duty
        if equipment_reqs and 'displays' in equipment_reqs:
            req_size = equipment_reqs['displays'].get('size_inches', 65)
            if req_size >= 85:
                matches = matches[matches['name'].str.contains(
                    r'(heavy.*duty|large.*format|commercial|85|90|95|98|100)',
                    case=False, na=False, regex=True
                )]

    # === TABLE CONNECTIVITY FIX ===
    if sub_category == 'Wall & Table Plate Module':
        # Prioritize complete connectivity solutions
        connectivity_priority = r'(aap|table.*box|connectivity.*box|hdmi.*plate|retractor|tbus|hydraport|floor.*box)'
        priority_matches = matches[matches['name'].str.contains(connectivity_priority, case=False, na=False, regex=True)]
        
        if not priority_matches.empty:
            matches = priority_matches
        
        # Exclude mounting-only hardware
        matches = matches[~matches['name'].str.contains(
            r'(mounting.*frame.*only|blank.*plate|housing.*only|bracket.*only|trim.*ring)',
            case=False, na=False, regex=True
        )]

    # === TOUCH CONTROLLER FIX ===
    if 'Touch Controller' in sub_category:
        # STRICT: Must have touch/panel/controller keywords
        matches = matches[matches['name'].str.contains(
            r'(touch.*panel|touch.*controller|control.*panel|scheduling.*panel|room.*panel|tap|navigator)',
            case=False, na=False, regex=True
        )]
        
        # EXCLUDE video conferencing systems
        matches = matches[~matches['name'].str.contains(
            r'\b(room.*kit|codec|bar|camera|ess)\b',
            case=False, na=False, regex=True
        )]

    # === DSP SELECTION FIX ===
    if 'DSP' in sub_category or 'Processor' in sub_category:
        # EXCLUDE amplifiers completely
        matches = matches[~matches['name'].str.contains(
            r'\b(amplifier|amp-|summing|quad.*active|power.*amp)\b',
            case=False, na=False, regex=True
        )]
        
        # REQUIRE DSP indicators
        dsp_matches = matches[matches['name'].str.contains(
            r'(dsp|digital.*signal.*processor|audio.*processor|dante|aec|matrix|tesira|core|q-sys)',
            case=False, na=False, regex=True
        )]
        
        if not dsp_matches.empty:
            matches = dsp_matches

    # === AMPLIFIER SELECTION FIX ===
    if sub_category == 'Amplifier':
        # Phase 1: Exclude non-amplifier categories
        matches = matches[matches['sub_category'] == 'Amplifier']
        
        # Phase 2: Strict blacklist
        AMP_BLACKLIST = ['60-552', '60-553', 'summing', 'quad active', 'line driver', 
                         'audio interface', 'dsp', 'processor', 'mixer']
        for blacklisted in AMP_BLACKLIST:
            matches = matches[~matches['name'].str.contains(blacklisted, case=False, na=False, regex=True)]
        
        # Phase 3: Require power amp indicators
        power_amp_matches = matches[matches['name'].str.contains(
            r'(power.*amp|multi.*channel|70v|100v|watts.*channel|\d+w.*amp|spa\d+|xpa\d+|amplifier)',
            case=False, na=False, regex=True
        )]
        
        if not power_amp_matches.empty:
            matches = power_amp_matches
        else:
            st.warning(f"⚠️ No valid power amplifiers found for passive speakers")
            return None

    # === DISPLAY SIZE MATCHING ===
    if category == 'Displays' and equipment_reqs and 'displays' in equipment_reqs:
        req_size = equipment_reqs['displays'].get('size_inches', 65)
        size_range = range(req_size - 3, req_size + 4)
        size_pattern = '|'.join([f'{s}"' for s in size_range])

        size_matches = matches[matches['name'].str.contains(size_pattern, na=False, regex=True)]
        if not size_matches.empty:
            matches = size_matches

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


# ==================== COMPONENT BLUEPRINT WITH CONTROL SYSTEM ====================
# UPDATE: components/boq_generator.py

def _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier='Standard', room_area=300):
    """
    Enhanced blueprint with strict product requirements
    """
    # This function requires a ProductRequirement class/object to be defined elsewhere
    # For this file to be self-contained, a placeholder is needed.
    class ProductRequirement:
        def __init__(self, **kwargs):
            self.spec = kwargs
        def __getitem__(self, key):
            return self.spec.get(key)

    blueprint = {}
    
    room_length = technical_reqs.get('room_length', (room_area ** 0.5) * 1.2)
    room_width = technical_reqs.get('room_width', room_area / room_length if room_length > 0 else 15)
    ceiling_height = technical_reqs.get('ceiling_height', 10)

    # === DISPLAYS with STRICT REQUIREMENTS ===
    if 'displays' in equipment_reqs:
        display_reqs = equipment_reqs['displays']
        qty = display_reqs.get('quantity', 1)
        size = display_reqs.get('size_inches', 65)

        blueprint['primary_display'] = ProductRequirement(
            category='Displays',
            sub_category='Professional Display',
            quantity=qty,
            priority=1,
            justification=f'{size}" professional 4K display for primary viewing',
            size_requirement=size,
            required_keywords=['display', 'monitor', '4k', 'uhd'],
            blacklist_keywords=['mount', 'bracket', 'stand', 'arm'],
            client_preference_weight=0.8  # High importance for display brand
        )

        # FIXED: Display Mount with STRICT requirements
        blueprint['display_mount'] = ProductRequirement(
            category='Mounts',
            sub_category='Display Mount / Cart',
            quantity=qty,
            priority=8,
            justification=f'Professional wall/floor mount for {size}" display',
            size_requirement=size,
            mounting_type='wall' if ceiling_height > 9 else 'floor',
            required_keywords=['mount', 'wall', 'tv', 'display'] if ceiling_height > 9 else ['cart', 'stand', 'trolley', 'mobile'],
            blacklist_keywords=[
                'ring', 'bezel', 'trim', 'spacer', 'adapter plate',
                'x70', 'x50', 'x30', 'rally', 'studio', 'camera',
                'accessory', 'bracket kit', 'finishing'
            ],
            compatibility_requirements=[f'{size}"'] if size >= 85 else []
        )

    # === VIDEO SYSTEM ===
    if 'video_system' in equipment_reqs:
        video_reqs = equipment_reqs['video_system']
        video_type = video_reqs.get('type', '')

        if video_type == 'All-in-one Video Bar':
            blueprint['video_conferencing_system'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Video Bar',
                quantity=1,
                priority=2,
                justification='All-in-one video bar with integrated camera, microphones, and speakers',
                required_keywords=['bar', 'video', 'all-in-one', 'camera'],
                blacklist_keywords=['mount', 'accessory', 'bracket', 'replacement'],
                client_preference_weight=0.9
            )
        elif video_type == 'Modular Codec + PTZ Camera':
            blueprint['video_codec'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Room Kit / Codec',
                quantity=1,
                priority=2,
                justification='Video conferencing codec/room system',
                required_keywords=['codec', 'room kit', 'system'],
                blacklist_keywords=['camera only', 'accessory', 'mount', 'license'],
                client_preference_weight=0.9
            )
            
            camera_count = video_reqs.get('camera_count', 1)
            if camera_count > 0:
                blueprint['ptz_camera'] = ProductRequirement(
                    category='Video Conferencing',
                    sub_category='PTZ Camera',
                    quantity=camera_count,
                    priority=2.5,
                    justification=f'{camera_count}x PTZ camera(s) for comprehensive room coverage',
                    required_keywords=['ptz', 'camera', 'zoom'],
                    blacklist_keywords=['mount', 'bracket', 'accessory', 'webcam'],
                    compatibility_requirements=[video_reqs.get('brand', '')]
                )

    # === CONTROL SYSTEM (MANDATORY) ===
    blueprint['touch_control_panel'] = ProductRequirement(
        category='Video Conferencing',
        sub_category='Touch Controller / Panel',
        quantity=1,
        priority=3,
        justification='Touch control panel for system control and meeting management',
        required_keywords=['touch', 'controller', 'panel', 'control'],
        blacklist_keywords=[
            'room kit', 'codec', 'bar', 'camera', 'display',
            'monitor', 'ess', 'system', 'video bar'
        ]
    )

    # === AUDIO SYSTEM with STRICT RULES ===
    if 'audio_system' in equipment_reqs:
        audio_reqs = equipment_reqs['audio_system']
        audio_type = audio_reqs.get('type', '')
        needs_dsp = audio_reqs.get('dsp_required', False)
        
        # Check if audio is integrated (video bar)
        has_integrated_audio = 'integrated' in audio_type.lower() or 'video bar' in audio_type.lower()

        # For large room audio systems
        is_large_room_audio = any(x in audio_type.lower() for x in 
                                  ['ceiling audio', 'pro audio', 'voice reinforcement', 'fully integrated'])
        if is_large_room_audio:
            has_integrated_audio = False
            needs_dsp = True
        
        # DSP (if needed)
        if needs_dsp and not has_integrated_audio:
            blueprint['audio_dsp'] = ProductRequirement(
                category='Audio',
                sub_category='DSP / Audio Processor / Mixer',
                quantity=1,
                priority=4,
                justification='Digital signal processor for audio management',
                required_keywords=['dsp', 'processor', 'audio', 'digital'],
                blacklist_keywords=[
                    'amplifier', 'amp-', 'power amp', 'summing',
                    '60-552', '60-553', 'line driver'
                ],
                client_preference_weight=0.7
            )

        # Microphones
        mic_type = audio_reqs.get('microphone_type', '')
        if mic_type and not has_integrated_audio:
            mic_count = audio_reqs.get('microphone_count', 2)

            if 'ceiling' in mic_type.lower():
                blueprint['ceiling_microphones'] = ProductRequirement(
                    category='Audio',
                    sub_category='Ceiling Microphone',
                    quantity=mic_count,
                    priority=5,
                    justification=f'{mic_count}x ceiling microphones for audio pickup',
                    required_keywords=['ceiling', 'microphone', 'mic'],
                    blacklist_keywords=['mount', 'bracket', 'accessory', 'table']
                )
            elif 'table' in mic_type.lower():
                blueprint['table_microphones'] = ProductRequirement(
                    category='Audio',
                    sub_category='Table/Boundary Microphone',
                    quantity=mic_count,
                    priority=5,
                    justification=f'{mic_count}x table microphones',
                    required_keywords=['table', 'boundary', 'microphone'],
                    blacklist_keywords=['ceiling', 'wireless', 'mount']
                )

        # Speakers
        speaker_type = audio_reqs.get('speaker_type', '')
        if speaker_type and not has_integrated_audio:
            speaker_count = audio_reqs.get('speaker_count', 2)

            if 'ceiling' in speaker_type.lower():
                blueprint['ceiling_speakers'] = ProductRequirement(
                    category='Audio',
                    sub_category='Ceiling Loudspeaker',
                    quantity=speaker_count,
                    priority=6,
                    justification=f'{speaker_count}x ceiling speakers',
                    required_keywords=['ceiling', 'speaker', 'loudspeaker'],
                    blacklist_keywords=['mount', 'bracket', 'wall', 'portable']
                )

            # CRITICAL: Amplifier for passive speakers
            if speaker_count > 0:
                blueprint['power_amplifier'] = ProductRequirement(
                    category='Audio',
                    sub_category='Amplifier',
                    quantity=1,
                    priority=7,
                    justification=f'Power amplifier for {speaker_count} passive speakers',
                    power_requirement=speaker_count * 100,  # Rough estimate
                    required_keywords=['amplifier', 'power', 'channel', 'watts'],
                    blacklist_keywords=[
                        'summing', 'quad active', 'line driver',
                        '60-552', '60-553', 'dsp', 'processor',
                        'mixer', 'interface'
                    ]
                )

    # === CONNECTIVITY ===
    if equipment_reqs.get('content_sharing') or 'wireless presentation' in technical_reqs.get('features', '').lower():
        blueprint['table_connectivity'] = ProductRequirement(
            category='Cables & Connectivity',
            sub_category='Wall & Table Plate Module',
            quantity=1,
            priority=9,
            justification='Table connectivity with HDMI, USB-C, and network',
            required_keywords=['table', 'plate', 'connectivity', 'hdmi'],
            blacklist_keywords=['mounting frame only', 'blank plate', 'housing only', 'trim ring']
        )

    # Network Cables
    cable_count = 5 if room_area < 400 else 8
    blueprint['network_cables'] = ProductRequirement(
        category='Cables & Connectivity',
        sub_category='AV Cable',
        quantity=cable_count,
        priority=10,
        justification='Network patch cables for equipment',
        required_keywords=['cable', 'network', 'ethernet', 'cat'],
        blacklist_keywords=['bulk', 'spool', 'reel']
    )

    # Infrastructure
    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['equipment_rack'] = ProductRequirement(
            category='Infrastructure',
            sub_category='AV Rack',
            quantity=1,
            priority=12,
            justification='Equipment rack for AV components',
            required_keywords=['rack', 'enclosure', 'cabinet'],
            blacklist_keywords=['shelf', 'mount kit', 'accessory']
        )

    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['power_distribution'] = ProductRequirement(
            category='Infrastructure',
            sub_category='Power (PDU/UPS)',
            quantity=1,
            priority=11,
            justification='Rackmount PDU with surge protection',
            required_keywords=['pdu', 'power', 'distribution'],
            blacklist_keywords=['ups battery', 'replacement battery']
        )

    return blueprint


# ==================== MAIN BOQ GENERATION ====================
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """
    Main BOQ generation with CLIENT PREFERENCE support
    """
    # Parse client preferences
    client_preferences = parse_client_preferences(features)
    
    if client_preferences:
        st.success(f"📋 Client Preferences Detected: {', '.join([f'{k}: {v}' for k, v in client_preferences.items() if v])}")
    
    length = (room_area ** 0.5) * 1.2
    width = room_area / length
    
    avixa_calcs = calculate_avixa_recommendations(
        length, width,
        technical_reqs.get('ceiling_height', 10),
        room_type
    )
    
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier, room_area)
    
    # Use fallback system with client preferences
    try:
        boq_items = []
        
        for comp_key, comp_spec in required_components.items():
            product = _get_fallback_product(
                comp_spec['category'],
                comp_spec.get('sub_category'),
                product_df,
                equipment_reqs,
                budget_tier,
                client_preferences  # PASS CLIENT PREFERENCES
            )
            
            if product:
                product.update({
                    'quantity': comp_spec['quantity'],
                    'justification': comp_spec['justification'],
                    'matched': True
                })
                boq_items.append(product)
            else:
                st.warning(f"⚠️ Could not find product for: {comp_key}")
        
        if not boq_items:
            raise Exception("No BOQ items generated")
            
    except Exception as e:
        st.error(f"BOQ generation failed: {str(e)}")
        return [], {}, {}, {}
    
    # Post-process and validate
    processed_boq, validation_results = post_process_boq(
        boq_items, product_df, avixa_calcs,
        equipment_reqs, room_type, required_components
    )
    
    return processed_boq, avixa_calcs, equipment_reqs, validation_results


# ==================== POST-PROCESSING ====================
def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components):
    """Enhanced validation"""
    validation_results = {'issues': [], 'warnings': []}
    
    # Check for control system
    has_control = any('Touch Controller' in item.get('sub_category', '') or 
                      'Control' in item.get('category', '') 
                      for item in boq_items)
    
    if not has_control:
        validation_results['warnings'].append("⚠️ No control system found - adding touch controller")
        
        control_product = _get_fallback_product(
            'Video Conferencing',
            'Touch Controller / Panel',
            product_df,
            equipment_reqs,
            'Standard'
        )
        
        if control_product:
            control_product.update({
                'quantity': 1,
                'justification': 'Touch controller (Auto-added for system control)',
                'matched': True
            })
            boq_items.append(control_product)
    
    # Validate display mounts
    display_count = sum(1 for item in boq_items if item.get('category') == 'Displays')
    mount_count = sum(1 for item in boq_items if item.get('category') == 'Mounts' and 
                      'Display Mount' in item.get('sub_category', ''))
    
    if display_count > 0 and mount_count == 0:
        validation_results['issues'].append("🚨 CRITICAL: Display present but NO proper mount found")
    elif mount_count > 0:
        # Validate mount is not a finishing ring
        for item in boq_items:
            if item.get('category') == 'Mounts':
                if any(word in item.get('name', '').lower() for word in ['ring', 'bezel', 'trim', 'spacer']):
                    validation_results['issues'].append(f"🚨 INVALID MOUNT: {item.get('name')} is not a proper display mount")
    
    return boq_items, validation_results


# Keep existing helper functions (boq_to_dataframe, calculate_boq_summary, etc.)
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
    
    return df


def calculate_boq_summary(boq_df):
    """Calculate summary statistics"""
    if boq_df.empty:
        return {'total_items': 0, 'total_quantity': 0, 'subtotal': 0, 
                'total_gst': 0, 'grand_total': 0, 'categories': {}}
    
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
