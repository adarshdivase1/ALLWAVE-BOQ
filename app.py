# app.py

import streamlit as st
import time
from datetime import datetime
import base64
from pathlib import Path

# --- Component Imports ---
try:
    from components.room_profiles import ROOM_SPECS
    from components.data_handler import load_and_validate_data
    from components.gemini_handler import setup_gemini
    from components.boq_generator import generate_boq_from_ai
    from components.ui_components import (
        create_project_header, create_room_calculator, create_advanced_requirements,
        create_multi_room_interface, display_boq_results, update_boq_content_with_current_items
    )
    from components.visualizer import create_3d_visualization
except ImportError as e:
    st.error(f"Failed to import a necessary component: {e}. Please ensure all component files are in the 'components' directory and are complete.")
    st.stop()


def load_css():
    """Reads the style.css file and injects it into the Streamlit app."""
    css_file_path = "assets/style.css"
    try:
        with open(css_file_path, "r") as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Could not find style.css. Please ensure it is in the '{css_file_path}' directory.")


def show_animated_loader(text="Processing...", duration=2):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem;"><div style="position: relative; width: 80px; height: 80px;"><div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 4px solid transparent; border-top-color: var(--glow-primary); animation: spin 1.2s linear infinite;"></div><div style="position: absolute; width: 80%; height: 80%; top: 10%; left: 10%; border-radius: 50%; border: 4px solid transparent; border-bottom-color: var(--glow-secondary); animation: spin-reverse 1.2s linear infinite;"></div></div><div style="text-align: center; margin-top: 1.5rem; font-weight: 500; color: var(--glow-primary); text-shadow: 0 0 5px var(--glow-primary);">{text}</div></div>', unsafe_allow_html=True)
    time.sleep(duration)
    placeholder.empty()

def show_success_message(message):
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(16, 185, 129, 0.5) 100%); border: 1px solid rgba(16, 185, 129, 0.8);"> <div style="font-size: 2rem;">✅</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)

def show_error_message(message):
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(220, 38, 38, 0.3) 0%, rgba(220, 38, 38, 0.5) 100%); border: 1px solid rgba(220, 38, 38, 0.8);"> <div style="font-size: 2rem;">❌</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)

@st.cache_data
def image_to_base64(img_path):
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

def create_header(main_logo, partner_logos):
    main_logo_b64 = image_to_base64(main_logo)
    partner_logos_b64 = {name: image_to_base64(path) for name, path in partner_logos.items()}
    
    partner_html = ""
    for name, b64 in partner_logos_b64.items():
        if b64:
            partner_html += f'<img src="data:image/png;base64,{b64}" alt="{name} Logo" title="{name}">'

    if main_logo_b64:
        st.markdown(f"""
        <div class="logo-container">
            <div class="main-logo">
                <img src="data:image/png;base64,{main_logo_b64}" alt="AllWave AV Logo">
            </div>
            <div class="partner-logos">
                {partner_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Main company logo not found. Please check the path in the 'assets' folder.")

def show_login_page(logo_b64, page_icon_path):
    st.set_page_config(page_title="AllWave AV - Login", page_icon=page_icon_path, layout="centered")
    load_css()
    
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="login-main-logo" alt="AllWave AV Logo">' if logo_b64 else '<div style="font-size: 3rem; margin-bottom: 2rem;">🚀</div>'
    st.markdown(f"""
    <div class="login-container">
        <div class="glass-container interactive-card has-corners">
            {logo_html}
            <div class="login-title">
                <h1 class="animated-header" style="font-size: 2.5rem;">AllWave AV & GS</h1>
                <p style="text-align: center; color: var(--text-secondary);">Design & Estimation Portal</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    with st.form(key="login_form", clear_on_submit=False): # Changed to False to capture inputs
        st.markdown('<div class="login-form">', unsafe_allow_html=True)
        email = st.text_input("📧 Email ID", placeholder="yourname@allwaveav.com", key="email_input", label_visibility="collapsed")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="password_input", label_visibility="collapsed")
        
        st.markdown("<hr style='border-color: var(--border-color); margin: 1rem 0;'>", unsafe_allow_html=True)
        
        # --- NEW QUESTIONS START HERE ---
        is_psni = st.radio(
            "Are you part of a PSNI Global Alliance certified company?",
            ("Yes", "No"), horizontal=True, key="is_psni_radio"
        )
        location_type = st.radio(
            "What is your operational region?",
            ("Local (India)", "Global"), horizontal=True, key="location_type_radio"
        )
        existing_customer = st.radio(
            "Have you worked with AllWave AV before?",
            ("Yes", "No"), horizontal=True, key="existing_customer_radio"
        )
        # --- NEW QUESTIONS END HERE ---
        submitted = st.form_submit_button("Engage", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    if submitted:
        if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
            show_animated_loader("Authenticating...", 1.5)
            st.session_state.authenticated = True
            st.session_state.user_email = email
            
            # --- STORE ANSWERS IN SESSION STATE ---
            st.session_state.is_psni_certified = (is_psni == "Yes")
            st.session_state.user_location_type = location_type
            st.session_state.is_existing_customer = (existing_customer == "Yes")
            
            show_success_message("Authentication Successful. Welcome.")
            time.sleep(1)
            st.rerun()
        else:
            show_error_message("Access Denied. Use official AllWave credentials.")


def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    main_logo_path = Path("assets/company_logo.png")
    
    if not st.session_state.authenticated:
        main_logo_b64 = image_to_base64(main_logo_path)
        show_login_page(main_logo_b64, str(main_logo_path) if main_logo_path.exists() else "🚀")
        return

    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon=str(main_logo_path) if main_logo_path.exists() else "🚀", layout="wide", initial_sidebar_state="expanded")
    load_css()

    # --- Session State Initializations ---
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}
    
    # --- NEW: AUTOMATICALLY SET CURRENCY BASED ON LOGIN INFO ---
    if st.session_state.get('user_location_type') == 'Local (India)':
        st.session_state.currency_select = "INR"
    else:
        st.session_state.currency_select = "USD"
    # --- END NEW BLOCK ---
    
    if 'room_length_input' not in st.session_state:
        st.session_state.room_length_input = 28.0
    if 'room_width_input' not in st.session_state:
        st.session_state.room_width_input = 20.0


    with st.spinner("Initializing system modules..."):
        product_df, guidelines, data_issues = load_and_validate_data()
        st.session_state.product_df = product_df
    if data_issues:
        with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
            for issue in data_issues: st.warning(issue)
    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded."); st.stop()
    model = setup_gemini()

    partner_logos_paths = {
        "Crestron": Path("assets/crestron_logo.png"),
        "AVIXA": Path("assets/avixa_logo.png"),
        "PSNI Global Alliance": Path("assets/iso_logo.png")
    }
    create_header(main_logo_path, partner_logos_paths)

    st.markdown('<div class="glass-container"><h1 class="animated-header">AllWave AV & GS Portal</h1><p style="text-align: center; color: var(--text-secondary);">Professional AV System Design & BOQ Generation Platform</p></div>', unsafe_allow_html=True)

    def update_dimensions_from_room_type():
        room_type = st.session_state.room_type_select
        if room_type in ROOM_SPECS and 'typical_dims_ft' in ROOM_SPECS[room_type]:
            length, width = ROOM_SPECS[room_type]['typical_dims_ft']
            st.session_state.room_length_input = float(length)
            st.session_state.room_width_input = float(width)

    with st.sidebar:
        st.markdown(f'''
        <div class="user-info">
            <h3>👤 Welcome</h3>
            <p>{st.session_state.get("user_email", "Unknown User")}</p>
        </div>
        ''', unsafe_allow_html=True)
        
        # --- NEW: DISPLAY PSNI STATUS ---
        if st.session_state.get('is_psni_certified', False):
            st.success("✅ PSNI Global Alliance Member")
        else:
            st.info("ℹ️ Not a PSNI Member")
        # --- END NEW BLOCK ---
        
        if st.button("🚪 Logout", use_container_width=True):
            show_animated_loader("De-authorizing...", 1)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("<hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🚀 Mission Parameters</h3>', unsafe_allow_html=True)
        
        st.text_input("Project Name", key="project_name_input", placeholder="Enter project name")
        st.text_input("Client Name", key="client_name_input", placeholder="Enter client name")
        st.text_input("Location", key="location_input", placeholder="e.g., Navi Mumbai, India")
        st.text_input("Design Engineer", key="design_engineer_input", placeholder="Enter engineer's name")
        st.text_input("Account Manager", key="account_manager_input", placeholder="Enter manager's name")
        st.text_input("Key Client Personnel", key="client_personnel_input", placeholder="Enter client contact name")
        st.text_area("Key Comments for this version", key="comments_input", placeholder="Add any relevant comments...")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>⚙️ Financial Config</h3>', unsafe_allow_html=True)
        
        # --- CHANGE: REMOVE CURRENCY SELECTOR, DISPLAY AUTOMATIC SETTING ---
        st.text_input("Currency", value=st.session_state.currency_select, disabled=True)
        
        st.session_state.gst_rates['Electronics'] = st.number_input(
            "Hardware GST (%)", value=18, min_value=0, max_value=50)
        st.session_state.gst_rates['Services'] = st.number_input(
            "Services GST (%)", value=18, min_value=0, max_value=50)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🌐 Environment Design</h3>', unsafe_allow_html=True)
        
        room_type_key = st.selectbox(
            "Primary Space Type", 
            list(ROOM_SPECS.keys()), 
            key="room_type_select",
            on_change=update_dimensions_from_room_type
        )
        
        if 'initial_load' not in st.session_state:
            update_dimensions_from_room_type()
            st.session_state.initial_load = True

        st.select_slider(
            "Budget Tier", options=["Economy", "Standard", "Premium", "Enterprise"], 
            value="Standard", key="budget_tier_slider")
        
        if room_type_key in ROOM_SPECS:
            spec = ROOM_SPECS[room_type_key]
            area_start, area_end = spec.get('area_sqft', ('N/A', 'N/A'))
            cap_start, cap_end = spec.get('capacity', ('N/A', 'N/A'))
            primary_use = spec.get('primary_use', 'N/A')
            st.markdown(f"""
            <div class="info-box">
                <p><b>📏 Area:</b> {area_start}-{area_end} sq ft<br>
                   <b>👥 Capacity:</b> {cap_start}-{cap_end} people<br>
                   <b>🎯 Primary Use:</b> {primary_use}</p>
            </div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    tab_titles = ["📋 Project Scope", "📐 Room Analysis", "📋 Requirements", "🛠️ Generate BOQ", "✨ 3D Visualization"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_titles)

    with tab1:
        st.markdown('<h2 class="section-header section-header-project">Multi-Room Project Management</h2>', unsafe_allow_html=True)
        create_multi_room_interface()
        
    with tab2:
        st.markdown('<h2 class="section-header section-header-room">AVIXA Standards Calculator</h2>', unsafe_allow_html=True)
        create_room_calculator()
        
    with tab3:
        st.markdown('<h2 class="section-header section-header-requirements">Advanced Technical Requirements</h2>', unsafe_allow_html=True)
        technical_reqs = {}
        st.text_area(
            "🎯 Specific Client Needs & Features:",
            key="features_text_area",
            placeholder="e.g., 'Must be Zoom certified, requires wireless presentation, needs ADA compliance.'",
            height=100)
        technical_reqs.update(create_advanced_requirements())
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
        
    with tab4:
        st.markdown('<h2 class="section-header section-header-boq">BOQ Generation Engine</h2>', unsafe_allow_html=True)
        
        if st.button("✨ Generate & Validate Production-Ready BOQ", type="primary", use_container_width=True, key="generate_boq_btn"):
            if not model:
                show_error_message("AI Model is not available. Please check API key.")
            else:
                progress_bar = st.progress(0, text="Initializing generation pipeline...")
                try:
                    room_area = st.session_state.room_length_input * st.session_state.room_width_input

                    progress_bar.progress(25, text="🤖 Step 1: Querying AI, validating, and post-processing...")
                    
                    processed_boq, avixa_calcs, equipment_reqs, validation_results = generate_boq_from_ai(
                        model, product_df, guidelines,
                        st.session_state.room_type_select,
                        st.session_state.budget_tier_slider,
                        st.session_state.get('features_text_area', ''),
                        technical_reqs,
                        room_area 
                    )
                    
                    if processed_boq:
                        progress_bar.progress(90, text="✅ Finalizing results...")
                        
                        st.session_state.boq_items = processed_boq
                        st.session_state.validation_results = validation_results
                        update_boq_content_with_current_items()

                        if st.session_state.project_rooms and st.session_state.current_room_index < len(st.session_state.project_rooms):
                            st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = processed_boq
                        
                        progress_bar.progress(100, text="✅ BOQ generation complete!")
                        time.sleep(0.5)
                        progress_bar.empty()
                        show_success_message("BOQ Generated Successfully with AVIXA Compliance Check")
                    else:
                        progress_bar.empty()
                        show_error_message("Failed to generate BOQ. Please check your inputs and try again.")
                except Exception as e:
                    progress_bar.empty()
                    show_error_message(f"Error during BOQ generation: {str(e)}")
                    st.exception(e)
        
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        if st.session_state.get('boq_items'):
            project_details = {
                'Project Name': st.session_state.get('project_name_input', 'Untitled Project'),
                'Client Name': st.session_state.get('client_name_input', 'N/A'),
                'Location': st.session_state.get('location_input', 'N/A'),
                'Design Engineer': st.session_state.get('design_engineer_input', 'N/A'),
                'Account Manager': st.session_state.get('account_manager_input', 'N/A'),
                'Key Client Personnel': st.session_state.get('client_personnel_input', 'N/A'),
                'Key Comments': st.session_state.get('comments_input', ''),
                'gst_rates': st.session_state.get('gst_rates', {}),
                
                # --- NEW: ADD CUSTOMER INFO TO PROJECT DETAILS ---
                'PSNI Certified': "Yes" if st.session_state.get('is_psni_certified') else "No",
                'Existing Customer': "Yes" if st.session_state.get('is_existing_customer') else "No",
                'Region': st.session_state.get('user_location_type', 'Global')
                # --- END NEW BLOCK ---
            }
            display_boq_results(product_df, project_details)

        else:
            st.info("👆 Click the 'Generate BOQ' button above to create your Bill of Quantities")
    
    with tab5:
        st.markdown('<h2 class="section-header section-header-viz">Interactive 3D Room Visualization</h2>', unsafe_allow_html=True)
        
        if st.button("🎨 Generate 3D Visualization", use_container_width=True, key="generate_viz_btn"):
            with st.spinner("Rendering 3D environment..."):
                viz_html = create_3d_visualization()
                
                if viz_html:
                    st.components.v1.html(viz_html, height=700, scrolling=False)
                    show_success_message("3D Visualization rendered successfully")
                else:
                    show_error_message("Failed to generate 3D visualization")
        
        st.markdown("""
        <div class="info-box" style="margin-top: 1.5rem;">
            <p>
                <b>💡 Visualization Controls:</b><br>
                • <b>Rotate:</b> Left-click and drag<br>
                • <b>Zoom:</b> Scroll wheel<br>
                • <b>Pan:</b> Right-click and drag<br>
                • Equipment placement is based on AVIXA standards and room acoustics
            </p>
        </div>""", unsafe_allow_html=True)

    # --- Footer ---
    st.markdown(f"""
    <div class="custom-footer">
        <p>© {datetime.now().year} AllWave Audio Visual & General Services | Powered by AI-driven Design Engine</p>
        <p style="font-size: 0.8rem; margin-top: 0.5rem;">Built with Streamlit • Gemini AI • AVIXA Standards Compliance</p>
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
