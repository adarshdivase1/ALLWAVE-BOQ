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
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}, 'control_system': {}, 'housing': {}, 'power_management': {}}
    def estimate_power_draw(*args): return 100
    ROOM_SPECS = {}

# --- NEW: Engineering Validation Function ---
def _perform_engineering_validation(boq_items, product_df):
    """
    Performs basic engineering checks like rack space and power load.
    """
    warnings = []
    
    # Check 1: Rack Unit (RU) capacity
    # This assumes your item dictionary contains a 'rack_units' key or can be estimated.
    rack_items = [item for item in boq_items if item.get('rack_units', 0) > 0 or item['category'] in ['Audio', 'Video Conferencing', 'Infrastructure']]
    rack_container = next((item for item in boq_items if 'Rack' in item.get('name', '')), None)
    
    if rack_items and rack_container:
        # Estimate RU for items that don't have it explicitly defined
        total_ru = sum(item.get('rack_units', 1) for item in rack_items) # Default to 1U if not specified
        rack_size_match = re.search(r'(\d+)U', rack_container['name'])
        if rack_size_match:
            rack_capacity = int(rack_size_match.group(1))
            # Add a buffer for cable management and ventilation
            if total_ru > rack_capacity:
                warnings.append(f"🔌 **Engineering Warning (Rack Overflow)**: The estimated **{total_ru}U** of equipment will not fit in the selected **{rack_capacity}U** rack.")

    # Check 2: Power Draw
    total_power = sum(item.get('power_draw', 0) for item in boq_items)
    if total_power > 1440: # Assuming 80% load on a standard 15A/120V circuit
        warnings.append(f"🔌 **Engineering Warning (Power Overload)**: Total system power draw is **{total_power}W**, which may exceed a standard 15A circuit.")
            
    return boq_items, warnings

# --- AI Interaction and Parsing ---
def _parse_ai_product_selection(ai_response_text):
    try:
        # More robust cleaning to handle markdown code blocks
        if "```json" in ai_response_text:
            cleaned = ai_response_text.split("```json")[1].split("```")[0]
        else:
             cleaned = ai_response_text.strip().replace("`", "").lstrip("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}. Response was: {ai_response_text[:200]}")
        return {}

def _build_comprehensive_boq_prompt(room_type, room_area, avixa_calcs, equipment_reqs, required_components, product_df, budget_tier, features):
    prompt = f"""You are an AVIXA CTS-D certified AV system designer. Your task is to create a complete, logical, and standards-compliant Bill of Quantities (BOQ).

# PROJECT BRIEF
- **Room Type:** {room_type}
- **Budget Tier:** {budget_tier}
- **Client Needs:** {features if features else 'Standard functionality for this room type.'}
- **System Requirements:** {json.dumps(equipment_reqs, indent=2)}

# MANDATORY SYSTEM COMPONENTS ({len(required_components)} items)
You MUST select one product for each of the following roles from the provided product lists.
"""
    for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
        prompt += f"\n## {comp_key.replace('_', ' ').upper()} (Category: {comp_spec['category']})\n"
        prompt += f"   - **Requirement:** {comp_spec['justification']}\n"
        prompt += f"   - **Rule:** {comp_spec.get('rule', 'Select the best fit.')}\n"
        
        matching_products = product_df[product_df['category'] == comp_spec['category']].head(15)
        if not matching_products.empty:
            for _, prod in matching_products.iterrows():
                prompt += f"   - {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"
        else:
            prompt += f"   - (No products found in catalog for {comp_spec['category']})\n"

    prompt += "\n# OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT OR COMMENTS)\n"
    prompt += "{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        prompt += f'  "{comp_key}": {{"name": "EXACT product name from list", "qty": {comp_spec["quantity"]}}}{comma}\n'
    prompt += "}\n"
    return prompt

# --- Dynamic Component Blueprint Builder ---
def _build_component_blueprint(equipment_reqs, room_type):
    """Dynamically builds the list of required components based on the actual system design."""
    
    blueprint = {
        'display': {'category': 'Displays', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 1, 'justification': f"Primary {equipment_reqs['displays'].get('size_inches', 65)}\" display for {room_type}", 'rule': f"Select a display as close to {equipment_reqs['displays'].get('size_inches', 65)}\" as possible."},
        'display_mount': {'category': 'Mounts', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 8, 'justification': 'Wall mount compatible with the selected display.', 'rule': "Select a WALL MOUNT for a display. DO NOT select a camera or ceiling mount."},
        'in_room_controller': {'category': 'Control', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel to start/join/control meetings.', 'rule': "Select a tabletop touch controller. DO NOT select a 'Scheduler'."},
        'table_connectivity': {'category': 'Cables', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input for wired HDMI presentation.', 'rule': "Select a table cubby or wall plate with HDMI."},
        'network_cables': {'category': 'Cables', 'quantity': 5, 'priority': 10, 'justification': 'Network patch cables for IP-enabled devices.', 'rule': "Select a standard pack of CAT6 patch cables."},
    }

    if equipment_reqs.get('video_system', {}).get('type') == 'All-in-one Video Bar':
        blueprint['video_bar'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar with integrated camera, mics, and speakers.', 'rule': "Select a complete video bar like a Poly Studio or Logitech Rally Bar."}
    elif equipment_reqs.get('video_system', {}).get('type') == 'Modular Codec + PTZ Camera':
        blueprint['video_codec'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'Core video codec for processing and connectivity.', 'rule': "Select a professional codec like a Poly G7500 or Cisco Codec."}
        blueprint['ptz_camera'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2.1, 'justification': 'PTZ (Pan-Tilt-Zoom) camera for the main video feed.', 'rule': "Select a PTZ camera like a Poly EagleEye or Logitech Rally Camera."}

    if equipment_reqs.get('audio_system', {}).get('dsp_required'):
        blueprint['dsp'] = {'category': 'Audio', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for echo cancellation and audio mixing.', 'rule': "Select a DSP like a Q-SYS Core or Biamp Tesira."}
        blueprint['microphones'] = {'category': 'Audio', 'quantity': equipment_reqs.get('audio_system', {}).get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones to cover the room seating.', 'rule': "Select ceiling or table microphones."}
        blueprint['speakers'] = {'category': 'Audio', 'quantity': equipment_reqs.get('audio_system', {}).get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for program audio and voice reinforcement.', 'rule': "Select ceiling or wall-mounted speakers."}
        blueprint['amplifier'] = {'category': 'Audio', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier to power the passive speakers.', 'rule': "Select an appropriate power amplifier."}

    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 12, 'justification': 'Equipment rack to house components.', 'rule': "Select a standard AV rack."}
    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit for the rack.', 'rule': "Select a rack-mounted PDU."}

    return blueprint

# --- Fallback and Matching Logic ---
def _get_fallback_product(category, product_df, comp_spec):
    """Get best fallback product, now with keyword filtering for accuracy."""
    matching = product_df[product_df['category'] == category]
    if matching.empty:
        matching = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    if matching.empty:
        st.error(f"CRITICAL: No products in catalog for category '{category}'!")
        return None

    rule = comp_spec.get('rule', '').lower()
    if 'wall mount' in rule:
        filtered = matching[matching['name'].str.contains("Wall Mount", case=False)]
        if not filtered.empty: matching = filtered
    if 'controller' in rule and "scheduler" not in rule:
        filtered = matching[~matching['name'].str.contains("Scheduler", case=False)]
        if not filtered.empty: matching = filtered
    
    if 'display' in category.lower() and 'size_inches' in equipment_reqs['displays']:
        target_size = equipment_reqs['displays']['size_inches']
        # Find closest size
        matching['size_diff'] = matching['name'].str.extract(r'(\d+)').astype(float).subtract(target_size).abs()
        return matching.sort_values('size_diff').iloc[0].to_dict()

    # Default to a mid-range product instead of the cheapest
    return matching.sort_values('price').iloc[len(matching)//2].to_dict()

def _strict_product_match(product_name, product_df, category):
    if product_df is None or len(product_df) == 0: return None
    filtered_by_cat = product_df[product_df['category'] == category]
    if filtered_by_cat.empty:
        filtered_by_cat = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    search_df = filtered_by_cat if not filtered_by_cat.empty else product_df
    exact_match = search_df[search_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty: return exact_match.iloc[0].to_dict()
    # Fuzzy match as a backup
    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3:
            matches = search_df[search_df['name'].str.lower().str.contains(term, na=False)]
            if not matches.empty: return matches.iloc[0].to_dict()
    return search_df.iloc[0].to_dict() if not search_df.empty else None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type):
    boq_items = []
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        comp_spec = required_components[comp_key]
        category = comp_spec['category']
        matched_product = _strict_product_match(selection.get('name', 'N/A'), product_df, category)
        
        if matched_product:
            boq_items.append({
                'category': matched_product['category'], 'name': matched_product['name'], 'brand': matched_product['brand'],
                'quantity': selection.get('qty', comp_spec['quantity']), 'price': float(matched_product['price']),
                'justification': comp_spec['justification'], 'specifications': matched_product.get('features', ''),
                'image_url': matched_product.get('image_url', ''), 'gst_rate': matched_product.get('gst_rate', 18),
                'matched': True, 'power_draw': estimate_power_draw(matched_product['category'], matched_product['name'])
            })
        else:
            fallback_product = _get_fallback_product(category, product_df, comp_spec)
            if fallback_product:
                boq_items.append({
                    'category': fallback_product['category'], 'name': fallback_product['name'], 'brand': fallback_product['brand'],
                    'quantity': comp_spec['quantity'], 'price': float(fallback_product['price']),
                    'justification': comp_spec['justification'] + ' (auto-selected)', 'specifications': fallback_product.get('features', ''),
                    'image_url': fallback_product.get('image_url', ''), 'gst_rate': fallback_product.get('gst_rate', 18),
                    'matched': False, 'power_draw': estimate_power_draw(fallback_product['category'], fallback_product['name'])
                })
    if len(boq_items) < len(required_components):
        boq_items = _add_essential_missing_components(boq_items, product_df, required_components)
    return boq_items

# --- Post-Processing and Validation Functions ---
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

def _add_essential_missing_components(boq_items, product_df, required_components):
    boq_categories = {item['category'] for item in boq_items}
    missing_components = {k: v for k, v in required_components.items() if v['category'] not in boq_categories}

    for key, comp_spec in missing_components.items():
        st.warning(f"Auto-adding missing essential component: {key.replace('_', ' ').title()}")
        fallback = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if fallback:
            boq_items.append({
                'category': fallback['category'], 'name': fallback['name'], 'brand': fallback['brand'],
                'quantity': comp_spec['quantity'], 'price': float(fallback['price']),
                'justification': f"{comp_spec['justification']} (auto-added)", 'specifications': fallback.get('features', ''),
                'image_url': fallback.get('image_url', ''), 'gst_rate': fallback.get('gst_rate', 18),
                'matched': False, 'power_draw': estimate_power_draw(fallback['category'], fallback['name'])
            })
    return boq_items
    
def create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs):
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    fallback_items = []
    st.warning("Creating a smart fallback BOQ based on median product choices.")
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if product:
            fallback_items.append({
                'category': product['category'], 'name': product['name'], 'brand': product['brand'],
                'quantity': comp_spec['quantity'], 'price': float(product['price']),
                'justification': comp_spec['justification'], 'specifications': product.get('features', ''),
                'image_url': product.get('image_url', ''), 'gst_rate': product.get('gst_rate', 18),
                'matched': True, 'power_draw': estimate_power_draw(product['category'], product['name'])
            })
    return fallback_items

# --- Core AI Generation Function (MODIFIED) ---
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area, feature_tags):
    """The re-architected core function to get the BOQ from the AI."""
    global equipment_reqs  # Make it accessible to fallback functions
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    # --- NEW: Filter product catalog based on feature tags ---
    filtered_df = product_df.copy()
    if feature_tags:
        st.info(f"Applying feature filters: {', '.join(feature_tags)}")
        for tag in feature_tags:
            # Check in both feature and compatibility columns
            filtered_df = filtered_df[
                filtered_df['feature_tags'].str.contains(tag, na=False, case=False) |
                filtered_df['compatibility_tags'].str.contains(tag, na=False, case=False)
            ]
        if filtered_df.empty:
            st.warning("Filtering resulted in an empty product list. Using the full catalog to ensure a result.")
            filtered_df = product_df.copy()
        else:
            st.success(f"Filtered catalog to {len(filtered_df)} products.")
    # -----------------------------------------------------------

    required_components = _build_component_blueprint(equipment_reqs, room_type)
    
    prompt = _build_comprehensive_boq_prompt(
        room_type, room_area, avixa_calcs, equipment_reqs, 
        required_components, filtered_df, budget_tier, features
    )
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text: raise Exception("AI returned an empty response.")
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection: raise Exception("Failed to parse valid JSON from AI response.")
        
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, filtered_df, equipment_reqs, room_type)
        return boq_items, avixa_calcs, equipment_reqs
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}")
        fallback_items = create_smart_fallback_boq(filtered_df, room_type, equipment_reqs, avixa_calcs)
        return fallback_items, avixa_calcs, equipment_reqs
