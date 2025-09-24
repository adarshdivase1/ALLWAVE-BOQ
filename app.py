import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import json
import time
import streamlit.components.v1 as components

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
        return 83.0  # Approximate USD to INR rate - update this or use real API
    except:
        return 83.0  # Fallback rate

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

# --- Enhanced Data Loading with Validation ---
@st.cache_data
def load_and_validate_data():
    """Loads and validates the product catalog and guidelines."""
    try:
        df = pd.read_csv("master_product_catalog.csv")
        
        # Data quality validation
        validation_issues = []
        
        # Check for missing critical data
        if df['name'].isnull().sum() > 0:
            validation_issues.append(f"{df['name'].isnull().sum()} products missing names")
        
        # Check for zero/missing prices - make price handling more robust
        if 'price' in df.columns:
            # Convert price to numeric, handling non-numeric values
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
            zero_price_count = (df['price'] == 0.0).sum()
            if zero_price_count > 100:  # Allow some zero prices for accessories
                validation_issues.append(f"{zero_price_count} products have zero pricing")
        else:
            df['price'] = 0.0  # Add price column if missing
            validation_issues.append("Price column missing - using default values")
            
        # Brand validation
        if 'brand' not in df.columns:
            df['brand'] = 'Unknown'
            validation_issues.append("Brand column missing - using default values")
        elif df['brand'].isnull().sum() > 0:
            df['brand'] = df['brand'].fillna('Unknown')
            validation_issues.append(f"{df['brand'].isnull().sum()} products missing brand information")
        
        # Category validation - ensure we have essential categories
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
        
        # Add features column if missing (for search functionality)
        if 'features' not in df.columns:
            df['features'] = df['name']  # Use name as fallback for features
            validation_issues.append("Features column missing - using product names for search")
        else:
            df['features'] = df['features'].fillna('')
        
        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found. Using basic industry standards."
            validation_issues.append("AVIXA guidelines file missing")
        
        return df, guidelines, validation_issues
        
    except FileNotFoundError:
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
        "table_size": [4, 2.5],  # length, width in feet
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
        "area_sqft": (250, 400),
        "recommended_display_size": (65, 75),
        "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed ceiling mics with expansion",
        "camera_type": "PTZ with presenter tracking",
        "power_requirements": "20A dedicated circuit",
        "network_ports": 3,
        "typical_budget_range": (25000, 50000),
        "furniture_config": "large_conference",
        "table_size": [14, 5],
        "chair_count": 12,
        "chair_arrangement": "rectangular"
    },
    "Executive Boardroom (10-16 People)": {
        "area_sqft": (350, 600),
        "recommended_display_size": (75, 86),
        "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling and table mics",
        "camera_type": "Multiple cameras with auto-switching",
        "power_requirements": "30A dedicated circuit",
        "network_ports": 4,
        "typical_budget_range": (50000, 100000),
        "furniture_config": "executive_boardroom",
        "table_size": [16, 6],
        "chair_count": 16,
        "chair_arrangement": "oval"
    },
    "Training Room (15-25 People)": {
        "area_sqft": (300, 500),
        "recommended_display_size": (65, 86),
        "viewing_distance_ft": (10, 18),
        "audio_coverage": "Distributed with wireless mic support",
        "camera_type": "Fixed or PTZ for presenter tracking",
        "power_requirements": "20A circuit with UPS backup",
        "network_ports": 3,
        "typical_budget_range": (30000, 70000),
        "furniture_config": "training_room",
        "table_size": [8, 4],  # Instructor table
        "chair_count": 25,
        "chair_arrangement": "classroom"
    },
    "Large Training/Presentation Room (25-40 People)": {
        "area_sqft": (500, 800),
        "recommended_display_size": (86, 98),
        "viewing_distance_ft": (15, 25),
        "audio_coverage": "Full distributed system with handheld mics",
        "camera_type": "Multiple PTZ cameras",
        "power_requirements": "30A circuit with UPS backup",
        "network_ports": 4,
        "typical_budget_range": (60000, 120000),
        "furniture_config": "large_training",
        "table_size": [10, 4],  # Instructor table
        "chair_count": 40,
        "chair_arrangement": "theater"
    },
    "Multipurpose Event Room (40+ People)": {
        "area_sqft": (800, 1500),
        "recommended_display_size": (98, 110),
        "viewing_distance_ft": (20, 35),
        "audio_coverage": "Professional distributed PA system",
        "camera_type": "Professional multi-camera setup",
        "power_requirements": "Multiple 30A circuits",
        "network_ports": 6,
        "typical_budget_range": (100000, 250000),
        "furniture_config": "multipurpose_event",
        "table_size": [12, 6],  # Main presentation table
        "chair_count": 50,
        "chair_arrangement": "flexible"
    },
    "Video Production Studio": {
        "area_sqft": (200, 400),
        "recommended_display_size": (32, 55),
        "viewing_distance_ft": (6, 12),
        "audio_coverage": "Professional studio monitors",
        "camera_type": "Professional broadcast cameras",
        "power_requirements": "Multiple 20A circuits",
        "network_ports": 4,
        "typical_budget_range": (75000, 200000),
        "furniture_config": "production_studio",
        "table_size": [8, 4],  # Control desk
        "chair_count": 6,
        "chair_arrangement": "production"
    },
    "Telepresence Suite": {
        "area_sqft": (150, 300),
        "recommended_display_size": (65, 98),
        "viewing_distance_ft": (8, 14),
        "audio_coverage": "High-fidelity spatial audio",
        "camera_type": "Multiple high-res cameras with AI tracking",
        "power_requirements": "20A dedicated circuit",
        "network_ports": 3,
        "typical_budget_range": (80000, 180000),
        "furniture_config": "telepresence",
        "table_size": [12, 4],
        "chair_count": 8,
        "chair_arrangement": "telepresence"
    }
}


# --- Enhanced Gemini Configuration with Retry Logic ---
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

# --- BOQ Validation Engine ---
class BOQValidator:
    def __init__(self, room_specs, product_df):
        self.room_specs = room_specs
        self.product_df = product_df
    
    def validate_technical_requirements(self, boq_items, room_type, room_area=None):
        """Validate technical requirements and compatibility."""
        issues = []
        warnings = []
        
        # Check display sizing against room specifications
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            room_spec = self.room_specs.get(room_type, {})
            recommended_size = room_spec.get('recommended_display_size', (32, 98))
            
            for display in displays:
                # Extract size from product name (rough heuristic)
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
        room_spec = self.room_specs.get(room_type, {})
        if total_estimated_power > 1800:  # 15A circuit limit
            warnings.append("System may require dedicated 20A circuit")
        
        return issues, warnings

def validate_against_avixa(model, guidelines, boq_items):
    """Use AI to validate the BOQ against AVIXA standards."""
    if not guidelines or not boq_items:
        return []
    
    prompt = f"""
    You are an AVIXA Certified Technology Specialist (CTS). Review the following Bill of Quantities (BOQ) against the provided AVIXA standards.
    List any potential non-compliance issues, missing items (like accessibility components), or areas for improvement based on the standards.
    If there are no obvious issues, respond with 'No specific compliance issues found based on the provided data.'

    **AVIXA Standards Summary:**
    {guidelines}

    **Bill of Quantities to Review:**
    {json.dumps(boq_items, indent=2)}

    **Your Compliance Review:**
    """
    try:
        response = generate_with_retry(model, prompt)
        if response and response.text:
            # Avoid adding the "no issues found" message as a warning
            if "no specific compliance issues" in response.text.lower():
                return []
            # Return findings as a list of warnings
            return [line.strip() for line in response.text.split('\n') if line.strip()]
        return []
    except Exception as e:
        return [f"AVIXA compliance check failed: {str(e)}"]


# --- Enhanced UI Components ---
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
        room_length = st.number_input("Room Length (ft)", min_value=8.0, max_value=50.0, value=16.0, key="room_length_input")
        room_width = st.number_input("Room Width (ft)", min_value=6.0, max_value=30.0, value=12.0, key="room_width_input")
        ceiling_height = st.number_input("Ceiling Height (ft)", min_value=8.0, max_value=20.0, value=9.0, key="ceiling_height_input")
    
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
            st.success(f"Recommended: {recommended_type}")
        else:
            st.warning("Room size outside typical ranges")
    
    return room_area, ceiling_height

def create_advanced_requirements():
    """Advanced technical requirements input."""
    st.subheader("Technical Requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Infrastructure**")
        has_dedicated_circuit = st.checkbox("Dedicated 20A Circuit Available", key="dedicated_circuit_checkbox")
        network_capability = st.selectbox("Network Infrastructure", 
                                          ["Standard 1Gb", "10Gb Capable", "Fiber Available"], key="network_capability_select")
        cable_management = st.selectbox("Cable Management", 
                                        ["Exposed", "Conduit", "Raised Floor", "Drop Ceiling"], key="cable_management_select")
    
    with col2:
        st.write("**Compliance & Standards**")
        ada_compliance = st.checkbox("ADA Compliance Required", key="ada_compliance_checkbox")
        fire_code_compliance = st.checkbox("Fire Code Compliance Required", key="fire_code_compliance_checkbox")
        security_clearance = st.selectbox("Security Level", 
                                          ["Standard", "Restricted", "Classified"], key="security_clearance_select")
    
    return {
        "dedicated_circuit": has_dedicated_circuit,
        "network_capability": network_capability,
        "cable_management": cable_management,
        "ada_compliance": ada_compliance,
        "fire_code_compliance": fire_code_compliance,
        "security_clearance": security_clearance
    }

# --- Professional BOQ Document Generator ---
def generate_professional_boq_document(boq_data, project_info, validation_results):
    """Generate a professional BOQ document with proper formatting."""
    
    # Create document header
    doc_content = f"""
# Professional Bill of Quantities
**Project:** {project_info['project_id']}  
**Date:** {datetime.now().strftime('%B %d, %Y')}  
**Valid Until:** {(datetime.now() + timedelta(days=project_info['quote_valid_days'])).strftime('%B %d, %Y')}

---

## System Design Summary
{boq_data.get('design_summary', 'Professional AV system designed to meet project requirements.')}

## Technical Validation
"""
    
    if validation_results['issues']:
        doc_content += "**⚠️ Critical Issues:**\n"
        for issue in validation_results['issues']:
            doc_content += f"- {issue}\n"
        doc_content += "\n"
    
    if validation_results['warnings']:
        doc_content += "**⚡ Technical Recommendations & Compliance Notes:**\n"
        for warning in validation_results['warnings']:
            doc_content += f"- {warning}\n"
        doc_content += "\n"
    
    doc_content += "---\n\n"
    
    return doc_content

# --- Enhanced BOQ Item Extraction ---
def extract_boq_items_from_response(boq_content, product_df):
    """Extract and match BOQ items from AI response with product database."""
    items = []
    
    # Look for markdown table sections
    lines = boq_content.split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        
        # Detect table start (header row with |)
        if '|' in line and any(keyword in line.lower() for keyword in ['category', 'product', 'brand', 'item', 'description']):
            in_table = True
            continue
            
        # Skip separator lines (|---|---|)
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
            
        # Process table rows
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 3:
                # Extract information from table row
                category = parts[0].lower() if len(parts) > 0 else 'general'
                brand = parts[1] if len(parts) > 1 else 'Unknown'
                product_name = parts[2] if len(parts) > 2 else parts[1] if len(parts) > 1 else 'Unknown'
                
                # Try to extract quantity and price if present
                quantity = 1
                price = 0
                
                # Look for quantity in the row (usually a number)
                for part in parts:
                    if part.isdigit():
                        quantity = int(part)
                        break
                
                # Try to match with actual product in database
                matched_product = match_product_in_database(product_name, brand, product_df)
                if matched_product is not None:
                    price = float(matched_product.get('price', 0))
                    actual_brand = matched_product.get('brand', brand)
                    actual_category = matched_product.get('category', category)
                    actual_name = matched_product.get('name', product_name)
                else:
                    actual_brand = brand
                    actual_category = normalize_category(category, product_name)
                    actual_name = product_name
                
                items.append({
                    'category': actual_category,
                    'name': actual_name,
                    'brand': actual_brand,
                    'quantity': quantity,
                    'price': price,
                    'matched': matched_product is not None
                })
                
        # End table when we hit a line that doesn't start with |
        elif in_table and not line.startswith('|'):
            in_table = False
    
    return items

def match_product_in_database(product_name, brand, product_df):
    """Try to match a product name and brand with the database."""
    if product_df is None or len(product_df) == 0:
        return None
    
    # First try exact brand and partial name match
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
    
    # Map common category terms to standard categories
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

# --- NEW/UPDATED FUNCTIONS START HERE ---

def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        return
    
    # Generate updated BOQ content from current items
    boq_content = "## Updated Bill of Quantities\n\n"
    boq_content += "| Category | Brand | Product Name | Quantity | Unit Price (USD) | Total (USD) |\n"
    boq_content += "|----------|--------|--------------|----------|------------------|-------------|\n"
    
    total_cost = 0
    for item in st.session_state.boq_items:
        quantity = item.get('quantity', 1)
        price = item.get('price', 0)
        total = quantity * price
        total_cost += total
        
        boq_content += f"| {item.get('category', 'General')} | {item.get('brand', 'Unknown')} | {item.get('name', 'Unknown')} | {quantity} | ${price:,.2f} | ${total:,.2f} |\n"
    
    # Add totals
    boq_content += f"|||||**SUBTOTAL**|**${total_cost:,.2f}**|\n"
    boq_content += f"|||||Installation & Labor (15%)|**${total_cost * 0.15:,.2f}**|\n"
    boq_content += f"|||||System Warranty (5%)|**${total_cost * 0.05:,.2f}**|\n"
    boq_content += f"|||||Project Contingency (10%)|**${total_cost * 0.10:,.2f}**|\n"
    boq_content += f"|||||**TOTAL PROJECT COST**|**${total_cost * 1.30:,.2f}**|\n"
    
    # Update session state
    st.session_state.boq_content = boq_content

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days, product_df):
    """Display BOQ results with interactive editing capabilities."""
    
    # Show current BOQ item count at the top
    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    st.subheader(f"Generated Bill of Quantities ({item_count} items)")
    
    # Show validation results first
    if validation_results and validation_results.get('issues'):
        st.error("Critical Issues Found:")
        for issue in validation_results['issues']:
            st.write(f"- {issue}")
    
    if validation_results and validation_results.get('warnings'):
        st.warning("Technical Recommendations & Compliance Notes:")
        for warning in validation_results['warnings']:
            st.write(f"- {warning}")
    
    # Display BOQ content
    if boq_content:
        st.markdown(boq_content)
    else:
        st.info("No BOQ content generated yet. Use the interactive editor below to add items manually.")
    
    # Show current total if items exist
    if 'boq_items' in st.session_state and st.session_state.boq_items:
        # Get currency preference
        currency = st.session_state.get('currency', 'USD')
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        
        if currency == 'INR':
            display_total = convert_currency(total_cost, 'INR')
            st.metric("Current BOQ Total", format_currency(display_total * 1.30, 'INR'), help="Includes installation, warranty, and contingency")
        else:
            st.metric("Current BOQ Total", format_currency(total_cost * 1.30, 'USD'), help="Includes installation, warranty, and contingency")
    
    # Add interactive BOQ editor
    st.markdown("---")
    create_interactive_boq_editor(product_df)
    
    # Add download functionality
    col1, col2 = st.columns(2)
    
    with col1:
        if boq_content and 'boq_items' in st.session_state and st.session_state.boq_items:
            # Generate Markdown/PDF-ready content
            doc_content = generate_professional_boq_document(
                {'design_summary': boq_content.split('---')[0] if '---' in boq_content else boq_content[:200]}, 
                {'project_id': project_id, 'quote_valid_days': quote_valid_days},
                validation_results or {}
            )
            final_doc = doc_content + "\n" + boq_content
            
            st.download_button(
                label="Download BOQ (Markdown)",
                data=final_doc,
                file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )
        else:
            st.button("Download BOQ (Markdown)", disabled=True, help="Generate a BOQ first")
    
    with col2:
        if 'boq_items' in st.session_state and st.session_state.boq_items:
            # Generate CSV for further processing
            df_to_download = pd.DataFrame(st.session_state.boq_items)
            # Ensure price and quantity are numeric for calculation
            df_to_download['price'] = pd.to_numeric(df_to_download['price'], errors='coerce').fillna(0)
            df_to_download['quantity'] = pd.to_numeric(df_to_download['quantity'], errors='coerce').fillna(0)
            df_to_download['total'] = df_to_download['price'] * df_to_download['quantity']
            csv_data = df_to_download[['category', 'brand', 'name', 'quantity', 'price', 'total']].to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="Download BOQ (CSV)",
                data=csv_data,
                file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.button("Download BOQ (CSV)", disabled=True, help="Add items to BOQ first")

def create_interactive_boq_editor(product_df):
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    
    # Real-time status indicator
    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    col_status1, col_status2, col_status3 = st.columns(3)
    
    with col_status1:
        st.metric("Items in BOQ", item_count)
    
    with col_status2:
        if 'boq_items' in st.session_state and st.session_state.boq_items:
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            currency = st.session_state.get('currency', 'USD')
            if currency == 'INR':
                display_total = convert_currency(total_cost, 'INR')
                st.metric("Subtotal", format_currency(display_total, 'INR'))
            else:
                st.metric("Subtotal", format_currency(total_cost, 'USD'))
        else:
            st.metric("Subtotal", "₹0" if st.session_state.get('currency', 'USD') == 'INR' else "$0")
    
    with col_status3:
        if st.button("🔄 Refresh BOQ Display", help="Update the main BOQ display with current items"):
            update_boq_content_with_current_items()
            st.success("BOQ display updated!")
            st.rerun()
    
    # Get product data for editing
    if product_df is None:
        st.error("Cannot load product catalog for editing")
        return
    
    # Currency selection for editor
    currency = st.session_state.get('currency', 'USD')
    
    tabs = st.tabs(["Edit Current BOQ", "Add Products", "Product Search"])
    
    with tabs[0]:
        edit_current_boq(currency)
    
    with tabs[1]:
        add_products_interface(product_df, currency)
    
    with tabs[2]:
        product_search_interface(product_df, currency)

def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ."""
    st.write("**Add Products to BOQ:**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Category filter
        categories = ['All'] + sorted(list(product_df['category'].unique())) if 'category' in product_df.columns else ['All']
        selected_category = st.selectbox("Filter by Category", categories, key="add_category_filter")
        
        # Filter products
        if selected_category != 'All':
            filtered_df = product_df[product_df['category'] == selected_category]
        else:
            filtered_df = product_df
        
        # Product selection
        product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
        if product_options:
            selected_product_str = st.selectbox("Select Product", product_options, key="add_product_select")
            
            # Find selected product
            selected_product = None
            for _, row in filtered_df.iterrows():
                if f"{row['brand']} - {row['name']}" == selected_product_str:
                    selected_product = row
                    break
        else:
            st.warning("No products found in selected category")
            return
    
    with col2:
        if 'selected_product' in locals() and selected_product is not None:
            quantity = st.number_input("Quantity", min_value=1, value=1, key="add_product_qty")
            
            # Display price in selected currency
            base_price = float(selected_product.get('price', 0))
            if currency == 'INR' and base_price > 0:
                display_price = convert_currency(base_price, 'INR')
                st.metric("Unit Price", format_currency(display_price, 'INR'))
                total = display_price * quantity
                st.metric("Total", format_currency(total, 'INR'))
            else:
                st.metric("Unit Price", format_currency(base_price, 'USD'))
                total = base_price * quantity
                st.metric("Total", format_currency(total, 'USD'))
            
            if st.button("Add to BOQ", type="primary"):
                # Add to BOQ items
                new_item = {
                    'category': selected_product.get('category', 'General'),
                    'name': selected_product.get('name', ''),
                    'brand': selected_product.get('brand', ''),
                    'quantity': quantity,
                    'price': base_price,  # Always store in USD
                    'matched': True
                }
                st.session_state.boq_items.append(new_item)
                
                # Force update the BOQ content to reflect new items
                update_boq_content_with_current_items()
                
                st.success(f"Added {quantity}x {selected_product['name']} to BOQ!")
                st.rerun()

def product_search_interface(product_df, currency):
    """Advanced product search interface."""
    st.write("**Search Product Catalog:**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input("Search products...", placeholder="Enter product name, brand, or features", key="search_term_input")
        
        if search_term:
            # Search across multiple columns
            search_cols = ['name', 'brand']
            if 'features' in product_df.columns:
                search_cols.append('features')
            
            mask = product_df[search_cols].apply(
                lambda x: x.astype(str).str.contains(search_term, case=False, na=False)
            ).any(axis=1)
            
            search_results = product_df[mask]
            
            st.write(f"Found {len(search_results)} products:")
            
            # Display search results
            for i, product in search_results.head(10).iterrows():  # Limit to first 10 results
                with st.expander(f"{product.get('brand', 'Unknown')} - {product.get('name', 'Unknown')[:60]}..."):
                    col_a, col_b, col_c = st.columns([2, 1, 1])
                    
                    with col_a:
                        st.write(f"**Category:** {product.get('category', 'N/A')}")
                        st.write(f"**Brand:** {product.get('brand', 'N/A')}")
                        if 'features' in product and pd.notna(product['features']):
                            st.write(f"**Features:** {str(product['features'])[:100]}...")
                    
                    with col_b:
                        price = float(product.get('price', 0))
                        if currency == 'INR' and price > 0:
                            display_price = convert_currency(price, 'INR')
                            st.metric("Price", format_currency(display_price, 'INR'))
                        else:
                            st.metric("Price", format_currency(price, 'USD'))
                    
                    with col_c:
                        # Use a unique key for each number input
                        add_qty = st.number_input(f"Qty", min_value=1, value=1, key=f"search_qty_{i}")
                        if st.button(f"Add", key=f"search_add_{i}"):
                            new_item = {
                                'category': product.get('category', 'General'),
                                'name': product.get('name', ''),
                                'brand': product.get('brand', ''),
                                'quantity': add_qty,
                                'price': price,
                                'matched': True
                            }
                            st.session_state.boq_items.append(new_item)
                            
                            # Force update the BOQ content to reflect new items
                            update_boq_content_with_current_items()
                            
                            st.success(f"Added {add_qty}x {product['name']} to BOQ!")
                            st.rerun()

# --- CORRECTED/ORIGINAL FUNCTIONS ---

def edit_current_boq(currency):
    """Interface for editing current BOQ items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ first or add products manually.")
        return
    
    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    
    # Create editable table
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        # SOLVED: Explicitly cast item name and category to string to prevent TypeError on slice
        category_str = str(item.get('category', 'General'))
        name_str = str(item.get('name', 'Unknown'))
        
        with st.expander(f"{category_str} - {name_str[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                # Ensure keys are unique using the index 'i'
                new_name = st.text_input(f"Product Name", value=item.get('name', ''), key=f"name_{i}")
                new_brand = st.text_input(f"Brand", value=item.get('brand', ''), key=f"brand_{i}")
            
            with col2:
                # Handle potential missing categories
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_category = item.get('category', 'General')
                if current_category not in category_list:
                    current_category = 'General'
                
                new_category = st.selectbox(
                    "Category", 
                    category_list,
                    index=category_list.index(current_category),
                    key=f"category_{i}"
                )
            
            with col3:
                # Ensure quantity is at least 1 and handle potential float/invalid values
                current_quantity = item.get('quantity', 1)
                try:
                    # Convert to int and ensure it's at least 1
                    safe_quantity = max(1, int(float(current_quantity))) if current_quantity else 1
                except (ValueError, TypeError):
                    safe_quantity = 1
                
                new_quantity = st.number_input(
                    "Quantity", 
                    min_value=1, 
                    value=safe_quantity, 
                    key=f"qty_{i}"
                )
                
                # Price input with currency conversion
                current_price = item.get('price', 0)
                try:
                    current_price = float(current_price) if current_price else 0
                except (ValueError, TypeError):
                    current_price = 0
                
                if currency == 'INR' and current_price > 0:
                    display_price = convert_currency(current_price, 'INR')
                else:
                    display_price = current_price
                
                new_price = st.number_input(
                    f"Unit Price ({currency})", 
                    min_value=0.0, 
                    value=float(display_price), 
                    key=f"price_{i}"
                )
                
                # Convert back to USD if needed for storage
                if currency == 'INR':
                    stored_price = new_price / get_usd_to_inr_rate() if get_usd_to_inr_rate() != 0 else 0
                else:
                    stored_price = new_price
            
            with col4:
                total_price = stored_price * new_quantity
                if currency == 'INR':
                    display_total = convert_currency(total_price, 'INR')
                    st.metric("Total", format_currency(display_total, 'INR'))
                else:
                    st.metric("Total", format_currency(total_price, 'USD'))
                
                if st.button(f"Remove", key=f"remove_{i}", type="secondary"):
                    items_to_remove.append(i)
            
            # Update item if changed
            st.session_state.boq_items[i].update({
                'name': new_name,
                'brand': new_brand,
                'category': new_category,
                'quantity': new_quantity,
                'price': stored_price
            })

    if items_to_remove:
        # Remove items in reverse order to avoid index issues
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()

    # Summary
    if 'boq_items' in st.session_state and st.session_state.boq_items:
        st.markdown("---")
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        if currency == 'INR':
            display_total = convert_currency(total_cost, 'INR')
            st.markdown(f"### **Total Project Cost: {format_currency(display_total * 1.30, 'INR')}**")
        else:
            st.markdown(f"### **Total Project Cost: {format_currency(total_cost * 1.30, 'USD')}**")

# --- FIXED UTILITY FUNCTIONS FOR VISUALIZATION (UPDATED AS PER YOUR REQUEST) ---

def map_equipment_type(category, product_name="", brand=""):
    """Enhanced mapping function that considers both category and product name."""
    if not category and not product_name:
        return 'control'
    
    # Combine category and product name for better matching
    search_text = f"{category} {product_name}".lower()
    
    # Enhanced mapping with more comprehensive patterns
    if any(term in search_text for term in ['display', 'monitor', 'screen', 'projector', 'tv', 'panel', 'signage', 'uh5j']):
        return 'display'
    elif any(term in search_text for term in ['speaker', 'audio', 'sound', 'amplifier', 'amp', 'c64p', 'pendant']):
        return 'audio_speaker'
    elif any(term in search_text for term in ['microphone', 'mic', 'sm58', 'handheld', 'wireless mic', 'mxw']):
        return 'audio_microphone'
    elif any(term in search_text for term in ['camera', 'video', 'conferencing', 'codec', 'webcam', 'studio', 'video bar', 'poly']):
        return 'camera'
    elif any(term in search_text for term in ['switch', 'network', 'poe', 'managed', 'cisco', 'cbs350', 'ethernet']):
        return 'network_switch'
    elif any(term in search_text for term in ['access point', 'transceiver', 'wireless', 'mxwapt', 'ap']):
        return 'network_device'
    elif any(term in search_text for term in ['charging station', 'charger', 'mxwncs', 'battery']):
        return 'charging_station'
    elif any(term in search_text for term in ['scheduler', 'controller', 'touch panel', 'tap', 'logitech', 'tc10']):
        return 'control_panel'
    elif any(term in search_text for term in ['control', 'processor', 'matrix', 'hub', 'interface']):
        return 'control'
    elif any(term in search_text for term in ['rack', 'cabinet', 'enclosure']):
        return 'rack'
    elif any(term in search_text for term in ['mount', 'bracket', 'stand', 'arm', 'vesa']):
        return 'mount'
    elif any(term in search_text for term in ['cable', 'wire', 'cord', 'connector', 'hdmi', 'usb', 'ethernet', 'kit']):
        return 'cable'
    elif any(term in search_text for term in ['installation', 'commissioning', 'testing', 'labor', 'service']):
        return 'service'  # Won't be visualized but handled properly
    elif any(term in search_text for term in ['power', 'ups', 'supply', 'conditioner']):
        return 'power'
    else:
        return 'control'  # Default fallback

def get_equipment_specs(equipment_type, product_name=""):
    """Enhanced specifications with new equipment types."""
    
    # Enhanced specifications by equipment type (width, height, depth in feet)
    default_specs = {
        'display': [4, 2.5, 0.2],
        'audio_speaker': [0.6, 1.0, 0.6],
        'audio_microphone': [0.2, 0.1, 0.2],
        'camera': [1.0, 0.4, 0.6],
        'control': [1.2, 0.6, 0.2],
        'control_panel': [0.8, 0.5, 0.1],
        'network_switch': [1.3, 0.15, 1.0],
        'network_device': [0.8, 0.8, 0.3],
        'charging_station': [1.0, 0.3, 0.8],
        'rack': [1.5, 5, 1.5],
        'mount': [0.3, 0.3, 0.8],
        'cable': [0.1, 0.1, 2],
        'power': [1.0, 0.4, 0.8],
        'service': [0, 0, 0],  # Services won't be visualized
        'generic_equipment': [0.8, 0.6, 0.6]
    }
    
    base_spec = default_specs.get(equipment_type, [1, 1, 1])
    
    # Extract size from product name for displays
    if equipment_type == 'display' and product_name:
        import re
        size_match = re.search(r'(\d+)"', product_name)
        if size_match:
            size_inches = int(size_match.group(1))
            # Convert diagonal size to approximate width/height (16:9 ratio)
            width_inches = size_inches * 0.87
            height_inches = size_inches * 0.49
            return [width_inches / 12, height_inches / 12, 0.2]
    
    # Scale based on product name keywords
    if product_name:
        product_lower = product_name.lower()
        if any(term in product_lower for term in ['large', 'big', 'tower']):
            return [spec * 1.3 for spec in base_spec]
        elif any(term in product_lower for term in ['small', 'compact', 'mini']):
            return [spec * 0.8 for spec in base_spec]
    
    return base_spec


# --- ENHANCED REALISTIC 3D VISUALIZATION FUNCTION ---
def create_3d_visualization():
    """Create a highly realistic, interactive 3D room visualization with enhanced materials and lighting."""
    st.subheader("Enhanced 3D Room Visualization")

    equipment_data = st.session_state.get('boq_items', [])

    if not equipment_data:
        st.info("No BOQ items to visualize. Generate a BOQ first or add items manually.")
        return

    # Enhanced equipment processing
    js_equipment = []
    for item in equipment_data:
        equipment_type = map_equipment_type(item.get('category', ''), item.get('name', ''))

        if equipment_type == 'service':
            continue
            
        specs = get_equipment_specs(equipment_type, item.get('name', ''))
        
        try:
            quantity = int(item.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1
            
        for i in range(quantity):
            js_equipment.append({
                'id': len(js_equipment) + 1,
                'type': equipment_type,
                'name': item.get('name', 'Unknown'),
                'brand': item.get('brand', 'Unknown'),
                'price': float(item.get('price', 0)),
                'instance': i + 1,
                'original_quantity': quantity,
                'specs': specs
            })

    if not js_equipment:
        st.warning("No visualizable equipment found in BOQ. All items may be services or accessories.")
        return

    room_length = st.session_state.get('room_length_input', 24.0)
    room_width = st.session_state.get('room_width_input', 16.0)
    room_height = st.session_state.get('ceiling_height_input', 9.0)
    room_type_str = st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)')
    
    # Enhanced room specifications for all types
    room_specs = {
        'Small Huddle Room (2-3 People)': {
            'furniture_config': 'small_huddle',
            'chair_count': 3,
            'table_size': [4, 4],
            'equipment_density': 'minimal',
            'lighting_type': 'intimate'
        },
        'Medium Huddle Room (4-6 People)': {
            'furniture_config': 'medium_huddle',
            'chair_count': 6,
            'table_size': [6, 4],
            'equipment_density': 'standard',
            'lighting_type': 'collaborative'
        },
        'Standard Conference Room (6-8 People)': {
            'furniture_config': 'standard_conference',
            'chair_count': 8,
            'table_size': [10, 4],
            'equipment_density': 'standard',
            'lighting_type': 'conference'
        },
        'Large Conference Room (8-12 People)': {
            'furniture_config': 'large_conference',
            'chair_count': 12,
            'table_size': [14, 5],
            'equipment_density': 'enhanced',
            'lighting_type': 'conference'
        },
        'Executive Boardroom (10-16 People)': {
            'furniture_config': 'executive_boardroom',
            'chair_count': 16,
            'table_size': [16, 6],
            'equipment_density': 'premium',
            'lighting_type': 'executive'
        },
        'Training Room (15-25 People)': {
            'furniture_config': 'training_room',
            'chair_count': 25,
            'table_size': [8, 3],
            'equipment_density': 'training',
            'lighting_type': 'presentation'
        },
        'Large Training/Presentation Room (25-40 People)': {
            'furniture_config': 'large_training',
            'chair_count': 40,
            'table_size': [10, 3],
            'equipment_density': 'presentation',
            'lighting_type': 'presentation'
        },
        'Multipurpose Event Room (40+ People)': {
            'furniture_config': 'multipurpose',
            'chair_count': 60,
            'table_size': [12, 4],
            'equipment_density': 'event',
            'lighting_type': 'event'
        },
        'Video Production Studio': {
            'furniture_config': 'production_studio',
            'chair_count': 8,
            'table_size': [8, 4],
            'equipment_density': 'studio',
            'lighting_type': 'studio'
        },
        'Telepresence Suite': {
            'furniture_config': 'telepresence',
            'chair_count': 10,
            'table_size': [12, 5],
            'equipment_density': 'telepresence',
            'lighting_type': 'telepresence'
        }
    }
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; }}
            #container {{ width: 100%; height: 650px; position: relative; cursor: grab; }}
            #container:active {{ cursor: grabbing; }}
            #info-panel {{ 
                position: absolute; top: 15px; left: 15px; color: #ffffff; 
                background: linear-gradient(135deg, rgba(0,0,0,0.95), rgba(30,30,30,0.9));
                padding: 18px; border-radius: 15px; backdrop-filter: blur(15px);
                border: 1px solid rgba(255,255,255,0.15); width: 340px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.5);
                display: flex; flex-direction: column; max-height: 620px;
            }}
            .equipment-manifest {{ flex-grow: 1; overflow-y: auto; margin-top: 12px; }}
            .equipment-item {{ 
                margin: 5px 0; padding: 10px; background: rgba(255,255,255,0.06); 
                border-radius: 8px; border-left: 3px solid transparent; cursor: pointer; 
                transition: all 0.3s ease; backdrop-filter: blur(5px);
            }}
            .equipment-item:hover {{ background: rgba(255,255,255,0.12); transform: translateX(2px); }}
            .equipment-item.selected-item {{
                background: rgba(79, 195, 247, 0.25);
                border-left: 3px solid #4FC3F7;
                box-shadow: 0 4px 15px rgba(79, 195, 247, 0.2);
            }}
            .equipment-name {{ color: #FFD54F; font-weight: bold; font-size: 14px; }}
            .equipment-details {{ color: #ccc; font-size: 12px; margin-top: 2px; }}
            #selectedItemInfo {{
                padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.2); margin-top: 12px;
                min-height: 60px; background: rgba(255,255,255,0.03); border-radius: 8px; padding: 12px;
            }}
            #controls {{
                position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.9); padding: 12px; border-radius: 25px;
                display: flex; gap: 8px; backdrop-filter: blur(15px);
                border: 1px solid rgba(255, 255, 255, 0.15); z-index: 1000;
                box-shadow: 0 8px 32px rgba(0,0,0,0.6);
            }}
            .control-btn {{
                background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.2);
                color: white; padding: 10px 18px; border-radius: 18px; cursor: pointer;
                transition: all 0.3s ease; font-size: 12px; font-weight: 500;
            }}
            .control-btn:hover {{ background: rgba(255, 255, 255, 0.25); transform: translateY(-2px); }}
            .control-btn.active {{ background: #4FC3F7; border-color: #03A9F4; box-shadow: 0 4px 15px rgba(79, 195, 247, 0.3); }}
            #lighting-controls {{
                position: absolute; top: 15px; right: 15px; background: rgba(0, 0, 0, 0.9);
                padding: 15px; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.15);
                backdrop-filter: blur(15px);
            }}
            .lighting-btn {{
                background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);
                color: white; padding: 8px 12px; margin: 2px; border-radius: 8px; cursor: pointer;
                transition: all 0.3s ease; font-size: 11px; display: block; width: 100%;
            }}
            .lighting-btn:hover {{ background: rgba(255, 255, 255, 0.2); }}
            .lighting-btn.active {{ background: #FFD54F; color: #000; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="info-panel">
                <div>
                    <h3 style="margin-top: 0; color: #4FC3F7; font-size: 17px;">Equipment Manifest</h3>
                    <div style="font-size: 13px; color: #ccc;">Visualizing {len(js_equipment)} equipment instances</div>
                    <div style="font-size: 12px; color: #888; margin-top: 5px;">Click items below to auto-zoom</div>
                </div>
                <div class="equipment-manifest" id="equipmentList"></div>
                <div id="selectedItemInfo">
                    <strong>Click an object or list item for details</strong>
                </div>
            </div>
            
            <div id="lighting-controls">
                <h4 style="margin: 0 0 8px 0; color: #FFD54F; font-size: 13px;">Lighting</h4>
                <button class="lighting-btn active" onclick="setLighting('default', this)">Default</button>
                <button class="lighting-btn" onclick="setLighting('warm', this)">Warm</button>
                <button class="lighting-btn" onclick="setLighting('cool', this)">Cool</button>
                <button class="lighting-btn" onclick="setLighting('dramatic', this)">Dramatic</button>
                <button class="lighting-btn" onclick="setLighting('presentation', this)">Presentation</button>
            </div>
            
            <div id="controls">
                <button class="control-btn active" onclick="setView('overview', true, this)">🏠 Overview</button>
                <button class="control-btn" onclick="setView('front', true, this)">📺 Front</button>
                <button class="control-btn" onclick="setView('side', true, this)">📐 Side</button>
                <button class="control-btn" onclick="setView('top', true, this)">📊 Top</button>
                <button class="control-btn" onclick="zoomToSelected()">🔍 Zoom Selected</button>
                <button class="control-btn" onclick="toggleWireframe()">🔲 Wireframe</button>
            </div>
        </div>
        
        <script>
            let scene, camera, renderer, raycaster, mouse;
            let animationId, selectedObject = null;
            let ambientLight, directionalLight1, directionalLight2, spotLight;
            let wireframeMode = false;
            
            const toUnits = (feet) => feet * 0.3048;
            const avEquipment = {json.dumps(js_equipment)};
            const roomType = `{room_type_str}`;
            const roomDims = {{
                length: {room_length},
                width: {room_width},
                height: {room_height}
            }};
            const roomSpecs = {json.dumps(room_specs)};

            // Enhanced material library
            const materials = {{
                // Wood materials
                lightWood: new THREE.MeshStandardMaterial({{ 
                    color: 0x8B7355, roughness: 0.8, metalness: 0.0 
                }}),
                darkWood: new THREE.MeshStandardMaterial({{ 
                    color: 0x4A3728, roughness: 0.7, metalness: 0.0 
                }}),
                mahogany: new THREE.MeshStandardMaterial({{ 
                    color: 0x6B4226, roughness: 0.6, metalness: 0.1 
                }}),
                
                // Fabric materials
                fabric: new THREE.MeshStandardMaterial({{ 
                    color: 0x2C3E50, roughness: 1.0, metalness: 0.0 
                }}),
                leather: new THREE.MeshStandardMaterial({{ 
                    color: 0x1A1A1A, roughness: 0.4, metalness: 0.0 
                }}),
                executiveLeather: new THREE.MeshStandardMaterial({{ 
                    color: 0x654321, roughness: 0.3, metalness: 0.1 
                }}),
                
                // Metal materials
                brushedMetal: new THREE.MeshStandardMaterial({{ 
                    color: 0xC0C0C0, roughness: 0.3, metalness: 0.8 
                }}),
                blackMetal: new THREE.MeshStandardMaterial({{ 
                    color: 0x2C2C2C, roughness: 0.4, metalness: 0.7 
                }}),
                chrome: new THREE.MeshStandardMaterial({{ 
                    color: 0xF0F0F0, roughness: 0.1, metalness: 0.9 
                }}),
                
                // Tech materials
                plasticBlack: new THREE.MeshStandardMaterial({{ 
                    color: 0x1C1C1C, roughness: 0.6, metalness: 0.1 
                }}),
                screenBezel: new THREE.MeshStandardMaterial({{ 
                    color: 0x0A0A0A, roughness: 0.2, metalness: 0.3 
                }}),
                screen: new THREE.MeshBasicMaterial({{ color: 0x0F1419 }}),
                
                // Wall and floor materials
                wall: new THREE.MeshStandardMaterial({{ 
                    color: 0xF5F5F5, roughness: 0.9, metalness: 0.0 
                }}),
                carpet: new THREE.MeshStandardMaterial({{ 
                    color: 0x4A5568, roughness: 1.0, metalness: 0.0 
                }}),
                ceiling: new THREE.MeshStandardMaterial({{ 
                    color: 0xFAFAFA, roughness: 0.8, metalness: 0.0 
                }}),
                
                // Glass materials
                glass: new THREE.MeshPhysicalMaterial({{
                    color: 0xFFFFFF, roughness: 0.0, metalness: 0.0,
                    transmission: 0.9, transparent: true, opacity: 0.3
                }})
            }};

            function init() {{
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x2C3E50);
                scene.fog = new THREE.Fog(0x2C3E50, toUnits(30), toUnits(120));
                
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
                
                createRoom();
                createAdvancedLighting();
                createRoomFurniture();
                createAllEquipmentObjects();
                setupCameraControls();
                updateEquipmentList();
                animate();
            }}

            function createRoom() {{
                const roomGroup = new THREE.Group();
                const wallHeight = toUnits(roomDims.height);
                const roomSpec = roomSpecs[roomType] || roomSpecs['Standard Conference Room (6-8 People)'];
                
                // Enhanced floor with subtle texture pattern
                const floorGeometry = new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width));
                const floor = new THREE.Mesh(floorGeometry, materials.carpet);
                floor.rotation.x = -Math.PI / 2;
                floor.receiveShadow = true;
                roomGroup.add(floor);
                
                // Create baseboards
                const baseboardHeight = toUnits(0.5);
                const baseboardMaterial = materials.darkWood;
                
                // Front baseboard
                const frontBaseboard = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(roomDims.length), baseboardHeight, toUnits(0.2)),
                    baseboardMaterial
                );
                frontBaseboard.position.set(0, baseboardHeight/2, toUnits(roomDims.width/2) - toUnits(0.1));
                roomGroup.add(frontBaseboard);
                
                // Enhanced walls with realistic proportions
                const walls = [
                    {{ // Back wall
                        geometry: new THREE.PlaneGeometry(toUnits(roomDims.length), wallHeight),
                        position: [0, wallHeight/2, -toUnits(roomDims.width/2)],
                        rotation: [0, 0, 0]
                    }},
                    {{ // Left wall  
                        geometry: new THREE.PlaneGeometry(toUnits(roomDims.width), wallHeight),
                        position: [-toUnits(roomDims.length/2), wallHeight/2, 0],
                        rotation: [0, Math.PI/2, 0]
                    }},
                    {{ // Right wall
                        geometry: new THREE.PlaneGeometry(toUnits(roomDims.width), wallHeight),
                        position: [toUnits(roomDims.length/2), wallHeight/2, 0],
                        rotation: [0, -Math.PI/2, 0]
                    }}
                ];
                
                walls.forEach(wall => {{
                    const mesh = new THREE.Mesh(wall.geometry, materials.wall);
                    mesh.position.set(...wall.position);
                    mesh.rotation.set(...wall.rotation);
                    mesh.receiveShadow = true;
                    roomGroup.add(mesh);
                }});
                
                // Enhanced ceiling with recessed lighting areas
                const ceiling = new THREE.Mesh(
                    new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)),
                    materials.ceiling
                );
                ceiling.rotation.x = Math.PI / 2;
                ceiling.position.y = wallHeight;
                ceiling.receiveShadow = true;
                roomGroup.add(ceiling);
                
                // Add ceiling tiles pattern
                for(let x = -roomDims.length/2 + 2; x < roomDims.length/2; x += 4) {{
                    for(let z = -roomDims.width/2 + 2; z < roomDims.width/2; z += 4) {{
                        const tile = new THREE.Mesh(
                            new THREE.PlaneGeometry(toUnits(3.8), toUnits(3.8)),
                            new THREE.MeshStandardMaterial({{ color: 0xF8F8F8, roughness: 0.7 }})
                        );
                        tile.rotation.x = Math.PI / 2;
                        tile.position.set(toUnits(x), wallHeight - toUnits(0.05), toUnits(z));
                        roomGroup.add(tile);
                    }}
                }}
                
                scene.add(roomGroup);
            }}

            function createAdvancedLighting() {{
                // Enhanced ambient lighting
                ambientLight = new THREE.AmbientLight(0x404040, 0.4);
                scene.add(ambientLight);
                
                // Main directional light (window light)
                directionalLight1 = new THREE.DirectionalLight(0xFFF8DC, 0.8);
                directionalLight1.position.set(toUnits(15), toUnits(15), toUnits(10));
                directionalLight1.castShadow = true;
                directionalLight1.shadow.mapSize.width = 2048;
                directionalLight1.shadow.mapSize.height = 2048;
                directionalLight1.shadow.camera.near = 0.5;
                directionalLight1.shadow.camera.far = toUnits(50);
                directionalLight1.shadow.camera.left = directionalLight1.shadow.camera.bottom = -toUnits(20);
                directionalLight1.shadow.camera.right = directionalLight1.shadow.camera.top = toUnits(20);
                scene.add(directionalLight1);
                
                // Secondary fill light
                directionalLight2 = new THREE.DirectionalLight(0xE6F3FF, 0.3);
                directionalLight2.position.set(toUnits(-10), toUnits(12), toUnits(-5));
                scene.add(directionalLight2);
                
                // Ceiling spot lights
                const lightPositions = [
                    [-roomDims.length/4, roomDims.height - 0.5, -roomDims.width/4],
                    [roomDims.length/4, roomDims.height - 0.5, -roomDims.width/4],
                    [-roomDims.length/4, roomDims.height - 0.5, roomDims.width/4],
                    [roomDims.length/4, roomDims.height - 0.5, roomDims.width/4]
                ];
                
                lightPositions.forEach((pos, i) => {{
                    const spotLight = new THREE.SpotLight(0xFFFFFF, 0.5, toUnits(20), Math.PI/6, 0.5, 2);
                    spotLight.position.set(toUnits(pos[0]), toUnits(pos[1]), toUnits(pos[2]));
                    spotLight.target.position.set(toUnits(pos[0]), 0, toUnits(pos[2]));
                    spotLight.castShadow = true;
                    scene.add(spotLight);
                    scene.add(spotLight.target);
                    
                    // Add visible light fixture
                    const fixture = new THREE.Mesh(
                        new THREE.CylinderGeometry(toUnits(0.5), toUnits(0.8), toUnits(0.3), 8),
                        materials.brushedMetal
                    );
                    fixture.position.set(toUnits(pos[0]), toUnits(pos[1]) + toUnits(0.2), toUnits(pos[2]));
                    scene.add(fixture);
                }});
            }}

            function createRoomFurniture() {{
                const furnitureGroup = new THREE.Group();
                const spec = roomSpecs[roomType] || roomSpecs['Standard Conference Room (6-8 People)'];
                
                // Ensure furniture fits in room
                const safeFurnitureSpec = {{
                    ...spec,
                    table_size: [
                        Math.min(spec.table_size[0], roomDims.length - 4),
                        Math.min(spec.table_size[1], roomDims.width - 4)
                    ]
                }};
                
                switch(spec.furniture_config) {{
                    case 'small_huddle':
                        createHuddleLayout(furnitureGroup, safeFurnitureSpec, 'small');
                        break;
                    case 'medium_huddle':
                        createHuddleLayout(furnitureGroup, safeFurnitureSpec, 'medium');
                        break;
                    case 'standard_conference':
                    case 'large_conference':
                        createConferenceLayout(furnitureGroup, safeFurnitureSpec, false);
                        break;
                    case 'executive_boardroom':
                        createConferenceLayout(furnitureGroup, safeFurnitureSpec, true);
                        break;
                    case 'training_room':
                    case 'large_training':
                        createTrainingLayout(furnitureGroup, safeFurnitureSpec);
                        break;
                    case 'multipurpose':
                        createMultipurposeLayout(furnitureGroup, safeFurnitureSpec);
                        break;
                    case 'production_studio':
                        createStudioLayout(furnitureGroup, safeFurnitureSpec);
                        break;
                    case 'telepresence':
                        createTelepresenceLayout(furnitureGroup, safeFurnitureSpec);
                        break;
                    default:
                        createConferenceLayout(furnitureGroup, safeFurnitureSpec, false);
                }}
                
                scene.add(furnitureGroup);
            }}

            function createHuddleLayout(group, spec, size) {{
                const isSmall = (size === 'small');
                const tableMaterial = isSmall ? materials.lightWood : materials.darkWood;
                const chairMaterial = materials.fabric;
                
                // Round table
                const tableRadius = toUnits(isSmall ? 2.5 : 3.0);
                const table = createRoundTable(tableRadius, tableMaterial);
                table.position.y = toUnits(2.5);
                group.add(table);
                
                // Chairs around table
                const chairCount = spec.chair_count;
                const chairOrbitRadius = tableRadius + toUnits(1.8);
                
                for (let i = 0; i < chairCount; i++) {{
                    const chair = createModernChair(chairMaterial);
                    const angle = (i / chairCount) * Math.PI * 2;
                    chair.position.x = Math.cos(angle) * chairOrbitRadius;
                    chair.position.z = Math.sin(angle) * chairOrbitRadius;
                    chair.rotation.y = angle + Math.PI;
                    group.add(chair);
                }}
                
                // Add side cabinet for huddle rooms
                const cabinet = createSideCabinet();
                cabinet.position.set(toUnits(-roomDims.length/2 + 2), 0, toUnits(roomDims.width/2 - 2));
                group.add(cabinet);
            }}

            function createConferenceLayout(group, spec, isExecutive) {{
                const tableMaterial = isExecutive ? materials.mahogany : materials.darkWood;
                const chairMaterial = isExecutive ? materials.executiveLeather : materials.fabric;
                
                // Enhanced conference table
                const tableLength = toUnits(spec.table_size[0]);
                const tableWidth = toUnits(spec.table_size[1]);
                const tableHeight = toUnits(2.5);
                
                // Table top with rounded edges
                const tableTop = new THREE.Mesh(
                    new THREE.BoxGeometry(tableLength, toUnits(0.3), tableWidth),
                    tableMaterial
                );
                tableTop.position.y = tableHeight;
                tableTop.castShadow = true;
                tableTop.receiveShadow = true;
                group.add(tableTop);
                
                // Table base structure
                const baseStructure = new THREE.Mesh(
                    new THREE.BoxGeometry(tableLength - toUnits(1), toUnits(0.8), tableWidth - toUnits(1)),
                    tableMaterial
                );
                baseStructure.position.y = tableHeight - toUnits(0.6);
                group.add(baseStructure);
                
                // Support legs
                const legPositions = [
                    [tableLength/3, -tableWidth/3], [-tableLength/3, -tableWidth/3],
                    [tableLength/3, tableWidth/3], [-tableLength/3, tableWidth/3]
                ];
                
                legPositions.forEach(pos => {{
                    const leg = new THREE.Mesh(
                        new THREE.CylinderGeometry(toUnits(0.15), toUnits(0.2), tableHeight - toUnits(0.8)),
                        materials.brushedMetal
                    );
                    leg.position.set(pos[0], (tableHeight - toUnits(0.8))/2, pos[1]);
                    group.add(leg);
                }});
                
                // Place chairs
                this.placeChairsAroundTable(group, tableLength, tableWidth, spec.chair_count, chairMaterial, isExecutive);
                
                // Add credenza for executive rooms
                if (isExecutive) {{
                    const credenza = createCredenza();
                    credenza.position.set(0, 0, -toUnits(roomDims.width/2) + toUnits(2));
                    group.add(credenza);
                }}
            }}

            function placeChairsAroundTable(group, tableLength, tableWidth, chairCount, material, isExecutive) {{
                const chairSpacing = toUnits(3.0);
                const chairOffset = toUnits(2.0);
                let chairsPlaced = 0;
                // Long sides of table
                const longSideChairs = Math.floor(chairCount * 0.6);
                const shortSideChairs = chairCount - longSideChairs;
                
                // Place chairs along long sides
                for (let i = 0; i < longSideChairs; i++) {
                    if (chairsPlaced >= chairCount) break;
                    
                    const chair = isExecutive ? createExecutiveChair(material) : createModernChair(material);
                    const side = i % 2; // Alternate sides
                    const positionIndex = Math.floor(i / 2);
                    const totalPositions = Math.ceil(longSideChairs / 2);
                    
                    const x = (positionIndex - (totalPositions - 1) / 2) * chairSpacing;
                    const z = side === 0 ? tableWidth/2 + chairOffset : -tableWidth/2 - chairOffset;
                    
                    chair.position.set(x, 0, z);
                    chair.rotation.y = side === 0 ? Math.PI : 0;
                    group.add(chair);
                    chairsPlaced++;
                }
                
                // Place chairs at short sides (head of table)
                for (let i = 0; i < shortSideChairs; i++) {
                    if (chairsPlaced >= chairCount) break;
                    
                    const chair = isExecutive ? createExecutiveChair(material) : createModernChair(material);
                    const side = i % 2;
                    
                    const x = side === 0 ? tableLength/2 + chairOffset : -tableLength/2 - chairOffset;
                    const z = 0;
                    
                    chair.position.set(x, 0, z);
                    chair.rotation.y = side === 0 ? -Math.PI/2 : Math.PI/2;
                    group.add(chair);
                    chairsPlaced++;
                }
            }

            function createTrainingLayout(group, spec) {
                const tableMaterial = materials.lightWood;
                const chairMaterial = materials.fabric;
                
                // Create classroom-style arrangement
                const rows = Math.ceil(spec.chair_count / 5);
                const chairsPerRow = Math.ceil(spec.chair_count / rows);
                
                for (let row = 0; row < rows; row++) {
                    // Small tables for each row
                    const tableLength = toUnits(8);
                    const tableWidth = toUnits(2);
                    
                    const table = new THREE.Mesh(
                        new THREE.BoxGeometry(tableLength, toUnits(0.2), tableWidth),
                        tableMaterial
                    );
                    table.position.set(0, toUnits(2.3), toUnits(-roomDims.width/4 + row * 4));
                    table.castShadow = true;
                    table.receiveShadow = true;
                    group.add(table);
                    
                    // Table legs
                    const legPositions = [
                        [tableLength/3, -tableWidth/2], [-tableLength/3, -tableWidth/2],
                        [tableLength/3, tableWidth/2], [-tableLength/3, tableWidth/2]
                    ];
                    
                    legPositions.forEach(pos => {
                        const leg = new THREE.Mesh(
                            new THREE.CylinderGeometry(toUnits(0.1), toUnits(0.1), toUnits(2.3)),
                            materials.brushedMetal
                        );
                        leg.position.set(pos[0], toUnits(1.15), toUnits(-roomDims.width/4 + row * 4) + pos[1]);
                        group.add(leg);
                    });
                    
                    // Chairs for this row
                    const chairsThisRow = Math.min(chairsPerRow, spec.chair_count - row * chairsPerRow);
                    for (let j = 0; j < chairsThisRow; j++) {
                        const chair = createModernChair(chairMaterial);
                        chair.position.set(
                            (j - (chairsThisRow - 1) / 2) * toUnits(3),
                            0,
                            toUnits(-roomDims.width/4 + row * 4) + toUnits(1.5)
                        );
                        group.add(chair);
                    }
                }
                
                // Presentation area at front
                const podium = createPodium();
                podium.position.set(toUnits(2), 0, toUnits(roomDims.width/2 - 3));
                group.add(podium);
            }

            function createMultipurposeLayout(group, spec) {
                // Flexible seating arrangement
                const sectionSize = Math.ceil(spec.chair_count / 4);
                
                // Create four sections of round tables
                const positions = [
                    [-roomDims.length/4, -roomDims.width/4],
                    [roomDims.length/4, -roomDims.width/4],
                    [-roomDims.length/4, roomDims.width/4],
                    [roomDims.length/4, roomDims.width/4]
                ];
                
                positions.forEach((pos, index) => {
                    const table = createRoundTable(toUnits(3), materials.lightWood);
                    table.position.set(toUnits(pos[0]), toUnits(2.5), toUnits(pos[1]));
                    group.add(table);
                    
                    // Chairs around each table
                    const chairsPerTable = Math.min(8, spec.chair_count - index * 8);
                    for (let i = 0; i < chairsPerTable; i++) {
                        const chair = createModernChair(materials.fabric);
                        const angle = (i / chairsPerTable) * Math.PI * 2;
                        chair.position.set(
                            toUnits(pos[0]) + Math.cos(angle) * toUnits(4.5),
                            0,
                            toUnits(pos[1]) + Math.sin(angle) * toUnits(4.5)
                        );
                        chair.rotation.y = angle + Math.PI;
                        group.add(chair);
                    }
                });
            }

            function createStudioLayout(group, spec) {
                // Production desk
                const deskLength = toUnits(12);
                const deskWidth = toUnits(4);
                
                const desk = new THREE.Mesh(
                    new THREE.BoxGeometry(deskLength, toUnits(0.3), deskWidth),
                    materials.blackMetal
                );
                desk.position.set(0, toUnits(3.5), 0);
                desk.castShadow = true;
                group.add(desk);
                
                // Control surface on desk
                const controlSurface = new THREE.Mesh(
                    new THREE.BoxGeometry(deskLength - toUnits(1), toUnits(0.1), deskWidth - toUnits(0.5)),
                    materials.plasticBlack
                );
                controlSurface.position.set(0, toUnits(3.8), 0);
                group.add(controlSurface);
                
                // Director chairs
                for (let i = 0; i < spec.chair_count; i++) {
                    const chair = createExecutiveChair(materials.leather);
                    chair.position.set(
                        (i - (spec.chair_count - 1) / 2) * toUnits(4),
                        0,
                        -deskWidth/2 - toUnits(2)
                    );
                    group.add(chair);
                }
                
                // Equipment racks
                for (let i = 0; i < 3; i++) {
                    const rack = createEquipmentRack();
                    rack.position.set(toUnits(-roomDims.length/2 + 2), 0, toUnits(-roomDims.width/2 + 2 + i * 3));
                    group.add(rack);
                }
            }

            function createTelepresenceLayout(group, spec) {
                // Curved conference table for telepresence
                const tableLength = toUnits(spec.table_size[0]);
                const tableWidth = toUnits(spec.table_size[1]);
                
                const table = new THREE.Mesh(
                    new THREE.BoxGeometry(tableLength, toUnits(0.3), tableWidth),
                    materials.mahogany
                );
                table.position.y = toUnits(2.5);
                table.castShadow = true;
                group.add(table);
                
                // Place chairs in telepresence arrangement (facing front)
                const chairsPerRow = 5;
                const rows = Math.ceil(spec.chair_count / chairsPerRow);
                
                for (let row = 0; row < rows; row++) {
                    const chairsThisRow = Math.min(chairsPerRow, spec.chair_count - row * chairsPerRow);
                    for (let i = 0; i < chairsThisRow; i++) {
                        const chair = createExecutiveChair(materials.executiveLeather);
                        chair.position.set(
                            (i - (chairsThisRow - 1) / 2) * toUnits(3),
                            0,
                            toUnits(-2 - row * 3)
                        );
                        group.add(chair);
                    }
                }
                
                // Technology integration area
                const techConsole = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(6), toUnits(3), toUnits(2)),
                    materials.blackMetal
                );
                techConsole.position.set(0, toUnits(1.5), toUnits(roomDims.width/2 - 2));
                group.add(techConsole);
            }

            // Helper functions for furniture creation
            function createModernChair(material) {
                const chairGroup = new THREE.Group();
                
                // Chair base
                const base = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(1), toUnits(1), toUnits(0.3), 5),
                    materials.brushedMetal
                );
                base.position.y = toUnits(0.15);
                chairGroup.add(base);
                
                // Chair stem
                const stem = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.2), toUnits(0.2), toUnits(1.5)),
                    materials.brushedMetal
                );
                stem.position.y = toUnits(1.05);
                chairGroup.add(stem);
                
                // Seat
                const seat = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(1.5), toUnits(0.3), toUnits(1.5)),
                    material
                );
                seat.position.y = toUnits(1.8);
                seat.castShadow = true;
                chairGroup.add(seat);
                
                // Backrest
                const backrest = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(1.5), toUnits(2), toUnits(0.3)),
                    material
                );
                backrest.position.set(0, toUnits(2.8), -toUnits(0.6));
                backrest.castShadow = true;
                chairGroup.add(backrest);
                
                return chairGroup;
            }

            function createExecutiveChair(material) {
                const chairGroup = createModernChair(material);
                
                // Add armrests
                [-0.9, 0.9].forEach(x => {
                    const armrest = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(0.3), toUnits(0.3), toUnits(1.2)),
                        materials.brushedMetal
                    );
                    armrest.position.set(toUnits(x), toUnits(2.3), 0);
                    chairGroup.add(armrest);
                });
                
                // Higher backrest
                const highBack = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(1.8), toUnits(1), toUnits(0.3)),
                    material
                );
                highBack.position.set(0, toUnits(3.8), -toUnits(0.6));
                chairGroup.add(highBack);
                
                return chairGroup;
            }

            function createRoundTable(radius, material) {
                const tableGroup = new THREE.Group();
                
                // Table top
                const top = new THREE.Mesh(
                    new THREE.CylinderGeometry(radius, radius, toUnits(0.3)),
                    material
                );
                top.position.y = toUnits(2.5);
                top.castShadow = true;
                top.receiveShadow = true;
                tableGroup.add(top);
                
                // Table base
                const base = new THREE.Mesh(
                    new THREE.CylinderGeometry(radius * 0.6, radius * 0.8, toUnits(2.3)),
                    materials.brushedMetal
                );
                base.position.y = toUnits(1.15);
                tableGroup.add(base);
                
                return tableGroup;
            }

            function createSideCabinet() {
                const cabinetGroup = new THREE.Group();
                
                const cabinet = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(4), toUnits(2.5), toUnits(1.5)),
                    materials.darkWood
                );
                cabinet.position.y = toUnits(1.25);
                cabinet.castShadow = true;
                cabinetGroup.add(cabinet);
                
                // Cabinet doors
                for (let i = 0; i < 2; i++) {
                    const door = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(1.8), toUnits(2.2), toUnits(0.1)),
                        materials.lightWood
                    );
                    door.position.set(toUnits(-0.9 + i * 1.8), toUnits(1.25), toUnits(0.8));
                    cabinetGroup.add(door);
                }
                
                return cabinetGroup;
            }

            function createCredenza() {
                const credenzaGroup = new THREE.Group();
                
                const main = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(8), toUnits(2.8), toUnits(1.8)),
                    materials.mahogany
                );
                main.position.y = toUnits(1.4);
                main.castShadow = true;
                credenzaGroup.add(main);
                
                // Decorative top
                const top = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(8.2), toUnits(0.2), toUnits(2)),
                    materials.mahogany
                );
                top.position.y = toUnits(2.9);
                credenzaGroup.add(top);
                
                return credenzaGroup;
            }

            function createPodium() {
                const podiumGroup = new THREE.Group();
                
                const base = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(2), toUnits(3.5), toUnits(1.5)),
                    materials.darkWood
                );
                base.position.y = toUnits(1.75);
                base.castShadow = true;
                podiumGroup.add(base);
                
                const top = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(2.5), toUnits(0.3), toUnits(2)),
                    materials.darkWood
                );
                top.position.y = toUnits(3.65);
                podiumGroup.add(top);
                
                return podiumGroup;
            }

            function createEquipmentRack() {
                const rackGroup = new THREE.Group();
                
                const frame = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(1.5), toUnits(6), toUnits(2)),
                    materials.blackMetal
                );
                frame.position.y = toUnits(3);
                frame.castShadow = true;
                rackGroup.add(frame);
                
                // Rack units
                for (let i = 0; i < 8; i++) {
                    const unit = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(1.3), toUnits(0.6), toUnits(1.8)),
                        materials.plasticBlack
                    );
                    unit.position.set(0, toUnits(0.5 + i * 0.7), 0);
                    rackGroup.add(unit);
                }
                
                return rackGroup;
            }

            function createAllEquipmentObjects() {
                const equipmentGroup = new THREE.Group();
                equipmentGroup.name = 'equipmentGroup';
                
                avEquipment.forEach((item, index) => {
                    const equipmentObject = createEquipmentObject(item);
                    if (equipmentObject) {
                        equipmentObject.userData = item;
                        equipmentObject.name = `equipment_${item.id}`;
                        equipmentGroup.add(equipmentObject);
                    }
                });
                
                scene.add(equipmentGroup);
                positionEquipmentInRoom();
            }

            function createEquipmentObject(item) {
                const group = new THREE.Group();
                
                switch(item.type) {
                    case 'display':
                        return createDisplayObject(item, group);
                    case 'projector':
                        return createProjectorObject(item, group);
                    case 'camera':
                        return createCameraObject(item, group);
                    case 'microphone':
                        return createMicrophoneObject(item, group);
                    case 'speaker':
                        return createSpeakerObject(item, group);
                    case 'control_system':
                        return createControlSystemObject(item, group);
                    case 'cable':
                        return createCableObject(item, group);
                    case 'mount':
                        return createMountObject(item, group);
                    case 'processor':
                        return createProcessorObject(item, group);
                    case 'amplifier':
                        return createAmplifierObject(item, group);
                    case 'switcher':
                        return createSwitcherObject(item, group);
                    case 'recorder':
                        return createRecorderObject(item, group);
                    case 'interface':
                        return createInterfaceObject(item, group);
                    default:
                        return createGenericEquipmentObject(item, group);
                }
            }

            function createDisplayObject(item, group) {
                const specs = item.specs || {};
                const width = toUnits(specs.width_inches || 65) / 12; // Convert to feet
                const height = width * 9/16; // 16:9 aspect ratio
                const depth = toUnits(0.3);
                
                // Screen
                const screen = new THREE.Mesh(
                    new THREE.BoxGeometry(width, height, toUnits(0.1)),
                    materials.screen
                );
                screen.position.z = depth/2;
                group.add(screen);
                
                // Bezel
                const bezelThickness = toUnits(0.05);
                const bezel = new THREE.Mesh(
                    new THREE.BoxGeometry(width + bezelThickness, height + bezelThickness, toUnits(0.12)),
                    materials.screenBezel
                );
                group.add(bezel);
                
                // Back panel
                const back = new THREE.Mesh(
                    new THREE.BoxGeometry(width, height, depth),
                    materials.plasticBlack
                );
                back.position.z = -depth/2;
                back.castShadow = true;
                group.add(back);
                
                return group;
            }

            function createProjectorObject(item, group) {
                const specs = item.specs || {};
                const length = toUnits(specs.length_inches || 15) / 12;
                const width = toUnits(specs.width_inches || 12) / 12;
                const height = toUnits(specs.height_inches || 6) / 12;
                
                // Main body
                const body = new THREE.Mesh(
                    new THREE.BoxGeometry(length, height, width),
                    materials.plasticBlack
                );
                body.castShadow = true;
                group.add(body);
                
                // Lens
                const lens = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.3), toUnits(0.3), toUnits(0.2)),
                    materials.glass
                );
                lens.rotation.z = Math.PI/2;
                lens.position.set(length/2, 0, 0);
                group.add(lens);
                
                // Cooling vents
                for (let i = 0; i < 3; i++) {
                    const vent = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(0.1), height * 0.8, toUnits(0.05)),
                        materials.blackMetal
                    );
                    vent.position.set(-length/4 + i * length/6, 0, width/2 + toUnits(0.025));
                    group.add(vent);
                }
                
                return group;
            }

            function createCameraObject(item, group) {
                // Camera base
                const base = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.4), toUnits(0.4), toUnits(0.3)),
                    materials.blackMetal
                );
                group.add(base);
                
                // Camera body
                const body = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(0.8), toUnits(0.5), toUnits(1.2)),
                    materials.plasticBlack
                );
                body.position.y = toUnits(0.4);
                body.castShadow = true;
                group.add(body);
                
                // Lens
                const lens = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.25), toUnits(0.25), toUnits(0.3)),
                    materials.glass
                );
                lens.rotation.x = Math.PI/2;
                lens.position.set(0, toUnits(0.4), toUnits(0.75));
                group.add(lens);
                
                return group;
            }

            function createMicrophoneObject(item, group) {
                // Microphone stand
                const stand = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.05), toUnits(0.1), toUnits(1.5)),
                    materials.brushedMetal
                );
                stand.position.y = toUnits(0.75);
                group.add(stand);
                
                // Microphone head
                const head = new THREE.Mesh(
                    new THREE.SphereGeometry(toUnits(0.15)),
                    materials.blackMetal
                );
                head.position.y = toUnits(1.5);
                head.castShadow = true;
                group.add(head);
                
                // Base
                const base = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.3), toUnits(0.3), toUnits(0.1)),
                    materials.brushedMetal
                );
                group.add(base);
                
                return group;
            }

            function createSpeakerObject(item, group) {
                const specs = item.specs || {};
                const width = toUnits(specs.width_inches || 8) / 12;
                const height = toUnits(specs.height_inches || 12) / 12;
                const depth = toUnits(specs.depth_inches || 8) / 12;
                
                // Speaker cabinet
                const cabinet = new THREE.Mesh(
                    new THREE.BoxGeometry(width, height, depth),
                    materials.blackMetal
                );
                cabinet.castShadow = true;
                group.add(cabinet);
                
                // Speaker drivers
                const driverPositions = specs.drivers || [0.3, -0.3];
                driverPositions.forEach(pos => {
                    const driver = new THREE.Mesh(
                        new THREE.CylinderGeometry(toUnits(0.2), toUnits(0.2), toUnits(0.1)),
                        materials.brushedMetal
                    );
                    driver.rotation.x = Math.PI/2;
                    driver.position.set(0, height * pos, depth/2 + toUnits(0.05));
                    group.add(driver);
                });
                
                // Speaker grille
                const grille = new THREE.Mesh(
                    new THREE.BoxGeometry(width * 0.9, height * 0.9, toUnits(0.05)),
                    materials.blackMetal
                );
                grille.position.z = depth/2 + toUnits(0.025);
                group.add(grille);
                
                return group;
            }

            function createControlSystemObject(item, group) {
                // Rack unit style
                const width = toUnits(19) / 12; // Standard rack width
                const height = toUnits(1.75) / 12; // 1U height
                const depth = toUnits(12) / 12;
                
                const body = new THREE.Mesh(
                    new THREE.BoxGeometry(width, height, depth),
                    materials.blackMetal
                );
                body.castShadow = true;
                group.add(body);
                
                // Front panel
                const frontPanel = new THREE.Mesh(
                    new THREE.BoxGeometry(width * 0.95, height * 0.8, toUnits(0.05)),
                    materials.brushedMetal
                );
                frontPanel.position.z = depth/2 + toUnits(0.025);
                group.add(frontPanel);
                
                // LED indicators
                for (let i = 0; i < 4; i++) {
                    const led = new THREE.Mesh(
                        new THREE.SphereGeometry(toUnits(0.02)),
                        new THREE.MeshBasicMaterial({ color: i === 0 ? 0x00ff00 : 0xff0000 })
                    );
                    led.position.set(
                        -width/3 + i * width/6,
                        0,
                        depth/2 + toUnits(0.08)
                    );
                    group.add(led);
                }
                
                return group;
            }

            function createCableObject(item, group) {
                // Simple cable representation
                const cable = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.02), toUnits(0.02), toUnits(6)),
                    materials.plasticBlack
                );
                cable.position.y = toUnits(0.1);
                group.add(cable);
                
                // Cable connectors
                [-1, 1].forEach(end => {
                    const connector = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(0.1), toUnits(0.05), toUnits(0.2)),
                        materials.brushedMetal
                    );
                    connector.position.y = end * toUnits(3);
                    group.add(connector);
                });
                
                return group;
            }

            function createMountObject(item, group) {
                // Wall/ceiling mount bracket
                const bracket = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(0.8), toUnits(0.2), toUnits(0.8)),
                    materials.brushedMetal
                );
                bracket.castShadow = true;
                group.add(bracket);
                
                // Mounting arm
                const arm = new THREE.Mesh(
                    new THREE.CylinderGeometry(toUnits(0.05), toUnits(0.05), toUnits(1.5)),
                    materials.brushedMetal
                );
                arm.position.y = toUnits(-0.75);
                group.add(arm);
                
                return group;
            }

            function createProcessorObject(item, group) {
                return createRackUnitObject(item, group, 2); // 2U height
            }

            function createAmplifierObject(item, group) {
                return createRackUnitObject(item, group, 3); // 3U height
            }

            function createSwitcherObject(item, group) {
                return createRackUnitObject(item, group, 1); // 1U height
            }

            function createRecorderObject(item, group) {
                return createRackUnitObject(item, group, 2); // 2U height
            }

            function createInterfaceObject(item, group) {
                return createRackUnitObject(item, group, 1); // 1U height
            }

            function createRackUnitObject(item, group, units = 1) {
                const width = toUnits(19) / 12; // Standard rack width
                const height = toUnits(1.75 * units) / 12; // U height
                const depth = toUnits(16) / 12; // Standard depth
                
                const body = new THREE.Mesh(
                    new THREE.BoxGeometry(width, height, depth),
                    materials.blackMetal
                );
                body.castShadow = true;
                group.add(body);
                
                // Front panel with ventilation
                const frontPanel = new THREE.Mesh(
                    new THREE.BoxGeometry(width * 0.95, height * 0.9, toUnits(0.05)),
                    materials.brushedMetal
                );
                frontPanel.position.z = depth/2 + toUnits(0.025);
                group.add(frontPanel);
                
                // Ventilation slots
                for (let i = 0; i < Math.floor(units * 3); i++) {
                    const slot = new THREE.Mesh(
                        new THREE.BoxGeometry(width * 0.8, toUnits(0.02), toUnits(0.06)),
                        materials.blackMetal
                    );
                    slot.position.set(
                        0,
                        -height/3 + i * (height/3)/units,
                        depth/2 + toUnits(0.08)
                    );
                    group.add(slot);
                }
                
                return group;
            }

            function createGenericEquipmentObject(item, group) {
                // Default generic equipment box
                const box = new THREE.Mesh(
                    new THREE.BoxGeometry(toUnits(1), toUnits(0.5), toUnits(1)),
                    materials.plasticBlack
                );
                box.castShadow = true;
                group.add(box);
                
                return group;
            }

            function positionEquipmentInRoom() {
                const equipmentGroup = scene.getObjectByName('equipmentGroup');
                if (!equipmentGroup) return;
                
                const wallPositions = {
                    front: { x: 0, z: toUnits(roomDims.width/2) - toUnits(1) },
                    back: { x: 0, z: -toUnits(roomDims.width/2) + toUnits(1) },
                    left: { x: -toUnits(roomDims.length/2) + toUnits(1), z: 0 },
                    right: { x: toUnits(roomDims.length/2) - toUnits(1), z: 0 }
                };
                
                const ceilingPositions = [];
                const floorPositions = [];
                const tablePositions = [];
                
                let displayCount = 0, projectorCount = 0, cameraCount = 0;
                let speakerCount = 0, microphoneCount = 0;
                
                equipmentGroup.children.forEach((equipment, index) => {
                    const item = equipment.userData;
                    let position = { x: 0, y: 0, z: 0 };
                    
                    switch(item.type) {
                        case 'display':
                            if (displayCount === 0) {
                                position = { ...wallPositions.front, y: toUnits(4) };
                            } else {
                                position = { 
                                    x: wallPositions.front.x + toUnits((displayCount - 1) * 4), 
                                    y: toUnits(4), 
                                    z: wallPositions.front.z 
                                };
                            }
                            displayCount++;
                            break;
                            
                        case 'projector':
                            position = {
                                x: 0,
                                y: toUnits(roomDims.height - 2),
                                z: toUnits(-roomDims.width/4)
                            };
                            projectorCount++;
                            break;
                            
                        case 'camera':
                            if (cameraCount === 0) {
                                position = { ...wallPositions.back, y: toUnits(8) };
                            } else {
                                position = {
                                    x: wallPositions.back.x + toUnits((cameraCount - 1) * 3),
                                    y: toUnits(8),
                                    z: wallPositions.back.z
                                };
                            }
                            cameraCount++;
                            break;
                            
                        case 'speaker':
                            const corners = [
                                { x: toUnits(roomDims.length/2 - 2), z: toUnits(roomDims.width/2 - 2) },
                                { x: -toUnits(roomDims.length/2 - 2), z: toUnits(roomDims.width/2 - 2) },
                                { x: toUnits(roomDims.length/2 - 2), z: -toUnits(roomDims.width/2 - 2) },
                                { x: -toUnits(roomDims.length/2 - 2), z: -toUnits(roomDims.width/2 - 2) }
                            ];
                            if (speakerCount < corners.length) {
                                position = { ...corners[speakerCount], y: toUnits(7) };
                            } else {
                                position = {
                                    x: toUnits((speakerCount - 4) * 3),
                                    y: toUnits(7),
                                    z: wallPositions.front.z
                                };
                            }
                            speakerCount++;
                            break;
                            
                        case 'microphone':
                            position = {
                                x: toUnits((microphoneCount - 1) * 4),
                                y: 0,
                                z: toUnits(2)
                            };
                            microphoneCount++;
                            break;
                            
                        case 'control_system':
                        case 'processor':
                        case 'amplifier':
                        case 'switcher':
                        case 'recorder':
                        case 'interface':
                            // Place in equipment rack area
                            position = {
                                x: wallPositions.left.x,
                                y: toUnits(3 + (index % 5) * 0.5),
                                z: toUnits(-roomDims.width/4 + (Math.floor(index/5) * 2))
                            };
                            break;
                            
                        default:
                            // Default positioning
                            position = {
                                x: toUnits((index % 4 - 2) * 3),
                                y: toUnits(1),
                                z: toUnits(roomDims.width/4)
                            };
                    }
                    
                    equipment.position.set(position.x, position.y, position.z);
                    equipment.castShadow = true;
                    equipment.receiveShadow = true;
                });
            }

            function setupCameraControls() {
                let isDragging = false;
                let previousMousePosition = { x: 0, y: 0 };
                
                renderer.domElement.addEventListener('mousedown', (event) => {
                    isDragging = true;
                    previousMousePosition = { x: event.clientX, y: event.clientY };
                });
                
                renderer.domElement.addEventListener('mousemove', (event) => {
                    if (!isDragging) return;
                    
                    const deltaMove = {
                        x: event.clientX - previousMousePosition.x,
                        y: event.clientY - previousMousePosition.y
                    };
                    
                    const deltaRotationQuaternion = new THREE.Quaternion()
                        .setFromEuler(new THREE.Euler(
                            toRadians(deltaMove.y * 0.5),
                            toRadians(deltaMove.x * 0.5),
                            0,
                            'XYZ'
                        ));
                    
                    camera.quaternion.multiplyQuaternions(deltaRotationQuaternion, camera.quaternion);
                    previousMousePosition = { x: event.clientX, y: event.clientY };
                });
                
                renderer.domElement.addEventListener('mouseup', () => {
                    isDragging = false;
                });
                
                renderer.domElement.addEventListener('wheel', (event) => {
                    const zoomIntensity = 0.1;
                    const zoom = event.deltaY > 0 ? 1 + zoomIntensity : 1 - zoomIntensity;
                    
                    camera.position.multiplyScalar(zoom);
                    camera.position.clampLength(toUnits(5), toUnits(100));
                });
                
                renderer.domElement.addEventListener('click', onMouseClick);
            }

            function onMouseClick(event) {
                const rect = renderer.domElement.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                
                raycaster.setFromCamera(mouse, camera);
                
                const equipmentGroup = scene.getObjectByName('equipmentGroup');
                if (!equipmentGroup) return;
                
                const intersects = raycaster.intersectObjects(equipmentGroup.children, true);
                
                if (intersects.length > 0) {
                    let targetObject = intersects[0].object;
                    while (targetObject.parent && !targetObject.userData.id) {
                        targetObject = targetObject.parent;
                    }
                    
                    selectEquipment(targetObject);
                }
            }

            function selectEquipment(equipmentObject) {
                // Clear previous selection
                if (selectedObject) {
                    selectedObject.traverse((child) => {
                        if (child.material && child.material.emissive) {
                            child.material.emissive.setHex(0x000000);
                        }
                    });
                }
                
                selectedObject = equipmentObject;
                
                // Highlight selected object
                if (selectedObject) {
                    selectedObject.traverse((child) => {
                        if (child.material && child.material.emissive) {
                            child.material.emissive.setHex(0x444444);
                        }
                    });
                    
                    updateSelectedItemInfo(selectedObject.userData);
                    updateEquipmentListSelection(selectedObject.userData.id);
                }
            }

            function updateEquipmentList() {
                const listContainer = document.getElementById('equipmentList');
                listContainer.innerHTML = '';
                
                avEquipment.forEach(item => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'equipment-item';
                    itemDiv.dataset.itemId = item.id;
                    
                    itemDiv.innerHTML = `
                        <div class="equipment-name">${item.name}</div>
                        <div class="equipment-details">
                            ${item.brand} | $${item.price.toLocaleString()}
                            ${item.original_quantity > 1 ? ` | Instance ${item.instance}/${item.original_quantity}` : ''}
                        </div>
                    `;
                    
                    itemDiv.addEventListener('click', () => {
                        const equipmentGroup = scene.getObjectByName('equipmentGroup');
                        if (equipmentGroup) {
                            const equipmentObject = equipmentGroup.getObjectByName(`equipment_${item.id}`);
                            if (equipmentObject) {
                                selectEquipment(equipmentObject);
                                zoomToObject(equipmentObject);
                            }
                        }
                    });
                    
                    listContainer.appendChild(itemDiv);
                });
            }

            function updateEquipmentListSelection(itemId) {
                document.querySelectorAll('.equipment-item').forEach(item => {
                    item.classList.remove('selected-item');
                });
                
                const selectedItem = document.querySelector(`[data-item-id="${itemId}"]`);
                if (selectedItem) {
                    selectedItem.classList.add('selected-item');
                }
            }

            function updateSelectedItemInfo(item) {
                const infoDiv = document.getElementById('selectedItemInfo');
                if (!item) {
                    infoDiv.innerHTML = '<strong>Click an object or list item for details</strong>';
                    return;
                }
                
                const specs = item.specs || {};
                let specsHtml = '';
                
                Object.keys(specs).forEach(key => {
                    const value = specs[key];
                    if (value && typeof value !== 'object') {
                        specsHtml += `<div style="font-size: 11px; color: #aaa;">${key}: ${value}</div>`;
                    }
                });
                
                infoDiv.innerHTML = `
                    <div style="color: #4FC3F7; font-weight: bold; margin-bottom: 8px;">${item.name}</div>
                    <div style="font-size: 12px; color: #ccc;">Brand: ${item.brand}</div>
                    <div style="font-size: 12px; color: #ccc;">Price: $${item.price.toLocaleString()}</div>
                    <div style="font-size: 12px; color: #ccc;">Type: ${item.type}</div>
                    ${item.original_quantity > 1 ? `<div style="font-size: 12px; color: #ccc;">Instance: ${item.instance}/${item.original_quantity}</div>` : ''}
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #444;">
                        ${specsHtml || '<div style="font-size: 11px; color: #888;">No specifications available</div>'}
                    </div>
                `;
            }

            function setView(viewType, animate = true, buttonElement) {
                // Update active button
                document.querySelectorAll('.control-btn').forEach(btn => btn.classList.remove('active'));
                if (buttonElement) buttonElement.classList.add('active');
                
                const roomCenter = new THREE.Vector3(0, toUnits(roomDims.height/2), 0);
                let targetPosition;
                
                switch(viewType) {
                    case 'overview':
                        targetPosition = new THREE.Vector3(
                            toUnits(roomDims.length * 0.8),
                            toUnits(roomDims.height * 1.2),
                            toUnits(roomDims.width * 0.8)
                        );
                        break;
                    case 'front':
                        targetPosition = new THREE.Vector3(0, toUnits(roomDims.height/2), toUnits(roomDims.width));
                        break;
                    case 'side':
                        targetPosition = new THREE.Vector3(toUnits(roomDims.length), toUnits(roomDims.height/2), 0);
                        break;
                    case 'top':
                        targetPosition = new THREE.Vector3(0, toUnits(roomDims.height * 1.5), 0);
                        break;
                }
                
                if (animate) {
                    animateCamera(targetPosition, roomCenter);
                } else {
                    camera.position.copy(targetPosition);
                    camera.lookAt(roomCenter);
                }
            }

            function animateCamera(targetPosition, targetLookAt) {
                const startPosition = camera.position.clone();
                const startTime = Date.now();
                const duration = 1500;
                
                function updateCamera() {
                    const elapsed = Date.now() - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3); // Ease out cubic
                    
                    camera.position.lerpVectors(startPosition, targetPosition, eased);
                    camera.lookAt(targetLookAt);
                    
                    if (progress < 1) {
                        requestAnimationFrame(updateCamera);
                    }
                }
                
                updateCamera();
            }

            function zoomToSelected() {
                if (!selectedObject) {
                    alert('Please select an equipment item first');
                    return;
                }
                
                zoomToObject(selectedObject);
            }

            function zoomToObject(object) {
                const box = new THREE.Box3().setFromObject(object);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());
                
                const maxDim = Math.max(size.x, size.y, size.z);
                const distance = maxDim * 3;
                
                const targetPosition = new THREE.Vector3(
                    center.x + distance,
                    center.y + distance * 0.7,
                    center.z + distance
                );
                
                animateCamera(targetPosition, center);
            }

            function toggleWireframe() {
                wireframeMode = !wireframeMode;
                
                scene.traverse((child) => {
                    if (child.isMesh && child.material) {
                        if (Array.isArray(child.material)) {
                            child.material.forEach(mat => {
                                mat.wireframe = wireframeMode;
                            });
                        } else {
                            child.material.wireframe = wireframeMode;
                        }
                    }
                });
            }

            function setLighting(type, buttonElement) {
                // Update active button
                document.querySelectorAll('.lighting-btn').forEach(btn => btn.classList.remove('active'));
                if (buttonElement) buttonElement.classList.add('active');
                
                switch(type) {
                    case 'default':
                        ambientLight.intensity = 0.4;
                        directionalLight1.intensity = 0.8;
                        directionalLight2.intensity = 0.3;
                        directionalLight1.color.setHex(0xFFF8DC);
                        directionalLight2.color.setHex(0xE6F3FF);
                        break;
                    case 'warm':
                        ambientLight.intensity = 0.3;
                        directionalLight1.intensity = 0.9;
                        directionalLight2.intensity = 0.2;
                        directionalLight1.color.setHex(0xFFE4B5);
                        directionalLight2.color.setHex(0xFFD700);
                        break;
                    case 'cool':
                        ambientLight.intensity = 0.5;
                        directionalLight1.intensity = 0.7;
                        directionalLight2.intensity = 0.4;
                        directionalLight1.color.setHex(0xE6F3FF);
                        directionalLight2.color.setHex(0xB0E0E6);
                        break;
                    case 'dramatic':
                        ambientLight.intensity = 0.1;
                        directionalLight1.intensity = 1.2;
                        directionalLight2.intensity = 0.1;
                        directionalLight1.color.setHex(0xFFFFFF);
                        directionalLight2.color.setHex(0x404040);
                        break;
                    case 'presentation':
                        ambientLight.intensity = 0.6;
                        directionalLight1.intensity = 0.5;
                        directionalLight2.intensity = 0.5;
                        directionalLight1.color.setHex(0xF5F5DC);
                        directionalLight2.color.setHex(0xF0F8FF);
                        break;
                }
            }

            function toRadians(degrees) {
                return degrees * (Math.PI / 180);
            }

            function animate() {
                animationId = requestAnimationFrame(animate);
                renderer.render(scene, camera);
            }

            // Handle window resize
            window.addEventListener('resize', () => {
                const container = document.getElementById('container');
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            });

            // Initialize the scene
            init();
        </script>
    </body>
    </html>
    """
    
    components.html(html_content, height=650)

# --- Main Application ---
def main():
    # Initialize session state for all generated content
    if 'boq_items' not in st.session_state:
        st.session_state.boq_items = []
    if 'boq_content' not in st.session_state:
        st.session_state.boq_content = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    
    # Load and validate data
    product_df, guidelines, data_issues = load_and_validate_data()
    
    # Display data quality status
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=len(data_issues) > 3):
            for issue in data_issues:
                st.warning(issue)
    
    if product_df is None:
        st.error("Cannot load product catalog. Please check data files.")
        return
    
    # Setup Gemini
    model = setup_gemini()
    if not model:
        return
    
    # Create professional header
    project_id, quote_valid_days = create_project_header()
    
    # Sidebar for project settings
    with st.sidebar:
        st.header("Project Configuration")
        
        client_name = st.text_input("Client Name", value="", key="client_name_input")
        project_name = st.text_input("Project Name", value="", key="project_name_input")
        
        # Currency selection
        currency = st.selectbox("Currency", ["USD", "INR"], index=1, key="currency_select")
        st.session_state['currency'] = currency  # Store in session state
        
        st.markdown("---")
        
        room_type = st.selectbox(
            "Primary Space Type:",
            list(ROOM_SPECS.keys()), key="room_type_select"
        )
        
        budget_tier = st.select_slider(
            "Budget Tier:",
            options=["Economy", "Standard", "Premium", "Enterprise"],
            value="Standard", key="budget_tier_slider"
        )
        
        # Display room specifications
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Typical area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display size: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
        st.caption(f"Budget range: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}")
    
    # Main content areas
    tab1, tab2, tab3, tab4 = st.tabs(["Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])
    
    with tab1:
        room_area, ceiling_height = create_room_calculator()
        
    with tab2:
        features = st.text_area(
            "Specific Requirements & Features:",
            placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified, recording capability'",
            height=100, key="features_text_area"
        )
        
        technical_reqs = create_advanced_requirements()
    
    with tab3:
        st.subheader("BOQ Generation")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("Generate Professional BOQ", type="primary", use_container_width=True, key="generate_boq_button"):
                generate_boq(model, product_df, guidelines, room_type, budget_tier, features, 
                             technical_reqs, room_area)
        
        with col2:
            st.markdown("**Product Stats:**")
            st.metric("Total Products", len(product_df))
            st.metric("Brands", product_df['brand'].nunique())
            if 'price' in product_df.columns:
                try:
                    numeric_prices = pd.to_numeric(product_df['price'], errors='coerce')
                    valid_prices = numeric_prices[numeric_prices > 0]
                    avg_price_usd = valid_prices.mean() if len(valid_prices) > 0 else None
                    
                    if avg_price_usd and not pd.isna(avg_price_usd):
                        display_currency = st.session_state.get('currency', 'USD')
                        
                        if display_currency == "INR":
                            avg_price_inr = convert_currency(avg_price_usd, "INR")
                            st.metric("Avg Price", format_currency(avg_price_inr, "INR"))
                        else:
                            st.metric("Avg Price", format_currency(avg_price_usd, "USD"))
                    else:
                        st.metric("Avg Price", "N/A")
                except Exception:
                    st.metric("Avg Price", "N/A")
        
        # Display results from session_state.
        if st.session_state.boq_content or st.session_state.boq_items:
            st.markdown("---")
            display_boq_results(
                st.session_state.boq_content,
                st.session_state.validation_results,
                project_id,
                quote_valid_days,
                product_df
            )
    
    with tab4:
        create_3d_visualization()

def generate_boq(model, product_df, guidelines, room_type, budget_tier, features, 
                 technical_reqs, room_area):
    """Enhanced BOQ generation that saves results to session_state."""
    
    with st.spinner("Engineering professional BOQ with technical validation..."):
        
        # Create enhanced prompt
        prompt = create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, 
                                        features, technical_reqs, room_area)
        
        try:
            # Generate BOQ with retry logic
            response = generate_with_retry(model, prompt)
            
            if response:
                boq_content = response.text
                
                # Extract structured data
                boq_items = extract_boq_items_from_response(boq_content, product_df)
                
                # Validate BOQ
                validator = BOQValidator(ROOM_SPECS, product_df)
                issues, warnings = validator.validate_technical_requirements(
                    boq_items, room_type, room_area
                )
                
                # Add AI-powered AVIXA compliance validation
                avixa_warnings = validate_against_avixa(model, guidelines, boq_items)
                warnings.extend(avixa_warnings)
                
                validation_results = {"issues": issues, "warnings": warnings}
                
                # Store all generated content in session_state to persist across reruns.
                st.session_state.boq_content = boq_content
                st.session_state.boq_items = boq_items
                st.session_state.validation_results = validation_results
                
                if boq_items:
                    st.success(f"✅ Successfully generated and loaded {len(boq_items)} items!")
                else:
                    st.warning("⚠️ BOQ generated, but no items could be parsed. Check the raw output.")

        except Exception as e:
            st.error(f"BOQ generation failed: {str(e)}")
            with st.expander("Technical Details"):
                st.code(str(e))

def create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Create comprehensive prompt for BOQ generation."""
    
    room_spec = ROOM_SPECS[room_type]
    # Provide a sample of the catalog instead of the full CSV to avoid overly large prompts
    product_catalog_string = product_df.head(100).to_csv(index=False)
    
    prompt = f"""
You are a Professional AV Systems Engineer with 15+ years experience. Create a production-ready BOQ.

**PROJECT SPECIFICATIONS:**
- Room Type: {room_type}
- Room Area: {room_area:.0f} sq ft
- Budget Tier: {budget_tier}
- Special Requirements: {features}
- Infrastructure: {technical_reqs}

**TECHNICAL CONSTRAINTS & GUIDELINES:**
- Adhere to the provided AVIXA standards for all design choices.
- Display size range: {room_spec['recommended_display_size'][0]}"-{room_spec['recommended_display_size'][1]}"
- Viewing distance: {room_spec['viewing_distance_ft'][0]}-{room_spec['viewing_distance_ft'][1]} ft
- Audio coverage: {room_spec['audio_coverage']}
- Budget target: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}

**MANDATORY REQUIREMENTS:**
1. ONLY use products from the provided product catalog sample. If a suitable product is not in the sample, note it.
2. Verify all components are compatible (e.g., mounts fit displays).
3. Include appropriate mounting hardware, cabling (HDMI, USB, Ethernet), and power distribution.
4. Add a line item for 'Installation & Commissioning Labor' as 15% of the total hardware cost.
5. Add a line item for 'System Warranty (3 Years)' as 5% of the total hardware cost.
6. Add a line item for 'Project Contingency' as 10% of the total hardware cost.

**OUTPUT FORMAT REQUIREMENT:**
- Start with a brief 2-3 sentence 'System Design Summary'.
- Then, provide the BOQ in a clear markdown table with the following columns:
| Category | Brand | Product Name | Quantity | Unit Price (USD) | Total (USD) |

**PRODUCT CATALOG SAMPLE:**
{product_catalog_string}

**AVIXA GUIDELINES:**
{guidelines}

Generate the BOQ now:
"""
    
    return prompt

# Run the application
if __name__ == "__main__":
    main()
