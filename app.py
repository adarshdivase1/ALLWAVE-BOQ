# app.py - ENHANCED VERSION with quality score calculation and display

import streamlit as st
import time
from datetime import datetime
import base64
from pathlib import Path
import logging
import traceback
import re  # <-- ADDED FOR CHANGE 6
from typing import Tuple, List, Dict # <-- MODIFIED: ADDED List, Dict

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
    # from components.smart_questionnaire import SmartQuestionnaire, show_smart_questionnaire_tab # <-- REMOVED
    from components.acim_form_questionnaire import show_acim_form_questionnaire # <-- ADDED IMPORT
    
    # ✅ ADD THESE TWO CRITICAL IMPORTS
    from components.multi_room_optimizer import MultiRoomOptimizer
    from components.excel_generator import generate_company_excel
    
except ImportError as e:
    st.error(f"Failed to import a necessary component: {e}")
    st.stop()

# ✅ FALLBACK HANDLERS for missing components
def fallback_optimizer():
    """Fallback if optimizer import fails"""
    class MockOptimizer:
        def optimize_multi_room_project(self, rooms):
            st.warning("⚠️ Optimizer component not available. Using rooms as-is.")
            return {
                'rooms': rooms,
                'optimization': 'none',
                'savings_pct': 0,
                'reason': 'Optimizer module not found'
            }
    return MockOptimizer()

def fallback_excel_generator(project_details, rooms_data, usd_to_inr_rate):
    """Fallback if Excel generator fails"""
    st.error("❌ Excel generator not available. Please check excel_generator.py exists.")
    return None

# Check if imports worked
# Note: Using globals() for a robust check of loaded modules
if 'MultiRoomOptimizer' not in globals():
    MultiRoomOptimizer = fallback_optimizer
    st.sidebar.warning("⚠️ Multi-room optimizer unavailable")

if 'generate_company_excel' not in globals():
    generate_company_excel = fallback_excel_generator
    st.sidebar.warning("⚠️ Excel export unavailable")


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

# ======================= START: ADDED HELPER FUNCTIONS (CHANGE 6) =======================

def _extract_dimensions_from_text(text: str, default_length: float, default_width: float, default_height: float) -> Tuple[float, float, float]:
    """
    Extract room dimensions from ACIM form text response.
    Looks for patterns like: "24ft x 18ft" or "7m x 6m x 3m" or "24' x 18' x 10'"
    """
    import re
    
    if not text:
        return default_length, default_width, default_height
    
    # Try to find dimensions in various formats
    patterns = [
        r'(\d+\.?\d*)\s*(?:ft|feet|\')\s*[xX×]\s*(\d+\.?\d*)\s*(?:ft|feet|\')\s*[xX×]?\s*(\d+\.?\d*)\s*(?:ft|feet|\')?',  # 24ft x 18ft x 10ft
        r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*[xX×]?\s*(\d+\.?\d*)',  # 24 x 18 x 10
        r'(\d+\.?\d*)m\s*[xX×]\s*(\d+\.?\d*)m\s*[xX×]?\s*(\d+\.?\d*)m?',  # 7m x 6m x 3m
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                length = float(match.group(1))
                width = float(match.group(2))
                height = float(match.group(3)) if match.group(3) else default_height
                
                # Convert meters to feet if needed
                if 'm' in text.lower() and 'ft' not in text.lower():
                    length *= 3.281
                    width *= 3.281
                    height *= 3.281
                
                return length, width, height
            except (ValueError, IndexError):
                continue
    
    # If no match, try to find just length and width
    simple_pattern = r'(\d+\.?\d*)\s*(?:ft|feet|\'|m)?\s*[xX×]\s*(\d+\.?\d*)\s*(?:ft|feet|\'|m)?'
    match = re.search(simple_pattern, text, re.IGNORECASE)
    if match:
        try:
            length = float(match.group(1))
            width = float(match.group(2))
            if 'm' in text.lower() and 'ft' not in text.lower():
                length *= 3.281
                width *= 3.281
            return length, width, default_height
        except (ValueError, IndexError):
            pass
    
    # Fallback to defaults
    return default_length, default_width, default_height


def _map_acim_to_standard_room(acim_room_type: str) -> str:
    """Map ACIM room types to standard room profiles"""
    mapping = {
        'Conference/Meeting Room/Boardroom': 'Standard Conference Room (6-8 People)',
        'Experience Center': 'Multipurpose Event Room (40+ People)',
        'Reception/Digital Signage': 'Small Huddle Room (2-3 People)',
        'Training Room': 'Training Room (15-25 People)',
        'Network Operations Center/Command Center': 'Large Conference Room (8-12 People)',
        'Town Hall': 'Multipurpose Event Room (40+ People)',
        'Auditorium': 'Multipurpose Event Room (40+ People)'
    }
    
    # Try exact match first
    if acim_room_type in mapping:
        return mapping[acim_room_type]
    
    # Try partial match
    for key, value in mapping.items():
        if key.lower() in acim_room_type.lower() or acim_room_type.lower() in key.lower():
            return value
    
    # Default fallback
    return 'Standard Conference Room (6-8 People)'

# ======================= END: ADDED HELPER FUNCTIONS (CHANGE 6) =======================


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


# ======================= START: NEW FUNCTION ADDED =======================
def parse_acim_to_client_requirements(acim_responses: Dict) -> 'ClientRequirements':
    """
    Parse ACIM form responses into a ClientRequirements object.
    Extracts all technical details from the form answers.
    """
    from components.smart_questionnaire import ClientRequirements
    import json # Added import
    
    # Get the first room's responses (you filled out Conference/Meeting Room)
    room_requirements = acim_responses.get('room_requirements', [])
    if not room_requirements:
        raise ValueError("No room requirements found in ACIM form")
    
    # Extract responses from the first room
    responses = room_requirements[0]['responses']
    
    # Helper function to check if text contains keywords
    def contains_any(text: str, keywords: List[str]) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)
    
    # Parse each response
    seating_layout = responses.get('seating_layout', '')
    solution_type = responses.get('solution_type', '')
    uc_platform = responses.get('uc_platform', '')
    native_solution = responses.get('native_solution', '')
    connectivity = responses.get('connectivity', '')
    digital_whiteboard = responses.get('digital_whiteboard', '')
    automation = responses.get('automation', '')
    room_scheduler = responses.get('room_scheduler', '')
    acoustic_solutions = responses.get('acoustic_solutions', '')
    budget = responses.get('budget', '')
    
    # Extract capacity from seating_layout
    capacity_match = re.search(r'(\d+)\s*people', seating_layout, re.IGNORECASE)
    capacity = int(capacity_match.group(1)) if capacity_match else 12
    
    # Determine budget tier from budget response
    budget_lower = budget.lower()
    if any(term in budget_lower for term in ['25000', '25,000', '35000', '35,000']):
        budget_tier = 'Premium'
    elif any(term in budget_lower for term in ['15000', '20000']):
        budget_tier = 'Standard'
    else:
        budget_tier = 'Standard'
    
    # Determine UC platform
    if contains_any(uc_platform, ['teams', 'microsoft']):
        vc_platform = 'Microsoft Teams'
    elif contains_any(uc_platform, ['zoom']):
        vc_platform = 'Zoom Rooms'
    elif contains_any(uc_platform, ['webex', 'cisco']):
        vc_platform = 'Cisco Webex'
    else:
        vc_platform = 'Microsoft Teams'
    
    # Determine display preferences
    dual_display = contains_any(solution_type, ['dual', 'two displays', '2 displays'])
    display_size = 75 if capacity >= 12 else 65
    
    # Determine if interactive display needed
    interactive_display = contains_any(digital_whiteboard, ['yes', 'logitech scribe', 'kaptivo'])
    
    # Video conferencing preferences
    native_vc = contains_any(native_solution, ['native', 'one-touch', 'touch panel'])
    vc_brand = 'No Preference'  # Will be determined by UC platform
    
    # Camera preferences
    auto_tracking = contains_any(native_solution, ['tracking', 'auto-track'])
    camera_type = 'PTZ Camera' if capacity > 8 else 'Video Bar'
    
    # Audio preferences
    voice_reinforcement = contains_any(acoustic_solutions, ['yes', 'acoustic', 'echo', 'reverberation'])
    
    # Connectivity
    wireless_presentation = contains_any(connectivity, ['wireless', 'clickshare', 'solstice', 'miracast', 'airplay'])
    
    # Control and automation
    lighting_control = contains_any(automation, ['yes', 'lighting', 'dimmable'])
    
    # Room scheduling
    room_scheduling = contains_any(room_scheduler, ['yes', '10-inch', 'touch panel', 'outlook', '365'])
    
    # Recording/streaming
    recording_needed = contains_any(solution_type, ['record', 'recording'])
    streaming_needed = contains_any(solution_type, ['stream', 'streaming'])
    
    # Create ClientRequirements object with all parsed data
    return ClientRequirements(
        project_type='New Installation',
        room_count=len(room_requirements),
        primary_use_case='Video Conferencing' if native_vc else 'Presentations & Training',
        budget_level=budget_tier,
        
        # Display preferences
        display_brand_preference='No Preference',
        display_size_preference=display_size,
        dual_display_needed=dual_display,
        interactive_display_needed=interactive_display,
        
        # Video conferencing
        vc_platform=vc_platform,
        vc_brand_preference=vc_brand,
        camera_type_preference=camera_type,
        auto_tracking_needed=auto_tracking,
        
        # Audio
        audio_brand_preference='No Preference',
        microphone_type='Ceiling Microphone' if capacity > 8 else 'Table/Boundary Microphones',
        ceiling_vs_table_audio='Ceiling Audio' if capacity > 8 else 'Integrated in Video Bar',
        voice_reinforcement_needed=voice_reinforcement,
        
        # Control
        control_brand_preference='Crestron',  # Default for MTR
        wireless_presentation_needed=wireless_presentation,
        room_scheduling_needed=room_scheduling,
        lighting_control_integration=lighting_control,
        
        # Infrastructure
        existing_network_capable=True,
        cable_management_type='In-Wall/Conduit',
        ada_compliance_required=False,
        power_infrastructure_adequate=True,
        
        # Special features
        recording_capability_needed=recording_needed,
        streaming_capability_needed=streaming_needed,
        
        # Additional requirements (raw text)
        additional_requirements=f"ACIM Form Responses:\n{json.dumps(responses, indent=2)}"
    )
# ======================= END: NEW FUNCTION ADDED =======================


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
    # --- CHANGED TAB TITLES ---
    tab_titles = ["📋 Project Scope", "📝 ACIM Form", "🛠️ Generate BOQ", "✨ 3D Visualization"]
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

    # ======================= MODIFIED TAB 2 =======================
    with tab2:
        from components.acim_form_questionnaire import show_acim_form_questionnaire
        show_acim_form_questionnaire()
    # ==============================================================
        
    # ======================= START: REPLACED TAB 3 LOGIC (CHANGE 6) =======================
    with tab3:
        st.markdown('<h2 class="section-header section-header-boq">BOQ Generation Engine</h2>', unsafe_allow_html=True)
        
        # Check if ACIM form is completed
        if 'acim_form_responses' not in st.session_state or not st.session_state.acim_form_responses.get('selected_rooms'):
            st.warning("⚠️ Please complete the ACIM Form in the previous tab first.")
            
            # ✅ NEW: Show what's needed
            with st.expander("ℹ️ What information is needed?"):
                st.markdown("""
                        The ACIM Form collects:
                - **Client Details** (Name, Company, Location)
                - **Room Types** (Select all room types in your project)
                - **Room-Specific Requirements** (Dimensions, features, equipment preferences)
                
                **📋 Quick Start:**
                1. Go to the "ACIM Form" tab
                2. Fill in your details
                3. Select room type(s)
                4. Answer the questions for each room
                5. Return here to generate the BOQ
                """)
            
            st.stop() # Stop execution if form not complete
        
        # ✅ ENHANCED: Show ACIM form summary
        acim_data = st.session_state.acim_form_responses
        
        with st.expander("📊 ACIM Form Summary", expanded=False):
            # FIXED: client_details is a dataclass, not a dict
            client_details = acim_data.get('client_details')
            
            if client_details:
                # Access dataclass attributes directly
                client_name = getattr(client_details, 'name', 'N/A')
                company_name = getattr(client_details, 'company_name', 'N/A')
                st.write(f"**Client:** {client_name}")
                st.write(f"**Company:** {company_name}")
            else:
                st.write("**Client:** N/A")
                st.write("**Company:** N/A")
            
            st.write(f"**Selected Rooms:** {', '.join(acim_data.get('selected_rooms', []))}")
        
        # Main generation button
        if st.button("✨ Generate BOQ from ACIM Form", 
                     type="primary", 
                     use_container_width=True):
            
            try:
                progress_bar = st.progress(0, text="Processing ACIM form data...")
                
                from components.optimized_boq_generator import OptimizedBOQGenerator
                from components.smart_questionnaire import ClientRequirements
                
                # ======================= START: REPLACED BLOCK =======================
                # ✅ PARSE ACIM FORM INTO CLIENT REQUIREMENTS
                try:
                    requirements = parse_acim_to_client_requirements(acim_data)
                    st.success(f"✅ Parsed ACIM form: {requirements.vc_platform}, {requirements.primary_use_case}, Budget: {requirements.budget_level}")
                except Exception as e:
                    st.error(f"Failed to parse ACIM form: {e}")
                    # Fallback to basic requirements
                    requirements = ClientRequirements(
                        project_type='New Installation',
                        room_count=len(acim_data['selected_rooms']),
                        primary_use_case='Video Conferencing',
                        budget_level='Standard',
                        display_brand_preference='No Preference',
                        display_size_preference=65,
                        dual_display_needed=False,
                        interactive_display_needed=False,
                        vc_platform='Microsoft Teams',
                        vc_brand_preference='No Preference',
                        camera_type_preference='Video Bar',
                        auto_tracking_needed=False,
                        audio_brand_preference='No Preference',
                        microphone_type='Table/Boundary Microphones',
                        ceiling_vs_table_audio='Integrated in Video Bar',
                        voice_reinforcement_needed=False,
                        control_brand_preference='No Preference',
                        wireless_presentation_needed=False,
                        room_scheduling_needed=False,
                        lighting_control_integration=False,
                        existing_network_capable=True,
                        cable_management_type='Exposed',
                        ada_compliance_required=False,
                        power_infrastructure_adequate=True,
                        recording_capability_needed=False,
                        streaming_capability_needed=False,
                        additional_requirements=''
                    )
                # ======================= END: REPLACED BLOCK =======================
                
                progress_bar.progress(30, text="🎯 Generating BOQ for each room...")
                
                generator = OptimizedBOQGenerator(
                    product_df=product_df,
                    client_requirements=requirements
                )
                
                # ✅ FIXED: Process each room from ACIM form
                all_boq_items = []
                all_validations = {}
                
                for idx, room_req in enumerate(acim_data.get('room_requirements', [])):
                    room_type = room_req['room_type']
                    responses = room_req['responses']
                    
                    # Parse room dimensions from ACIM responses
                    # Look for the room dimensions question response
                    dimensions_response = responses.get('room_dimensions', '') or responses.get('seating_layout', '')
                    
                    # ✅ NEW: Smart dimension extraction
                    room_length, room_width, ceiling_height = _extract_dimensions_from_text(
                        dimensions_response,
                        default_length=28.0,
                        default_width=20.0,
                        default_height=10.0
                    )
                    
                    st.info(f"Processing: {room_type} ({room_length}' x {room_width}')")
                    
                    # Map ACIM room type to standard room type
                    standard_room_type = _map_acim_to_standard_room(room_type)
                    
                    # Generate BOQ for this room
                    boq_items, validation = generator.generate_boq_for_room(
                        room_type=standard_room_type,
                        room_length=room_length,
                        room_width=room_width,
                        ceiling_height=ceiling_height
                    )
                    
                    # Tag items with room name
                    for item in boq_items:
                        item['room_name'] = f"{room_type} ({idx+1})"
                    
                    all_boq_items.extend(boq_items)
                    all_validations[room_type] = validation
                    
                    progress_bar.progress(30 + (idx+1)/len(acim_data['room_requirements'])*60, 
                                         text=f"Processed room {idx+1}/{len(acim_data['room_requirements'])}")
                
                progress_bar.progress(90, text="⚖️ Calculating Quality Score...")
                
                if all_boq_items:
                    # Combine all validations
                    combined_validation = {
                        'warnings': [],
                        'issues': [],
                        'compliance_score': 0
                    }
                    
                    total_score = 0
                    for room, val in all_validations.items():
                        combined_validation['warnings'].extend(val.get('warnings', []))
                        combined_validation['issues'].extend(val.get('issues', []))
                        total_score += val.get('compliance_score', 0)
                    
                    if all_validations:
                        combined_validation['compliance_score'] = total_score / len(all_validations)
                    else:
                        combined_validation['compliance_score'] = 0

                    
                    # Calculate quality score
                    quality_score = generator.calculate_boq_quality_score(all_boq_items, combined_validation)
                    st.session_state.boq_quality_score = quality_score
                    
                    st.session_state.boq_items = all_boq_items
                    st.session_state.validation_results = combined_validation
                    st.session_state.boq_selector = generator.selector
                    
                    # ✅ NEW: Display quality score with breakdown
                    st.markdown("---")
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
                                     border-radius: 8px;">
                            <h3 style="margin: 0; color: {quality_score['color']};">
                                {quality_score['quality_level']}
                            </h3>
                            <p style="margin: 0.5rem 0 0 0; color: #666;">
                                Generated BOQ for {len(acim_data['selected_rooms'])} room type(s)
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_q3:
                        with st.expander("📊 Score Breakdown"):
                            for category, score in quality_score['breakdown'].items():
                                max_score = quality_score['max_breakdown'][category]
                                pct = (score / max_score) * 100 if max_score > 0 else 0
                                st.progress(pct / 100, text=f"{category.replace('_', ' ').title()}: {score:.0f}/{max_score}")
                    
                    update_boq_content_with_current_items()
                    
                    progress_bar.progress(100, text="✅ BOQ generation complete!")
                    time.sleep(0.5)
                    progress_bar.empty()
                    
                    show_success_message(f"BOQ Generated Successfully for {len(acim_data['selected_rooms'])} Room Type(s)")
                else:
                    progress_bar.empty()
                    show_error_message("Failed to generate BOQ from ACIM form.")
                    
            except Exception as e:
                progress_bar.empty()
                st.error(f"❌ Error: {e}")
                with st.expander("🔍 Technical Details"):
                    st.code(traceback.format_exc())
        
        # ======================= END: REPLACED TAB 3 LOGIC (CHANGE 6) =======================

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
            st.info("👆 Complete the ACIM form and click 'Generate BOQ' to create your Bill of Quantities")

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
