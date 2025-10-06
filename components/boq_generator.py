# components/boq_generator.py
# FINAL, FULLY LOGICAL VERSION

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


# ==================== IMPROVED FALLBACK LOGIC ====================
def _get_fallback_product(category, sub_category, product_df, equipment_reqs=None, budget_tier='Standard'):
    """
    Intelligent fallback product selection with filtering and validation
    """
    # Initial filtering
    if sub_category:
        matches = product_df[
            (product_df['category'] == category) &
            (product_df['sub_category'] == sub_category)
        ].copy()
    else:
        matches = product_df[product_df['category'] == category].copy()

    if matches.empty:
        return None

    # === CRITICAL FILTERING: Exclude service contracts from hardware ===
    if category not in ['Software & Services']:
        matches = matches[~matches['name'].str.contains(
            r'\b(ess|con-snt|con-ecdn|support|warranty|service contract|smartcare)\b',
            case=False, na=False, regex=True
        )]

    if matches.empty:
        return None

    # === CATEGORY-SPECIFIC INTELLIGENT SELECTION ===

    # Displays: Match size requirement
    if category == 'Displays' and equipment_reqs and 'displays' in equipment_reqs:
        req_size = equipment_reqs['displays'].get('size_inches', 65)
        size_range = range(req_size - 3, req_size + 4)
        size_pattern = '|'.join([f'{s}"' for s in size_range])

        size_matches = matches[matches['name'].str.contains(size_pattern, na=False, regex=True)]
        if not size_matches.empty:
            matches = size_matches

    # Intelligent Mount Selection
    if category == 'Mounts' and equipment_reqs and 'displays' in equipment_reqs:
        req_size = equipment_reqs['displays'].get('size_inches', 65)
        
        matches = matches[~matches['name'].str.contains(
            r'\b(video bar|soundbar|Studio X30|Studio X50|Rally Bar|Meetup|for Poly)\b',
            case=False, na=False, regex=True
        )]
        
        if req_size >= 65:
            large_mounts = matches[matches['name'].str.contains(
                r'(heavy-duty|large display|65"|75"|85"|86"|98"|universal flat)',
                case=False, na=False, regex=True
            )]
            if not large_mounts.empty:
                matches = large_mounts

    # Video Conferencing: Prefer quality brands based on ecosystem
    if category == 'Video Conferencing':
        preferred_ecosystem = equipment_reqs.get('preferred_ecosystem') if equipment_reqs else None
        base_priority = ['Poly', 'Cisco', 'Logitech', 'Yealink', 'Neat', 'Crestron']
        
        brand_priority = base_priority
        if preferred_ecosystem and preferred_ecosystem.capitalize() in base_priority:
            brand_priority = [preferred_ecosystem.capitalize()] + [b for b in base_priority if b.lower() != preferred_ecosystem.lower()]

        for brand in brand_priority:
            brand_matches = matches[matches['brand'].str.contains(brand, case=False, na=False)]
            if not brand_matches.empty:
                matches = brand_matches
                break

    # Audio DSP: Exclude mixers, amplifiers, and invalid products
    if sub_category in ['DSP / Processor', 'DSP / Audio Processor / Mixer']:
        matches = matches[~matches['name'].str.contains(
            r'\b(amplifier|amp-|summing|quad active|wall mount power)\b',
            case=False, na=False, regex=True
        )]
        dsp_brands = ['Biamp', 'QSC', 'Shure', 'Extron', 'Crestron', 'BSS']
        for brand in dsp_brands:
            brand_matches = matches[matches['brand'].str.contains(brand, case=False, na=False)]
            if not brand_matches.empty:
                matches = brand_matches
                break

    # Touch Controllers: Exclude room kits and service contracts
    if sub_category in ['Touch Controller', 'Touch Controller / Panel']:
        matches = matches[~matches['name'].str.contains(
            r'\b(room kit|ess|codec|service)\b',
            case=False, na=False, regex=True
        )]
        matches = matches[matches['name'].str.contains(
            r'(touch|panel|controller|tap|pad)',
            case=False, na=False, regex=True
        )]

    # PDU: Exclude wall mount power supplies
    if sub_category == 'Power (PDU/UPS)':
        matches = matches[~matches['name'].str.contains(
            r'\b(wall mount|power pack|adapter|injector)\b',
            case=False, na=False, regex=True
        )]
        pdu_matches = matches[matches['name'].str.contains(
            r'(pdu|power distribution|rack.*power|ups)',
            case=False, na=False, regex=True
        )]
        if not pdu_matches.empty:
            matches = pdu_matches

    # --- MODIFICATION START: Intelligent Power Amplifier Selection ---
    # Amplifiers: Exclude utility/line amps and PRIORITIZE power amps
    if sub_category == 'Amplifier':
        # 1. Exclude devices that are not power amplifiers
        matches = matches[~matches['name'].str.contains(
            r'\b(processor|dsp|summing|mixer|line driver|distribution|extender)\b',
            case=False, na=False, regex=True
        )]
        
        # 2. Prioritize true power amplifiers by looking for relevant keywords
        power_amp_matches = matches[matches['name'].str.contains(
            r'(power amp|70v|100v|\d-channel|\dW)',
            case=False, na=False, regex=True
        )]
        
        if not power_amp_matches.empty:
            matches = power_amp_matches
    # --- MODIFICATION END ---


    # Table Connectivity: Exclude wall plates
    if sub_category == 'Wall & Table Plate Module':
        table_matches = matches[matches['name'].str.contains(
            r'(table|tbus|floor|cubby|connectivity box|retractor)',
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

    start_idx = int(len(sorted_matches) * 0.25)
    end_idx = int(len(sorted_matches) * 0.75)
    selection_pool = sorted_matches.iloc[start_idx:end_idx] if end_idx > start_idx else sorted_matches

    return selection_pool.iloc[len(selection_pool) // 2].to_dict()


# ==================== IMPROVED COMPONENT BLUEPRINT ====================
def _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier='Standard'):
    """
    Build component requirements with detailed specifications
    """
    blueprint = {}

    # Displays
    if 'displays' in equipment_reqs:
        display_reqs = equipment_reqs.get('displays', {})
        qty = display_reqs.get('quantity', 1)
        size = display_reqs.get('size_inches', 65)

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
            'sub_category': 'Display Mount / Cart',
            'quantity': qty,
            'priority': 8,
            'justification': f'Heavy-duty wall mount for {size}" display',
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
        if control_reqs.get('type') == 'Touch Controller':
            blueprint['touch_control_panel'] = {
                'category': 'Video Conferencing',
                'sub_category': 'Touch Controller / Panel',
                'quantity': 1,
                'priority': 3,
                'justification': 'Touch control panel for intuitive meeting control'
            }

    # Audio System
    if 'audio_system' in equipment_reqs:
        audio_reqs = equipment_reqs.get('audio_system', {})
        audio_type = audio_reqs.get('type', '')
        needs_dsp = audio_reqs.get('dsp_required', False)
        has_integrated_audio = 'integrated' in audio_type.lower() or 'video bar' in audio_type.lower()

        is_large_room_audio = any(x in audio_type.lower() for x in ['ceiling audio', 'pro audio', 'voice reinforcement'])
        if is_large_room_audio:
            has_integrated_audio = False
            needs_dsp = True
        
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

        elif needs_dsp and not has_integrated_audio:
            blueprint['audio_dsp'] = {
                'category': 'Audio',
                'sub_category': 'DSP / Audio Processor / Mixer',
                'quantity': 1,
                'priority': 4,
                'justification': 'Digital signal processor for advanced audio control and mixing'
            }

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

        speaker_type = audio_reqs.get('speaker_type', '')
        if speaker_type and not has_integrated_audio:
            speaker_count = audio_reqs.get('speaker_count', 2)
            if 'ceiling' in speaker_type.lower():
                blueprint['ceiling_speakers'] = {
                    'category': 'Audio',
                    'sub_category': 'Ceiling Loudspeaker',
                    'quantity': speaker_count,
                    'priority': 6,
                    'justification': f'{speaker_count}x ceiling speakers for even audio distribution'
                }
            elif 'wall' in speaker_type.lower():
                blueprint['wall_speakers'] = {
                    'category': 'Audio',
                    'sub_category': 'Wall-mounted Loudspeaker',
                    'quantity': speaker_count,
                    'priority': 6,
                    'justification': f'{speaker_count}x wall-mounted speakers'
                }

            if speaker_count > 0:
                blueprint['power_amplifier'] = {
                    'category': 'Audio',
                    'sub_category': 'Amplifier',
                    'quantity': 1,
                    'priority': 7,
                    'justification': f'Power amplifier for {speaker_count}x speakers'
                }

    # Connectivity & Infrastructure
    if equipment_reqs.get('content_sharing') or 'wireless presentation' in technical_reqs.get('features', '').lower():
        blueprint['table_connectivity'] = {
            'category': 'Cables & Connectivity',
            'sub_category': 'AV Cable',
            'quantity': 1,
            'priority': 9,
            'justification': 'Table connectivity solution with HDMI/USB-C inputs'
        }

    blueprint['network_cables'] = {
        'category': 'Cables & Connectivity',
        'sub_category': 'AV Cable',
        'quantity': 5,
        'priority': 10,
        'justification': 'Cat6 network patch cables for equipment connections'
    }

    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['equipment_rack'] = {
            'category': 'Infrastructure',
            'sub_category': 'AV Rack',
            'quantity': 1,
            'priority': 12,
            'justification': 'Professional equipment rack for AV components'
        }

    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['power_distribution'] = {
            'category': 'Infrastructure',
            'sub_category': 'Power (PDU/UPS)',
            'quantity': 1,
            'priority': 11,
            'justification': 'Rackmount power distribution unit for equipment power'
        }

    return blueprint


# (The rest of the file remains unchanged)
# ==================== AI PROMPT ====================
def _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features):
    def format_product_list():
        product_text = ""
        for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
            product_text += f"\n## {comp_key.replace('_', ' ').upper()}\n"
            product_text += f"**Requirement:** {comp_spec['justification']}\n"
            cat = comp_spec['category']
            sub_cat = comp_spec.get('sub_category')
            if sub_cat:
                filtered_df = product_df[(product_df['category'] == cat) & (product_df['sub_category'] == sub_cat)].copy()
            else:
                filtered_df = product_df[product_df['category'] == cat].copy()
            if cat not in ['Software & Services']:
                filtered_df = filtered_df[~filtered_df['name'].str.contains(r'\b(ess|con-snt|con-ecdn|support|warranty|service contract|smartcare|jumpstart)\b', case=False, na=False, regex=True)]
            if cat == 'Displays':
                req_size = equipment_reqs.get('displays', {}).get('size_inches')
                if req_size:
                    size_range = range(req_size - 3, req_size + 4)
                    size_pattern = '|'.join([f'{s}"' for s in size_range])
                    size_filtered = filtered_df[filtered_df['name'].str.contains(size_pattern, na=False, regex=True)]
                    if not size_filtered.empty:
                        filtered_df = size_filtered
                        product_text += f"     **CRITICAL:** Must be approximately {req_size}\" display (±3 inches)\n"
            if sub_cat in ['DSP / Processor', 'DSP / Audio Processor / Mixer']:
                filtered_df = filtered_df[~filtered_df['name'].str.contains(r'\b(amplifier|amp-|summing|quad active)\b', case=False, na=False, regex=True)]
                product_text += "     **CRITICAL:** Must be actual DSP/processor, NOT amplifier or mixer\n"
            if sub_cat and 'Touch Controller' in sub_cat:
                filtered_df = filtered_df[~filtered_df['name'].str.contains(r'\b(room kit|codec|ess)\b', case=False, na=False, regex=True)]
                product_text += "     **CRITICAL:** Must be touch panel/controller, NOT room kit or codec\n"
            if sub_cat == 'Power (PDU/UPS)':
                filtered_df = filtered_df[~filtered_df['name'].str.contains(r'\b(wall mount|power pack|adapter)\b', case=False, na=False, regex=True)]
                product_text += "     **CRITICAL:** Must be rackmount PDU, NOT wall power supply\n"
            if not filtered_df.empty:
                product_text += "     **Available Products:**\n"
                product_text += "     | Brand | Model | Product Name | Price (USD) |\n"
                product_text += "     |-------|-------|--------------|-------------|\n"
                for _, prod in filtered_df.head(25).iterrows():
                    safe_name = str(prod['name'])[:60].replace('|', '-')
                    product_text += f"     | {prod['brand']} | {prod['model_number']} | {safe_name} | ${prod['price']:.0f} |\n"
            else:
                product_text += "     ⚠️ **WARNING:** No matching products found after filtering\n"
        return product_text
    base_prompt = f"""You are a CTS-D certified AV systems designer selecting products for a professional '{room_type}' installation.
# CRITICAL SELECTION RULES (MUST FOLLOW)
1. Select ONLY products that EXACTLY match the component's sub-category.
2. NEVER select service contracts (ESS, warranty, support agreements) for hardware components.
3. For displays: Match size requirement within ±3 inches.
4. For DSPs: Select actual digital signal processors, NEVER amplifiers or mixers.
5. For Touch Controllers: Select touch panels/controllers, NEVER room kits or codecs.
6. For PDUs: Select rackmount power distribution, NEVER wall-mount power supplies.
7. Verify each selection makes sense for the component role described.
# Room Configuration
- **Room Type:** {room_type}
- **Budget Level:** {budget_tier}
- **Special Requirements:** {features if features else 'Standard professional AV configuration'}
# Required Components and Available Products
{format_product_list()}
# OUTPUT REQUIREMENTS
Return ONLY valid JSON with exact product names and models from the lists above.
Double-check each selection matches the component requirement.
JSON Format:
{{"""
    json_format = '\n'
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format += f'  "{comp_key}": {{"name": "EXACT product name from table", "model_number": "EXACT model from table", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format += "}\n"
    return base_prompt + json_format

def _parse_ai_product_selection(ai_response_text):
    try:
        cleaned = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
        if cleaned: return json.loads(cleaned.group(0))
        st.warning("Could not find valid JSON in AI response.")
        return {}
    except Exception as e:
        st.warning(f"Failed to parse AI response: {e}")
        return {}

def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs):
    boq_items = []
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        comp_spec = required_components[comp_key]
        matched_product = match_product_in_database(product_name=selection.get('name'), brand=None, model_number=selection.get('model_number'), product_df=product_df)
        if matched_product:
            item = {'category': matched_product.get('category', comp_spec['category']), 'sub_category': matched_product.get('sub_category', comp_spec.get('sub_category', '')), 'name': matched_product.get('name', ''), 'brand': matched_product.get('brand', ''), 'model_number': matched_product.get('model_number', ''), 'quantity': selection.get('qty', comp_spec['quantity']), 'price': float(matched_product.get('price', 0)), 'justification': comp_spec['justification'], 'specifications': matched_product.get('specifications', ''), 'image_url': matched_product.get('image_url', ''), 'gst_rate': matched_product.get('gst_rate', 18), 'warranty': matched_product.get('warranty', 'Not Specified'), 'lead_time_days': matched_product.get('lead_time_days', 14), 'matched': True}
            boq_items.append(item)
        else:
            fallback = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df, equipment_reqs, 'Standard')
            if fallback:
                fallback.update({'quantity': comp_spec['quantity'], 'justification': f"{comp_spec['justification']} (Auto-selected fallback)", 'matched': False})
                boq_items.append(fallback)
    return boq_items

def _validate_boq_selections(boq_items, equipment_reqs):
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
    seen = set()
    unique_items = []
    for item in boq_items:
        identifier = item.get('model_number') or item.get('name')
        if identifier not in seen:
            unique_items.append(item)
            seen.add(identifier)
    return unique_items

def _correct_quantities(boq_items):
    for item in boq_items:
        try: item['quantity'] = int(float(item.get('quantity', 1)))
        except (ValueError, TypeError): item['quantity'] = 1
        if item['quantity'] == 0: item['quantity'] = 1
    return boq_items

def validate_boq_completeness(boq_items, required_components):
    missing_components = []
    present_sub_categories = {item.get('sub_category') for item in boq_items}
    for comp_key, comp_spec in required_components.items():
        if comp_spec.get('sub_category') not in present_sub_categories:
            missing_components.append({'component': comp_key, 'category': comp_spec['category'], 'justification': comp_spec['justification']})
    return missing_components

def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components):
    processed_boq = _correct_quantities(boq_items)
    processed_boq = _remove_exact_duplicates(processed_boq)
    processed_boq = _validate_boq_selections(processed_boq, equipment_reqs)
    validation_results = {'issues': [], 'warnings': []}
    missing_components = validate_boq_completeness(processed_boq, required_components)
    if missing_components:
        for missing in missing_components:
            issue_text = f"Missing Component: The BOQ is missing a required '{missing['component'].replace('_', ' ')}' ({missing['category']}). Justification: {missing['justification']}"
            validation_results['issues'].append(issue_text)
    return processed_boq, validation_results

def create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs, budget_tier='Standard'):
    st.warning("AI selection unavailable. Building BOQ with intelligent fallback logic.")
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df, equipment_reqs, budget_tier)
        if product:
            product.update({'quantity': comp_spec['quantity'], 'justification': f"{comp_spec['justification']} (Intelligent auto-selection)", 'matched': False})
            fallback_items.append(product)
    return fallback_items, required_components

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    length = (room_area ** 0.5) * 1.2
    width = room_area / length
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier)
    prompt = _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features)
    try:
        response = generate_with_retry(model, prompt)
        if not response or not hasattr(response, 'text') or not response.text: raise Exception("AI returned empty response")
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection: raise Exception("Failed to parse AI product selection")
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs)
        if not boq_items: raise Exception("No BOQ items generated from AI selection")
    except Exception as e:
        st.warning(f"AI generation failed ({str(e)}). Using intelligent fallback system.")
        boq_items, required_components = create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs, budget_tier)
    processed_boq, validation_results = post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components)
    return processed_boq, avixa_calcs, equipment_reqs, validation_results

def boq_to_dataframe(boq_items):
    if not boq_items: return pd.DataFrame()
    df = pd.DataFrame(boq_items)
    required_columns = ['category', 'sub_category', 'name', 'brand', 'model_number', 'quantity', 'price', 'justification', 'specifications', 'gst_rate', 'warranty', 'lead_time_days']
    for col in required_columns:
        if col not in df.columns: df[col] = ''
    df['line_total'] = df['quantity'] * df['price']
    df['gst_amount'] = df['line_total'] * (df['gst_rate'] / 100)
    df['total_with_gst'] = df['line_total'] + df['gst_amount']
    column_order = ['category', 'sub_category', 'brand', 'model_number', 'name', 'quantity', 'price', 'line_total', 'gst_rate', 'gst_amount', 'total_with_gst', 'justification', 'specifications', 'warranty', 'lead_time_days']
    column_order = [col for col in column_order if col in df.columns]
    df = df[column_order]
    return df

def calculate_boq_summary(boq_df):
    if boq_df.empty: return {'total_items': 0, 'total_quantity': 0, 'subtotal': 0, 'total_gst': 0, 'grand_total': 0, 'categories': {}}
    summary = {'total_items': len(boq_df), 'total_quantity': int(boq_df['quantity'].sum()), 'subtotal': float(boq_df['line_total'].sum()), 'total_gst': float(boq_df['gst_amount'].sum()), 'grand_total': float(boq_df['total_with_gst'].sum()), 'categories': {}}
    if 'category' in boq_df.columns:
        summary['categories'] = boq_df.groupby('category').agg({'quantity': 'sum', 'line_total': 'sum', 'total_with_gst': 'sum'}).to_dict('index')
    return summary

def export_boq_to_excel(boq_df, filename="boq_export.xlsx"):
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
                except: pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    output.seek(0)
    return output
