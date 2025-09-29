import streamlit as st
import pandas as pd
import re
import json
import time

# Assuming these components are in your project structure as discussed
try:
    from components.gemini_handler import generate_with_retry
    from components.av_designer import calculate_avixa_recommendations, determine_equipment_requirements
    from components.visualizer import ROOM_SPECS
    from components.utils import estimate_power_draw
except ImportError:
    st.error("Could not import one or more required components (gemini, av_designer, visualizer, utils).")
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}, 'control_system': {}}
    def estimate_power_draw(*args): return 100
    ROOM_SPECS = {}

# --- AI Interaction and Parsing ---

def _parse_ai_product_selection(ai_response_text):
    """Extract JSON from AI response."""
    try:
        cleaned = ai_response_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}")
        return {}

def _build_comprehensive_boq_prompt(room_type, complexity, room_area, avixa_calcs, equipment_reqs, required_components, product_df, budget_tier):
    """Build detailed AI prompt with all product options."""
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

    prompt = f"""You are an AVIXA-certified AV system designer. Design a complete system for: {room_type}

ROOM SPECIFICATIONS:
- Area: {room_area} sq ft
- Capacity: {avixa_calcs['estimated_occupancy']} people
- Complexity Level: {complexity.upper()}
- Budget Tier: {budget_tier}

AVIXA CALCULATIONS:
- Display Size Required: {equipment_reqs['displays']['size_inches']}" (Qty: {equipment_reqs['displays']['quantity']})
- Camera System: {equipment_reqs['video_system']['camera_type']} (Qty: {equipment_reqs['video_system']['camera_count']})
- Microphone Zones: {equipment_reqs['audio_system'].get('microphone_count', 2)}
- Speaker Zones: {equipment_reqs['audio_system'].get('speaker_count', 2)}
- DSP Required: {'YES' if equipment_reqs['audio_system'].get('dsp_required') else 'NO'}
- Control System: {equipment_reqs['control_system']['type']}
- Network Bandwidth: {avixa_calcs['recommended_bandwidth_mbps']} Mbps
- Power Load: {avixa_calcs['total_power_load_watts']}W

MANDATORY COMPONENTS ({len(required_components)} items):
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
1. Output ONLY valid JSON - no markdown, no explanations.
2. Use EXACT product names from the lists above.
3. You MUST include ALL {len(required_components)} components.
4. Match display size requirements ({equipment_reqs['displays']['size_inches']}" minimum).
5. Select products appropriate for {budget_tier} budget tier.
6. Prefer known brands (Samsung, LG, Poly, Shure, QSC, Crestron).
"""
    return prompt


# --- Product Matching and BOQ Assembly ---

def _strict_product_match(product_name, product_df, category):
    """Enhanced fuzzy matching with fallback logic."""
    filtered = product_df[product_df['category'] == category]
    if len(filtered) == 0:
        filtered = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    if len(filtered) == 0:
        st.warning(f"No products found for category '{category}' - searching all categories.")
        filtered = product_df
    if len(filtered) == 0: return None
    
    exact = filtered[filtered['name'].str.lower() == product_name.lower()]
    if len(exact) > 0: return exact.iloc[0].to_dict()

    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3:
            matches = filtered[filtered['name'].str.lower().str.contains(term, na=False)]
            if len(matches) > 0: return matches.iloc[0].to_dict()

    return filtered.iloc[0].to_dict() if len(filtered) > 0 else None

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
        boq_items = _add_essential_missing_components(boq_items, equipment_reqs, product_df, required_components)
        
    return boq_items

def _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type):
    """Define required components using explicit blueprints for each complexity level."""
    if complexity == 'simple' and any(keyword in room_type for keyword in ["Large", "Executive", "Training", "Boardroom", "Suite"]):
        st.warning(f"Mismatch: Room type '{room_type}' should not be 'simple'. Upgrading to 'advanced'.")
        complexity = 'advanced'
    
    component_definitions = {
        'display': {'category': 'Displays', 'quantity': equipment_reqs['displays']['quantity'], 'size_requirement': equipment_reqs['displays']['size_inches'], 'priority': 1, 'justification': f"Primary display for {room_type}"},
        'mount': {'category': 'Mounts', 'quantity': equipment_reqs['displays']['quantity'], 'priority': 5, 'justification': 'Professional display mounting hardware'},
        'cables': {'category': 'Cables', 'quantity': 4, 'priority': 6, 'justification': 'Essential AV connectivity'},
        'video_bar': {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'All-in-one VC solution'},
        'camera': {'category': 'Video Conferencing', 'quantity': equipment_reqs['video_system']['camera_count'], 'priority': 2, 'justification': f"{equipment_reqs['video_system']['camera_type']}"},
        'codec': {'category': 'Video Conferencing', 'quantity': 1, 'priority': 2, 'justification': 'Professional 4K video codec'},
        'microphones': {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('microphone_count', 2), 'priority': 3, 'justification': f"Microphone coverage"},
        'speakers': {'category': 'Audio', 'quantity': equipment_reqs['audio_system'].get('speaker_count', 2), 'priority': 3, 'justification': f"Distributed speaker system"},
        'control': {'category': 'Control', 'quantity': 1, 'priority': 4, 'justification': f"{equipment_reqs['control_system']['type']}"},
        'dsp': {'category': 'Audio', 'quantity': 1, 'priority': 3, 'justification': 'DSP for echo cancellation'},
        'network_switch': {'category': 'Infrastructure', 'quantity': 1, 'priority': 5, 'justification': f"Managed network switch"},
        'amplifier': {'category': 'Audio', 'quantity': 1, 'priority': 4, 'justification': f"Amplifier for audio system"},
        'ups': {'category': 'Infrastructure', 'quantity': 1, 'priority': 6, 'justification': f"UPS for power protection"}
    }
    
    complexity_map = {
        'simple': ['display', 'mount', 'cables', 'video_bar'],
        'moderate': ['display', 'mount', 'cables', 'video_bar', 'microphones', 'speakers', 'control'],
        'advanced': ['display', 'mount', 'cables', 'camera', 'codec', 'microphones', 'speakers', 'dsp', 'control', 'network_switch'],
        'complex': ['display', 'mount', 'cables', 'camera', 'codec', 'microphones', 'speakers', 'dsp', 'control', 'network_switch', 'amplifier', 'ups']
    }
    
    if complexity not in complexity_map:
        st.error(f"Unknown complexity: '{complexity}' - using 'moderate' as fallback.")
        complexity = 'moderate'
        
    required_keys = complexity_map[complexity]
    return {key: component_definitions[key] for key in required_keys}

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

def _add_essential_missing_components(boq_items, equipment_reqs, product_df, required_components):
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

# **** NEWLY ADDED FUNCTION ****
def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    """Validate BOQ against AVIXA standards and compliance requirements."""
    issues = []
    warnings = []
    if not avixa_calcs: return {'avixa_issues': ['AVIXA calculations not available.'], 'avixa_warnings': [], 'compliance_score': 0}

    # Display Compliance Validation
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
                    warnings.append(f"Display size ({size}\") deviates from AVIXA recommendation ({recommended_size}\").")

    # Audio System Compliance
    has_dsp = any('dsp' in item.get('name', '').lower() for item in boq_items)
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')
    if equipment_reqs.get('audio_system', {}).get('dsp_required') and not has_dsp and complexity != 'simple':
        issues.append("CRITICAL: DSP required for this room type but not found in BOQ.")

    # UPS Requirement Check
    has_ups = any('ups' in item.get('name', '').lower() for item in boq_items)
    if avixa_calcs.get('ups_va_required', 0) > 1000 and not has_ups and complexity in ['advanced', 'complex']:
        issues.append("CRITICAL: A UPS system is required for this high-power configuration but is missing.")
        
    # ADA Compliance Check
    if avixa_calcs.get('requires_ada_compliance'):
        ada_items = [item for item in boq_items if any(term in item.get('name', '').lower() for term in ['assistive', 'hearing', 'loop'])]
        if not ada_items:
            warnings.append("ADA compliance may be required, but no assistive listening devices were found in the BOQ.")

    return {
        'avixa_issues': issues,
        'avixa_warnings': warnings,
        'compliance_score': max(0, 100 - (len(issues) * 25) - (len(warnings) * 5)),
    }


# --- Main Generator Function ---

def generate_boq_with_justifications(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Orchestrates the entire BOQ generation process."""
    if product_df is None or len(product_df) == 0:
        st.error("No valid products in catalog to generate a BOQ.")
        return [], None, None

    # 1. Perform AV calculations
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    # 2. Determine system components based on complexity
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')
    required_components = _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type)
    
    st.info(f"Designing a {complexity.upper()} system with {len(required_components)} components for a {room_type}.")
    
    # 3. Build and send prompt to AI
    prompt = _build_comprehensive_boq_prompt(
        room_type, complexity, room_area, avixa_calcs, equipment_reqs,
        required_components, product_df, budget_tier
    )

    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text:
            raise Exception("AI returned an empty response.")
        
        # 4. Parse response and build BOQ
        ai_selection = _parse_ai_product_selection(response.text)
        if not ai_selection:
             raise Exception("Failed to parse a valid JSON object from the AI response.")

        boq_items = _build_boq_from_ai_selection(
            ai_selection, required_components, product_df, equipment_reqs, room_type
        )
        return boq_items, avixa_calcs, equipment_reqs

    except Exception as e:
        # 5. If AI fails, use the smart fallback
        st.error(f"AI generation failed: {str(e)}")
        fallback_items = create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs)
        
        if len(fallback_items) < len(required_components):
            st.error("Critical: Fallback system also failed to generate a complete BOQ. Please check the product catalog for availability.")
            return [], avixa_calcs, equipment_reqs

        return fallback_items, avixa_calcs, equipment_reqs
