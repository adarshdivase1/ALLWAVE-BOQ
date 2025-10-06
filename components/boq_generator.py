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
    # Define dummy functions for fallback
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {}
    def match_product_in_database(*args): return None

# --- AI Interaction and Parsing ---
def _parse_ai_product_selection(ai_response_text):
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
    """ -- REWRITTEN FOR PROFILE-DRIVEN LOGIC & ECOSYSTEM AWARENESS -- """
    preferred_ecosystem = equipment_reqs.get('preferred_ecosystem', '').lower()

    def format_product_list():
        product_text = ""
        # Sort by category then by component key for consistent ordering
        sorted_components = sorted(required_components.items(), key=lambda x: (x[1].get('category', ''), x[0]))

        for comp_key, comp_spec in sorted_components:
            justification = comp_spec.get('justification', f"Core component for a {room_type}.")
            product_text += f"\n## {comp_key.replace('_', ' ').upper()} (Requirement: {justification})\n"
            cat = comp_spec.get('category')
            sub_cat = comp_spec.get('sub_category')

            if not cat or not sub_cat:
                product_text += "     - (Misconfigured component: Missing category or sub_category)\n"
                continue
                
            filtered_df = product_df[(product_df['category'] == cat) & (product_df['sub_category'] == sub_cat)].copy()

            # Ecosystem filtering for core VC components
            if preferred_ecosystem and cat == 'Video Conferencing':
                eco_filtered_df = filtered_df[filtered_df['brand'].str.lower() == preferred_ecosystem]
                if not eco_filtered_df.empty:
                    filtered_df = eco_filtered_df
                    product_text += f"     - INFO: Prioritizing '{preferred_ecosystem.capitalize()}' brand for system cohesion.\n"

            # Display size filtering
            if cat == 'Displays' and 'display' in comp_key:
                req_size = equipment_reqs.get('avixa_calcs', {}).get('recommended_display_size_inches')
                if req_size:
                    size_tolerance = 5 # Looser tolerance for more options
                    size_filtered_df = filtered_df[
                        filtered_df['name'].str.contains(fr'\b({req_size}|{req_size-2}|{req_size+2}|{req_size-5}|{req_size+5})\b', na=False)
                    ]
                    if not size_filtered_df.empty:
                        filtered_df = size_filtered_df
                        product_text += f"     - INFO: Room requires a ~{req_size}\" display, filtering options.\n"

            if not filtered_df.empty:
                product_text += "     - Options: | Brand | Name | Model No. | Price (USD) |\n"
                for _, prod in filtered_df.head(10).iterrows(): # Limit options to keep prompt concise
                    product_text += f"     - | {prod['brand']} | {prod['name']} | {prod['model_number']} | ${prod['price']:.0f} |\n"
            else:
                product_text += f"     - (No products found in catalog for {cat} > {sub_cat})\n"
        return product_text

    base_prompt = f"""
    You are a world-class CTS-D Certified AV Systems Designer. Your task is to select the most appropriate products from a provided catalog to create a Bill of Quantities (BOQ) for a '{room_type}'.
    Adhere strictly to the requirements and the filtered options provided for each component.

    # Design Parameters
    - **Room Type:** {room_type}
    - **Budget Tier:** {budget_tier}
    - **Key Features Requested:** {features if features else 'Standard features for this room type.'}

    # Product Catalog Subset (Filtered by Role)
    You MUST select one product for each of the following roles from the filtered options. Choose the best fit based on the design parameters.

    {format_product_list()}

    # INSTRUCTIONS
    Your entire output MUST be a single, valid JSON object and nothing else.
    The JSON keys must match the component keys from the list above (e.g., "display", "codec", "dsp").
    For each key, provide the EXACT "name" and "model_number" from the options provided.
    """
    json_format_instruction = "\n# REQUIRED JSON OUTPUT FORMAT\n{\n"
    for i, (comp_key, comp_spec) in enumerate(sorted_components):
        comma = "," if i < len(sorted_components) - 1 else ""
        json_format_instruction += f'  "{comp_key}": {{"name": "EXACT product name from list", "model_number": "EXACT model number from list", "qty": {comp_spec.get("quantity", 1)}}}{comma}\n'
    json_format_instruction += "}\n"
    return base_prompt + json_format_instruction

def _build_component_blueprint(equipment_reqs):
    """
    Builds the component list directly from the detailed room profile.
    """
    blueprint = {}
    if 'components' in equipment_reqs:
        for key, details in equipment_reqs['components'].items():
            blueprint[key] = {
                'category': details.get('category'),
                'sub_category': details.get('sub_category'),
                'quantity': details.get('quantity', 1),
                'justification': details.get('justification', f"Standard component for a {equipment_reqs.get('room_type')}.")
            }
    return blueprint

# --- BOQ Construction & Post-Processing ---
def _get_fallback_product(category, sub_category, product_df):
    if sub_category:
        matches = product_df[(product_df['category'] == category) & (product_df['sub_category'] == sub_category)]
        if not matches.empty:
            return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    matches = product_df[product_df['category'] == category]
    if not matches.empty:
        return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    return None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df):
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
        
        item_data = {
            'category': comp_spec.get('category'),
            'sub_category': comp_spec.get('sub_category'),
            'quantity': selection.get('qty', comp_spec.get('quantity', 1)),
            'justification': comp_spec.get('justification', ''),
            'matched': bool(matched_product)
        }
        
        if matched_product:
            item_data.update(matched_product) # Add all details from the DB
        else: # Handle AI hallucination or mismatch
            item_data.update({
                'name': selection.get('name', 'N/A'),
                'brand': 'Unknown',
                'model_number': selection.get('model_number', 'N/A'),
                'price': 0,
                'justification': f"{item_data['justification']} (⚠️ VERIFY MODEL - Not found in catalog)",
            })

        boq_items.append(item_data)
    return boq_items

def _ensure_system_cohesion(boq_items):
    """Final sanity check for logical system dependencies."""
    # Example check: If there's a modular codec, ensure a camera and controller exist.
    sub_categories_present = {item.get('sub_category') for item in boq_items}
    
    if 'Room Kit / Codec' in sub_categories_present:
        if 'PTZ Camera' not in sub_categories_present:
            st.warning("Cohesion Check: Modular codec is present, but no PTZ Camera was added.")
        if 'Touch Controller' not in sub_categories_present:
            st.warning("Cohesion Check: Modular codec is present, but no Touch Controller was added.")
            
    # Example check: If there are passive loudspeakers, ensure an amplifier exists.
    if 'Loudspeaker' in sub_categories_present:
        if 'Amplifier' not in sub_categories_present:
            st.warning("Cohesion Check: Passive loudspeakers are present, but no Power Amplifier was added.")
            
    return boq_items

def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components):
    # Standard cleaning
    for item in boq_items: # Ensure quantity is an integer
        item['quantity'] = int(item.get('quantity', 1))

    # Run final cohesion check
    processed_boq = _ensure_system_cohesion(boq_items)
    
    # Validation results can be expanded with more rules
    validation_results = {'issues': [], 'warnings': []}
    
    return processed_boq, validation_results

# --- Main Entry Point ---
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    length, width = (room_area**0.5) * 1.2, room_area / ((room_area**0.5) * 1.2)
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    
    # This now gets the rich, detailed profile
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    # This builds the blueprint from the rich profile
    required_components = _build_component_blueprint(equipment_reqs)
    
    if not required_components:
        st.error(f"No components defined for room type '{room_type}' in room_profiles.py. Cannot generate BOQ.")
        return [], {}, {}, {}

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
        st.error(f"AI generation failed: {str(e)}. Creating a smart fallback BOQ.")
        # Fallback logic remains valuable
        fallback_items = []
        for key, spec in required_components.items():
            product = _get_fallback_product(spec['category'], spec.get('sub_category'), product_df)
            if product:
                product.update({'quantity': spec.get('quantity', 1), 'justification': f"{spec.get('justification')} (Fallback Selection)", 'matched': False})
                fallback_items.append(product)
        return fallback_items, avixa_calcs, equipment_reqs, required_components
