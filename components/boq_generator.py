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
    from components.data_handler import match_product_in_database # Use the enhanced matcher
except ImportError as e:
    st.error(f"BOQ Generator failed to import a component: {e}")
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}, 'control_system': {}}
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
    """
    -- RE-ENGINEERED PROMPT FACTORY --
    Builds a highly contextual prompt with filtered product lists based on sub-category.
    """
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
    You MUST select one product for each of the following roles. Choose the most suitable option from the provided lists. Prioritize items that fit the budget tier.

    {format_product_list()}

    # --- MODIFICATION START: Added new rules to the AI prompt ---
    # RULES & CONSTRAINTS
    - **Prioritize Ecosystems**: For video conferencing, select components from a single brand (e.g., Poly, Yealink, Crestron) to ensure compatibility. Do not mix brands for the codec, camera, and touch panel.
    - **Avoid Redundancy**: If you select a 'Video Bar' or a 'Room Kit', DO NOT select a separate PTZ camera, webcam, or microphone, as the kit already includes them.
    - **Select Complete Products**: For components like microphones or wall plates, ensure your selection is the main product, not just a mounting accessory.
    # --- MODIFICATION END ---

    # INSTRUCTIONS
    1.  Review all the requirements and the available product options for each component.
    2.  Select exactly one product for each mandatory component key (e.g., 'display', 'video_bar_system').
    3.  Your entire output MUST be a single, valid JSON object and nothing else. Do not include any text, greetings, or explanations before or after the JSON block.
    4.  The JSON keys must match the component keys provided (e.g., "display", "display_mount").
    5.  For each component, provide the EXACT 'name' and 'model_number' from the catalog list.
    """

    json_format_instruction = "\n# REQUIRED JSON OUTPUT FORMAT\n{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format_instruction += f'  "{comp_key}": {{"name": "EXACT product name from list", "model_number": "EXACT model number from list", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format_instruction += "}\n"

    return base_prompt + json_format_instruction


# --- MODIFICATION START: Replaced _build_component_blueprint with "kit-aware" logic ---
def _build_component_blueprint(equipment_reqs):
    """
    Dynamically builds the list of required components, now with intelligence
    to handle all-in-one kits and prevent redundancy.
    """
    # Base components required in almost any room
    blueprint = {
        'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 1, 'justification': f"Primary {equipment_reqs['displays'].get('size_inches', 65)}\" display."},
        'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 8, 'justification': 'Wall mount for the display.'},
        'table_connectivity': {'category': 'Cables & Connectivity', 'sub_category': 'Wall & Table Plate', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input for wired presentation.'},
        'network_cables': {'category': 'Cables & Connectivity', 'sub_category': 'AV Cable', 'quantity': 5, 'priority': 10, 'justification': 'Network patch cables for devices.'},
    }

    video_system_type = equipment_reqs['video_system']['type']

    # If the system is an all-in-one solution, request the kit and DO NOT request individual parts.
    if video_system_type == 'All-in-one Video Bar':
        blueprint['video_bar_system'] = {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar (camera, mics, speakers).'}
        blueprint['in_room_controller'] = {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel for meeting control.'}

    # If the system is a modular kit, request the kit, which often includes camera and codec.
    elif video_system_type == 'Modular Codec + PTZ Camera':
        blueprint['video_conferencing_kit'] = {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1, 'priority': 2, 'justification': 'Core video conferencing room kit (codec, camera, controller).'}
        # Since the Room Kit is requested, we no longer need to ask for a separate camera or codec.

    # Logic for audio system remains, as it's often separate from the video kit.
    if equipment_reqs['audio_system'].get('dsp_required', False):
        blueprint['dsp'] = {'category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for audio.'}
        blueprint['microphones'] = {'category': 'Audio', 'sub_category': 'Ceiling Microphone', 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones for room coverage.'}
        blueprint['speakers'] = {'category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for audio playback.'}
        blueprint['amplifier'] = {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier for speakers.'}

    # Infrastructure logic
    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1, 'priority': 12, 'justification': 'Equipment rack.'}
    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit.'}
        
    return blueprint
# --- MODIFICATION END ---


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

# --- MODIFICATION START: Replaced _remove_duplicate_core_components with a more aggressive version ---
def _remove_duplicate_core_components(boq_items):
    """
    More aggressive logic to remove redundant items if a 'kit' is present.
    """
    final_items = list(boq_items)

    # Identify if a primary 'kit' system exists
    kit_present = any(item.get('sub_category') in ['Video Bar', 'Room Kit / Codec'] for item in final_items)

    if kit_present:
        # If a kit exists, aggressively remove individual components that would be redundant
        items_to_remove = []
        redundant_sub_categories = ['PTZ Camera', 'Webcam / Personal Camera', 'Touch Controller', 'Table Microphone']
        for item in final_items:
            if item.get('sub_category') in redundant_sub_categories:
                # Keep it only if it was manually added by the user
                if "Manually added" not in item.get('justification', ''):
                    items_to_remove.append(item)

        # Remove the identified redundant items
        final_items = [item for item in final_items if item not in items_to_remove]
    
    return _remove_exact_duplicates(final_items)
# --- MODIFICATION END ---

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type):
    issues, warnings = [], []
    # This logic can be expanded, but for now, it's a placeholder
    return {'issues': issues, 'warnings': warnings}

# --- MODIFICATION START: Added new price sanity check function ---
def _sanity_check_prices(boq_items):
    """
    Adds a warning to the justification field if a product's price seems
    like an outlier for its category.
    """
    for item in boq_items:
        price = item.get('price', 0)
        category = item.get('category', '')
        sub_category = item.get('sub_category', '')
        warning_msg = " ⚠️ **PRICE WARNING**: Price seems unusually high for this category. Please verify."

        # Flag any 'Amplifier' that costs more than $2,500
        if sub_category == 'Amplifier' and price > 2500 and warning_msg not in item['justification']:
            item['justification'] += warning_msg
        
        # Flag any 'Cable' or 'Connector' that costs more than $500
        if category == 'Cables & Connectivity' and price > 500 and warning_msg not in item['justification']:
            item['justification'] += warning_msg
            
    return boq_items
# --- MODIFICATION END ---


# --- CHANGE START: Added a new master function to consolidate post-processing ---
def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type):
    """
    Consolidates all post-processing, cleanup, and validation steps for a generated BOQ.
    The product_df is passed for potential future enhancements but is not used in the current version.
    """
    # Step 1: Correct quantities to ensure they are valid integers.
    processed_boq = _correct_quantities(boq_items)
    
    # Step 2: Remove any items that are exact duplicates based on model number.
    processed_boq = _remove_exact_duplicates(processed_boq)
    
    # Step 3: A more advanced rule to remove redundant core components, keeping the best option.
    processed_boq = _remove_duplicate_core_components(processed_boq)
    
    # --- MODIFICATION START: Added price sanity check to the pipeline ---
    # Step 4: Run a sanity check on prices to flag potential data errors.
    processed_boq = _sanity_check_prices(processed_boq)
    # --- MODIFICATION END ---

    # Step 5: Validate the final, cleaned BOQ against AVIXA standards.
    validation_results = validate_avixa_compliance(processed_boq, avixa_calcs, equipment_reqs, room_type)
    
    return processed_boq, validation_results
# --- CHANGE END ---

def create_smart_fallback_boq(product_df, equipment_reqs):
    """Creates a BOQ using fallback logic if the AI fails."""
    st.warning("AI failed. Building a BOQ with standard fallback components.")
    required_components = _build_component_blueprint(equipment_reqs)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
        if product:
            product['quantity'] = comp_spec['quantity']
            product['justification'] = f"{comp_spec['justification']} (Fallback Selection)"
            product['matched'] = False
            fallback_items.append(product)
    return fallback_items

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """The re-architected core function to generate the BOQ."""
    length = (room_area**0.5) * 1.2
    width = room_area / length
    
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
            
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df)
        # The raw boq_items are returned; processing is now handled by post_process_boq
        return boq_items, avixa_calcs, equipment_reqs
        
    except Exception as e:
        st.error(f"AI generation failed spectacularly: {str(e)}. Creating a smart fallback BOQ.")
        fallback_items = create_smart_fallback_boq(product_df, equipment_reqs)
        return fallback_items, avixa_calcs, equipment_reqs
