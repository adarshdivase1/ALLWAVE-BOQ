# components/ui_components.py

import streamlit as st
from datetime import datetime
from components.visualizer import ROOM_SPECS # Assuming visualizer.py has ROOM_SPECS
from components.utils import convert_currency, format_currency, get_usd_to_inr_rate
from components.excel_generator import generate_company_excel

def create_project_header():
    """Create professional project header."""
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("Professional AV BOQ Generator")
        st.caption("Production-ready Bill of Quantities with technical validation")
    with col2:
        st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}", key="project_id_input")
    with col3:
        st.number_input("Quote Valid (Days)", min_value=15, max_value=90, value=30, key="quote_days_input")

def create_room_calculator():
    """Room size calculator and validator."""
    st.subheader("Room Analysis & Specifications")
    col1, col2 = st.columns(2)
    with col1:
        room_length = st.number_input("Room Length (ft)", min_value=10.0, max_value=80.0, value=28.0, key="room_length_input")
        room_width = st.number_input("Room Width (ft)", min_value=8.0, max_value=50.0, value=20.0, key="room_width_input")
        ceiling_height = st.number_input("Ceiling Height (ft)", min_value=8.0, max_value=20.0, value=10.0, key="ceiling_height_input")
    with col2:
        room_area = room_length * room_width
        st.metric("Room Area", f"{room_area:.0f} sq ft")
        recommended_type = next((rt for rt, specs in ROOM_SPECS.items() if specs["area_sqft"][0] <= room_area <= specs["area_sqft"][1]), None)
        if recommended_type:
            st.success(f"Recommended Room Type: {recommended_type}")
        else:
            st.warning("Room size is outside typical ranges")
    return room_area, ceiling_height

def create_advanced_requirements():
    """Advanced technical requirements input."""
    st.subheader("Technical Requirements")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Infrastructure**")
        has_dedicated_circuit = st.checkbox("Dedicated 20A Circuit Available", key="dedicated_circuit_checkbox")
        network_capability = st.selectbox("Network Infrastructure", ["Standard 1Gb", "10Gb Capable", "Fiber Available"], key="network_capability_select")
        cable_management = st.selectbox("Cable Management", ["Exposed", "Conduit", "Raised Floor", "Drop Ceiling"], key="cable_management_select")
    with col2:
        st.write("**Compliance & Standards**")
        ada_compliance = st.checkbox("ADA Compliance Required", key="ada_compliance_checkbox")
        fire_code_compliance = st.checkbox("Fire Code Compliance Required", key="fire_code_compliance_checkbox")
        security_clearance = st.selectbox("Security Level", ["Standard", "Restricted", "Classified"], key="security_clearance_select")
    return {"dedicated_circuit": has_dedicated_circuit, "network_capability": network_capability, "cable_management": cable_management, "ada_compliance": ada_compliance, "fire_code_compliance": fire_code_compliance, "security_clearance": security_clearance}

def create_multi_room_interface():
    # ... [Multi-room UI logic, same as original] ...
    # This is also self-contained UI code.
    pass # Placeholder for brevity

def display_boq_results(boq_content, validation_results, product_df):
    # ... [BOQ results display logic, same as original] ...
    pass # Placeholder for brevity

# And so on for other UI functions like create_interactive_boq_editor, etc.
# The goal is to move all `st.` calls that build the interface into this file.
