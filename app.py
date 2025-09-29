# app.py

import streamlit as st
from datetime import datetime

# --- Import from new component files ---
from components.data_handler import load_and_validate_data
from components.gemini_handler import setup_gemini, validate_against_avixa
from components.boq_generator import generate_boq_with_justifications
from components.ui_components import (
    create_project_header, create_room_calculator, create_advanced_requirements,
    create_multi_room_interface, display_boq_results
)
from components.visualizer import create_3d_visualization, ROOM_SPECS

# --- Simple Login Page ---
def show_login_page():
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="⚡")
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 AllWave AV & GS")
        st.subheader("Design & Estimation Portal")
        with st.form("login_form"):
            email = st.text_input("Email ID", placeholder="yourname@allwaveav.com or yourname@allwavegs.com")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.rerun()
                else:
                    st.error("Please use a valid AllWave email and password.")

# --- Main Application Logic ---
def main():
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        show_login_page()
        return

    st.set_page_config(page_title="Professional AV BOQ Generator", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

    # --- Initialize Session State ---
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18, 'Default': 18}

    # --- Load Data and Setup Model ---
    product_df, guidelines, data_issues = load_and_validate_data()
    model = setup_gemini()
    
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=False):
            for issue in data_issues: st.warning(issue)
    if product_df is None: return

    # --- Header ---
    create_project_header()

    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"👤 **Logged in as:** {st.session_state.get('user_email', 'Unknown')}")
        if st.button("Logout", type="secondary"):
            st.session_state.clear()
            st.rerun()
        st.markdown("---")
        st.header("Project Configuration")
        st.text_input("Client Name", key="client_name_input")
        st.text_input("Project Name", key="project_name_input")

        st.markdown("---")
        st.subheader("🇮🇳 Indian Business Settings")
        st.selectbox("Currency Display", ["INR", "USD"], index=0, key="currency_select")
        st.session_state.gst_rates['Electronics'] = st.number_input("Hardware GST (%)", value=18)
        st.session_state.gst_rates['Services'] = st.number_input("Services GST (%)", value=18)

        st.markdown("---")
        st.subheader("Room Design Settings")
        room_type_key = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        
        # Room guidelines display
        if room_type_key in ROOM_SPECS:
            spec = ROOM_SPECS[room_type_key]
            st.caption(f"Complexity: {spec.get('complexity', 'N/A')}")
        
    # --- Main Content Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Multi-Room Project", "Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])

    with tab2:
        room_area, ceiling_height = create_room_calculator()
    with tab3:
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual displays, Zoom certified'", key="features_text_area")
        technical_reqs = create_advanced_requirements()
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)

    with tab4:
        st.subheader("Professional BOQ Generation")
        if st.button("🚀 Generate BOQ with Justifications", type="primary", use_container_width=True):
            if not model:
                st.error("AI Model not available. Check API key.")
            else:
                with st.spinner("Generating and validating professional BOQ..."):
                    # Use latest values from session state for generation
                    _, boq_items, _, _ = generate_boq_with_justifications(
                        model, product_df, guidelines,
                        st.session_state.room_type_select, st.session_state.budget_tier_slider,
                        st.session_state.features_text_area, technical_reqs,
                        st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                    )
                    if boq_items:
                        st.session_state.boq_items = boq_items
                        st.session_state.validation_results['warnings'] = validate_against_avixa(model, guidelines, boq_items)
                        st.success("✅ Generated and validated BOQ!")
                        st.rerun()
                    else:
                        st.error("Failed to generate a valid BOQ.")
        
        display_boq_results(product_df)
    
    with tab5:
        create_3d_visualization()

if __name__ == "__main__":
    main()
