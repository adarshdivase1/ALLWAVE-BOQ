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


# --- Enhanced CSS Styling ---
def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container styling */
    .main-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2rem;
        margin: 1rem;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Animated header */
    .animated-header {
        text-align: center;
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 3.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        animation: fadeInUp 1s ease-out;
    }
    
    .subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 1.2rem;
        font-weight: 400;
        margin-bottom: 2rem;
        animation: fadeInUp 1s ease-out 0.2s both;
    }
    
    /* Login form styling */
    .login-container {
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 3rem;
        box-shadow: 0 25px 80px rgba(0, 0, 0, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.3);
        animation: slideInUp 0.8s ease-out;
        max-width: 450px;
        margin: 0 auto;
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .company-logo {
        font-size: 3rem;
        margin-bottom: 1rem;
        animation: pulse 2s infinite;
    }
    
    .company-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .company-subtitle {
        color: #6b7280;
        font-size: 1.1rem;
        font-weight: 500;
        margin-bottom: 2rem;
    }
    
    /* Enhanced buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    .primary-button {
        background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%) !important;
        animation: glow 2s ease-in-out infinite alternate;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    .sidebar-content {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border-radius: 15px;
        padding: 0.5rem;
        margin-bottom: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Cards and containers */
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(255, 255, 255, 0.7) 100%);
        backdrop-filter: blur(20px);
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
    }
    
    .progress-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
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
    
    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.05);
        }
    }
    
    @keyframes glow {
        from {
            box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
        }
        to {
            box-shadow: 0 8px 30px rgba(255, 107, 107, 0.6);
        }
    }
    
    @keyframes shimmer {
        0% {
            background-position: -200px 0;
        }
        100% {
            background-position: calc(200px + 100%) 0;
        }
    }
    
    .shimmer {
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
        background-size: 200px 100%;
        animation: shimmer 2s infinite;
    }
    
    /* Loading animations */
    .loading-container {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 3rem;
    }
    
    .loading-spinner {
        width: 60px;
        height: 60px;
        border: 4px solid rgba(102, 126, 234, 0.3);
        border-top: 4px solid #667eea;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Success/Error states */
    .success-container {
        background: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
        color: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        animation: slideInUp 0.5s ease-out;
    }
    
    .error-container {
        background: linear-gradient(135deg, #ff6b6b 0%, #ffa8a8 100%);
        color: white;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
        animation: slideInUp 0.5s ease-out;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .animated-header {
            font-size: 2.5rem;
        }
        
        .login-container {
            margin: 1rem;
            padding: 2rem;
        }
        
        .metric-card {
            margin: 0.5rem 0;
            padding: 1.5rem;
        }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    </style>
    """, unsafe_allow_html=True)


def show_animated_loader(text="Processing...", duration=2):
    """Show an animated loader with text"""
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f"""
        <div class="loading-container">
            <div class="loading-spinner"></div>
        </div>
        <div style="text-align: center; margin-top: 1rem; font-weight: 600; color: #667eea;">
            {text}
        </div>
        """, unsafe_allow_html=True)
    
    time.sleep(duration)
    placeholder.empty()


def show_success_message(message):
    """Show an animated success message"""
    st.markdown(f"""
    <div class="success-container">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2rem;">✅</div>
            <div style="font-weight: 600; font-size: 1.1rem;">{message}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_error_message(message):
    """Show an animated error message"""
    st.markdown(f"""
    <div class="error-container">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2rem;">❌</div>
            <div style="font-weight: 600; font-size: 1.1rem;">{message}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def create_metric_card(title, value, subtitle="", icon="📊"):
    """Create an animated metric card"""
    st.markdown(f"""
    <div class="metric-card">
        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
            <div style="font-size: 2.5rem;">{icon}</div>
            <div>
                <h3 style="margin: 0; color: #1f2937; font-weight: 700;">{title}</h3>
                <p style="margin: 0; color: #6b7280; font-size: 0.9rem;">{subtitle}</p>
            </div>
        </div>
        <div style="font-size: 2rem; font-weight: 700; color: #667eea;">{value}</div>
    </div>
    """, unsafe_allow_html=True)


# --- Enhanced Login Page ---
def show_login_page():
    """Enhanced login page with animations and modern design"""
    st.set_page_config(
        page_title="AllWave AV - BOQ Generator", 
        page_icon="⚡",
        layout="centered"
    )
    
    load_css()
    
    # Create centered login container
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-header">
                <div class="company-logo">🏢</div>
                <h1 class="company-title">AllWave AV & GS</h1>
                <p class="company-subtitle">Design & Estimation Portal</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.text_input(
                "📧 Email ID", 
                placeholder="yourname@allwaveav.com or yourname@allwavegs.com",
                key="email_input"
            )
            st.text_input(
                "🔒 Password", 
                type="password", 
                placeholder="Enter your password",
                key="password_input"
            )
            
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                login_clicked = st.form_submit_button(
                    "🚀 Login", 
                    type="primary", 
                    use_container_width=True
                )
            
            if login_clicked:
                email = st.session_state.email_input
                password = st.session_state.password_input
                
                if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                    show_animated_loader("Authenticating...", 1.5)
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.login_time = datetime.now()
                    show_success_message("Login successful! Welcome to AllWave AV & GS Portal")
                    time.sleep(1)
                    st.rerun()
                else:
                    show_error_message("Please use your AllWave AV or AllWave GS email and a valid password.")
        
        st.markdown("""
            </div>
        """, unsafe_allow_html=True)
        
        # Add footer info
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: rgba(255, 255, 255, 0.7);">
            <p>🔐 Phase 1 Internal Tool - Contact IT for access issues</p>
            <p style="font-size: 0.8rem;">Powered by AI • Secure • Professional</p>
        </div>
        """, unsafe_allow_html=True)


# --- Enhanced Main Application ---
def main():
    if not st.session_state.get('authenticated'):
        show_login_page()
        return

    st.set_page_config(
        page_title="AllWave AV - BOQ Generator",
        page_icon="⚡",
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
        <h1 class="animated-header">AllWave AV & GS Portal</h1>
        <p class="subtitle">Professional AV System Design & BOQ Generation Platform</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Enhanced Sidebar ---
    with st.sidebar:
        st.markdown(f"""
        <div class="sidebar-content">
            <h3 style="color: white; margin-bottom: 1rem;">👤 Welcome!</h3>
            <p style="color: rgba(255, 255, 255, 0.8); margin-bottom: 1rem;">
                {st.session_state.get('user_email', 'Unknown')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            show_animated_loader("Logging out...", 1)
            st.session_state.clear()
            st.rerun()
        
        st.markdown("---")
        
        st.markdown("""
        <div class="sidebar-content">
            <h3 style="color: white; margin-bottom: 1rem;">📋 Project Configuration</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.text_input("👤 Client Name", key="client_name_input", placeholder="Enter client name")
        st.text_input("🏗️ Project Name", key="project_name_input", placeholder="Enter project name")

        st.markdown("---")
        
        st.markdown("""
        <div class="sidebar-content">
            <h3 style="color: white; margin-bottom: 1rem;">🇮🇳 Business Settings</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.session_state['currency'] = st.selectbox(
            "💱 Currency Display", 
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
            <h3 style="color: white; margin-bottom: 1rem;">🏢 Room Design Settings</h3>
        </div>
        """, unsafe_allow_html=True)
        
        room_type_key = st.selectbox(
            "🎯 Primary Space Type:", 
            list(ROOM_SPECS.keys()), 
            key="room_type_select"
        )
        st.select_slider(
            "💰 Budget Tier:", 
            options=["Economy", "Standard", "Premium", "Enterprise"], 
            value="Standard", 
            key="budget_tier_slider"
        )
        
        if room_type_key in ROOM_SPECS:
            spec = ROOM_SPECS[room_type_key]
            st.markdown(f"""
            <div style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                <p style="color: rgba(255, 255, 255, 0.8); margin: 0;">
                    📐 Area: {spec.get('area_sqft', ('N/A', 'N/A'))[0]}-{spec.get('area_sqft', ('N/A', 'N/A'))[1]} sq ft<br>
                    ⚡ Complexity: {spec.get('complexity', 'N/A')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        
    # --- Enhanced Main Content Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏢 Multi-Room Project", 
        "📊 Room Analysis", 
        "⚙️ Requirements", 
        "📋 Generate BOQ", 
        "🎮 3D Visualization"
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
            "🎯 Specific Client Needs & Features:", 
            key="features_text_area", 
            placeholder="e.g., 'Must be Zoom certified, requires wireless presentation for 10 users, needs ADA compliance.'",
            height=100
        )
        technical_reqs.update(create_advanced_requirements())
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab4:
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.markdown("""
        <h2 style="color: #1f2937; margin-bottom: 2rem; display: flex; align-items: center; gap: 1rem;">
            <span style="font-size: 2rem;">🚀</span>
            Professional BOQ Generation
        </h2>
        """, unsafe_allow_html=True)
        
        col_gen1, col_gen2, col_gen3 = st.columns([1, 2, 1])
        with col_gen2:
            if st.button(
                "✨ Generate & Validate Production-Ready BOQ", 
                type="primary", 
                use_container_width=True,
                key="generate_boq_btn"
            ):
                if not model:
                    show_error_message("AI Model is not available. Please check API key.")
                else:
                    # Enhanced progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # Step 1
                        status_text.markdown("🔄 **Step 1:** Generating initial design with AI...")
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
                            status_text.markdown("⚙️ **Step 2:** Applying AVIXA-based logic and correction rules...")
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
                            status_text.markdown("✅ **Step 3:** Verifying final system against AVIXA standards...")
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
                            
                            show_success_message("BOQ generation pipeline completed successfully!")
                            time.sleep(1)
                            st.rerun()
                            
                        else:
                            progress_bar.empty()
                            status_text.empty()
                            show_error_message("Failed to generate BOQ. The AI and fallback system did not return valid items.")
                            
                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        show_error_message(f"An error occurred during BOQ generation: {str(e)}")
        
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
    <div style="text-align: center; margin-top: 3rem; padding: 2rem; color: rgba(0, 0, 0, 0.6);">
        <p>🏢 AllWave AV & GS • Professional AV Solutions • Powered by AI</p>
        <p style="font-size: 0.8rem;">© 2024 AllWave Technologies. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
