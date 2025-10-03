# components/boq_generator.py

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


# --- AI Interaction and Parsing ---
def _parse_ai_product_selection(ai_response_text):
    try:
        cleaned = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
        if cleaned: return json.loads(cleaned.group(0))
        st.warning("Could not find a valid JSON object in the AI response.")
        return {}
    except Exception as e:
        st.warning(f"Failed to parse AI JSON response: {e}. Response preview: {ai_response_text[:200]}")
        return {}

# --- MODIFICATION START: The entire prompt and filtering function is replaced ---
def _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features):
    """ -- FINAL REVISION WITH INTELLIGENT, CONTEXT-AWARE FILTERING -- """

    # Helper function to parse brand preferences from the features text
    def parse_brand_preferences(features_text):
        preferences = {}
        # Simple parsing for "brand for category" patterns
        # Example: "Use a Samsung display", "The VC system must be Poly"
        patterns = {
            'Displays': r'(samsung|lg|nec|sony|benq|viewsonic)\s*(display|monitor)',
            'Video Conferencing': r'(poly|cisco|yealink|logitech|neat)\s*(vc|video|conferencing)',
            'Audio': r'(shure|biamp|qsc|sennheiser)\s*(audio|mic|dsp)'
        }
        for category, pattern in patterns.items():
            match = re.search(pattern, features_text, re.IGNORECASE)
            if match:
                preferences[category] = match.group(1).lower()
        return preferences

    brand_preferences = parse_brand_preferences(features)

    # Helper function to format the product list shown to the AI
    def format_product_list():
        product_text = ""
        for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
            product_text += f"\n## {comp_key.replace('_', ' ').upper()} (Requirement: {comp_spec['justification']})\n"
            
            cat = comp_spec['category']
            sub_cat = comp_spec.get('sub_category')
            
            # Start with the base filtered dataframe
            if sub_cat:
                filtered_df = product_df[(product_df['category'] == cat) & (product_df['sub_category'] == sub_cat)].copy()
            else:
                filtered_df = product_df[product_df['category'] == cat].copy()

            # --- 1. APPLY BRAND PREFERENCE FILTER ---
            preferred_brand = brand_preferences.get(cat)
            if preferred_brand:
                brand_filtered_df = filtered_df[filtered_df['brand'].str.lower() == preferred_brand]
                if not brand_filtered_df.empty:
                    filtered_df = brand_filtered_df
                    product_text += f"    - INFO: User requested brand '{preferred_brand.capitalize()}', filtering options.\n"

            # --- 2. APPLY DISPLAY SIZE FILTER ---
            if cat == 'Displays':
                req_size = equipment_reqs.get('displays', {}).get('size_inches')
                if req_size:
                    # Filter by looking for the size number in the product name/model, allowing for a small tolerance
                    size_tolerance = 2
                    size_filtered_df = filtered_df[
                        filtered_df['name'].str.contains(fr'\b({req_size}|{req_size-1}|{req_size+1}|{req_size-2}|{req_size+2})\b', na=False)
                    ]
                    if not size_filtered_df.empty:
                        filtered_df = size_filtered_df
                        product_text += f"    - INFO: Room requires a ~{req_size}\" display, filtering options.\n"

            # Format the final filtered list for the prompt
            if not filtered_df.empty:
                product_text += "    - Options: | Brand | Name | Model No. | Price (USD) |\n"
                for _, prod in filtered_df.head(15).iterrows():
                    product_text += f"    - | {prod['brand']} | {prod['name']} | {prod['model_number']} | ${prod['price']:.0f} |\n"
            else:
                product_text += f"    - (No products found in catalog matching the specific filters for {cat} > {sub_cat})\n"
        return product_text

    # The rest of the prompt structure remains the same but now uses the intelligently filtered list
    base_prompt = f"""
    You are a world-class CTS-D Certified AV Systems Designer. Your task is to select the most appropriate products from a provided catalog to create a Bill of Quantities (BOQ) for a '{room_type}'.
    Adhere strictly to the requirements and the filtered options provided for each role.

    # Design Parameters
    - **Room Type:** {room_type}
    - **Budget Tier:** {budget_tier}
    - **Key Features Requested:** {features if features else 'Standard collaboration features.'}

    # Product Catalog Subset (Intelligently Filtered)
    You MUST select one product for each of the following roles from the filtered options.

    {format_product_list()}

    # INSTRUCTIONS
    Your entire output MUST be a single, valid JSON object and nothing else.
    The JSON keys must match the component keys provided (e.g., "display", "display_mount").
    For each component, provide the EXACT 'name' and 'model_number' from the catalog list.
    """
    json_format_instruction = "\n# REQUIRED JSON OUTPUT FORMAT\n{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format_instruction += f'  "{comp_key}": {{"name": "EXACT product name from list", "model_number": "EXACT model number from list", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format_instruction += "}\n"
    return base_prompt + json_format_instruction
# --- MODIFICATION END ---


# The rest of the file remains the same as the last version you received.
# Functions like _build_component_blueprint, post_process_boq, generate_boq_from_ai, etc.,
# are still valid and should be kept. The only change is how the prompt and its product
# list are generated. The following is the rest of the file for completeness.


def _build_component_blueprint(equipment_reqs, technical_reqs):
    """ -- FINAL REVISION WITH DSP LOGIC -- """
    blueprint = {
        'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 1, 'justification': f"Primary {equipment_reqs['displays'].get('size_inches', 65)}\" display."},
        'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 8, 'justification': 'Wall mount for the display.'},
        'table_connectivity_module': {'category': 'Cables & Connectivity', 'sub_category': 'Wall & Table Plate Module', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input module (e.g., HDMI/USB-C).'},
        'network_cables': {'category': 'Cables & Connectivity', 'sub_category': 'Network Cable', 'quantity': 5, 'priority': 10, 'justification': 'Network patch cables for devices.'},
    }
    video_system_type = equipment_reqs['video_system']['type']
    needs_separate_dsp = equipment_reqs['audio_system'].get('dsp_required', False)
    if 'voice lift' in technical_reqs.get('audio_requirements', '').lower():
        needs_separate_dsp = True

    if video_system_type == 'All-in-one Video Bar':
        blueprint['video_bar_system'] = {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar system.'}
        blueprint['in_room_controller'] = {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel.'}
    elif video_system_type == 'Modular Codec + PTZ Camera':
        blueprint['video_conferencing_kit'] = {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1, 'priority': 2, 'justification': 'Core video conferencing room kit.'}
        if 'Boardroom' not in equipment_reqs.get('room_type', '') and 'Training' not in equipment_reqs.get('room_type', ''):
            needs_separate_dsp = False

    if needs_separate_dsp:
        blueprint['dsp'] = {'category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for advanced audio control.'}
    if equipment_reqs['audio_system'].get('microphone_type'):
        blueprint['microphones'] = {'category': 'Audio', 'sub_category': 'Ceiling Microphone', 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones for room coverage.'}
    if equipment_reqs['audio_system'].get('speaker_type'):
        blueprint['speakers'] = {'category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for audio playback.'}
        blueprint['amplifier'] = {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier for speakers.'}

    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1, 'priority': 12, 'justification': 'Full-size equipment rack.'}
    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit.'}
    return blueprint

def _get_fallback_product(category, sub_category, product_df):
    if sub_category:
        matches = product_df[(product_df['category'] == category) & (product_df['sub_category'] == sub_category)]
        if not matches.empty: return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    matches = product_df[product_df['category'] == category]
    if not matches.empty: return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    return None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df):
    boq_items = []
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        comp_spec = required_components[comp_key]
        matched_product = match_product_in_database(product_name=selection.get('name'), brand=None, model_number=selection.get('model_number'), product_df=product_df)
        if matched_product:
            item = {k: matched_product.get(k, v) for k, v in {'category':'', 'sub_category':'', 'name':'', 'brand':'', 'model_number':'', 'quantity':comp_spec['quantity'], 'price':0, 'justification':comp_spec['justification'], 'specifications':'', 'image_url':'', 'gst_rate':18, 'warranty':'Not Specified', 'lead_time_days':14, 'matched':True}.items()}
            item.update({
                'quantity': selection.get('qty', comp_spec['quantity']),
                'price': float(matched_product.get('price', 0))
            })
            boq_items.append(item)
        else:
            fallback = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
            if fallback:
                fallback.update({'quantity': comp_spec['quantity'], 'justification': f"{comp_spec['justification']} (Fallback Selection)", 'matched': False})
                boq_items.append(fallback)
    return boq_items

def _remove_exact_duplicates(boq_items):
    seen, unique_items = set(), []
    for item in boq_items:
        identifier = item.get('model_number') or item.get('name')
        if identifier not in seen:
            unique_items.append(item); seen.add(identifier)
    return unique_items

def _correct_quantities(boq_items):
    for item in boq_items:
        try: item['quantity'] = int(float(item.get('quantity', 1)))
        except (ValueError, TypeError): item['quantity'] = 1
        if item['quantity'] == 0: item['quantity'] = 1
    return boq_items

def _remove_duplicate_core_components(boq_items):
    final_items = list(boq_items)
    kit_present = any(item.get('sub_category') in ['Video Bar', 'Room Kit / Codec'] for item in final_items)
    if kit_present:
        redundant_sub_categories = ['PTZ Camera', 'Webcam / Personal Camera', 'Touch Controller', 'Table Microphone']
        final_items = [item for item in final_items if item.get('sub_category') not in redundant_sub_categories or "Manually added" in item.get('justification', '')]
    return _remove_exact_duplicates(final_items)

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type):
    return {'issues': [], 'warnings': []}

def _sanity_check_prices(boq_items):
    for item in boq_items:
        price, category, sub_category = item.get('price', 0), item.get('category', ''), item.get('sub_category', '')
        warning_msg = " ⚠️ **PRICE WARNING**: Price seems unusually high. Please verify."
        if (sub_category == 'Amplifier' and price > 2500) or (category == 'Cables & Connectivity' and price > 500):
            if warning_msg not in item['justification']: item['justification'] += warning_msg
    return boq_items

def _validate_ai_selections(boq_items, required_components):
    for item in boq_items:
        original_req = next((rc for rc in required_components.values() if rc['category'] == item['category'] and rc.get('sub_category') == item['sub_category']), None)
        if not original_req: continue
        if item['category'] == 'Displays':
            req_size_match = re.search(r'(\d+)"', original_req['justification'])
            if req_size_match:
                req_size = req_size_match.group(1)
                item_name = item.get('name', '').lower()
                if req_size not in item_name and not any(size in item_name for size in [str(int(req_size)-2), str(int(req_size)+2)]):
                    item['justification'] += f" ⚠️ **SPEC MISMATCH**: Required a {req_size}\" display."
    return boq_items

def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components):
    processed_boq = _correct_quantities(boq_items)
    processed_boq = _remove_exact_duplicates(processed_boq)
    processed_boq = _remove_duplicate_core_components(processed_boq)
    processed_boq = _sanity_check_prices(processed_boq)
    processed_boq = _validate_ai_selections(processed_boq, required_components)
    validation_results = validate_avixa_compliance(processed_boq, avixa_calcs, equipment_reqs, room_type)
    return processed_boq, validation_results

def create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs):
    st.warning("AI failed. Building a BOQ with standard fallback components.")
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
        if product:
            product.update({'quantity': comp_spec['quantity'], 'justification': f"{comp_spec['justification']} (Fallback Selection)", 'matched': False})
            fallback_items.append(product)
    return fallback_items, required_components

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    length, width = (room_area**0.5) * 1.2, room_area / ((room_area**0.5) * 1.2)
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs)
    prompt = _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features)
    try:
        response = generate_with_retry(model, prompt)
        if not response or not hasattr(response, 'text') or not response.text:
            raise Exception("AI returned an empty or invalid response.")
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse a valid JSON object from the AI response.")
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df)
        return boq_items, avixa_calcs, equipment_reqs, required_components
    except Exception as e:
        st.error(f"AI generation failed spectacularly: {str(e)}. Creating a smart fallback BOQ.")
        fallback_items, required_components = create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs)
        return fallback_items, avixa_calcs, equipment_reqs, required_components
