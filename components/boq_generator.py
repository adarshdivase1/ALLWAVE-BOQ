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
    """
    Parses the JSON object from the AI's response text.
    """
    try:
        # Clean the text: remove markdown, leading/trailing whitespace, and "json" language specifier
        cleaned = ai_response_text.strip().replace("`", "").lstrip("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}. Response was: {ai_response_text[:200]}")
        return {}

def _get_prompt_for_room_type(room_type, avixa_calcs, equipment_reqs, product_df, budget_tier, features):
    """
    -- UPGRADED PROMPT FACTORY --
    Builds a highly specific, structured prompt for the AI using the new detailed equipment requirements.
    """
    
    def get_filtered_products(primary, sub):
        """Helper to get products based on new primary/sub category structure."""
        # This assumes your product_df has 'primary_category' and 'sub_category' columns
        # If not, you might need to adjust this logic.
        if 'primary_category' in product_df.columns and 'sub_category' in product_df.columns:
             return product_df[
                (product_df['primary_category'] == primary) & 
                (product_df['sub_category'] == sub)
            ].to_dict('records')
        else: # Fallback for old 'category' structure
            return product_df[product_df['category'] == sub].to_dict('records')


    # Build a library of available components based on the new detailed requirements
    available_components = {}
    
    # Displays
    display_req = equipment_reqs.get('displays', {})
    if display_req and 'sub_category' in display_req:
        available_components['display_options'] = get_filtered_products('Displays', display_req['sub_category'])

    # Video System
    video_req = equipment_reqs.get('video_system', {})
    if video_req and 'primary_category' in video_req:
        available_components['camera_options'] = get_filtered_products(video_req['primary_category'], video_req.get('sub_category', 'Video Bar')) # Default to Video Bar if no sub_cat

    # Audio System
    audio_req = equipment_reqs.get('audio_system', {})
    if audio_req:
        available_components['speaker_options'] = get_filtered_products('Audio', 'Loudspeaker')
        if 'microphone_type' in audio_req:
            available_components['mic_options'] = get_filtered_products('Audio', audio_req['microphone_type'])
        if audio_req.get('dsp_required'):
            available_components['dsp_options'] = get_filtered_products('Audio', 'DSP / Processor')
        if audio_req.get('amp_required'):
            available_components['amp_options'] = get_filtered_products('Audio', 'Amplifier')

    # Control System
    control_req = equipment_reqs.get('control_system', {})
    if control_req and 'primary_category' in control_req:
        available_components['control_options'] = get_filtered_products(control_req['primary_category'], control_req['sub_category'])

    # Connectivity
    conn_req = equipment_reqs.get('connectivity', {})
    if conn_req and 'primary_category' in conn_req:
        available_components['wireless_presentation_options'] = get_filtered_products(conn_req['primary_category'], conn_req['sub_category'])
    
    # Housing & Power
    if equipment_reqs.get('housing'):
        available_components['rack_options'] = get_filtered_products('Infrastructure', 'AV Rack')
    if equipment_reqs.get('power_management'):
        available_components['pdu_options'] = get_filtered_products('Infrastructure', 'Power (PDU/UPS)')

    # Convert component lists to JSON strings for the prompt
    json_components = {key: json.dumps(value[:30], indent=2) for key, value in available_components.items() if value} # Limit to 30 items to keep prompt size manageable

    prompt = f"""
    You are an expert AV System Designer. Your task is to create a Bill of Quantities (BOQ) for a '{room_type}'.
    
    **Budget Tier:** {budget_tier}
    **Key Features:** {features}
    **AVIXA Recommendations:** {json.dumps(avixa_calcs, indent=2)}
    **Required Equipment Blueprint:** {json.dumps(equipment_reqs, indent=2)}

    From the provided JSON lists of available products, select the BEST single product for each required category based on the Blueprint.
    - Adhere strictly to the 'Required Equipment Blueprint'. For example, if the blueprint specifies a 65-inch display, choose the product closest to that size.
    - For the '{budget_tier}' tier, select products with appropriate pricing (e.g., avoid premium for an 'economy' budget).
    - If a required category is missing from the provided product lists, state that no suitable product was found for that category.
    - You MUST return your selections in a single, valid JSON object, with no other text. The keys of the JSON should correspond to the main categories in the blueprint (e.g., "display", "camera", "microphone", "controller").

    **Available Products:**
    {json.dumps(json_components, indent=2)}

    **Your BOQ Selection (JSON Only):**
    """
    return prompt

# --- Fallback & Post-Processing Logic ---
def _get_fallback_product(category, product_df):
    """Get a median-priced product from a given category as a fallback."""
    matching = product_df[product_df['category'] == category]
    if matching.empty:
        # Try a case-insensitive search if direct match fails
        matching = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    if matching.empty:
        st.error(f"CRITICAL: No products in catalog for category '{category}'!")
        return None
    # Return the median-priced item to avoid extremes
    return matching.sort_values('price').iloc[len(matching)//2].to_dict()

def _strict_product_match(product_name, product_df):
    """Finds the best match for a product name in the dataframe."""
    if product_df is None or len(product_df) == 0: return None
    
    # 1. Exact match (case-insensitive)
    exact_match = product_df[product_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty: return exact_match.iloc[0].to_dict()

    # 2. Contains all key terms from the product name
    search_terms = [term for term in product_name.lower().split() if len(term) > 3]
    if not search_terms: return None
    
    # Create a boolean mask for each term
    matches = product_df['name'].str.lower()
    for term in search_terms:
        matches = matches & product_df['name'].str.lower().str.contains(term, na=False)
    
    matching_df = product_df[matches]
    if not matching_df.empty:
        return matching_df.iloc[0].to_dict()

    # 3. Fallback to any partial match on the first significant term
    for term in search_terms:
        partial_matches = product_df[product_df['name'].str.lower().str.contains(term, na=False)]
        if not partial_matches.empty: return partial_matches.iloc[0].to_dict()

    return None

def _build_boq_from_ai_selection(ai_selection, equipment_reqs, product_df):
    """
    Builds the BOQ list from the AI's JSON response, mapping selections to equipment requirements.
    """
    boq_items = []
    # Map AI selection keys to equipment_reqs keys and details
    key_map = {
        'display': ('displays', equipment_reqs.get('displays', {})),
        'camera': ('video_system', equipment_reqs.get('video_system', {})),
        'video_bar': ('video_system', equipment_reqs.get('video_system', {})),
        'microphone': ('audio_system', equipment_reqs.get('audio_system', {})),
        'speaker': ('audio_system', equipment_reqs.get('audio_system', {})),
        'dsp': ('audio_system', equipment_reqs.get('audio_system', {})),
        'amplifier': ('audio_system', equipment_reqs.get('audio_system', {})),
        'controller': ('control_system', equipment_reqs.get('control_system', {})),
        'wireless_presentation': ('connectivity', equipment_reqs.get('connectivity', {})),
        'rack': ('housing', equipment_reqs.get('housing', {})),
        'pdu': ('power_management', equipment_reqs.get('power_management', {}))
    }

    for key, selected_product_info in ai_selection.items():
        # Sanity check if the AI returned a valid-looking product object
        if not isinstance(selected_product_info, dict) or 'name' not in selected_product_info:
            continue
        
        product_name = selected_product_info['name']
        matched_product = _strict_product_match(product_name, product_df)
        
        # Determine quantity and justification from equipment_reqs
        req_key, req_details = key_map.get(key, (None, {}))
        
        # Special handling for quantity based on component type
        quantity = 1 # Default
        if key == 'display':
            quantity = req_details.get('quantity', 1)
        elif key == 'microphone':
            quantity = req_details.get('microphone_count', 1)
        elif key == 'speaker':
            quantity = req_details.get('speaker_count', 1)
        
        justification = req_details.get('justification', f"Selected for {key} role.")

        if matched_product:
            boq_items.append({
                'category': matched_product['category'],
                'name': matched_product['name'],
                'brand': matched_product['brand'],
                'quantity': quantity,
                'price': float(matched_product['price']),
                'justification': justification,
                'specifications': matched_product.get('features', ''),
                'image_url': matched_product.get('image_url', ''),
                'gst_rate': matched_product.get('gst_rate', 18),
                'matched': True,
                'power_draw': estimate_power_draw(matched_product['category'], matched_product['name'])
            })
        else:
            # If strict match fails, use a fallback based on the expected category from equipment_reqs
            fallback_category = req_details.get('sub_category')
            if fallback_category:
                fallback_product = _get_fallback_product(fallback_category, product_df)
                if fallback_product:
                     boq_items.append({
                        'category': fallback_product['category'],
                        'name': fallback_product['name'],
                        'brand': fallback_product['brand'],
                        'quantity': quantity,
                        'price': float(fallback_product['price']),
                        'justification': justification + ' (auto-selected fallback)',
                        'specifications': fallback_product.get('features', ''),
                        'image_url': fallback_product.get('image_url', ''),
                        'gst_rate': fallback_product.get('gst_rate', 18),
                        'matched': False,
                        'power_draw': estimate_power_draw(fallback_product['category'], fallback_product['name'])
                    })

    return boq_items

def _remove_exact_duplicates(boq_items):
    seen, unique_items = set(), []
    for item in boq_items:
        if item.get('name') not in seen:
            seen.add(item.get('name'))
            unique_items.append(item)
    return unique_items

def _correct_quantities(boq_items):
    for item in boq_items:
        try:
            item['quantity'] = int(float(item.get('quantity', 1)))
        except (ValueError, TypeError):
            item['quantity'] = 1
    return boq_items

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    issues, warnings = [], []
    # This function can be expanded with more detailed validation rules.
    return {'avixa_issues': issues, 'avixa_warnings': warnings}

# --- Core AI Generation Function ---
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """The re-architected core function to get the BOQ from the AI."""
    # Step 1: Calculate room dimensions and engineering requirements
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    # Step 2: Call the new "Prompt Factory" to get a tailored prompt
    prompt = _get_prompt_for_room_type(
        room_type, avixa_calcs, equipment_reqs, 
        product_df, budget_tier, features
    )
    
    # Step 3: Call the AI and process the response
    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text:
            raise Exception("AI returned an empty response.")
        
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse valid JSON from AI response.")
            
        # Step 4: Build the BOQ from the AI's structured response
        # This function is now adapted for the new AI response format
        boq_items = _build_boq_from_ai_selection(ai_selection, equipment_reqs, product_df)
        
        # Post-processing steps
        boq_items = _remove_exact_duplicates(boq_items)
        boq_items = _correct_quantities(boq_items)

        return boq_items, avixa_calcs, equipment_reqs
        
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}. Generating a fallback BOQ.")
        # Fallback mechanism can be improved, e.g., by creating a simple BOQ from equipment_reqs
        return [], avixa_calcs, equipment_reqs
