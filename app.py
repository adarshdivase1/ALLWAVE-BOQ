# app.py - ENHANCED VERSION with quality score calculation and display

import streamlit as st
import time
from datetime import datetime
import base64
from pathlib import Path
import logging
import traceback
import re
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
    from components.acim_form_questionnaire import show_acim_form_questionnaire # <-- ADDED IMPORT

    # ✅ ADD THESE TWO CRITICAL IMPORTS
    from components.multi_room_optimizer import MultiRoomOptimizer
    from components.excel_generator import generate_company_excel

    # Import necessary functions for the fix
    from components.av_designer import calculate_avixa_recommendations
    from components.smart_questionnaire import ClientRequirements # Ensure this is available

except ImportError as e:
    st.error(f"Failed to import a necessary component: {e}")
    logger.error(f"ImportError: {e}", exc_info=True)
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
        logger.warning(f"Image not found: {img_path}")
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


def _extract_dimensions_from_text(text: str, default_length: float, default_width: float, default_height: float) -> Tuple[float, float, float]:
    """
    Extract room dimensions from ACIM form text response.
    Looks for patterns like: "24ft x 18ft" or "7m x 6m x 3m" or "24' x 18' x 10'"
    """
    import re

    if not text:
        return default_length, default_width, default_height

    # Try to find dimensions in various formats (LxWxH or variations)
    patterns = [
        # Feet patterns (e.g., 80ft x 60ft x 25ft, 80'x60'x25', 80 x 60 x 25 ft)
        r'(\d+\.?\d*)\s*(?:ft|feet|\')?\s*[xX×]\s*(\d+\.?\d*)\s*(?:ft|feet|\')?\s*[xX×]?\s*(\d+\.?\d*)\s*(?:ft|feet|\')',
        # Meters pattern (e.g., 24m x 18m x 7m)
        r'(\d+\.?\d*)\s*m\s*[xX×]\s*(\d+\.?\d*)\s*m\s*[xX×]?\s*(\d+\.?\d*)\s*m',
        # Unitless pattern (assume feet if no 'm' present)
        r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)',
         # Keyword pattern (length: 80 ft, width: 60 ft, height: 25 ft)
        r'length[:\s]*(\d+\.?\d*)\s*(ft|m)?.*(?:width|breadth)[:\s]*(\d+\.?\d*)\s*(ft|m)?.*height[:\s]*(\d+\.?\d*)\s*(ft|m)?'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                # Handle keyword pattern separately due to unit groups
                if 'length[:\s]*' in pattern:
                     g1, u1, g2, u2, g3, u3 = match.groups()
                     units = (u1 or u2 or u3 or '').lower()
                     is_meters = 'm' in units
                else:
                    g1, g2, g3 = match.groups()[:3] # Ensure only 3 groups accessed
                    is_meters = 'm' in text.lower() and 'ft' not in text.lower()

                # Parse values, checking for None or empty strings
                parsed_length = float(g1) if g1 and g1.strip() else None
                parsed_width = float(g2) if g2 and g2.strip() else None
                parsed_height = float(g3) if g3 and g3.strip() else None

                length = parsed_length if parsed_length is not None else default_length
                width = parsed_width if parsed_width is not None else default_width
                height = parsed_height if parsed_height is not None else default_height

                # Convert meters to feet if needed
                if is_meters:
                    if parsed_length is not None: length *= 3.281
                    if parsed_width is not None: width *= 3.281
                    if parsed_height is not None: height *= 3.281

                # Basic sanity check
                if length > 3 and width > 3 and height > 5:
                    logger.info(f"Extracted dimensions (LxWxH): {length:.1f}ft x {width:.1f}ft x {height:.1f}ft from text: '{text[:50]}...'")
                    return length, width, height
                else:
                    logger.warning(f"Discarded unreasonable dimensions: L:{length} W:{width} H:{height}")

            except (ValueError, IndexError, AttributeError) as e:
                logger.warning(f"Dimension parsing error for pattern '{pattern}' on text '{text[:50]}...': {e}")
                continue # Try next pattern

    # Fallback to LxW patterns if LxWxH fails
    simple_patterns = [
        r'(\d+\.?\d*)\s*(?:ft|feet|\')?\s*[xX×]\s*(\d+\.?\d*)\s*(?:ft|feet|\')', # 80ft x 60ft
        r'(\d+\.?\d*)\s*m\s*[xX×]\s*(\d+\.?\d*)\s*m', # 24m x 18m
        r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)', # 80 x 60
        r'length[:\s]*(\d+\.?\d*)\s*(ft|m)?.*(?:width|breadth)[:\s]*(\d+\.?\d*)\s*(ft|m)?' # length: 80, width: 60
    ]
    for pattern in simple_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                # Handle keyword pattern
                if 'length[:\s]*' in pattern:
                    g1, u1, g2, u2 = match.groups()
                    units = (u1 or u2 or '').lower()
                    is_meters = 'm' in units
                else:
                    g1, g2 = match.groups()[:2]
                    is_meters = 'm' in text.lower() and 'ft' not in text.lower()

                parsed_length = float(g1) if g1 and g1.strip() else None
                parsed_width = float(g2) if g2 and g2.strip() else None

                length = parsed_length if parsed_length is not None else default_length
                width = parsed_width if parsed_width is not None else default_width

                if is_meters:
                    if parsed_length is not None: length *= 3.281
                    if parsed_width is not None: width *= 3.281

                if length > 3 and width > 3:
                    logger.info(f"Extracted dimensions (LxW): {length:.1f}ft x {width:.1f}ft (using default height) from text: '{text[:50]}...'")
                    return length, width, default_height
                else:
                     logger.warning(f"Discarded unreasonable dimensions: L:{length} W:{width}")

            except (ValueError, IndexError, AttributeError) as e:
                logger.warning(f"Dimension parsing error (LxW) for pattern '{pattern}' on text '{text[:50]}...': {e}")
                continue

    # Final fallback
    logger.warning(f"Could not extract dimensions from text: '{text[:50]}...'. Using defaults.")
    return default_length, default_width, default_height


def _map_acim_to_standard_room(acim_room_type: str) -> str:
    """Map ACIM room types to standard room profiles"""
    mapping = {
        'Conference/Meeting Room/Boardroom': 'Standard Conference Room (6-8 People)',
        'Experience Center': 'Multipurpose Event Room (40+ People)', # Map to large multi purpose as base
        'Reception/Digital Signage': 'Small Huddle Room (2-3 People)', # Use small huddle as base
        'Training Room': 'Training Room (15-25 People)',
        'Network Operations Center/Command Center': 'Large Conference Room (8-12 People)', # Map to large conf as base
        'Town Hall': 'Multipurpose Event Room (40+ People)', # Map to large multi purpose as base
        'Auditorium': 'Multipurpose Event Room (40+ People)' # Map to large multi purpose as base
    }

    # Try exact match first
    if acim_room_type in mapping:
        return mapping[acim_room_type]

    # Try partial match (case-insensitive)
    acim_lower = acim_room_type.lower()
    for key, value in mapping.items():
        key_lower = key.lower()
        # Check if ACIM type contains a keyword OR if a keyword contains the ACIM type
        if any(term in acim_lower for term in key_lower.split('/')) or \
           any(acim_lower in term for term in key_lower.split('/')):
            logger.info(f"Mapped ACIM type '{acim_room_type}' to Standard Profile '{value}' based on partial match.")
            return value

    # Default fallback
    logger.warning(f"Could not map ACIM type '{acim_room_type}'. Falling back to Standard Conference Room.")
    return 'Standard Conference Room (6-8 People)'


def parse_acim_to_client_requirements(acim_responses: Dict) -> ClientRequirements:
    """
    Parse ACIM form responses into a ClientRequirements object.
    Extracts CLIENT PREFERENCES ONLY - no engineering decisions.
    """
    import json # Ensure json is imported

    room_requirements = acim_responses.get('room_requirements', [])
    if not room_requirements:
        # Return default requirements if no rooms selected yet
        logger.warning("No room requirements found in ACIM form, using default ClientRequirements.")
        return ClientRequirements()

    # Use requirements from the *first* selected room for general preferences
    responses = room_requirements[0]['responses']
    room_type = room_requirements[0]['room_type'] # Get the room type for context

    # Helper function
    def contains_any(text: str, keywords: List[str]) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    # Parse responses - PREFERENCES ONLY
    # Use .get() with default values for robustness
    seating_layout = responses.get('seating_layout', responses.get('seating_info', ''))
    solution_type = responses.get('solution_type', responses.get('primary_applications',''))
    uc_platform = responses.get('uc_platform', '')
    connectivity = responses.get('connectivity', '')
    digital_whiteboard = responses.get('digital_whiteboard', '')
    budget = responses.get('budget', '')
    native_solution_pref = responses.get('native_solution', responses.get('vc_solution', ''))
    automation_pref = responses.get('automation', '')
    scheduler_pref = responses.get('room_scheduler', '')
    acoustics_pref = responses.get('acoustic_solutions', responses.get('audio_performance', ''))
    tracking_pref = responses.get('camera_features', '')

    # Extract capacity (FACT, not decision) - More robust parsing
    capacity = 12 # Default
    capacity_text = seating_layout
    capacity_match_people = re.search(r'(\d+)\s*(?:person|people|participant)', capacity_text, re.IGNORECASE)
    capacity_match_seats = re.search(r'(\d+)\s*(?:seat|chair)', capacity_text, re.IGNORECASE)
    if capacity_match_people:
        capacity = int(capacity_match_people.group(1))
    elif capacity_match_seats:
        capacity = int(capacity_match_seats.group(1))
    logger.info(f"Parsed capacity: {capacity}")

    # Determine budget tier (PREFERENCE)
    # Use the more robust parsing from acim_parser_enhanced
    from components.acim_parser_enhanced import _parse_budget # Assuming it's accessible
    budget_midpoint = _parse_budget(budget, capacity) # Pass capacity for estimation

    # Basic tiering based on midpoint estimate per seat
    cost_per_seat = budget_midpoint / capacity if capacity > 0 else 0
    if cost_per_seat > 1500: budget_tier = 'Premium'
    elif cost_per_seat < 500: budget_tier = 'Economy'
    else: budget_tier = 'Standard'
    # Override if keywords are present
    budget_lower = budget.lower()
    if any(term in budget_lower for term in ['premium', 'high end', 'top']): budget_tier = 'Premium'
    if any(term in budget_lower for term in ['economy', 'budget', 'low cost']): budget_tier = 'Economy'
    logger.info(f"Determined budget tier: {budget_tier} (Midpoint: ${budget_midpoint:.0f}, Cost/Seat: ${cost_per_seat:.0f})")

    # UC Platform (PREFERENCE)
    vc_platform = 'Microsoft Teams' # Default
    if contains_any(uc_platform, ['zoom']): vc_platform = 'Zoom Rooms'
    elif contains_any(uc_platform, ['webex', 'cisco']): vc_platform = 'Cisco Webex'
    elif contains_any(uc_platform, ['google', 'meet']): vc_platform = 'Google Meet'
    logger.info(f"Determined VC Platform: {vc_platform}")

    # CLIENT PREFERENCES (not engineering specs)
    # Check across multiple possible question IDs
    dual_display = contains_any(solution_type, ['dual', 'two displays']) or \
                   contains_any(responses.get('display_preference', ''), ['dual', 'two displays'])
    interactive_display = contains_any(digital_whiteboard, ['yes', 'logitech', 'kaptivo', 'interactive'])
    native_vc = contains_any(native_solution_pref, ['native', 'one-touch'])
    auto_tracking = contains_any(tracking_pref, ['tracking', 'auto-focus'])
    wireless_presentation = contains_any(connectivity, ['wireless', 'clickshare', 'byod'])
    lighting_control = contains_any(automation_pref, ['yes', 'lighting'])
    room_scheduling = contains_any(scheduler_pref, ['yes', 'touch panel', 'scheduler'])
    voice_reinforcement = contains_any(acoustics_pref, ['yes', 'acoustic', 'high-performance', 'column']) or \
                           ('Training' in room_type or 'Auditorium' in room_type or 'Town Hall' in room_type) # Assume needed for large rooms
    recording_needed = contains_any(solution_type, ['record', 'capture']) or \
                       contains_any(responses.get('live_streaming', ''), ['record'])
    streaming_needed = contains_any(responses.get('live_streaming', ''), ['yes', 'stream', 'broadcast'])

    # Determine primary use case more dynamically
    use_case = 'General Collaboration'
    if native_vc: use_case = 'Video Conferencing'
    elif 'presentation' in solution_type.lower(): use_case = 'Presentations'
    if 'training' in solution_type.lower() or 'Training' in room_type: use_case = 'Training & Education'
    if 'auditorium' in room_type.lower() or 'town hall' in room_type.lower(): use_case = 'Event & Broadcast'
    logger.info(f"Determined Primary Use Case: {use_case}")

    return ClientRequirements(
        project_type='New Installation', # Assume new for now
        room_count=len(room_requirements),
        primary_use_case=use_case,
        budget_level=budget_tier,

        # Display PREFERENCES
        display_brand_preference='No Preference', # Can be enhanced later
        display_size_preference=0, # Let AVIXA calculate size
        dual_display_needed=dual_display,
        interactive_display_needed=interactive_display,

        # Video conferencing PREFERENCES
        vc_platform=vc_platform,
        vc_brand_preference='No Preference', # Can be enhanced later
        camera_type_preference='Auto', # Let generator decide based on room/use
        auto_tracking_needed=auto_tracking,

        # Audio PREFERENCES
        audio_brand_preference='No Preference', # Can be enhanced later
        microphone_type='Auto', # Let AVIXA decide based on room
        ceiling_vs_table_audio='Auto', # Default, can be refined
        voice_reinforcement_needed=voice_reinforcement,

        # Control PREFERENCES
        control_brand_preference='Crestron', # Default preference
        wireless_presentation_needed=wireless_presentation,
        room_scheduling_needed=room_scheduling,
        lighting_control_integration=lighting_control,

        # Infrastructure - Assume defaults, can be asked in form
        existing_network_capable=True,
        cable_management_type='In-Wall/Conduit',
        ada_compliance_required=False,
        power_infrastructure_adequate=True,

        # Special features
        recording_capability_needed=recording_needed,
        streaming_capability_needed=streaming_needed,

        # Raw data for reference
        additional_requirements=f"Parsed from ACIM Form.\nRoom Type: {room_type}\nCapacity: {capacity}\n" + json.dumps(responses, indent=2, default=str) # Use default=str for non-serializable
    )


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
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = {}
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state:
        st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}
    else:
        st.session_state.gst_rates['Electronics'] = int(st.session_state.gst_rates.get('Electronics', 18))
        st.session_state.gst_rates['Services'] = int(st.session_state.gst_rates.get('Services', 18))

    if 'currency_select' not in st.session_state:
        st.session_state.currency_select = "INR" if st.session_state.get('client_is_local') else "USD"

    if 'room_length_input' not in st.session_state: st.session_state.room_length_input = 28.0
    if 'room_width_input' not in st.session_state: st.session_state.room_width_input = 20.0

    # Load product data
    with st.spinner("Initializing system modules..."):
        product_df, guidelines, data_issues = load_and_validate_data()
        st.session_state.product_df = product_df

    # --- DEBUG INFO ---
    if product_df is not None:
        st.sidebar.write("--- DEBUG INFO ---")
        st.sidebar.write(f"Product DB Rows: {len(product_df)}")
        st.sidebar.write(f"Product DB Columns: {len(product_df.columns)}")
        if 'category' in product_df.columns:
            st.sidebar.success("✅ 'category' column exists")
            categories = product_df['category'].unique()
            st.sidebar.write(f"Categories Found: {len(categories)}")
            # st.sidebar.write(f"Sample: {', '.join(categories[:3])}") # Removed for brevity
        else:
            st.sidebar.error("❌ 'category' column MISSING in product_df!")
        st.sidebar.write("--- End Debug ---")
    else:
         st.sidebar.error("❌ Product DataFrame is None!")
    # --- END DEBUG INFO ---

    if data_issues:
        with st.expander("⚠️ Data Quality Issues Detected", expanded=False):
            for issue in data_issues: st.warning(issue)

    if product_df is None:
        show_error_message("Fatal Error: Product catalog could not be loaded. Check data source.")
        logger.critical("product_df is None. Halting execution.")
        st.stop()
    if product_df.empty:
        show_error_message("Fatal Error: Product catalog is empty. Check data source.")
        logger.critical("product_df is empty. Halting execution.")
        st.stop()


    model = setup_gemini()

    # Create header
    partner_logos_paths = {
        "Crestron": Path("assets/crestron_logo.png"),
        "AVIXA": Path("assets/avixa_logo.png"),
        "PSNI Global Alliance": Path("assets/iso_logo.png") # Changed from iso_logo
    }
    create_header(main_logo_path, partner_logos_paths)

    st.markdown(
        '<div class="glass-container"><h1 class="animated-header">AllWave AV & GS Portal</h1>'
        '<p style="text-align: center; color: var(--text-secondary);">Professional AV System Design & BOQ Generation Platform</p></div>',
        unsafe_allow_html=True
    )

    # Sidebar function
    def update_dimensions_from_room_type():
        room_type = st.session_state.get('room_type_select') # Use .get() for safety
        if room_type and room_type in ROOM_SPECS and 'typical_dims_ft' in ROOM_SPECS[room_type]:
            dims = ROOM_SPECS[room_type]['typical_dims_ft']
            if dims and len(dims) >= 2: # Ensure dims is not None and has at least two elements
                length, width = dims
                st.session_state.room_length_input = float(length)
                st.session_state.room_width_input = float(width)
                logger.info(f"Updated dimensions for {room_type}: L={length}, W={width}")

    # ============= SIDEBAR =============
    with st.sidebar:
        st.markdown(f'''
        <div class="user-info">
            <h3>👤 Welcome</h3>
            <p>{st.session_state.get("user_email", "Unknown User")}</p>
        </div>
        ''', unsafe_allow_html=True)

        if st.session_state.get('is_psni_referral', False): st.success("✅ PSNI Global Alliance Referral")
        else: st.info("ℹ️ Direct Client Project")

        if st.session_state.get('client_is_local', True): st.info("🇮🇳 Local Client (India) - INR Currency") # Default to local if not set
        else: st.info("🌍 International Client - USD Currency")

        if st.button("🚪 Logout", use_container_width=True):
            show_animated_loader("De-authorizing...", 1)
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()

        st.markdown("<hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🚀 Mission Parameters</h3>', unsafe_allow_html=True)

        st.text_input("Project Name", key="project_name_input", placeholder="Enter project name")
        st.text_input("Client Name", key="client_name_input", placeholder="Enter client name")

        if st.session_state.get('is_existing_customer', False): st.success("✅ Existing Customer (Discount Applied)")
        else: st.info("ℹ️ New Customer")

        st.text_input("Location", key="location_input", placeholder="e.g., Navi Mumbai, India")
        st.text_input("Design Engineer", key="design_engineer_input", placeholder="Enter engineer's name")
        st.text_input("Account Manager", key="account_manager_input", placeholder="Enter manager's name")
        st.text_input("Key Client Personnel", key="client_personnel_input", placeholder="Enter client contact name")
        st.text_area("Key Comments for this version", key="comments_input", placeholder="Add any relevant comments...")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<hr style='border-color: var(--border-color);'>", unsafe_allow_html=True)
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🔧 Multi-Room Options</h3>', unsafe_allow_html=True)

        if len(st.session_state.get('project_rooms', [])) >= 3:
            enable_optimization = st.checkbox(
                "Enable Multi-Room Optimization", value=True, key="multi_room_optimization_enabled",
                help="Consolidates network switches, racks, and shared infrastructure across 3+ rooms for cost savings"
            )
            if enable_optimization: st.success(f"✅ Optimizing across {len(st.session_state.project_rooms)} rooms")
            else: st.info("ℹ️ Each room will have independent equipment")
        else:
            st.info(f"ℹ️ Multi-room optimization requires 3+ rooms\nCurrent: {len(st.session_state.get('project_rooms', []))} room(s)")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>⚙️ Financial Config</h3>', unsafe_allow_html=True)

        currency_display = "INR (₹)" if st.session_state.get('client_is_local', True) else "USD ($)"
        st.text_input("Currency (Auto-set)", value=currency_display, disabled=True,
                      help="Currency is automatically set based on client location")

        st.session_state.gst_rates['Electronics'] = st.number_input(
            "Hardware GST (%)", value=int(st.session_state.gst_rates.get('Electronics', 18)), min_value=0, max_value=50
        )
        st.session_state.gst_rates['Services'] = st.number_input(
            "Services GST (%)", value=int(st.session_state.gst_rates.get('Services', 18)), min_value=0, max_value=50
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown('<h3>🌍 Environment Design</h3>', unsafe_allow_html=True)

        # Room Type Selection Logic (improved default handling)
        use_case_to_room_type = {
            'Video Conferencing': 'Standard Conference Room (6-8 People)',
            'Presentations & Training': 'Training Room (15-25 People)',
            'Hybrid Meetings': 'Large Conference Room (8-12 People)',
            'Executive Boardroom': 'Executive Boardroom (10-16 People)',
            'Event & Broadcast': 'Multipurpose Event Room (40+ People)',
            'Multipurpose': 'Large Training/Presentation Room (25-40 People)',
             'General Collaboration': 'Medium Huddle Room (4-6 People)', # Added default
        }

        default_room_type = 'Standard Conference Room (6-8 People)'
        if 'client_requirements' in st.session_state and hasattr(st.session_state.client_requirements, 'primary_use_case'):
            req = st.session_state.client_requirements
            default_room_type = use_case_to_room_type.get(req.primary_use_case, default_room_type)
        elif 'acim_form_responses' in st.session_state:
             # Try deriving from first selected ACIM room if client_requirements not populated yet
             selected_acim_rooms = st.session_state.acim_form_responses.get('selected_rooms', [])
             if selected_acim_rooms:
                 default_room_type = _map_acim_to_standard_room(selected_acim_rooms[0])


        current_room_type = st.session_state.get('room_type_select', default_room_type)
        room_types_list = list(ROOM_SPECS.keys())

        try: default_index = room_types_list.index(current_room_type)
        except ValueError: default_index = 0

        room_type_key = st.selectbox(
            "Primary Space Type", room_types_list, index=default_index, key="room_type_select",
            on_change=update_dimensions_from_room_type
        )

        # Call once on initial load if needed
        if 'initial_load_done' not in st.session_state:
            update_dimensions_from_room_type()
            st.session_state.initial_load_done = True


        st.select_slider(
            "Budget Tier", options=["Economy", "Standard", "Premium", "Enterprise"],
            value=st.session_state.get('budget_tier_slider', 'Standard'), key="budget_tier_slider"
        )

        if room_type_key and room_type_key in ROOM_SPECS:
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
    tab_titles = ["📋 Project Scope", "📝 ACIM Form", "🛠️ Generate BOQ", "✨ 3D Visualization"]
    tab1, tab2, tab3, tab4 = st.tabs(tab_titles)

    with tab1:
        st.markdown('<h2 class="section-header section-header-project">Project Management</h2>', unsafe_allow_html=True)

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
                        'features': st.session_state.get('features_text_area', ''), # Assuming this exists elsewhere
                        # Save ACIM data if present
                        'acim_form_responses': st.session_state.get('acim_form_responses', None)
                    }
                    if save_project(db, st.session_state.user_email, project_data):
                        show_success_message(f"Project '{project_name}' saved successfully!")
                        st.session_state.user_projects = load_projects(db, st.session_state.user_email)
                        time.sleep(1); st.rerun()
                    else: show_error_message("Failed to save project.")
                else: show_error_message("Database connection not available.")

        with col_load:
            if st.session_state.get('user_projects'):
                project_names = [p.get('name', 'Unnamed Project') for p in st.session_state.user_projects]
                if project_names:
                    selected_project = st.selectbox("Select Project to Load", project_names, key="project_selector_dropdown")
                    if st.button("📂 Load Selected Project", use_container_width=True, key="load_project_btn"):
                        st.session_state.project_to_load = selected_project
                        st.rerun()
                else: st.info("No saved projects found.")
            else: st.info("No saved projects found. Save your current project to see it here.")

        st.markdown("---")
        create_multi_room_interface()

    with tab2:
        show_acim_form_questionnaire() # Call the ACIM form function

    with tab3:
        st.markdown('<h2 class="section-header section-header-boq">BOQ Generation Engine</h2>', unsafe_allow_html=True)

        if 'acim_form_responses' not in st.session_state or not st.session_state.acim_form_responses.get('selected_rooms'):
            st.warning("⚠️ Please complete the ACIM Form in the previous tab first.")
            with st.expander("ℹ️ What information is needed?"):
                 st.markdown("""
                        The ACIM Form collects essential details about your client and the specific requirements for each room in the project.
                        **📋 Quick Start:** Go to the "ACIM Form" tab, fill in the details, select room type(s), answer the questions for each room, then return here.
                        """)
            st.stop()

        acim_data = st.session_state.acim_form_responses
        with st.expander("📊 ACIM Form Summary", expanded=False):
            client_details = acim_data.get('client_details')
            if client_details and hasattr(client_details, 'name'): # Check if dataclass exists and has attribute
                st.write(f"**Client:** {getattr(client_details, 'name', 'N/A')}")
                st.write(f"**Company:** {getattr(client_details, 'company_name', 'N/A')}")
            else: st.write("**Client/Company:** N/A")
            st.write(f"**Selected Rooms:** {', '.join(acim_data.get('selected_rooms', ['None']))}")


        # --- Main generation button with corrected logic ---
        if st.button("✨ Generate BOQ from ACIM Form", type="primary", use_container_width=True):
            logger.info("BOQ Generation triggered from ACIM form.")
            try:
                progress_bar = st.progress(0.0, text="Initializing generation...")

                # Ensure product data is loaded correctly
                if 'product_df' not in st.session_state or st.session_state.product_df is None or st.session_state.product_df.empty:
                     show_error_message("CRITICAL ERROR: Product catalog not loaded or empty. Cannot generate BOQ.")
                     logger.critical("Aborting BOQ generation: product_df is missing or empty.")
                     st.stop()
                product_df_local = st.session_state.product_df # Use local variable for safety

                acim_data_local = st.session_state.acim_form_responses # Use local variable

                room_requirements_list = acim_data_local.get('room_requirements', [])
                if not room_requirements_list:
                    show_error_message("No room requirements found in ACIM form data.")
                    logger.error("Aborting BOQ generation: No room requirements in acim_data.")
                    st.stop()

                first_room_type = room_requirements_list[0]['room_type']
                st.write(f"DEBUG: Detected first room type: '{first_room_type}'")
                logger.info(f"Detected first room type for processing: '{first_room_type}'")

                # Parse general client requirements from the first room's ACIM form data
                # This populates st.session_state.client_requirements needed by standard generator
                try:
                     st.session_state.client_requirements = parse_acim_to_client_requirements(acim_data_local)
                     logger.info("Successfully parsed ACIM to ClientRequirements object.")
                except Exception as parse_error:
                     show_error_message(f"Error parsing ACIM data: {parse_error}")
                     logger.error(f"Error in parse_acim_to_client_requirements: {parse_error}", exc_info=True)
                     st.stop()


                # Make the check more robust:
                room_type_lower = first_room_type.lower().strip()

                # ========== AUDITORIUM / TOWN HALL LOGIC ==========
                if 'auditorium' in room_type_lower or 'town hall' in room_type_lower:
                    st.write("DEBUG: Calling SPECIALIZED Auditorium/Town Hall generator...")
                    logger.info("Detected Auditorium/Town Hall - Using specialized generator.")
                    st.info("🎭 **Auditorium/Town Hall Detected** - Using specialized enterprise-grade generator")
                    progress_bar.progress(0.10, text="Loading specialized system designer...")

                    try:
                        # --- START: AUDITORIUM FIX INTEGRATION ---
                        from components.acim_parser_enhanced import generate_auditorium_boq
                        # calculate_avixa_recommendations already imported

                        # Extract dimensions for AVIXA calc
                        dimensions_response = room_requirements_list[0]['responses'].get('room_dimensions', '')
                        # Ensure using the correct default constants if available
                        default_len = getattr(st.session_state, 'DEFAULT_AUDITORIUM_LENGTH', 80.0)
                        default_wid = getattr(st.session_state, 'DEFAULT_AUDITORIUM_WIDTH', 60.0)
                        default_hei = getattr(st.session_state, 'DEFAULT_AUDITORIUM_HEIGHT', 20.0)

                        room_length, room_width, ceiling_height = _extract_dimensions_from_text(
                            dimensions_response, default_length=default_len, default_width=default_wid, default_height=default_hei
                        )
                        logger.info(f"Extracted dimensions for Auditorium: L={room_length:.1f} W={room_width:.1f} H={ceiling_height:.1f}")

                        # Perform AVIXA Calculations FIRST
                        progress_bar.progress(0.25, text="📊 Performing AVIXA calculations...")
                        avixa_calcs = calculate_avixa_recommendations(
                            room_length, room_width, ceiling_height, first_room_type
                        )
                        logger.info("AVIXA Calculations completed for Auditorium.")

                        # Call generator WITH avixa_calcs
                        progress_bar.progress(0.50, text="🛠️ Generating Auditorium blueprint & selecting products...")
                        # Ensure product_df_local is passed correctly
                        boq_items, validation = generate_auditorium_boq(acim_data_local, product_df_local, avixa_calcs)
                        logger.info(f"Auditorium generator returned {len(boq_items)} items.")
                        # --- END: AUDITORIUM FIX INTEGRATION ---

                        progress_bar.progress(0.85, text="Finalizing enterprise system design...")

                        if boq_items:
                            st.session_state.boq_items = boq_items
                            st.session_state.validation_results = validation
                            st.session_state.boq_selector = validation.get('selector_instance', None)

                            update_boq_content_with_current_items()

                            progress_bar.progress(1.0, text="✅ Auditorium BOQ generated!")
                            time.sleep(0.5); progress_bar.empty()

                            st.success(f"""
                            ✅ **Enterprise Auditorium/Town Hall System Generated**
                            - **Seating Capacity**: {validation.get('seating_capacity', 'N/A')} seats
                            - **System Components**: {len([i for i in boq_items if i.get('matched', True)])} items found ({len([i for i in boq_items if not i.get('matched', True)])} missing)
                            - **Estimated Investment**: ${validation.get('estimated_cost', 0):,.2f} ({validation.get('budget_status', '')})
                            - **System Grade**: Broadcast/Production Quality
                            """)
                            if validation.get('issues'):
                                st.error("🚨 Critical Issues Found:")
                                for issue in validation['issues']: st.write(f"- {issue}")
                            if validation.get('warnings'):
                                st.warning("⚠️ Warnings / Recommendations:")
                                for warning in validation['warnings']: st.write(f"- {warning}")

                            st.rerun()
                        else:
                            show_error_message("Failed to generate Auditorium BOQ items after processing. Check logs.")
                            logger.error("Auditorium BOQ generation resulted in an empty item list.")

                    except ImportError as ie:
                         show_error_message(f"Failed to import specialized Auditorium component: {ie}")
                         logger.error(f"ImportError in Auditorium path: {ie}", exc_info=True)
                         progress_bar.empty()
                    except Exception as auditorium_error:
                        show_error_message(f"Auditorium BOQ generation failed: {auditorium_error}")
                        logger.error(f"Error during Auditorium BOQ generation: {auditorium_error}", exc_info=True)
                        with st.expander("🔍 Technical Details"): st.code(traceback.format_exc())
                        progress_bar.empty()

                # ========== STANDARD ROOM TYPES LOGIC ==========
                else:
                    st.write("DEBUG: Calling STANDARD generator...")
                    logger.info("Detected Standard room type - Using standard generator.")
                    progress_bar.progress(0.15, text="Loading standard room designer...")

                    try:
                        from components.optimized_boq_generator import OptimizedBOQGenerator

                        # Ensure client_requirements exists in session state
                        if 'client_requirements' not in st.session_state or not isinstance(st.session_state.client_requirements, ClientRequirements):
                             show_error_message("Client Requirements not parsed correctly. Cannot proceed.")
                             logger.error("Aborting standard BOQ generation: client_requirements missing or invalid.")
                             st.stop()

                        generator = OptimizedBOQGenerator(
                            product_df=product_df_local, # Use local copy
                            client_requirements=st.session_state.client_requirements
                        )

                        all_boq_items = []
                        all_validations = {}
                        processed_rooms = 0

                        progress_bar.progress(0.30, text="🎯 Generating BOQ for each room...")
                        for idx, room_req in enumerate(room_requirements_list):
                            room_type = room_req['room_type']
                            responses = room_req['responses']
                            logger.info(f"Processing standard room {idx+1}: {room_type}")

                            dimensions_response = responses.get('room_dimensions', '') or responses.get('seating_layout', '')
                            room_length, room_width, ceiling_height = _extract_dimensions_from_text(
                                dimensions_response, default_length=28.0, default_width=20.0, default_height=10.0
                            )
                            logger.info(f"  Extracted dimensions: L={room_length:.1f} W={room_width:.1f} H={ceiling_height:.1f}")

                            standard_room_type = _map_acim_to_standard_room(room_type)
                            logger.info(f"  Mapped to standard profile: {standard_room_type}")

                            # Generate BOQ for this room
                            boq_items, validation = generator.generate_boq_for_room(
                                room_type=standard_room_type,
                                room_length=room_length,
                                room_width=room_width,
                                ceiling_height=ceiling_height
                            )
                            logger.info(f"  Generated {len(boq_items)} items for {room_type}")

                            # Tag items with room name
                            for item in boq_items: item['room_name'] = f"{room_type} ({idx+1})"

                            all_boq_items.extend(boq_items)
                            all_validations[f"{room_type}_{idx}"] = validation # Use unique key
                            processed_rooms += 1

                            progress_value = 0.30 + (processed_rooms / len(room_requirements_list)) * 0.60
                            progress_bar.progress(progress_value,
                                                 text=f"Processed room {processed_rooms}/{len(room_requirements_list)}: {room_type}")

                        progress_bar.progress(0.95, text="⚖️ Calculating Quality Score...")

                        if all_boq_items:
                            # Combine validations
                            combined_validation = {'warnings': [], 'issues': [], 'compliance_score': 0}
                            total_score = 0
                            valid_room_count = 0
                            for room_key, val in all_validations.items():
                                if isinstance(val, dict): # Check if validation result is valid
                                     combined_validation['warnings'].extend(val.get('warnings', []))
                                     combined_validation['issues'].extend(val.get('issues', []))
                                     total_score += val.get('compliance_score', 0)
                                     valid_room_count += 1
                                else:
                                     logger.warning(f"Invalid validation result for room {room_key}: {val}")


                            combined_validation['compliance_score'] = (total_score / valid_room_count) if valid_room_count > 0 else 0

                            quality_score = generator.calculate_boq_quality_score(all_boq_items, combined_validation)
                            st.session_state.boq_quality_score = quality_score

                            st.session_state.boq_items = all_boq_items
                            st.session_state.validation_results = combined_validation
                            st.session_state.boq_selector = generator.selector # Store selector instance

                            # Display Quality Score (moved outside try block for clarity)


                            update_boq_content_with_current_items()

                            progress_bar.progress(1.0, text="✅ BOQ generation complete!")
                            time.sleep(0.5); progress_bar.empty()

                            show_success_message(f"BOQ Generated Successfully for {len(room_requirements_list)} Room Type(s)")

                            # Display Quality Score after success message
                            st.markdown("---")
                            col_q1, col_q2, col_q3 = st.columns([1, 2, 1])
                            with col_q1:
                                st.metric("BOQ Quality Score", f"{quality_score['percentage']:.1f}%", f"Grade: {quality_score['grade']}")
                            with col_q2:
                                st.markdown(f"""
                                <div style="background: linear-gradient(135deg, {quality_score['color']}22, {quality_score['color']}44);
                                             border-left: 4px solid {quality_score['color']}; padding: 1rem; border-radius: 8px;">
                                    <h3 style="margin: 0; color: {quality_score['color']};">{quality_score['quality_level']}</h3>
                                    <p style="margin: 0.5rem 0 0 0; color: #666;">Generated BOQ for {len(room_requirements_list)} room type(s)</p>
                                </div>""", unsafe_allow_html=True)
                            with col_q3:
                                with st.expander("📊 Score Breakdown"):
                                    for category, score in quality_score['breakdown'].items():
                                        max_score = quality_score['max_breakdown'].get(category, 0) # Use .get()
                                        pct = (score / max_score) * 100 if max_score > 0 else 0
                                        st.progress(pct / 100, text=f"{category.replace('_', ' ').title()}: {score:.0f}/{max_score}")

                            # Show optimization status
                            if len(room_requirements_list) >= 3:
                                st.info("""
                                🔧 **Multi-Room Project Detected**
                                When you export to Excel, the system can consolidate infrastructure if enabled in the sidebar.
                                💰 **Potential Savings:** 8-15% on shared infrastructure.
                                """)

                        else:
                            show_error_message("Failed to generate BOQ items from ACIM form. Check logs.")
                            logger.error("Standard BOQ generation resulted in an empty item list.")

                    except ImportError as ie:
                         show_error_message(f"Failed to import standard BOQ component: {ie}")
                         logger.error(f"ImportError in Standard path: {ie}", exc_info=True)
                         progress_bar.empty()
                    except Exception as standard_error:
                        show_error_message(f"Standard BOQ generation failed: {standard_error}")
                        logger.error(f"Error during Standard BOQ generation: {standard_error}", exc_info=True)
                        with st.expander("🔍 Technical Details"): st.code(traceback.format_exc())
                        progress_bar.empty()


            # Generic Exception Handler for the entire button press
            except Exception as e:
                if 'progress_bar' in locals() and progress_bar: progress_bar.empty()
                show_error_message(f"An unexpected error occurred during BOQ generation: {e}")
                logger.critical(f"Unhandled error in BOQ generation button: {e}", exc_info=True)
                with st.expander("🔍 Technical Details"): st.code(traceback.format_exc())


        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

        # Display BOQ results (if items exist)
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
                'Client Type': "Local (India)" if st.session_state.get('client_is_local', True) else "International",
                'Existing Customer': "Yes" if st.session_state.get('is_existing_customer') else "No",
                'Currency': st.session_state.get('currency_select', 'INR')
            }
            display_boq_results(product_df, project_details) # Pass product_df for potential lookups

            # AI OPTIMIZATION
            if st.session_state.get('boq_items') and model:
                with st.expander("💡 AI-Powered Cost Optimization Suggestions"):
                    if st.button("Generate Optimization Suggestions", key="optimize_btn"):
                        with st.spinner("AI analyzing BOQ..."):
                            try:
                                from components.gemini_handler import generate_cost_optimization_suggestions
                                suggestions = generate_cost_optimization_suggestions(
                                    model=model, boq_items=st.session_state.boq_items,
                                    room_type=st.session_state.get('room_type_select', 'Conference Room'),
                                    budget_tier=st.session_state.get('budget_tier_slider', 'Standard')
                                )
                                if suggestions:
                                    st.markdown("### 🎯 Optimization Opportunities")
                                    for suggestion in suggestions: st.markdown(f"- {suggestion}")
                                else: st.info("No clear optimization opportunities found.")
                            except Exception as ai_opt_error:
                                show_error_message(f"AI Optimization Error: {ai_opt_error}")
                                logger.error(f"Error during AI Optimization: {ai_opt_error}", exc_info=True)

        else:
            st.info("👆 Complete the ACIM form and click 'Generate BOQ' to create your Bill of Quantities")

    with tab4:
        st.markdown('<h2 class="section-header section-header-viz">Interactive 3D Room Visualization</h2>', unsafe_allow_html=True)

        if st.button("🎨 Generate 3D Visualization", use_container_width=True, key="generate_viz_btn"):
            with st.spinner("Rendering 3D environment..."):
                try:
                    viz_html = create_3d_visualization() # Assuming this function exists
                    if viz_html:
                        st.components.v1.html(viz_html, height=700, scrolling=False)
                        show_success_message("3D Visualization rendered successfully")
                    else: show_error_message("Failed to generate 3D visualization")
                except Exception as viz_error:
                    show_error_message(f"Visualization Error: {viz_error}")
                    logger.error(f"Error during 3D Visualization: {viz_error}", exc_info=True)

        st.markdown("""
        <div class="info-box" style="margin-top: 1.5rem;">
            <p><b>💡 Visualization Controls:</b> Rotate: Left-click + drag | Zoom: Scroll wheel | Pan: Right-click + drag</p>
        </div>""", unsafe_allow_html=True)

    # --- Footer ---
    st.markdown(f"""
    <div class="custom-footer">
        <p>© {datetime.now().year} AllWave Audio Visual & General Services | Powered by AI-driven Design Engine</p>
        <p style="font-size: 0.8rem; margin-top: 0.5rem;">Built with Streamlit • Gemini AI • AVIXA Standards Compliance</p>
    </div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
