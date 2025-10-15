# components/utils.py

import streamlit as st
from typing import List, Dict

@st.cache_data(ttl=3600) # Cache for 1 hour
def get_usd_to_inr_rate():
    """Get current USD to INR exchange rate."""
    try:
        # In a real app, you'd use an API like exchangerate-api.com
        return 83.5 
    except:
        return 83.5 # Fallback rate

def convert_currency(amount_usd, to_currency="INR"):
    """Convert USD amount to specified currency."""
    if to_currency == "INR":
        rate = get_usd_to_inr_rate()
        return amount_usd * rate
    return amount_usd

def format_currency(amount, currency="USD"):
    """Format currency with proper symbols and formatting."""
    if currency == "INR":
        return f"₹{amount:,.0f}"
    else:
        return f"${amount:,.2f}"

def estimate_power_draw(category, name):
    """Estimate power draw based on equipment category and name."""
    name_lower, category_lower = name.lower(), category.lower()
    if 'display' in category_lower:
        if any(size in name_lower for size in ['55', '60', '65']): return 200
        elif any(size in name_lower for size in ['70', '75', '80']): return 300
        elif any(size in name_lower for size in ['85', '90', '95', '98']): return 400
        else: return 150
    elif 'audio' in category_lower:
        if 'amplifier' in name_lower: return 300
        elif 'speaker' in name_lower: return 60
        elif 'microphone' in name_lower: return 15
        else: return 50
    elif 'video conferencing' in category_lower:
        if 'rally' in name_lower or 'bar' in name_lower: return 90
        elif 'camera' in name_lower: return 25
        else: return 40
    elif 'control' in category_lower: return 75
    else: return 25

def estimate_installation_hours(boq_items: List[Dict], room_type: str, 
                                cable_management: str) -> Dict:
    """
    ✅ NEW: Estimate installation labor hours based on equipment complexity
    """
    base_hours = {
        'Small Huddle Room': 4,
        'Medium Huddle Room': 6,
        'Standard Conference Room': 12,
        'Large Conference Room': 16,
        'Executive Boardroom': 24,
        'Training Room': 20,
        'Large Training': 32,
        'Multipurpose Event': 40
    }.get(room_type, 12)
    
    # Complexity multipliers
    has_ceiling_audio = any('Ceiling' in item.get('sub_category', '') for item in boq_items)
    has_ptz_camera = any('PTZ' in item.get('sub_category', '') for item in boq_items)
    has_matrix_switcher = any('Matrix' in item.get('sub_category', '') for item in boq_items)
    
    multiplier = 1.0
    if has_ceiling_audio:
        multiplier += 0.3
    if has_ptz_camera:
        multiplier += 0.2
    if has_matrix_switcher:
        multiplier += 0.4
    
    # Cable management impact
    if cable_management == 'In-Wall/Conduit':
        multiplier += 0.5
    elif cable_management == 'Surface Mount':
        multiplier += 0.2
    
    total_hours = base_hours * multiplier
    
    return {
        'installation_hours': total_hours,
        'programming_hours': total_hours * 0.3,  # 30% of install time
        'commissioning_hours': 4,
        'training_hours': 2,
        'total_project_hours': total_hours + (total_hours * 0.3) + 4 + 2
    }
