# app.py - ENHANCED VERSION with quality score calculation and display

import streamlit as st
import time
from datetime import datetime
import base64
from pathlib import Path
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('boq_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Component Imports ---
try:
    from components.database_handler import (
        initialize_firebase, save_project, load_projects, restore_project_state
    )
    from components.room_profiles import ROOM_SPECS
    from components.data_handler import load_and_validate_data
    from components.gemini_handler import setup_gemini
    from components.ui_components import (
        create_project_header, create_room_calculator, create_advanced_requirements,
        create_multi_room_interface, display_boq_results, update_boq_content_with_current_items
    )
    from components.visualizer import create_3d_visualization
    from components.smart_questionnaire import SmartQuestionnaire, show_smart_questionnaire_tab
    
    # ✅ ADD THIS LINE:
    from components.multi_room_optimizer import MultiRoomOptimizer  # NEW IMPORT
    
except ImportError as e:
    st.error(f"Failed to import a necessary component: {e}")
    st.stop()


def load_css():
    """Reads the style.css file and injects it into the Streamlit app."""
    css_file_path = "assets/style.css"
    try:
        with open(css_file_path, "r") as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Could not find style.css at '{css_file_path}'")


def show_animated_loader(text="Processing...", duration=2):
    """Displays a custom animated loading spinner."""
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 2rem;"><div style="position: relative; width: 80px; height: 80px;"><div style="position: absolute; width: 100%; height: 100%; border-radius: 50%; border: 4px solid transparent; border-top-color: var(--glow-primary); animation: spin 1.2s linear infinite;"></div><div style="position: absolute; width: 80%; height: 80%; top: 10%; left: 10%; border-radius: 50%; border: 4px solid transparent; border-bottom-color: var(--glow-secondary); animation: spin-reverse 1.2s linear infinite;"></div></div><div style="text-align: center; margin-top: 1.5rem; font-weight: 500; color: var(--glow-primary); text-shadow: 0 0 5px var(--glow-primary);">{text}</div></div>', unsafe_allow_html=True)
    time.sleep(duration)
    placeholder.empty()


def show_success_message(message):
    """Displays a custom success message."""
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(16, 185, 129, 0.3) 0%, rgba(16, 185, 129, 0.5) 100%); border: 1px solid rgba(16, 185, 129, 0.8);"> <div style="font-size: 2rem;">✅</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)


def show_error_message(message):
    """Displays a custom error message."""
    st.markdown(f'<div style="display: flex; align-items: center; gap: 1rem; color: var(--text-primary); border-radius: var(--border-radius-md); padding: 1.5rem; margin: 1rem 0; background: linear-gradient(135deg, rgba(220, 38, 38, 0.3) 0%, rgba(220, 38, 38, 0.5) 100%); border: 1px solid rgba(220, 38, 38, 0.8);"> <div style="font-size: 2rem;">❌</div> <div style="font-weight: 600; font-size: 1.1rem;">{message}</div></div>', unsafe_allow_html=True)


@st.cache_data
def image_to_base64(img_path):
    """Converts an image file to a base64 string for embedding in HTML."""
    try:
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


def create_header(main_logo, partner_logos):
    """Creates the header section with main and partner logos."""
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


def validate_required_fields():
    """Validates that all required project fields are filled"""
    required_fields = {
        'project_name_input': 'Project Name',
        'client_name_input': 'Client Name',
        'location_input': 'Location',
        'design_engineer_input': 'Design Engineer',
        'account_manager_input': 'Account Manager'
    }
    
    missing = []
    for key, label in required_fields.items():
        if not st.session_state.get(key, '').strip():
            missing.append(label)
    
    return missing


def show_login_page(logo_b64, page_icon_path):
    """Displays the login page for user authentication."""
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
    
    with st.form(key="login_form", clear_on_submit=False):
        st.markdown('<div class="login-form">', unsafe_allow_html=True)
        email = st.text_input("📧 Email ID", placeholder="yourname@allwaveav.com", key="email_input", label_visibility="collapsed")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="password_input", label_visibility="collapsed")
        
        st.markdown("<hr style='border-color: var(--border-color); margin: 1rem 0;'>", unsafe_allow_html=True)
        
        is_psni = st.radio(
            "Is this project referred/sourced through PSNI Global Alliance?", 
            ("Yes - PSNI Referral", "No - Direct Client"), 
            horizontal=True, 
            key="is_psni_radio",
            help="Select 'Yes' if PSNI recommended your company for this project"
        )

        client_location = st.radio(
            "Client Location & Currency", 
            ("Local (India) - INR", "International - USD"), 
            horizontal=True, 
            key="client_location_radio",
            help="This determines the currency used throughout the proposal"
        )

        existing_customer = st.radio(
            "Client Relationship Status", 
            ("Existing Client", "New Client"), 
            horizontal=True, 
            key="existing_customer_radio",
            help="Existing clients receive preferential pricing"
        )
        submitted = st.form_submit_button("Engage", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    if submitted:
        if email.endswith(("@allwaveav.com", "@allwavegs.com")) and len(password) > 3:
            show_animated_loader("Authenticating...", 1.5)
            st.session_state.authenticated = True
            st.session_state.user_email = email
            
            # UPDATED: Store PSNI referral status
            st.session_state.is_psni_referral = (is_psni == "Yes - PSNI Referral")
            
            # UPDATED: Store client location and set currency
            st.session_state.client_is_local = ("Local" in client_location)
            st.session_state.currency_select = "INR" if st.session_state.client_is_local else "USD"
            
            # Store customer status
            st.session_state.is_existing_customer = (existing_customer == "Existing Client")
            
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

    st.set_page_config(
        page_title="AllWave AV - BOQ Generator",
        page_icon=str(main_logo_path) if main_logo_path.exists() else "🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    load_css()
    
    # Initialize database connection
    db = initialize_firebase()

    # ============= ENHANCED PROJECT LOADING LOGIC =============
    if 'project_to_load' in st.session_state and st.session_state.project_to_load:
        project_name_to_load = st.session_state.project_to_load
        
        # IMPORTANT: Clear the trigger IMMEDIATELY to prevent loops
        st.session_state.project_to_load = None
        
        if 'user_projects' in st.session_state:
            project_data = next(
                (p for p in st.session_state.user_projects if p.get('name') == project_name_to_load),
                None
            )
            
            if project_data:
                # Use the restore function to load EVERYTHING
                if restore_project_state(project_data):
                    update_boq_content_with_current_items()
                    st.session_state.project_loaded_successfully = project_name_to_load
                else:
                    st.session_state.project_load_failed = True
    # ============= END ENHANCED LOADING LOGIC =============

    # Load user's projects from DB once per session
    if 'projects_loaded' not in st.session_state:
        if db:
            user_email = st.session_state.get("user_email")
            st.session_state.user_projects = load_projects(db, user_email)
            st.session_state.projects_loaded = True
        else:
            st.session_state.user_projects = []

    # Session State Initializations
    if 'boq_items' not in st.session_state:
        st.session_state.boq_items = []
    if 'boq_content' not in st.session_state:
        st.session_state.boq_content = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state:
        st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state:
        st.session_state.current_room_index = 0
    # --- CHANGE 2: MODIFIED GST INITIALIZATION ---
    if 'gst_rates' not in st.session_state:
        st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}
    else:
        # Ensure GST rates are always integers
        st.session_state.gst_rates['Electronics'] = int(st.session_state.gst_rates.get('Electronics', 18))
        st.session_state.gst_rates['Services'] = int(st.session_state.gst_rates.get('Services', 18))
    
    # Set currency based on location - This is now set at login, but keep a fallback
    if 'currency_select' not in st.session_state:
        if st.session_state.get('client_is_local'):
            st.session_state.currency_select = "INR"
        else:
            st.session_state.currency_select = "USD"
    
    # Room dimensions
    if 'room_length_input' not in st.session_state:
        st.session_state.room_length_input = 28.0
    if 'room_width_input' not in st.session_state:
        st.session_state.room_width_input = 20.0

    # Load product data
    with st.spinner("Initializing system modules..."):
        product_df, guidelines, data_issues = load_and_validate_data()
        st.session_state.product_df = product_df

    # --- START OF UPDATED DEBUG CODE ---
    if product_df is not None:
        st.sidebar.write("🔍 DEBUG INFO")
        st.sidebar.write(f"Rows: {len(product_df)}")
        st.sidebar.write(f"Columns: {len(product_df.columns)}")
        
        # Show first few column names
        cols_preview = ', '.join(product_df.columns.tolist()[:8])
        st.sidebar.write(f"First cols: {cols_preview}...")
        
        # Check for category column
        if 'category' in product_df.columns:
            st.sidebar.success("✅ 'category' column exists")
            categories = product_df['category'].unique()
            st.sidebar.write(f"Categories: {len(categories)}")
            st.sidebar.write(f"Sample: {', '.join(categories[:3])}")
        else:
            st.sidebar.error("❌ 'category' column MISSING")
            st.sidebar.write("All columns:")
            st.sidebar.write(product_df.columns.tolist())
    # --- END OF UPDATED DEBUG CODE ---
    
    if data_issues:
        with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
            for issue in data_issues:
                st.warning(issue)
    
    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded.")
        st.stop()
    
    model = setup_gemini()

    # Create header
    partner_logos_paths = {
        "Crestron": Path("assets/crestron_logo.png"),
        "AVIXA": Path("assets/avixa_logo.png"),
        "PSNI Global Alliance": Path("assets/iso_logo.png")
    }
    create_header(main_logo_path, partner_logos_paths)

    st.markdown(
        '<div class="glass-container"><h1 class="animated-header">AllWave AV & GS Portal</h1>'
        '<p style="text-align: center; color: var(--text-secondary);">Professional AV System Design & BOQ Generation Platform</p></div>',
        unsafe_allow_html=True
    )

    # Sidebar function
    def update_dimensions_from_room_type():
        room_type = st.session_state.room_type_select
        if room_type in ROOM_SPECS and 'typical_dims_ft' in ROOM_SPECS[room_type]:
            length, width = ROOM_SPECS[room_type]['typical_dims_ft']
            st.session_state.room_length_input = float(length)
            st.session_state.room_width_input = float(width)

    # ============= SIDEBAR =============
    with st.sidebar:
        st.markdown(f'''
        <div class="user-info">
            <h3>👤 Welcome</h3>
            <p>{st.session_state.get("user_email", "Unknown User")}</p>
        </div>
        ''', unsafe_allow_html=True)
        
        if st.session_state.get('is_psni_referral', False):
            st.success("✅ PSNI Global Alliance Referral")
        else:
            st.info("ℹ️ Direct Client Project")

        if st.session_state.get('client_is_local', False):
            st.info("🇮🇳 Local Client (India) - INR Currency")
        else:
            st.info("🌍 International Client - USD Currency")
        
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

        if st.session_state.get('is_existing_customer', False):
            st.success("✅ Existing Customer (Discount Applied)")
        else:
            st.info("ℹ️ New Customer")

        st.text_input("Location", key="location_input", placeholder="e.g., Navi Mumbai, India")
        st.text_input("Design Engineer", key="design_engineer_input", placeholder="Enter engineer's name")
        st.text_input("Account Manager", key="account_manager_input", placeholder="Enter manager's name")
        st.text_input("Key Client Personnel", key="client_personnel_input", placeholder="Enter client contact name")
        st.text_area("Key Comments for this version", key="comments_input", placeholder="Add any relevant comments...")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # ✅ ADD THIS NEW SECTION:
        st.markdown("<hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🔧 Multi-Room Options</h3>', unsafe_allow_html=True)
        
        if len(st.session_state.get('project_rooms', [])) >= 3:
            enable_optimization = st.checkbox(
                "Enable Multi-Room Optimization",
                value=True,
                key="multi_room_optimization_enabled",
                help="Consolidates network switches, racks, and shared infrastructure across 3+ rooms for cost savings"
            )
            
            if enable_optimization:
                st.success(f"✅ Optimizing across {len(st.session_state.project_rooms)} rooms")
            else:
                st.info("ℹ️ Each room will have independent equipment")
        else:
            st.info(f"ℹ️ Multi-room optimization requires 3+ rooms\n\nCurrent: {len(st.session_state.get('project_rooms', []))} room(s)")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>⚙️ Financial Config</h3>', unsafe_allow_html=True)
        
        currency_display = "INR (₹)" if st.session_state.get('client_is_local') else "USD ($)"
        st.text_input("Currency (Auto-set)", value=currency_display, disabled=True, 
                      help="Currency is automatically set based on client location")
        
        st.session_state.gst_rates['Electronics'] = st.number_input(
            "Hardware GST (%)", 
            value=int(st.session_state.gst_rates.get('Electronics', 18)),
            min_value=0, 
            max_value=50
        )
        st.session_state.gst_rates['Services'] = st.number_input(
            "Services GST (%)", 
            value=int(st.session_state.gst_rates.get('Services', 18)),
            min_value=0, 
            max_value=50
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🌍 Environment Design</h3>', unsafe_allow_html=True)
        
        # ============= APPLIED CHANGE HERE =============
        # Determine default room type from questionnaire
        use_case_to_room_type = {
            'Video Conferencing': 'Standard Conference Room (6-8 People)',
            'Presentations & Training': 'Training Room (15-25 People)',
            'Hybrid Meetings': 'Large Conference Room (8-12 People)',
            'Executive Boardroom': 'Executive Boardroom (10-16 People)',
            'Event & Broadcast': 'Multipurpose Event Room (40+ People)',
            'Multipurpose': 'Large Training/Presentation Room (25-40 People)'
        }

        default_room_type = 'Standard Conference Room (6-8 People)'
        if 'client_requirements' in st.session_state:
            req = st.session_state.client_requirements
            default_room_type = use_case_to_room_type.get(
                req.primary_use_case, 
                default_room_type
            )

        # Get current value or use questionnaire-based default
        current_room_type = st.session_state.get('room_type_select', default_room_type)
        room_types_list = list(ROOM_SPECS.keys())

        try:
            default_index = room_types_list.index(current_room_type)
        except ValueError:
            default_index = 0

        room_type_key = st.selectbox(
            "Primary Space Type",
            room_types_list,
            index=default_index,
            key="room_type_select",
            on_change=update_dimensions_from_room_type
        )
        # ===============================================

        if 'initial_load' not in st.session_state:
            update_dimensions_from_room_type()
            st.session_state.initial_load = True

        st.select_slider(
            "Budget Tier",
            options=["Economy", "Standard", "Premium", "Enterprise"],
            value=st.session_state.get('budget_tier_slider', 'Standard'),
            key="budget_tier_slider"
        )
        
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

    # ============= MAIN TABS =============
    tab_titles = ["📋 Project Scope", "🎯 Smart Questionnaire", "🛠️ Generate BOQ", "✨ 3D Visualization"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

    with tab1:
        st.markdown('<h2 class="section-header section-header-project">Project Management</h2>', unsafe_allow_html=True)
        
        # Display messages
        if 'project_loaded_successfully' in st.session_state:
            show_success_message(f"Project '{st.session_state.project_loaded_successfully}' loaded successfully!")
            del st.session_state.project_loaded_successfully
        
        if 'project_load_failed' in st.session_state:
            show_error_message("Failed to load project. Please try again.")
            del st.session_state.project_load_failed
        
        project_name = st.session_state.get('project_name_input', '')
        
        col_save, col_load = st.columns(2)
        with col_save:
            if st.button("💾 Save Current Project", type="primary", use_container_width=True, disabled=not project_name):
                if db:
                    # Save all relevant project data
                    project_data = {
                        'name': project_name,
                        'project_name_input': project_name,
                        'client_name_input': st.session_state.get('client_name_input', ''),
                        'location_input': st.session_state.get('location_input', ''),
                        'design_engineer_input': st.session_state.get('design_engineer_input', ''),
                        'account_manager_input': st.session_state.get('account_manager_input', ''),
                        'client_personnel_input': st.session_state.get('client_personnel_input', ''),
                        'comments_input': st.session_state.get('comments_input', ''),
                        'rooms': st.session_state.get('project_rooms', []),
                        'gst_rates': st.session_state.get('gst_rates', {}),
                        'currency': st.session_state.get('currency_select', 'USD'),
                        'room_type': st.session_state.get('room_type_select', ''),
                        'budget_tier': st.session_state.get('budget_tier_slider', 'Standard'),
                        'room_length': st.session_state.get('room_length_input', 28.0),
                        'room_width': st.session_state.get('room_width_input', 20.0),
                        'features': st.session_state.get('features_text_area', '')
                    }
                    if save_project(db, st.session_state.user_email, project_data):
                        show_success_message(f"Project '{project_name}' saved successfully!")
                        # Refresh project list from the database
                        st.session_state.user_projects = load_projects(db, st.session_state.user_email)
                        time.sleep(1)
                        st.rerun()
                    else:
                        show_error_message("Failed to save project.")
                else:
                    show_error_message("Database connection not available.")
        
        with col_load:
            if st.session_state.get('user_projects'):
                project_names = [p.get('name', 'Unnamed Project') for p in st.session_state.user_projects]
                
                if project_names:
                    selected_project = st.selectbox(
                        "Select Project to Load", 
                        project_names,
                        key="project_selector_dropdown"
                    )
                    
                    # Use a button to trigger the load
                    if st.button("📂 Load Selected Project", use_container_width=True, key="load_project_btn"):
                        st.session_state.project_to_load = selected_project
                        st.rerun()
                else:
                    st.info("No saved projects found.")
            else:
                st.info("No saved projects found. Save your current project to see it here.")

        st.markdown("---")
        create_multi_room_interface()

    with tab2:
        show_smart_questionnaire_tab()
        
    with tab3:
        st.markdown('<h2 class="section-header section-header-boq">BOQ Generation Engine</h2>', unsafe_allow_html=True)
        # Check if questionnaire is completed
        if 'client_requirements' not in st.session_state:
            st.warning("⚠️ Please complete the Smart Questionnaire in the previous tab first.")
            st.info("The questionnaire gathers all necessary information to generate an optimized BOQ.")
        else:
            # Show summary of requirements
            with st.expander("📋 Your Requirements Summary", expanded=False):
                requirements = st.session_state.client_requirements
                st.write(f"**Primary Use:** {requirements.primary_use_case}")
                st.write(f"**Budget Level:** {requirements.budget_level}")
                st.write(f"**VC Platform:** {requirements.vc_platform}")
                # Show brand preferences
                brand_prefs = requirements.get_brand_preferences()
                if any(v != 'No Preference' for v in brand_prefs.values()):
                    st.write("**Brand Preferences:**")
                    for category, brand in brand_prefs.items():
                        if brand != 'No Preference':
                            st.write(f"  • {category.replace('_', ' ').title()}: {brand}")
            
            # Get room dimensions from sidebar (already captured)
            room_length = st.session_state.get('room_length_input', 28.0)
            room_width = st.session_state.get('room_width_input', 20.0)
            ceiling_height = st.session_state.get('ceiling_height_input', 10.0)
            room_type = st.session_state.get('room_type_select', 'Standard Conference Room')

            # Just show summary (no input fields)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Room Length", f"{room_length:.0f} ft")
            with col2:
                st.metric("Room Width", f"{room_width:.0f} ft")
            with col3:
                st.metric("Ceiling Height", f"{ceiling_height:.0f} ft")

            room_area = room_length * room_width
            st.metric("Room Area", f"{room_area:.0f} sq ft")
            st.info(f"📐 Room Type: {room_type}")
            
            # Pre-Generation Checklist
            st.markdown("### 📋 Pre-Generation Checklist")
            checklist_items = []

            # Check questionnaire completion
            if 'client_requirements' in st.session_state:
                req = st.session_state.client_requirements
                checklist_items.append(("✅", "Questionnaire completed"))
                
                # Check for brand preferences
                prefs = req.get_brand_preferences()
                pref_count = sum(1 for v in prefs.values() if v != 'No Preference')
                if pref_count > 0:
                    checklist_items.append(("✅", f"{pref_count} brand preferences set"))
                else:
                    checklist_items.append(("⚠️", "No brand preferences (using best available)"))
            else:
                checklist_items.append(("❌", "Questionnaire not completed"))

            # Check room dimensions
            if room_area > 0:
                checklist_items.append(("✅", f"Room: {room_length:.0f}' × {room_width:.0f}' = {room_area:.0f} sqft"))
            else:
                checklist_items.append(("❌", "Invalid room dimensions"))

            # Check project details
            missing_fields = validate_required_fields()
            if not missing_fields:
                checklist_items.append(("✅", "All project details filled"))
            else:
                checklist_items.append(("⚠️", f"{len(missing_fields)} project detail(s) missing"))

            # Display checklist
            for icon, text in checklist_items:
                st.markdown(f"{icon} {text}")

            st.markdown("---")
            
            generate_disabled = bool(missing_fields)
            if missing_fields:
                st.warning(f"⚠️ Please fill required fields in sidebar: {', '.join(missing_fields)}")
            
            # ======================= MODIFIED ERROR HANDLING BLOCK =======================
            if st.button("✨ Generate Optimized BOQ",
                          type="primary",
                          use_container_width=True,
                          disabled=generate_disabled):
                try:
                    progress_bar = st.progress(0, text="Initializing optimized generation...")
                    
                    # Import the optimized generator
                    from components.optimized_boq_generator import OptimizedBOQGenerator
                    progress_bar.progress(25, text="🎯 Building logical equipment blueprint...")
                    # Create generator with questionnaire requirements
                    generator = OptimizedBOQGenerator(
                        product_df=product_df,
                        client_requirements=st.session_state.client_requirements
                    )
                    st.session_state.boq_selector = generator.selector
                    progress_bar.progress(50, text="🔍 Selecting optimal products...")
                    
                    # Generate BOQ
                    boq_items, validation_results = generator.generate_boq_for_room(
                        room_type=room_type,
                        room_length=room_length,
                        room_width=room_width,
                        ceiling_height=ceiling_height
                    )
                    
                    progress_bar.progress(90, text="⚖️ Calculating Quality Score...")

                    # Calculate quality score
                    quality_score = generator.calculate_boq_quality_score(boq_items, validation_results)
                    st.session_state.boq_quality_score = quality_score

                    if boq_items:
                        st.session_state.boq_items = boq_items
                        st.session_state.validation_results = validation_results
                        st.session_state.boq_selector = generator.selector
                        
                        # Display quality score prominently
                        col_q1, col_q2, col_q3 = st.columns([1, 2, 1])
                        
                        with col_q1:
                            st.metric(
                                "BOQ Quality Score",
                                f"{quality_score['percentage']:.1f}%",
                                f"Grade: {quality_score['grade']}"
                            )
                        
                        with col_q2:
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, {quality_score['color']}22, {quality_score['color']}44); 
                                         border-left: 4px solid {quality_score['color']}; 
                                         padding: 1rem; 
                                         border-radius: 8px; 
                                         margin: 1rem 0;">
                                <h3 style="margin: 0; color: {quality_score['color']};">
                                    {quality_score['quality_level']}
                                </h3>
                                <p style="margin: 0.5rem 0 0 0; color: #666;">
                                    This BOQ meets professional standards for {room_type}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_q3:
                            with st.expander("📊 Score Breakdown"):
                                for category, score in quality_score['breakdown'].items():
                                    max_score = quality_score['max_breakdown'][category]
                                    pct = (score / max_score) * 100
                                    st.progress(pct / 100, text=f"{category.replace('_', ' ').title()}: {score:.0f}/{max_score}")
                        
                        update_boq_content_with_current_items()
                        
                        # Save to current room
                        if st.session_state.project_rooms and st.session_state.current_room_index < len(st.session_state.project_rooms):
                            st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = boq_items
                        
                        progress_bar.progress(100, text="✅ BOQ generation complete!")
                        time.sleep(0.5)
                        progress_bar.empty()
                        show_success_message("BOQ Generated Successfully with AVIXA Compliance")
                    else:
                        progress_bar.empty()
                        show_error_message("Failed to generate BOQ. Please check your inputs.")

                except KeyError as e:
                    progress_bar.empty()
                    st.error(f"❌ Data Error: Missing required field - {e}")
                    st.info("This usually means the product catalog is incomplete. Please check the catalog data file.")
                except ValueError as e:
                    progress_bar.empty()
                    st.error(f"❌ Validation Error: {e}")
                except Exception as e:
                    progress_bar.empty()
                    st.error(f"❌ Unexpected Error: {e}")
                    with st.expander("🔍 Technical Details"):
                        st.code(traceback.format_exc())
            # ======================= END MODIFIED BLOCK =======================

            st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        
        # Display BOQ results
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
                'PSNI Referral': "Yes" if st.session_state.get('is_psni_referral', False) else "No",
                'Client Type': "Local (India)" if st.session_state.get('client_is_local', False) else "International",
                'Existing Customer': "Yes" if st.session_state.get('is_existing_customer') else "No",
                'Currency': st.session_state.get('currency_select', 'USD')
            }
            display_boq_results(product_df, project_details)

            # ======================== NEW CODE: AI OPTIMIZATION ========================
            if st.session_state.get('boq_items') and model:
                with st.expander("💡 AI-Powered Cost Optimization Suggestions"):
                    if st.button("Generate Optimization Suggestions", key="optimize_btn"):
                        with st.spinner("AI analyzing BOQ for optimization opportunities..."):
                            from components.gemini_handler import generate_cost_optimization_suggestions
                            
                            suggestions = generate_cost_optimization_suggestions(
                                model=model,
                                boq_items=st.session_state.boq_items,
                                room_type=st.session_state.get('room_type_select', 'Conference Room'),
                                budget_tier=st.session_state.get('budget_tier_slider', 'Standard')
                            )
                            
                            if suggestions:
                                st.markdown("### 🎯 Optimization Opportunities")
                                for suggestion in suggestions:
                                    st.markdown(f"- {suggestion}")
                            else:
                                st.info("No optimization opportunities found. Your BOQ is already well-optimized!")
            # ============================ END OF NEW CODE ===========================

        else:
            st.info("👆 Complete the questionnaire and click 'Generate BOQ' to create your Bill of Quantities")

    with tab4:
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
