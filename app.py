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
    # CORRECTED LINE 15 BELOW
    from components.ui_components import (
        create_project_header, create_room_calculator, create_advanced_requirements,
        create_multi_room_interface, display_boq_results, update_boq_content_with_current_items
    )
    from components.visualizer import create_3d_visualization, ROOM_SPECS
except ImportError as e:
    # A placeholder to allow the app to run without the component files
    st.error(f"Failed to import a necessary component: {e}. Please ensure all component files are in the 'components' directory and are complete. Some features may not work.")
    # Define dummy functions if imports fail to prevent crashes
    def load_and_validate_data(): return (None, None, ["Dummy error: component files missing."])
    def setup_gemini(): return None
    def generate_boq_from_ai(*args, **kwargs): return ([], {}, {})
    def validate_avixa_compliance(*args, **kwargs): return {}
    def _remove_exact_duplicates(items): return items
    def _remove_duplicate_core_components(items): return items
    def _validate_and_correct_mounts(items): return items
    def _ensure_system_completeness(items, df): return items
    def _flag_hallucinated_models(items): return items
    def _correct_quantities(items): return items
    def create_project_header(): pass
    def create_room_calculator(): pass
    def create_advanced_requirements(): return {}
    def create_multi_room_interface(): pass
    def display_boq_results(df): pass
    def update_boq_content_with_current_items(): pass
    def create_3d_visualization(): pass
    ROOM_SPECS = {"Standard Conference Room": {}}


# --- Futuristic CSS Styling ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Orbitron:wght@400;500;700;900&display=swap');

    /* Global Styles - Dark Futuristic Theme */
    .stApp {
        background: #0a0e27;
        background-image:
            radial-gradient(at 20% 30%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
            radial-gradient(at 80% 70%, rgba(139, 92, 246, 0.15) 0px, transparent 50%),
            radial-gradient(at 50% 50%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
        font-family: 'Space Grotesk', sans-serif;
        color: #e2e8f0;
        position: relative;
        overflow-x: hidden;
    }

    /* Animated Background Grid */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image:
            linear-gradient(rgba(59, 130, 246, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59, 130, 246, 0.03) 1px, transparent 1px);
        background-size: 50px 50px;
        animation: gridMove 20s linear infinite;
        pointer-events: none;
        z-index: 0;
    }

    @keyframes gridMove {
        0% { transform: translateY(0); }
        100% { transform: translateY(50px); }
    }

    /* Main container styling */
    .main-container {
        background: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(20px) saturate(180%);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 1.5rem;
        box-shadow:
            0 0 60px rgba(59, 130, 246, 0.1),
            inset 0 0 60px rgba(59, 130, 246, 0.02),
            0 20px 60px rgba(0, 0, 0, 0.3);
        border: 1px solid rgba(59, 130, 246, 0.2);
        position: relative;
        overflow: hidden;
        animation: containerFadeIn 0.8s ease-out;
    }

    .main-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.1), transparent);
        animation: scanline 3s infinite;
    }

    @keyframes scanline {
        0%, 100% { left: -100%; }
        50% { left: 100%; }
    }

    @keyframes containerFadeIn {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Animated Futuristic Header */
    .animated-header {
        text-align: center;
        font-family: 'Orbitron', sans-serif;
        font-size: 4rem;
        font-weight: 900;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #10b981 100%);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 4s ease infinite, textGlow 2s ease-in-out infinite;
        text-shadow: 0 0 40px rgba(59, 130, 246, 0.5);
        position: relative;
        letter-spacing: 2px;
    }

    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    @keyframes textGlow {
        0%, 100% { filter: brightness(1) drop-shadow(0 0 10px rgba(59, 130, 246, 0.5)); }
        50% { filter: brightness(1.3) drop-shadow(0 0 20px rgba(59, 130, 246, 0.8)); }
    }

    .subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1.3rem;
        font-weight: 400;
        margin-bottom: 2.5rem;
        animation: fadeInUp 1s ease-out 0.3s both;
        letter-spacing: 1px;
    }

    /* Login Container - Cyber Style */
    .login-container {
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(30px) saturate(180%);
        border-radius: 32px;
        padding: 3.5rem;
        box-shadow:
            0 0 100px rgba(59, 130, 246, 0.2),
            inset 0 0 100px rgba(59, 130, 246, 0.03),
            0 30px 90px rgba(0, 0, 0, 0.4);
        border: 2px solid rgba(59, 130, 246, 0.3);
        animation: loginFloat 3s ease-in-out infinite, slideInUp 0.8s ease-out;
        max-width: 480px;
        margin: 0 auto;
        position: relative;
        overflow: hidden;
    }

    .login-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: conic-gradient(from 0deg, transparent, rgba(59, 130, 246, 0.1), transparent 60deg);
        animation: rotate 8s linear infinite;
    }

    @keyframes rotate {
        100% { transform: rotate(360deg); }
    }

    @keyframes loginFloat {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }

    .login-header {
        text-align: center;
        margin-bottom: 2.5rem;
        position: relative;
        z-index: 1;
    }

    .company-logo {
        font-size: 4rem;
        margin-bottom: 1rem;
        animation: logoPulse 2s ease-in-out infinite;
        filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.6));
    }

    @keyframes logoPulse {
        0%, 100% { transform: scale(1); filter: drop-shadow(0 0 20px rgba(59, 130, 246, 0.6)); }
        50% { transform: scale(1.1); filter: drop-shadow(0 0 30px rgba(59, 130, 246, 0.9)); }
    }

    .company-title {
        font-family: 'Orbitron', sans-serif;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.8rem;
        font-weight: 900;
        margin-bottom: 0.5rem;
        letter-spacing: 2px;
    }

    .company-subtitle {
        color: #94a3b8;
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 2rem;
        letter-spacing: 1px;
    }

    /* Futuristic Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.4) !important;
        background: rgba(30, 41, 59, 0.8) !important;
    }

    /* Enhanced Neon Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%) !important;
        color: white !important;
        border: 2px solid rgba(59, 130, 246, 0.5) !important;
        border-radius: 14px !important;
        padding: 0.85rem 2.5rem !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        font-family: 'Space Grotesk', sans-serif !important;
        transition: all 0.4s ease !important;
        box-shadow: 0 0 30px rgba(59, 130, 246, 0.4), inset 0 0 20px rgba(59, 130, 246, 0.1) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        position: relative !important;
        overflow: hidden !important;
    }

    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.2);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }

    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }

    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow: 0 0 50px rgba(59, 130, 246, 0.7), inset 0 0 30px rgba(59, 130, 246, 0.2) !important;
        border-color: rgba(139, 92, 246, 0.8) !important;
    }

    .stButton > button:active {
        transform: translateY(-1px) scale(0.98) !important;
    }

    /* Holographic Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%) !important;
        border-right: 2px solid rgba(59, 130, 246, 0.3) !important;
        box-shadow: 0 0 50px rgba(59, 130, 246, 0.1) !important;
    }

    .sidebar-content {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(59, 130, 246, 0.3);
        box-shadow: 0 0 30px rgba(59, 130, 246, 0.1);
        animation: sidebarPulse 3s ease-in-out infinite;
    }

    @keyframes sidebarPulse {
        0%, 100% { box-shadow: 0 0 30px rgba(59, 130, 246, 0.1); }
        50% { box-shadow: 0 0 40px rgba(59, 130, 246, 0.2); }
    }

    /* Futuristic Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.75rem;
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(20px);
        border-radius: 18px;
        padding: 0.75rem;
        margin-bottom: 2.5rem;
        border: 1px solid rgba(59, 130, 246, 0.2);
        box-shadow: 0 0 30px rgba(59, 130, 246, 0.1);
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 12px;
        padding: 0.85rem 1.75rem;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
        transition: all 0.4s ease;
        border: 1px solid transparent;
        color: #94a3b8;
        letter-spacing: 0.5px;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(59, 130, 246, 0.1);
        border-color: rgba(59, 130, 246, 0.3);
        color: #3b82f6;
        transform: translateY(-2px);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        color: white !important;
        box-shadow: 0 0 30px rgba(59, 130, 246, 0.5), inset 0 0 20px rgba(255, 255, 255, 0.1);
        border-color: rgba(139, 92, 246, 0.5);
        transform: translateY(-2px);
    }

    /* Holographic Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.8) 100%);
        backdrop-filter: blur(20px) saturate(180%);
        border-radius: 20px;
        padding: 2.5rem;
        margin: 1rem 0;
        box-shadow:
            0 0 40px rgba(59, 130, 246, 0.15),
            inset 0 0 40px rgba(59, 130, 246, 0.05),
            0 10px 40px rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(59, 130, 246, 0.3);
        transition: all 0.5s ease;
        position: relative;
        overflow: hidden;
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200%;
        height: 200%;
        background: conic-gradient(from 0deg, transparent, rgba(59, 130, 246, 0.1), transparent 30deg);
        animation: rotate 6s linear infinite;
        opacity: 0;
        transition: opacity 0.5s ease;
    }

    .metric-card:hover::before {
        opacity: 1;
    }

    .metric-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow:
            0 0 60px rgba(59, 130, 246, 0.3),
            inset 0 0 60px rgba(59, 130, 246, 0.08),
            0 20px 60px rgba(0, 0, 0, 0.3);
        border-color: rgba(59, 130, 246, 0.5);
    }

    /* Progress Container with Neon Effect */
    .progress-container {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(20px);
        border-radius: 18px;
        padding: 2rem;
        margin: 1.5rem 0;
        border: 1px solid rgba(59, 130, 246, 0.3);
        box-shadow: 0 0 40px rgba(59, 130, 246, 0.15);
        position: relative;
    }

    /* Enhanced Loading Animations */
    .loading-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 4rem;
    }

    .loading-spinner {
        width: 80px;
        height: 80px;
        border: 4px solid rgba(59, 130, 246, 0.2);
        border-top: 4px solid #3b82f6;
        border-right: 4px solid #8b5cf6;
        border-radius: 50%;
        animation: spin 1s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
        box-shadow: 0 0 40px rgba(59, 130, 246, 0.5);
        position: relative;
    }

    .loading-spinner::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 60px;
        height: 60px;
        border: 3px solid rgba(139, 92, 246, 0.3);
        border-bottom: 3px solid #8b5cf6;
        border-radius: 50%;
        transform: translate(-50%, -50%);
        animation: spin 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite reverse;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    /* Success/Error Holographic States */
    .success-container {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(5, 150, 105, 0.2) 100%);
        backdrop-filter: blur(20px);
        color: #a7f3d0;
        border: 2px solid rgba(16, 185, 129, 0.5);
        border-radius: 18px;
        padding: 2rem;
        margin: 1.5rem 0;
        animation: slideInUp 0.5s ease-out, successPulse 2s ease-in-out infinite;
        box-shadow: 0 0 40px rgba(16, 185, 129, 0.3);
    }

    @keyframes successPulse {
        0%, 100% { box-shadow: 0 0 40px rgba(16, 185, 129, 0.3); }
        50% { box-shadow: 0 0 60px rgba(16, 185, 129, 0.5); }
    }

    .error-container {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.2) 100%);
        backdrop-filter: blur(20px);
        color: #fca5a5;
        border: 2px solid rgba(239, 68, 68, 0.5);
        border-radius: 18px;
        padding: 2rem;
        margin: 1.5rem 0;
        animation: slideInUp 0.5s ease-out, errorPulse 2s ease-in-out infinite;
        box-shadow: 0 0 40px rgba(239, 68, 68, 0.3);
    }

    @keyframes errorPulse {
        0%, 100% { box-shadow: 0 0 40px rgba(239, 68, 68, 0.3); }
        50% { box-shadow: 0 0 60px rgba(239, 68, 68, 0.5); }
    }

    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(50px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* Holographic Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.5), transparent);
        margin: 2rem 0;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .animated-header {
            font-size: 2.5rem;
        }

        .login-container {
            margin: 1rem;
            padding: 2.5rem;
        }

        .metric-card {
            margin: 0.5rem 0;
            padding: 1.75rem;
        }
    }

    /* Hide Streamlit Branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Neon Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.5);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #3b82f6 0%, #8b5cf6 100%);
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #8b5cf6 0%, #3b82f6 100%);
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.8);
    }

    /* Select Box Styling */
    .stSelectbox > div > div {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
    }

    /* Slider Styling */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%) !important;
    }

    /* Data Frame Styling */
    .dataframe {
        background: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
    }

    /* Expander Styling */
    .streamlit-expanderHeader {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: 12px !important;
        color: #e2e8f0 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def show_animated_loader(text="Processing...", duration=2):
    """Show a futuristic animated loader with text"""
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
        <div class="loading-container">
            <div class="loading-spinner"></div>
            <div style="text-align: center; margin-top: 2rem; font-weight: 700; color: #3b82f6; font-size: 1.2rem; letter-spacing: 1px; text-transform: uppercase;">
                {text}
            </div>
        </div>
        """, unsafe_allow_html=True)

    time.sleep(duration)
    placeholder.empty()


def show_success_message(message):
    """Show a holographic success message"""
    st.markdown(f"""
    <div class="success-container">
        <div style="display: flex; align-items: center; gap: 1.5rem;">
            <div style="font-size: 2.5rem;">✅</div>
            <div style="font-weight: 700; font-size: 1.2rem; letter-spacing: 0.5px;">{message}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_error_message(message):
    """Show a holographic error message"""
    st.markdown(f"""
    <div class="error-container">
        <div style="display: flex; align-items: center; gap: 1.5rem;">
            <div style="font-size: 2.5rem;">❌</div>
            <div style="font-weight: 700; font-size: 1.2rem; letter-spacing: 0.5px;">{message}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def create_metric_card(title, value, subtitle="", icon="📊"):
    """Create a holographic metric card"""
    st.markdown(f"""
    <div class="metric-card">
        <div style="display: flex; align-items: center; gap: 1.5rem; margin-bottom: 1.5rem;">
            <div style="font-size: 3rem; filter: drop-shadow(0 0 10px rgba(59, 130, 246, 0.5));">{icon}</div>
            <div>
                <h3 style="margin: 0; color: #e2e8f0; font-weight: 700; font-size: 1.3rem; letter-spacing: 0.5px;">{title}</h3>
                <p style="margin: 0; color: #94a3b8; font-size: 0.95rem; margin-top: 0.3rem;">{subtitle}</p>
            </div>
        </div>
        <div style="font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">{value}</div>
    </div>
    """, unsafe_allow_html=True)


# --- Enhanced Login Page ---
def show_login_page():
    """Futuristic holographic login page"""
    # Create centered login container
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <div class="company-logo">⚡</div>
                <h1 class="company-title">ALLWAVE AV & GS</h1>
                <p class="company-subtitle">FUTURE OF AV DESIGN</p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            st.text_input(
                "📧 SECURE ACCESS",
                placeholder="yourname@allwaveav.com or yourname@allwavegs.com",
                key="email_input"
            )
            st.text_input(
                "🔒 AUTHORIZATION KEY",
                type="password",
                placeholder="Enter your secure password",
                key="password_input"
            )

            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                login_clicked = st.form_submit_button(
                    "🚀 INITIALIZE SYSTEM",
                    type="primary",
                    use_container_width=True
                )

            if login_clicked:
                email = st.session_state.email_input
                password = st.session_state.password_input

                if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                    show_animated_loader("⚡ AUTHENTICATING CREDENTIALS...", 1.5)
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.login_time = datetime.now()
                    show_success_message("🎯 AUTHENTICATION SUCCESSFUL! INITIALIZING SYSTEM...")
                    time.sleep(1)
                    st.rerun()
                else:
                    show_error_message("⚠️ AUTHENTICATION FAILED: Invalid credentials or unauthorized domain.")

        st.markdown("""
            </div>
        """, unsafe_allow_html=True)

        # Add footer info
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: rgba(255, 255, 255, 0.5);">
            <p>🔐 SECURE ACCESS PORTAL - PHASE 1 INTERNAL TOOL</p>
            <p style="font-size: 0.8rem;">POWERED BY AI • QUANTUM SECURE • NEXT-GEN ARCHITECTURE</p>
            <p style="font-size: 0.75rem; margin-top: 0.5rem;">Contact IT Support for access issues</p>
        </div>
        """, unsafe_allow_html=True)

# --- Enhanced Main Application ---
def main():
    # Call st.set_page_config() as the first Streamlit command
    st.set_page_config(
        page_title="AllWave AV - BOQ Generator",
        page_icon="⚡",
        layout="wide" if st.session_state.get('authenticated') else "centered",
        initial_sidebar_state="expanded" if st.session_state.get('authenticated') else "collapsed"
    )

    load_css()

    # Check authentication AFTER page config
    if not st.session_state.get('authenticated'):
        show_login_page()
        return

    # --- Initialize Session State ---
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    # --- Load Data and Setup Model ---
    with st.spinner("🔄 Loading product catalog and AI models..."):
        product_df, guidelines, data_issues = load_and_validate_data()

    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=False):
            for issue in data_issues:
                st.warning(issue)

    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded. App cannot continue.")
        st.stop()

    model = setup_gemini()

    # --- Enhanced Header ---
    st.markdown("""
    <div class="main-container">
        <h1 class="animated-header">⚡ ALLWAVE AV & GS NEXUS ⚡</h1>
        <p class="subtitle">QUANTUM-POWERED AV SYSTEM DESIGN & BOQ GENERATION MATRIX</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Enhanced Sidebar ---
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-content">
            <h3 style="color: #e2e8f0; margin-bottom: 1rem;">👤 OPERATOR ACCESS</h3>
            <p style="color: #94a3b8; margin-bottom: 1rem; font-size: 0.9rem;">
                {st.session_state.get('user_email', 'Unknown')}
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 SYSTEM LOGOUT", type="secondary", use_container_width=True):
            show_animated_loader("⚡ DISCONNECTING...", 1)
            st.session_state.clear()
            st.rerun()

        st.markdown("---")

        st.markdown("""
        <div class="sidebar-content">
            <h3 style="color: #e2e8f0; margin-bottom: 1rem;">📋 PROJECT MATRIX</h3>
        </div>
        """, unsafe_allow_html=True)

        st.text_input("👤 Client Identity", key="client_name_input", placeholder="Enter client designation")
        st.text_input("🏗️ Project Codename", key="project_name_input", placeholder="Enter project identifier")

        st.markdown("---")

        st.markdown("""
        <div class="sidebar-content">
            <h3 style="color: #e2e8f0; margin-bottom: 1rem;">🇮🇳 FINANCIAL PARAMETERS</h3>
        </div>
        """, unsafe_allow_html=True)

        st.session_state['currency'] = st.selectbox(
            "💱 Currency Protocol",
            ["INR", "USD"],
            index=0,
            key="currency_select"
        )
        st.session_state.gst_rates['Electronics'] = st.number_input(
            "🔧 Hardware GST (%)",
            value=18,
            min_value=0,
            max_value=50
        )
        st.session_state.gst_rates['Services'] = st.number_input(
            "⚙️ Services GST (%)",
            value=18,
            min_value=0,
            max_value=50
        )

        st.markdown("---")

        st.markdown("""
        <div class="sidebar-content">
            <h3 style="color: #e2e8f0; margin-bottom: 1rem;">🏢 SPACE CONFIGURATION</h3>
        </div>
        """, unsafe_allow_html=True)

        room_type_key = st.selectbox(
            "🎯 Space Classification:",
            list(ROOM_SPECS.keys()),
            key="room_type_select"
        )
        st.select_slider(
            "💰 Investment Tier:",
            options=["Economy", "Standard", "Premium", "Enterprise"],
            value="Standard",
            key="budget_tier_slider"
        )

        if room_type_key in ROOM_SPECS:
            spec = ROOM_SPECS[room_type_key]
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.8); padding: 1rem; border-radius: 12px; margin-top: 1rem; border: 1px solid rgba(59, 130, 246, 0.3);">
                <p style="color: #94a3b8; margin: 0; font-size: 0.9rem;">
                    📐 Surface Area: {spec.get('area_sqft', ('N/A', 'N/A'))[0]}-{spec.get('area_sqft', ('N/A', 'N/A'))[1]} sq ft<br>
                    ⚡ Complexity Index: {spec.get('complexity', 'N/A')}
                </p>
            </div>
            """, unsafe_allow_html=True)

    # --- Enhanced Main Content Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏢 MULTI-SPACE MATRIX",
        "📊 SPACE ANALYTICS",
        "⚙️ SYSTEM SPECS",
        "📋 BOQ GENERATOR",
        "🎮 3D HOLOGRAM"
    ])

    with tab1:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        create_multi_room_interface()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        create_room_calculator()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        technical_reqs = {}
        st.text_area(
            "🎯 Advanced Requirements Matrix:",
            key="features_text_area",
            placeholder="e.g., 'Quantum-secure conferencing, Neural interface support, AI-driven automation, Biometric access control'",
            height=100
        )
        technical_reqs.update(create_advanced_requirements())
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab4:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.markdown("""
        <h2 style="color: #e2e8f0; margin-bottom: 2rem; display: flex; align-items: center; gap: 1rem; font-family: 'Orbitron', sans-serif;">
            <span style="font-size: 2rem;">🚀</span>
            NEURAL BOQ GENERATION PROTOCOL
        </h2>
        """, unsafe_allow_html=True)

        col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
        with col_gen2:
            if st.button(
                "⚡ INITIATE QUANTUM BOQ SYNTHESIS",
                type="primary",
                use_container_width=True,
                key="generate_boq_btn"
            ):
                if not model:
                    show_error_message("⚠️ NEURAL CORE UNAVAILABLE: API connection failed")
                else:
                    # Enhanced progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    try:
                        # Step 1
                        status_text.markdown("🔄 **PHASE 1:** Neural network analyzing space parameters...")
                        progress_bar.progress(25)
                        time.sleep(0.5)

                        boq_items, avixa_calcs, equipment_reqs = generate_boq_from_ai(
                            model, product_df, guidelines,
                            st.session_state.room_type_select, st.session_state.budget_tier_slider,
                            st.session_state.features_text_area, technical_reqs,
                            st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                        )

                        if boq_items:
                            # Step 2
                            status_text.markdown("⚙️ **PHASE 2:** Applying AVIXA quantum correction protocols...")
                            progress_bar.progress(50)
                            time.sleep(0.5)

                            # --- Full Validation and Correction Pipeline ---
                            processed_boq = _remove_exact_duplicates(boq_items)
                            processed_boq = _correct_quantities(processed_boq)
                            processed_boq = _remove_duplicate_core_components(processed_boq)
                            processed_boq = _validate_and_correct_mounts(processed_boq)
                            processed_boq = _ensure_system_completeness(processed_boq, product_df)
                            processed_boq = _flag_hallucinated_models(processed_boq)

                            progress_bar.progress(75)
                            time.sleep(0.5)

                            st.session_state.boq_items = processed_boq
                            update_boq_content_with_current_items()

                            if st.session_state.project_rooms:
                                st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = boq_items

                            # Step 3
                            status_text.markdown("✅ **PHASE 3:** Verifying system integrity against standards matrix...")
                            progress_bar.progress(100)
                            time.sleep(0.5)

                            avixa_validation = validate_avixa_compliance(
                                processed_boq, avixa_calcs, equipment_reqs, st.session_state.room_type_select
                            )
                            st.session_state.validation_results = {
                                "issues": avixa_validation.get('avixa_issues', []),
                                "warnings": avixa_validation.get('avixa_warnings', [])
                            }

                            # Clear progress indicators
                            progress_bar.empty()
                            status_text.empty()

                            show_success_message("⚡ QUANTUM BOQ SYNTHESIS COMPLETE!")
                            time.sleep(1)
                            st.rerun()

                        else:
                            progress_bar.empty()
                            status_text.empty()
                            show_error_message("❌ SYNTHESIS FAILED: Neural network returned null matrix")

                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        show_error_message(f"⚠️ SYSTEM ERROR: {str(e)}")

        if st.session_state.get('boq_items'):
            st.markdown("---")
            display_boq_results(product_df)

        st.markdown('</div>', unsafe_allow_html=True)

    with tab5:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        create_3d_visualization()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Footer ---
    st.markdown("""
    <div style="text-align: center; margin-top: 3rem; padding: 2rem; color: rgba(255, 255, 255, 0.4);">
        <p style="font-family: 'Orbitron', sans-serif; font-size: 1.1rem;">⚡ ALLWAVE AV & GS • QUANTUM AV SOLUTIONS • NEURAL-POWERED DESIGN</p>
        <p style="font-size: 0.8rem; margin-top: 0.5rem;">© 2024 AllWave Technologies. Classified System. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
