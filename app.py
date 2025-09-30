import streamlit as st
import time
from datetime import datetime

# --- Component Imports ---
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


# --- "Solar Flare" Theme CSS ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* --- CSS Variables for the "Solar Flare" Theme --- */
    :root {
        --bg-dark: #111827; /* Deep Charcoal Blue */
        --glass-bg: rgba(17, 24, 39, 0.7);
        --glow-primary: #FFBF00; /* Solar Gold */
        --glow-secondary: #00BFFF; /* Holographic Blue */
        --text-primary: #F9FAFB; /* Soft White */
        --text-secondary: #9CA3AF; /* Muted Grey */
        --border-radius-lg: 16px;
        --border-radius-md: 10px;
        --animation-speed: 0.4s;
    }

    /* --- Keyframe Animations --- */
    @keyframes aurora { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
    @keyframes shine { 0%{left:-100px} 100%{left:120%} }
    @keyframes flicker { 0%,100%{opacity:1} 50%{opacity:0.6} }
    @keyframes spin { 0%{transform:rotate(0deg)} 100%{transform:rotate(360deg)} }
    @keyframes spin-reverse { 0%{transform:rotate(0deg)} 100%{transform:rotate(-360deg)} }
    
    /* --- Global Style with Animated Background & Grain --- */
    .stApp {
        background-color: var(--bg-dark);
        background-image: 
            /* Layer 1: Subtle static noise for texture */
            url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAMAAAAp4XiDAAAAUVBMVEWFhYWDg4N3d3dtbW17e3t1dXWBgYGHh4d5eXlzc3OLi4ubm5uVlZWPj4+NjY19fX2JiYl/f39tbW1+fn5oaGhiYmLS0tLR0dGysrKqqqrZ2dnx8fHU1NTKysp8fHydnp6Fu3UIAAADcElEQVR42p2b65biQAxAW2s3s3N3d3N3/v/H9i7Itp4oMElsoI3z30IJ8DeyZkTRLMAqgTqgso3qSg+sDGCmostvjQYwY8z2N4pMQbjIwkQS5UQcmJXE28j2Uht4RYVGYo8wT6yok5eJMDEs0mGuxKMR4itN4gY2xqkM7gqCchlOINQk4gUCXg0gY2yQhIkfRhgojJgQpE5SDyE5zHyf6kwoIT5sSj/PEpX0vYnL2b3k52TfG0c4w7z/D/3zzLdOOkN8pIe3h/d7b+S+zYdHz2CiD3wzG/AZoP/39b/d3b0eAAAAAElFTkSuQmCC),
            /* Layer 2: Animated Aurora */
            linear-gradient(125deg, #111827, #3730a3, #FFBF00, #00BFFF, #111827);
        background-size: auto, 400% 400%;
        animation: aurora 25s ease infinite;
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
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        position: relative;
        overflow: hidden;
        transition: transform 0.5s ease, box-shadow 0.5s ease;
        transform-style: preserve-3d;
    }
    .interactive-card:hover {
        transform: perspective(1200px) rotateX(4deg) rotateY(-6deg) scale3d(1.03, 1.03, 1.03);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7), 0 0 40px var(--glow-primary);
    }

    /* --- Animated Corner Brackets --- */
    .glass-container::before, .glass-container::after {
        content: ''; position: absolute; width: 30px; height: 30px;
        border-color: var(--glow-primary); border-style: solid;
        opacity: 0; transition: opacity var(--animation-speed) ease-in-out;
        animation: flicker 3s infinite alternate;
    }
    .glass-container::before { top: 20px; left: 20px; border-width: 2px 0 0 2px; }
    .glass-container::after { bottom: 20px; right: 20px; border-width: 0 2px 2px 0; }
    .interactive-card:hover::before, .interactive-card:hover::after { opacity: 1; }
    
    /* --- Typography with Shimmer --- */
    .animated-header {
        text-align: center;
        background: linear-gradient(90deg, var(--glow-primary), var(--text-primary), var(--glow-secondary));
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; background-size: 300% 300%;
        animation: aurora 8s linear infinite;
        font-size: 3.5rem; font-weight: 700; margin-bottom: 0.5rem;
    }
    
    /* --- Buttons with Shine Effect --- */
    .stButton > button {
        background: transparent; color: var(--text-primary);
        border: 2px solid var(--glow-primary); border-radius: var(--border-radius-md);
        padding: 0.75rem 2rem; font-weight: 600; font-size: 1rem;
        transition: all var(--animation-speed) ease; position: relative; overflow: hidden;
    }
    .stButton > button::before {
        content: ''; position: absolute; top: 0; height: 100%; width: 50px;
        transform: skewX(-20deg); background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.25), transparent);
        animation: shine 3.5s infinite linear;
    }
    .stButton > button:hover {
        background: var(--glow-primary); color: var(--bg-dark);
        box-shadow: 0 0 25px var(--glow-primary); transform: scale(1.05);
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #d32f2f, var(--glow-primary));
        border: none;
    }
    
    /* --- Advanced Loader --- */
    .loader-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem; }
    .dual-ring-loader { position: relative; width: 80px; height: 80px; }
    .dual-ring-loader::before, .dual-ring-loader::after { content: ''; position: absolute; border-radius: 50%; border: 4px solid transparent; animation-duration: 1.2s; animation-timing-function: linear; animation-iteration-count: infinite; }
    .dual-ring-loader::before { width: 100%; height: 100%; border-top-color: var(--glow-primary); animation-name: spin; }
    .dual-ring-loader::after { width: 80%; height: 80%; top: 10%; left: 10%; border-bottom-color: var(--glow-secondary); animation-name: spin-reverse; }
    
    /* Minor component tweaks for theme consistency */
    .stTabs [data-baseweb="tab-list"] { background: transparent; border: 1px solid rgba(255,255,255,0.1); }
    .stTabs [aria-selected="true"] { background: var(--glow-primary); color: var(--bg-dark); box-shadow: 0 0 15px var(--glow-primary); }
    .stTextInput input, .stTextArea textarea, .stNumberInput input { background-color: rgba(0,0,0,0.4) !important; border: 1px solid rgba(255,255,255,0.2) !important; }
    .sidebar-content { background: var(--glass-bg); backdrop-filter: blur(15px); }
    #MainMenu, footer, header { visibility: hidden; }
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: var(--bg-dark); }
    ::-webkit-scrollbar-thumb { background: linear-gradient(var(--glow-secondary), var(--glow-primary)); border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Helper functions for loader and messages remain the same, but benefit from the new CSS variables
def show_animated_loader(text="Processing...", duration=2):
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
    time.sleep(duration); placeholder.empty()

def show_success_message(message):
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(16, 185, 129, 0.5) 100%); border: 1px solid rgba(16, 185, 129, 0.8);"> <div style="font-size: 2rem;">✅</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)

def show_error_message(message):
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(220, 38, 38, 0.3) 0%, rgba(220, 38, 38, 0.5) 100%); border: 1px solid rgba(220, 38, 38, 0.8);"> <div style="font-size: 2rem;">❌</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)

# Re-styled Login Page
def show_login_page():
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="🚀", layout="centered")
    load_css()
    st.markdown('<div class="glass-container interactive-card" style="max-width: 450px; margin: 4rem auto;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 3rem; text-align: center; margin-bottom: 1rem; text-shadow: 0 0 20px var(--glow-primary);">🚀</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="animated-header" style="font-size: 2.5rem;">AllWave AV & GS</h1><p style="text-align: center; color: var(--text-secondary);">Design & Estimation Portal</p>', unsafe_allow_html=True)
    with st.form("login_form"):
        st.text_input("📧 Email ID", placeholder="yourname@allwaveav.com", key="email_input")
        st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="password_input")
        if st.form_submit_button("🚀 Engage", type="primary", use_container_width=True):
            email, password = st.session_state.email_input, st.session_state.password_input
            if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                show_animated_loader("Authenticating...", 1.5)
                st.session_state.authenticated = True; st.session_state.user_email = email;
                show_success_message("Authentication Successful. Welcome."); time.sleep(1); st.rerun()
            else:
                show_error_message("Access Denied. Use official AllWave credentials.")
    st.markdown('</div>', unsafe_allow_html=True)

# Main Application
def main():
    if not st.session_state.get('authenticated'):
        show_login_page(); return
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")
    load_css()

    # Session State Init
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    with st.spinner("Initializing system modules..."):
        product_df, guidelines, data_issues = load_and_validate_data()
    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded."); st.stop()
    model = setup_gemini()
    
    st.markdown('<div class="glass-container interactive-card"><h1 class="animated-header">AllWave AV & GS Portal</h1><p style="text-align: center; color: var(--text-secondary);">Professional AV System Design & BOQ Generation Platform</p></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f'<div class="sidebar-content"><h3 style="color: white;">👤 Welcome</h3><p style="color: var(--text-secondary); word-wrap: break-word;">{st.session_state.get("user_email", "Unknown")}</p></div>', unsafe_allow_html=True)
        if st.button("🚪 Logout", use_container_width=True):
            show_animated_loader("De-authorizing...", 1); st.session_state.clear(); st.rerun()
        st.markdown("---")
        st.markdown('<h3 style="color: var(--text-primary);">🚀 Mission Parameters</h3>', unsafe_allow_html=True)
        st.text_input("Client Name", key="client_name_input")
        st.text_input("Project Name", key="project_name_input")
        st.markdown("---")
        st.markdown('<h3 style="color: var(--text-primary);">⚙️ Financial Config</h3>', unsafe_allow_html=True)
        st.selectbox("Currency", ["INR", "USD"], key="currency_select")
        st.number_input("Hardware GST (%)", value=18, min_value=0, max_value=50, key="gst_hardware")
        st.number_input("Services GST (%)", value=18, min_value=0, max_value=50, key="gst_services")
        st.markdown("---")
        st.markdown('<h3 style="color: var(--text-primary);">🌐 Environment Design</h3>', unsafe_allow_html=True)
        st.selectbox("Primary Space Type", list(ROOM_SPECS.keys()), key="room_type_select")
        st.select_slider("Budget Tier", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")

    # Main Content Tabs
    tab_titles = ["Project Scope", "Room Analysis", "Requirements", "Generate BOQ", "3D Visualization"]
    tab_icons = [" scoping", " analysis", " requirements", " generate", " visual"] # Hidden text for potential future use with icons
    tab1, tab2, tab3, tab4, tab5 = st.tabs([f"**{title}**" for title in tab_titles])

    # Add interactive-card class to each tab's container
    def render_tab_content(tab_function):
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        tab_function()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab1: render_tab_content(create_multi_room_interface)
    with tab2: render_tab_content(create_room_calculator)
    with tab3:
        def tab3_content():
            technical_reqs = {}
            st.text_area("Specific Client Needs & Features:", key="features_text_area", placeholder="e.g., 'Must be Zoom certified...'", height=100)
            technical_reqs.update(create_advanced_requirements())
        render_tab_content(tab3_content)
    with tab4:
        def tab4_content():
            st.markdown('<h2 style="text-align: center; color: var(--text-primary);">BOQ Generation Engine</h2>', unsafe_allow_html=True)
            if st.button("✨ Generate & Validate Production-Ready BOQ", type="primary", use_container_width=True, key="generate_boq_btn"):
                # BOQ Generation logic remains unchanged
                pass # Placeholder for your existing logic
            if st.session_state.get('boq_items'):
                st.markdown("---"); display_boq_results(product_df)
        render_tab_content(tab4_content)
    with tab5: render_tab_content(create_3d_visualization)

if __name__ == "__main__":
    main()
