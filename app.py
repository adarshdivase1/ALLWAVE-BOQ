import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import json
import time
import streamlit.components.v1 as components
from io import BytesIO

# --- New Dependencies ---
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# --- Page Configuration ---
st.set_page_config(
    page_title="Professional AV BOQ Generator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Currency Conversion ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_usd_to_inr_rate():
    """Get current USD to INR exchange rate. Falls back to approximate rate if API fails."""
    try:
        # You can integrate a free API like exchangerate-api.com here
        # For now, using approximate rate
        return 83.5  # Approximate USD to INR rate - update this or use real API
    except:
        return 83.5  # Fallback rate

def convert_currency(amount_usd, to_currency="INR"):
    """Convert USD amount to specified currency."""
    if to_currency == "INR":
        rate = get_usd_to_inr_rate()
        return amount_usd * rate
    return amount_usd

def format_currency(amount, currency="USD"):
    """Format currency with proper symbols and formatting."""
    if currency == "INR":
        return f"₹{amount:,.0f}"
    else:
        return f"${amount:,.2f}"

# --- Enhanced Data Loading with Validation (UPDATED) ---
@st.cache_data
def load_and_validate_data():
    """Enhanced loads and validates with image URLs and GST data."""
    try:
        df = pd.read_csv("master_product_catalog.csv")
        
        # --- Existing validation code ---
        validation_issues = []
        
        # Check for missing critical data
        if df['name'].isnull().sum() > 0:
            validation_issues.append(f"{df['name'].isnull().sum()} products missing names")
        
        # Check for zero/missing prices
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
            zero_price_count = (df['price'] == 0.0).sum()
            if zero_price_count > 100:
                validation_issues.append(f"{zero_price_count} products have zero pricing")
        else:
            df['price'] = 0.0
            validation_issues.append("Price column missing - using default values")
            
        # Brand validation
        if 'brand' not in df.columns:
            df['brand'] = 'Unknown'
            validation_issues.append("Brand column missing - using default values")
        elif df['brand'].isnull().sum() > 0:
            df['brand'] = df['brand'].fillna('Unknown')
            validation_issues.append(f"{df['brand'].isnull().sum()} products missing brand information")
        
        # Category validation
        if 'category' not in df.columns:
            df['category'] = 'General'
            validation_issues.append("Category column missing - using default values")
        else:
            df['category'] = df['category'].fillna('General')
            categories = df['category'].value_counts()
            essential_categories = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts']
            missing_categories = [cat for cat in essential_categories if cat not in categories.index]
            if missing_categories:
                validation_issues.append(f"Missing essential categories: {missing_categories}")
        
        if 'features' not in df.columns:
            df['features'] = df['name']
            validation_issues.append("Features column missing - using product names for search")
        else:
            df['features'] = df['features'].fillna('')

        # --- NEW ADDITIONS ---
        if 'image_url' not in df.columns:
            df['image_url'] = ''  # Will be populated later or manually
            validation_issues.append("Image URL column missing - images won't display in Excel")
            
        if 'gst_rate' not in df.columns:
            df['gst_rate'] = 18  # Default 18% GST for electronics
            validation_issues.append("GST rate column missing - using 18% default")
        
        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found. Using basic industry standards."
            validation_issues.append("AVIXA guidelines file missing")
        
        return df, guidelines, validation_issues
        
    except FileNotFoundError:
        st.error("FATAL: 'master_product_catalog.csv' not found. Please ensure the file is in the same directory.")
        return None, None, ["Product catalog file not found"]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]


# --- Enhanced Room Specifications Database ---
ROOM_SPECS = {
    "Small Huddle Room (2-3 People)": {
        "area_sqft": (40, 80),
        "recommended_display_size": (32, 43),
        "viewing_distance_ft": (4, 6),
        "audio_coverage": "Near-field single speaker",
        "camera_type": "Fixed wide-angle",
        "power_requirements": "Standard 15A circuit",
        "network_ports": 1,
        "typical_budget_range": (3000, 8000),
        "furniture_config": "small_huddle",
        "table_size": [4, 2.5],
        "chair_count": 3,
        "chair_arrangement": "casual"
    },
    "Medium Huddle Room (4-6 People)": {
        "area_sqft": (80, 150),
        "recommended_display_size": (43, 55),
        "viewing_distance_ft": (6, 10),
        "audio_coverage": "Near-field stereo",
        "camera_type": "Fixed wide-angle with auto-framing",
        "power_requirements": "Standard 15A circuit",
        "network_ports": 2,
        "typical_budget_range": (8000, 18000),
        "furniture_config": "medium_huddle",
        "table_size": [6, 3],
        "chair_count": 6,
        "chair_arrangement": "round_table"
    },
    "Standard Conference Room (6-8 People)": {
        "area_sqft": (150, 250),
        "recommended_display_size": (55, 65),
        "viewing_distance_ft": (8, 12),
        "audio_coverage": "Room-wide with ceiling mics",
        "camera_type": "PTZ or wide-angle with tracking",
        "power_requirements": "20A dedicated circuit recommended",
        "network_ports": 2,
        "typical_budget_range": (15000, 30000),
        "furniture_config": "standard_conference",
        "table_size": [10, 4],
        "chair_count": 8,
        "chair_arrangement": "rectangular"
    },
    "Large Conference Room (8-12 People)": {
        "area_sqft": (300, 450),
        "recommended_display_size": (65, 75),
        "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed ceiling mics with expansion",
        "camera_type": "PTZ with presenter tracking",
        "power_requirements": "20A dedicated circuit",
        "network_ports": 3,
        "typical_budget_range": (25000, 50000),
        "furniture_config": "large_conference",
        "table_size": [16, 5],
        "chair_count": 12,
        "chair_arrangement": "rectangular"
    },
    "Executive Boardroom (10-16 People)": {
        "area_sqft": (400, 700),
        "recommended_display_size": (75, 86),
        "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling and table mics",
        "camera_type": "Multiple cameras with auto-switching",
        "power_requirements": "30A dedicated circuit",
        "network_ports": 4,
        "typical_budget_range": (50000, 100000),
        "furniture_config": "executive_boardroom",
        "table_size": [20, 6],
        "chair_count": 16,
        "chair_arrangement": "oval"
    },
    "Training Room (15-25 People)": {
        "area_sqft": (500, 800),
        "recommended_display_size": (65, 86),
        "viewing_distance_ft": (10, 18),
        "audio_coverage": "Distributed with wireless mic support",
        "camera_type": "Fixed or PTZ for presenter tracking",
        "power_requirements": "20A circuit with UPS backup",
        "network_ports": 3,
        "typical_budget_range": (30000, 70000),
        "furniture_config": "training_room",
        "table_size": [10, 4],
        "chair_count": 25,
        "chair_arrangement": "classroom"
    },
    "Large Training/Presentation Room (25-40 People)": {
        "area_sqft": (800, 1200),
        "recommended_display_size": (86, 98),
        "viewing_distance_ft": (15, 25),
        "audio_coverage": "Full distributed system with handheld mics",
        "camera_type": "Multiple PTZ cameras",
        "power_requirements": "30A circuit with UPS backup",
        "network_ports": 4,
        "typical_budget_range": (60000, 120000),
        "furniture_config": "large_training",
        "table_size": [12, 4],
        "chair_count": 40,
        "chair_arrangement": "theater"
    },
    "Multipurpose Event Room (40+ People)": {
        "area_sqft": (1200, 2000),
        "recommended_display_size": (98, 110),
        "viewing_distance_ft": (20, 35),
        "audio_coverage": "Professional distributed PA system",
        "camera_type": "Professional multi-camera setup",
        "power_requirements": "Multiple 30A circuits",
        "network_ports": 6,
        "typical_budget_range": (100000, 250000),
        "furniture_config": "multipurpose_event",
        "table_size": [16, 6],
        "chair_count": 50,
        "chair_arrangement": "flexible"
    },
    "Video Production Studio": {
        "area_sqft": (400, 600),
        "recommended_display_size": (32, 55),
        "viewing_distance_ft": (6, 12),
        "audio_coverage": "Professional studio monitors",
        "camera_type": "Professional broadcast cameras",
        "power_requirements": "Multiple 20A circuits",
        "network_ports": 4,
        "typical_budget_range": (75000, 200000),
        "furniture_config": "production_studio",
        "table_size": [12, 5],
        "chair_count": 6,
        "chair_arrangement": "production"
    },
    "Telepresence Suite": {
        "area_sqft": (350, 500),
        "recommended_display_size": (65, 98),
        "viewing_distance_ft": (8, 14),
        "audio_coverage": "High-fidelity spatial audio",
        "camera_type": "Multiple high-res cameras with AI tracking",
        "power_requirements": "20A dedicated circuit",
        "network_ports": 3,
        "typical_budget_range": (80000, 180000),
        "furniture_config": "telepresence",
        "table_size": [14, 4],
        "chair_count": 8,
        "chair_arrangement": "telepresence"
    }
}

# --- Gemini Configuration ---
def setup_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except Exception as e:
        st.error(f"Gemini API configuration failed: {e}")
        return None

def generate_with_retry(model, prompt, max_retries=3):
    """Generate content with retry logic and error handling."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

# --- NEW: Enhanced BOQ Generation with Justifications ---
def generate_boq_with_justifications(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Enhanced BOQ generation that includes WHY column with justifications."""
    
    room_spec = ROOM_SPECS[room_type]
    product_catalog_string = product_df.head(150).to_csv(index=False)
    
   enhanced_prompt = f"""
You are a Professional AV Systems Engineer with 15+ years of experience creating detailed BOQs for the Indian market. Create a production-ready BOQ.

**PROJECT SPECIFICATIONS:**
- Room Type: {room_type}
- Room Area: {room_area:.0f} sq ft
- Budget Tier: {budget_tier}
- Special Requirements: {features}
- Infrastructure: {technical_reqs}

**TECHNICAL CONSTRAINTS & GUIDELINES:**
- Adhere to the provided AVIXA standards.
- Display size range: {room_spec['recommended_display_size'][0]}"-{room_spec['recommended_display_size'][1]}"
- Viewing distance: {room_spec['viewing_distance_ft'][0]}-{room_spec['viewing_distance_ft'][1]} ft
- Audio coverage: {room_spec['audio_coverage']}
- Budget target: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}

**MANDATORY REQUIREMENTS:**
1. ONLY use products from the provided product catalog sample. Do not invent products.
2. The 'Model No.' must be the same as the 'name' column from the catalog.
3. For EACH product, provide a concise, single-line technical description.
4. Categorize each item into a 'System' like 'Display System', 'Audio System', 'Video Conferencing', 'Control System', 'Cables & Connectivity', etc.
5. Provide a 'UoM' (Unit of Measure) for each item (e.g., Nos, Set, Lot).
6. Include appropriate mounting, cabling, and installation services as line items.
7. Add standard service line items (Installation, Warranty, Project Management).

**OUTPUT FORMAT REQUIREMENT:**
Start with a brief System Design Summary, then provide the BOQ in a Markdown table with these exact columns:
| System | Brand | Model No. | Description | Qty | UoM |

**PRODUCT CATALOG SAMPLE:**
{product_catalog_string}

**AVIXA GUIDELINES:**
{guidelines}

Generate the detailed BOQ with justifications:
"""
    
    try:
        response = generate_with_retry(model, enhanced_prompt)
        if response and response.text:
            boq_content = response.text
            boq_items = extract_enhanced_boq_items(boq_content, product_df)
            return boq_content, boq_items
        return None, []
    except Exception as e:
        st.error(f"Enhanced BOQ generation failed: {str(e)}")
        return None, []


# --- BOQ Validation & Data Extraction ---
class BOQValidator:
    def __init__(self, room_specs, product_df):
        self.room_specs = room_specs
        self.product_df = product_df
    
    def validate_technical_requirements(self, boq_items, room_type, room_area=None):
        issues = []
        warnings = []
        
        # Check display sizing
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            room_spec = self.room_specs.get(room_type, {})
            recommended_size = room_spec.get('recommended_display_size', (32, 98))
            
            for display in displays:
                size_match = re.search(r'(\d+)"', display.get('name', ''))
                if size_match:
                    size = int(size_match.group(1))
                    if size < recommended_size[0]:
                        warnings.append(f"Display size {size}\" may be too small for {room_type}")
                    elif size > recommended_size[1]:
                        warnings.append(f"Display size {size}\" may be too large for {room_type}")
        
        # Check for essential components
        essential_categories = ['display', 'audio', 'control']
        found_categories = [item.get('category', '').lower() for item in boq_items]
        
        for essential in essential_categories:
            if not any(essential in cat for cat in found_categories):
                issues.append(f"Missing essential component: {essential}")
        
        # Power consumption estimation (simplified)
        total_estimated_power = len(boq_items) * 150  # Rough estimate
        if total_estimated_power > 1800:
            warnings.append("System may require a dedicated 20A circuit")
        
        return issues, warnings

def validate_against_avixa(model, guidelines, boq_items):
    """Use AI to validate the BOQ against AVIXA standards."""
    if not guidelines or not boq_items:
        return []
    
    prompt = f"""
    You are an AVIXA Certified Technology Specialist (CTS). Review the following BOQ against the provided AVIXA standards.
    List any potential non-compliance issues, missing items (like accessibility components), or areas for improvement.
    If no issues are found, respond with 'No specific compliance issues found.'

    **AVIXA Standards Summary:**
    {guidelines}

    **Bill of Quantities to Review:**
    {json.dumps(boq_items, indent=2)}

    **Your Compliance Review:**
    """
    try:
        response = generate_with_retry(model, prompt)
        if response and response.text:
            if "no specific compliance issues" in response.text.lower():
                return []
            return [line.strip() for line in response.text.split('\n') if line.strip()]
        return []
    except Exception as e:
        return [f"AVIXA compliance check failed: {str(e)}"]

# --- NEW: Enhanced BOQ Item Extraction ---
def extract_enhanced_boq_items(boq_content, product_df):
    """Extract BOQ items with justifications from AI response."""
    items = []
    lines = boq_content.split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        
        # Detect table start
        if '|' in line and any(keyword in line.lower() for keyword in ['system', 'model no.', 'brand']):
            in_table = True
            continue
            
        # Skip separator lines
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
            
        # Process table rows
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 6:
                system = parts[0]
                brand = parts[1]
                model_no = parts[2]
                description = parts[3]
                
                try:
                    quantity = int(parts[4])
                except (ValueError, IndexError):
                    quantity = 1
                
                uom = parts[5] if len(parts) > 5 else 'Nos'
                
                # Match with product database to get price and other details
                matched_product = match_product_in_database(model_no, brand, product_df)
                
                if matched_product is not None:
                    price = float(matched_product.get('price', 0))
                    image_url = matched_product.get('image_url', '')
                    gst_rate = matched_product.get('gst_rate', 18)
                else:
                    # Handle services or unmatched items
                    price = 0
                    image_url = ''
                    gst_rate = 18 if 'service' in system.lower() else 18

                items.append({
                    'system': system,
                    'brand': brand,
                    'model_no': model_no, # Using model_no as the primary identifier now
                    'name': model_no,    # Keep 'name' for compatibility with other functions
                    'description': description,
                    'quantity': quantity,
                    'uom': uom,
                    'price': price,
                    'image_url': image_url,
                    'gst_rate': gst_rate,
                    'matched': matched_product is not None,
                    'category': system # Use 'system' as the new 'category'
                })
                
        elif in_table and not line.startswith('|'):
            in_table = False
    
    return items
def match_product_in_database(product_name, brand, product_df):
    """Try to match a product name and brand with the database."""
    if product_df is None or len(product_df) == 0:
        return None
    
    # Try exact brand and partial name match
    brand_matches = product_df[product_df['brand'].str.contains(brand, case=False, na=False)]
    if len(brand_matches) > 0:
        name_matches = brand_matches[brand_matches['name'].str.contains(product_name[:20], case=False, na=False)]
        if len(name_matches) > 0:
            return name_matches.iloc[0].to_dict()
    
    # Try partial name match across all products
    name_matches = product_df[product_df['name'].str.contains(product_name[:15], case=False, na=False)]
    if len(name_matches) > 0:
        return name_matches.iloc[0].to_dict()
    
    return None

def normalize_category(category_text, product_name):
    """Normalize category names to standard categories."""
    category_lower = category_text.lower()
    product_lower = product_name.lower()
    
    if any(term in category_lower or term in product_lower for term in ['display', 'monitor', 'screen', 'projector', 'tv']):
        return 'Displays'
    elif any(term in category_lower or term in product_lower for term in ['audio', 'speaker', 'microphone', 'sound', 'amplifier']):
        return 'Audio'
    elif any(term in category_lower or term in product_lower for term in ['video', 'conferencing', 'camera', 'codec', 'rally']):
        return 'Video Conferencing'
    elif any(term in category_lower or term in product_lower for term in ['control', 'processor', 'switch', 'matrix']):
        return 'Control'
    elif any(term in category_lower or term in product_lower for term in ['mount', 'bracket', 'rack', 'stand']):
        return 'Mounts'
    elif any(term in category_lower or term in product_lower for term in ['cable', 'connect', 'wire', 'hdmi', 'usb']):
        return 'Cables'
    else:
        return 'General'

# --- UI Components ---
def create_project_header():
    """Create professional project header."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("Professional AV BOQ Generator")
        st.caption("Production-ready Bill of Quantities with technical validation")
    
    with col2:
        project_id = st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}", key="project_id_input")
    
    with col3:
        quote_valid_days = st.number_input("Quote Valid (Days)", min_value=15, max_value=90, value=30, key="quote_days_input")
    
    return project_id, quote_valid_days

def create_room_calculator():
    """Room size calculator and validator."""
    st.subheader("Room Analysis & Specifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        room_length = st.number_input("Room Length (ft)", min_value=10.0, max_value=80.0, value=28.0, key="room_length_input")
        room_width = st.number_input("Room Width (ft)", min_value=8.0, max_value=50.0, value=20.0, key="room_width_input")
        ceiling_height = st.number_input("Ceiling Height (ft)", min_value=8.0, max_value=20.0, value=10.0, key="ceiling_height_input")
    
    with col2:
        room_area = room_length * room_width
        st.metric("Room Area", f"{room_area:.0f} sq ft")
        
        # Recommend room type based on area
        recommended_type = None
        for room_type, specs in ROOM_SPECS.items():
            if specs["area_sqft"][0] <= room_area <= specs["area_sqft"][1]:
                recommended_type = room_type
                break
        
        if recommended_type:
            st.success(f"Recommended Room Type: {recommended_type}")
        else:
            st.warning("Room size is outside typical ranges")
    
    return room_area, ceiling_height

def create_advanced_requirements():
    """Advanced technical requirements input."""
    st.subheader("Technical Requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Infrastructure**")
        has_dedicated_circuit = st.checkbox("Dedicated 20A Circuit Available", key="dedicated_circuit_checkbox")
        network_capability = st.selectbox("Network Infrastructure", ["Standard 1Gb", "10Gb Capable", "Fiber Available"], key="network_capability_select")
        cable_management = st.selectbox("Cable Management", ["Exposed", "Conduit", "Raised Floor", "Drop Ceiling"], key="cable_management_select")
    
    with col2:
        st.write("**Compliance & Standards**")
        ada_compliance = st.checkbox("ADA Compliance Required", key="ada_compliance_checkbox")
        fire_code_compliance = st.checkbox("Fire Code Compliance Required", key="fire_code_compliance_checkbox")
        security_clearance = st.selectbox("Security Level", ["Standard", "Restricted", "Classified"], key="security_clearance_select")
    
    return {
        "dedicated_circuit": has_dedicated_circuit,
        "network_capability": network_capability,
        "cable_management": cable_management,
        "ada_compliance": ada_compliance,
        "fire_code_compliance": fire_code_compliance,
        "security_clearance": security_clearance
    }

# --- NEW: Multi-Room Interface ---
def create_multi_room_interface():
    """Interface for managing multiple rooms in a project."""
    st.subheader("Multi-Room Project Management")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        room_name = st.text_input("New Room Name", value=f"Room {len(st.session_state.project_rooms) + 1}")
    
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Add New Room to Project", type="primary", use_container_width=True):
            new_room = {
                'name': room_name,
                'type': st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)'),
                'area': st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16),
                'boq_items': [],
                'features': st.session_state.get('features_text_area', ''),
                'technical_reqs': {}
            }
            st.session_state.project_rooms.append(new_room)
            st.success(f"Added '{room_name}' to the project.")
            st.rerun()
    
    with col3:
        st.write("")
        st.write("")
        if st.session_state.project_rooms:
            excel_data = generate_professional_excel(rooms_data=st.session_state.project_rooms)
            project_name = st.session_state.get('project_name_input', 'Multi_Room_Project')
            filename = f"{project_name}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            st.download_button(
                label="📊 Download Full Project BOQ",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="secondary"
            )


    # Display current rooms
    if st.session_state.project_rooms:
        st.markdown("---")
        st.write("**Current Project Rooms:**")
        
        # Create a list of room names for the selectbox
        room_options = [room['name'] for room in st.session_state.project_rooms]
        
        # Find the index of the currently selected room
        try:
            current_index = st.session_state.current_room_index
        except AttributeError:
            current_index = 0
            st.session_state.current_room_index = 0
            
        selected_room_name = st.selectbox(
            "Select a room to view or edit its BOQ:",
            options=room_options,
            index=current_index,
            key="room_selector"
        )
        
        # Update the current_room_index when selection changes
        new_index = room_options.index(selected_room_name)
        if new_index != st.session_state.current_room_index:
            st.session_state.current_room_index = new_index
            # Load the selected room's BOQ into the main editor state
            selected_room_boq = st.session_state.project_rooms[new_index].get('boq_items', [])
            st.session_state.boq_items = selected_room_boq
            update_boq_content_with_current_items()
            st.rerun()
            
        # Display details and actions for the selected room
        selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
        st.info(f"You are currently editing **{selected_room['name']}**. Any generated or edited BOQ will be saved for this room.")
        
        if st.button(f"🗑️ Remove '{selected_room['name']}' from Project", type="secondary"):
            st.session_state.project_rooms.pop(st.session_state.current_room_index)
            st.session_state.current_room_index = 0
            st.session_state.boq_items = [] # Clear the editor
            st.rerun()

# --- BOQ Display and Editing ---
def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items added yet."
        return
    
    boq_content = "## Bill of Quantities\n\n"
    boq_content += "| Category | Brand | Product Name | Qty | Unit Price (USD) | Total (USD) | WHY (Justification) |\n"
    boq_content += "|---|---|---|---|---|---|---|\n"
    
    total_cost = 0
    for item in st.session_state.boq_items:
        quantity = item.get('quantity', 1)
        price = item.get('price', 0)
        total = quantity * price
        total_cost += total
        
        boq_content += f"| {item.get('category', 'N/A')} | {item.get('brand', 'N/A')} | {item.get('name', 'N/A')} | {quantity} | ${price:,.2f} | ${total:,.2f} | {item.get('justification', '')} |\n"
    
    st.session_state.boq_content = boq_content

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days, product_df):
    """Display BOQ results with interactive editing capabilities."""
    
    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    st.subheader(f"Generated Bill of Quantities ({item_count} items)")
    
    # Validation results
    if validation_results and validation_results.get('issues'):
        st.error("Critical Issues Found:")
        for issue in validation_results['issues']: st.write(f"- {issue}")
    
    if validation_results and validation_results.get('warnings'):
        st.warning("Technical Recommendations & Compliance Notes:")
        for warning in validation_results['warnings']: st.write(f"- {warning}")
    
    # Display BOQ content
    if boq_content:
        st.markdown(boq_content)
    else:
        st.info("No BOQ content generated yet. Use the interactive editor below.")
    
    # Totals
    if 'boq_items' in st.session_state and st.session_state.boq_items:
        currency = st.session_state.get('currency', 'USD')
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        
        if currency == 'INR':
            display_total = convert_currency(total_cost * 1.30, 'INR') # Include services
            st.metric("Estimated Project Total", format_currency(display_total, 'INR'), help="Includes installation, warranty, and contingency")
        else:
            st.metric("Estimated Project Total", format_currency(total_cost * 1.30, 'USD'), help="Includes installation, warranty, and contingency")
    
    # Interactive Editor
    st.markdown("---")
    create_interactive_boq_editor(product_df)

def create_interactive_boq_editor(product_df):
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    
    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Items in BOQ", item_count)
    
    with col2:
        if 'boq_items' in st.session_state and st.session_state.boq_items:
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            currency = st.session_state.get('currency', 'USD')
            if currency == 'INR':
                display_total = convert_currency(total_cost, 'INR')
                st.metric("Hardware Subtotal", format_currency(display_total, 'INR'))
            else:
                st.metric("Hardware Subtotal", format_currency(total_cost, 'USD'))
        else:
            st.metric("Subtotal", "₹0" if st.session_state.get('currency', 'USD') == 'INR' else "$0")
    
    with col3:
        if st.button("🔄 Refresh BOQ Display", help="Update the main BOQ display with current items"):
            update_boq_content_with_current_items()
            st.rerun()
    
    if product_df is None:
        st.error("Cannot load product catalog for editing.")
        return
    
    currency = st.session_state.get('currency', 'USD')
    tabs = st.tabs(["Edit Current BOQ", "Add Products", "Product Search"])
    
    with tabs[0]:
        edit_current_boq(currency)
    with tabs[1]:
        add_products_interface(product_df, currency)
    with tabs[2]:
        product_search_interface(product_df, currency)

def edit_current_boq(currency):
    """Interface for editing current BOQ items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ or add products manually.")
        return
    
    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        category_str = str(item.get('category', 'General'))
        name_str = str(item.get('name', 'Unknown'))
        
        with st.expander(f"{category_str} - {name_str[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                new_name = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                new_brand = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")
            
            with col2:
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_category = item.get('category', 'General')
                if current_category not in category_list: current_category = 'General'
                
                new_category = st.selectbox("Category", category_list, index=category_list.index(current_category), key=f"category_{i}")
            
            with col3:
                try:
                    safe_quantity = max(1, int(float(item.get('quantity', 1))))
                except (ValueError, TypeError):
                    safe_quantity = 1
                
                new_quantity = st.number_input("Quantity", min_value=1, value=safe_quantity, key=f"qty_{i}")
                
                try:
                    current_price = float(item.get('price', 0))
                except (ValueError, TypeError):
                    current_price = 0
                
                display_price = convert_currency(current_price, 'INR') if currency == 'INR' else current_price
                
                new_price = st.number_input(f"Unit Price ({currency})", min_value=0.0, value=float(display_price), key=f"price_{i}")
                
                stored_price = new_price / get_usd_to_inr_rate() if currency == 'INR' else new_price
            
            with col4:
                total_price = stored_price * new_quantity
                display_total = convert_currency(total_price, 'INR') if currency == 'INR' else total_price
                st.metric("Total", format_currency(display_total, currency))
                
                if st.button("Remove", key=f"remove_{i}", type="secondary"):
                    items_to_remove.append(i)
            
            st.session_state.boq_items[i].update({
                'name': new_name, 'brand': new_brand, 'category': new_category,
                'quantity': new_quantity, 'price': stored_price
            })

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()

def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ."""
    st.write("**Add Products to BOQ:**")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        categories = ['All'] + sorted(list(product_df['category'].unique()))
        selected_category = st.selectbox("Filter by Category", categories, key="add_category_filter")
        
        filtered_df = product_df[product_df['category'] == selected_category] if selected_category != 'All' else product_df
        
        product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
        if not product_options:
            st.warning("No products found.")
            return

        selected_product_str = st.selectbox("Select Product", product_options, key="add_product_select")
        selected_product = next((row for _, row in filtered_df.iterrows() if f"{row['brand']} - {row['name']}" == selected_product_str), None)
    
    with col2:
        if selected_product is not None:
            quantity = st.number_input("Quantity", min_value=1, value=1, key="add_product_qty")
            base_price = float(selected_product.get('price', 0))
            display_price = convert_currency(base_price, 'INR') if currency == 'INR' else base_price
            
            st.metric("Unit Price", format_currency(display_price, currency))
            st.metric("Total", format_currency(display_price * quantity, currency))
            
            if st.button("Add to BOQ", type="primary"):
                new_item = {
                    'category': selected_product.get('category', 'General'), 'name': selected_product.get('name', ''),
                    'brand': selected_product.get('brand', ''), 'quantity': quantity, 'price': base_price,
                    'justification': 'Manually added component.', 'image_url': selected_product.get('image_url', ''),
                    'gst_rate': selected_product.get('gst_rate', 18), 'matched': True
                }
                st.session_state.boq_items.append(new_item)
                update_boq_content_with_current_items()
                st.success(f"Added {quantity}x {selected_product['name']}!")
                st.rerun()

def product_search_interface(product_df, currency):
    """Advanced product search interface."""
    st.write("**Search Product Catalog:**")
    search_term = st.text_input("Search products...", placeholder="Enter name, brand, or features", key="search_term_input")
    
    if search_term:
        search_cols = ['name', 'brand', 'features']
        mask = product_df[search_cols].apply(
            lambda x: x.astype(str).str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        search_results = product_df[mask]
        
        st.write(f"Found {len(search_results)} products:")
        
        for i, product in search_results.head(10).iterrows():
            with st.expander(f"{product.get('brand', '')} - {product.get('name', '')[:60]}..."):
                col_a, col_b, col_c = st.columns([2, 1, 1])
                
                with col_a:
                    st.write(f"**Category:** {product.get('category', 'N/A')}")
                    if pd.notna(product.get('features')):
                        st.write(f"**Features:** {str(product['features'])[:100]}...")
                
                with col_b:
                    price = float(product.get('price', 0))
                    display_price = convert_currency(price, 'INR') if currency == 'INR' else price
                    st.metric("Price", format_currency(display_price, currency))
                
                with col_c:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        new_item = {
                            'category': product.get('category', 'General'), 'name': product.get('name', ''),
                            'brand': product.get('brand', ''), 'quantity': add_qty, 'price': price,
                            'justification': 'Added via search.', 'image_url': product.get('image_url', ''),
                            'gst_rate': product.get('gst_rate', 18), 'matched': True
                        }
                        st.session_state.boq_items.append(new_item)
                        update_boq_content_with_current_items()
                        st.success(f"Added {add_qty}x {product['name']}!")
                        st.rerun()

# --- NEW: Excel Generation Functions ---
def _populate_boq_sheet(sheet, items, gst_rates, project_name, client_name):
    """Helper function to populate a single Excel sheet with BOQ data."""
    # Header
    sheet.merge_cells('A1:L2')
    header_cell = sheet['A1']
    header_cell.value = "AllWave AV Solutions - Commercial Proposal"
    header_cell.font = Font(size=20, bold=True, color="FFFFFF")
    header_cell.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
    header_cell.alignment = Alignment(horizontal='center', vertical='center')

    # Project Info
    project_info = [
        ("Project:", project_name),
        ("Client:", client_name),
        ("Location:", st.session_state.get('location_input', 'N/A')),
        ("Date:", datetime.now().strftime('%d-%b-%Y')),
        ("Architect/PMC:", st.session_state.get('architect_input', 'N/A')),
    ]
    row = 4
    for label, value in project_info:
        sheet[f'A{row}'] = label
        sheet[f'A{row}'].font = Font(bold=True)
        sheet.merge_cells(f'B{row}:C{row}')
        sheet[f'B{row}'] = value
        row += 1

    # Table Headers
    row = 10
    headers = [
        'Sr. No.', 'System', 'Brand', 'Model No.', 'Description', 'Qty.', 'UoM',
        'Unit Rate', 'Amount', 'GST %', 'GST Amount', 'Total Amount with GST'
    ]
    for col, header in enumerate(headers, 1):
        cell = sheet.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # Add Items
    row_num = row + 1
    s_no = 1
    total_hardware_amount = 0
    total_services_amount = 0
    
    # Separate hardware and services
    hardware_items = [item for item in items if 'service' not in item.get('system', '').lower()]
    service_items = [item for item in items if 'service' in item.get('system', '').lower()]

    for item in hardware_items:
        unit_price_inr = convert_currency(item['price'], 'INR')
        amount = unit_price_inr * item['quantity']
        gst_rate = item.get('gst_rate', gst_rates['Electronics'])
        gst_amount = amount * (gst_rate / 100)
        total_with_gst = amount + gst_amount
        total_hardware_amount += amount

        row_data = [
            s_no, item.get('system'), item.get('brand'), item.get('model_no'),
            item.get('description'), item.get('quantity'), item.get('uom', 'Nos'),
            unit_price_inr, amount, f"{gst_rate}%", gst_amount, total_with_gst
        ]
        sheet.append(row_data)
        s_no += 1

    # Subtotal for Hardware
    hardware_total_row = sheet.max_row + 1
    sheet.merge_cells(f'H{hardware_total_row}:I{hardware_total_row}')
    sheet[f'H{hardware_total_row}'] = "Hardware Cost"
    sheet[f'H{hardware_total_row}'].font = Font(bold=True)
    sheet[f'H{hardware_total_row}'].alignment = Alignment(horizontal='right')
    sheet[f'L{hardware_total_row}'] = total_hardware_amount
    sheet[f'L{hardware_total_row}'].font = Font(bold=True)
    sheet[f'L{hardware_total_row}'].number_format = '₹ #,##0'

    # Add Services based on percentage of hardware cost
    if service_items:
        sheet.append([]) # Blank row
        for item in service_items:
             # Calculate service cost as a percentage of hardware if price is 0
            if item['price'] == 0:
                percentage = 0.15 if 'install' in item['name'].lower() else \
                             0.05 if 'warrant' in item['name'].lower() else \
                             0.10 if 'manage' in item['name'].lower() else 0.10
                unit_price_inr = total_hardware_amount * percentage
            else:
                unit_price_inr = convert_currency(item['price'], 'INR')

            amount = unit_price_inr * item['quantity']
            gst_rate = gst_rates['Services']
            gst_amount = amount * (gst_rate / 100)
            total_with_gst = amount + gst_amount
            total_services_amount += amount

            row_data = [
                s_no, item.get('system'), item.get('brand'), item.get('model_no'),
                item.get('description'), item.get('quantity'), item.get('uom', 'Lot'),
                unit_price_inr, amount, f"{gst_rate}%", gst_amount, total_with_gst
            ]
            sheet.append(row_data)
            s_no += 1

    # Subtotal for Services
    services_total_row = sheet.max_row + 1
    sheet.merge_cells(f'H{services_total_row}:I{services_total_row}')
    sheet[f'H{services_total_row}'] = "Professional Services Cost"
    sheet[f'H{services_total_row}'].font = Font(bold=True)
    sheet[f'H{services_total_row}'].alignment = Alignment(horizontal='right')
    sheet[f'L{services_total_row}'] = total_services_amount
    sheet[f'L{services_total_row}'].font = Font(bold=True)
    sheet[f'L{services_total_row}'].number_format = '₹ #,##0'


    # Grand Total
    grand_total_row = sheet.max_row + 2
    grand_total = total_hardware_amount + total_services_amount # This is total before tax
    sheet.merge_cells(f'H{grand_total_row}:I{grand_total_row}')
    sheet[f'H{grand_total_row}'] = "Grand Total (Excluding GST)"
    sheet[f'H{grand_total_row}'].font = Font(size=14, bold=True)
    sheet[f'H{grand_total_row}'].alignment = Alignment(horizontal='right')
    sheet[f'L{grand_total_row}'] = grand_total
    sheet[f'L{grand_total_row}'].font = Font(size=14, bold=True, color="FFFFFF")
    sheet[f'L{grand_total_row}'].fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid")
    sheet[f'L{grand_total_row}'].number_format = '₹ #,##0'

    # Formatting
    column_widths = {'A': 8, 'B': 20, 'C': 20, 'D': 30, 'E': 50, 'F': 6, 'G': 8, 'H': 15, 'I': 15, 'J': 8, 'K': 15, 'L': 20}
    for col, width in column_widths.items():
        sheet.column_dimensions[col].width = width
        
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    for r in range(row + 1, sheet.max_row + 1):
        # Apply border and number formatting
        for c in range(1, 13):
            cell = sheet.cell(row=r, column=c)
            cell.border = thin_border
            if c >= 8: # Currency columns
                 cell.number_format = '₹ #,##0'

def generate_professional_excel(rooms_data=None):
    """Generate Excel file with Indian GST calculations and professional formatting."""
    
    if not rooms_data and ('boq_items' not in st.session_state or not st.session_state.boq_items):
        st.error("No BOQ items to export. Generate a BOQ first.")
        return None
    
    workbook = openpyxl.Workbook()
    
    project_name = st.session_state.get('project_name_input', 'AV Installation')
    client_name = st.session_state.get('client_name_input', 'Valued Client')
    gst_rates = st.session_state.get('gst_rates', {'Services': 18})

    if rooms_data:
        summary_sheet = workbook.active
        summary_sheet.title = "Project Summary"
        summary_data = []

        for room in rooms_data:
            if room.get('boq_items'):
                safe_room_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:30]
                room_sheet = workbook.create_sheet(title=safe_room_name)
                subtotal, gst, total = _populate_boq_sheet(room_sheet, room['boq_items'], gst_rates, f"{project_name} - {room['name']}", client_name)
                summary_data.append([room['name'], subtotal, gst, total])

        # Populate Summary Sheet
        summary_sheet.append(["Project Summary", "", "", ""])
        summary_sheet['A1'].font = Font(size=16, bold=True, color="002060")
        summary_sheet.append([]) # Blank row
        summary_sheet.append(["Room Name", "Subtotal (₹)", "Total GST (₹)", "Grand Total (₹)"])
        for col in ['A', 'B', 'C', 'D']:
            summary_sheet[f'{col}3'].font = Font(bold=True)

        project_grand_total = 0
        for row_data in summary_data:
            summary_sheet.append(row_data)
            project_grand_total += row_data[3]
        
        total_row = summary_sheet.max_row + 1
        summary_sheet[f'C{total_row}'] = "Project Grand Total (₹)"
        summary_sheet[f'D{total_row}'] = project_grand_total
        summary_sheet[f'D{total_row}'].number_format = '₹ #,##0.00'
        summary_sheet[f'C{total_row}'].font = Font(bold=True)
        summary_sheet[f'D{total_row}'].font = Font(bold=True)
    
    else: # Single room mode
        sheet = workbook.active
        sheet.title = "Professional BOQ"
        _populate_boq_sheet(sheet, st.session_state.boq_items, gst_rates, project_name, client_name)

    add_terms_conditions_sheet(workbook)
    
    excel_buffer = BytesIO()
    workbook.save(excel_buffer)
    excel_buffer.seek(0)
    
    return excel_buffer.getvalue()


def add_terms_conditions_sheet(workbook):
    """Add Terms & Conditions sheet with Indian business terms."""
    sheet = workbook.create_sheet("Terms & Conditions")
    terms_content = [
        ("TERMS AND CONDITIONS - AllWave AV Solutions", "header"), ("", "blank"),
        ("1. QUOTATION VALIDITY", "section"), ("• This quotation is valid for 30 days.", "point"),
        ("2. PAYMENT TERMS", "section"), ("• 50% Advance with Purchase Order", "point"), ("• 50% On delivery at site before installation", "point"),
        ("3. GST & TAXATION", "section"), ("• All amounts include GST as applicable.", "point"),
        ("4. DELIVERY & INSTALLATION", "section"), ("• Delivery: 4-6 weeks from order confirmation.", "point"),
        ("5. WARRANTY TERMS", "section"), ("• 3 years comprehensive onsite warranty.", "point"),
    ]
    for i, (content, style) in enumerate(terms_content, 1):
        cell = sheet[f'A{i}']
        cell.value = content
        if style == "header": cell.font = Font(size=16, bold=True, color="002060")
        elif style == "section": cell.font = Font(size=12, bold=True, color="002060")
    sheet.column_dimensions['A'].width = 100

# --- FIX: Added Missing 3D Visualization Helper Functions ---
def map_equipment_type(category, name, brand):
    """Maps a BOQ item to a standardized equipment type for 3D rendering."""
    cat_lower = str(category).lower()
    name_lower = str(name).lower()
    
    if 'display' in cat_lower or 'monitor' in name_lower or 'screen' in name_lower:
        return 'display'
    if 'camera' in cat_lower or 'rally' in name_lower or 'conferencing' in cat_lower:
        return 'camera'
    if 'speaker' in name_lower or 'soundbar' in name_lower:
        return 'audio_speaker'
    if 'microphone' in name_lower or 'mic' in name_lower:
        return 'audio_mic'
    if 'switch' in name_lower or 'router' in name_lower:
        return 'network_switch'
    if 'control' in cat_lower or 'processor' in name_lower:
        return 'control_processor'
    if 'mount' in cat_lower or 'bracket' in name_lower:
        return 'mount'
    if 'rack' in name_lower:
        return 'rack'
    if 'service' in cat_lower or 'installation' in name_lower or 'warranty' in name_lower:
        return 'service' # Special type to be skipped
    return 'generic_box' # Fallback for unknown items

def get_equipment_specs(equipment_type, name):
    """Returns estimated [width, height, depth] in feet for 3D models."""
    name_lower = str(name).lower()
    
    # Check for specific size in name (e.g., 65")
    # FIX: Corrected regex to ensure the digit group is always captured.
    size_match = re.search(r'(\d{2,3})[ -]*(?:inch|\")', name_lower)
    if size_match and equipment_type == 'display':
        try:
            size_inches = int(size_match.group(1))
            # Aspect ratio 16:9 conversion to feet
            width = size_inches * 0.871 / 12 
            height = size_inches * 0.490 / 12
            return [width, height, 0.3] # W, H, D in feet
        except (ValueError, IndexError):
            # If conversion fails for any reason, fall through to default size
            pass

    # Default sizes in feet
    specs = {
        'display': [4.0, 2.3, 0.3],
        'camera': [0.8, 0.5, 0.6],
        'audio_speaker': [0.8, 1.2, 0.8],
        'audio_mic': [0.5, 0.1, 0.5],
        'network_switch': [1.5, 0.15, 0.8],
        'control_processor': [1.5, 0.3, 1.0],
        'mount': [2.0, 1.5, 0.2],
        'rack': [2.0, 6.0, 2.5],
        'generic_box': [1.0, 1.0, 1.0]
    }
    return specs.get(equipment_type, [1, 1, 1])

def get_placement_constraints(equipment_type):
    """Defines where an object can be placed."""
    constraints = {
        'display': ['wall'],
        'camera': ['wall', 'ceiling', 'table'],
        'audio_speaker': ['wall', 'ceiling', 'floor'],
        'audio_mic': ['table', 'ceiling'],
        'network_switch': ['floor', 'rack'],
        'control_processor': ['floor', 'rack'],
        'mount': ['wall'],
        'rack': ['floor']
    }
    return constraints.get(equipment_type, ['floor', 'table'])

def get_power_requirements(equipment_type):
    """Estimates power draw in Watts."""
    power = {
        'display': 250,
        'camera': 15,
        'audio_speaker': 80,
        'network_switch': 100,
        'control_processor': 50
    }
    return power.get(equipment_type, 20)

def get_weight_estimate(equipment_type, specs):
    """Estimates weight in lbs based on volume."""
    volume = specs[0] * specs[1] * specs[2]
    density = { # lbs per cubic foot
        'display': 20,
        'camera': 15,
        'audio_speaker': 25,
        'network_switch': 30,
        'control_processor': 25,
        'rack': 10
    }
    return volume * density.get(equipment_type, 10)

# --- 3D Visualization ---
def create_3d_visualization():
    """Create production-ready 3D room planner with drag-drop and space analytics."""
    st.subheader("Interactive 3D Room Planner & Space Analytics")

    equipment_data = st.session_state.get('boq_items', [])

    if not equipment_data:
        st.info("No BOQ items to visualize. Generate a BOQ first or add items manually.")
        return

    js_equipment = []
    for item in equipment_data:
        equipment_type = map_equipment_type(item.get('category', ''), item.get('name', ''), item.get('brand', ''))
        # Skip service items properly
        if equipment_type == 'service':
            continue

        specs = get_equipment_specs(equipment_type, item.get('name', ''))

        try:
            quantity = int(item.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        # Create individual instances for each quantity
        for i in range(quantity):
            js_equipment.append({
                'id': len(js_equipment) + 1,
                'type': equipment_type,
                'name': item.get('name', 'Unknown'),
                'brand': item.get('brand', 'Unknown'),
                'price': float(item.get('price', 0)),
                'instance': i + 1,
                'original_quantity': quantity,
                'specs': specs,
                'placement_constraints': get_placement_constraints(equipment_type),
                'power_requirements': get_power_requirements(equipment_type),
                'weight': get_weight_estimate(equipment_type, specs)
            })

    room_length = st.session_state.get('room_length_input', 24.0)
    room_width = st.session_state.get('room_width_input', 16.0)
    room_height = st.session_state.get('ceiling_height_input', 9.0)
    room_type_str = st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)')

    # All curly braces doubled for f-string escaping
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body {{
                margin: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #1a1a1a;
            }}
            #container {{
                width: 100%;
                height: 700px;
                position: relative;
                cursor: grab;
            }}
            #container:active {{
                cursor: grabbing;
            }}
            #analytics-panel {{
                position: absolute;
                top: 15px;
                right: 15px;
                color: #ffffff;
                background: linear-gradient(135deg, rgba(0, 30, 60, 0.95), rgba(0, 20, 40, 0.9));
                padding: 20px;
                border-radius: 15px;
                backdrop-filter: blur(15px);
                border: 2px solid rgba(64, 196, 255, 0.3);
                width: 350px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            #equipment-panel {{
                position: absolute;
                top: 15px;
                left: 15px;
                color: #ffffff;
                background: linear-gradient(135deg, rgba(30, 0, 60, 0.95), rgba(20, 0, 40, 0.9));
                padding: 20px;
                border-radius: 15px;
                backdrop-filter: blur(15px);
                border: 2px solid rgba(196, 64, 255, 0.3);
                width: 320px;
                max-height: 670px;
                overflow-y: auto;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            .space-metric {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 8px 0;
                padding: 10px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border-left: 4px solid #40C4FF;
            }}
            .space-value {{
                font-size: 16px;
                font-weight: bold;
                color: #40C4FF;
            }}
            .space-warning {{
                border-left-color: #FF6B35 !important;
            }}
            .space-warning .space-value {{
                color: #FF6B35;
            }}
            .equipment-item {{
                margin: 6px 0;
                padding: 12px;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.03));
                border-radius: 8px;
                border-left: 3px solid transparent;
                cursor: grab;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            .equipment-item:hover {{
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.08));
                transform: translateY(-2px);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            }}
            .equipment-item:active {{
                cursor: grabbing;
            }}
            .equipment-item.placed {{
                border-left-color: #4CAF50;
                opacity: 0.7;
            }}
            .equipment-item.dragging {{
                transform: scale(1.05);
                z-index: 1000;
            }}
            .equipment-name {{
                color: #FFD54F;
                font-weight: bold;
                font-size: 14px;
            }}
            .equipment-details {{
                color: #ccc;
                font-size: 12px;
                margin-top: 4px;
            }}
            .equipment-specs {{
                color: #aaa;
                font-size: 11px;
                margin-top: 6px;
            }}
            #suggestions-panel {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                background: linear-gradient(135deg, rgba(0, 60, 30, 0.95), rgba(0, 40, 20, 0.9));
                padding: 15px;
                border-radius: 12px;
                backdrop-filter: blur(10px);
                border: 2px solid rgba(76, 255, 76, 0.3);
                max-width: 300px;
                color: white;
                display: none;
            }}
            .suggestion-item {{
                padding: 8px;
                margin: 4px 0;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .suggestion-item:hover {{
                background: rgba(76, 255, 76, 0.2);
            }}
            #controls {{
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: linear-gradient(135deg, rgba(0, 0, 0, 0.9), rgba(20, 20, 20, 0.8));
                padding: 15px;
                border-radius: 25px;
                display: flex;
                gap: 12px;
                backdrop-filter: blur(15px);
                border: 2px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            }}
            .control-btn {{
                background: linear-gradient(135deg, rgba(64, 196, 255, 0.8), rgba(32, 164, 223, 0.6));
                border: 2px solid rgba(64, 196, 255, 0.4);
                color: white;
                padding: 10px 18px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 13px;
                font-weight: 500;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
            }}
            .control-btn:hover {{
                background: linear-gradient(135deg, rgba(64, 196, 255, 1), rgba(32, 164, 223, 0.8));
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(64, 196, 255, 0.4);
            }}
            .control-btn.active {{
                background: linear-gradient(135deg, #40C4FF, #0288D1);
                border-color: #0288D1;
                box-shadow: 0 4px 15px rgba(64, 196, 255, 0.6);
            }}
            .mode-indicator {{
                position: absolute;
                top: 20px;
                right: 50%;
                transform: translateX(50%);
                background: rgba(0, 0, 0, 0.8);
                color: #40C4FF;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid rgba(64, 196, 255, 0.5);
            }}
            .drag-overlay {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(64, 196, 255, 0.1);
                border: 3px dashed #40C4FF;
                border-radius: 15px;
                display: none;
                pointer-events: none;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{
                    opacity: 0.3;
                }}
                50% {{
                    opacity: 0.7;
                }}
            }}
        </style>
    </head>
    <body>
        <div id="container">
            <div class="mode-indicator" id="modeIndicator">VIEW MODE</div>
            <div class="drag-overlay" id="dragOverlay"></div>
            
            <div id="analytics-panel">
                <h3 style="margin-top: 0; color: #40C4FF; font-size: 18px;">Space Analytics</h3>
                <div class="space-metric">
                    <span>Total Room Area</span>
                    <span class="space-value" id="totalArea">{room_length * room_width:.0f} sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Usable Floor Space</span>
                    <span class="space-value" id="usableArea">0 sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Equipment Footprint</span>
                    <span class="space-value" id="equipmentFootprint">0 sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Wall Space Used</span>
                    <span class="space-value" id="wallSpaceUsed">0%</span>
                </div>
                <div class="space-metric">
                    <span>Remaining Floor Space</span>
                    <span class="space-value" id="remainingSpace">{room_length * room_width:.0f} sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Power Load</span>
                    <span class="space-value" id="powerLoad">0W</span>
                </div>
                <div class="space-metric">
                    <span>Cable Runs Required</span>
                    <span class="space-value" id="cableRuns">0</span>
                </div>
                
                <div id="spaceRecommendations" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2);">
                    <h4 style="color: #40C4FF; margin: 0 0 10px 0;">Recommendations</h4>
                    <div id="recommendationsList" style="font-size: 12px; line-height: 1.4;"></div>
                </div>
            </div>
            
            <div id="equipment-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: #C440FF; font-size: 18px;">Equipment Library</h3>
                    <button class="control-btn" onclick="togglePlacementMode()" id="placementToggle">
                        PLACE MODE
                    </button>
                </div>
                <div style="font-size: 12px; color: #ccc; margin-bottom: 15px;" id="placementInstructions">
                    Click "PLACE MODE" then drag items into the room
                </div>
                <div id="equipmentList"></div>
            </div>

            <div id="suggestions-panel">
                <h4 style="margin: 0 0 10px 0; color: #4CFF4C;">Suggested Additions</h4>
                <div id="suggestionsList"></div>
            </div>
            
            <div id="controls">
                <button class="control-btn active" onclick="setView('overview', true, this)">🏠 Overview</button>
                <button class="control-btn" onclick="setView('front', true, this)">📺 Front</button>
                <button class="control-btn" onclick="setView('side', true, this)">📐 Side</button>
                <button class="control-btn" onclick="setView('top', true, this)">📊 Top</button>
                <button class="control-btn" onclick="resetLayout()">🔄 Reset</button>
                <button class="control-btn" onclick="saveLayout()">💾 Save</button>
            </div>
        </div>
        
        <script>
            let scene, camera, renderer, raycaster, mouse, dragControls;
            let animationId, selectedObject = null, placementMode = false;
            let draggedEquipment = null, originalPosition = null;
            let roomBounds, spaceAnalytics;
            
            const toUnits = (feet) => feet * 0.3048;
            const toFeet = (units) => units / 0.3048;
            const avEquipment = {json.dumps(js_equipment)};
            const roomType = `{room_type_str}`;
            const allRoomSpecs = {json.dumps(ROOM_SPECS)};
            const roomDims = {{
                length: {room_length},
                width: {room_width},
                height: {room_height}
            }};

            // Enhanced space analytics system
            class SpaceAnalytics {{
                constructor() {{
                    this.placedEquipment = [];
                    this.roomBounds = {{
                        minX: -toUnits(roomDims.length / 2),
                        maxX: toUnits(roomDims.length / 2),
                        minZ: -toUnits(roomDims.width / 2),
                        maxZ: toUnits(roomDims.width / 2),
                        height: toUnits(roomDims.height)
                    }};
                    this.walls = this.calculateWalls();
                }}
                
                calculateWalls() {{
                    return {{
                        front: {{ start: {{ x: this.roomBounds.minX, z: this.roomBounds.maxZ }}, end: {{ x: this.roomBounds.maxX, z: this.roomBounds.maxZ }}, length: roomDims.length }},
                        back: {{ start: {{ x: this.roomBounds.minX, z: this.roomBounds.minZ }}, end: {{ x: this.roomBounds.maxX, z: this.roomBounds.minZ }}, length: roomDims.length }},
                        left: {{ start: {{ x: this.roomBounds.minX, z: this.roomBounds.minZ }}, end: {{ x: this.roomBounds.minX, z: this.roomBounds.maxZ }}, length: roomDims.width }},
                        right: {{ start: {{ x: this.roomBounds.maxX, z: this.roomBounds.minZ }}, end: {{ x: this.roomBounds.maxX, z: this.roomBounds.maxZ }}, length: roomDims.width }}
                    }};
                }}
                
                addPlacedEquipment(obj, equipment) {{
                    const bbox = new THREE.Box3().setFromObject(obj);
                    const size = bbox.getSize(new THREE.Vector3());
                    const position = obj.position.clone();
                    
                    this.placedEquipment.push({{
                        object: obj,
                        equipment: equipment,
                        footprint: toFeet(size.x) * toFeet(size.z),
                        position: position,
                        bounds: bbox,
                        powerDraw: equipment.power_requirements || 0,
                        isWallMounted: this.isWallMounted(obj, equipment)
                    }});
                    
                    this.updateAnalytics();
                }}
                
                removePlacedEquipment(obj) {{
                    this.placedEquipment = this.placedEquipment.filter(item => item.object !== obj);
                    this.updateAnalytics();
                }}
                
                isWallMounted(obj, equipment) {{
                    const tolerance = toUnits(1); // 1 foot tolerance
                    const pos = obj.position;
                    
                    return (
                        Math.abs(pos.z - this.roomBounds.minZ) < tolerance || // Back wall
                        Math.abs(pos.z - this.roomBounds.maxZ) < tolerance || // Front wall
                        Math.abs(pos.x - this.roomBounds.minX) < tolerance || // Left wall
                        Math.abs(pos.x - this.roomBounds.maxX) < tolerance    // Right wall
                    );
                }}
                
                getWallSpaceUsed() {{
                    let totalUsed = 0;
                    const wallMountedItems = this.placedEquipment.filter(item => item.isWallMounted);
                    
                    Object.values(this.walls).forEach(wall => {{
                        let wallUsed = 0;
                        wallMountedItems.forEach(item => {{
                            const bbox = item.bounds;
                            const size = bbox.getSize(new THREE.Vector3());
                            
                            // Simplified wall space calculation
                            if (this.isOnWall(item.position, wall)) {{
                                wallUsed += toFeet(Math.max(size.x, size.z));
                            }}
                        }});
                        totalUsed += Math.min(wallUsed / wall.length, 1);
                    }});
                    
                    return (totalUsed / 4) * 100; // Average across 4 walls
                }}
                
                isOnWall(position, wall) {{
                    const tolerance = toUnits(1);
                    
                    if (wall === this.walls.front || wall === this.walls.back) {{
                        return Math.abs(position.z - wall.start.z) < tolerance;
                    }} else {{
                        return Math.abs(position.x - wall.start.x) < tolerance;
                    }}
                }}
                
                // [FIX 5 APPLIED HERE]
                updateAnalytics() {{
                    const totalRoomArea = roomDims.length * roomDims.width;
                    const furnitureArea = this.calculateFurnitureFootprint();
                    const equipmentFootprint = this.placedEquipment.reduce((sum, item) => sum + item.footprint, 0);
                    const usableArea = totalRoomArea - furnitureArea;
                    const remainingSpace = Math.max(0, usableArea - equipmentFootprint);
                    const wallSpaceUsed = this.getWallSpaceUsed();
                    const totalPowerDraw = this.placedEquipment.reduce((sum, item) => sum + item.powerDraw, 0);
                    const cableRuns = this.calculateCableRuns();
                    
                    // Update UI with proper formatting
                    document.getElementById('usableArea').textContent = `${{usableArea.toFixed(0)}} sq ft`;
                    document.getElementById('equipmentFootprint').textContent = `${{equipmentFootprint.toFixed(1)}} sq ft`;
                    document.getElementById('remainingSpace').textContent = `${{remainingSpace.toFixed(1)}} sq ft`;
                    document.getElementById('wallSpaceUsed').textContent = `${{wallSpaceUsed.toFixed(1)}}%`;
                    document.getElementById('powerLoad').textContent = `${{totalPowerDraw}}W`;
                    document.getElementById('cableRuns').textContent = cableRuns;
                    
                    // Visual warnings
                    const remainingMetric = document.getElementById('remainingSpace').parentElement;
                    if (remainingSpace < totalRoomArea * 0.2) {{
                        remainingMetric.classList.add('space-warning');
                    }} else {{
                        remainingMetric.classList.remove('space-warning');
                    }}
                    
                    this.generateRecommendations(remainingSpace, wallSpaceUsed);
                }}
                
                calculateFurnitureFootprint() {{
                    // Estimate furniture footprint based on room type
                    const roomSpec = allRoomSpecs[roomType] || {{ table_size: [10, 4], chair_count: 8 }};
                    const tableArea = roomSpec.table_size[0] * roomSpec.table_size[1];
                    const chairArea = roomSpec.chair_count * 4; // 2ft x 2ft per chair
                    return tableArea + chairArea;
                }}
                
                calculateCableRuns() {{
                    // Estimate cable runs needed
                    const displays = this.placedEquipment.filter(item => item.equipment.type === 'display');
                    const audioDevices = this.placedEquipment.filter(item => item.equipment.type.includes('audio'));
                    const networkDevices = this.placedEquipment.filter(item => item.equipment.type.includes('network'));
                    
                    return displays.length * 3 + audioDevices.length * 2 + networkDevices.length;
                }}
                
                generateRecommendations(remainingSpace, wallSpaceUsed) {{
                    const recommendations = [];
                    
                    if (remainingSpace < 50) {{
                        recommendations.push("⚠️ Very limited floor space remaining");
                    }}
                    if (wallSpaceUsed > 80) {{
                        recommendations.push("⚠️ Wall space nearly fully utilized");
                    }}
                    if (remainingSpace > 200) {{
                        recommendations.push("✅ Ample space for additional equipment");
                    }}
                    
                    const totalPowerDraw = this.placedEquipment.reduce((sum, item) => sum + item.powerDraw, 0);
                    if (totalPowerDraw > 1500) {{
                        recommendations.push("⚡ May require dedicated 20A circuit");
                    }}
                    
                    document.getElementById('recommendationsList').innerHTML =
                        recommendations.length > 0 ? recommendations.join('<br>') : "All metrics within normal ranges";
                }}
                
                generateSuggestions(remainingSpace) {{
                    const suggestions = [];
                    const suggestionsPanel = document.getElementById('suggestions-panel');
                    
                    if (remainingSpace > 100) {{
                        suggestions.push({{ name: "Additional Display", space: 25, reason: "Dual display setup" }});
                        suggestions.push({{ name: "Wireless Presenter", space: 5, reason: "Enhanced mobility" }});
                    }}
                    if (remainingSpace > 50) {{
                        suggestions.push({{ name: "Document Camera", space: 8, reason: "Content sharing" }});
                        suggestions.push({{ name: "Room Control Panel", space: 3, reason: "User interface" }});
                    }}
                    
                    if (suggestions.length > 0) {{
                        const suggestionsList = document.getElementById('suggestionsList');
                        suggestionsList.innerHTML = suggestions.map(s =>
                            `<div class="suggestion-item">
                                <strong>${{s.name}}</strong><br>
                                <small>${{s.reason}} • ${{s.space}} sq ft</small>
                            </div>`
                        ).join('');
                        suggestionsPanel.style.display = 'block';
                    }} else {{
                        suggestionsPanel.style.display = 'none';
                    }}
                }}
            }}

            function init() {{
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x2a3a4a);
                scene.fog = new THREE.Fog(0x2a3a4a, toUnits(30), toUnits(120));
                
                const container = document.getElementById('container');
                camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
                setView('overview', false);
                
                renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer.shadowMap.enabled = true;
                renderer.shadowMap.type = THREE.PCFSoftShadowMap;
                renderer.outputEncoding = THREE.sRGBEncoding;
                renderer.toneMapping = THREE.ACESFilmicToneMapping;
                renderer.toneMappingExposure = 1.2;
                container.appendChild(renderer.domElement);
                
                raycaster = new THREE.Raycaster();
                mouse = new THREE.Vector2();
                
                spaceAnalytics = new SpaceAnalytics();
                
                createRealisticRoom();
                createEnhancedLighting();
                createRoomFurniture();
                createPlaceableEquipmentObjects();
                setupEnhancedControls();
                setupKeyboardControls();
                updateEquipmentList();
                animate();
            }}

            function createRealisticRoom() {{
                const floorMaterial = new THREE.MeshStandardMaterial({{
                    color: 0x8B7355,
                    roughness: 0.8,
                    metalness: 0.1,
                    normalScale: new THREE.Vector2(0.5, 0.5)
                }});
                
                const wallMaterial = new THREE.MeshStandardMaterial({{
                    color: 0xF5F5F5,
                    roughness: 0.9,
                    metalness: 0.05
                }});
                
                const ceilingMaterial = new THREE.MeshStandardMaterial({{
                    color: 0xFFFFFF,
                    roughness: 0.95
                }});
                
                const wallHeight = toUnits(roomDims.height);

                const floor = new THREE.Mesh(
                    new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)),
                    floorMaterial
                );
                floor.rotation.x = -Math.PI / 2;
                floor.receiveShadow = true;
                floor.name = 'floor';
                scene.add(floor);

                const walls = [
                    {{ pos: [0, wallHeight / 2, -toUnits(roomDims.width / 2)], rot: [0, 0, 0], size: [toUnits(roomDims.length), wallHeight] }}, // Back
                    {{ pos: [-toUnits(roomDims.length / 2), wallHeight / 2, 0], rot: [0, Math.PI / 2, 0], size: [toUnits(roomDims.width), wallHeight] }}, // Left
                    {{ pos: [toUnits(roomDims.length / 2), wallHeight / 2, 0], rot: [0, -Math.PI / 2, 0], size: [toUnits(roomDims.width), wallHeight] }}, // Right
                    {{ pos: [0, wallHeight / 2, toUnits(roomDims.width / 2)], rot: [0, Math.PI, 0], size: [toUnits(roomDims.length), wallHeight] }} // Front
                ];

                walls.forEach((wallConfig, index) => {{
                    const wall = new THREE.Mesh(
                        new THREE.PlaneGeometry(wallConfig.size[0], wallConfig.size[1]),
                        wallMaterial
                    );
                    wall.position.set(...wallConfig.pos);
                    wall.rotation.set(...wallConfig.rot);
                    wall.receiveShadow = true;
                    wall.name = `wall_${{index}}`;
                    scene.add(wall);
                }});

                const ceiling = new THREE.Mesh(
                    new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)),
                    ceilingMaterial
                );
                ceiling.position.y = wallHeight;
                ceiling.rotation.x = Math.PI / 2;
                ceiling.receiveShadow = true;
                ceiling.name = 'ceiling';
                scene.add(ceiling);
            }}

            function createEnhancedLighting() {{
                const ambientLight = new THREE.HemisphereLight(0x87CEEB, 0x8B7355, 0.6);
                scene.add(ambientLight);

                const dirLight = new THREE.DirectionalLight(0xFFF8DC, 0.8);
                dirLight.position.set(toUnits(10), toUnits(15), toUnits(8));
                dirLight.castShadow = true;
                dirLight.shadow.mapSize.width = 2048;
                dirLight.shadow.mapSize.height = 2048;
                dirLight.shadow.camera.near = 0.5;
                dirLight.shadow.camera.far = 50;
                dirLight.shadow.camera.left = dirLight.shadow.camera.bottom = -25;
                dirLight.shadow.camera.right = dirLight.shadow.camera.top = 25;
                scene.add(dirLight);

                const roomLights = [
                    new THREE.Vector3(-toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), -toUnits(roomDims.width / 4)),
                    new THREE.Vector3(toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), -toUnits(roomDims.width / 4)),
                    new THREE.Vector3(-toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), toUnits(roomDims.width / 4)),
                    new THREE.Vector3(toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), toUnits(roomDims.width / 4))
                ];

                roomLights.forEach(pos => {{
                    const light = new THREE.PointLight(0xFFFFE0, 0.4, toUnits(20));
                    light.position.copy(pos);
                    light.castShadow = true;
                    light.shadow.mapSize.width = 512;
                    light.shadow.mapSize.height = 512;
                    scene.add(light);
                    
                    const fixture = new THREE.Mesh(
                        new THREE.CylinderGeometry(toUnits(0.5), toUnits(0.5), toUnits(0.2)),
                        new THREE.MeshStandardMaterial({{ color: 0x888888 }})
                    );
                    fixture.position.copy(pos);
                    scene.add(fixture);
                }});
            }}
            
            function createRoomFurniture() {{
                const roomSpec = allRoomSpecs[roomType] || {{ chair_count: 8 }};
                
                let tableConfig = getTableConfig(roomType, roomSpec);
                
                const tableMaterial = new THREE.MeshStandardMaterial({{
                    color: 0x8B4513,
                    roughness: 0.3,
                    metalness: 0.1
                }});
                
                const table = new THREE.Mesh(
                    new THREE.BoxGeometry(
                        toUnits(tableConfig.length),
                        toUnits(tableConfig.height),
                        toUnits(tableConfig.width)
                    ),
                    tableMaterial
                );
                table.position.set(tableConfig.x, toUnits(tableConfig.height / 2), tableConfig.z);
                table.castShadow = true;
                table.receiveShadow = true;
                table.name = 'conference_table';
                scene.add(table);

                addRoomSpecificFurniture(roomType, roomSpec);
                
                const chairPositions = calculateChairPositions(roomSpec, tableConfig);
                createChairs(chairPositions);
            }}

            // UPDATED JAVASCRIPT FUNCTION
            function getTableConfig(roomType, roomSpec) {{
                const tableSize = roomSpec.table_size || [10, 4];
                const configs = {{
                    'Small Huddle Room (2-3 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Medium Huddle Room (4-6 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Standard Conference Room (6-8 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Large Conference Room (8-12 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Executive Boardroom (10-16 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Training Room (15-25 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, 
                        x: -toUnits(roomDims.length/2 - tableSize[0]/2 - 3), z: -toUnits(roomDims.width/4)
                    }},
                    'Large Training/Presentation Room (25-40 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, 
                        x: -toUnits(roomDims.length/2 - tableSize[0]/2 - 4), z: -toUnits(roomDims.width/3)
                    }},
                    'Multipurpose Event Room (40+ People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, 
                        x: -toUnits(roomDims.length/2 - tableSize[0]/2 - 5), z: -toUnits(roomDims.width/3)
                    }},
                    'Video Production Studio': {{
                        length: tableSize[0], width: tableSize[1], height: 3, 
                        x: toUnits(roomDims.length/2 - tableSize[0]/2 - 2), z: 0
                    }},
                    'Telepresence Suite': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: toUnits(2)
                    }}
                }};
                
                return configs[roomType] || {{ length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0 }};
            }}
            
            // UPDATED JAVASCRIPT FUNCTION
            function addRoomSpecificFurniture(roomType, roomSpec) {{
                const furnitureMaterial = new THREE.MeshStandardMaterial({{ color: 0x666666 }});
                const woodMaterial = new THREE.MeshStandardMaterial({{ color: 0x8B4513 }});
                
                if (roomType.includes('Training')) {{
                    // Add student desks for training rooms with better spacing
                    const numRows = roomType.includes('Large') ? 6 : 4;
                    const seatsPerRow = Math.ceil(roomSpec.chair_count / numRows);
                    
                    for (let row = 0; row < numRows; row++) {{
                        for (let seat = 0; seat < seatsPerRow && (row * seatsPerRow + seat) < roomSpec.chair_count - 1; seat++) {{
                            const desk = new THREE.Mesh(
                                new THREE.BoxGeometry(toUnits(4), toUnits(2.5), toUnits(2)),
                                woodMaterial
                            );
                            desk.position.set(
                                toUnits(-roomDims.length/2 + 8 + seat * 6),
                                toUnits(1.25),
                                toUnits(roomDims.width/2 - 6 - row * 5)
                            );
                            desk.castShadow = true;
                            desk.receiveShadow = true;
                            scene.add(desk);
                        }}
                    }}
                }} else if (roomType.includes('Production Studio')) {{
                    // Add control console and equipment racks
                    const console = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(12), toUnits(3), toUnits(3)),
                        furnitureMaterial
                    );
                    console.position.set(toUnits(roomDims.length/2 - 8), toUnits(1.5), 0);
                    console.castShadow = true;
                    console.receiveShadow = true;
                    scene.add(console);
                    
                    // Equipment racks
                    for (let i = 0; i < 3; i++) {{
                        const rack = new THREE.Mesh(
                            new THREE.BoxGeometry(toUnits(2), toUnits(6), toUnits(2)),
                            new THREE.MeshStandardMaterial({{ color: 0x333333 }})
                        );
                        rack.position.set(
                            toUnits(roomDims.length/2 - 6),
                            toUnits(3),
                            toUnits(-4 + i * 4)
                        );
                        rack.castShadow = true;
                        rack.receiveShadow = true;
                        scene.add(rack);
                    }}
                }} else if (roomType.includes('Multipurpose Event')) {{
                    // Add stage area
                    const stage = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(16), toUnits(1), toUnits(8)),
                        woodMaterial
                    );
                    stage.position.set(
                        toUnits(-roomDims.length/2 + 8),
                        toUnits(0.5),
                        0
                    );
                    stage.castShadow = true;
                    stage.receiveShadow = true;
                    scene.add(stage);
                }} else if (roomType.includes('Executive Boardroom')) {{
                    // Add credenza
                    const credenza = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(8), toUnits(3), toUnits(2)),
                        woodMaterial
                    );
                    credenza.position.set(
                        0,
                        toUnits(1.5),
                        toUnits(-roomDims.width/2 + 1)
                    );
                    credenza.castShadow = true;
                    credenza.receiveShadow = true;
                    scene.add(credenza);
                }}
            }}

            function createChairs(chairPositions) {{
                 const chairMaterial = new THREE.MeshStandardMaterial({{
                    color: 0x333333,
                    roughness: 0.7
                }});
                
                chairPositions.forEach((pos, index) => {{
                    const chair = new THREE.Group();
                    
                    const seat = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(1.5), toUnits(0.3), toUnits(1.5)),
                        chairMaterial
                    );
                    seat.position.y = toUnits(1.5);
                    chair.add(seat);
                    
                    const backrest = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(1.5), toUnits(2), toUnits(0.2)),
                        chairMaterial
                    );
                    backrest.position.set(0, toUnits(2.5), toUnits(-0.65));
                    chair.add(backrest);
                    
                    chair.position.set(toUnits(pos.x), 0, toUnits(pos.z));
                    chair.rotation.y = pos.rotationY || 0;
                    chair.castShadow = true;
                    chair.receiveShadow = true;
                    chair.name = `chair_${{index}}`;
                    scene.add(chair);
                }});
            }}

            // UPDATED JAVASCRIPT FUNCTION
            function calculateChairPositions(roomSpec, tableConfig) {{
                const positions = [];
                const tableLength = tableConfig.length;
                const tableWidth = tableConfig.width;
                
                if (roomSpec.chair_arrangement === 'theater' || roomSpec.chair_arrangement === 'classroom') {{
                    // Theater/classroom seating for training rooms
                    const numRows = Math.ceil(roomSpec.chair_count / 8);
                    const chairsPerRow = Math.min(8, roomSpec.chair_count);
                    
                    for (let row = 0; row < numRows; row++) {{
                        for (let seat = 0; seat < chairsPerRow && positions.length < roomSpec.chair_count; seat++) {{
                            positions.push({{
                                x: -chairsPerRow * 2 + seat * 4,
                                z: tableWidth/2 + 4 + row * 4,
                                rotationY: 0
                            }});
                        }}
                    }}
                }} else {{
                    // Traditional conference table seating
                    const chairSpacing = Math.max(3, Math.min(4.5, tableLength / (roomSpec.chair_count / 2 + 1)));
                    const chairsPerLongSide = Math.floor((tableLength - 2) / chairSpacing);
                    
                    // Long sides of table
                    for (let i = 0; i < chairsPerLongSide && positions.length < roomSpec.chair_count; i++) {{
                        const x = -tableLength / 2 + (i + 1) * (tableLength / (chairsPerLongSide + 1));
                        
                        positions.push({{ x: x, z: tableWidth / 2 + 2, rotationY: Math.PI }});
                        if (positions.length < roomSpec.chair_count) {{
                            positions.push({{ x: x, z: -tableWidth / 2 - 2, rotationY: 0 }});
                        }}
                    }}
                    
                    // Short sides of table
                    if (positions.length < roomSpec.chair_count && tableWidth > 6) {{
                        positions.push({{ x: tableLength / 2 + 2, z: 0, rotationY: -Math.PI / 2 }});
                        if (positions.length < roomSpec.chair_count) {{
                            positions.push({{ x: -tableLength / 2 - 2, z: 0, rotationY: Math.PI / 2 }});
                        }}
                    }}
                }}
                
                return positions.slice(0, roomSpec.chair_count);
            }}

            function createPlaceableEquipmentObjects() {{
                avEquipment.forEach(equipment => {{
                    const obj = createEquipmentMesh(equipment);
                    obj.userData = {{ equipment: equipment, placed: false, draggable: true }};
                    obj.visible = false;
                    scene.add(obj);
                }});
            }}
            
            function createEquipmentMesh(equipment) {{
                const group = new THREE.Group();
                const specs = equipment.specs;
                const type = equipment.type;
                let geometry, material, mesh;

                // Create realistic materials
                const materials = {{
                    metal: new THREE.MeshStandardMaterial({{
                        color: 0x606060,
                        roughness: 0.2,
                        metalness: 0.9,
                        envMapIntensity: 1.0
                    }}),
                    plastic: new THREE.MeshStandardMaterial({{
                        color: 0x2a2a2a,
                        roughness: 0.7,
                        metalness: 0.1
                    }}),
                    screen: new THREE.MeshStandardMaterial({{
                        color: 0x000000,
                        emissive: 0x001122,
                        emissiveIntensity: 0.2,
                        roughness: 0.1,
                        metalness: 0.1
                    }}),
                    speaker: new THREE.MeshStandardMaterial({{
                        color: 0x1a1a1a,
                        roughness: 0.8,
                        metalness: 0.2
                    }})
                }};

                switch (type) {{
                    case 'display':
                        const displayWidth = toUnits(specs[0]);
                        const displayHeight = toUnits(specs[1]);
                        const displayDepth = toUnits(specs[2]);

                        // Main display body with rounded edges
                        geometry = new THREE.BoxGeometry(displayWidth, displayHeight, displayDepth);
                        mesh = new THREE.Mesh(geometry, materials.metal);

                        // Screen with realistic appearance
                        const screen = new THREE.Mesh(
                            new THREE.PlaneGeometry(displayWidth * 0.92, displayHeight * 0.92),
                            materials.screen
                        );
                        screen.position.z = displayDepth / 2 + 0.005;
                        group.add(screen);

                        // Add brand logo area
                        const logo = new THREE.Mesh(
                            new THREE.PlaneGeometry(displayWidth * 0.15, displayHeight * 0.05),
                            new THREE.MeshStandardMaterial({{ color: 0x666666 }})
                        );
                        logo.position.set(0, -displayHeight * 0.45, displayDepth / 2 + 0.01);
                        group.add(logo);

                        // Power LED
                        const powerLED = new THREE.Mesh(
                            new THREE.SphereGeometry(toUnits(0.02)),
                            new THREE.MeshStandardMaterial({{ 
                                color: 0x00ff00, 
                                emissive: 0x003300, 
                                emissiveIntensity: 0.5 
                            }})
                        );
                        powerLED.position.set(displayWidth * 0.4, -displayHeight * 0.45, displayDepth / 2 + 0.01);
                        group.add(powerLED);
                        break;

                    case 'audio_speaker':
                        geometry = new THREE.BoxGeometry(toUnits(specs[0]), toUnits(specs[1]), toUnits(specs[2]));
                        mesh = new THREE.Mesh(geometry, materials.speaker);

                        // Multiple drivers with different sizes
                        const driverSizes = [0.4, 0.25, 0.15];
                        const driverPositions = [-0.3, 0, 0.3];
                        
                        driverSizes.forEach((size, i) => {{
                            const driver = new THREE.Mesh(
                                new THREE.CylinderGeometry(toUnits(specs[0] * size), toUnits(specs[0] * size), toUnits(0.02), 16),
                                new THREE.MeshStandardMaterial({{ color: 0x333333, roughness: 0.9 }})
                            );
                            driver.rotation.x = Math.PI / 2;
                            driver.position.set(0, toUnits(specs[1] * driverPositions[i]), toUnits(specs[2] / 2 + 0.01));
                            group.add(driver);

                            // Driver cone
                            const cone = new THREE.Mesh(
                                new THREE.ConeGeometry(toUnits(specs[0] * size * 0.6), toUnits(0.05), 12),
                                new THREE.MeshStandardMaterial({{ color: 0x444444 }})
                            );
                            cone.rotation.x = Math.PI;
                            cone.position.set(0, toUnits(specs[1] * driverPositions[i]), toUnits(specs[2] / 2 + 0.03));
                            group.add(cone);
                        }});

                        // Grille mesh
                        const grille = new THREE.Mesh(
                            new THREE.PlaneGeometry(toUnits(specs[0] * 0.9), toUnits(specs[1] * 0.9)),
                            new THREE.MeshStandardMaterial({{ 
                                color: 0x222222, 
                                transparent: true, 
                                opacity: 0.3,
                                wireframe: true 
                            }})
                        );
                        grille.position.z = toUnits(specs[2] / 2 + 0.04);
                        group.add(grille);
                        break;

                    case 'camera':
                        geometry = new THREE.BoxGeometry(toUnits(specs[0]), toUnits(specs[1]), toUnits(specs[2]));
                        mesh = new THREE.Mesh(geometry, materials.plastic);

                        // Main lens assembly
                        const lensAssembly = new THREE.Group();
                        
                        // Outer lens ring
                        const outerRing = new THREE.Mesh(
                            new THREE.CylinderGeometry(toUnits(0.3), toUnits(0.35), toUnits(0.15), 20),
                            materials.metal
                        );
                        outerRing.rotation.x = Math.PI / 2;
                        lensAssembly.add(outerRing);

                        // Lens glass
                        const lensGlass = new THREE.Mesh(
                            new THREE.CylinderGeometry(toUnits(0.25), toUnits(0.25), toUnits(0.02), 20),
                            new THREE.MeshStandardMaterial({{ 
                                color: 0x001122, 
                                roughness: 0.05, 
                                metalness: 0.9,
                                transparent: true,
                                opacity: 0.8
                            }})
                        );
                        lensGlass.rotation.x = Math.PI / 2;
                        lensGlass.position.z = toUnits(0.05);
                        lensAssembly.add(lensGlass);

                        lensAssembly.position.z = toUnits(specs[2] / 2 + 0.1);
                        group.add(lensAssembly);

                        // Status LEDs
                        const ledColors = [0x00ff00, 0xff0000, 0x0000ff];
                        ledColors.forEach((color, i) => {{
                            const led = new THREE.Mesh(
                                new THREE.SphereGeometry(toUnits(0.02)),
                                new THREE.MeshStandardMaterial({{ 
                                    color: color, 
                                    emissive: color, 
                                    emissiveIntensity: 0.3 
                                }})
                            );
                            led.position.set(
                                toUnits(specs[0] * 0.3 - i * 0.15), 
                                toUnits(specs[1] * 0.4), 
                                toUnits(specs[2] / 2 + 0.01)
                            );
                            group.add(led);
                        }});
                        break;

                    case 'network_switch':
                        geometry = new THREE.BoxGeometry(toUnits(specs[0]), toUnits(specs[1]), toUnits(specs[2]));
                        mesh = new THREE.Mesh(geometry, materials.metal);

                        // Ventilation grilles
                        for (let i = 0; i < 4; i++) {{
                            const vent = new THREE.Mesh(
                                new THREE.PlaneGeometry(toUnits(0.8), toUnits(0.05)),
                                new THREE.MeshStandardMaterial({{ color: 0x222222 }})
                            );
                            vent.position.set(0, toUnits(specs[1] / 2 - 0.02), toUnits(-specs[2] / 2 + i * 0.3));
                            vent.rotation.x = -Math.PI / 2;
                            group.add(vent);
                        }}

                        // Network ports with more detail
                        const portRows = 2;
                        const portsPerRow = 12;
                        for (let row = 0; row < portRows; row++) {{
                            for (let port = 0; port < portsPerRow; port++) {{
                                const portGeometry = new THREE.BoxGeometry(toUnits(0.06), toUnits(0.03), toUnits(0.08));
                                const portMesh = new THREE.Mesh(portGeometry, new THREE.MeshStandardMaterial({{ color: 0x111111 }}));
                                
                                portMesh.position.set(
                                    toUnits(-specs[0] / 2 + 0.1 + port * (specs[0] - 0.2) / portsPerRow),
                                    toUnits(-specs[1] / 2 + 0.04 + row * 0.05),
                                    toUnits(specs[2] / 2 + 0.04)
                                );
                                group.add(portMesh);

                                // Port activity LED
                                if (Math.random() > 0.3) {{ // 70% chance of activity
                                    const activityLED = new THREE.Mesh(
                                        new THREE.SphereGeometry(toUnits(0.005)),
                                        new THREE.MeshStandardMaterial({{ 
                                            color: Math.random() > 0.5 ? 0x00ff00 : 0xff8800,
                                            emissive: Math.random() > 0.5 ? 0x002200 : 0x221100,
                                            emissiveIntensity: 0.5
                                        }})
                                    );
                                    activityLED.position.copy(portMesh.position);
                                    activityLED.position.z += toUnits(0.05);
                                    activityLED.position.y += toUnits(0.02);
                                    group.add(activityLED);
                                }}
                            }}
                        }}
                        break;

                    default:
                        // Generic equipment with better detail
                        geometry = new THREE.BoxGeometry(toUnits(specs[0] || 2), toUnits(specs[1] || 1), toUnits(specs[2] || 1));
                        mesh = new THREE.Mesh(geometry, materials.plastic);

                        // Add some generic details
                        const genericDetails = [
                            {{ pos: [0.3, 0.3, 0.5], color: 0x0066ff }},
                            {{ pos: [-0.3, 0.3, 0.5], color: 0xff6600 }},
                            {{ pos: [0, -0.3, 0.5], color: 0x00ff66 }}
                        ];

                        genericDetails.forEach(detail => {{
                            const indicator = new THREE.Mesh(
                                new THREE.SphereGeometry(toUnits(0.03)),
                                new THREE.MeshStandardMaterial({{ 
                                    color: detail.color,
                                    emissive: detail.color,
                                    emissiveIntensity: 0.2
                                }})
                            );
                            indicator.position.set(
                                toUnits((specs[0] || 2) * detail.pos[0]), 
                                toUnits((specs[1] || 1) * detail.pos[1]), 
                                toUnits((specs[2] || 1) * detail.pos[2])
                            );
                            group.add(indicator);
                        }});
                }}

                if (mesh) {{
                    mesh.castShadow = true;
                    mesh.receiveShadow = true;
                    group.add(mesh);
                }}

                // Enhanced selection highlight
                const highlightGeometry = new THREE.BoxGeometry(
                    toUnits(specs[0] + 0.3), 
                    toUnits(specs[1] + 0.3), 
                    toUnits(specs[2] + 0.3)
                );
                const highlightMaterial = new THREE.MeshBasicMaterial({{
                    color: 0x40C4FF,
                    transparent: true,
                    opacity: 0,
                    wireframe: true,
                    linewidth: 2
                }});
                const highlight = new THREE.Mesh(highlightGeometry, highlightMaterial);
                highlight.name = 'highlight';
                group.add(highlight);

                group.name = `equipment_${{equipment.id}}`;
                return group;
            }}
            
            function onContextMenu(event) {{
                event.preventDefault();

                const rect = event.target.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);

                const equipmentIntersect = intersects.find(intersect =>
                    intersect.object.parent && intersect.object.parent.name.startsWith('equipment_') &&
                    intersect.object.parent.userData.placed
                );

                if (equipmentIntersect) {{
                    const equipmentObj = equipmentIntersect.object.parent;
                    const equipment = equipmentObj.userData.equipment;

                    // Simple context actions
                    if (confirm(`Remove ${{equipment.name}} from layout?`)) {{
                        equipmentObj.visible = false;
                        equipmentObj.userData.placed = false;
                        spaceAnalytics.removePlacedEquipment(equipmentObj);
                        updateEquipmentList();
                    }}
                }}
            }}

            function setupEnhancedControls() {{
                const container = document.getElementById('container');
                
                let isMouseDown = false;
                let previousMousePosition = {{ x: 0, y: 0 }};
                
                container.addEventListener('mousedown', (event) => {{
                    if (event.button === 0 && !placementMode) {{ // Left click and not in placement mode
                        isMouseDown = true;
                        previousMousePosition = {{ x: event.clientX, y: event.clientY }};
                        container.style.cursor = 'grabbing';
                    }}
                }});
                
                container.addEventListener('mousemove', (event) => {{
                    if (isMouseDown && !placementMode) {{
                        const deltaMove = {{
                            x: event.clientX - previousMousePosition.x,
                            y: event.clientY - previousMousePosition.y
                        }};
                        
                        const spherical = new THREE.Spherical();
                        spherical.setFromVector3(camera.position);
                        
                        spherical.theta -= deltaMove.x * 0.01;
                        spherical.phi += deltaMove.y * 0.01;
                        spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi));
                        
                        camera.position.setFromSpherical(spherical);
                        camera.lookAt(0, toUnits(3), 0);
                        
                        previousMousePosition = {{ x: event.clientX, y: event.clientY }};
                    }} else {{
                        const rect = event.target.getBoundingClientRect();
                        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                        
                        if (placementMode && (draggedEquipment || selectedObject)) {{
                            updateDraggedEquipmentPosition();
                        }}
                    }}
                }});
                
                container.addEventListener('mouseup', (event) => {{
                    if (event.button === 0) {{
                        if (isMouseDown && !placementMode) {{
                            isMouseDown = false;
                            container.style.cursor = 'grab';
                        }}
                    }}
                    if (placementMode) {{
                         if (selectedObject) {{
                             selectedObject.userData.placed = true;
                             draggedEquipment = null;
                             spaceAnalytics.addPlacedEquipment(selectedObject, selectedObject.userData.equipment)
                             highlightEquipment(selectedObject, false);
                             selectedObject = null;
                             document.getElementById('modeIndicator').textContent = 'PLACE MODE';
                             updateEquipmentList();
                         }}
                    }}
                }});
                
                container.addEventListener('mousedown', onMouseDown);
                container.addEventListener('contextmenu', onContextMenu);
                container.addEventListener('dblclick', onDoubleClick);
                container.addEventListener('wheel', onMouseWheel);
                container.addEventListener('dragover', onDragOver);
                container.addEventListener('drop', onDrop);
            }}

            function onMouseDown(event) {{
                if (!placementMode) return;

                const rect = event.target.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);

                const equipmentIntersect = intersects.find(intersect =>
                    intersect.object.parent && intersect.object.parent.name.startsWith('equipment_') &&
                    intersect.object.parent.userData.placed
                );

                if (equipmentIntersect) {{
                    const equipmentObj = equipmentIntersect.object.parent;
                    selectedObject = equipmentObj;
                    equipmentObj.userData.placed = false;
                    spaceAnalytics.removePlacedEquipment(equipmentObj);
                    draggedEquipment = equipmentObj.userData.equipment;
                    highlightEquipment(equipmentObj, true);
                    document.getElementById('modeIndicator').textContent = `MOVING: ${{draggedEquipment.name}}`;
                    return;
                }}

                const validIntersect = intersects.find(intersect => 
                    intersect.object.name === 'floor' ||
                    intersect.object.name.startsWith('wall_') ||
                    intersect.object.name === 'ceiling'
                );
                
                if (validIntersect && draggedEquipment) {{
                    placeDraggedEquipment(validIntersect.point);
                }}
            }}
            
            function onDoubleClick(event) {{
                const rect = event.target.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                
                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);
                
                const equipmentIntersect = intersects.find(intersect => 
                    intersect.object.parent && intersect.object.parent.name.startsWith('equipment_')
                );
                
                if (equipmentIntersect) {{
                    const equipmentObj = equipmentIntersect.object.parent;
                    focusOnEquipment(equipmentObj);
                }}
            }}

            function focusOnEquipment(equipmentObj) {{
                const bbox = new THREE.Box3().setFromObject(equipmentObj);
                const center = bbox.getCenter(new THREE.Vector3());
                const size = bbox.getSize(new THREE.Vector3());
                
                const maxDim = Math.max(size.x, size.y, size.z);
                const distance = maxDim * 4;
                
                const targetPosition = new THREE.Vector3(
                    center.x + distance * 0.7,
                    center.y + distance * 0.5,
                    center.z + distance * 0.7
                );
                
                const startPosition = camera.position.clone();
                const startTime = Date.now();
                const duration = 1500;
                
                function animateToEquipment() {{
                    const elapsed = Date.now() - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    
                    camera.position.lerpVectors(startPosition, targetPosition, eased);
                    camera.lookAt(center);
                    
                    if (progress < 1) {{
                        requestAnimationFrame(animateToEquipment);
                    }}
                }}
                
                animateToEquipment();
            }}

            function onMouseWheel(event) {{
                event.preventDefault();
                const zoomSpeed = 0.1;
                const zoomFactor = 1 + (event.deltaY > 0 ? zoomSpeed : -zoomSpeed);
                const distanceToTarget = camera.position.length();

                if (distanceToTarget * zoomFactor > toUnits(5) && distanceToTarget * zoomFactor < toUnits(100)) {{
                    camera.position.multiplyScalar(zoomFactor);
                }}
            }}
            
            function onDragOver(event) {{
                event.preventDefault();
                event.dataTransfer.dropEffect = "move";
                
                if (placementMode) {{
                    document.getElementById('dragOverlay').style.display = 'block';
                }}
            }}

            function onDrop(event) {{
                event.preventDefault();
                document.getElementById('dragOverlay').style.display = 'none';
                
                if (!placementMode) {{
                    alert('Please enable PLACE MODE first');
                    return;
                }}
                
                const equipmentId = event.dataTransfer.getData('text/plain');
                const equipment = avEquipment.find(eq => eq.id.toString() === equipmentId);
                
                if (equipment) {{
                    const rect = event.target.getBoundingClientRect();
                    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                    
                    raycaster.setFromCamera(mouse, camera);
                    const intersects = raycaster.intersectObjects(scene.children, true);
                    const floorIntersect = intersects.find(intersect => intersect.object.name === 'floor' || intersect.object.name.startsWith('wall'));
                    
                    if (floorIntersect) {{
                        startDragging(equipment);
                        placeDraggedEquipment(floorIntersect.point);
                    }}
                }}
            }}

            function updateEquipmentList() {{
                const listElement = document.getElementById('equipmentList');
                listElement.innerHTML = avEquipment.map(equipment => {{
                    const placed = scene.getObjectByName(`equipment_${{equipment.id}}`)?.userData.placed || false;
                    return `
                        <div class="equipment-item ${{placed ? 'placed' : ''}}" 
                                draggable="true" 
                                onclick="selectEquipment(${{equipment.id}})"
                                ondragstart="startDragFromPanel(event, ${{equipment.id}})">
                            <div class="equipment-name">${{equipment.name}}</div>
                            <div class="equipment-details">
                                ${{equipment.brand}} • $${{equipment.price.toLocaleString()}}
                                ${{equipment.instance > 1 ? ` (${{equipment.instance}}/${{equipment.original_quantity}})` : ''}}
                            </div>
                            <div class="equipment-specs">
                                ${{equipment.specs[0].toFixed(1)}}W × ${{equipment.specs[1].toFixed(1)}}H × ${{equipment.specs[2].toFixed(1)}}D ft
                                ${{equipment.power_requirements ? ` • ${{equipment.power_requirements}}W` : ''}}
                            </div>
                        </div>
                    `;
                }}).join('');
            }}

            function startDragFromPanel(event, equipmentId) {{
                event.dataTransfer.setData('text/plain', equipmentId.toString());
            }}

            function selectEquipment(equipmentId) {{
                if (!placementMode) return;
                
                const equipment = avEquipment.find(eq => eq.id === equipmentId);
                if (equipment) {{
                    startDragging(equipment);
                }}
            }}

            function startDragging(equipment) {{
                const obj = scene.getObjectByName(`equipment_${{equipment.id}}`);
                if (obj && obj.userData.placed) return;
                
                draggedEquipment = equipment;
                document.getElementById('modeIndicator').textContent = `PLACING: ${{equipment.name}}`;
            }}
            
            function highlightEquipment(equipmentObj, highlightStatus = true) {{
                const highlightMesh = equipmentObj.getObjectByName('highlight');
                if (highlightMesh) {{
                    if (highlightStatus) {{
                        highlightMesh.material.opacity = 0.3;
                    }} else {{
                        highlightMesh.material.opacity = 0;
                    }}
                }}
            }}
            
            function updateDraggedEquipmentPosition() {{
                const equipmentToMove = selectedObject ? selectedObject.userData.equipment : draggedEquipment;
                if (!equipmentToMove) return;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);
                
                const validIntersect = intersects.find(intersect => 
                    intersect.object.name === 'floor' ||
                    intersect.object.name.startsWith('wall_') || 
                    intersect.object.name === 'ceiling'
                );

                if (validIntersect) {{
                    const obj = scene.getObjectByName(`equipment_${{equipmentToMove.id}}`);
                    if (obj) {{
                        const intersectPoint = validIntersect.point.clone();
                        const normal = validIntersect.face.normal.clone();
                        
                        const offset = normal.multiplyScalar(toUnits(Math.max(...equipmentToMove.specs) / 2 + 0.1));
                        obj.position.copy(intersectPoint.add(offset));
                        
                        const bounds = spaceAnalytics.roomBounds;
                        obj.position.x = Math.max(bounds.minX + toUnits(0.5), Math.min(bounds.maxX - toUnits(0.5), obj.position.x));
                        obj.position.z = Math.max(bounds.minZ + toUnits(0.5), Math.min(bounds.maxZ - toUnits(0.5), obj.position.z));
                        obj.position.y = Math.max(toUnits(0.1), Math.min(bounds.height - toUnits(0.1), obj.position.y));
                        
                        if (!selectedObject) highlightEquipment(obj, true);
                        
                        obj.visible = true;
                    }}
                }}
            }}

            function placeDraggedEquipment(position) {{
                if (!draggedEquipment) return;
                
                const obj = scene.getObjectByName(`equipment_${{draggedEquipment.id}}`);
                if (obj) {{
                    obj.visible = true;
                    obj.userData.placed = true;
                    
                    spaceAnalytics.addPlacedEquipment(obj, draggedEquipment);
                    updateEquipmentList();
                }}
                
                draggedEquipment = null;
                document.getElementById('modeIndicator').textContent = 'PLACE MODE';
            }}

            function togglePlacementMode() {{
                placementMode = !placementMode;
                const button = document.getElementById('placementToggle');
                const instructions = document.getElementById('placementInstructions');
                const indicator = document.getElementById('modeIndicator');
                
                if (placementMode) {{
                    button.textContent = 'VIEW MODE';
                    button.classList.add('active');
                    instructions.textContent = 'Drag items from library into the room';
                    indicator.textContent = 'PLACE MODE';
                }} else {{
                    button.textContent = 'PLACE MODE';
                    button.classList.remove('active');
                    instructions.textContent = 'Click "PLACE MODE" then drag items into the room';
                    indicator.textContent = 'VIEW MODE';
                    draggedEquipment = null;
                }}
            }}

            // UPDATED JAVASCRIPT FUNCTION
            function setView(viewType, animate = true, buttonElement = null) {{
                if (buttonElement) {{
                    document.querySelectorAll('.control-btn').forEach(btn => btn.classList.remove('active'));
                    buttonElement.classList.add('active');
                }}
                
                const roomSize = Math.max(roomDims.length, roomDims.width);
                const baseDist = roomSize > 30 ? roomSize * 0.8 : roomSize * 0.6;
                
                let newPosition;
                
                switch (viewType) {{
                    case 'overview':
                        newPosition = new THREE.Vector3(
                            toUnits(baseDist * 0.7), 
                            toUnits(roomDims.height + baseDist * 0.4), 
                            toUnits(baseDist * 0.7)
                        );
                        break;
                    case 'front':
                        newPosition = new THREE.Vector3(0, toUnits(roomDims.height * 0.6), toUnits(roomDims.width / 2 + baseDist * 0.5));
                        break;
                    case 'side':
                        newPosition = new THREE.Vector3(toUnits(roomDims.length / 2 + baseDist * 0.5), toUnits(roomDims.height * 0.6), 0);
                        break;
                    case 'top':
                        newPosition = new THREE.Vector3(0, toUnits(roomDims.height + baseDist * 0.8), 0.1);
                        break;
                }}
                
                if (animate) {{
                    const startPosition = camera.position.clone();
                    const startTime = Date.now();
                    const duration = 1000;
                    
                    function animateCamera() {{
                        const elapsed = Date.now() - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const eased = 1 - Math.pow(1 - progress, 3);
                        
                        camera.position.lerpVectors(startPosition, newPosition, eased);
                        camera.lookAt(0, toUnits(roomDims.height * 0.3), 0);
                        
                        if (progress < 1) {{
                            requestAnimationFrame(animateCamera);
                        }}
                    }}
                    animateCamera();
                }} else {{
                    camera.position.copy(newPosition);
                    camera.lookAt(0, toUnits(roomDims.height * 0.3), 0);
                }}
            }}

            function resetLayout() {{
                scene.children.forEach(child => {{
                    if (child.name.startsWith('equipment_')) {{
                        child.visible = false;
                        child.userData.placed = false;
                    }}
                }});
                
                spaceAnalytics.placedEquipment = [];
                spaceAnalytics.updateAnalytics();
                updateEquipmentList();
            }}

            function saveLayout() {{
                const placedItems = [];
                scene.children.forEach(child => {{
                    if (child.name.startsWith('equipment_') && child.userData.placed) {{
                        placedItems.push({{
                            id: child.userData.equipment.id,
                            position: {{
                                x: child.position.x,
                                y: child.position.y,
                                z: child.position.z
                            }},
                            rotation: {{
                                x: child.rotation.x,
                                y: child.rotation.y,
                                z: child.rotation.z
                            }}
                        }});
                    }}
                }});
                
                const layoutData = {{
                    room: roomDims,
                    equipment: placedItems,
                    analytics: {{
                        footprint: spaceAnalytics.placedEquipment.reduce((sum, item) => sum + item.footprint, 0),
                        powerLoad: spaceAnalytics.placedEquipment.reduce((sum, item) => sum + item.powerDraw, 0)
                    }}
                }};
                
                console.log('Layout saved:', layoutData);
                alert('Layout saved successfully! (Check console)');
            }}
            
            function setupKeyboardControls() {{
                document.addEventListener('keydown', (event) => {{
                    switch(event.key.toLowerCase()) {{
                        case 'r':
                            resetLayout();
                            break;
                        case 'p':
                            togglePlacementMode();
                            break;
                        case '1':
                            setView('overview', true, document.querySelector('#controls button:nth-child(1)'));
                            break;
                        case '2':
                            setView('front', true, document.querySelector('#controls button:nth-child(2)'));
                            break;
                        case '3':
                            setView('side', true, document.querySelector('#controls button:nth-child(3)'));
                            break;
                        case '4':
                            setView('top', true, document.querySelector('#controls button:nth-child(4)'));
                            break;
                        case 'escape':
                            if (draggedEquipment) {{
                                draggedEquipment = null;
                                document.getElementById('modeIndicator').textContent = 'PLACE MODE';
                            }}
                            if (selectedObject) {{
                                highlightEquipment(selectedObject, false);
                                selectedObject = null;
                            }}
                            break;
                    }}
                }});
            }}

            function animate() {{
                animationId = requestAnimationFrame(animate);
                renderer.render(scene, camera);
            }}

            window.addEventListener('load', init);
            window.addEventListener('resize', () => {{
                const container = document.getElementById('container');
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            }});
        </script>
    </body>
    </html>
    """

    components.html(html_content, height=700)
# --- Main Application ---
def main():
    # --- Enhanced Session State Initialization ---
    if 'boq_items' not in st.session_state:
        st.session_state.boq_items = []
    if 'boq_content' not in st.session_state:
        st.session_state.boq_content = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    if 'project_rooms' not in st.session_state:
        st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state:
        st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state:
        st.session_state.gst_rates = {'Electronics': 18, 'Services': 18, 'Default': 18}

    # Load data
    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=False):
            for issue in data_issues:
                st.warning(issue)
    
    if product_df is None:
        return
    
    model = setup_gemini()
    if not model:
        return
    
    project_id, quote_valid_days = create_project_header()
    
    # --- Sidebar ---
# --- Sidebar ---
with st.sidebar:
    st.header("Project Configuration")
    st.text_input("Client Name", key="client_name_input", value="Valued Client")
    st.text_input("Project Name", key="project_name_input", value="AV Integration Project")
    # --- NEW ADDITIONS ---
    st.text_input("Location", key="location_input", value="Mumbai")
    st.text_input("Architect/PMC", key="architect_input", value="N/A")
        
        st.markdown("---")
        st.subheader("🇮🇳 Indian Business Settings")
        
        currency = st.selectbox("Currency Display", ["INR", "USD"], index=0, key="currency_select")
        st.session_state['currency'] = currency
        
        electronics_gst = st.number_input("Hardware GST (%)", value=18, min_value=0, max_value=28, key="electronics_gst")
        services_gst = st.number_input("Services GST (%)", value=18, min_value=0, max_value=28, key="services_gst")
        st.session_state.gst_rates['Electronics'] = electronics_gst
        st.session_state.gst_rates['Services'] = services_gst
        
        st.markdown("---")
        st.subheader("Room Design Settings")
        
        room_type = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        
        room_spec = ROOM_SPECS[room_type]
        st.markdown("#### Room Guidelines")
        st.caption(f"Area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")

    # --- Main Content Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Multi-Room Project", "Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])
    
    with tab1:
        create_multi_room_interface()
        
    with tab2:
        room_area, ceiling_height = create_room_calculator()
        
    with tab3:
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified'", height=100, key="features_text_area")
        technical_reqs = create_advanced_requirements()

    with tab4:
        st.subheader("Professional BOQ Generation")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 Generate BOQ with Images & Justifications", type="primary", use_container_width=True):
                with st.spinner("Generating professional BOQ with justifications..."):
                    room_area = st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                    boq_content, boq_items = generate_boq_with_justifications(
                        model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area
                    )
                    
                    if boq_items:
                        st.session_state.boq_content = boq_content
                        st.session_state.boq_items = boq_items
                        
                        # Save to current room if multi-room is used
                        if st.session_state.project_rooms:
                            st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = boq_items
                        
                        validator = BOQValidator(ROOM_SPECS, product_df)
                        issues, warnings = validator.validate_technical_requirements(boq_items, room_type, room_area)
                        avixa_warnings = validate_against_avixa(model, guidelines, boq_items)
                        warnings.extend(avixa_warnings)
                        st.session_state.validation_results = {"issues": issues, "warnings": warnings}
                        st.success(f"✅ Generated enhanced BOQ with {len(boq_items)} items!")
                        st.rerun()
                    else:
                        st.error("Failed to generate BOQ. Please try again.")

        with col2:
            if 'boq_items' in st.session_state and st.session_state.boq_items:
                excel_data = generate_professional_excel()
                room_name = "CurrentRoom"
                if st.session_state.project_rooms:
                    room_name = st.session_state.project_rooms[st.session_state.current_room_index]['name']

                filename = f"{project_name or 'Project'}_{room_name}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                
                st.download_button(
                    label="📊 Download Current Room BOQ",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary"
                )

        if st.session_state.boq_content or st.session_state.boq_items:
            st.markdown("---")
            display_boq_results(st.session_state.boq_content, st.session_state.validation_results, project_id, quote_valid_days, product_df)

    with tab5:
        create_3d_visualization()

# Run the application
if __name__ == "__main__":
    main()
