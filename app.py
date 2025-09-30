import streamlit as st
import time
from datetime import datetime
import base64
from pathlib import Path

# --- Component Imports ---
# Make sure your component files are in a 'components' directory.
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


# --- "Solar Flare" Theme CSS (Enhanced for Branding) ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    :root {
        --bg-dark: #111827;
        --glass-bg: rgba(17, 24, 39, 0.75);
        --widget-bg: rgba(0, 0, 0, 0.3);
        --glow-primary: #FFBF00; /* Solar Gold */
        --glow-secondary: #00BFFF; /* Holographic Blue */
        --text-primary: #F9FAFB;
        --text-secondary: #9CA3AF;
        --border-color: rgba(255, 255, 255, 0.2);
        --border-radius-lg: 16px;
        --border-radius-md: 10px;
        --animation-speed: 0.4s;
    }

    /* Keyframe Animations */
    @keyframes aurora { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
    @keyframes shine { 0%{left:-100px} 100%{left:120%} }
    @keyframes flicker { 0%,100%{opacity:1} 50%{opacity:0.6} }
    @keyframes pulse-glow { 0%, 100% { filter: drop-shadow(0 0 10px var(--glow-primary)); } 50% { filter: drop-shadow(0 0 20px var(--glow-primary)); } }
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
    @keyframes spin { 100% { transform: rotate(360deg); } }
    @keyframes spin-reverse { 100% { transform: rotate(-360deg); } }
    
    /* Global Style */
    .stApp {
        background-color: var(--bg-dark);
        background-image: 
            url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAMAAAAp4XiDAAAAUVBMVEWFhYWDg4N3d3dtbW17e3t1dXWBgYGHh4d5eXlzc3OLi4ubm5uVlZWPj4+NjY19fX2JiYl/f39tbW1+fn5oaGhiYmLS0tLR0dGysrKqqqrZ2dnx8fHU1NTKysp8fHydnp6Fu3UIAAADcElEQVR42p2b65biQAxAW2s3s3N3d3N3/v/H9i7Itp4oMElsoI3z30IJ8DeyZkTRLMAqgTqgso3qSg+sDGCmostvjQYwY8z2N4pMQbjIwkQS5UQcmJXE28j2Uht4RYVGYo8wT6yok5eJMDEs0mGuxKMR4itN4gY2xqkM7gqCchlOINQk4gUCXg0gY2yQhIkfRhgojJgQpE5SDyE5zHyf6kwoIT5sSj/PEpX0vYnL2b3k52TfG0c4w7z/D/3zzLdOOkN8pIe3h/d7b+S+zYdHz2CiD3wzG/AZoP/39b/d3b0eAAAAAElFTSuQmCC),
            linear-gradient(125deg, #111827, #3730a3, #FFBF00, #00BFFF, #111827);
        background-size: auto, 400% 400%;
        animation: aurora 25s ease infinite;
        font-family: 'Inter', sans-serif;
        color: var(--text-primary);
    }
    
    /* Glassmorphism Containers & Corner Brackets */
    .glass-container { background: var(--glass-bg); backdrop-filter: blur(20px); border-radius: var(--border-radius-lg); padding: 2.5rem; margin-bottom: 2rem; border: 1px solid var(--border-color); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5); position: relative; overflow: hidden; transition: transform 0.5s ease, box-shadow 0.5s ease; transform-style: preserve-3d; }
    .interactive-card:hover { transform: perspective(1200px) rotateX(4deg) rotateY(-6deg) scale3d(1.03, 1.03, 1.03); box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7), 0 0 40px var(--glow-primary); }
    .has-corners::before, .has-corners::after { content: ''; position: absolute; width: 30px; height: 30px; border-color: var(--glow-primary); border-style: solid; transition: opacity var(--animation-speed) ease-in-out; animation: flicker 3s infinite alternate; }
    .interactive-card.has-corners:hover::before, .interactive-card.has-corners:hover::after { opacity: 1; }
    .has-corners::before { top: 20px; left: 20px; border-width: 2px 0 0 2px; opacity: 0; }
    .has-corners::after { bottom: 20px; right: 20px; border-width: 0 2px 2px 0; opacity: 0; }
    
    /* Sidebar Styles */
    .st-emotion-cache-16txtl3 { padding: 2rem 1rem; } /* Main sidebar container */
    .user-info { margin-bottom: 1rem; }
    .user-info h3 { margin-bottom: 0.5rem; color: var(--text-primary); }
    .user-info p { color: var(--text-secondary); word-wrap: break-word; font-size: 0.95rem; }
    .sidebar-section { margin-top: 1.5rem; }
    .sidebar-section h3 { margin-bottom: 1rem; color: var(--text-primary); }
    .info-box { background: var(--widget-bg); padding: 1rem; border-radius: var(--border-radius-md); margin-top: 1rem; border: 1px solid var(--border-color); }
    .info-box p { color: var(--text-secondary); margin: 0; font-size: 0.9rem; line-height: 1.6; }

    /* Themed Widgets (Sidebar & Main) */
    .stTextInput input, .stNumberInput input, .stTextArea textarea { background-color: var(--widget-bg) !important; color: var(--text-primary) !important; border: 1px solid var(--border-color) !important; border-radius: var(--border-radius-md) !important; transition: all 0.3s ease; }
    [data-baseweb="select"] > div { background-color: var(--widget-bg) !important; color: var(--text-primary) !importanT; border: 1px solid var(--border-color) !important; border-radius: var(--border-radius-md) !important; }
    [data-baseweb="select"] svg { fill: var(--text-secondary) !important; }
    [data-baseweb="slider"] div[role="slider"] { background-color: var(--glow-primary) !important; box-shadow: 0 0 10px var(--glow-primary); border: none !important; }
    [data-baseweb="slider"] > div:first-of-type { background-image: linear-gradient(to right, var(--glow-primary), var(--glow-secondary)); }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus, [data-baseweb="select"] > div[aria-expanded="true"] { border-color: var(--glow-primary) !important; box-shadow: 0 0 15px rgba(255, 191, 0, 0.5) !important; }
    
    /* Login Page Boot-Up Sequence & Logo */
    .login-container { max-width: 450px; margin: 4rem auto; text-align: center; }
    .login-main-logo { max-height: 60px; margin-bottom: 2rem; animation: fadeInUp 0.8s ease-out 0.2s both, pulse-glow 2.5s infinite ease-in-out; }
    .login-title { animation: fadeInUp 0.8s ease-out 0.4s both; }
    .login-form { animation: fadeInUp 0.8s ease-out 0.6s both; }
    
    /* Other Styles */
    .animated-header { text-align: center; background: linear-gradient(90deg, var(--glow-primary), var(--text-primary), var(--glow-secondary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; background-size: 300% 300%; animation: aurora 8s linear infinite; font-size: 3.5rem; font-weight: 700; margin-bottom: 0.5rem; }
    .stButton > button { background: transparent; color: var(--text-primary); border: 2px solid var(--glow-primary); border-radius: var(--border-radius-md); padding: 0.75rem 2rem; font-weight: 600; font-size: 1rem; transition: all var(--animation-speed) ease; position: relative; overflow: hidden; }
    .stButton > button::before { content: ''; position: absolute; top: 0; height: 100%; width: 50px; transform: skewX(-20deg); background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent); animation: shine 3.5s infinite linear; }
    .stButton > button:hover { background: var(--glow-primary); color: var(--bg-dark); box-shadow: 0 0 25px var(--glow-primary); transform: scale(1.05); }
    .stButton > button[kind="primary"] { background: linear-gradient(90deg, #d32f2f, var(--glow-primary)); border: none; }
    #MainMenu, header { visibility: hidden; }
    footer { visibility: hidden; }
    .custom-footer { text-align: center; padding: 1.5rem; color: var(--text-secondary); font-size: 0.9rem; margin-top: 2rem; }
    ::-webkit-scrollbar { width: 10px; } ::-webkit-scrollbar-track { background: var(--bg-dark); } ::-webkit-scrollbar-thumb { background: linear-gradient(var(--glow-secondary), var(--glow-primary)); border-radius: 10px; }
    
    /* Custom Header/Logo Styles */
    .logo-container { display: flex; align-items: center; justify-content: space-between; padding: 1rem 2rem; background: var(--glass-bg); border-bottom: 1px solid var(--border-color); border-radius: var(--border-radius-lg); margin-bottom: 2rem; }
    .main-logo img { max-height: 50px; }
    .partner-logos { display: flex; align-items: center; gap: 2rem; }
    .partner-logos img { max-height: 35px; opacity: 0.7; transition: opacity 0.3s ease, transform 0.3s ease; }
    .partner-logos img:hover { opacity: 1; transform: scale(1.1); }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def show_animated_loader(text="Processing...", duration=2):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem;"><div style="position: relative; width: 80px; height: 80px;"><div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 4px solid transparent; border-top-color: var(--glow-primary); animation: spin 1.2s linear infinite;"></div><div style="position: absolute; width: 80%; height: 80%; top: 10%; left: 10%; border-radius: 50%; border: 4px solid transparent; border-bottom-color: var(--glow-secondary); animation: spin-reverse 1.2s linear infinite;"></div></div><div style="text-align: center; margin-top: 1.5rem; font-weight: 500; color: var(--glow-primary); text-shadow: 0 0 5px var(--glow-primary);">{text}</div></div>', unsafe_allow_html=True)
    time.sleep(duration); placeholder.empty()

def show_success_message(message):
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(16, 185, 129, 0.5) 100%); border: 1px solid rgba(16, 185, 129, 0.8);"> <div style="font-size: 2rem;">✅</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)

def show_error_message(message):
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(220, 38, 38, 0.3) 0%, rgba(220, 38, 38, 0.5) 100%); border: 1px solid rgba(220, 38, 38, 0.8);"> <div style="font-size: 2rem;">❌</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)

@st.cache_data
def image_to_base64(img_path):
    """Encodes an image to Base64 to embed in HTML."""
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None

def create_header(main_logo, partner_logos):
    """Creates the branded header with main and partner logos."""
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

    # Render the static HTML part of the login page
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

    # Use st.form for login inputs and button
    with st.form(key="login_form", clear_on_submit=True):
        st.markdown('<div class="login-form">', unsafe_allow_html=True)
        email = st.text_input("📧 Email ID", placeholder="yourname@allwaveav.com", key="email_input", label_visibility="collapsed")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="password_input", label_visibility="collapsed")
        submitted = st.form_submit_button("Engage", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Handle form submission
    if submitted:
        if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
            show_animated_loader("Authenticating...", 1.5)
            st.session_state.authenticated = True
            st.session_state.user_email = email
            show_success_message("Authentication Successful. Welcome.")
            time.sleep(1)
            st.rerun()
        else:
            show_error_message("Access Denied. Use official AllWave credentials.")

# The main application function
def main():
    # --- Define asset paths ---
    main_logo_path = Path("assets/company_logo.png")
    
    # --- Handle Authentication and Login Page ---
    if not st.session_state.get('authenticated'):
        main_logo_b64 = image_to_base64(main_logo_path)
        show_login_page(main_logo_b64, str(main_logo_path) if main_logo_path.exists() else "🚀")
        return

    # --- Main App Configuration ---
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon=str(main_logo_path) if main_logo_path.exists() else "🚀", layout="wide", initial_sidebar_state="expanded")
    load_css()

    # --- Initialize Session State ---
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    # --- Load Data and Setup Model ---
    with st.spinner("Initializing system modules..."):
        product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
            for issue in data_issues: st.warning(issue)
    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded."); st.stop()
    model = setup_gemini()

    # --- Display Header and Logos ---
    partner_logos_paths = {
        "Crestron": Path("assets/crestron_logo.png"),
        "AVIXA": Path("assets/avixa_logo.png"),
        "PSNI Global Alliance": Path("assets/iso_logo.png")
    }
    create_header(main_logo_path, partner_logos_paths)

    st.markdown('<div class="glass-container"><h1 class="animated-header">AllWave AV & GS Portal</h1><p style="text-align: center; color: var(--text-secondary);">Professional AV System Design & BOQ Generation Platform</p></div>', unsafe_allow_html=True)

    # --- Sidebar ---
    with st.sidebar:
        # User Info Section
        st.markdown(f'''
        <div class="user-info">
            <h3>👤 Welcome</h3>
            <p>{st.session_state.get("user_email", "Unknown User")}</p>
        </div>
        ''', unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            show_animated_loader("De-authorizing...", 1)
            st.session_state.clear()
            st.rerun()
        
        st.markdown("<hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)
        
        # Mission Parameters Section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🚀 Mission Parameters</h3>', unsafe_allow_html=True)
        
        # ===== NEW FIELDS ADDED HERE =====
        st.text_input("Project Name", key="project_name_input", placeholder="Enter project name")
        st.text_input("Client Name", key="client_name_input", placeholder="Enter client name")
        st.text_input("Location", key="location_input", placeholder="e.g., Mumbai, India")
        st.text_input("Design Engineer", key="design_engineer_input", placeholder="Enter engineer's name")
        st.text_input("Account Manager", key="account_manager_input", placeholder="Enter manager's name")
        st.text_input("Key Client Personnel", key="client_personnel_input", placeholder="Enter client contact name")
        st.text_area("Key Comments for this version", key="comments_input", placeholder="Add any relevant comments...")
        # ==================================

        st.markdown('</div>', unsafe_allow_html=True)
        
        # Financial Config Section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>⚙️ Financial Config</h3>', unsafe_allow_html=True)
        st.selectbox("Currency", ["INR", "USD"], key="currency_select")
        st.session_state.gst_rates['Electronics'] = st.number_input(
            "Hardware GST (%)", 
            value=18, 
            min_value=0, 
            max_value=50
        )
        st.session_state.gst_rates['Services'] = st.number_input(
            "Services GST (%)", 
            value=18, 
            min_value=0, 
            max_value=50
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Environment Design Section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🌐 Environment Design</h3>', unsafe_allow_html=True)
        room_type_key = st.selectbox(
            "Primary Space Type", 
            list(ROOM_SPECS.keys()), 
            key="room_type_select"
        )
        st.select_slider(
            "Budget Tier", 
            options=["Economy", "Standard", "Premium", "Enterprise"], 
            value="Standard", 
            key="budget_tier_slider"
        )
        
        if room_type_key in ROOM_SPECS:
            spec = ROOM_SPECS[room_type_key]
            area_start, area_end = spec.get('area_sqft', ('N/A', 'N/A'))
            cap_start, cap_end = spec.get('capacity', ('N/A', 'N/A'))
            primary_use = spec.get('primary_use', 'N/A')
            
            st.markdown(f"""
            <div class="info-box">
                <p>
                    <b>📐 Area:</b> {area_start}-{area_end} sq ft<br>
                    <b>👥 Capacity:</b> {cap_start}-{cap_end} people<br>
                    <b>🎯 Primary Use:</b> {primary_use}
                </p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Main Content Tabs with Icons ---
    tab_titles = ["📝 Project Scope", "📐 Room Analysis", "📋 Requirements", "🛠️ Generate BOQ", "✨ 3D Visualization"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_titles)

    with tab1:
        st.markdown('<div class="glass-container interactive-card has-corners">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: var(--text-primary);">Multi-Room Project Management</h2>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color: var(--border-color); margin-bottom: 2rem;">', unsafe_allow_html=True)
        create_multi_room_interface()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab2:
        st.markdown('<div class="glass-container interactive-card has-corners">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: var(--text-primary);">AVIXA Standards Calculator</h2>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color: var(--border-color); margin-bottom: 2rem;">', unsafe_allow_html=True)
        create_room_calculator()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab3:
        st.markdown('<div class="glass-container interactive-card has-corners">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: var(--text-primary);">Advanced Technical Requirements</h2>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color: var(--border-color); margin-bottom: 2rem;">', unsafe_allow_html=True)
        technical_reqs = {}
        st.text_area("🎯 Specific Client Needs & Features:", key="features_text_area", placeholder="e.g., 'Must be Zoom certified, requires wireless presentation, needs ADA compliance.'", height=100)
        technical_reqs.update(create_advanced_requirements())
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with tab4:
        st.markdown('<div class="glass-container interactive-card has-corners">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: var(--text-primary);">BOQ Generation Engine</h2>', unsafe_allow_html=True)
        if st.button("✨ Generate & Validate Production-Ready BOQ", type="primary", use_container_width=True, key="generate_boq_btn"):
            if not model:
                show_error_message("AI Model is not available. Please check API key.")
            else:
                progress_bar = st.progress(0, text="Initializing generation pipeline...")
                try:
                    # ... (rest of the code for generation remains the same) ...
                    boq_items, avixa_calcs, equipment_reqs = generate_boq_from_ai(model, product_df, guidelines, st.session_state.room_type_select, st.session_state.budget_tier_slider, st.session_state.features_text_area, technical_reqs, st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16))
                    if boq_items:
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
                        progress_bar.progress(80, text="✅ Step 3: Verifying final system against AVIXA standards...")
                        avixa_validation = validate_avixa_compliance(processed_boq, avixa_calcs, equipment_reqs, st.session_state.room_type_select)
                        st.session_state.validation_results = {"issues": avixa_validation.get('avixa_issues', []), "warnings": avixa_validation.get('avixa_warnings', [])}
                        progress_bar.progress(100, text="Pipeline complete!")
                        time.sleep(1); progress_bar.empty()
                        show_success_message("BOQ generation pipeline completed successfully!")
                        st.rerun()
                    else:
                        progress_bar.empty(); show_error_message("Failed to generate BOQ. The AI and fallback system did not return valid items.")
                except Exception as e:
                    progress_bar.empty(); show_error_message(f"An error occurred during BOQ generation: {str(e)}")

        if st.session_state.get('boq_items'):
            st.markdown("---")
            # ===== PASSING NEW DETAILS TO THE DISPLAY FUNCTION =====
            project_details = {
                "Project Name": st.session_state.get("project_name_input", ""),
                "Client Name": st.session_state.get("client_name_input", ""),
                "Location": st.session_state.get("location_input", ""),
                "Design Engineer": st.session_state.get("design_engineer_input", ""),
                "Account Manager": st.session_state.get("account_manager_input", ""),
                "Key Client Personnel": st.session_state.get("client_personnel_input", ""),
                "Key Comments": st.session_state.get("comments_input", "")
            }
            display_boq_results(product_df, project_details)
            # =======================================================
        st.markdown('</div>', unsafe_allow_html=True)

    with tab5:
        st.markdown('<div class="glass-container interactive-card has-corners">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center; color: var(--text-primary);">3D Room Visualizer</h2>', unsafe_allow_html=True)
        st.markdown('<hr style="border-color: var(--border-color); margin-bottom: 2rem;">', unsafe_allow_html=True)
        create_3d_visualization()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Custom Footer ---
    st.markdown(f'<div class="custom-footer">© {datetime.now().year} AllWave AV & GS. All Rights Reserved.</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
