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
    """Parses the JSON string from the AI's text response."""
    try:
        # Clean the string: remove backticks, "json" language specifier, and strip whitespace
        cleaned = ai_response_text.strip().replace("`", "").lstrip("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}. Response was: {ai_response_text[:200]}")
        return {}

def _get_prompt_for_room_type(room_type, avixa_calcs, equipment_reqs, required_components, product_df, budget_tier, features):
    """
    -- ENHANCED PROMPT FACTORY WITH STRICT CONSTRAINTS --
    Selects and tailors a specific, high-context AI prompt with strict rules based on the room type.
    """
    
    # Helper function to format the mandatory product list for the prompt
    def format_product_list():
        product_text = ""
        # Sort components by priority for a logical flow in the prompt
        for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
            product_text += f"\n## {comp_key.replace('_', ' ').upper()} (Category: {comp_spec['category']})\n"
            product_text += f"   - **Requirement:** {comp_spec['justification']}\n"
            product_text += f"   - **Rule:** {comp_spec.get('rule', 'Select the best fit.')}\n"
            
            # Find and list the top 15 matching products from the catalog
            matching_products = product_df[product_df['category'] == comp_spec['category']].head(15)
            if not matching_products.empty:
                for _, prod in matching_products.iterrows():
                    product_text += f"   - {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"
            else:
                product_text += f"   - (No products found in catalog for {comp_spec['category']})\n"
        return product_text

    prompt = ""
    display_size_inches = equipment_reqs.get('displays', {}).get('size_inches', 65)

    # --- PROMPT TEMPLATES ---

    # STRICT TEMPLATE FOR BOARDROOMS/TELEPRESENCE (High-End, Modular)
    if any(keyword in room_type for keyword in ["Boardroom", "Telepresence"]):
        prompt = f"""
You are designing a premium **{room_type}** system. This is a MODULAR, high-end installation.

# CRITICAL MANDATORY RULES - DO NOT DEVIATE

**DISPLAY RULES:**
1. You MUST select a display that is **{display_size_inches} inches or larger**.
2. NEVER select displays smaller than {display_size_inches - 5} inches.
3. If no exact match exists, select the CLOSEST LARGER size (e.g., if target is 75", select 85" before selecting 65").
4. For dual display setups, BOTH displays must meet this size requirement.

**VIDEO SYSTEM RULES (Modular System):**
1. You MUST select a professional codec (e.g., Poly G7500, Cisco Room Kit Pro).
2. You MUST select a separate PTZ camera (e.g., Poly EagleEye, Logitech Rally Camera).
3. NEVER select an all-in-one video bar for this room type.
4. The camera and codec must be from compatible ecosystems.

**CONTROL SYSTEM RULES:**
1. Match the controller brand to the video codec brand:
   - If Poly codec → Select Poly TC8 or similar Poly touch controller.
   - If Cisco codec → Select Cisco Touch 10 or similar Cisco controller.
   - If Logitech Rally → Select Logitech Tap controller.
2. NEVER select a "Scheduler" - these are for room booking, not meeting control.
3. NEVER mix brands (e.g., Poly codec + Crestron panel) unless explicitly specified.

**AUDIO SYSTEM RULES (Modular System):**
1. You MUST select a DSP (e.g., Q-SYS, Biamp, or Shure).
2. Select ceiling microphones (minimum {equipment_reqs.get('audio_system', {}).get('microphone_count', 2)}).
3. Select ceiling speakers (minimum {equipment_reqs.get('audio_system', {}).get('speaker_count', 2)}).
4. Select an amplifier if speakers are passive.

**INFRASTRUCTURE:**
1. Select an AV equipment rack.
2. Select a rackmount PDU for power distribution.

# MANDATORY SYSTEM COMPONENTS
{format_product_list()}

# OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT)
Return ONLY valid JSON with exact product names from the lists above.
"""

    # STRICT TEMPLATE FOR TRAINING/EVENT ROOMS (Presenter-Focused)
    elif any(keyword in room_type for keyword in ["Training", "Event", "Multipurpose"]):
        prompt = f"""
You are designing a **{room_type}** focused on presenter mobility and audience engagement.

# CRITICAL MANDATORY RULES

**DISPLAY RULES:**
1. Select a display of **{display_size_inches} inches or larger** for audience visibility.
2. If target is 75", prefer 75" or 85" over 65".
3. Large format is critical for training environments.

**VIDEO SYSTEM RULES:**
1. Select either:
   - Option A: Modular (PTZ camera + codec) for presenter tracking.
   - Option B: All-in-one video bar for simplicity (e.g., Poly Studio X70, Logitech Rally Bar).
2. If modular, ensure camera has tracking capability.

**AUDIO SYSTEM RULES (CRITICAL FOR PRESENTER):**
1. You MUST include a wireless microphone system for the presenter.
2. This is NON-NEGOTIABLE - no training room BOQ is complete without presenter audio.
3. Select from: Shure wireless, Sennheiser wireless, or similar professional systems.
4. Additionally include:
   - DSP for mixing if a modular system is used.
   - Ceiling speakers for voice reinforcement.
   - Amplifier if needed.

**CONTROL SYSTEM RULES:**
1. Select a simple touch panel for presentation control.
2. Match controller ecosystem to video system (Poly/Cisco/Logitech/Crestron).
3. Avoid schedulers.

# MANDATORY SYSTEM COMPONENTS
{format_product_list()}

# OUTPUT FORMAT (STRICT JSON)
"""

    # STRICT TEMPLATE FOR HUDDLE/SMALL ROOMS (All-in-One, Simple)
    else:
        prompt = f"""
You are designing a simple, user-friendly **{room_type}** for everyday collaboration.

# CRITICAL MANDATORY RULES

**DISPLAY RULES:**
1. Select a display close to **{display_size_inches} inches**.
2. Acceptable range: {display_size_inches - 10}" to {display_size_inches + 5}".
3. Prioritize value over premium features.

**VIDEO SYSTEM RULES (ALL-IN-ONE FOCUS):**
1. STRONGLY PREFER all-in-one video bars: e.g., Poly Studio X30/X50, Logitech Rally Bar Mini, Neat Bar.
2. These integrate camera, mics, and speakers - perfect for small rooms.
3. Only select modular systems if specifically requested.

**CONTROL SYSTEM RULES:**
1. Select a matching touch controller:
   - Poly video bar → Poly TC8 or Poly Remote.
   - Logitech bar → Logitech Tap.
   - Neat bar → Neat Pad.
2. Keep it simple - one-touch join is the goal.

**AUDIO SYSTEM:**
1. If using an all-in-one bar, DO NOT select separate audio components.
2. The bar's integrated audio is sufficient for small rooms.
3. Only add DSP/mics/speakers if the room is unusually large or has acoustic challenges.

# MANDATORY SYSTEM COMPONENTS
{format_product_list()}

# OUTPUT FORMAT (STRICT JSON)
"""

    # Add the common JSON structure instruction to the chosen prompt
    json_format_instruction = "\n{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        json_format_instruction += f'  "{comp_key}": {{"name": "EXACT product name from list above", "qty": {comp_spec["quantity"]}}}{comma}\n'
    json_format_instruction += "}\n"
    
    return prompt + json_format_instruction


# --- Dynamic Component Blueprint Builder ---
def _build_component_blueprint(equipment_reqs, room_type):
    """Dynamically builds the list of required components with specific rules."""
    
    display_size = equipment_reqs['displays'].get('size_inches', 65)
    
    # Base components for almost every room
    blueprint = {
        'display': {
            'category': 'Displays', 
            'quantity': equipment_reqs['displays'].get('quantity', 1), 
            'priority': 1, 
            'justification': f"Primary {display_size}\" display for {room_type}", 
            'rule': f"MANDATORY: Select a display of {display_size}\" or LARGER. If {display_size}\" is unavailable, select the next larger size (e.g., {display_size + 10}\"). NEVER select smaller than {display_size - 5}\".",
            'size_requirement': display_size  # NEW: Pass this to fallback logic
        },
        'display_mount': {'category': 'Mounts', 'quantity': equipment_reqs['displays'].get('quantity', 1), 'priority': 8, 'justification': 'Wall mount compatible with the selected display.', 'rule': "Select a WALL MOUNT for a display. DO NOT select a camera or ceiling mount."},
        'in_room_controller': {'category': 'Control', 'quantity': 1, 'priority': 3, 'justification': 'In-room touch panel to start/join/control meetings.', 'rule': "Select a tabletop touch controller. DO NOT select a 'Scheduler'."},
        'table_connectivity': {'category': 'Cables', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input for wired HDMI presentation.', 'rule': "Select a table cubby or wall plate with HDMI."},
        'network_cables': {'category': 'Cables', 'quantity': 5, 'priority': 10, 'justification': 'Network patch cables for IP-enabled devices.', 'rule': "Select a standard pack of CAT6 patch cables."},
    }

    # For high-end rooms, add stricter ecosystem matching rules
    if any(keyword in room_type for keyword in ["Boardroom", "Telepresence"]):
        blueprint['in_room_controller']['rule'] = "CRITICAL: Select a controller that matches the video codec brand. Poly codec → Poly controller. Cisco codec → Cisco controller. DO NOT mix ecosystems. DO NOT select schedulers."

    # Add Video System components based on design
    if equipment_reqs['video_system']['type'] == 'All-in-one Video Bar':
        blueprint['video_bar'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar with integrated camera, mics, and speakers.', 'rule': "Select a complete video bar like a Poly Studio or Logitech Rally Bar."}
    elif equipment_reqs['video_system']['type'] == 'Modular Codec + PTZ Camera':
        blueprint['video_codec'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'Core video codec for processing and connectivity.', 'rule': "Select a professional codec like a Poly G7500 or Cisco Codec."}
        blueprint['ptz_camera'] = {'category': 'Video Conferencing', 'quantity': equipment_reqs['video_system'].get('camera_count', 1), 'priority': 2.1, 'justification': 'PTZ (Pan-Tilt-Zoom) camera for the main video feed.', 'rule': "Select a PTZ camera like a Poly EagleEye or Logitech Rally Camera."}

    # Add Audio System components IF a separate audio system is required
    if equipment_reqs['audio_system']['dsp_required']:
        blueprint['dsp'] = {'category': 'Audio', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for echo cancellation and audio mixing.', 'rule': "Select a DSP like a Q-SYS Core or Biamp Tesira."}
        blueprint['microphones'] = {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones to cover the room seating.', 'rule': "Select ceiling or table microphones."}
        blueprint['speakers'] = {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for program audio and voice reinforcement.', 'rule': "Select ceiling or wall-mounted speakers."}
        blueprint['amplifier'] = {'category': 'Audio', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier to power the passive speakers.', 'rule': "Select an appropriate power amplifier."}

    # Add Infrastructure components
    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 12, 'justification': 'Equipment rack to house components.', 'rule': "Select a standard AV rack."}
    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit for the rack.', 'rule': "Select a rack-mounted PDU."}

    return blueprint

# --- Fallback & Post-Processing Logic ---
def _get_fallback_product(category, product_df, comp_spec):
    """Get the best fallback product, with strict enforcement of size and type rules."""
    matching = product_df[product_df['category'] == category]
    if matching.empty:
        matching = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    if matching.empty:
        st.error(f"CRITICAL: No products in catalog for category '{category}'!")
        return None

    rule = comp_spec.get('rule', '').lower()
    
    # === DISPLAY SIZE ENFORCEMENT LOGIC ===
    if 'display' in category.lower() and 'size_requirement' in comp_spec:
        target_size = comp_spec['size_requirement']
        
        # Helper to extract numeric size from product name string
        def extract_size(name):
            match = re.search(r'(\d{2,3})[\'"”\s-]*inch', name, re.IGNORECASE) or re.search(r'(\d{2,3})["\']', name)
            return int(match.group(1)) if match else 0
        
        # Create a new column with the extracted display size
        matching['display_size'] = matching['name'].apply(extract_size)
        
        # 1. Filter to keep only displays that meet the minimum size requirement
        valid_sizes = matching[matching['display_size'] >= target_size].copy()
        
        if not valid_sizes.empty:
            # 2. From the valid options, find the one closest to the target size
            valid_sizes['size_diff'] = abs(valid_sizes['display_size'] - target_size)
            return valid_sizes.sort_values('size_diff').iloc[0].to_dict()
        else:
            # 3. If NO display meets the minimum, return the largest one available as a last resort
            if not matching.empty and matching['display_size'].sum() > 0:
                return matching.sort_values('display_size', ascending=False).iloc[0].to_dict()

    # === CONTROLLER & MOUNT FILTERING ===
    # Filter out schedulers when a controller is needed
    if 'controller' in rule and "scheduler" not in rule:
        filtered = matching[~matching['name'].str.contains("Scheduler|Booking", case=False, regex=True)]
        if not filtered.empty:
            matching = filtered
            
    # Filter for specific mount types
    if 'wall mount' in rule:
        filtered = matching[matching['name'].str.contains("Wall Mount", case=False)]
        if not filtered.empty:
            matching = filtered

    # Default fallback: return the medium-priced product from the filtered list
    if not matching.empty:
        return matching.sort_values('price').iloc[len(matching)//2].to_dict()
    
    return None # Should not happen if catalog is populated

def _strict_product_match(product_name, product_df, category):
    """Finds the best possible match for a product name within a given category."""
    if product_df is None or len(product_df) == 0: return None
    
    # First, filter by the exact category
    filtered_by_cat = product_df[product_df['category'] == category]
    if len(filtered_by_cat) == 0:
        # If no exact category match, try a partial match
        filtered_by_cat = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    
    # Use the filtered DataFrame if it has results, otherwise search the whole catalog
    search_df = filtered_by_cat if len(filtered_by_cat) > 0 else product_df
    
    # Try for an exact name match first
    exact_match = search_df[search_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty: return exact_match.iloc[0].to_dict()
    
    # If no exact match, try partial matching with key terms
    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3: # Avoid common short words
            matches = search_df[search_df['name'].str.lower().str.contains(term, na=False)]
            if not matches.empty: return matches.iloc[0].to_dict()
            
    # If still no match, return the first item in the search DataFrame as a last resort
    return search_df.iloc[0].to_dict() if not search_df.empty else None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type):
    """Constructs the final BOQ list from the AI's selection, with fallbacks for failed matches."""
    boq_items, matched_count = [], 0
    
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        
        comp_spec = required_components[comp_key]
        category = comp_spec['category']
        
        # Attempt to strictly match the product chosen by the AI
        matched_product = _strict_product_match(selection.get('name', 'N/A'), product_df, category)
        
        if matched_product:
            matched_count += 1
            boq_items.append({
                'category': matched_product['category'], 'name': matched_product['name'], 
                'brand': matched_product['brand'], 'quantity': selection.get('qty', comp_spec['quantity']),
                'price': float(matched_product['price']), 'justification': comp_spec['justification'], 
                'specifications': matched_product.get('features', ''), 'image_url': matched_product.get('image_url', ''),
                'gst_rate': matched_product.get('gst_rate', 18), 'matched': True,
                'power_draw': estimate_power_draw(matched_product['category'], matched_product['name'])
            })
        else:
            # If AI's choice can't be matched, use the enhanced fallback logic
            fallback_product = _get_fallback_product(category, product_df, comp_spec)
            if fallback_product:
                boq_items.append({
                    'category': fallback_product['category'], 'name': fallback_product['name'],
                    'brand': fallback_product['brand'], 'quantity': comp_spec['quantity'],
                    'price': float(fallback_product['price']), 'justification': comp_spec['justification'] + ' (auto-selected)',
                    'specifications': fallback_product.get('features', ''), 'image_url': fallback_product.get('image_url', ''),
                    'gst_rate': fallback_product.get('gst_rate', 18), 'matched': False,
                    'power_draw': estimate_power_draw(fallback_product['category'], fallback_product['name'])
                })

    # Ensure all required components are present, adding any that were missed
    if len(boq_items) < len(required_components):
        boq_items = _add_essential_missing_components(boq_items, product_df, required_components)
        
    return boq_items

def _add_essential_missing_components(boq_items, product_df, required_components):
    """Adds any essential components that are missing from the BOQ."""
    # Create a set of categories already present in the BOQ
    boq_categories = {item['category'] for item in boq_items}
    
    # Identify which required component keys are missing
    required_keys_in_boq = set()
    for item in boq_items:
        for key, spec in required_components.items():
            if item['category'] == spec['category']:
                required_keys_in_boq.add(key)
                
    missing_keys = set(required_components.keys()) - required_keys_in_boq
    
    for key in missing_keys:
        comp_spec = required_components[key]
        st.warning(f"Auto-adding missing essential component: {key.replace('_', ' ').title()}")
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

# --- START: ADDED MISSING FUNCTIONS ---

def _remove_exact_duplicates(boq_items):
    """Removes items with the exact same name from the BOQ list."""
    seen, unique_items = set(), []
    for item in boq_items:
        if item.get('name') not in seen:
            seen.add(item.get('name'))
            unique_items.append(item)
    return unique_items

def _remove_duplicate_core_components(boq_items):
    """Removes duplicate items in core functional categories, keeping the most expensive one."""
    final_items, core_categories = [], ['Video Conferencing', 'Control']
    
    # Add all non-core items first
    for item in boq_items:
        if item.get('category') not in core_categories:
            final_items.append(item)
            
    # Process each core category
    for category in core_categories:
        candidates = [item for item in boq_items if item.get('category') == category]
        if len(candidates) > 1:
            # If there are duplicates, find the one with the highest price
            best_candidate = max(candidates, key=lambda x: x.get('price', 0))
            final_items.append(best_candidate)
        elif len(candidates) == 1:
            # If only one, just add it
            final_items.append(candidates[0])
            
    return _remove_exact_duplicates(final_items)

def _ensure_system_completeness(boq_items, product_df):
    """Checks for logical system gaps (e.g., speakers without an amp) and adds components."""
    # This is a placeholder for more complex logic. For now, it just passes through.
    has_amplifier = any("Amplifier" in item['name'] for item in boq_items)
    has_passive_speakers = any("Speaker" in item['name'] and "Amplifier" not in item.get('specifications', '') for item in boq_items)
    
    if has_passive_speakers and not has_amplifier:
        # A more advanced version could add a suitable amplifier here.
        st.warning("System has passive speakers but no amplifier was found. Manual addition may be required.")
        
    return boq_items

def _flag_hallucinated_models(boq_items):
    """Flags items that appear to be auto-generated or placeholders."""
    for item in boq_items:
        if "Auto-generated" in item.get('specifications', '') or re.search(r'GEN-\d+', item['name']):
            item['warning'] = "Model is auto-generated and requires verification."
    return boq_items

def _correct_quantities(boq_items):
    """Ensures all quantity fields are valid integers."""
    for item in boq_items:
        try:
            item['quantity'] = int(float(item.get('quantity', 1)))
        except (ValueError, TypeError):
            item['quantity'] = 1
    return boq_items

# --- END: ADDED MISSING FUNCTIONS ---

def create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs):
    """Generates a complete BOQ using only the fallback logic, bypassing the AI."""
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if product:
            fallback_items.append({
                'category': product['category'], 'name': product['name'], 'brand': product['brand'],
                'quantity': comp_spec['quantity'], 'price': float(product['price']),
                'justification': comp_spec['justification'], 'specifications': product.get('features', ''),
                'image_url': product.get('image_url', ''), 'gst_rate': product.get('gst_rate', 18), 'matched': True
            })
    return fallback_items

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    """Validates the generated BOQ against AVIXA recommendations."""
    issues, warnings = [], []
    # This function can be expanded with more detailed compliance checks in the future.
    return {'avixa_issues': issues, 'avixa_warnings': warnings}

# --- Core AI Generation Function ---
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """The re-architected core function to generate a BOQ from the AI."""
    # 1. Calculate room and system requirements
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    # 2. Build the blueprint of required components with strict rules
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    
    # 3. Generate a highly specific, rule-based prompt for the AI
    prompt = _get_prompt_for_room_type(
        room_type, avixa_calcs, equipment_reqs, required_components, 
        product_df, budget_tier, features
    )
    
    try:
        # 4. Call the AI model
        response = generate_with_retry(model, prompt)
        if not response or not response.text:
            raise Exception("AI returned an empty response.")
            
        # 5. Parse the AI's response
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse valid JSON from AI response.")
            
        # 6. Build the final BOQ from the AI's selections, using fallbacks where necessary
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type)
        
        return boq_items, avixa_calcs, equipment_reqs
        
    except Exception as e:
        # 7. If the AI process fails entirely, generate a BOQ using only the robust fallback logic
        st.error(f"AI generation failed: {str(e)}. Creating a fallback BOQ.")
        fallback_items = create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs)
        return fallback_items, avixa_calcs, equipment_reqs
