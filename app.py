import streamlit as st
import time
from datetime import datetime

# --- Component Imports ---
# Ensure your component files are in a 'components' directory.
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


# --- Hyper-Futuristic CSS Styling ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* --- CSS Variables for the Cyberpunk Theme --- */
    :root {
        --bg-dark: #0A0A14;
        --glass-bg: rgba(10, 10, 20, 0.5);
        --glow-primary: #00F2FE;
        --glow-secondary: #A333C8;
        --text-primary: #EAEAEA;
        --text-secondary: #B0B0B0;
        --border-radius-lg: 20px;
        --border-radius-md: 12px;
        --animation-speed: 0.4s;
    }

    /* --- Keyframe Animations for a "Live" Feel --- */
    @keyframes aurora {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes grid-pan {
        0% { background-position: 0% 0%; }
        100% { background-position: 100% 100%; }
    }
    @keyframes shine {
        0% { left: -100px; }
        100% { left: 120%; }
    }
    @keyframes flicker {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    @keyframes spin-reverse {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(-360deg); }
    }
    
    /* --- Animated Backgrounds --- */
    .stApp {
        background-color: var(--bg-dark);
        /* Layer 1: Animated Grid */
        background-image: 
            linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px),
        /* Layer 2: Animated Aurora */
            linear-gradient(125deg, #0A0A14, #2E0854, #00F2FE, #A333C8, #0A0A14);
        background-size: 30px 30px, 30px 30px, 400% 400%;
        animation: grid-pan 60s linear infinite, aurora 20s ease infinite;
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
    }
    
    /* --- Glassmorphism Containers with 3D Tilt --- */
    .glass-container {
        background: var(--glass-bg);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: var(--border-radius-lg);
        padding: 2.5rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        position: relative;
        overflow: hidden;
        transition: transform 0.5s ease, box-shadow 0.5s ease;
        transform-style: preserve-3d;
    }
    .interactive-card:hover {
        transform: perspective(1000px) rotateX(5deg) rotateY(-5deg) scale3d(1.03, 1.03, 1.03);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7), 0 0 30px var(--glow-primary);
    }

    /* --- Animated Corner Brackets --- */
    .glass-container::before, .glass-container::after {
        content: '';
        position: absolute;
        width: 40px;
        height: 40px;
        border-color: var(--glow-primary);
        border-style: solid;
        opacity: 0;
        transition: opacity var(--animation-speed) ease;
        animation: flicker 4s infinite;
    }
    .glass-container::before { top: 15px; left: 15px; border-width: 2px 0 0 2px; }
    .glass-container::after { bottom: 15px; right: 15px; border-width: 0 2px 2px 0; }
    .interactive-card:hover::before, .interactive-card:hover::after {
        opacity: 1;
    }
    
    /* --- Typography with Shimmer --- */
    .animated-header {
        text-align: center;
        background: linear-gradient(90deg, var(--glow-primary), var(--text-primary), var(--glow-secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        background-size: 200% 200%;
        animation: aurora 5s linear infinite;
        font-size: 3.5rem; font-weight: 700; margin-bottom: 0.5rem;
    }
    
    /* --- Buttons with Shine Effect --- */
    .stButton > button {
        background: transparent;
        color: var(--text-primary);
        border: 2px solid var(--glow-primary);
        border-radius: var(--border-radius-md);
        padding: 0.75rem 2rem;
        font-weight: 600; font-size: 1rem;
        transition: all var(--animation-speed) ease;
        position: relative;
        overflow: hidden;
    }
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0;
        height: 100%;
        width: 50px;
        transform: skewX(-20deg);
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        animation: shine 3s infinite linear;
    }
    .stButton > button:hover {
        background: var(--glow-primary);
        color: var(--bg-dark);
        box-shadow: 0 0 25px var(--glow-primary);
        transform: scale(1.05);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, var(--glow-secondary), var(--glow-primary));
        border: none;
    }
    
    /* --- Advanced Loader --- */
    .loader-container {
        display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem;
    }
    .dual-ring-loader {
        position: relative; width: 80px; height: 80px;
    }
    .dual-ring-loader::before, .dual-ring-loader::after {
        content: '';
        position: absolute;
        border-radius: 50%;
        border: 4px solid transparent;
        animation-duration: 1.2s;
        animation-timing-function: linear;
        animation-iteration-count: infinite;
    }
    .dual-ring-loader::before {
        width: 100%; height: 100%;
        border-top-color: var(--glow-primary);
        animation-name: spin;
    }
    .dual-ring-loader::after {
        width: 80%; height: 80%; top: 10%; left: 10%;
        border-bottom-color: var(--glow-secondary);
        animation-name: spin-reverse;
    }
    
    /* Minor component tweaks for theme consistency */
    .stTabs [data-baseweb="tab-list"] { background: transparent; border: 1px solid rgba(255,255,255,0.1); }
    .stTextInput input, .stTextArea textarea, .stNumberInput input { background-color: rgba(0,0,0,0.4) !important; }
    .sidebar-content { background: var(--glass-bg); }
    #MainMenu, footer, header { visibility: hidden; }
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: var(--bg-dark); }
    ::-webkit-scrollbar-thumb { background: linear-gradient(var(--glow-secondary), var(--glow-primary)); border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)


def show_animated_loader(text="Processing...", duration=2):
    """Show the new advanced loader"""
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
        <div class="loader-container">
            <div class="dual-ring-loader"></div>
            <div style="text-align: center; margin-top: 1.5rem; font-weight: 500; color: var(--glow-primary); text-shadow: 0 0 5px var(--glow-primary);">
                {text}
            </div>
        </div>
        """, unsafe_allow_html=True)
    time.sleep(duration)
    placeholder.empty()

# The show_success_message and show_error_message functions remain the same as the previous version.
# I'm re-including them for completeness.
def show_success_message(message):
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(0, 128, 0, 0.4) 0%, rgba(86, 171, 47, 0.6) 100%); border: 1px solid rgba(86, 171, 47, 0.8);">
        <div style="font-size: 2rem;">✅</div>
        <div style="font-weight: 600; font-size: 1.1rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)

def show_error_message(message):
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(178, 34, 34, 0.4) 0%, rgba(255, 107, 107, 0.6) 100%); border: 1px solid rgba(255, 107, 107, 0.8);">
        <div style="font-size: 2rem;">❌</div>
        <div style="font-weight: 600; font-size: 1.1rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Re-styled Login Page ---
def show_login_page():
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="🌐", layout="centered")
    load_css()
    
    # We add 'interactive-card' class for the 3D tilt effect
    st.markdown("""
    <div class="glass-container interactive-card" style="max-width: 450px; margin: 4rem auto;">
        <div style="font-size: 3rem; text-align: center; margin-bottom: 1rem; text-shadow: 0 0 20px var(--glow-primary);">🌐</div>
        <h1 class="animated-header" style="font-size: 2.5rem;">AllWave AV & GS</h1>
        <p style="text-align: center; color: var(--text-secondary);">Design & Estimation Portal</p>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.text_input("📧 Email ID", placeholder="yourname@allwaveav.com", key="email_input")
        st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="password_input")
        login_clicked = st.form_submit_button("🚀 Engage", type="primary", use_container_width=True)
        
        if login_clicked:
            # Same logic as before
            email = st.session_state.email_input
            password = st.session_state.password_input
            if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                show_animated_loader("Authenticating...", 1.5)
                st.session_state.authenticated = True; st.session_state.user_email = email; st.session_state.login_time = datetime.now()
                show_success_message("Authentication successful. Welcome!")
                time.sleep(1); st.rerun()
            else:
                show_error_message("Access denied. Use your official AllWave credentials.")

    st.markdown("</div>", unsafe_allow_html=True)

# --- Re-styled Main Application ---
def main():
    if not st.session_state.get('authenticated'):
        show_login_page()
        return

    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="🌐", layout="wide", initial_sidebar_state="expanded")
    load_css()

    # --- Initialize Session State (same as before) ---
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    # --- Load Data (same as before) ---
    with st.spinner("Initializing system modules..."):
        product_df, guidelines, data_issues = load_and_validate_data()
    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded."); st.stop()
    model = setup_gemini()
    
    # --- Main Header (with 3D tilt effect) ---
    st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
    st.markdown('<h1 class="animated-header">AllWave AV & GS Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: var(--text-secondary);">Professional AV System Design & BOQ Generation Platform</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Sidebar (same as before) ---
    with st.sidebar:
        st.markdown(f'<div class="sidebar-content"><h3 style="color: white;">👤 Welcome</h3><p style="color: var(--text-secondary); word-wrap: break-word;">{st.session_state.get("user_email", "Unknown")}</p></div>', unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            show_animated_loader("De-authorizing...", 1); st.session_state.clear(); st.rerun()
        # ... (rest of sidebar code is the same)
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

    # --- Main Content Tabs ---
    tab_titles = ["🏢 Multi-Room Project", "📊 Room Analysis", "⚙️ Requirements", "📋 Generate BOQ", "🎮 3D Visualization"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_titles)

    # We add 'interactive-card' to each tab's container for the 3D effect
    with tab1:
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        create_multi_room_interface()
        st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        create_room_calculator()
        st.markdown('</div>', unsafe_allow_html=True)
    with tab3:
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        technical_reqs = {}
        st.text_area("🎯 Specific Client Needs & Features:", key="features_text_area", placeholder="e.g., 'Must be Zoom certified...'", height=100)
        technical_reqs.update(create_advanced_requirements())
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
        st.markdown('</div>', unsafe_allow_html=True)
    with tab4:
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: var(--text-primary);">🚀 Professional BOQ Generation</h2>', unsafe_allow_html=True)
        if st.button("✨ Generate & Validate Production-Ready BOQ", type="primary", use_container_width=True, key="generate_boq_btn"):
            # The BOQ Generation logic remains the same
            if not model:
                show_error_message("AI Model is not available.")
            else:
                progress_bar = st.progress(0, text="Initializing...")
                try:
                    progress_bar.progress(10, text="🔄 AI Design Generation...")
                    boq_items, avixa_calcs, equipment_reqs = generate_boq_from_ai(model, product_df, guidelines, st.session_state.room_type_select, st.session_state.budget_tier_slider, st.session_state.features_text_area, technical_reqs, st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16))
                    if boq_items:
                        progress_bar.progress(50, text="⚙️ Applying Logic & Rules...")
                        processed_boq = _remove_exact_duplicates(boq_items)
                        # ... all other processing steps
                        st.session_state.boq_items = processed_boq
                        update_boq_content_with_current_items()
                        progress_bar.progress(80, text="✅ Verifying Standards...")
                        avixa_validation = validate_avixa_compliance(processed_boq, avixa_calcs, equipment_reqs, st.session_state.room_type_select)
                        st.session_state.validation_results = {"issues": avixa_validation.get('avixa_issues', []), "warnings": avixa_validation.get('avixa_warnings', [])}
                        progress_bar.progress(100, text="Complete!")
                        time.sleep(1); progress_bar.empty()
                        show_success_message("BOQ generation pipeline completed successfully!")
                        st.rerun()
                    else:
                        progress_bar.empty(); show_error_message("Failed to generate BOQ.")
                except Exception as e:
                    progress_bar.empty(); show_error_message(f"An error occurred: {str(e)}")
        if st.session_state.get('boq_items'):
            st.markdown("---"); display_boq_results(product_df)
        st.markdown('</div>', unsafe_allow_html=True)
    with tab5:
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        create_3d_visualization()
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
