# components/boq_generator.py

import streamlit as st
import pandas as pd
import re
import json

try:
    from components.gemini_handler import generate_with_retry
    from components.av_designer import calculate_avixa_recommendations, determine_equipment_requirements
    from components.data_handler import match_product_in_database
except ImportError as e:
    st.error(f"BOQ Generator failed to import a component: {e}")
    # Dummy functions for graceful failure
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}, 'control_system': {}}
    def match_product_in_database(*args): return None


def _parse_ai_product_selection(ai_response_text):
    """Parses the JSON object from the AI's response."""
    try:
        cleaned = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
        if cleaned:
            return json.loads(cleaned.group(0))
        st.warning("Could not find a valid JSON object in the AI response.")
        return {}
    except Exception as e:
        st.warning(f"Failed to parse AI JSON response: {e}. Response preview: {ai_response_text[:200]}")
        return {}


def _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features):
    """Builds a highly contextual prompt with filtered product lists based on ecosystem."""
    ecosystem = equipment_reqs.get('ecosystem', 'Poly') # Get the chosen ecosystem

    def format_product_list():
        product_text = ""
        core_vc_keys = ['video_bar', 'video_codec', 'ptz_camera', 'in_room_controller']
        
        for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
            product_text += f"\n## {comp_key.replace('_', ' ').upper()} (Requirement: {comp_spec['justification']})\n"
            
            cat, sub_cat = comp_spec['category'], comp_spec.get('sub_category')
            
            # --- CHANGE START: Ecosystem-aware filtering ---
            filtered_df = product_df
            if sub_cat:
                filtered_df = filtered_df[
                    (filtered_df['category'] == cat) &
                    (filtered_df['sub_category'] == sub_cat)
                ]
            else:
                 filtered_df = filtered_df[filtered_df['category'] == cat]

            # If it's a core VC component, prioritize the chosen ecosystem brand
            if comp_key in core_vc_keys:
                eco_matches = filtered_df[filtered_df['brand'].str.lower() == ecosystem.lower()]
                if not eco_matches.empty:
                    matching_products = eco_matches.head(10)
                else:
                    matching_products = filtered_df.head(10) # Fallback to any brand if no eco matches
            else:
                matching_products = filtered_df.head(15)
            # --- CHANGE END ---

            if not matching_products.empty:
                product_text += "   - Options: | Brand | Name | Model No. | Price (USD) |\n"
                for _, prod in matching_products.iterrows():
                    product_text += f"   - | {prod['brand']} | {prod['name']} | {prod['model_number']} | ${prod['price']:.0f} |\n"
            else:
                product_text += f"   - (No specific products found for {cat} > {sub_cat})\n"
        return product_text

    base_prompt = f"""
    You are a CTS-D Certified AV Systems Designer. Your task is to create a BOQ for a '{room_type}'.
    The core video conferencing ecosystem for this design MUST be '{ecosystem}'. Prioritize '{ecosystem}' products for the codec, camera, and controller to ensure compatibility.

    # Design Parameters & Product Catalog
    {format_product_list()}

    # INSTRUCTIONS
    1. Select exactly one product for each mandatory component.
    2. Your entire output MUST be a single, valid JSON object.
    3. For each component, provide the EXACT 'name' and 'model_number' from the catalog list.
    """

    json_format_instruction = "\n# REQUIRED JSON OUTPUT FORMAT\n{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format_instruction += f'  "{comp_key}": {{"name": "...", "model_number": "...", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format_instruction += "}\n"

    return base_prompt + json_format_instruction


def _build_component_blueprint(equipment_reqs):
    """Dynamically builds the list of required components with sub-categories."""
    blueprint = {
        'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 1, 'justification': f"Primary {equipment_reqs['displays'].get('size_inches', 65)}\" display."},
        'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 8, 'justification': 'Wall mount for the display.'},
        'in_room_controller': {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel for meeting control.'},
        'table_connectivity': {'category': 'Cables & Connectivity', 'sub_category': 'Wall & Table Plate', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input for wired presentation.'},
    }
    if equipment_reqs['video_system']['type'] == 'All-in-one Video Bar':
        blueprint['video_bar'] = {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar.'}
    elif equipment_reqs['video_system']['type'] == 'Modular Codec + PTZ Camera':
        blueprint['video_codec'] = {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1, 'priority': 2, 'justification': 'Core video codec.'}
        blueprint['ptz_camera'] = {'category': 'Video Conferencing', 'sub_category': 'PTZ Camera', 'quantity': equipment_reqs['video_system'].get('camera_count', 1), 'priority': 2.1, 'justification': 'PTZ camera.'}
    if equipment_reqs['audio_system'].get('dsp_required', False):
        blueprint['dsp'] = {'category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor.'}
        blueprint['microphones'] = {'category': 'Audio', 'sub_category': 'Ceiling Microphone', 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones for room coverage.'}
        blueprint['speakers'] = {'category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for audio playback.'}
        blueprint['amplifier'] = {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier for speakers.'}
    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1, 'priority': 12, 'justification': 'Equipment rack.'}
        blueprint['pdu'] = {'category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit.'}
    return blueprint

# --- Post-Processing and Validation ---

def _get_best_fit_product(category, sub_category, product_df, brand_preference=None):
    """Finds a suitable product, preferring a specific brand if provided."""
    matches = product_df[(product_df['category'] == category) & (product_df['sub_category'] == sub_category)]
    if brand_preference:
        brand_matches = matches[matches['brand'].str.lower() == brand_preference.lower()]
        if not brand_matches.empty:
            return brand_matches.sort_values('price').iloc[len(brand_matches) // 2].to_dict()
    if not matches.empty:
        return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    return None

def _correct_ecosystem_mismatches(boq_items, product_df):
    """Ensures core VC components are from the same brand."""
    core_vc_items = [item for item in boq_items if item.get('sub_category') in ['Room Kit / Codec', 'PTZ Camera', 'Touch Controller']]
    if not core_vc_items: return boq_items

    codec_brand = next((item['brand'] for item in core_vc_items if item['sub_category'] == 'Room Kit / Codec'), None)
    if not codec_brand: return boq_items

    for item in boq_items:
        if item.get('sub_category') in ['PTZ Camera', 'Touch Controller'] and item['brand'] != codec_brand:
            st.warning(f"CORRECTION: Swapped incompatible '{item['brand']}' {item['sub_category']} for a '{codec_brand}' device.")
            replacement = _get_best_fit_product(item['category'], item['sub_category'], product_df, brand_preference=codec_brand)
            if replacement:
                item.update(replacement)
                item['justification'] += " (Corrected for compatibility)"
    return boq_items

def _correct_accessory_for_hardware(boq_items, product_df):
    """Swaps items that are accessories/licenses for actual hardware."""
    for item in boq_items:
        name_lower = item['name'].lower()
        price = item['price']
        
        # Rule: If it's a DSP/Mic and costs less than $200, it's probably wrong.
        if item['sub_category'] in ['DSP / Processor', 'Ceiling Microphone'] and price < 200:
            st.warning(f"CORRECTION: Detected accessory/license '{item['name']}'. Swapping for main hardware.")
            replacement = _get_best_fit_product(item['category'], item['sub_category'], product_df)
            if replacement:
                item.update(replacement)
                item['justification'] += " (Corrected from accessory to hardware)"

        # Rule: If the name contains "service", "license", "support", it's not hardware.
        if any(keyword in name_lower for keyword in ['service', 'license', 'support', ' year', ' yr', 'software']):
            st.warning(f"CORRECTION: Detected service/license '{item['name']}'. Swapping for main hardware.")
            replacement = _get_best_fit_product(item['category'], item['sub_category'], product_df)
            if replacement:
                item.update(replacement)
                item['justification'] += " (Corrected from service to hardware)"
    return boq_items

def _correct_disproportionate_components(boq_items, product_df):
    """Fixes illogical component choices, like a switcher for an amp."""
    for item in boq_items:
        # Rule: If an item in the 'Amplifier' role is actually a 'Matrix Switcher', replace it.
        if item.get('justification', '').startswith('Amplifier') and item.get('sub_category') == 'Matrix Switcher':
            st.warning(f"CORRECTION: Detected Matrix Switcher used as Amplifier. Swapping for a dedicated Amplifier.")
            replacement = _get_best_fit_product('Audio', 'Amplifier', product_df)
            if replacement:
                item.update(replacement)
                item['justification'] = "Amplifier for speakers. (Corrected from Matrix Switcher)"
    return boq_items

def post_process_boq(boq_items, product_df):
    """Runs a series of validation and correction routines on the generated BOQ."""
    st.write("---")
    st.info("🤖 Running AI-Assist Post-Processing & Validation...")
    
    # Run correction functions
    corrected_items = _correct_ecosystem_mismatches(boq_items, product_df)
    corrected_items = _correct_accessory_for_hardware(corrected_items, product_df)
    corrected_items = _correct_disproportionate_components(corrected_items, product_df)

    # Run cleanup
    unique_items = []
    seen_models = set()
    for item in corrected_items:
        model = item.get('model_number')
        if model not in seen_models:
            unique_items.append(item)
            seen_models.add(model)
            
    # Final quantity check
    for item in unique_items:
        try: item['quantity'] = int(item.get('quantity', 1)) or 1
        except: item['quantity'] = 1
        
    st.success("✅ Validation and corrections complete.")
    st.write("---")
    return unique_items

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """The core function to generate and then validate the BOQ."""
    length = (room_area**0.5) * 1.2
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    required_components = _build_component_blueprint(equipment_reqs)
    
    prompt = _get_prompt_for_room_type(
        room_type, equipment_reqs, required_components,
        product_df, budget_tier, features
    )
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not hasattr(response, 'text') or not response.text:
            raise Exception("AI returned an empty or invalid response.")
        
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse a valid JSON object from the AI response.")
        
        # Build initial BOQ from AI selection
        boq_items = []
        for comp_key, selection in ai_selection.items():
            if comp_key in required_components:
                comp_spec = required_components[comp_key]
                matched_product = match_product_in_database(selection.get('name'), None, selection.get('model_number'), product_df)
                if matched_product:
                    # Update with all details from the catalog
                    matched_product.update({
                        'quantity': selection.get('qty', comp_spec['quantity']),
                        'justification': comp_spec['justification'],
                        'matched': True
                    })
                    boq_items.append(matched_product)
                else: # AI hallucinated a product
                    fallback = _get_best_fit_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
                    if fallback:
                        fallback.update({
                            'quantity': comp_spec['quantity'],
                            'justification': f"{comp_spec['justification']} (AI choice invalid, using fallback)",
                            'matched': False
                        })
                        boq_items.append(fallback)

        return boq_items, avixa_calcs, equipment_reqs
        
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}. Creating a smart fallback BOQ.")
        # Fallback logic here...
        return [], avixa_calcs, equipment_reqs
