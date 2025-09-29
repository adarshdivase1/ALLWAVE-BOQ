import streamlit as st

# --- Component Imports ---
try:
    from components.data_handler import load_and_validate_data
    from components.gemini_handler import setup_gemini
    from components.boq_generator import (
        generate_boq_from_ai, validate_avixa_compliance, 
        _remove_duplicate_core_components, _validate_and_correct_mounts,
        _ensure_system_completeness, _flag_hallucinated_models, _correct_quantities
    )
    from components.ui_components import (
        create_project_header, create_room_calculator, create_advanced_requirements,
        create_multi_room_interface, display_boq_results, update_boq_content_with_current_items
    )
    from components.visualizer import create_3d_visualization, ROOM_SPECS
except ImportError as e:
    st.error(f"Failed to import a necessary component: {e}. Please ensure all component files are in the 'components' directory and are complete.")
    st.stop()


# --- Simple Login Page ---
def show_login_page():
    """Simple login page for internal users."""
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="⚡")
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 AllWave AV & GS")
        st.subheader("Design & Estimation Portal")
        st.markdown("---")
        with st.form("login_form"):
            email = st.text_input("Email ID", placeholder="yourname@allwaveav.com or yourname@allwavegs.com")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Please use your AllWave AV or AllWave GS email and a valid password.")
        st.markdown("---")
        st.info("Phase 1 Internal Tool - Contact IT for access issues")

# --- Main Application Logic ---
def main():
    if not st.session_state.get('authenticated'):
        show_login_page()
        return

    st.set_page_config(
        page_title="Production-Ready AV BOQ Generator",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- Initialize Session State ---
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    # --- Load Data and Setup Model ---
    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=False):
            for issue in data_issues: st.warning(issue)
    if product_df is None:
        st.error("Fatal Error: Product catalog could not be loaded. App cannot continue.")
        st.stop()

    model = setup_gemini()
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
        st.session_state['currency'] = st.selectbox("Currency Display", ["INR", "USD"], index=0, key="currency_select")
        st.session_state.gst_rates['Electronics'] = st.number_input("Hardware GST (%)", value=18)
        st.session_state.gst_rates['Services'] = st.number_input("Services GST (%)", value=18)

        st.markdown("---")
        st.subheader("Room Design Settings")
        room_type_key = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        
        if room_type_key in ROOM_SPECS:
            spec = ROOM_SPECS[room_type_key]
            st.caption(f"Area: {spec.get('area_sqft', ('N/A', 'N/A'))[0]}-{spec.get('area_sqft', ('N/A', 'N/A'))[1]} sq ft")
            st.caption(f"Complexity: {spec.get('complexity', 'N/A')}")
        
    # --- Main Content Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Multi-Room Project", "Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])

    with tab1:
        create_multi_room_interface()
    with tab2:
        create_room_calculator()
    with tab3:
        st.text_area("Specific Client Needs & Features:", key="features_text_area", placeholder="e.g., 'Must be Zoom certified, requires wireless presentation for 10 users, needs ADA compliance.'")
        technical_reqs = create_advanced_requirements()
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
    
    with tab4:
        st.subheader("Professional BOQ Generation")
        if st.button("🚀 Generate & Validate Production-Ready BOQ", type="primary", use_container_width=True):
            if not model:
                st.error("AI Model is not available. Please check API key.")
            else:
                with st.spinner("Running AVIXA Design and Validation Pipeline..."):
                    
                    st.info("Step 1: Generating initial design with AI...")
                    boq_items, avixa_calcs, equipment_reqs = generate_boq_from_ai(
                        model, product_df, guidelines,
                        st.session_state.room_type_select, st.session_state.budget_tier_slider,
                        st.session_state.features_text_area, technical_reqs,
                        st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                    )
                    
                    if boq_items:
                        st.info("Step 2: Applying AVIXA-based logic and correction rules...")
                        processed_boq = _correct_quantities(boq_items)
                        processed_boq = _remove_duplicate_core_components(processed_boq)
                        processed_boq = _validate_and_correct_mounts(processed_boq)
                        processed_boq = _ensure_system_completeness(processed_boq, product_df)
                        processed_boq = _flag_hallucinated_models(processed_boq)
                        
                        st.session_state.boq_items = processed_boq
                        update_boq_content_with_current_items()
                        
                        if st.session_state.project_rooms:
                            st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = boq_items
                        
                        st.info("Step 3: Verifying final system against AVIXA standards...")
                        avixa_validation = validate_avixa_compliance(processed_boq, avixa_calcs, equipment_reqs, st.session_state.room_type_select)
                        st.session_state.validation_results = {
                            "issues": avixa_validation.get('avixa_issues', []),
                            "warnings": avixa_validation.get('avixa_warnings', [])
                        }
                        
                        st.success("✅ BOQ pipeline complete!")
                        st.rerun()
                    else:
                        st.error("Failed to generate BOQ. The AI and fallback system did not return valid items.")
        
        if st.session_state.get('boq_items'):
            display_boq_results(product_df)
            
    with tab5:
        create_3d_visualization()

if __name__ == "__main__":
    main()
