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
    # Define dummy functions to prevent app from crashing if imports fail
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}}
    def match_product_in_database(*args): return None

# --- AI Interaction and Parsing ---

def _parse_ai_product_selection(ai_response_text: str) -> dict:
    """Safely parses a JSON object from the AI's text response."""
    try:
        # Use regex to find the JSON block, making it robust against surrounding text
        cleaned_json_str = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
        if cleaned_json_str:
            return json.loads(cleaned_json_str.group(0))
        st.warning("Could not find a valid JSON object in the AI response.")
        return {}
    except json.JSONDecodeError as e:
        st.warning(f"Failed to parse AI JSON response: {e}. Response preview: {ai_response_text[:200]}")
        return {}

def _get_prompt_for_room_type(room_type: str, equipment_reqs: dict, required_components: dict, product_df: pd.DataFrame, budget_tier: str, features: str) -> str:
    """Generates a detailed, context-aware prompt for the AI, now with enhanced budget guidance."""
    
    # Helper to parse brand preferences from user features text
    def parse_brand_preferences(features_text: str) -> dict:
        preferences = {}
        # Patterns to detect preferred brands for major categories
        patterns = {
            'Displays': r'(samsung|lg|nec|sony|benq|viewsonic)\s*(display|monitor)',
            'Video Conferencing': r'(poly|cisco|yealink|logitech|neat)\s*(vc|video|conferencing)',
            'Audio': r'(shure|biamp|qsc|sennheiser|bose)\s*(audio|mic|dsp|speaker)'
        }
        for category, pattern in patterns.items():
            match = re.search(pattern, features_text, re.IGNORECASE)
            if match:
                preferences[category] = match.group(1).lower()
        return preferences

    brand_preferences = parse_brand_preferences(features)

    def format_product_list() -> str:
        """Formats the filtered product catalog for the AI to select from."""
        product_text = ""
        # Sort components by priority to present a logical flow in the prompt
        for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
            product_text += f"\n## For Component: {comp_key.replace('_', ' ').upper()} (Requirement: {comp_spec['justification']})\n"
            cat = comp_spec['category']
            sub_cat = comp_spec.get('sub_category')

            # Filter dataframe by category and sub-category
            if sub_cat:
                filtered_df = product_df[(product_df['category'] == cat) & (product_df['sub_category'] == sub_cat)].copy()
            else:
                filtered_df = product_df[product_df['category'] == cat].copy()

            # Apply brand preference filter if specified by the user
            preferred_brand = brand_preferences.get(cat)
            if preferred_brand:
                brand_filtered_df = filtered_df[filtered_df['brand'].str.lower() == preferred_brand]
                if not brand_filtered_df.empty:
                    filtered_df = brand_filtered_df
                    product_text += f"    -> INFO: User prefers brand '{preferred_brand.capitalize()}', options filtered.\n"

            # Apply display size filter based on AVIXA calculations
            if cat == 'Displays':
                req_size = equipment_reqs.get('displays', {}).get('size_inches')
                if req_size:
                    # Allow a tolerance of +/- 2 inches for flexibility
                    size_tolerance = 2
                    size_range = range(req_size - size_tolerance, req_size + size_tolerance + 1)
                    size_pattern = r'\b(' + '|'.join(map(str, size_range)) + r')["\']?\b'
                    size_filtered_df = filtered_df[filtered_df['name'].str.contains(size_pattern, na=False)]
                    if not size_filtered_df.empty:
                        filtered_df = size_filtered_df
                        product_text += f"    -> INFO: Room requires a ~{req_size}\" display, options filtered.\n"

            # Format the top 15 matching products for the AI
            if not filtered_df.empty:
                product_text += "    | Brand | Name | Model No. | Price (USD) |\n"
                # Sort by price to help the AI make budget-conscious decisions
                for _, prod in filtered_df.sort_values(by='price').head(15).iterrows():
                    product_text += f"    | {prod['brand']} | {prod['name']} | {prod['model_number']} | ${prod['price']:.0f} |\n"
            else:
                product_text += f"    - (No products found in catalog matching filters for {cat} > {sub_cat})\n"
        return product_text

    # The main prompt given to the AI
    base_prompt = f"""
    You are a world-class CTS-D Certified AV Systems Designer. Your task is to select the most appropriate products from a provided catalog to create a Bill of Quantities (BOQ) for a '{room_type}'.
    Adhere strictly to the requirements and the filtered options provided for each component role.

    # Design Parameters
    - **Room Type:** {room_type}
    - **Budget Tier:** {budget_tier.upper()} (Select lower-priced options for Economy, mid-range for Standard, and higher-end for Premium/Enterprise).
    - **Key Features Requested:** {features if features else 'Standard collaboration features.'}

    # Product Catalog Subset (Filtered by Role)
    You MUST select exactly one product for each of the following roles from the filtered options.

    {format_product_list()}

    # INSTRUCTIONS
    Your entire output MUST be a single, valid JSON object and nothing else.
    The JSON keys must match the component keys provided below (e.g., "display", "video_bar_system").
    For each key, provide the EXACT product name and model number from the list.
    """
    
    # Dynamically generate the required JSON output format structure for the AI
    json_format_instruction = "\n# REQUIRED JSON OUTPUT FORMAT\n{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format_instruction += f'  "{comp_key}": {{"name": "EXACT product name from list", "model_number": "EXACT model number from list", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format_instruction += "}\n"
    
    return base_prompt + json_format_instruction


def _build_component_blueprint(equipment_reqs: dict, technical_reqs: dict) -> dict:
    """Builds the list of required components based on the room's equipment profile."""
    blueprint = {}
    
    # Use a priority system to ensure logical ordering
    # Displays (Priority 1)
    if 'displays' in equipment_reqs:
        display_reqs = equipment_reqs.get('displays', {})
        blueprint['display'] = {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': display_reqs.get('quantity', 1), 'priority': 1, 'justification': f"Primary {display_reqs.get('size_inches', 65)}\" display for content."}
        blueprint['display_mount'] = {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': display_reqs.get('quantity', 1), 'priority': 8, 'justification': 'Wall mount for the display.'}

    # Video System (Priority 2)
    if 'video_system' in equipment_reqs:
        video_reqs = equipment_reqs.get('video_system', {})
        if video_reqs.get('type') == 'All-in-one Video Bar':
            blueprint['video_bar_system'] = {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar for camera, mics, and speakers.'}
        elif video_reqs.get('type') == 'Modular Codec + PTZ Camera':
            blueprint['video_conferencing_kit'] = {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1, 'priority': 2, 'justification': 'Core video conferencing codec and camera kit.'}

    # Control System (Priority 3)
    if 'control_system' in equipment_reqs:
        if equipment_reqs['control_system'].get('type') == 'Touch Controller':
            blueprint['in_room_controller'] = {'category': 'Video Conferencing', 'sub_category': 'Touch Controller / Panel', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel for meeting control.'}

    # Audio System (Priorities 4-7)
    if 'audio_system' in equipment_reqs:
        audio_reqs = equipment_reqs.get('audio_system', {})
        # Special logic for Voice Reinforcement systems
        if audio_reqs.get('type') == 'Voice Reinforcement System' or 'voice lift' in technical_reqs.get('features', '').lower():
            blueprint['dsp'] = {'category': 'Audio', 'sub_category': 'DSP / Audio Processor / Mixer', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for voice reinforcement.'}
            blueprint['presenter_microphone'] = {'category': 'Audio', 'sub_category': 'Wireless Microphone System', 'quantity': 1, 'priority': 4.5, 'justification': 'Wireless mic for presenter.'}
        
        if audio_reqs.get('dsp_required', False) and 'dsp' not in blueprint:
            blueprint['dsp'] = {'category': 'Audio', 'sub_category': 'DSP / Audio Processor / Mixer', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for advanced audio control.'}

        if audio_reqs.get('microphone_type') == 'Ceiling Microphone':
            blueprint['audience_microphones'] = {'category': 'Audio', 'sub_category': 'Ceiling Microphone', 'quantity': audio_reqs.get('microphone_count', 2), 'priority': 5, 'justification': 'Ceiling mics for audience participation.'}
        
        if audio_reqs.get('speaker_type') == 'Ceiling Loudspeaker':
            blueprint['speakers'] = {'category': 'Audio', 'sub_category': 'Loudspeaker / Speaker', 'quantity': audio_reqs.get('speaker_count', 2), 'priority': 6, 'justification': 'Ceiling speakers for even audio coverage.'}
            blueprint['amplifier'] = {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier to power the ceiling speakers.'}

    # Connectivity & Infrastructure (Priorities 9+)
    if 'content_sharing' in equipment_reqs:
        blueprint['table_connectivity_module'] = {'category': 'Infrastructure', 'sub_category': 'Architectural / In-Wall', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input module (HDMI/USB-C).'}
    
    blueprint['cabling_kit'] = {'category': 'Cables & Connectivity', 'sub_category': 'AV Cable', 'quantity': 5, 'priority': 10, 'justification': 'Essential AV and Network patch cables.'}
    
    if 'housing' in equipment_reqs and equipment_reqs['housing'].get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1, 'priority': 12, 'justification': 'Equipment rack for housing components.'}
    
    if 'power_management' in equipment_reqs and equipment_reqs['power_management'].get('type') == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'sub_category': 'Power Management', 'quantity': 1, 'priority': 11, 'justification': 'Rackmount power distribution unit.'}
        
    return blueprint

# --- BOQ Construction and Post-Processing ---

def _get_fallback_product(category: str, sub_category: str, product_df: pd.DataFrame) -> dict | None:
    """Selects a median-priced product as a fallback if the AI fails."""
    if sub_category:
        matches = product_df[(product_df['category'] == category) & (product_df['sub_category'] == sub_category)]
        if not matches.empty:
            # Return the median-priced item to avoid the cheapest/lowest quality or most expensive
            return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    # If no sub-category match, try matching by primary category only
    matches = product_df[product_df['category'] == category]
    if not matches.empty:
        return matches.sort_values('price').iloc[len(matches) // 2].to_dict()
    return None

def _build_boq_from_ai_selection(ai_selection: dict, required_components: dict, product_df: pd.DataFrame) -> list:
    """Constructs the BOQ list from the AI's JSON output, with fallbacks for failed matches."""
    boq_items = []
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components:
            continue
        
        comp_spec = required_components[comp_key]
        # Match the product from the AI selection in our database
        matched_product = match_product_in_database(
            product_name=selection.get('name'), 
            brand=None,  # Brand is not needed as model number is primary key
            model_number=selection.get('model_number'), 
            product_df=product_df
        )
        
        if matched_product:
            item = {
                'category': matched_product.get('category'),
                'sub_category': matched_product.get('sub_category'),
                'name': matched_product.get('name'),
                'brand': matched_product.get('brand'),
                'model_number': matched_product.get('model_number'),
                'quantity': selection.get('qty', comp_spec['quantity']),
                'price': float(matched_product.get('price', 0)),
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
            # If AI hallucinates a product, use our fallback logic
            fallback = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
            if fallback:
                fallback.update({
                    'quantity': comp_spec['quantity'],
                    'justification': f"{comp_spec['justification']} (Fallback Selection - AI choice not found)",
                    'matched': False
                })
                boq_items.append(fallback)
    return boq_items

def _remove_redundant_components(boq_items: list) -> list:
    """Removes items that are included in a primary kit (e.g., a camera if a Video Bar is present)."""
    final_items = list(boq_items)
    # Check if an all-in-one system is present
    kit_present = any(item.get('sub_category') in ['Video Bar', 'Room Kit / Codec', 'Collaboration Display'] for item in final_items)
    
    if kit_present:
        # These components are often included in kits
        redundant_sub_categories = ['PTZ Camera', 'Webcam / Personal Camera', 'Touch Controller / Panel', 'Table/Boundary Microphone']
        # Remove redundant items unless they were manually added by the user
        final_items = [
            item for item in final_items 
            if item.get('sub_category') not in redundant_sub_categories 
            or "Manually added" in item.get('justification', '')
        ]
    return final_items

def _validate_boq_logic(boq_items: list, required_components: dict) -> list:
    """Performs final validation checks on the generated BOQ."""
    for item in boq_items:
        # Price Sanity Check
        price, category, sub_category = item.get('price', 0), item.get('category', ''), item.get('sub_category', '')
        warning_msg = " ⚠️ **PRICE WARNING**: Price seems unusually high. Please verify."
        if (sub_category == 'Amplifier' and price > 3000) or \
           (category == 'Cables & Connectivity' and price > 750) or \
           (sub_category == 'Display Mount / Cart' and price > 1500):
            if warning_msg not in item['justification']:
                item['justification'] += warning_msg
        
        # Specification Mismatch Check (e.g., Display Size)
        original_req = next((rc for rc in required_components.values() if rc['category'] == item['category'] and rc.get('sub_category') == item['sub_category']), None)
        if not original_req:
            continue
            
        if item['category'] == 'Displays':
            req_size_match = re.search(r'(\d+)"', original_req['justification'])
            if req_size_match:
                req_size = int(req_size_match.group(1))
                item_name = item.get('name', '').lower()
                # Check if the required size (or a close size) is mentioned in the product name
                if not any(str(s) in item_name for s in range(req_size - 2, req_size + 3)):
                    item['justification'] += f" ⚠️ **SPEC MISMATCH**: Required a {req_size}\" display."
    return boq_items

def post_process_boq(boq_items: list, required_components: dict) -> tuple[list, dict]:
    """Applies a series of cleaning and validation steps to the raw BOQ list."""
    # Correct quantities to be integers
    for item in boq_items:
        try:
            item['quantity'] = int(float(item.get('quantity', 1)))
            if item['quantity'] == 0: item['quantity'] = 1
        except (ValueError, TypeError):
            item['quantity'] = 1
    
    # Remove items that are logically redundant
    processed_boq = _remove_redundant_components(boq_items)
    
    # Run final validation checks for price and specs
    processed_boq = _validate_boq_logic(processed_boq, required_components)

    # In a real-world scenario, a more complex AVIXA compliance check would go here
    validation_results = {'issues': [], 'warnings': []}
    
    return processed_boq, validation_results

def create_smart_fallback_boq(product_df: pd.DataFrame, equipment_reqs: dict, technical_reqs: dict) -> tuple[list, dict]:
    """Creates a BOQ with standard, median-priced components when the AI fails."""
    st.warning("AI generation failed or returned an invalid response. Building a BOQ with standard fallback components.")
    required_components = _build_component_blueprint(equipment_reqs, technical_reqs)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], comp_spec.get('sub_category'), product_df)
        if product:
            product.update({
                'quantity': comp_spec['quantity'],
                'justification': f"{comp_spec['justification']} (Standard Fallback Selection)",
                'matched': False
            })
            fallback_items.append(product)
    return fallback_items, required_components

# --- Main Generation Function ---

def generate_boq_from_ai(model, product_df: pd.DataFrame, guidelines: str, room_type: str, budget_tier: str, features: str, technical_reqs: dict, room_area: float) -> tuple:
    """Orchestrates the entire BOQ generation process from design to AI selection."""
    try:
        # 1. Calculate AVIXA-based design parameters
        length, width = (room_area**0.5) * 1.2, room_area / ((room_area**0.5) * 1.2)
        avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
        
        # 2. Determine the full equipment profile
        equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
        
        # 3. Build the component blueprint (list of required items)
        required_components = _build_component_blueprint(equipment_reqs, technical_reqs)
        
        # 4. Generate the AI prompt
        prompt = _get_prompt_for_room_type(room_type, equipment_reqs, required_components, product_df, budget_tier, features)
        
        # 5. Call the AI model
        response = generate_with_retry(model, prompt)
        if not response or not hasattr(response, 'text') or not response.text:
            raise Exception("AI returned an empty or invalid response.")
        
        # 6. Parse the AI's response
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse a valid JSON object from the AI response.")
        
        # 7. Build the initial BOQ from the AI's selection
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df)
        
        return boq_items, avixa_calcs, equipment_reqs, required_components
    
    except Exception as e:
        # If any step fails, trigger the fallback mechanism
        st.error(f"An error occurred during AI generation: {str(e)}. Creating a smart fallback BOQ.")
        fallback_items, required_components = create_smart_fallback_boq(product_df, equipment_reqs, technical_reqs)
        # We still need avixa_calcs and equipment_reqs for post-processing
        length, width = (room_area**0.5) * 1.2, room_area / ((room_area**0.5) * 1.2)
        avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
        equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
        return fallback_items, avixa_calcs, equipment_reqs, required_components
