# components/utils.py

import streamlit as st

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
