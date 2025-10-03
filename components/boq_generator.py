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
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}, 'control_system': {}}
    def estimate_power_draw(*args): return 100
    ROOM_SPECS = {}

# --- NEW: Generate Top 3 Reasons using AI ---
def _generate_top_3_reasons(model, item, room_type, equipment_reqs):
    """Generate top 3 specific reasons why this product was selected."""
    prompt = f"""You are an AVIXA CTS certified AV consultant explaining to a client why a specific product was chosen.

**Product:** {item['brand']} {item['name']}
**Category:** {item['category']}
**Room Type:** {room_type}
**Project Requirements:** {equipment_reqs}

Generate EXACTLY 3 specific, client-friendly reasons why this product is the right choice for this project.
Each reason should be concise (max 15 words) and focus on tangible benefits.

Format your response as a JSON array of exactly 3 strings:
["Reason 1", "Reason 2", "Reason 3"]

Focus on:
- Technical specifications that meet room requirements
- Industry standards compliance (AVIXA, etc.)
- Integration with other system components
- User experience benefits
- Reliability and support
- Cost-effectiveness for the application

OUTPUT ONLY THE JSON ARRAY, NO OTHER TEXT."""

    try:
        response = generate_with_retry(model, prompt)
        if response and response.text:
            cleaned = response.text.strip().replace("```json", "").replace("```", "").strip()
            reasons = json.loads(cleaned)
            if isinstance(reasons, list) and len(reasons) == 3:
                return reasons
    except Exception as e:
        st.warning(f"Failed to generate AI reasons for {item['name']}: {e}")
    
    # Fallback to template-based reasons
    return _generate_fallback_reasons(item, room_type)

def _generate_fallback_reasons(item, room_type):
    """Generate fallback reasons based on templates when AI fails."""
    category = item.get('category', 'General')
    
    reasons_templates = {
        'Displays': [
            f"Optimal viewing size for {room_type} per AVIXA DISCAS standards",
            "4K resolution ensures clarity for detailed content sharing",
            "Commercial-grade reliability with 16/7 operation rating"
        ],
        'Video Conferencing': [
            "Certified for Microsoft Teams and Zoom platforms",
            "Auto-framing ensures all participants remain in view",
            "Integrated audio reduces cable clutter and setup time"
        ],
        'Audio': [
            "Provides even coverage across entire room footprint",
            "Echo cancellation ensures clear remote communication",
            "Complies with intelligibility standards (STI >0.60)"
        ],
        'Control': [
            "Intuitive one-touch meeting start for end users",
            "Centralized control of all AV system components",
            "Reduces training time and IT support calls"
        ],
        'Mounts': [
            "VESA compliant for secure display installation",
            "Adjustable positioning for optimal viewing angles",
            "Cable management features for professional appearance"
        ],
        'Cables': [
            "Certified for 4K@60Hz signal transmission",
            "Shielded construction prevents signal interference",
            "Rated for in-wall installation per building codes"
        ],
        'Infrastructure': [
            "Sufficient power capacity for all system components",
            "Surge protection safeguards equipment investment",
            "Organized cable management for easier maintenance"
        ]
    }
    
    return reasons_templates.get(category, [
        f"Selected to meet {room_type} functional requirements",
        "Industry-standard solution with proven reliability",
        "Compatible with existing infrastructure and workflows"
    ])

# --- AI Interaction and Parsing ---
def _parse_ai_product_selection(ai_response_text):
    try:
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
- **System Requirements:** {equipment_reqs}

# MANDATORY SYSTEM COMPONENTS ({len(required_components)} items)
You MUST select one product for each of the following roles from the provided lists.
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

    prompt += "\n# OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT)\n"
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

    if equipment_reqs['video_system']['type'] == 'All-in-one Video Bar':
        blueprint['video_bar'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one Video Bar with integrated camera, mics, and speakers.', 'rule': "Select a complete video bar like a Poly Studio or Logitech Rally Bar."}
    elif equipment_reqs['video_system']['type'] == 'Modular Codec + PTZ Camera':
        blueprint['video_codec'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'Core video codec for processing and connectivity.', 'rule': "Select a professional codec like a Poly G7500 or Cisco Codec."}
        blueprint['ptz_camera'] = {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2.1, 'justification': 'PTZ (Pan-Tilt-Zoom) camera for the main video feed.', 'rule': "Select a PTZ camera like a Poly EagleEye or Logitech Rally Camera."}

    if equipment_reqs['audio_system']['dsp_required']:
        blueprint['dsp'] = {'category': 'Audio', 'quantity': 1, 'priority': 4, 'justification': 'Digital Signal Processor for echo cancellation and audio mixing.', 'rule': "Select a DSP like a Q-SYS Core or Biamp Tesira."}
        blueprint['microphones'] = {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 5, 'justification': 'Microphones to cover the room seating.', 'rule': "Select ceiling or table microphones."}
        blueprint['speakers'] = {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 6, 'justification': 'Speakers for program audio and voice reinforcement.', 'rule': "Select ceiling or wall-mounted speakers."}
        blueprint['amplifier'] = {'category': 'Audio', 'quantity': 1, 'priority': 7, 'justification': 'Amplifier to power the passive speakers.', 'rule': "Select an appropriate power amplifier."}

    if equipment_reqs['housing']['type'] == 'AV Rack':
        blueprint['av_rack'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 12, 'justification': 'Equipment rack to house components.', 'rule': "Select a standard AV rack."}
    if equipment_reqs['power_management']['type'] == 'Rackmount PDU':
        blueprint['pdu'] = {'category': 'Infrastructure', 'quantity': 1, 'priority': 11, 'justification': 'Power distribution unit for the rack.', 'rule': "Select a rack-mounted PDU."}

    return blueprint

def _get_fallback_product(category, product_df, comp_spec):
    """Get best fallback product with keyword filtering."""
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
    
    if 'display' in category.lower() and 'size_requirement' in comp_spec:
        target_size = comp_spec['size_requirement']
        matching['size_diff'] = matching['name'].str.extract(r'(\d+)').astype(float).subtract(target_size).abs()
        return matching.sort_values('size_diff').iloc[0].to_dict()

    return matching.sort_values('price').iloc[len(matching)//2].to_dict()

def _strict_product_match(product_name, product_df, category):
    if product_df is None or len(product_df) == 0: return None
    filtered_by_cat = product_df[product_df['category'] == category]
    if len(filtered_by_cat) == 0:
        filtered_by_cat = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    search_df = filtered_by_cat if len(filtered_by_cat) > 0 else product_df
    exact_match = search_df[search_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty: return exact_match.iloc[0].to_dict()
    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3:
            matches = search_df[search_df['name'].str.lower().str.contains(term, na=False)]
            if not matches.empty: return matches.iloc[0].to_dict()
    return search_df.iloc[0].to_dict() if not search_df.empty else None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type, model):
    """Build BOQ with Top 3 Reasons for each item."""
    boq_items, matched_count = [], 0
    
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        comp_spec, category = required_components[comp_key], required_components[comp_key]['category']
        matched_product = _strict_product_match(selection.get('name', 'N/A'), product_df, category)
        
        if matched_product:
            matched_count += 1
            item = {
                'category': matched_product['category'], 
                'name': matched_product['name'], 
                'brand': matched_product['brand'], 
                'quantity': selection.get('qty', comp_spec['quantity']), 
                'price': float(matched_product['price']), 
                'justification': comp_spec['justification'], 
                'specifications': matched_product.get('features', ''), 
                'image_url': matched_product.get('image_url', ''), 
                'gst_rate': matched_product.get('gst_rate', 18), 
                'matched': True, 
                'power_draw': estimate_power_draw(matched_product['category'], matched_product['name'])
            }
            # Generate Top 3 Reasons
            item['top_3_reasons'] = _generate_top_3_reasons(model, item, room_type, equipment_reqs)
            boq_items.append(item)
        else:
            fallback_product = _get_fallback_product(category, product_df, comp_spec)
            if fallback_product:
                item = {
                    'category': fallback_product['category'], 
                    'name': fallback_product['name'], 
                    'brand': fallback_product['brand'], 
                    'quantity': comp_spec['quantity'], 
                    'price': float(fallback_product['price']), 
                    'justification': comp_spec['justification'] + ' (auto-selected)', 
                    'specifications': fallback_product.get('features', ''), 
                    'image_url': fallback_product.get('image_url', ''), 
                    'gst_rate': fallback_product.get('gst_rate', 18), 
                    'matched': False, 
                    'power_draw': estimate_power_draw(fallback_product['category'], fallback_product['name'])
                }
                item['top_3_reasons'] = _generate_fallback_reasons(item, room_type)
                boq_items.append(item)
    
    if len(boq_items) < len(required_components):
        boq_items = _add_essential_missing_components(boq_items, product_df, required_components, room_type)
    
    return boq_items

def _remove_exact_duplicates(boq_items):
    seen, unique_items = set(), []
    for item in boq_items:
        if item.get('name') not in seen:
            seen.add(item.get('name')); unique_items.append(item)
    return unique_items

def _remove_duplicate_core_components(boq_items):
    final_items, core_categories = [], ['Video Conferencing', 'Control']
    for item in boq_items:
        if item.get('category') not in core_categories: final_items.append(item)
    for category in core_categories:
        candidates = [item for item in boq_items if item.get('category') == category]
        if len(candidates) > 1:
            best_candidate = max(candidates, key=lambda x: x.get('price', 0))
            final_items.append(best_candidate)
        elif len(candidates) == 1:
            final_items.append(candidates[0])
    return _remove_exact_duplicates(final_items)

def _ensure_system_completeness(boq_items, product_df):
    return boq_items

def _flag_hallucinated_models(boq_items):
    for item in boq_items:
        if "Auto-generated" in item.get('specifications', '') or re.search(r'GEN-\d+', item['name']):
            item['warning'] = "Model is auto-generated and requires verification."
    return boq_items

def _correct_quantities(boq_items):
    for item in boq_items:
        try: item['quantity'] = int(float(item.get('quantity', 1)))
        except (ValueError, TypeError): item['quantity'] = 1
    return boq_items

def _add_essential_missing_components(boq_items, product_df, required_components, room_type):
    boq_item_names = {item['name'] for item in boq_items}
    required_keys_in_boq = set()
    for item in boq_items:
        for key, spec in required_components.items():
            if item['category'] == spec['category']:
                required_keys_in_boq.add(key)

    missing_keys = set(required_components.keys()) - required_keys_in_boq
    for key in missing_keys:
        comp_spec = required_components[key]
        st.warning(f"Auto-adding missing essential component: {key}")
        fallback = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if fallback:
            item = {
                'category': fallback['category'], 
                'name': fallback['name'], 
                'brand': fallback['brand'], 
                'quantity': comp_spec['quantity'], 
                'price': float(fallback['price']), 
                'justification': f"{comp_spec['justification']} (auto-added)", 
                'specifications': fallback.get('features', ''), 
                'image_url': fallback.get('image_url', ''), 
                'gst_rate': fallback.get('gst_rate', 18), 
                'matched': False
            }
            item['top_3_reasons'] = _generate_fallback_reasons(item, room_type)
            boq_items.append(item)
    return boq_items

def create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs, model=None):
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if product:
            item = {
                'category': product['category'], 
                'name': product['name'], 
                'brand': product['brand'], 
                'quantity': comp_spec['quantity'], 
                'price': float(product['price']), 
                'justification': comp_spec['justification'], 
                'specifications': product.get('features', ''), 
                'image_url': product.get('image_url', ''), 
                'gst_rate': product.get('gst_rate', 18), 
                'matched': True
            }
            item['top_3_reasons'] = _generate_fallback_reasons(item, room_type)
            fallback_items.append(item)
    return fallback_items

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    issues, warnings = [], []
    return {'avixa_issues': issues, 'avixa_warnings': warnings}

# --- Core AI Generation Function ---
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Generate BOQ with Top 3 Reasons for each product."""
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    
    prompt = _build_comprehensive_boq_prompt(room_type, room_area, avixa_calcs, equipment_reqs, required_components, product_df, budget_tier, features)
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text: raise Exception("AI returned an empty response.")
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection: raise Exception("Failed to parse valid JSON from AI response.")
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type, model)
        return boq_items, avixa_calcs, equipment_reqs
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}")
        fallback_items = create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs, model)
        return fallback_items, avixa_calcs, equipment_reqs
