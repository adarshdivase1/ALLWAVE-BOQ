import streamlit as st
import pandas as pd
import re
import json
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- Component Imports ---
try:
    from components.gemini_handler import generate_with_retry
    from components.av_designer import calculate_avixa_recommendations, determine_equipment_requirements
    from components.utils import estimate_power_draw
except ImportError as e:
    st.error(f"BOQ Generator failed to import a component: {e}")
    # Dummy functions
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {}
    def estimate_power_draw(*args): return 100

def _parse_ai_response(response_text):
    """Cleans and parses the AI's JSON response."""
    try:
        cleaned = response_text.strip().replace("`", "").lstrip("json").strip()
        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}. Response: {response_text[:200]}")
        return {}

def _get_prompt_for_specs(room_type, equipment_reqs, features):
    """NEW PROMPT: Asks the AI for specs, not product selections."""
    prompt = f"""
    You are a world-class CTS-D certified AV System Designer.
    Your task is to provide the ideal technical specifications for an AV system in a '{room_type}'.
    
    Based on the required equipment blueprint below, describe the key features and specifications for each component.
    Be specific and technical. For example, for a camera, specify '4K PTZ with auto-tracking' instead of just 'a good camera'.
    
    # Required Equipment Blueprint
    {json.dumps(equipment_reqs, indent=2)}
    
    # Specific Client Needs
    {features if features else "Standard functionality for this room type."}
    
    # Your Output (MUST be ONLY this JSON structure):
    {{
    """
    output_structure = []
    for key, req in equipment_reqs.items():
        if req: # Only include required components
            output_structure.append(f'  "{key}": {{"specifications": "Provide ideal technical specs here", "quantity": {req.get("quantity", 1)}}}')
    prompt += ",\n".join(output_structure)
    prompt += "\n}"
    return prompt

def _find_best_product_match(specs, category, sub_category, product_df, budget_tier):
    """Programmatically finds the best product match based on specs, category, and budget."""
    if product_df.empty: return None
    
    # 1. Hard Filter by Category (prevents mismatches)
    candidates = product_df[
        (product_df['category'] == category) & 
        (product_df['sub_category'] == sub_category)
    ]
    if candidates.empty:
        # Broaden search if specific sub-category fails
        candidates = product_df[product_df['category'] == category]
    
    if candidates.empty: return None # No products in the required category

    # 2. Score remaining candidates based on spec keywords
    candidates = candidates.copy() # Avoid SettingWithCopyWarning
    candidates['search_text'] = candidates['name'].fillna('') + ' ' + candidates['features'].fillna('')
    
    vectorizer = TfidfVectorizer(stop_words='english')
    product_matrix = vectorizer.fit_transform(candidates['search_text'])
    spec_vector = vectorizer.transform([specs])
    
    cosine_similarities = cosine_similarity(spec_vector, product_matrix).flatten()
    
    candidates['score'] = cosine_similarities
    
    top_candidates = candidates[candidates['score'] > 0.1].sort_values(by='score', ascending=False)
    
    if top_candidates.empty:
        top_candidates = candidates

    # 3. Select from top matches based on budget
    if top_candidates.empty: return None
    
    sorted_by_price = top_candidates.sort_values(by='price')
    
    if budget_tier == "Economy":
        return sorted_by_price.iloc[0].to_dict()
    elif budget_tier == "Premium" or budget_tier == "Enterprise":
        return sorted_by_price.iloc[-1].to_dict()
    else: # Standard
        median_index = len(sorted_by_price) // 2
        return sorted_by_price.iloc[median_index].to_dict()

def _build_boq_from_ai_recommendations(ai_recs, equipment_reqs, product_df, budget_tier):
    """Builds the BOQ using the new AI spec recommendations."""
    boq_items = []
    
    for key, req_details in equipment_reqs.items():
        if not req_details: continue

        rec = ai_recs.get(key)
        if not rec or not rec.get('specifications'):
            st.warning(f"AI did not provide specs for '{key}'. Using generic selection.")
            specs = f"Standard {req_details.get('sub_category', key)}"
        else:
            specs = rec['specifications']
        
        quantity = rec.get('quantity', req_details.get('quantity', 1))
        
        matched_product = _find_best_product_match(
            specs,
            req_details['primary_category'],
            req_details['sub_category'],
            product_df,
            budget_tier
        )

        if matched_product:
            boq_items.append({
                'category': matched_product.get('category'),
                'name': matched_product.get('name'),
                'brand': matched_product.get('brand'),
                'quantity': quantity,
                'price': float(matched_product.get('price', 0)),
                'justification': f"Selected to meet spec: '{specs}'",
                'specifications': matched_product.get('features', ''),
                'image_url': matched_product.get('image_url', ''),
                'gst_rate': matched_product.get('gst_rate', 18),
                'power_draw': estimate_power_draw(matched_product.get('category', ''), matched_product.get('name', ''))
            })
        else:
            st.error(f"Could not find any product in the catalog for: {key} (Category: {req_details.get('primary_category')} -> {req_details.get('sub_category')})")

    if equipment_reqs.get('displays'):
        mount_specs = "Wall mount compatible with large format display"
        mount = _find_best_product_match(mount_specs, "Mounts", "Display Mount / Cart", product_df, "Standard")
        if mount:
            boq_items.append({
                'category': 'Mounts', 'name': mount.get('name'), 'brand': mount.get('brand'),
                'quantity': equipment_reqs['displays'].get('quantity', 1), 'price': float(mount.get('price', 0)),
                'justification': 'Essential wall mount for display (auto-added)'
            })
            
    return boq_items

# --- ADDED BACK: The missing function ---
def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    """
    Placeholder for validating the final BOQ against AVIXA standards.
    """
    issues, warnings = [], []
    # Example check:
    if display_req := equipment_reqs.get('displays'):
        target_size = display_req.get('size_inches', 65)
        selected_display = next((item for item in boq_items if item.get('category') == 'Displays'), None)
        if selected_display:
            match = re.search(r'(\d+)', str(selected_display.get('name', '')))
            if match and abs(int(match.group(1)) - target_size) > 10:
                warnings.append(f"Selected display ({match.group(1)}\") is different from the recommended size ({target_size}\").")
    
    return {'avixa_issues': issues, 'avixa_warnings': warnings}


def generate_boq_from_ai(model, product_df, room_type, budget_tier, features, technical_reqs, room_area):
    """The re-architected core function to generate a BOQ."""
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    prompt = _get_prompt_for_specs(room_type, equipment_reqs, features)
    
    try:
        response = generate_with_retry(model, prompt)
        if not response or not response.text: raise Exception("AI returned empty response.")
        
        ai_recs = _parse_ai_response(response.text)
        if not ai_recs: raise Exception("Failed to parse AI recommendations.")
            
        boq_items = _build_boq_from_ai_recommendations(ai_recs, equipment_reqs, product_df, budget_tier)
        return boq_items, avixa_calcs, equipment_reqs

    except Exception as e:
        st.error(f"AI generation failed: {str(e)}")
        return [], avixa_calcs, equipment_reqs
