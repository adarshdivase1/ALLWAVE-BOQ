import streamlit as st
import pandas as pd
import re
import json
import time

# --- Component Imports ---
try:
    from components.gemini_handler import generate_with_retry
    from components.av_designer import calculate_avixa_recommendations, determine_equipment_requirements
    from components.visualizer import ROOM_SPECS
    from components.utils import estimate_power_draw
except ImportError as e:
    st.error(f"BOQ Generator failed to import a component: {e}")
    # Define dummy functions to prevent crashes
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}, 'control_system': {}}
    def estimate_power_draw(*args): return 100
    ROOM_SPECS = {}

# --- AI Interaction and Parsing ---
def _parse_ai_product_selection(ai_response_text):
    try:
        cleaned = ai_response_text.strip().replace("`", "").lstrip("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}. Response was: {ai_response_text[:200]}")
        return {}

# --- NEW: Intelligent Product Filtering for Prompts ---
def _get_filtered_product_list_for_prompt(comp_key, comp_spec, product_df):
    """
    Pre-filters the product list based on component type and rules BEFORE sending it to the AI.
    This is the core of the new, more logical system.
    """
    category = comp_spec['category']
    rule = comp_spec.get('rule', '').lower()
    
    # Start with all products in the category
    matching_products = product_df[product_df['category'] == category].copy()
    if matching_products.empty:
        return "   - (No products found in catalog for this category)\n"

    # --- APPLY SPECIFIC, HARD-CODED FILTERS ---
    
    # 1. Filter for Displays by Size
    if 'display' in comp_key:
        target_size_match = re.search(r'(\d+)"', rule)
        if target_size_match:
            target_size = int(target_size_match.group(1))
            # Extract size from product name (e.g., "Samsung 65" TV" -> 65)
            matching_products['extracted_size'] = matching_products['name'].str.extract(r'(\d+)').astype(float)
            # Keep only products within a tolerance (e.g., +/- 5 inches)
            matching_products = matching_products[abs(matching_products['extracted_size'] - target_size) <= 5]

    # 2. Filter for Controllers (exclude Schedulers)
    if 'controller' in comp_key:
        matching_products = matching_products[~matching_products['name'].str.contains("Scheduler", case=False, na=False)]

    # 3. Filter for Mounts (only wall mounts)
    if 'mount' in comp_key and 'wall mount' in rule:
        matching_products = matching_products[matching_products['name'].str.contains("Wall Mount", case=False, na=False)]
        
    # --- Format the filtered list for the prompt ---
    prompt_text = ""
    if not matching_products.empty:
        for _, prod in matching_products.head(10).iterrows(): # Limit to top 10 choices
            prompt_text += f"   - {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"
    else:
        # If filters remove everything, provide a message
        prompt_text += f"   - (No products in catalog match the specific rule: '{rule}')\n"
            
    return prompt_text

def _get_prompt_for_room_type(room_type, avixa_calcs, equipment_reqs, required_components, product_df, budget_tier, features):
    """
    -- REVISED PROMPT FACTORY --
    Now uses the intelligent pre-filter to build the product list.
    """
    
    # --- Build the intelligently filtered product list for the prompt ---
    product_text_list = ""
    for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
        product_text_list += f"\n## {comp_key.replace('_', ' ').upper()} (Category: {comp_spec['category']})\n"
        product_text_list += f"   - **Requirement:** {comp_spec['justification']}\n"
        # Get the pre-filtered list of products for this specific component
        product_text_list += _get_filtered_product_list_for_prompt(comp_key, comp_spec, product_df)

    # --- PROMPT TEMPLATES ---
    prompt = ""
    display_size_inches = equipment_reqs.get('displays', {}).get('size_inches', 65)
    display_qty = equipment_reqs.get('displays', {}).get('quantity', 1)

    # Template for Boardrooms & Telepresence (High-End, Premium)
    if any(keyword in room_type for keyword in ["Boardroom", "Telepresence"]):
        prompt = f"""
        You are a top-tier CTS-D AV consultant designing a premium, executive-level **{room_type}**.
        The client demands flawless performance and a seamless user experience.

        # CRITICAL REQUIREMENTS
        - **Display:** The design requires **{display_qty}x {display_size_inches}-inch display(s)**. Your choice MUST be from the pre-filtered list which only contains correctly sized models.
        - **Audio:** Audio quality is paramount. Select premium ceiling microphones and speakers from the list for crystal-clear voice reproduction.
        - **System Type:** This is a fully integrated, modular system. Choose a high-performance codec and PTZ camera. Do NOT select an all-in-one video bar.
        - **Client Needs:** {features if features else 'Standard executive conferencing functionality.'}
        """

    # Template for Training & Event Rooms (Presenter-Focused, Robust)
    elif any(keyword in room_type for keyword in ["Training", "Event", "Multipurpose"]):
        prompt = f"""
        You are an AV engineer designing a flexible system for a **{room_type}**.
        The focus is on the presenter's ability to engage with both local and remote audiences.

        # CRITICAL REQUIREMENTS
        - **Presenter Audio:** A wireless microphone system for the presenter is a NON-NEGOTIABLE requirement.
        - **Display:** The main presentation display must be **{display_size_inches} inches**. Choose the best option from the pre-filtered list.
        - **Client Needs:** {features if features else 'Standard presentation and hybrid training functionality.'}
        """
    # Default Template for Huddle & Standard Rooms (Simplicity & Value)
    else:
        prompt = f"""
        You are an AV system designer creating a reliable and user-friendly BOQ for a **{room_type}**.
        The goal is simplicity and excellent value for everyday collaboration.

        # CRITICAL REQUIREMENTS
        - **Simplicity:** Prioritize an all-in-one video bar that integrates the camera, microphones, and speakers.
        - **User Interface:** The in-room controller must be intuitive for non-technical users. Choose a standard controller from the pre-filtered list, which correctly excludes room schedulers.
        - **Display Size:** The display must be **{display_size_inches} inches**. Select the best value option from the provided list of correctly-sized displays.
        """

    prompt += f"""
    # MANDATORY SYSTEM COMPONENTS
    You MUST select one product for each of the following roles from the pre-filtered lists provided.
    {product_text_list}

    # OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT)
    """
    
    # Add the final JSON structure to the chosen prompt
    json_format_instruction = "{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format_instruction += f'  "{comp_key}": {{"name": "EXACT product name from list", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format_instruction += "}\n"
    
    return prompt + json_format_instruction

# --- Dynamic Component Blueprint Builder ---
def _build_component_blueprint(equipment_reqs, room_type):
    """Dynamically builds the list of required components based on the actual system design."""
    
    displays_req = equipment_reqs.get('displays', {})
    display_size = displays_req.get('size_inches', 65)
    display_qty = displays_req.get('quantity', 1)
    
    blueprint = {
        'display': {'category': 'Displays', 'quantity': display_qty, 'priority': 1, 'justification': f"Primary {display_size}\" display(s) for {room_type}", 'rule': f'Select a display as close to {display_size}" as possible.'},
        'display_mount': {'category': 'Mounts', 'quantity': display_qty, 'priority': 8, 'justification': 'Wall mount compatible with the selected display.', 'rule': "Select a WALL MOUNT for a display."},
        'in_room_controller': {'category': 'Control', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel to start/join/control meetings.', 'rule': "Select a tabletop touch controller. DO NOT select a 'Scheduler'."},
        'table_connectivity': {'category': 'Cables', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input for wired HDMI presentation.', 'rule': "Select a table cubby or wall plate with HDMI."},
        'network_cables': {'category': 'Cables', 'quantity': 5, 'priority': 10, 'justification': 'Network patch cables for IP-enabled devices.', 'rule': "Select a standard pack of CAT6 patch cables."},
    }

    video_system_req = equipment_reqs.get('video_system', {})
    if video_system_req.get('type') == 'All-in-one Video Bar':
        blueprint['video_bar'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar with integrated camera, mics, and speakers.', 'rule': "Select a complete video bar."}
    elif video_system_req.get('type') == 'Modular Codec + PTZ Camera':
        blueprint['video_codec'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'Core video codec for processing and connectivity.', 'rule': "Select a professional codec."}
        blueprint['ptz_camera'] = {'category': 'Video Conferencing', 'quantity': video_system_req.get('camera_count', 1), 'priority': 2.1, 'justification': 'PTZ (Pan-Tilt-Zoom) camera for the main video feed.', 'rule': "Select a PTZ camera."}

    audio_system_req = equipment_reqs.get('audio_system', {})
    if audio_system_req.get('dsp_required'):
        blueprint['dsp'] = {'category': 'Audio', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for echo cancellation and audio mixing.', 'rule': "Select a DSP."}
        blueprint['microphones'] = {'category': 'Audio', 'quantity': audio_system_req.get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones to cover the room seating.', 'rule': "Select ceiling or table microphones."}
        blueprint['speakers'] = {'category': 'Audio', 'quantity': audio_system_req.get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for program audio.', 'rule': "Select ceiling or wall-mounted speakers."}
        blueprint['amplifier'] = {'category': 'Audio', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier to power the passive speakers.', 'rule': "Select an appropriate power amplifier."}

    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 12, 'justification': 'Equipment rack to house components.', 'rule': "Select a standard AV rack."}
    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit for the rack.', 'rule': "Select a rack-mounted PDU."}

    return blueprint

# --- Fallback & Post-Processing Logic (Largely Unchanged) ---
def _get_fallback_product(category, product_df, comp_spec):
    matching = product_df[product_df['category'] == category]
    if matching.empty:
        matching = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    if matching.empty:
        st.error(f"CRITICAL: No products in catalog for category '{category}'!")
        return None
    return matching.sort_values('price').iloc[len(matching)//2].to_dict()

def _strict_product_match(product_name, product_df, category):
    if product_df is None or len(product_df) == 0: return None
    search_df = product_df[product_df['category'] == category]
    if search_df.empty: search_df = product_df
    
    exact_match = search_df[search_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty: return exact_match.iloc[0].to_dict()
    
    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3:
            matches = search_df[search_df['name'].str.lower().str.contains(term, na=False)]
            if not matches.empty: return matches.iloc[0].to_dict()
    return None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df):
    boq_items = []
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        comp_spec = required_components[comp_key]
        category = comp_spec['category']
        
        matched_product = _strict_product_match(selection.get('name', 'N/A'), product_df, category)
        
        product_to_add = None
        was_matched = False

        if matched_product:
            product_to_add = matched_product
            was_matched = True
        else:
            product_to_add = _get_fallback_product(category, product_df, comp_spec)
            comp_spec['justification'] += ' (auto-selected)'

        if product_to_add:
            boq_items.append({
                'category': product_to_add['category'], 'name': product_to_add['name'], 
                'brand': product_to_add['brand'], 'quantity': selection.get('qty', comp_spec['quantity']), 
                'price': float(product_to_add['price']), 'justification': comp_spec['justification'], 
                'specifications': product_to_add.get('features', ''), 'image_url': product_to_add.get('image_url', ''), 
                'gst_rate': product_to_add.get('gst_rate', 18), 'matched': was_matched, 
                'power_draw': estimate_power_draw(product_to_add['category'], product_to_add['name'])
            })
            
    if len(boq_items) < len(required_components):
        boq_items = _add_essential_missing_components(boq_items, product_df, required_components)
    return boq_items

def _add_essential_missing_components(boq_items, product_df, required_components):
    # This function remains important for robustness
    present_keys = set()
    for item in boq_items:
        for key, spec in required_components.items():
            if item['category'] == spec['category']: # A simple but effective check
                present_keys.add(key)

    missing_keys = set(required_components.keys()) - present_keys
    for key in missing_keys:
        comp_spec = required_components[key]
        st.warning(f"AI failed to select a '{key}'. Adding a fallback.")
        fallback = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if fallback:
            boq_items.append({
                'category': fallback['category'], 'name': fallback['name'], 'brand': fallback['brand'],
                'quantity': comp_spec['quantity'], 'price': float(fallback['price']),
                'justification': f"{comp_spec['justification']} (auto-added)",
                'specifications': fallback.get('features', ''), 'image_url': fallback.get('image_url', ''),
                'gst_rate': fallback.get('gst_rate', 18), 'matched': False
            })
    return boq_items

def create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs):
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if product:
            fallback_items.append({'category': product['category'], 'name': product['name'], 'brand': product['brand'], 'quantity': comp_spec['quantity'], 'price': float(product['price']), 'justification': comp_spec['justification'], 'specifications': product.get('features', ''), 'image_url': product.get('image_url', ''), 'gst_rate': product.get('gst_rate', 18), 'matched': True})
    return fallback_items
    
# --- Core AI Generation Function ---
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """The final, re-architected core function to get the BOQ from the AI."""
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    
    # Call the new "Prompt Factory" which now uses intelligent pre-filtering
    prompt = _get_prompt_for_room_type(
        room_type, avixa_calcs, equipment_reqs, required_components, 
        product_df, budget_tier, features
    )
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text: raise Exception("AI returned an empty response.")
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection: raise Exception("Failed to parse valid JSON from AI response.")
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df)
        return boq_items, avixa_calcs, equipment_reqs
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}")
        fallback_items = create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs)
        return fallback_items, avixa_calcs, equipment_reqs
