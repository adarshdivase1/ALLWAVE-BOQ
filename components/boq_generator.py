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
    """Extract JSON from AI response."""
    try:
        cleaned = ai_response_text.strip().replace("`", "")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}")
        return {}

def _build_comprehensive_boq_prompt(room_type, complexity, room_area, avixa_calcs, equipment_reqs, required_components, product_df, budget_tier, features):
    """Build detailed AI prompt incorporating client needs and AVIXA principles."""
    budget_filters = {
        'Economy': (0, 2000), 'Standard': (500, 4000),
        'Premium': (2000, 8000), 'Enterprise': (5000, 15000)
    }
    price_range = budget_filters.get(budget_tier, (0, 10000))
    product_catalog = {}
    for comp_key, comp_spec in required_components.items():
        category = comp_spec['category']
        matching_products = product_df[product_df['category'] == category]
        if len(matching_products) == 0:
            matching_products = product_df[product_df['category'].str.contains(category, case=False, na=False)]
        if len(matching_products) > 20:
            budget_filtered = matching_products[
                (matching_products['price'] >= price_range[0]) &
                (matching_products['price'] <= price_range[1])
            ]
            if len(budget_filtered) >= 5:
                matching_products = budget_filtered
        product_catalog[comp_key] = matching_products.head(20)

    prompt = f"""You are an AVIXA CTS-D certified AV system designer. Your task is to create a complete, logical, and standards-compliant Bill of Quantities (BOQ).

# PROJECT BRIEF
- **Room Type:** {room_type}
- **Complexity Level:** {complexity.upper()}
- **Budget Tier:** {budget_tier}
- **Client Needs/Features:** {features if features else 'Standard functionality for this room type.'}

# AVIXA-BASED DESIGN PARAMETERS
- **Area:** {room_area:.0f} sq ft
- **Required Display Size (DISCAS):** {equipment_reqs.get('displays', {}).get('size_inches', 'N/A')}"

# MANDATORY SYSTEM COMPONENTS ({len(required_components)} items)
You must select one product for each of the following roles. Use the product lists provided below.
"""
    for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
        prompt += f"\n{comp_key.upper()} (Category: {comp_spec['category']}, Qty: {comp_spec['quantity']}):\n"
        if comp_key in product_catalog and len(product_catalog[comp_key]) > 0:
            for _, prod in product_catalog[comp_key].iterrows():
                prompt += f"  • {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"
        else:
            prompt += f"  • (Use any available {comp_spec['category']} product)\n"

    prompt += f"""

OUTPUT FORMAT (STRICT JSON - NO TEXT BEFORE OR AFTER):
{{
"""
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        prompt += f'  "{comp_key}": {{"name": "EXACT product name from list above", "qty": {comp_spec["quantity"]}}}{comma}\n'
    prompt += f"""}}

CRITICAL RULES:
1. Output ONLY valid JSON.
2. Use EXACT product names from the lists.
3. Include ALL {len(required_components)} components.
"""
    return prompt


# --- Product Matching and BOQ Assembly ---
def _strict_product_match(product_name, product_df, category):
    """Enhanced fuzzy matching with fallback logic."""
    if product_df is None or len(product_df) == 0: return None
    
    filtered_by_cat = product_df[product_df['category'] == category]
    if len(filtered_by_cat) == 0:
        filtered_by_cat = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    
    search_df = filtered_by_cat if len(filtered_by_cat) > 0 else product_df

    exact_match = search_df[search_df['name'].str.lower() == product_name.lower()]
    if not exact_match.empty:
        return exact_match.iloc[0].to_dict()

    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3:
            matches = search_df[search_df['name'].str.lower().str.contains(term, na=False)]
            if not matches.empty:
                return matches.iloc[0].to_dict()

    return search_df.iloc[0].to_dict() if not search_df.empty else None

def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type):
    """Build BOQ items from AI selection with enhanced matching and validation."""
    boq_items = []
    matched_count = 0
    
    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components: continue
        comp_spec = required_components[comp_key]
        category = comp_spec['category']
        matched_product = _strict_product_match(selection.get('name', 'N/A'), product_df, category)
        
        if matched_product:
            matched_count += 1
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
    
    st.info(f"Matched {matched_count}/{len(required_components)} components from AI selection.")
    
    if len(boq_items) < len(required_components):
        st.warning(f"AI returned {len(boq_items)}/{len(required_components)} components. Adding missing items.")
        boq_items = _add_essential_missing_components(boq_items, product_df, required_components)
        
    return boq_items

def _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type):
    """MODIFIED: Define required components using more flexible and complete blueprints."""
    
    # MODIFIED: Expanded component definitions for a complete solution
    component_definitions = {
        'display': {'category': 'Displays', 'quantity': equipment_reqs['displays']['quantity'], 'size_requirement': equipment_reqs['displays']['size_inches'], 'priority': 1, 'justification': f"Primary display for {room_type}"},
        'mount': {'category': 'Mounts', 'quantity': equipment_reqs['displays']['quantity'], 'priority': 8, 'justification': 'Professional display mounting hardware'},
        'video_bar': {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one VC solution for huddle spaces'},
        'touch_panel': {'category': 'Control', 'quantity': 1, 'priority': 3, 'justification': 'Primary user interface for meeting control'},
        'table_connectivity': {'category': 'Cables', 'quantity': 1, 'priority': 9, 'justification': 'Table-mounted input plate/cubby for wired HDMI presentation'},
        'cables': {'category': 'Cables', 'quantity': 4, 'priority': 10, 'justification': 'Essential AV network and power connectivity'},
        'pdu': {'category': 'Infrastructure', 'quantity': 1, 'priority': 11, 'justification': 'Rack-mounted power distribution and protection'},
        'rack': {'category': 'Infrastructure', 'quantity': 1, 'priority': 12, 'justification': 'Professional housing for AV equipment'},
        'camera': {'category': 'Video Conferencing', 'quantity': equipment_reqs['video_system']['camera_count'], 'priority': 2, 'justification': f"{equipment_reqs['video_system']['camera_type']}"},
        'codec': {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'Professional 4K video codec for integrated rooms'},
        'microphones': {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 4, 'justification': f"Microphone coverage for room occupants"},
        'speakers': {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 5, 'justification': f"Distributed speaker system for even audio coverage"},
        'dsp': {'category': 'Audio', 'quantity': 1, 'priority': 6, 'justification': 'DSP for acoustic echo cancellation and audio routing'},
        'amplifier': {'category': 'Audio', 'quantity': 1, 'priority': 7, 'justification': f"Amplifier for passive audio system components"},
    }
    
    # MODIFIED: Blueprints now include controllers and infrastructure for all levels
    complexity_map = {
        'simple': ['display', 'mount', 'video_bar', 'touch_panel', 'table_connectivity', 'cables'],
        'moderate': ['display', 'mount', 'video_bar', 'touch_panel', 'table_connectivity', 'cables', 'pdu'],
        'advanced': ['display', 'mount', 'camera', 'codec', 'microphones', 'speakers', 'dsp', 'touch_panel', 'table_connectivity', 'cables', 'pdu', 'rack'],
        'complex': ['display', 'mount', 'camera', 'codec', 'microphones', 'speakers', 'dsp', 'amplifier', 'touch_panel', 'table_connectivity', 'cables', 'pdu', 'rack']
    }
        
    required_keys = complexity_map.get(complexity, complexity_map['moderate'])
    return {key: component_definitions[key] for key in required_keys if key in component_definitions}

# --- PRODUCTION-READY VALIDATION & CORRECTION LAYER ---

def _remove_exact_duplicates(boq_items):
    """Removes items that are exact duplicates based on their name."""
    seen = set()
    unique_items = []
    for item in boq_items:
        item_key = item.get('name')
        if item_key not in seen:
            seen.add(item_key)
            unique_items.append(item)
        else:
            st.warning(f"🧹 Removed exact duplicate item: {item_key}")
    return unique_items

def _remove_duplicate_core_components(boq_items):
    """Finds and removes duplicate core items based on category, keeping the best one."""
    final_items = []
    core_categories = ['Video Conferencing', 'Control']
    
    # Handle non-core and audio items first
    for item in boq_items:
        if item.get('category') not in core_categories:
            final_items.append(item)

    # Handle core categories by finding the best candidate
    for category in core_categories:
        candidates = [item for item in boq_items if item.get('category') == category]
        if len(candidates) > 1:
            st.warning(f"Multiple items found for core category '{category}'. Consolidating to one.")
            best_candidate = max(candidates, key=lambda x: x.get('price', 0))
            final_items.append(best_candidate)
        elif len(candidates) == 1:
            final_items.append(candidates[0])
            
    # Remove duplicates from the final list one last time to be safe
    return _remove_exact_duplicates(final_items)

def _validate_and_correct_mounts(boq_items):
    """Ensures the mount is for the display, not a hallway sign."""
    display_item = next((item for item in boq_items if item['category'] == 'Displays'), None)
    mount_item = next((item for item in boq_items if item['category'] == 'Mounts'), None)

    if display_item and mount_item:
        if "Hallway Sign" in mount_item['name']:
            st.warning(f"⚠️ Correcting incorrect mount for '{display_item['name']}'.")
            display_size_match = re.search(r'(\d+)"', display_item['name'])
            display_size = display_size_match.group(1) if display_size_match else 'display'
            mount_item['name'] = f"Professional Wall Mount for {display_size}\" Display"
            mount_item['specifications'] = "Heavy-duty, professional-grade wall mounting bracket."
            mount_item['justification'] = "Secure mounting for primary room display."
    return boq_items

def _ensure_system_completeness(boq_items, product_df):
    """Checks for logical pairings, like an amplifier needing speakers."""
    has_amplifier = any("Amplifier" in item['name'] for item in boq_items)
    has_speakers = any("Speaker" in item['name'] for item in boq_items)

    if has_amplifier and not has_speakers:
        st.warning("System Incomplete: Amplifier found but no speakers. Adding appropriate ceiling speakers.")
        speaker_products = product_df[
            (product_df['category'] == 'Audio') & 
            (product_df['name'].str.contains("Ceiling Speaker", case=False))
        ]
        if not speaker_products.empty:
            speaker_product = speaker_products.iloc[0].to_dict()
            boq_items.append({
                'category': 'Audio', 'name': speaker_product['name'], 'brand': speaker_product['brand'],
                'quantity': 4, 'price': float(speaker_product['price']),
                'justification': 'Required speakers for the audio amplifier (auto-added for system completeness).',
                'specifications': speaker_product.get('features', ''), 'image_url': speaker_product.get('image_url', ''),
                'gst_rate': speaker_product.get('gst_rate', 18), 'matched': True,
                'power_draw': estimate_power_draw('Audio', speaker_product['name'])
            })
    return boq_items

def _flag_hallucinated_models(boq_items):
    """Adds a warning to items with auto-generated or generic model names."""
    for item in boq_items:
        if "Auto-generated" in item.get('specifications', '') or re.search(r'GEN-\d+', item['name']):
            item['warning'] = "Model is auto-generated and requires verification."
            st.warning(f" flagged '{item['name']}' as a likely hallucinated product.")
    return boq_items

def _correct_quantities(boq_items):
    """Ensures all quantities are integers and logical (e.g., 1 codec per room)."""
    core_keywords = ['G7500', 'Room Kit', 'Codec', 'Crestron Flex']
    for item in boq_items:
        try:
            item['quantity'] = int(float(item.get('quantity', 1)))
            is_core = any(keyword in item['name'] for keyword in core_keywords)
            if is_core and item['quantity'] > 1:
                st.warning(f"Correcting quantity of core component '{item['name']}' from {item['quantity']} to 1.")
                item['quantity'] = 1
        except (ValueError, TypeError):
            item['quantity'] = 1
    return boq_items


# --- Fallback and Validation Logic ---
def _get_fallback_product(category, product_df, comp_spec):
    """Get best fallback product for a category."""
    matching = product_df[product_df['category'] == category]
    if len(matching) == 0:
        matching = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    if len(matching) == 0:
        st.error(f"CRITICAL: No products in catalog for category '{category}'!")
        return None
    
    if 'display' in category.lower() and 'size_requirement' in comp_spec:
        target_size = comp_spec['size_requirement']
        for _, prod in matching.iterrows():
            size_match = re.search(r'(\d+)"', prod['name'])
            if size_match and abs(int(size_match.group(1)) - target_size) <= 10:
                return prod.to_dict()
    
    matching_sorted = matching.sort_values('price')
    index = int(len(matching_sorted) * 0.4) if len(matching_sorted) > 5 else len(matching_sorted) // 2
    return matching_sorted.iloc[index].to_dict()

def _add_essential_missing_components(boq_items, product_df, required_components):
    """Add missing components if AI fails to provide a complete list."""
    added_categories = {item['category'] for item in boq_items}
    for comp_key, comp_spec in required_components.items():
        if comp_spec['category'] not in added_categories:
            st.warning(f"Auto-adding missing component: {comp_key} ({comp_spec['category']})")
            fallback = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
            if fallback:
                boq_items.append({
                    'category': fallback['category'], 'name': fallback['name'], 'brand': fallback['brand'],
                    'quantity': comp_spec['quantity'], 'price': float(fallback['price']),
                    'justification': f"{comp_spec['justification']} (auto-added)", 'specifications': fallback.get('features', ''),
                    'image_url': fallback.get('image_url', ''), 'gst_rate': fallback.get('gst_rate', 18), 'matched': False
                })
    return boq_items

def create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs):
    """Create comprehensive fallback BOQ based on room complexity."""
    st.info("AI generation failed. Using intelligent fallback system.")
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')
    required_components = _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type)
    
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
    st.success(f"Fallback generated {len(fallback_items)} components.")
    return fallback_items

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    """Validate BOQ against AVIXA standards and compliance requirements."""
    issues = []
    warnings = []
    if not avixa_calcs: return {'avixa_issues': ['AVIXA calculations not available.'], 'avixa_warnings': [], 'compliance_score': 0}

    displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
    if not displays:
        issues.append("CRITICAL: No display found in BOQ")
    else:
        for display in displays:
            size_match = re.search(r'(\d+)"', display.get('name', ''))
            if size_match:
                size = int(size_match.group(1))
                recommended_size = avixa_calcs.get('detailed_viewing_display_size', 75)
                if abs(size - recommended_size) > 10:
                    warnings.append(f"Display size ({size}\") deviates from AVIXA DISCAS recommendation ({recommended_size}\").")

    has_dsp = any('dsp' in item.get('name', '').lower() for item in boq_items)
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')
    if equipment_reqs.get('audio_system', {}).get('dsp_required') and not has_dsp and complexity != 'simple':
        issues.append("CRITICAL: DSP required for this room type but not found in BOQ.")
    
    return {
        'avixa_issues': issues,
        'avixa_warnings': warnings,
        'compliance_score': max(0, 100 - (len(issues) * 25) - (len(warnings) * 5)),
    }


# --- Core AI Generation Function ---
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """The core function to get the BOQ from the AI, with fallback logic."""
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')
    required_components = _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type)
    prompt = _build_comprehensive_boq_prompt(
        room_type, complexity, room_area, avixa_calcs, equipment_reqs, 
        required_components, product_df, budget_tier, features
    )
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text: raise Exception("AI returned an empty response.")
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection: raise Exception("Failed to parse valid JSON from AI response.")
        boq_items = _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type)
        return boq_items, avixa_calcs, equipment_reqs
    except Exception as e:
        st.error(f"AI generation failed: {str(e)}")
        fallback_items = create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs)
        return fallback_items, avixa_calcs, equipment_reqs
