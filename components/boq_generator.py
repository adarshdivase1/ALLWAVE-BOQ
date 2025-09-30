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

# --- MOVED OUTSIDE THE EXCEPT BLOCK ---
def _validate_product_type(product, expected_type):
    """
    Returns True only if the product name actually matches the expected type.
    This prevents selecting accessories when we need core equipment.
    """
    name_lower = product.get('name', '').lower()
    
    validation_rules = {
        'display': {
            'required': ['display', 'monitor', 'screen', 'tv'],
            'forbidden': ['mount', 'bracket', 'cable', 'adapter', 'stand alone']
        },
        'mount': {
            'required': ['mount', 'bracket'],
            'forbidden': ['camera mount', 'shelf']
        },
        'video_bar': {
            'required': ['bar', 'rally bar', 'studio', 'meetup'],
            'forbidden': ['camera', 'codec', 'mount']
        },
        'codec': {
            'required': ['codec', 'roommate', 'sx80'],
            'forbidden': ['camera', 'bar']
        },
        'camera': {
            'required': ['camera', 'ptz'],
            'forbidden': ['mount', 'shelf', 'bracket']
        },
        'microphone': {
            'required': ['mic', 'microphone'],
            'forbidden': ['cable', 'adapter', 'stand']
        },
        'speaker': {
            'required': ['speaker', 'loudspeaker'],
            'forbidden': ['cable', 'mount', 'bracket']
        },
        'touch_panel': {
            'required': ['touch', 'panel', 'controller'],
            'forbidden': ['scheduler', 'processor']
        },
        'rack': {
            'required': ['rack', 'enclosure', 'cabinet'],
            'forbidden': ['shelf', 'plate', 'mount']
        },
    }
    
    if expected_type not in validation_rules:
        return True
    
    rules = validation_rules[expected_type]
    
    # Must have at least one required keyword
    has_required = any(req in name_lower for req in rules['required'])
    # Must NOT have any forbidden keywords
    has_forbidden = any(forb in name_lower for forb in rules['forbidden'])
    
    return has_required and not has_forbidden

def _perform_engineering_validation(boq_items, product_df):
    """
    Performs basic engineering checks like rack space and power load.
    """
    warnings = []
    rack_items = []
    for item in boq_items:
        if item['category'] in ['Audio', 'Video Conferencing', 'Infrastructure']:
            rack_items.append({'name': item['name'], 'rack_units': item.get('rack_units', 1)})
            
    rack_container = next((item for item in boq_items if 'Rack' in item.get('name')), None)
    
    if rack_items and rack_container:
        total_ru = sum(item['rack_units'] for item in rack_items)
        rack_size_match = re.search(r'(\d+)U', rack_container['name'])
        if rack_size_match:
            rack_capacity = int(rack_size_match.group(1))
            if total_ru > rack_capacity * 0.8:
                warnings.append(f"🔌 Engineering Warning (Rack Overflow): The estimated {total_ru}U of equipment may not fit comfortably in the selected {rack_capacity}U rack, leaving little room for ventilation and cabling.")

    total_power = sum(item.get('power_draw', 0) for item in boq_items)
    if total_power > 1440:
        warnings.append(f"🔌 Engineering Warning (Power Overload): Total system power draw is {total_power}W, which may exceed a standard 15A circuit.")
            
    return boq_items, warnings

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
        prompt += f"    - **Requirement:** {comp_spec['justification']}\n"
        prompt += f"    - **Rule:** {comp_spec.get('rule', 'Select the best fit.')}\n"
        
        matching_products = product_df[product_df['category'] == comp_spec['category']].head(15)
        if not matching_products.empty:
            for _, prod in matching_products.iterrows():
                prompt += f"    - {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"
        else:
            prompt += f"    - (No products found in catalog for {comp_spec['category']})\n"

    prompt += "\n# OUTPUT FORMAT (STRICT JSON - NO EXTRA TEXT)\n"
    prompt += "{\n"
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        prompt += f'  "{comp_key}": {{"name": "EXACT product name from list", "qty": {comp_spec["quantity"]}}}{comma}\n'
    prompt += "}\n"
    return prompt

def _build_component_blueprint(equipment_reqs, room_type):
    """Dynamically builds the list of required components with strict rules."""
    
    display_size = equipment_reqs['displays'].get('size_inches', 65)
    
    blueprint = {
        'display': {
            'category': 'Displays', 
            'quantity': equipment_reqs['displays'].get('quantity', 1), 
            'priority': 1, 
            'justification': f"Primary {display_size}\" 4K display for presentations", 
            'rule': f"Select a {display_size}\" DISPLAY, MONITOR, or TV. Must be an actual screen, not a mount or cable."
        },
        'display_mount': {
            'category': 'Mounts', 
            'quantity': equipment_reqs['displays'].get('quantity', 1), 
            'priority': 8, 
            'justification': 'Wall mount bracket for the display', 
            'rule': "Select a wall MOUNT or BRACKET for displays. DO NOT select a camera mount, shelf, or rack."
        },
        'in_room_controller': {
            'category': 'Control', 
            'quantity': 1, 
            'priority': 3, 
            'justification': 'Touch panel for room control', 
            'rule': "Select a TOUCH PANEL or tabletop CONTROLLER. DO NOT select a scheduler, processor, or switch."
        },
        'table_connectivity': {
            'category': 'Cables', 
            'quantity': 1, 
            'priority': 9, 
            'justification': 'HDMI cable or connectivity box for presentations', 
            'rule': "Select an HDMI cable, table box, or connectivity solution. Must include HDMI."
        },
        'network_cables': {
            'category': 'Cables', 
            'quantity': 3, 
            'priority': 10, 
            'justification': 'CAT6 network cables for device connectivity', 
            'rule': "Select CAT6 or Ethernet patch cables. Must be network cables."
        },
    }

    # Video system
    if equipment_reqs['video_system']['type'] == 'All-in-one Video Bar':
        blueprint['video_bar'] = {
            'category': 'Video Conferencing', 
            'quantity': 1, 
            'priority': 2, 
            'justification': 'All-in-one video conferencing system with camera, mics, and speakers', 
            'rule': "Select a VIDEO BAR like Poly Studio, Logitech Rally Bar, or similar. Must be an all-in-one unit, not a standalone camera or codec."
        }
    elif equipment_reqs['video_system']['type'] == 'Modular Codec + PTZ Camera':
        blueprint['video_codec'] = {
            'category': 'Video Conferencing', 
            'quantity': 1, 
            'priority': 2, 
            'justification': 'Video conferencing codec', 
            'rule': "Select a CODEC like Poly G7500, Cisco Codec, or similar. DO NOT select a camera or video bar."
        }
        blueprint['ptz_camera'] = {
            'category': 'Video Conferencing', 
            'quantity': 1, 
            'priority': 2.1, 
            'justification': 'PTZ camera for video feed', 
            'rule': "Select a PTZ CAMERA. Must be a camera device, not a mount, shelf, or cable."
        }

    # Audio system
    if equipment_reqs['audio_system'].get('dsp_required'):
        blueprint['dsp'] = {
            'category': 'Audio', 
            'quantity': 1, 
            'priority': 4, 
            'justification': 'Digital Signal Processor for audio mixing', 
            'rule': "Select a DSP like Q-SYS Core, Biamp Tesira, or Crestron processor. DO NOT select a simple amplifier or summing device."
        }
        blueprint['microphones'] = {
            'category': 'Audio', 
            'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 
            'priority': 5, 
            'justification': 'Ceiling or table microphones for voice pickup', 
            'rule': "Select MICROPHONES (ceiling or table). Must be actual microphones, not cables or accessories."
        }
        blueprint['speakers'] = {
            'category': 'Audio', 
            'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 
            'priority': 6, 
            'justification': 'Ceiling or wall speakers for room audio', 
            'rule': "Select ceiling or wall SPEAKERS. Must be speakers, not cables or accessories."
        }
        blueprint['amplifier'] = {
            'category': 'Audio', 
            'quantity': 1, 
            'priority': 7, 
            'justification': 'Power amplifier for speakers', 
            'rule': "Select a power AMPLIFIER. Must be an amplifier, not a summing amp or audio accessory."
        }

    # Infrastructure
    if equipment_reqs['housing']['type'] == 'AV Rack':
        blueprint['av_rack'] = {
            'category': 'Infrastructure', 
            'quantity': 1, 
            'priority': 12, 
            'justification': 'Equipment rack for housing AV components', 
            'rule': "Select a floor-standing AV RACK or enclosure (12U-42U). DO NOT select a shelf, plate, or adapter."
        }
    
    if equipment_reqs['power_management']['type'] == 'Rackmount PDU':
        blueprint['pdu'] = {
            'category': 'Infrastructure', 
            'quantity': 1, 
            'priority': 11, 
            'justification': 'Rack-mounted power distribution unit', 
            'rule': "Select a rack-mounted PDU with multiple outlets."
        }

    return blueprint

def _get_fallback_product(category, product_df, comp_spec):
    """Get best fallback product with strict validation."""
    matching = product_df[product_df['category'] == category]
    if matching.empty:
        st.error(f"No products found for category: {category}")
        return None

    rule = comp_spec.get('rule', '').lower()
    expected_type = None
    
    # Determine what type of product we're looking for
    if 'display' in rule and category == 'Displays':
        expected_type = 'display'
        size_match = re.search(r'(\d+)"', rule)
        if size_match:
            target_size = int(size_match.group(1))
            matching['size_num'] = matching['name'].str.extract(r'(\d+)"?')[0].astype(float)
            matching = matching[matching['size_num'].notna()]
            matching['size_diff'] = abs(matching['size_num'] - target_size)
            matching = matching.sort_values('size_diff')
    elif 'mount' in rule and category == 'Mounts':
        expected_type = 'mount'
    elif 'video bar' in rule:
        expected_type = 'video_bar'
    elif 'codec' in rule:
        expected_type = 'codec'
    elif 'camera' in rule or 'ptz' in rule:
        expected_type = 'camera'
    elif 'microphone' in rule or 'mic' in rule:
        expected_type = 'microphone'
    elif 'speaker' in rule:
        expected_type = 'speaker'
    elif 'touch panel' in rule or 'controller' in rule:
        expected_type = 'touch_panel'
    elif 'rack' in rule and category == 'Infrastructure':
        expected_type = 'rack'
    
    # Apply validation filter
    if expected_type:
        validated = []
        for _, product in matching.iterrows():
            if _validate_product_type(product.to_dict(), expected_type):
                validated.append(product)
        
        if validated:
            matching = pd.DataFrame(validated)
        else:
            st.warning(f"No validated products found for {expected_type} in {category}")
            return None
    
    if matching.empty:
        return None
    
    # Return median-priced item
    matching = matching.sort_values('price')
    return matching.iloc[len(matching)//2].to_dict()

def _strict_product_match(product_name, product_df, category):
    if product_df is None or len(product_df) == 0: return None
    filtered_by_cat = product_df[product_df['category'] == category]
    search_df = filtered_by_cat if not filtered_by_cat.empty else product_df
    
    exact_match = search_df[search_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty: return exact_match.iloc[0].to_dict()
    
    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3:
            matches = search_df[search_df['name'].str.lower().str.contains(re.escape(term), na=False)]
            if not matches.empty: return matches.iloc[0].to_dict()
    
    return None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type):
    boq_items, matched_count = [], 0
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        comp_spec, category = required_components[comp_key], required_components[comp_key]['category']
        
        matched_product = _strict_product_match(selection.get('name', 'N/A'), product_df, category)
        
        if matched_product:
            matched_count += 1
            boq_items.append({'category': matched_product['category'], 'name': matched_product['name'], 'brand': matched_product['brand'], 'quantity': selection.get('qty', comp_spec['quantity']), 'price': float(matched_product['price']), 'justification': comp_spec['justification'], 'specifications': matched_product.get('features', ''), 'image_url': matched_product.get('image_url', ''), 'gst_rate': matched_product.get('gst_rate', 18), 'matched': True, 'power_draw': estimate_power_draw(matched_product['category'], matched_product['name'])})
        else:
            fallback_product = _get_fallback_product(category, product_df, comp_spec)
            if fallback_product:
                boq_items.append({'category': fallback_product['category'], 'name': fallback_product['name'], 'brand': fallback_product['brand'], 'quantity': comp_spec['quantity'], 'price': float(fallback_product['price']), 'justification': comp_spec['justification'] + ' (auto-selected)', 'specifications': fallback_product.get('features', ''), 'image_url': fallback_product.get('image_url', ''), 'gst_rate': fallback_product.get('gst_rate', 18), 'matched': False, 'power_draw': estimate_power_draw(fallback_product['category'], fallback_product['name'])})

    if len(boq_items) < len(required_components):
        boq_items = _add_essential_missing_components(boq_items, product_df, required_components)
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

def _add_essential_missing_components(boq_items, product_df, required_components):
    current_categories = {item['category'] for item in boq_items}
    missing_components = {key: spec for key, spec in required_components.items() if spec['category'] not in current_categories}

    for key, comp_spec in missing_components.items():
        st.warning(f"Auto-adding missing essential component: {key}")
        fallback = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if fallback:
            boq_items.append({'category': fallback['category'], 'name': fallback['name'], 'brand': fallback['brand'], 'quantity': comp_spec['quantity'], 'price': float(fallback['price']), 'justification': f"{comp_spec['justification']} (auto-added)", 'specifications': fallback.get('features', ''), 'image_url': fallback.get('image_url', ''), 'gst_rate': fallback.get('gst_rate', 18), 'matched': False})
    return boq_items
    
def create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs):
    required_components = _build_component_blueprint(equipment_reqs, room_type)
    fallback_items = []
    for comp_key, comp_spec in required_components.items():
        product = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
        if product:
            fallback_items.append({'category': product['category'], 'name': product['name'], 'brand': product['brand'], 'quantity': comp_spec['quantity'], 'price': float(product['price']), 'justification': comp_spec['justification'], 'specifications': product.get('features', ''), 'image_url': product.get('image_url', ''), 'gst_rate': product.get('gst_rate', 18), 'matched': True})
    return fallback_items

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    issues, warnings = [], []
    return {'avixa_issues': issues, 'avixa_warnings': warnings}

def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area, feature_tags):
    """The re-architected core function to get the BOQ from the AI."""
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    filtered_df = product_df.copy()
    if feature_tags:
        st.info(f"Applying feature filters: {', '.join(feature_tags)}")
        for tag in feature_tags:
            filtered_df = filtered_df[
                filtered_df['feature_tags'].str.contains(tag, na=False, case=False) |
                filtered_df['compatibility_tags'].str.contains(tag, na=False, case=False)
            ]
        if filtered_df.empty:
            st.warning("Filtering with selected features resulted in an empty product list. Using the full catalog.")
            filtered_df = product_df.copy()
        else:
            st.success(f"Filtered catalog to {len(filtered_df)} products based on requirements.")

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
        
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type)
        return boq_items, avixa_calcs, equipment_reqs
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}. Creating a smart fallback BOQ.")
        fallback_items = create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs)
        return fallback_items, avixa_calcs, equipment_reqs
