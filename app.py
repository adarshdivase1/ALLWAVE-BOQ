import streamlit as st
import time
from datetime import datetime

# --- Component Imports ---
# Ensure your component files are in a 'components' directory.
# If they are not, create one and place them inside.
try:
    from components.data_handler import load_and_validate_data
    from components.gemini_handler import setup_gemini
    from components.boq_generator import (
        generate_boq_from_ai, validate_avixa_compliance,
        _remove_exact_duplicates, _remove_duplicate_core_components,
        _validate_and_correct_mounts, _ensure_system_completeness,
        _flag_hallucinated_models, _correct_quantities
    )
    from components.ui_components import (
        create_project_header, create_room_calculator, create_advanced_requirements,
        create_multi_room_interface, display_boq_results, update_boq_content_with_current_items
    )
    from components.visualizer import create_3d_visualization, ROOM_SPECS
except ImportError as e:
    st.error(f"Failed to import a necessary component: {e}. Please ensure all component files are in the 'components' directory and are complete.")
    st.stop()


# --- Futuristic CSS Styling ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* --- CSS Variables for easy theme management --- */
    :root {
        --bg-dark: #0D0D1A;
        --glass-bg: rgba(20, 20, 30, 0.6);
        --glow-primary: #00F2FE;
        --glow-secondary: #7B1FA2;
        --text-primary: #F0F0F0;
        --text-secondary: #A0A0A0;
        --border-radius-lg: 20px;
        --border-radius-md: 12px;
    }

    /* --- Keyframe Animations --- */
    @keyframes gradient-animation {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes subtle-glow {
        0% { box-shadow: 0 0 15px rgba(0, 242, 254, 0.2), inset 0 0 5px rgba(0, 242, 254, 0.1); }
        50% { box-shadow: 0 0 25px rgba(0, 242, 254, 0.4), inset 0 0 8px rgba(0, 242, 254, 0.2); }
        100% { box-shadow: 0 0 15px rgba(0, 242, 254, 0.2), inset 0 0 5px rgba(0, 242, 254, 0.1); }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* --- Global Styles --- */
    .stApp {
        background: var(--bg-dark);
        background-image: linear-gradient(135deg, #1a237e 0%, #121212 50%, #4a148c 100%);
        background-size: 400% 400%;
        animation: gradient-animation 15s ease infinite;
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
    }
    
    /* --- Glassmorphism Containers --- */
    .glass-container {
        background: var(--glass-bg);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border-radius: var(--border-radius-lg);
        padding: 2.5rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        animation: fadeInUp 0.7s ease-out;
    }
    
    /* --- Typography --- */
    .animated-header {
        text-align: center;
        background: linear-gradient(90deg, var(--glow-primary), #D469FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 10px rgba(0, 242, 254, 0.3);
    }
    .subtitle {
        text-align: center;
        color: var(--text-secondary);
        font-size: 1.2rem;
        font-weight: 400;
        margin-bottom: 2rem;
    }
    
    /* --- Login Page Styling --- */
    .login-container {
        max-width: 450px;
        margin: 4rem auto;
        padding: 3rem;
    }
    .company-logo {
        font-size: 3rem; text-align: center; margin-bottom: 1rem;
        text-shadow: 0 0 20px var(--glow-primary);
    }
    .company-title {
        font-size: 2.5rem; text-align: center; margin-bottom: 0.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FFFFFF, #B0B0B0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .company-subtitle {
        font-size: 1.1rem; text-align: center; color: var(--text-secondary);
    }
    
    /* --- Buttons & Inputs --- */
    .stButton > button {
        background: transparent;
        color: var(--text-primary);
        border: 2px solid var(--glow-primary);
        border-radius: var(--border-radius-md);
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 0 10px rgba(0, 242, 254, 0.3), inset 0 0 5px rgba(0, 242, 254, 0.2);
    }
    .stButton > button:hover {
        background: var(--glow-primary);
        color: var(--bg-dark);
        box-shadow: 0 0 25px rgba(0, 242, 254, 0.7);
        transform: translateY(-3px) scale(1.02);
    }
    .stButton > button:active {
        transform: translateY(-1px) scale(0.98);
    }
    /* Primary button has a special animated glow */
    .stButton > button[kind="primary"] {
        border-color: transparent;
        background: linear-gradient(90deg, var(--glow-primary), #6f42c1);
        animation: subtle-glow 3s ease-in-out infinite;
    }
    .stTextInput input, .stTextArea textarea, .stNumberInput input {
        background-color: rgba(0,0,0,0.3) !important;
        color: var(--text-primary) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
    }
    
    /* --- Sidebar Styling --- */
    .css-1d391kg { /* Streamlit's sidebar class */
        background: transparent;
    }
    .sidebar-content {
        background: var(--glass-bg);
        border-radius: var(--border-radius-md);
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* --- Tab Styling --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        border-radius: var(--border-radius-md);
        background: var(--glass-bg);
        padding: 0.5rem;
        margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        color: var(--text-secondary);
        transition: all 0.3s ease;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: var(--glow-primary);
        color: var(--bg-dark);
        box-shadow: 0 0 15px rgba(0, 242, 254, 0.5);
    }
    
    /* --- Loaders and Messages --- */
    .loading-spinner {
        width: 60px; height: 60px;
        border: 4px solid rgba(0, 242, 254, 0.2);
        border-top: 4px solid var(--glow-primary);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    .status-message-container {
        display: flex; align-items: center; gap: 1rem;
        color: var(--text-primary);
        border-radius: var(--border-radius-md);
        padding: 1.5rem; margin: 1rem 0;
        animation: fadeInUp 0.5s ease-out;
        backdrop-filter: blur(10px);
    }
    .success-container {
        background: linear-gradient(135deg, rgba(0, 128, 0, 0.4) 0%, rgba(86, 171, 47, 0.6) 100%);
        border: 1px solid rgba(86, 171, 47, 0.8);
    }
    .error-container {
        background: linear-gradient(135deg, rgba(178, 34, 34, 0.4) 0%, rgba(255, 107, 107, 0.6) 100%);
        border: 1px solid rgba(255, 107, 107, 0.8);
    }
    
    /* --- Hide Streamlit Branding --- */
    #MainMenu, footer, header { visibility: hidden; }
    
    /* --- Custom Scrollbar --- */
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: var(--bg-dark); }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(var(--glow-secondary), var(--glow-primary));
        border-radius: 10px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(var(--glow-primary), var(--glow-secondary));
    }
    </style>
    """, unsafe_allow_html=True)


def show_animated_loader(text="Processing...", duration=2):
    """Show a futuristic animated loader"""
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem;">
            <div class="loading-spinner"></div>
            <div style="text-align: center; margin-top: 1.5rem; font-weight: 500; color: var(--glow-primary); text-shadow: 0 0 5px var(--glow-primary);">
                {text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    time.sleep(duration)
    placeholder.empty()


def show_success_message(message):
    """Show an animated success message with the new theme"""
    st.markdown(f"""
    <div class="status-message-container success-container">
        <div style="font-size: 2rem;">✅</div>
        <div style="font-weight: 600; font-size: 1.1rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


def show_error_message(message):
    """Show an animated error message with the new theme"""
    st.markdown(f"""
    <div class="status-message-container error-container">
        <div style="font-size: 2rem;">❌</div>
        <div style="font-weight: 600; font-size: 1.1rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


# --- Re-styled Login Page ---
def show_login_page():
    """Futuristic login page"""
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="🌐", layout="centered")
    load_css()
    
    st.markdown(f"""
    <div class="login-container glass-container">
        <div class="company-logo">🌐</div>
        <h1 class="company-title">AllWave AV & GS</h1>
        <p class="company-subtitle">Design & Estimation Portal</p>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.text_input("📧 Email ID", placeholder="yourname@allwaveav.com", key="email_input")
        st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="password_input")
        
        login_clicked = st.form_submit_button("🚀 Engage", type="primary", use_container_width=True)
        
        if login_clicked:
            email = st.session_state.email_input
            password = st.session_state.password_input
            
            if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                show_animated_loader("Authenticating...", 1.5)
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.login_time = datetime.now()
                show_success_message("Authentication successful. Welcome!")
                time.sleep(1)
                st.rerun()
            else:
                show_error_message("Access denied. Use your official AllWave credentials.")

    st.markdown("""
    </div>
    <div style="text-align: center; margin-top: 2rem; color: var(--text-secondary);">
        <p>🔐 Phase 1 Internal Tool - Contact IT for access issues</p>
        <p style="font-size: 0.8rem;">Powered by AI • Secure • Professional</p>
    </div>
    """, unsafe_allow_html=True)


# --- Re-styled Main Application ---
def main():
    if not st.session_state.get('authenticated'):
        show_login_page()
        return

    st.set_page_config(
        page_title="AllWave AV - BOQ Generator",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    load_css()

    # --- Initialize Session State ---
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    # --- Load Data and Setup Model ---
    with st.spinner("Initializing system modules... Please wait."):
        product_df, guidelines, data_issues = load_and_validate_data()
        
    if data_issues:
        with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
            for issue in data_issues:
                st.warning(issue)
                
    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded. App cannot continue.")
        st.stop()

    model = setup_gemini()
    
    # --- Main Header ---
    st.markdown("""
    <div class="glass-container">
        <h1 class="animated-header">AllWave AV & GS Portal</h1>
        <p class="subtitle">Professional AV System Design & BOQ Generation Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-content">
            <h3 style="color: white; margin-bottom: 1rem;">👤 Welcome</h3>
            <p style="color: var(--text-secondary); margin-bottom: 1rem; word-wrap: break-word;">
                {st.session_state.get('user_email', 'Unknown')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            show_animated_loader("De-authorizing...", 1)
            st.session_state.clear()
            st.rerun()
        
        st.markdown("---")
        
        st.markdown('<h3 style="color: var(--text-primary);">📋 Project Config</h3>', unsafe_allow_html=True)
        st.text_input("👤 Client Name", key="client_name_input", placeholder="Enter client name")
        st.text_input("🏗️ Project Name", key="project_name_input", placeholder="Enter project name")

        st.markdown("---")
        
        st.markdown('<h3 style="color: var(--text-primary);">🇮🇳 Business Settings</h3>', unsafe_allow_html=True)
        st.session_state['currency'] = st.selectbox("💱 Currency", ["INR", "USD"], key="currency_select")
        st.session_state.gst_rates['Electronics'] = st.number_input("🔧 Hardware GST (%)", value=18, min_value=0, max_value=50)
        st.session_state.gst_rates['Services'] = st.number_input("⚙️ Services GST (%)", value=18, min_value=0, max_value=50)

        st.markdown("---")
        
        st.markdown('<h3 style="color: var(--text-primary);">🏢 Room Design</h3>', unsafe_allow_html=True)
        room_type_key = st.selectbox("🎯 Primary Space Type", list(ROOM_SPECS.keys()), key="room_type_select")
        st.select_slider("💰 Budget Tier", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        
        if room_type_key in ROOM_SPECS:
            spec = ROOM_SPECS[room_type_key]
            st.markdown(f"""
            <div style="background: rgba(0,0,0,0.2); padding: 1rem; border-radius: 10px; margin-top: 1rem; border: 1px solid rgba(255,255,255,0.1);">
                <p style="color: var(--text-secondary); margin: 0; font-size: 0.9rem;">
                    <b>📐 Area:</b> {spec.get('area_sqft', ('N/A', 'N/A'))[0]}-{spec.get('area_sqft', ('N/A', 'N/A'))[1]} sq ft<br>
                    <b>⚡ Complexity:</b> {spec.get('complexity', 'N/A')}
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # --- Main Content Tabs ---
    tab_titles = [
        "🏢 Multi-Room Project",
        "📊 Room Analysis",
        "⚙️ Requirements",
        "📋 Generate BOQ",
        "🎮 3D Visualization"
    ]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_titles)

    with tab1:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        create_multi_room_interface()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab2:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        create_room_calculator()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab3:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        technical_reqs = {}
        st.text_area(
            "🎯 Specific Client Needs & Features:",
            key="features_text_area",
            placeholder="e.g., 'Must be Zoom certified, requires wireless presentation, needs ADA compliance.'",
            height=100
        )
        technical_reqs.update(create_advanced_requirements())
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: var(--text-primary);">🚀 Professional BOQ Generation</h2>', unsafe_allow_html=True)
        
        if st.button("✨ Generate & Validate Production-Ready BOQ", type="primary", use_container_width=True, key="generate_boq_btn"):
            if not model:
                show_error_message("AI Model is not available. Please check API key.")
            else:
                progress_bar = st.progress(0, text="Initializing generation pipeline...")
                
                try:
                    # Step 1
                    progress_bar.progress(10, text="🔄 Step 1: Generating initial design with AI...")
                    boq_items, avixa_calcs, equipment_reqs = generate_boq_from_ai(
                        model, product_df, guidelines,
                        st.session_state.room_type_select, st.session_state.budget_tier_slider,
                        st.session_state.features_text_area, technical_reqs,
                        st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                    )
                    
                    if boq_items:
                        # Step 2
                        progress_bar.progress(50, text="⚙️ Step 2: Applying AVIXA-based logic and correction rules...")
                        processed_boq = _remove_exact_duplicates(boq_items)
                        processed_boq = _correct_quantities(processed_boq)
                        processed_boq = _remove_duplicate_core_components(processed_boq)
                        processed_boq = _validate_and_correct_mounts(processed_boq)
                        processed_boq = _ensure_system_completeness(processed_boq, product_df)
                        processed_boq = _flag_hallucinated_models(processed_boq)
                        
                        st.session_state.boq_items = processed_boq
                        update_boq_content_with_current_items()
                        
                        if st.session_state.project_rooms:
                            st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = boq_items
                        
                        # Step 3
                        progress_bar.progress(80, text="✅ Step 3: Verifying final system against AVIXA standards...")
                        avixa_validation = validate_avixa_compliance(
                            processed_boq, avixa_calcs, equipment_reqs, st.session_state.room_type_select
                        )
                        st.session_state.validation_results = {
                            "issues": avixa_validation.get('avixa_issues', []),
                            "warnings": avixa_validation.get('avixa_warnings', [])
                        }
                        
                        progress_bar.progress(100, text="Pipeline complete!")
                        time.sleep(1)
                        progress_bar.empty()
                        show_success_message("BOQ generation pipeline completed successfully!")
                        st.rerun()
                        
                    else:
                        progress_bar.empty()
                        show_error_message("Failed to generate BOQ. The AI and fallback system did not return valid items.")
                        
                except Exception as e:
                    progress_bar.empty()
                    show_error_message(f"An error occurred during BOQ generation: {str(e)}")
        
        if st.session_state.get('boq_items'):
            st.markdown("---")
            display_boq_results(product_df)
            
        st.markdown('</div>', unsafe_allow_html=True)
            
    with tab5:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        create_3d_visualization()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Footer ---
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 2rem; color: var(--text-secondary);">
        <p>🌐 AllWave AV & GS • Professional AV Solutions • Powered by AI</p>
        <p style="font-size: 0.8rem;">© 2024 AllWave Technologies. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
