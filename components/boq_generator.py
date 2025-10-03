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
    # Define dummy functions to prevent crashes if components are missing
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}, 'control_system': {}}
    def estimate_power_draw(*args): return 100
    ROOM_SPECS = {}

# --- AI Interaction and Parsing ---

def _parse_ai_product_selection(ai_response_text):
    """
    Cleans and parses the AI's JSON response, removing markdown and other artifacts.
    """
    try:
        # More robust cleaning: remove markdown, leading/trailing whitespace, and "json" specifier
        cleaned = ai_response_text.strip().replace("`", "").lstrip("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON response: {e}. Response snippet: {ai_response_text[:200]}")
        return {}

def _get_prompt_for_room_type(room_type, avixa_calcs, equipment_reqs, product_df, budget_tier, features):
    """
    -- UPGRADED PROMPT FACTORY --
    Builds a highly specific, structured prompt for the AI using detailed equipment requirements.
    This prompt sends curated lists of products for the AI to choose from.
    """
    
    def get_filtered_products(primary_cat, sub_cat, limit=20):
        """Fetches and formats a list of products based on new detailed categories."""
        # Ensure product_df has the required columns
        if 'primary_category' not in product_df.columns or 'sub_category' not in product_df.columns:
            st.error("Product catalog is missing 'primary_category' or 'sub_category' columns.")
            return []
            
        return product_df[
            (product_df['primary_category'] == primary_cat) & 
            (product_df['sub_category'] == sub_cat)
        ].head(limit).to_dict('records')

    # Build a library of available components based on the detailed requirements blueprint
    available_components = {}
    
    # Map requirements to product categories and add to the available components library
    if req := equipment_reqs.get('displays'):
        available_components['display_options'] = get_filtered_products('Displays', req['sub_category'])
    if req := equipment_reqs.get('video_system'):
        available_components['camera_options'] = get_filtered_products(req['primary_category'], req['sub_category'])
    if req := equipment_reqs.get('audio_system'):
        available_components['speaker_options'] = get_filtered_products('Audio', 'Loudspeaker')
        available_components['mic_options'] = get_filtered_products('Audio', req['microphone_type'])
        if req.get('dsp_required'):
            available_components['dsp_options'] = get_filtered_products('Audio', 'DSP / Processor')
        if req.get('amplifier_required'):
            available_components['amplifier_options'] = get_filtered_products('Audio', 'Amplifier')
    if req := equipment_reqs.get('control_system'):
        available_components['control_options'] = get_filtered_products(req['primary_category'], req['sub_category'])
    if req := equipment_reqs.get('connectivity'):
        available_components['connectivity_options'] = get_filtered_products(req['primary_category'], req['sub_category'])
    if equipment_reqs.get('housing'):
        available_components['rack_options'] = get_filtered_products('Infrastructure', 'AV Rack')
    if equipment_reqs.get('power'):
        available_components['pdu_options'] = get_filtered_products('Infrastructure', 'Power (PDU/UPS)')
    
    # Add generic components
    available_components['mount_options'] = get_filtered_products('Infrastructure', 'Mount')
    available_components['cable_options'] = get_filtered_products('Infrastructure', 'Cable')
    
    # Convert component lists to JSON strings for the prompt, filtering out empty lists
    json_components = {key: json.dumps(value, indent=2) for key, value in available_components.items() if value}

    # Define the required output structure for the AI
    output_format = {
        "display": {"name": "EXACT product name from display_options"},
        "camera": {"name": "EXACT product name from camera_options"},
        "microphone": {"name": "EXACT product name from mic_options"},
        "speaker": {"name": "EXACT product name from speaker_options"},
        "controller": {"name": "EXACT product name from control_options"},
        # Add other potential keys that the AI should fill
    }

    prompt = f"""
    You are an expert AV System Designer. Your task is to create a Bill of Quantities (BOQ) for a '{room_type}'.

    **Budget Tier:** {budget_tier}
    **Key Features:** {features if features else "Standard functionality"}
    **AVIXA Recommendations:** {json.dumps(avixa_calcs, indent=2)}
    **Required Equipment Blueprint:** {json.dumps(equipment_reqs, indent=2)}

    From the provided JSON lists of available products, you MUST select the best single product model for each required role defined in the 'Required Equipment Blueprint'.
    - Adhere strictly to the blueprint's requirements (e.g., display size, camera type).
    - For the '{budget_tier}' budget, select products with appropriate pricing (e.g., lower-priced for 'Value', higher-priced for 'Premium').
    - Your response MUST be a single, valid JSON object and nothing else. Use the keys 'display', 'camera', 'microphone', 'speaker', etc.

    **Available Products:**
    {json.dumps(json_components, indent=2)}

    **Your BOQ Selection (JSON Only - follow this structure):**
    {json.dumps(output_format, indent=2)}
    """
    return prompt

# --- Fallback & Post-Processing Logic ---

def _get_fallback_product(product_df, primary_cat, sub_cat, rule=""):
    """
    Selects a sensible default product when the AI fails to provide a valid one.
    """
    matching = product_df[(product_df['primary_category'] == primary_cat) & (product_df['sub_category'] == sub_cat)]
    if matching.empty:
        # Broaden search if specific sub-category fails
        matching = product_df[product_df['primary_category'] == primary_cat]
    if matching.empty:
        st.error(f"CRITICAL: No products in catalog for category '{primary_cat} -> {sub_cat}'!")
        return None

    # Apply specific rules if provided
    rule = rule.lower()
    if 'wall mount' in rule:
        filtered = matching[matching['name'].str.contains("Wall Mount", case=False, na=False)]
        if not filtered.empty: matching = filtered
    
    # Select a mid-range product as a safe default
    return matching.sort_values('price').iloc[len(matching)//2].to_dict()

def _strict_product_match(product_name, product_df):
    """
    Finds a product in the dataframe that closely matches the given name.
    """
    if product_df is None or len(product_df) == 0 or not product_name: return None
    
    # Try for an exact match first
    exact_match = product_df[product_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty: return exact_match.iloc[0].to_dict()

    # If no exact match, try a containment search using key terms
    search_terms = product_name.lower().split()
    for term in search_terms:
        if len(term) > 3: # Avoid common short words
            matches = product_df[product_df['name'].str.lower().str.contains(term, na=False)]
            if not matches.empty: return matches.iloc[0].to_dict()
            
    return None

def _build_boq_from_ai_selection(ai_selection, equipment_reqs, product_df):
    """
    Constructs the final BOQ list by matching AI selections to the product catalog,
    with robust fallback logic for missing or invalid selections.
    """
    boq_items = []
    processed_items = set()

    # A helper function to add items to the BOQ
    def add_item(product_data, justification, qty, matched_by_ai):
        if product_data and product_data['name'] not in processed_items:
            boq_items.append({
                'category': product_data.get('sub_category', 'N/A'),
                'name': product_data['name'],
                'brand': product_data.get('brand', 'N/A'),
                'quantity': qty,
                'price': float(product_data.get('price', 0)),
                'justification': justification,
                'specifications': product_data.get('features', ''),
                'image_url': product_data.get('image_url', ''),
                'gst_rate': product_data.get('gst_rate', 18),
                'matched': matched_by_ai,
                'power_draw': estimate_power_draw(product_data.get('category', ''), product_data['name'])
            })
            processed_items.add(product_data['name'])
            return True
        return False

    # Define a mapping from the equipment blueprint to AI selection keys and product categories
    blueprint_map = {
        'displays': {'key': 'display', 'justification': 'Primary room display'},
        'video_system': {'key': 'camera', 'justification': 'Primary video camera/bar'},
        'audio_system_mic': {'key': 'microphone', 'justification': 'Room microphone coverage'},
        'audio_system_spk': {'key': 'speaker', 'justification': 'Room audio output'},
        'audio_system_dsp': {'key': 'dsp', 'justification': 'Audio signal processing'},
        'audio_system_amp': {'key': 'amplifier', 'justification': 'Power for speakers'},
        'control_system': {'key': 'controller', 'justification': 'In-room meeting controller'},
        'connectivity': {'key': 'connectivity', 'justification': 'Content sharing input'},
        'housing': {'key': 'rack', 'justification': 'Equipment housing'},
        'power': {'key': 'pdu', 'justification': 'Power distribution'},
    }

    # Process each required component type from the blueprint
    for item_key, mapping in blueprint_map.items():
        req_details = None
        # Handle nested audio requirements
        if item_key.startswith('audio_system_'):
            part = item_key.split('_')[-1]
            if equipment_reqs.get('audio_system'):
                if (part == 'mic' and equipment_reqs['audio_system'].get('microphone_type')) or \
                   (part == 'spk') or \
                   (part == 'dsp' and equipment_reqs['audio_system'].get('dsp_required')) or \
                   (part == 'amp' and equipment_reqs['audio_system'].get('amplifier_required')):
                    req_details = equipment_reqs['audio_system']
                    # Refine details for specific audio part
                    if part == 'mic': req_details = {'primary_category': 'Audio', 'sub_category': req_details['microphone_type'], 'quantity': req_details.get('microphone_count', 1)}
                    elif part == 'spk': req_details = {'primary_category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': req_details.get('speaker_count', 2)}
                    elif part == 'dsp': req_details = {'primary_category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1}
                    elif part == 'amp': req_details = {'primary_category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1}
        else:
            req_details = equipment_reqs.get(item_key)

        if not req_details:
            continue
        
        # Try to find the AI's selection
        selected_product_name = ai_selection.get(mapping['key'], {}).get('name')
        product_data = _strict_product_match(selected_product_name, product_df)
        
        if product_data and add_item(product_data, mapping['justification'], req_details.get('quantity', 1), True):
            continue # Item successfully added from AI selection
        else:
            # If AI selection fails, use fallback
            st.warning(f"AI selection for '{mapping['key']}' ('{selected_product_name}') not found or invalid. Using fallback.")
            fallback_product = _get_fallback_product(product_df, req_details['primary_category'], req_details['sub_category'])
            add_item(fallback_product, f"{mapping['justification']} (auto-selected)", req_details.get('quantity', 1), False)

    # Add essential accessories that the AI might miss
    if not any('Mount' in item['category'] for item in boq_items) and equipment_reqs.get('displays'):
        fallback_mount = _get_fallback_product(product_df, 'Infrastructure', 'Mount', rule="wall mount")
        add_item(fallback_mount, "Wall mount for display (auto-added)", equipment_reqs['displays'].get('quantity', 1), False)

    if not any('Cable' in item['category'] for item in boq_items):
        fallback_cable = _get_fallback_product(product_df, 'Infrastructure', 'Cable')
        add_item(fallback_cable, "Network & HDMI cables (auto-added)", 5, False)
        
    return boq_items

# --- Post-Processing & Validation ---

def _post_process_boq(boq_items):
    """
    Runs a series of cleanup and validation steps on the generated BOQ.
    """
    # Step 1: Correct any non-integer quantities
    for item in boq_items:
        try:
            item['quantity'] = int(float(item.get('quantity', 1)))
        except (ValueError, TypeError):
            item['quantity'] = 1

    # Step 2: Remove exact duplicate line items
    seen, unique_items = set(), []
    for item in boq_items:
        if item.get('name') not in seen:
            seen.add(item.get('name'))
            unique_items.append(item)
    
    return unique_items

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    """
    Placeholder for validating the final BOQ against AVIXA standards.
    """
    issues, warnings = [], []
    # Example check (can be expanded): Check if display size is close to recommendation
    if display_req := equipment_reqs.get('displays'):
        target_size = display_req.get('size_inches', 65)
        selected_display = next((item for item in boq_items if 'Display' in item['category']), None)
        if selected_display:
            match = re.search(r'(\d+)', selected_display['name'])
            if match and abs(int(match.group(1)) - target_size) > 10:
                warnings.append(f"Selected display ({match.group(1)}\") is significantly different from the recommended size ({target_size}\").")
                
    return {'avixa_issues': issues, 'avixa_warnings': warnings}

# --- Core Generation Function ---

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """
    The re-architected core function to generate a Bill of Quantities using an AI model.
    """
    # 1. Calculate environmental and technical requirements
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    # 2. Build a high-context prompt for the AI
    prompt = _get_prompt_for_room_type(
        room_type, avixa_calcs, equipment_reqs, 
        product_df, budget_tier, features
    )
    
    boq_items = []
    try:
        # 3. Call the AI model and parse the response
        response = generate_with_retry(model, prompt)
        if not response or not response.text:
            raise Exception("AI returned an empty response.")
        
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse valid JSON from AI response.")
            
        # 4. Build the BOQ from the AI's selections with fallbacks
        boq_items = _build_boq_from_ai_selection(ai_selection, equipment_reqs, product_df)

    except Exception as e:
        st.error(f"AI generation failed: {str(e)}. Building a BOQ with default components.")
        # If the entire AI process fails, create a BOQ using only fallbacks
        boq_items = _build_boq_from_ai_selection({}, equipment_reqs, product_df)

    # 5. Post-process and clean the final BOQ
    final_boq = _post_process_boq(boq_items)
    
    return final_boq, avixa_calcs, equipment_reqs
