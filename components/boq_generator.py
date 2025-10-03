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
    # Define dummy functions for graceful failure
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}}
    def match_product_in_database(*args): return None


# --- AI Interaction and Parsing ---
def _parse_ai_product_selection(ai_response_text):
    """Parses the JSON object from the AI's response."""
    try:
        # More robust cleaning to handle markdown code blocks
        cleaned = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
        if cleaned:
            return json.loads(cleaned.group(0))
        st.warning("Could not find a valid JSON object in the AI response.")
        return {}
    except Exception as e:
        st.warning(f"Failed to parse AI JSON response: {e}. Response preview: {ai_response_text[:200]}")
        return {}

def _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features):
    """ -- FINAL REVISION WITH ENHANCED PROMPT -- """
    def format_product_list():
        product_text = ""
        for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
            product_text += f"\n## {comp_key.replace('_', ' ').upper()} (Requirement: {comp_spec['justification']})\n"
            
            cat = comp_spec['category']
            sub_cat = comp_spec.get('sub_category')
            
            if sub_cat:
                matching_products = product_df[
                    (product_df['category'] == cat) &
                    (product_df['sub_category'] == sub_cat)
                ].head(15)
            else:
                matching_products = product_df[product_df['category'] == cat].head(15)

            if not matching_products.empty:
                product_text += "    - Options: | Brand | Name | Model No. | Price (USD) |\n"
                for _, prod in matching_products.iterrows():
                    product_text += f"    - | {prod['brand']} | {prod['name']} | {prod['model_number']} | ${prod['price']:.0f} |\n"
            else:
                product_text += f"    - (No specific products found in catalog for {cat} > {sub_cat})\n"
        return product_text

    base_prompt = f"""
    You are a world-class CTS-D Certified AV Systems Designer. Your task is to select the most appropriate products from a provided catalog to create a Bill of Quantities (BOQ) for a '{room_type}'.
    Adhere strictly to the requirements. Your selections must be logical and create a fully functional, compatible system.

    # Design Parameters
    - **Room Type:** {room_type}
    - **Budget Tier:** {budget_tier}
    - **Key Features Requested:** {features if features else 'Standard collaboration features.'}
    - **Core System Design:** Based on the room type, the core design is a '{equipment_reqs.get('video_system', {}).get('type', 'Unknown')}' system.

    # Product Catalog Subset
    You MUST select one product for each of the following roles.

    {format_product_list()}

    # --- ENHANCED RULES & CONSTRAINTS ---
    - **Ecosystem Priority**: For video conferencing, select components from a single brand (e.g., Poly, Yealink, Cisco) to ensure compatibility.
    - **No Redundancy**: If you select a 'Video Bar' or a 'Room Kit', DO NOT select a separate camera or microphone.
    - **Select Core Products**: Ensure your selection is the main product, not just a mounting accessory (e.g., select the microphone, not the mic bracket).
    - **Match Specifications**: For the 'display' requirement, you MUST select a model where the size in its name or description matches the size in the justification (e.g., if justification says '85-inch', pick a display with '85' in the name).
    - **Correct Cable Type**: For the 'network_cables' requirement, you MUST select a product from the 'Network Cable' sub-category (e.g., CAT6, Ethernet), not a control cable like RS-232.

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


def _build_component_blueprint(equipment_reqs, technical_reqs):
    """ -- FINAL REVISION WITH DSP LOGIC -- """
    blueprint = {
        'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 1, 'justification': f"Primary {equipment_reqs['displays'].get('size_inches', 65)}\" display."},
        'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 8, 'justification': 'Wall mount for the display.'},
        'table_connectivity_module': {'category': 'Cables & Connectivity', 'sub_category': 'Wall & Table Plate Module', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input module (e.g., HDMI/USB-C).'},
        'network_cables': {'category': 'Cables & Connectivity', 'sub_category': 'Network Cable', 'quantity': 5, 'priority': 10, 'justification': 'Network patch cables for devices.'},
    }
    video_system_type = equipment_reqs['video_system']['type']
    
    # Add video system and decide if a separate DSP is needed
    needs_separate_dsp = equipment_reqs['audio_system'].get('dsp_required', False)
    if 'voice lift' in technical_reqs.get('audio_requirements', '').lower():
        needs_separate_dsp = True # Voice lift always requires a dedicated DSP

    if video_system_type == 'All-in-one Video Bar':
        blueprint['video_bar_system'] = {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar system.'}
        blueprint['in_room_controller'] = {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel.'}
    elif video_system_type == 'Modular Codec + PTZ Camera':
        blueprint['video_conferencing_kit'] = {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1, 'priority': 2, 'justification': 'Core video conferencing room kit.'}
        # High-end kits often have good DSPs, so only add a separate one if explicitly needed for complex audio
        if 'Boardroom' in equipment_reqs.get('room_type', '') or 'Training' in equipment_reqs.get('room_type', ''):
            pass # Keep DSP requirement for these complex rooms
        else:
            needs_separate_dsp = False # Assume codec DSP is sufficient for standard/large rooms

    # Add audio components
    if needs_separate_dsp:
        blueprint['dsp'] = {'category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for advanced audio control.'}
    
    if equipment_reqs['audio_system'].get('microphone_type'):
        blueprint['microphones'] = {'category': 'Audio', 'sub_category': equipment_reqs['audio_system']['microphone_type'], 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones for room coverage.'}
    if equipment_reqs['audio_system'].get('speaker_type'):
        blueprint['speakers'] = {'category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for audio playback.'}
        blueprint['amplifier'] = {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier for speakers.'}

    # Add infrastructure
    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1, 'priority': 12, 'justification': 'Full-size equipment rack.'}
    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit.'}
        
    return blueprint

def _get_fallback_product(category, sub_category, product_df):
    """Gets a fallback product, filtering by sub-category first."""
    if sub_category:
        matches = product_df[
            (product_df['category'] == category) &
            (product_df['sub_category'] == sub_category)
        ]
        if not matches.empty:
            # Return a mid-range product as a safe bet
            return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    
    # If no sub-category match, try the primary category
    matches = product_df[product_df['category'] == category]
    if not matches.empty:
        return matches.sort_values('price').iloc[len(matches) // 2].to_dict()

    return None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df):
    """Builds the final BOQ list, pulling all rich data from the matched product."""
    boq_items = []
    
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components:
            continue
        
        comp_spec = required_components[comp_key]
        
        matched_product = match_product_in_database(
            product_name=selection.get('name'),
            brand=None, # Brand can be inferred from the matched product
            model_number=selection.get('model_number'),
            product_df=product_df
        )
        
        if matched_product:
            item = {
                'category': matched_product['category'],
                'sub_category': matched_product['sub_category'],
                'name': matched_product['name'],
                'brand': matched_product['brand'],
                'model_number': matched_product['model_number'],
                'quantity': selection.get('qty', comp_spec['quantity']),
                'price': float(matched_product['price']),
                'justification': comp_spec['justification'],
                'specifications': matched_product.get('features', ''),
                'image_url': matched_product.get('image_url', ''),
                'gst_rate': matched_product.get('gst_rate', 18),
                'warranty': matched_product.get('warranty', 'Not Specified'),
                'lead_time_days': matched_product.get('lead_time_days', 14),
                'matched': True
            }
            boq_items.append(item)
        else:
            # Fallback if AI hallucinates or match fails
            fallback = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
            if fallback:
                fallback['quantity'] = comp_spec['quantity']
                fallback['justification'] = f"{comp_spec['justification']} (Fallback Selection)"
                fallback['matched'] = False
                boq_items.append(fallback)
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
        try:
            item['quantity'] = int(float(item.get('quantity', 1)))
            if item['quantity'] == 0: item['quantity'] = 1
        except (ValueError, TypeError):
            item['quantity'] = 1
    return boq_items

def _remove_duplicate_core_components(boq_items):
    final_items = list(boq_items)
    kit_present = any(item.get('sub_category') in ['Video Bar', 'Room Kit / Codec'] for item in final_items)
    if kit_present:
        redundant_sub_categories = ['PTZ Camera', 'Webcam / Personal Camera', 'Touch Controller', 'Table Microphone']
        final_items = [item for item in final_items if item.get('sub_category') not in redundant_sub_categories or "Manually added" in item.get('justification', '')]
    return _remove_exact_duplicates(final_items)

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type):
    # This is a placeholder for more complex rules
    return {'issues': [], 'warnings': []}

def _sanity_check_prices(boq_items):
    for item in boq_items:
        price, category, sub_category = item.get('price', 0), item.get('category', ''), item.get('sub_category', '')
        warning_msg = " ⚠️ **PRICE WARNING**: Price seems unusually high. Please verify."
        if (sub_category == 'Amplifier' and price > 2500) or (category == 'Cables & Connectivity' and price > 500):
            if warning_msg not in item['justification']: item['justification'] += warning_msg
    return boq_items

def _validate_ai_selections(boq_items, required_components):
    """ NEW: Validates AI choices against original requirements. """
    for item in boq_items:
        # Find the original requirement for this item
        original_req = next((rc for rc in required_components.values() if rc['category'] == item['category'] and rc.get('sub_category') == item['sub_category']), None)
        if not original_req: continue

        # Check for display size mismatch
        if item['category'] == 'Displays':
            req_size_match = re.search(r'(\d+)"', original_req['justification'])
            if req_size_match:
                req_size = req_size_match.group(1)
                item_name = item.get('name', '').lower()
                # Allow some tolerance for nearby sizes
                if req_size not in item_name and not any(size in item_name for size in [str(int(req_size)-2), str(int(req_size)+2)]):
                    item['justification'] += f" ⚠️ **SPEC MISMATCH**: Required a {req_size}\" display."
    return boq_items

def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components):
    """ -- FINAL REVISION -- Consolidates all post-processing and validation. """
    processed_boq = _correct_quantities(boq_items)
    processed_boq = _remove_exact_duplicates(processed_boq)
    processed_boq = _remove_duplicate_core_components(processed_boq)
    processed_boq = _sanity_check_prices(processed_boq)
    # Add the new validation step
    processed_boq = _validate_ai_selections(processed_boq, required_components)
    
    validation_results = validate_avixa_compliance(processed_boq, avixa_calcs, equipment_reqs, room_type)
    return processed_boq, validation_results

def create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs):
    """Creates a BOQ using fallback logic if the AI fails."""
    st.warning("AI failed. Building a BOQ with standard fallback components.")
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
        if product:
            product['quantity'] = comp_spec['quantity']
            product['justification'] = f"{comp_spec['justification']} (Fallback Selection)"
            product['matched'] = False
            fallback_items.append(product)
    return fallback_items, required_components

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """ -- FINAL REVISION -- The core generation function. """
    length = (room_area**0.5) * 1.2
    width = room_area / length
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    # Pass technical_reqs to blueprint for smarter DSP logic
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs)
    
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
            
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df)
        
        # Return required_components so it can be used in the new validation step
        return boq_items, avixa_calcs, equipment_reqs, required_components
        
    except Exception as e:
        st.error(f"AI generation failed spectacularly: {str(e)}. Creating a smart fallback BOQ.")
        fallback_items, required_components = create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs)
        return fallback_items, avixa_calcs, equipment_reqs, required_components
