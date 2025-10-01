import streamlit as st
import pandas as pd
import re
import json
import time
import math

# --- Component Imports ---
try:
    from components.gemini_handler import generate_with_retry
    from components.utils import estimate_power_draw
except ImportError as e:
    st.error(f"BOQ Generator failed to import a component: {e}")
    # Define dummy functions to prevent crashes if components are missing
    def generate_with_retry(model, prompt): return None
    def estimate_power_draw(*args): return 100

# --- AI Interaction and Parsing ---
def _parse_ai_product_selection(ai_response_text):
    """
    Parses the JSON output from the AI, cleaning it of markdown formatting.
    """
    try:
        # Clean the string from potential markdown code fences and 'json' identifiers
        cleaned = ai_response_text.strip().replace("`", "").lstrip("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON response: {e}. Response snippet: {ai_response_text[:200]}")
        return {}

def _build_comprehensive_boq_prompt(room_type, room_area, equipment_reqs, required_components, product_df, budget_tier, features):
    """
    Builds the detailed prompt for the AI to select products for the BOQ.
    This version is adapted to use the new guideline-driven equipment_reqs.
    """
    prompt = f"""You are an AVIXA CTS-D certified AV system designer. Your task is to create a complete, logical, and standards-compliant Bill of Quantities (BOQ).

# PROJECT BRIEF
- **Room Type:** {room_type}
- **Budget Tier:** {budget_tier}
- **Client Needs:** {features if features else 'Standard functionality for this room type.'}
- **System Requirements:** {equipment_reqs}

# MANDATORY SYSTEM COMPONENTS ({len(required_components)} items)
You MUST select one product for each of the following roles from the provided product lists.
"""
    # Sort components by priority for a logical prompt flow
    for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
        prompt += f"\n## {comp_key.replace('_', ' ').upper()} (Category: {comp_spec['category']})\n"
        prompt += f"   - **Requirement:** {comp_spec['justification']}\n"
        prompt += f"   - **Rule:** {comp_spec.get('rule', 'Select the best fit.')}\n"
        
        # Find and list matching products from the catalog
        matching_products = product_df[product_df['category'] == comp_spec['category']].head(15)
        if not matching_products.empty:
            for _, prod in matching_products.iterrows():
                prompt += f"   - {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"
        else:
            prompt += f"   - (No products found in catalog for {comp_spec['category']})\n"

    # Define the strict JSON output format
    prompt += "\n# OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT)\n"
    prompt += "{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        prompt += f'  "{comp_key}": {{"name": "EXACT product name from list", "qty": {comp_spec["quantity"]}}}{comma}\n'
    prompt += "}\n"
    return prompt

# --- NEW: Guideline-Driven Component Blueprint Builder ---
def _build_component_blueprint_from_guidelines(system_reqs, room_area):
    """
    Dynamically builds the list of required components based on the parsed system requirements from guidelines.
    """
    blueprint = {}
    priority_counter = 1

    # Display Components
    if 'display' in system_reqs:
        display_req = system_reqs['display']
        qty = display_req.get('quantity', 1)
        blueprint['display'] = {'category': 'Displays', 'quantity': qty, 'priority': priority_counter, 'justification': "Primary display for the room."}
        priority_counter += 1
        blueprint['display_mount'] = {'category': 'Mounts', 'quantity': qty, 'priority': priority_counter + 7, 'justification': 'Wall mount compatible with the selected display.', 'rule': "Select a WALL MOUNT. Do not select a camera or ceiling mount."}

    # Video Conferencing Components
    if 'video' in system_reqs:
        video_req = system_reqs['video']
        if video_req.get('system_type') == 'All-in-one Video Bar':
            blueprint['video_bar'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': priority_counter, 'justification': 'All-in-one Video Bar with integrated camera, mics, and speakers.'}
        elif video_req.get('system_type') == 'Modular Codec + PTZ Camera':
            blueprint['video_codec'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': priority_counter, 'justification': 'Core video codec for processing and connectivity.'}
            blueprint['ptz_camera'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': priority_counter + 0.1, 'justification': 'PTZ (Pan-Tilt-Zoom) camera for the main video feed.'}
        priority_counter += 1

    # Audio Components
    if 'audio' in system_reqs and system_reqs['audio'].get('dsp_required'):
        audio_req = system_reqs['audio']
        blueprint['dsp'] = {'category': 'Audio', 'quantity': 1, 'priority': priority_counter, 'justification': 'Digital Signal Processor for audio routing and echo cancellation.'}
        
        # Safely evaluate speaker count formula from guidelines
        try:
            speaker_count = math.ceil(eval(audio_req['speaker_count_formula'], {"area_sqft": room_area, "math": math, "max": max, "ceil": math.ceil}))
        except:
            speaker_count = 4 # Default fallback
            
        blueprint['speakers'] = {'category': 'Audio', 'quantity': speaker_count, 'priority': priority_counter + 2, 'justification': 'Ceiling speakers for even audio coverage.'}
        blueprint['amplifier'] = {'category': 'Audio', 'quantity': 1, 'priority': priority_counter + 1, 'justification': 'Amplifier to power the passive speakers.'}
        priority_counter += 3

    # Control & Infrastructure Components
    if 'control' in system_reqs:
        blueprint['in_room_controller'] = {'category': 'Control', 'quantity': 1, 'priority': priority_counter, 'justification': 'In-room touch panel for meeting control.', 'rule': "Select a tabletop touch controller. DO NOT select a 'Scheduler'."}
    
    if 'infrastructure' in system_reqs:
        infra_req = system_reqs['infrastructure']
        if infra_req.get('rack_required'):
            blueprint['av_rack'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': priority_counter + 10, 'justification': 'Equipment rack to house components.'}
        if infra_req.get('power_management_type') == 'Rackmount PDU':
            blueprint['pdu'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': priority_counter + 9, 'justification': 'Power distribution unit for the rack.'}

    return blueprint

# --- Product Matching and Fallback Logic ---
def _get_fallback_product(category, product_df, comp_spec):
    """
    Finds the best possible fallback product for a given category, with keyword filtering for accuracy.
    """
    matching = product_df[product_df['category'] == category]
    if matching.empty:
        st.error(f"CRITICAL: No products found in catalog for category '{category}'!")
        return None

    # Apply keyword filtering from component rules to prevent mismatches
    rule = comp_spec.get('rule', '').lower()
    if 'wall mount' in rule:
        filtered = matching[matching['name'].str.contains("Wall Mount", case=False)]
        if not filtered.empty: matching = filtered
    if 'controller' in rule and "scheduler" not in rule:
        filtered = matching[~matching['name'].str.contains("Scheduler", case=False)]
        if not filtered.empty: matching = filtered
    
    # Return a mid-range product as a safe default
    return matching.sort_values('price').iloc[len(matching)//2].to_dict()

def _strict_product_match(product_name, product_df, category):
    """
    Attempts to find an exact or close match for a product name within a specific category.
    """
    if product_df is None or len(product_df) == 0: return None
    
    # First, filter by the exact category
    search_df = product_df[product_df['category'] == category]
    if search_df.empty:
        # If no exact category match, try a broader search (less ideal)
        search_df = product_df[product_df['category'].str.contains(category, case=False, na=False)]
        if search_df.empty: search_df = product_df

    # Attempt an exact name match (case-insensitive)
    exact_match = search_df[search_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty:
        return exact_match.iloc[0].to_dict()

    # Attempt a partial match using the first few words of the product name
    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3: # Avoid common short words
            matches = search_df[search_df['name'].str.lower().str.contains(term, na=False)]
            if not matches.empty:
                return matches.iloc[0].to_dict() # Return the first partial match
                
    return None # No reliable match found

def _build_boq_from_ai_selection(ai_selection, required_components, product_df):
    """
    Constructs the BOQ list by matching AI selections to the product catalog and using fallbacks.
    """
    boq_items = []
    
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components:
            continue
            
        comp_spec = required_components[comp_key]
        category = comp_spec['category']
        
        # Try to find the product the AI selected
        matched_product = _strict_product_match(selection.get('name', 'N/A'), product_df, category)
        
        product_to_add = None
        was_matched = False
        
        if matched_product:
            product_to_add = matched_product
            was_matched = True
        else:
            # If AI selection fails, get a safe fallback product
            product_to_add = _get_fallback_product(category, product_df, comp_spec)
        
        if product_to_add:
            boq_items.append({
                'category': product_to_add['category'],
                'name': product_to_add['name'],
                'brand': product_to_add['brand'],
                'quantity': selection.get('qty', comp_spec.get('quantity', 1)),
                'price': float(product_to_add['price']),
                'justification': comp_spec['justification'] + (' (auto-selected)' if not was_matched else ''),
                'specifications': product_to_add.get('features', ''),
                'image_url': product_to_add.get('image_url', ''),
                'gst_rate': product_to_add.get('gst_rate', 18),
                'matched': was_matched,
                'power_draw': estimate_power_draw(product_to_add['category'], product_to_add['name'])
            })
            
    return boq_items

# --- NEW: Intelligent, Guideline-Driven AVIXA Compliance Validation ---
def validate_avixa_compliance(boq_items, room_archetype, technical_reqs, guidelines_config):
    """
    Uses the parsed YAML rules from guidelines to programmatically validate the generated BOQ.
    """
    issues, warnings = [], []
    if not room_archetype or 'validation_rules' not in room_archetype:
        return {'avixa_issues': ["Could not find validation rules for this room type."], 'avixa_warnings': []}

    validation_rules = room_archetype['validation_rules']
    total_power_draw = sum(item.get('power_draw', 0) * item.get('quantity', 1) for item in boq_items)
    
    for rule_text in validation_rules:
        rule_lower = rule_text.lower()
        
        # Power Draw Check
        if "power draw" in rule_lower and "circuit" in rule_lower:
            power_margin = guidelines_config.get('global_rules', {}).get('power_capacity_margin', 0.8)
            # Example check for a 20A circuit (can be expanded)
            if "20a" in room_archetype.get('system_requirements', {}).get('infrastructure', {}).get('dedicated_circuit_recommended', '').lower():
                max_power = 20 * 120 * power_margin  # P = I * V * margin (assuming 120V)
                if total_power_draw > max_power:
                    issues.append(f"Power Violation: Total estimated power draw ({total_power_draw}W) exceeds the recommended {power_margin*100}% limit for a 20A circuit ({max_power:.0f}W).")
        
        # Required Component Check
        if "must contain" in rule_lower:
            if "dsp" in rule_lower:
                if not any("dsp" in item.get('name', '').lower() or "processor" in item.get('name', '').lower() for item in boq_items if item.get('category') == 'Audio'):
                    issues.append("Missing Component: BOQ requires a Digital Signal Processor (DSP) for this room size, but none was found.")
            if "assistive listening" in rule_lower and technical_reqs.get('ada_compliance'):
                if not any(item.get('category') == 'Assistive Listening' for item in boq_items):
                    issues.append("ADA Compliance Issue: Project requires an Assistive Listening System, but none was found in the BOQ.")

        # Warnings and Recommendations
        if "warn:" in rule_lower or "should include" in rule_lower:
            if "acoustic treatment" in rule_lower:
                warnings.append("Recommendation: Consider adding Acoustic Treatment panels to manage reverb, especially if the room has hard surfaces like glass or concrete.")

    return {'avixa_issues': issues, 'avixa_warnings': warnings}

# --- REVISED: Core AI Generation and Fallback Function ---
def create_smart_fallback_boq(product_df, room_type, equipment_reqs, room_area):
    """
    Creates a BOQ using fallback logic without calling the AI.
    This is a safety net for when the AI generation fails.
    """
    required_components = _build_component_blueprint_from_guidelines(equipment_reqs, room_area)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if product:
            fallback_items.append({
                'category': product['category'], 
                'name': product['name'], 
                'brand': product['brand'], 
                'quantity': comp_spec['quantity'], 
                'price': float(product['price']), 
                'justification': comp_spec['justification'] + ' (fallback)', 
                'specifications': product.get('features', ''), 
                'image_url': product.get('image_url', ''), 
                'gst_rate': product.get('gst_rate', 18), 
                'matched': False,
                'power_draw': estimate_power_draw(product['category'], product['name'])
            })
    return fallback_items

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """
    The re-architected core function that uses the parsed guidelines to generate a BOQ.
    """
    # Find the correct room archetype from the parsed guidelines file
    room_archetype = next((r for r in guidelines.get('room_archetypes', []) if r.get('name') == room_type), None)
    if not room_archetype:
        st.error(f"Could not find design rules for room type: '{room_type}'. Please check guidelines file.")
        return [], {}, {}
    
    equipment_reqs = room_archetype.get('system_requirements', {})
    required_components = _build_component_blueprint_from_guidelines(equipment_reqs, room_area)
    
    prompt = _build_comprehensive_boq_prompt(room_type, room_area, equipment_reqs, required_components, product_df, budget_tier, features)
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text:
            raise Exception("AI returned an empty or invalid response.")
        
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
            raise Exception("Failed to parse valid JSON from AI response.")
            
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df)
        
        return boq_items, room_archetype, equipment_reqs
        
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}. Generating a fallback BOQ based on standard rules.")
        # Generate a fallback BOQ if the AI fails
        fallback_items = create_smart_fallback_boq(product_df, room_type, equipment_reqs, room_area)
        return fallback_items, room_archetype, equipment_reqs
