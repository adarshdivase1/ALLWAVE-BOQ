import streamlit as st
import time
from datetime import datetime

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


# --- "Cyberpunk Aurora" Theme CSS (Full Version) ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;900&family=Rajdhani:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
    
    :root {
        /* Core Colors */
        --bg-primary: #0a0e1a;
        --bg-secondary: #0f1729;
        --bg-tertiary: #141d33;
        
        /* Glassmorphism */
        --glass-bg: rgba(15, 23, 41, 0.85);
        --glass-light: rgba(255, 255, 255, 0.03);
        --glass-border: rgba(255, 255, 255, 0.08);
        
        /* Neon Colors */
        --neon-cyan: #00ffff;
        --neon-pink: #ff00ff;
        --neon-yellow: #ffff00;
        --neon-green: #00ff00;
        --neon-orange: #ff9500;
        --neon-purple: #9945ff;
        
        /* Gradients */
        --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --gradient-cyber: linear-gradient(135deg, #00ffff 0%, #ff00ff 50%, #ffff00 100%);
        --gradient-holographic: linear-gradient(45deg, #00ffff, #ff00ff, #ffff00, #00ffff);
        
        /* Text */
        --text-primary: #ffffff;
        --text-secondary: #94a3b8;
        --text-tertiary: #64748b;
        
        /* Spacing & Borders */
        --border-radius-sm: 8px;
        --border-radius-md: 12px;
        --border-radius-lg: 20px;
        --border-radius-xl: 28px;
        
        /* Shadows */
        --shadow-neon: 0 0 40px rgba(0, 255, 255, 0.5);
        --shadow-deep: 0 20px 60px -10px rgba(0, 0, 0, 0.8);
    }

    /* ============ KEYFRAME ANIMATIONS ============ */
    
    @keyframes matrix-rain { 0% { transform: translateY(-100%); opacity: 0; } 10% { opacity: 1; } 90% { opacity: 1; } 100% { transform: translateY(100vh); opacity: 0; } }
    @keyframes holographic { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    @keyframes cyber-glitch { 0%, 100% { clip-path: polygon(0 0, 100% 0, 100% 100%, 0% 100%); transform: translate(0); } 33% { clip-path: polygon(0 15%, 100% 22%, 100% 85%, 0 92%); transform: translate(-2px, 2px); } 66% { clip-path: polygon(0 8%, 100% 12%, 100% 95%, 0 88%); transform: translate(2px, -2px); } }
    @keyframes neon-pulse { 0%, 100% { box-shadow: 0 0 10px var(--neon-cyan), 0 0 20px var(--neon-cyan), 0 0 30px var(--neon-cyan), inset 0 0 10px rgba(0, 255, 255, 0.1); } 50% { box-shadow: 0 0 20px var(--neon-cyan), 0 0 40px var(--neon-cyan), 0 0 60px var(--neon-cyan), inset 0 0 20px rgba(0, 255, 255, 0.2); } }
    @keyframes float { 0%, 100% { transform: translateY(0px) rotate(0deg); } 33% { transform: translateY(-10px) rotate(1deg); } 66% { transform: translateY(5px) rotate(-1deg); } }
    @keyframes scan-line { 0% { top: -10%; } 100% { top: 110%; } }
    @keyframes data-stream { 0% { background-position: 0 0; } 100% { background-position: 0 100%; } }
    @keyframes rotate-3d { 0% { transform: perspective(1000px) rotateY(0deg); } 100% { transform: perspective(1000px) rotateY(360deg); } }
    
    /* ============ GLOBAL STYLES ============ */
    
    .stApp { background: var(--bg-primary); position: relative; overflow-x: hidden; }
    .stApp::before { content: ''; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-image: repeating-linear-gradient( 0deg, transparent, transparent 2px, rgba(0, 255, 255, 0.03) 2px, rgba(0, 255, 255, 0.03) 4px ), repeating-linear-gradient( 90deg, transparent, transparent 2px, rgba(255, 0, 255, 0.03) 2px, rgba(255, 0, 255, 0.03) 4px ); pointer-events: none; z-index: 1; }
    .stApp::after { content: ''; position: fixed; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient( circle at 20% 80%, rgba(0, 255, 255, 0.1) 0%, transparent 50% ), radial-gradient( circle at 80% 20%, rgba(255, 0, 255, 0.1) 0%, transparent 50% ), radial-gradient( circle at 40% 40%, rgba(255, 255, 0, 0.05) 0%, transparent 50% ); animation: holographic 20s ease infinite; pointer-events: none; z-index: 0; }
    
    /* ============ TYPOGRAPHY ============ */
    
    h1, h2, h3, h4, h5, h6 { font-family: 'Orbitron', monospace !important; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }
    p, span, div, label { font-family: 'Rajdhani', sans-serif; letter-spacing: 0.02em; }
    
    /* ============ GLASS CONTAINERS ============ */
    
    .glass-container { background: linear-gradient(135deg, rgba(15, 23, 41, 0.9) 0%, rgba(20, 29, 51, 0.8) 100%); backdrop-filter: blur(20px) saturate(180%); -webkit-backdrop-filter: blur(20px) saturate(180%); border-radius: var(--border-radius-lg); border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1), inset 0 -1px 0 rgba(0, 0, 0, 0.3); padding: 2.5rem; margin-bottom: 2rem; position: relative; overflow: hidden; z-index: 10; transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); }
    .glass-container::before { content: ''; position: absolute; top: -2px; left: -2px; right: -2px; bottom: -2px; background: var(--gradient-holographic); background-size: 400% 400%; border-radius: var(--border-radius-lg); opacity: 0; z-index: -1; animation: holographic 4s ease infinite; transition: opacity 0.3s ease; }
    .glass-container:hover::before { opacity: 0.8; }
    .glass-container::after { content: ''; position: absolute; left: 0; width: 100%; height: 2px; background: linear-gradient(90deg, transparent, var(--neon-cyan), transparent); animation: scan-line 3s linear infinite; opacity: 0; transition: opacity 0.3s ease; }
    .glass-container:hover::after { opacity: 0.6; }

    /* ============ INTERACTIVE CARDS ============ */
    
    .interactive-card { transform-style: preserve-3d; transform: perspective(1000px) rotateX(0deg) rotateY(0deg); transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1); }
    .interactive-card:hover { transform: perspective(1000px) rotateX(2deg) rotateY(-5deg) scale(1.02); box-shadow: 0 25px 60px rgba(0, 255, 255, 0.3), 0 0 100px rgba(255, 0, 255, 0.2), inset 0 0 30px rgba(255, 255, 255, 0.05); }
    
    /* ============ ANIMATED HEADERS ============ */
    
    .animated-header { font-family: 'Orbitron', monospace; font-size: 3.5rem; font-weight: 900; text-transform: uppercase; background: linear-gradient(90deg, var(--neon-cyan) 0%, var(--neon-pink) 25%, var(--neon-yellow) 50%, var(--neon-cyan) 100%); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; animation: holographic 3s linear infinite; text-align: center; position: relative; text-shadow: 0 0 30px rgba(0, 255, 255, 0.5), 0 0 60px rgba(255, 0, 255, 0.3); margin-bottom: 1rem; }
    .animated-header::after { content: attr(data-text); position: absolute; left: 0; top: 0; width: 100%; height: 100%; z-index: -1; text-shadow: 0 0 10px var(--neon-cyan), 0 0 20px var(--neon-pink), 0 0 30px var(--neon-cyan); opacity: 0.5; animation: cyber-glitch 2s infinite; }
    
    /* ============ BUTTONS ============ */
    
    .stButton > button { font-family: 'Rajdhani', sans-serif; font-weight: 600; font-size: 1.1rem; text-transform: uppercase; letter-spacing: 0.1em; background: linear-gradient(135deg, rgba(0, 255, 255, 0.1) 0%, rgba(255, 0, 255, 0.1) 100%); color: var(--text-primary); border: 2px solid transparent; border-image: linear-gradient(45deg, var(--neon-cyan), var(--neon-pink)) 1; border-radius: var(--border-radius-md); padding: 0.9rem 2.5rem; position: relative; overflow: hidden; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 4px 15px rgba(0, 255, 255, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1); }
    .stButton > button::before { content: ''; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent); transition: left 0.5s ease; }
    .stButton > button:hover::before { left: 100%; }
    .stButton > button:hover { background: linear-gradient(135deg, rgba(0, 255, 255, 0.3) 0%, rgba(255, 0, 255, 0.3) 100%); transform: translateY(-2px) scale(1.02); box-shadow: 0 8px 25px rgba(0, 255, 255, 0.4), 0 0 40px rgba(255, 0, 255, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2); border-image: linear-gradient(45deg, var(--neon-yellow), var(--neon-green)) 1; }
    .stButton > button:active { transform: translateY(0) scale(0.98); }
    .stButton > button[kind="primary"] { background: linear-gradient(135deg, var(--neon-cyan), var(--neon-pink)); border: none; color: var(--bg-primary); font-weight: 700; animation: neon-pulse 2s ease infinite; }
    .stButton > button[kind="primary"]:hover { background: linear-gradient(135deg, var(--neon-pink), var(--neon-yellow)); animation: none; }
    
    /* ============ INPUT FIELDS ============ */
    
    .stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox > div[data-baseweb="select"] > div, .stMultiSelect > div[data-baseweb="select"] > div { font-family: 'Space Mono', monospace; background: linear-gradient(135deg, rgba(15, 23, 41, 0.95) 0%, rgba(20, 29, 51, 0.95) 100%); color: var(--text-primary); border: 1px solid rgba(0, 255, 255, 0.3); border-radius: var(--border-radius-md); padding: 0.75rem 1rem; transition: all 0.3s ease; box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.2), 0 0 10px rgba(0, 255, 255, 0.1); }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus, .stSelectbox > div[data-baseweb="select"] > div[aria-expanded="true"], .stMultiSelect > div[data-baseweb="select"] > div[aria-expanded="true"] { border-color: var(--neon-cyan); box-shadow: 0 0 20px rgba(0, 255, 255, 0.4), inset 0 0 10px rgba(0, 255, 255, 0.1); outline: none; }
    input::placeholder, textarea::placeholder { color: var(--text-tertiary); font-style: italic; }
    
    /* ============ SLIDERS ============ */
    
    div[data-baseweb="slider"] { margin: 1rem 0; }
    div[data-baseweb="slider"] > div { background: linear-gradient(90deg, var(--neon-cyan) 0%, var(--neon-pink) 50%, var(--neon-yellow) 100%); height: 6px; border-radius: 3px; box-shadow: 0 0 15px rgba(0, 255, 255, 0.5); }
    div[data-baseweb="slider"] div[role="slider"] { background: radial-gradient(circle, var(--neon-cyan), var(--neon-pink)); border: 2px solid var(--text-primary); width: 24px; height: 24px; box-shadow: 0 0 20px var(--neon-cyan), 0 0 40px rgba(0, 255, 255, 0.5); transition: all 0.3s ease; }
    div[data-baseweb="slider"] div[role="slider"]:hover { transform: scale(1.2); box-shadow: 0 0 30px var(--neon-cyan), 0 0 60px rgba(0, 255, 255, 0.7); }
    
    /* ============ TABS ============ */
    
    .stTabs [data-baseweb="tab-list"] { background: linear-gradient(135deg, rgba(15, 23, 41, 0.8) 0%, rgba(20, 29, 51, 0.8) 100%); border-radius: var(--border-radius-lg); padding: 0.5rem; border: 1px solid rgba(0, 255, 255, 0.2); gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] { font-family: 'Rajdhani', sans-serif; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; background: transparent; color: var(--text-secondary); border-radius: var(--border-radius-md); padding: 0.75rem 1.5rem; border: 1px solid transparent; transition: all 0.3s ease; }
    .stTabs [data-baseweb="tab"]:hover { background: rgba(0, 255, 255, 0.1); color: var(--neon-cyan); border-color: rgba(0, 255, 255, 0.3); }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, rgba(0, 255, 255, 0.2) 0%, rgba(255, 0, 255, 0.2) 100%); color: var(--text-primary) !important; border: 1px solid var(--neon-cyan); box-shadow: 0 0 20px rgba(0, 255, 255, 0.4), inset 0 0 10px rgba(0, 255, 255, 0.1); }
    
    /* ============ SIDEBAR ============ */
    
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%); border-right: 1px solid rgba(0, 255, 255, 0.2); box-shadow: 4px 0 20px rgba(0, 0, 0, 0.5); }
    section[data-testid="stSidebar"] h3 { color: var(--neon-cyan); text-shadow: 0 0 10px rgba(0, 255, 255, 0.5); }
    
    /* ============ PROGRESS BAR ============ */
    
    .stProgress > div > div { background: linear-gradient(90deg, var(--neon-cyan) 0%, var(--neon-pink) 50%, var(--neon-yellow) 100%); background-size: 200% 100%; animation: holographic 2s linear infinite; border-radius: var(--border-radius-sm); box-shadow: 0 0 20px rgba(0, 255, 255, 0.5); }
    
    /* ============ LOADER ANIMATION ============ */
    
    .loading-spinner { width: 80px; height: 80px; position: relative; margin: 2rem auto; }
    .loading-spinner::before, .loading-spinner::after { content: ''; position: absolute; border-radius: 50%; border: 3px solid transparent; animation: rotate-3d 2s linear infinite; }
    .loading-spinner::before { width: 100%; height: 100%; border-top-color: var(--neon-cyan); border-bottom-color: var(--neon-pink); animation-direction: normal; }
    .loading-spinner::after { width: 70%; height: 70%; top: 15%; left: 15%; border-left-color: var(--neon-yellow); border-right-color: var(--neon-green); animation-direction: reverse; animation-duration: 1.5s; }
    
    /* ============ SCROLLBAR ============ */
    
    ::-webkit-scrollbar { width: 12px; height: 12px; }
    ::-webkit-scrollbar-track { background: var(--bg-secondary); border-radius: var(--border-radius-sm); }
    ::-webkit-scrollbar-thumb { background: linear-gradient(180deg, var(--neon-cyan) 0%, var(--neon-pink) 100%); border-radius: var(--border-radius-sm); border: 2px solid var(--bg-secondary); }
    ::-webkit-scrollbar-thumb:hover { background: linear-gradient(180deg, var(--neon-pink) 0%, var(--neon-yellow) 100%); }
    
    /* ============ EXPANDER ============ */
    
    .st-expander, .streamlit-expanderHeader { background: linear-gradient(135deg, rgba(0, 255, 255, 0.1) 0%, rgba(255, 0, 255, 0.1) 100%); border-radius: var(--border-radius-md); border: 1px solid rgba(0, 255, 255, 0.3); transition: all 0.3s ease; }
    .st-expander:hover, .streamlit-expanderHeader:hover { background: linear-gradient(135deg, rgba(0, 255, 255, 0.2) 0%, rgba(255, 0, 255, 0.2) 100%); border-color: var(--neon-cyan); box-shadow: 0 0 20px rgba(0, 255, 255, 0.3); }
    
    /* ============ DATAFRAME STYLING ============ */
    
    .stDataFrame { border: 1px solid rgba(0, 255, 255, 0.3) !important; border-radius: var(--border-radius-md) !important; background: var(--glass-bg) !important; overflow: hidden !important; }
    .stDataFrame thead th { background: linear-gradient(135deg, rgba(0, 255, 255, 0.2) 0%, rgba(255, 0, 255, 0.2) 100%) !important; color: var(--text-primary) !important; font-family: 'Rajdhani', sans-serif !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; border-bottom: 2px solid var(--neon-cyan) !important; padding: 1rem !important; }
    .stDataFrame tbody tr { background: rgba(15, 23, 41, 0.5) !important; transition: all 0.3s ease !important; }
    .stDataFrame tbody tr:hover { background: rgba(0, 255, 255, 0.1) !important; box-shadow: inset 0 0 20px rgba(0, 255, 255, 0.1) !important; }
    .stDataFrame tbody td { color: var(--text-primary) !important; font-family: 'Space Mono', monospace !important; padding: 0.75rem 1rem !important; border-bottom: 1px solid rgba(0, 255, 255, 0.1) !important; }
    
    /* ============ ALERT BOXES ============ */
    
    .stAlert { background: linear-gradient(135deg, rgba(15, 23, 41, 0.95) 0%, rgba(20, 29, 51, 0.95) 100%) !important; border-left: 4px solid var(--neon-cyan) !important; border-radius: var(--border-radius-md) !important; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important; }
    .stAlert p { color: var(--text-primary) !important; }
    .stAlert[data-baseweb="notification"][kind="error"] { border-left-color: #ff0055 !important; }
    .stAlert[data-baseweb="notification"][kind="success"] { border-left-color: var(--neon-green) !important; }
    .stAlert[data-baseweb="notification"][kind="warning"] { border-left-color: var(--neon-orange) !important; }
    .stAlert[data-baseweb="notification"][kind="info"] { border-left-color: var(--neon-cyan) !important; }
    
    /* ============ HIDE STREAMLIT BRANDING ============ */
    
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

def show_animated_loader(text="Processing...", duration=2):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <div class="loading-spinner"></div>
            <p style="font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: var(--neon-cyan); text-shadow: 0 0 10px var(--neon-cyan); text-transform: uppercase; letter-spacing: 0.1em;">
                {text}
            </p>
        </div>
        """, unsafe_allow_html=True)
    time.sleep(duration); placeholder.empty()

def show_login_page():
    st.set_page_config(page_title="AllWave AV :: BOQ Engine", page_icon="⚡", layout="centered")
    load_css()
    
    st.markdown("""
    <div class="glass-container interactive-card" style="max-width: 500px; margin: 4rem auto;">
        <div style="text-align: center; margin-bottom: 2rem;">
             <h1 class="animated-header" data-text="AllWave AV & GS" style="font-size: 2.5rem;">AllWave AV & GS</h1>
             <p style="color: var(--text-secondary); font-size: 1.1rem;">Cybernetic Design & Estimation Portal</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.text_input("👤 User ID", placeholder="user@allwaveav.com", key="email_input")
        st.text_input("🔑 Access Code", type="password", placeholder="Enter your access code", key="password_input")
        
        if st.form_submit_button("==[ INITIATE CONNECTION ]==", type="primary", use_container_width=True):
            email, password = st.session_state.email_input, st.session_state.password_input
            if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                show_animated_loader("Authenticating Cyberspace Link...", 1.5)
                st.session_state.authenticated = True; st.session_state.user_email = email;
                st.success("Connection Established. Welcome, Operator."); time.sleep(1); st.rerun()
            else:
                st.error("Access Denied. Invalid Credentials.")
    st.markdown("</div>", unsafe_allow_html=True)

def main():
    if not st.session_state.get('authenticated'):
        show_login_page(); return
    st.set_page_config(page_title="AllWave AV :: BOQ Engine", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
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
        with st.expander("⚠️ Data Quality Anomalies Detected!"):
            for issue in data_issues: st.warning(issue)
    if product_df is None:
        st.error("FATAL ERROR: Product Database Offline. System cannot continue."); st.stop()
    model = setup_gemini()

    # --- Main Header ---
    st.markdown('<div class="glass-container interactive-card"><h1 class="animated-header" data-text="BOQ Generation Engine">BOQ Generation Engine</h1><p style="text-align: center; color: var(--text-secondary);">Powered by AllWave AV & GS Cybernetic Intelligence</p></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f'<h3 style="color: var(--text-primary);">OPERATOR:</h3><p style="color: var(--text-secondary); word-wrap: break-word; font-family: \'Space Mono\', monospace;">{st.session_state.get("user_email", "UNKNOWN")}</p>', unsafe_allow_html=True)
        if st.button("==[ DISCONNECT ]=="):
            show_animated_loader("Terminating Session...", 1); st.session_state.clear(); st.rerun()
        st.markdown("---")
        st.markdown('<h3>Mission Parameters</h3>', unsafe_allow_html=True)
        st.text_input("Client Designation", key="client_name_input", placeholder="Enter client name")
        st.text_input("Project Codename", key="project_name_input", placeholder="Enter project name")
        st.markdown("---")
        st.markdown('<h3>Financial Matrix</h3>', unsafe_allow_html=True)
        st.selectbox("Currency Unit", ["INR", "USD"], key="currency_select")
        st.session_state.gst_rates['Electronics'] = st.number_input("Hardware GST (%)", value=18, min_value=0, max_value=50)
        st.session_state.gst_rates['Services'] = st.number_input("Services GST (%)", value=18, min_value=0, max_value=50)
        st.markdown("---")
        st.markdown('<h3>Environment Blueprint</h3>', unsafe_allow_html=True)
        room_type_key = st.selectbox("Primary Space Type", list(ROOM_SPECS.keys()), key="room_type_select")
        st.select_slider("Threat Level (Budget)", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")

    # --- Main Content Tabs ---
    tab_titles = ["Multi-Room Deployment", "Single Zone Analysis", "System Directives", "Generate BOQ", "3D Holo-Deck"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_titles)

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
        st.text_area("Client Directives & Features:", key="features_text_area", placeholder="e.g., 'System must be Zoom-certified, requires wireless presentation protocols, ADA compliance matrix must be met.'", height=120)
        technical_reqs.update(create_advanced_requirements())
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
        st.markdown('</div>', unsafe_allow_html=True)
    with tab4:
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align: center;">BOQ SYNTHESIS</h2>', unsafe_allow_html=True)
        if st.button("==[ EXECUTE GENERATION ]==", type="primary", use_container_width=True, key="generate_boq_btn"):
            if not model:
                st.error("AI Core Offline. Cannot execute generation.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                try:
                    status_text.info("10% :: Engaging AI Core for Initial Design Schema...")
                    progress_bar.progress(10)
                    boq_items, avixa_calcs, equipment_reqs = generate_boq_from_ai(model, product_df, guidelines, st.session_state.room_type_select, st.session_state.budget_tier_slider, st.session_state.features_text_area, technical_reqs, st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16))
                    
                    if boq_items:
                        status_text.info("50% :: Applying AVIXA Heuristics & Correction Subroutines...")
                        progress_bar.progress(50)
                        processed_boq = _remove_exact_duplicates(boq_items)
                        processed_boq = _correct_quantities(processed_boq)
                        processed_boq = _remove_duplicate_core_components(processed_boq)
                        processed_boq = _validate_and_correct_mounts(processed_boq)
                        processed_boq = _ensure_system_completeness(processed_boq, product_df)
                        processed_boq = _flag_hallucinated_models(processed_boq)
                        st.session_state.boq_items = processed_boq
                        update_boq_content_with_current_items()
                        
                        status_text.info("80% :: Final Verification against Compliance Matrix...")
                        progress_bar.progress(80)
                        avixa_validation = validate_avixa_compliance(processed_boq, avixa_calcs, equipment_reqs, st.session_state.room_type_select)
                        st.session_state.validation_results = {"issues": avixa_validation.get('avixa_issues', []), "warnings": avixa_validation.get('avixa_warnings', [])}
                        
                        progress_bar.progress(100)
                        status_text.success("100% :: BOQ Synthesis Complete!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        status_text.error("Generation Failed. AI Core returned no valid items.")
                except Exception as e:
                    status_text.error(f"System Crash! An error occurred: {str(e)}")
        if st.session_state.get('boq_items'):
            st.markdown("---"); display_boq_results(product_df)
        st.markdown('</div>', unsafe_allow_html=True)
    with tab5:
        st.markdown('<div class="glass-container interactive-card">', unsafe_allow_html=True)
        create_3d_visualization()
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
