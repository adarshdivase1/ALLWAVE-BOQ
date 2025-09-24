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
        "area_sqft": (40, 80), "recommended_display_size": (32, 43), "viewing_distance_ft": (4, 6),
        "audio_coverage": "Near-field single speaker", "camera_type": "Fixed wide-angle",
        "power_requirements": "Standard 15A circuit", "network_ports": 1, "typical_budget_range": (3000, 8000),
        "furniture_config": "small_huddle", "table_size": [4, 2.5], "chair_count": 3, "chair_arrangement": "casual"
    },
    "Medium Huddle Room (4-6 People)": {
        "area_sqft": (80, 150), "recommended_display_size": (43, 55), "viewing_distance_ft": (6, 10),
        "audio_coverage": "Near-field stereo", "camera_type": "Fixed wide-angle with auto-framing",
        "power_requirements": "Standard 15A circuit", "network_ports": 2, "typical_budget_range": (8000, 18000),
        "furniture_config": "medium_huddle", "table_size": [6, 3], "chair_count": 6, "chair_arrangement": "round_table"
    },
    "Standard Conference Room (6-8 People)": {
        "area_sqft": (150, 250), "recommended_display_size": (55, 65), "viewing_distance_ft": (8, 12),
        "audio_coverage": "Room-wide with ceiling mics", "camera_type": "PTZ or wide-angle with tracking",
        "power_requirements": "20A dedicated circuit recommended", "network_ports": 2, "typical_budget_range": (15000, 30000),
        "furniture_config": "standard_conference", "table_size": [10, 4], "chair_count": 8, "chair_arrangement": "rectangular"
    },
    "Large Conference Room (8-12 People)": {
        "area_sqft": (250, 400), "recommended_display_size": (65, 75), "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed ceiling mics with expansion", "camera_type": "PTZ with presenter tracking",
        "power_requirements": "20A dedicated circuit", "network_ports": 3, "typical_budget_range": (25000, 50000),
        "furniture_config": "large_conference", "table_size": [14, 5], "chair_count": 12, "chair_arrangement": "rectangular"
    },
    "Executive Boardroom (10-16 People)": {
        "area_sqft": (350, 600), "recommended_display_size": (75, 86), "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling and table mics", "camera_type": "Multiple cameras with auto-switching",
        "power_requirements": "30A dedicated circuit", "network_ports": 4, "typical_budget_range": (50000, 100000),
        "furniture_config": "executive_boardroom", "table_size": [16, 6], "chair_count": 16, "chair_arrangement": "oval"
    },
    "Training Room (15-25 People)": {
        "area_sqft": (300, 500), "recommended_display_size": (65, 86), "viewing_distance_ft": (10, 18),
        "audio_coverage": "Distributed with wireless mic support", "camera_type": "Fixed or PTZ for presenter tracking",
        "power_requirements": "20A circuit with UPS backup", "network_ports": 3, "typical_budget_range": (30000, 70000),
        "furniture_config": "training_room", "table_size": [8, 4], "chair_count": 25, "chair_arrangement": "classroom"
    },
    "Large Training/Presentation Room (25-40 People)": {
        "area_sqft": (500, 800), "recommended_display_size": (86, 98), "viewing_distance_ft": (15, 25),
        "audio_coverage": "Full distributed system with handheld mics", "camera_type": "Multiple PTZ cameras",
        "power_requirements": "30A circuit with UPS backup", "network_ports": 4, "typical_budget_range": (60000, 120000),
        "furniture_config": "large_training", "table_size": [10, 4], "chair_count": 40, "chair_arrangement": "theater"
    },
    "Multipurpose Event Room (40+ People)": {
        "area_sqft": (800, 1500), "recommended_display_size": (98, 110), "viewing_distance_ft": (20, 35),
        "audio_coverage": "Professional distributed PA system", "camera_type": "Professional multi-camera setup",
        "power_requirements": "Multiple 30A circuits", "network_ports": 6, "typical_budget_range": (100000, 250000),
        "furniture_config": "multipurpose_event", "table_size": [12, 6], "chair_count": 50, "chair_arrangement": "flexible"
    },
    "Video Production Studio": {
        "area_sqft": (200, 400), "recommended_display_size": (32, 55), "viewing_distance_ft": (6, 12),
        "audio_coverage": "Professional studio monitors", "camera_type": "Professional broadcast cameras",
        "power_requirements": "Multiple 20A circuits", "network_ports": 4, "typical_budget_range": (75000, 200000),
        "furniture_config": "production_studio", "table_size": [8, 4], "chair_count": 6, "chair_arrangement": "production"
    },
    "Telepresence Suite": {
        "area_sqft": (150, 300), "recommended_display_size": (65, 98), "viewing_distance_ft": (8, 14),
        "audio_coverage": "High-fidelity spatial audio", "camera_type": "Multiple high-res cameras with AI tracking",
        "power_requirements": "20A dedicated circuit", "network_ports": 3, "typical_budget_range": (80000, 180000),
        "furniture_config": "telepresence", "table_size": [12, 4], "chair_count": 8, "chair_arrangement": "telepresence"
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

# --- Interactive BOQ Editor Functions ---
def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items in BOQ."
        return
    
    # Generate updated BOQ content from current items
    boq_content = "## Bill of Quantities\n\n"
    boq_content += "| Category | Brand | Product Name | Quantity | Unit Price (USD) | Total (USD) |\n"
    boq_content += "|----------|--------|--------------|----------|------------------|-------------|\n"
    
    total_cost = 0
    for item in st.session_state.boq_items:
        quantity = int(item.get('quantity', 1))
        price = float(item.get('price', 0))
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
    
    item_count = len(st.session_state.get('boq_items', []))
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
    
    # Display BOQ content from session state
    st.markdown(st.session_state.get('boq_content', "No BOQ generated yet."))
    
    # Add download functionality
    if st.session_state.get('boq_items'):
        col1, col2 = st.columns(2)
        with col1:
            doc_content = generate_professional_boq_document(
                {'design_summary': "See table below."},
                {'project_id': project_id, 'quote_valid_days': quote_valid_days},
                validation_results or {}
            )
            final_doc = doc_content + "\n" + st.session_state.boq_content
            
            st.download_button(
                label="Download BOQ (Markdown)",
                data=final_doc,
                file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )
        
        with col2:
            df_to_download = pd.DataFrame(st.session_state.boq_items)
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

    # Add interactive BOQ editor
    st.markdown("---")
    create_interactive_boq_editor(product_df)

def create_interactive_boq_editor(product_df):
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    
    item_count = len(st.session_state.get('boq_items', []))
    total_cost = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in st.session_state.get('boq_items', []))
    currency = st.session_state.get('currency', 'USD')
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Items in BOQ", item_count)
    if currency == 'INR':
        display_total = convert_currency(total_cost, 'INR')
        col2.metric("Subtotal", format_currency(display_total, 'INR'))
    else:
        col2.metric("Subtotal", format_currency(total_cost, 'USD'))
    
    with col3:
        if st.button("🔄 Refresh BOQ Display", help="Update the main BOQ display with any edits"):
            update_boq_content_with_current_items()
            st.success("BOQ display refreshed!")
            st.rerun()

    if product_df is None:
        st.error("Product catalog not loaded. Editor disabled.")
        return

    tabs = st.tabs(["Edit Current BOQ", "Add Products", "Product Search"])
    
    with tabs[0]:
        edit_current_boq(currency)
    
    with tabs[1]:
        add_products_interface(product_df, currency)
    
    with tabs[2]:
        product_search_interface(product_df, currency)

def edit_current_boq(currency):
    """Interface for editing current BOQ items."""
    if not st.session_state.get('boq_items'):
        st.info("No items in BOQ to edit. Add items from the other tabs.")
        return

    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        with st.expander(f"{item.get('category', 'N/A')} - {str(item.get('name', 'N/A'))[:60]}"):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                item['name'] = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                item['brand'] = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")
            
            with col2:
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_cat_idx = category_list.index(item.get('category', 'General')) if item.get('category') in category_list else 6
                item['category'] = st.selectbox("Category", category_list, index=current_cat_idx, key=f"cat_{i}")
            
            with col3:
                item['quantity'] = st.number_input("Quantity", min_value=1, value=int(item.get('quantity', 1)), key=f"qty_{i}")
                
                base_price = float(item.get('price', 0))
                if currency == 'INR':
                    display_price = convert_currency(base_price, 'INR')
                    new_display_price = st.number_input(f"Price ({currency})", min_value=0.0, value=display_price, format="%.2f", key=f"price_{i}")
                    item['price'] = new_display_price / get_usd_to_inr_rate()
                else:
                    new_price = st.number_input(f"Price ({currency})", min_value=0.0, value=base_price, format="%.2f", key=f"price_{i}")
                    item['price'] = new_price

            with col4:
                total = item['price'] * item['quantity']
                if currency == 'INR':
                    st.metric("Total", format_currency(convert_currency(total, 'INR'), 'INR'), label_visibility="hidden")
                else:
                    st.metric("Total", format_currency(total, 'USD'), label_visibility="hidden")
                
                if st.button("Remove", key=f"remove_{i}"):
                    items_to_remove.append(i)

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()

def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ."""
    st.write("**Add Products from Catalog**")
    
    categories = ['All'] + sorted(list(product_df['category'].unique()))
    selected_category = st.selectbox("Filter by Category", categories, key="add_cat_filter")

    if selected_category != 'All':
        filtered_df = product_df[product_df['category'] == selected_category]
    else:
        filtered_df = product_df

    product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
    if not product_options:
        st.warning("No products found for this category.")
        return

    col1, col2 = st.columns([3,1])
    with col1:
        selected_product_str = st.selectbox("Select Product", product_options, key="add_prod_select")
    with col2:
        quantity = st.number_input("Quantity", min_value=1, value=1, key="add_prod_qty")
        
    selected_product = filtered_df[filtered_df.apply(lambda row: f"{row['brand']} - {row['name']}" == selected_product_str, axis=1)].iloc[0]

    if st.button("Add to BOQ", type="primary"):
        new_item = selected_product.to_dict()
        new_item['quantity'] = quantity
        new_item['matched'] = True
        st.session_state.boq_items.append(new_item)
        st.success(f"Added {quantity}x {selected_product['name']} to BOQ.")
        st.rerun()

def product_search_interface(product_df, currency):
    """Advanced product search interface."""
    st.write("**Search Product Catalog**")
    search_term = st.text_input("Search by name, brand, or features", key="search_input")

    if search_term:
        search_cols = ['name', 'brand', 'features']
        mask = product_df[search_cols].apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        results = product_df[mask]
        
        st.write(f"Found {len(results)} matching products:")
        for i, row in results.head(5).iterrows(): # Show top 5 results
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.markdown(f"**{row['brand']} - {row['name']}**")
                    st.caption(f"Category: {row['category']} | Features: {str(row['features'])[:100]}...")
                with col2:
                    price = float(row['price'])
                    if currency == 'INR':
                        st.metric("Price", format_currency(convert_currency(price, 'INR'), 'INR'))
                    else:
                        st.metric("Price", format_currency(price, 'USD'))
                with col3:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        new_item = row.to_dict()
                        new_item['quantity'] = add_qty
                        new_item['matched'] = True
                        st.session_state.boq_items.append(new_item)
                        st.success(f"Added {add_qty}x {row['name']} to BOQ.")
                        st.rerun()

# --- Visualization Utility Functions ---
def map_equipment_type(category, product_name="", brand=""):
    """Enhanced mapping function that considers both category and product name."""
    search_text = f"{category} {product_name}".lower()
    
    if any(term in search_text for term in ['display', 'monitor', 'screen', 'projector', 'tv']):
        return 'display'
    elif any(term in search_text for term in ['speaker', 'soundbar', 'amplifier']):
        return 'audio_speaker'
    elif any(term in search_text for term in ['microphone', 'mic']):
        return 'audio_microphone'
    elif any(term in search_text for term in ['camera', 'video conferencing', 'codec', 'video bar']):
        return 'camera'
    elif any(term in search_text for term in ['switch', 'network', 'router']):
        return 'network_switch'
    elif any(term in search_text for term in ['control panel', 'touch panel', 'scheduler']):
        return 'control_panel'
    elif any(term in search_text for term in ['control', 'processor', 'matrix']):
        return 'control'
    elif 'service' in search_text or 'labor' in search_text:
        return 'service'
    else:
        return 'generic_equipment'

def get_equipment_specs(equipment_type, product_name=""):
    """Get equipment dimensions in feet (width, height, depth)."""
    specs = {
        'display': [4, 2.25, 0.2], 'audio_speaker': [0.8, 1.2, 0.8], 'audio_microphone': [0.4, 0.1, 0.4],
        'camera': [0.8, 0.4, 0.5], 'network_switch': [1.5, 0.15, 0.8], 'control_panel': [0.8, 0.5, 0.1],
        'control': [1.5, 0.3, 1.0], 'generic_equipment': [1, 1, 1], 'service': [0, 0, 0]
    }
    base_spec = specs.get(equipment_type, [1, 1, 1])

    if equipment_type == 'display' and product_name:
        size_match = re.search(r'(\d{2,3})', product_name)
        if size_match:
            size_inches = int(size_match.group(1))
            width_ft = (size_inches * 0.871) / 12
            height_ft = (size_inches * 0.490) / 12
            return [width_ft, height_ft, 0.25]
    return base_spec

# --- Final 3D Visualization Function ---
def create_3d_visualization():
    """Create an interactive, realistic 3D room visualization with auto-zoom functionality."""
    st.subheader("3D Room Visualization")

    equipment_data = st.session_state.get('boq_items', [])

    if not equipment_data:
        st.info("No BOQ items to visualize. Generate a BOQ first or add items manually.")
        return

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
                'id': len(js_equipment) + 1, 'type': equipment_type, 'name': item.get('name', 'Unknown'),
                'brand': item.get('brand', 'Unknown'), 'price': float(item.get('price', 0)),
                'instance': i + 1, 'original_quantity': quantity, 'specs': specs
            })

    if not js_equipment:
        st.warning("No visualizable equipment found in BOQ.")
        return

    room_length = st.session_state.get('room_length_input', 24.0)
    room_width = st.session_state.get('room_width_input', 16.0)
    room_height = st.session_state.get('ceiling_height_input', 9.0)
    room_type_str = st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
            #container {{ width: 100%; height: 650px; position: relative; cursor: grab; }}
            #container:active {{ cursor: grabbing; }}
            #info-panel {{ 
                position: absolute; top: 15px; left: 15px; color: #ffffff; 
                background: linear-gradient(135deg, rgba(0,0,0,0.9), rgba(20,20,20,0.8));
                padding: 15px; border-radius: 12px; backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1); width: 320px;
                display: flex; flex-direction: column; max-height: 620px;
            }}
            .equipment-manifest {{ flex-grow: 1; overflow-y: auto; margin-top: 10px; }}
            .equipment-item {{ 
                margin: 4px 0; padding: 8px; background: rgba(255,255,255,0.05); 
                border-radius: 4px; border-left: 3px solid transparent; cursor: pointer; transition: all 0.2s ease;
            }}
            .equipment-item:hover {{ background: rgba(255,255,255,0.15); }}
            .equipment-item.selected-item {{
                background: rgba(79, 195, 247, 0.2);
                border-left: 3px solid #4FC3F7;
            }}
            .equipment-name {{ color: #FFD54F; font-weight: bold; font-size: 13px; }}
            .equipment-details {{ color: #ccc; font-size: 11px; }}
            #selectedItemInfo {{
                padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2); margin-top: 10px;
                min-height: 60px;
            }}
            #controls {{
                position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.8); padding: 10px; border-radius: 25px;
                display: flex; gap: 10px; backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1); z-index: 1000;
            }}
            .control-btn {{
                background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.3);
                color: white; padding: 8px 16px; border-radius: 15px; cursor: pointer;
                transition: all 0.3s ease; font-size: 12px;
            }}
            .control-btn:hover {{ background: rgba(255, 255, 255, 0.3); transform: translateY(-2px); }}
            .control-btn.active {{ background: #4FC3F7; border-color: #03A9F4; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="info-panel">
                <div>
                    <h3 style="margin-top: 0; color: #4FC3F7; font-size: 16px;">Equipment Manifest</h3>
                    <div style="font-size: 12px; color: #ccc;">Visualizing {len(js_equipment)} equipment instances</div>
                    <div style="font-size: 11px; color: #888; margin-top: 5px;">Click items below to auto-zoom</div>
                </div>
                <div class="equipment-manifest" id="equipmentList"></div>
                <div id="selectedItemInfo">
                    <strong>Click an object or list item for details</strong>
                </div>
            </div>
             <div id="controls">
                <button class="control-btn active" onclick="setView('overview', true, this)">🏠 Overview</button>
                <button class="control-btn" onclick="setView('front', true, this)">📺 Front</button>
                <button class="control-btn" onclick="setView('side', true, this)">📐 Side</button>
                <button class="control-btn" onclick="setView('top', true, this)">📊 Top</button>
                <button class="control-btn" onclick="zoomToSelected()">🔍 Zoom Selected</button>
            </div>
        </div>
        
        <script>
            let scene, camera, renderer, raycaster, mouse;
            let animationId, selectedObject = null;
            const toUnits = (feet) => feet * 0.3048;
            const avEquipment = {json.dumps(js_equipment)};
            const roomType = `{room_type_str}`;
            const roomDims = {{
                length: {room_length},
                width: {room_width},
                height: {room_height}
            }};

            function init() {{
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x334455);
                scene.fog = new THREE.Fog(0x334455, toUnits(20), toUnits(100));
                
                const container = document.getElementById('container');
                camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);
                setView('overview', false);
                
                renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer.shadowMap.enabled = true;
                renderer.shadowMap.type = THREE.PCFSoftShadowMap;
                renderer.outputEncoding = THREE.sRGBEncoding;
                renderer.toneMapping = THREE.ACESFilmicToneMapping;
                container.appendChild(renderer.domElement);
                
                raycaster = new THREE.Raycaster();
                mouse = new THREE.Vector2();
                
                createRoom();
                createLighting();
                createRoomFurniture();
                createAllEquipmentObjects();
                setupCameraControls();
                updateEquipmentList();
                animate();
            }}

            function createRoom() {{
                const wallMaterial = new THREE.MeshStandardMaterial({{ color: 0xddeeff, roughness: 0.9 }});
                const floorMaterial = new THREE.MeshStandardMaterial({{ color: 0x6e5a47, roughness: 0.7 }});
                const wallHeight = toUnits(roomDims.height);

                const floor = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)), floorMaterial);
                floor.rotation.x = -Math.PI / 2;
                floor.receiveShadow = true;
                scene.add(floor);

                const backWall = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomDims.length), wallHeight), wallMaterial.clone());
                backWall.position.set(0, wallHeight/2, -toUnits(roomDims.width/2));
                backWall.receiveShadow = true;
                backWall.name = 'backWall';
                scene.add(backWall);

                const leftWall = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomDims.width), wallHeight), wallMaterial.clone());
                leftWall.position.set(-toUnits(roomDims.length/2), wallHeight/2, 0);
                leftWall.rotation.y = Math.PI/2;
                leftWall.receiveShadow = true;
                scene.add(leftWall);
            }}

            function createLighting() {{
                scene.add(new THREE.HemisphereLight(0x8899aa, 0x555555, 0.8));
                const dirLight = new THREE.DirectionalLight(0xffeedd, 0.7);
                dirLight.position.set(toUnits(-5), toUnits(8), toUnits(5));
                dirLight.castShadow = true;
                dirLight.shadow.mapSize.width = 1024;
                dirLight.shadow.mapSize.height = 1024;
                scene.add(dirLight);
            }}

            function getRoomSpecFromType(rt) {{
                const specs = {json.dumps(ROOM_SPECS)};
                return specs[rt] || specs['Standard Conference Room (6-8 People)'];
            }}

            function createRoomFurniture() {{
                const furnitureGroup = new THREE.Group();
                const spec = getRoomSpecFromType(roomType);
                
                const tableMaterial = new THREE.MeshStandardMaterial({{ color: 0x4d3a2a, roughness: 0.6 }});
                const chairMaterial = new THREE.MeshStandardMaterial({{ color: 0x222222, roughness: 0.5 }});

                const safeSpec = {{
                    ...spec,
                    table_size: [
                        Math.min(spec.table_size[0], roomDims.length - 6),
                        Math.min(spec.table_size[1], roomDims.width - 8)
                    ]
                }};
                
                switch(safeSpec.furniture_config) {{
                    case 'small_huddle': 
                    case 'medium_huddle':
                        createHuddleLayout(furnitureGroup, tableMaterial, chairMaterial, safeSpec); break;
                    case 'standard_conference': 
                    case 'large_conference':
                        createConferenceLayout(furnitureGroup, tableMaterial, chairMaterial, safeSpec, false); break;
                    case 'executive_boardroom': 
                        createConferenceLayout(furnitureGroup, tableMaterial, chairMaterial, safeSpec, true); break;
                    case 'training_room': 
                    case 'large_training':
                        createTrainingLayout(furnitureGroup, tableMaterial, chairMaterial, safeSpec); break;
                    case 'telepresence':
                        createTelepresenceLayout(furnitureGroup, tableMaterial, chairMaterial, safeSpec); break;
                    case 'production_studio':
                        createStudioLayout(furnitureGroup, tableMaterial, chairMaterial, safeSpec); break;
                    case 'multipurpose_event':
                        createMultipurposeLayout(furnitureGroup, chairMaterial, safeSpec); break;
                    default: 
                        createConferenceLayout(furnitureGroup, tableMaterial, chairMaterial, safeSpec, false);
                }}
                scene.add(furnitureGroup);
            }}

            function createHuddleLayout(group, tableMaterial, chairMaterial, spec) {{
                const tableWidth = toUnits(Math.min(spec.table_size[0], spec.table_size[1]));
                const table = createRectangularTable(tableWidth, tableWidth * 0.8, toUnits(2.5), tableMaterial);
                group.add(table);

                const chairOrbitRadius = tableWidth / 2 + toUnits(1.8);
                const chairCount = spec.chair_count;
                for (let i = 0; i < chairCount; i++) {{
                    const chair = createChair(chairMaterial);
                    const angle = Math.PI / (chairCount + 1) * (i + 1) + Math.PI / 2;
                    chair.position.x = Math.cos(angle) * chairOrbitRadius;
                    chair.position.z = Math.sin(angle) * (chairOrbitRadius - toUnits(1.0));
                    chair.rotation.y = -angle + Math.PI/2;
                    group.add(chair);
                }}
            }}

            function createConferenceLayout(group, tableMaterial, chairMaterial, spec, isExecutive) {{
                const tableLength = toUnits(spec.table_size[0]);
                const tableWidth = toUnits(spec.table_size[1]);

                const table = createRectangularTable(tableLength, tableWidth, toUnits(2.5), tableMaterial);
                group.add(table);

                let chairsPlaced = 0;
                const chairSpacing = toUnits(3.5);
                const chairsPerSide = Math.floor((tableLength - toUnits(2)) / chairSpacing);
                
                for(let side = 0; side < 2; side++) {{
                    const zPos = (side === 0) ? tableWidth / 2 + toUnits(1.8) : -tableWidth / 2 - toUnits(1.8);
                    const rotation = (side === 0) ? Math.PI : 0;
                    for(let i = 0; i < chairsPerSide; i++) {{
                        if (chairsPlaced >= spec.chair_count) break;
                        const xPos = -tableLength/2 + toUnits(2) + i * chairSpacing;
                        const chair = isExecutive ? createExecutiveChair(chairMaterial) : createChair(chairMaterial);
                        chair.position.set(xPos, 0, zPos);
                        chair.rotation.y = rotation;
                        group.add(chair);
                        chairsPlaced++;
                    }}
                }}
                
                if (chairsPlaced < spec.chair_count) {{
                    const chair = isExecutive ? createExecutiveChair(chairMaterial) : createChair(chairMaterial);
                    chair.position.set(tableLength / 2 + toUnits(2.2), 0, 0);
                    chair.rotation.y = -Math.PI / 2;
                    group.add(chair);
                    chairsPlaced++;
                }}
                if (chairsPlaced < spec.chair_count) {{
                    const chair = isExecutive ? createExecutiveChair(chairMaterial) : createChair(chairMaterial);
                    chair.position.set(-tableLength / 2 - toUnits(2.2), 0, 0);
                    chair.rotation.y = Math.PI / 2;
                    group.add(chair);
                }}
            }}

            function createTelepresenceLayout(group, tableMaterial, chairMaterial, spec) {{
                const tableLength = toUnits(spec.table_size[0] * 0.5);
                const tableWidth = toUnits(spec.table_size[1] * 0.7);
                const angle = Math.PI / 8;

                for (let i = -1; i <= 1; i += 2) {{
                    const tableHalf = createRectangularTable(tableLength, tableWidth, toUnits(2.5), tableMaterial);
                    tableHalf.rotation.y = i * angle;
                    tableHalf.position.x = i * (tableLength / 2) * Math.cos(angle);
                    tableHalf.position.z = i * (tableLength / 2) * Math.sin(angle) - toUnits(2);
                    group.add(tableHalf);
                }}

                const chairCount = spec.chair_count;
                const chairsPerSide = Math.ceil(chairCount / 2);
                const chairSpacing = tableLength / (chairsPerSide);

                for (let i = 0; i < chairCount; i++) {{
                    const side = (i < chairsPerSide) ? -1 : 1;
                    const indexOnSide = (i < chairsPerSide) ? i : i - chairsPerSide;
                    const chair = createExecutiveChair(chairMaterial);
                    const xOffset = (indexOnSide * chairSpacing) - (tableLength/2) + chairSpacing/2;
                    const chairPos = new THREE.Vector3(xOffset, 0, tableWidth/2 + toUnits(1.8));
                    chairPos.applyAxisAngle(new THREE.Vector3(0,1,0), side * angle);
                    chair.position.set(chairPos.x, 0, chairPos.z);
                    chair.position.x += side * (tableLength / 2) * Math.cos(angle);
                    chair.position.z += side * (tableLength / 2) * Math.sin(angle) - toUnits(2);
                    chair.rotation.y = Math.PI - (side * angle);
                    group.add(chair);
                }}
            }}
            
            function createTrainingLayout(group, tableMaterial, chairMaterial, spec) {{
                const chairCount = spec.chair_count;
                const rowSpacing = toUnits(5.5);
                const seatSpacing = toUnits(4.5);
                const startZ = -toUnits(roomDims.width/2) + toUnits(8);
                const maxSeatsPerRow = Math.floor((toUnits(roomDims.length) - toUnits(4)) / seatSpacing);
                if (maxSeatsPerRow === 0) return;
                const numRows = Math.ceil(chairCount / maxSeatsPerRow);

                let chairsPlaced = 0;
                for(let r = 0; r < numRows; r++) {{
                    const seatsInThisRow = Math.min(maxSeatsPerRow, chairCount - chairsPlaced);
                    const rowWidth = (seatsInThisRow - 1) * seatSpacing;
                    for(let s = 0; s < seatsInThisRow; s++) {{
                        const xPos = -rowWidth/2 + s * seatSpacing;
                        const zPos = startZ + r * rowSpacing;
                        if (zPos > toUnits(roomDims.width / 2) - toUnits(2)) continue;

                        const chair = createChair(chairMaterial);
                        chair.position.set(xPos, 0, zPos);
                        chair.rotation.y = Math.PI;
                        group.add(chair);

                        const desk = createStudentDesk(tableMaterial);
                        desk.position.set(xPos, 0, zPos - toUnits(1.5));
                        desk.rotation.y = Math.PI;
                        group.add(desk);
                        chairsPlaced++;
                    }}
                }}
            }}
            
            function createStudioLayout(group, tableMaterial, chairMaterial, spec) {{
                const greenScreenMaterial = new THREE.MeshBasicMaterial({{ color: 0x00ff00 }});
                const backWall = scene.getObjectByName('backWall');
                if (backWall) {{
                    backWall.material = greenScreenMaterial;
                }}
                const presenterDesk = createRectangularTable(toUnits(5), toUnits(2.5), toUnits(2.5), tableMaterial);
                presenterDesk.position.z = -toUnits(roomDims.width/2) + toUnits(4);
                group.add(presenterDesk);
            }}

            function createMultipurposeLayout(group, chairMaterial, spec) {{
                const stacks = 4;
                const chairsPerStack = 10;
                for (let s = 0; s < stacks; s++) {{
                    const stack = new THREE.Group();
                    for (let i = 0; i < chairsPerStack; i++) {{
                        const chair = createChair(chairMaterial);
                        chair.position.y = i * toUnits(0.2);
                        stack.add(chair);
                    }}
                    stack.position.set(-toUnits(roomDims.length/2) + toUnits(2), 0, -toUnits(roomDims.width/2) + toUnits(4) + s * toUnits(3));
                    group.add(stack);
                }}
            }}

            function createChair(material) {{
                const chair = new THREE.Group();
                const seat = new THREE.Mesh(new THREE.BoxGeometry(toUnits(1.5), toUnits(0.2), toUnits(1.5)), material);
                seat.position.y = toUnits(1.5);
                seat.castShadow = true;
                chair.add(seat);
                const back = new THREE.Mesh(new THREE.BoxGeometry(toUnits(1.5), toUnits(2), toUnits(0.2)), material);
                back.position.set(0, toUnits(2.5), toUnits(-0.65));
                back.castShadow = true;
                chair.add(back);
                return chair;
            }}

            function createExecutiveChair(material) {{
                const chair = new THREE.Group();
                const seat = new THREE.Mesh(new THREE.BoxGeometry(toUnits(1.8), toUnits(0.3), toUnits(1.8)), material);
                seat.position.y = toUnits(1.6);
                seat.castShadow = true;
                chair.add(seat);
                const back = new THREE.Mesh(new THREE.BoxGeometry(toUnits(1.8), toUnits(2.5), toUnits(0.3)), material);
                back.position.set(0, toUnits(2.8), toUnits(-0.75));
                back.castShadow = true;
                chair.add(back);
                return chair;
            }}

            function createRectangularTable(length, width, height, material) {{
                const table = new THREE.Group();
                const tableTop = new THREE.Mesh(new THREE.BoxGeometry(length, toUnits(0.2), width), material);
                tableTop.position.y = height;
                tableTop.castShadow = true; tableTop.receiveShadow = true;
                table.add(tableTop);

                const legHeight = height - toUnits(0.1);
                const legSize = toUnits(0.2);
                const legPositions = [
                    {{x: length/2 - legSize*2, z: width/2 - legSize*2}}, {{x: -length/2 + legSize*2, z: width/2 - legSize*2}},
                    {{x: length/2 - legSize*2, z: -width/2 + legSize*2}}, {{x: -length/2 + legSize*2, z: -width/2 + legSize*2}},
                ];
                legPositions.forEach(pos => {{
                    const leg = new THREE.Mesh(new THREE.BoxGeometry(legSize, legHeight, legSize), material);
                    leg.position.set(pos.x, legHeight/2, pos.z);
                    leg.castShadow = true;
                    table.add(leg);
                }});
                return table;
            }}

            function createStudentDesk(material) {{
                const desk = new THREE.Group();
                const deskTop = new THREE.Mesh(new THREE.BoxGeometry(toUnits(3.5), toUnits(0.15), toUnits(1.8)), material);
                deskTop.position.y = toUnits(2.5);
                desk.add(deskTop);
                const legHeight = toUnits(2.4);
                for(let i = -1; i <=1; i+=2) {{
                    const leg = new THREE.Mesh(new THREE.BoxGeometry(toUnits(0.1), legHeight, toUnits(1.6)), material);
                    leg.position.set(i * toUnits(3.5/2 - 0.2), legHeight / 2, 0);
                    desk.add(leg);
                }}
                desk.traverse(obj => {{ if(obj.isMesh) obj.castShadow = true; }});
                return desk;
            }}

            function createAllEquipmentObjects() {{
                avEquipment.forEach((equipment, index) => {{
                    const equipmentObj = createEquipmentObject(equipment);
                    if (equipmentObj) {{
                        equipmentObj.userData = {{ equipment, index }};
                        equipmentObj.name = `equipment_${{index}}`;
                        scene.add(equipmentObj);
                    }}
                }});
            }}

            function createEquipmentObject(equipment) {{
                const size = equipment.specs;
                const material = new THREE.MeshStandardMaterial({{ color: 0x333333, roughness: 0.5, metalness: 0.1 }});
                let object;

                switch(equipment.type) {{
                    case 'display':
                        object = new THREE.Mesh(new THREE.BoxGeometry(toUnits(size[0]), toUnits(size[1]), toUnits(size[2])), material);
                        const screen = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(size[0]*0.95), toUnits(size[1]*0.9)), new THREE.MeshBasicMaterial({{color: 0x1a1a2e}}));
                        screen.position.z = toUnits(size[2]/2 + 0.01);
                        object.add(screen);
                        break;
                    case 'camera':
                        object = new THREE.Mesh(new THREE.CylinderGeometry(toUnits(size[0]/2), toUnits(size[0]/2), toUnits(size[2]), 16), material);
                        object.rotation.x = Math.PI / 2;
                        break;
                    default:
                        object = new THREE.Mesh(new THREE.BoxGeometry(toUnits(size[0]), toUnits(size[1]), toUnits(size[2])), material);
                }}
                object.traverse(obj => {{ if(obj.isMesh) obj.castShadow = true; }});
                const pos = getSmartPosition(equipment.type, equipment.instance - 1, equipment.original_quantity, size);
                object.position.set(pos.x, pos.y, pos.z);
                return object;
            }}

            function getSmartPosition(type, instanceIndex, quantity, size) {{
                let x_ft = 0, y_ft = 0, z_ft = 0;
                const spacing_ft = Math.max(size[0] + 1, 1.5);

                switch (type) {{
                    case 'display':
                        x_ft = -(quantity - 1) * spacing_ft / 2 + (instanceIndex * spacing_ft);
                        y_ft = roomDims.height * 0.55;
                        z_ft = -roomDims.width / 2 + 0.3;
                        break;
                    case 'camera':
                        y_ft = toUnits(size[1]) / 2; // on top of the display
                        x_ft = -(quantity - 1) * 5 / 2 + (instanceIndex * 5);
                        z_ft = -roomDims.width / 2 + 0.3;
                        y_ft = roomDims.height * 0.55 + toUnits(size[1]) + 0.2;
                        break;
                    case 'audio_speaker':
                        const positions = [
                            [-roomDims.length/4, roomDims.height - 1, -roomDims.width/4], [roomDims.length/4, roomDims.height - 1, -roomDims.width/4],
                            [-roomDims.length/4, roomDims.height - 1, roomDims.width/4], [roomDims.length/4, roomDims.height - 1, roomDims.width/4]
                        ];
                        [x_ft, y_ft, z_ft] = positions[instanceIndex % 4];
                        break;
                    case 'audio_microphone':
                        x_ft = -(quantity - 1) * 4 / 2 + (instanceIndex * 4);
                        y_ft = 2.6; // Table height
                        z_ft = 0;
                        break;
                    default:
                        x_ft = -roomDims.length / 2 + 2 + (instanceIndex * 2);
                        y_ft = 3 + toUnits(size[1])/2;
                        z_ft = roomDims.width / 2 - 2;
                        break;
                }}
                return {{ x: toUnits(x_ft), y: toUnits(y_ft), z: toUnits(z_ft) }};
            }}

            function setupCameraControls() {{
                let isDragging = false, isPanning = false;
                let prevMouse = {{x: 0, y: 0}};
                const container = renderer.domElement;

                container.addEventListener('mousedown', (e) => {{
                    isDragging = e.button === 0;
                    isPanning = e.button === 2;
                    prevMouse = {{x: e.clientX, y: e.clientY}};
                }});
                container.addEventListener('mousemove', (e) => {{
                    if (!isDragging && !isPanning) return;
                    const delta = {{x: e.clientX - prevMouse.x, y: e.clientY - prevMouse.y}};
                    if(isDragging) {{
                        const spherical = new THREE.Spherical().setFromVector3(camera.position);
                        spherical.theta -= delta.x * 0.005;
                        spherical.phi -= delta.y * 0.005;
                        spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi));
                        camera.position.setFromSpherical(spherical);
                    }}
                    if(isPanning){{
                        const pan = new THREE.Vector3(-delta.x, delta.y, 0).applyQuaternion(camera.quaternion);
                        camera.position.addScaledVector(pan, 0.002 * camera.position.length());
                    }}
                    camera.lookAt(0, toUnits(roomDims.height / 4), 0);
                    prevMouse = {{x: e.clientX, y: e.clientY}};
                }});
                container.addEventListener('mouseup', () => {{ isDragging = isPanning = false; }});
                container.addEventListener('wheel', (e) => {{
                    e.preventDefault();
                    const scale = e.deltaY > 0 ? 1.1 : 0.9;
                    const dist = camera.position.length() * scale;
                    camera.position.setLength(Math.max(toUnits(5), Math.min(toUnits(50), dist)));
                }});
                container.addEventListener('contextmenu', (e) => e.preventDefault());
                container.addEventListener('click', (event) => {{
                    const rect = container.getBoundingClientRect();
                    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                    raycaster.setFromCamera(mouse, camera);
                    const intersects = raycaster.intersectObjects(scene.children, true);
                    let clickedObj = null;
                    if (intersects.length > 0) {{
                        let obj = intersects[0].object;
                        while(obj.parent && !obj.userData.equipment) {{ obj = obj.parent; }}
                        if(obj.userData.equipment) clickedObj = obj;
                    }}
                    selectEquipment(clickedObj);
                }});
            }}

            function selectEquipment(obj) {{
                if (selectedObject) resetObjectMaterial(selectedObject);
                selectedObject = obj;
                if (obj) {{
                    highlightObject(obj);
                    updateSelectedItemInfo(obj.userData.equipment);
                    updateEquipmentListSelection(obj.userData.equipment.id);
                    zoomToObject(obj);
                }} else {{
                    document.getElementById('selectedItemInfo').innerHTML = '<strong>Click an object or list item for details</strong>';
                    updateEquipmentListSelection(null);
                }}
            }}

            function highlightObject(obj) {{
                obj.traverse(c => {{ if (c.isMesh) {{ c.userData.originalMaterial = c.material; c.material = new THREE.MeshStandardMaterial({{color: 0x4FC3F7, emissive: 0x002244}}); }} }});
            }}

            function resetObjectMaterial(obj) {{
                obj.traverse(c => {{ if (c.isMesh && c.userData.originalMaterial) c.material = c.userData.originalMaterial; }});
            }}

            function updateSelectedItemInfo(eq) {{
                const info = document.getElementById('selectedItemInfo');
                info.innerHTML = `
                    <div style="color: #4FC3F7; font-weight: bold; font-size: 14px;">${{eq.name}}</div>
                    <div style="font-size: 12px;">Brand: ${{eq.brand}} | ${{new Intl.NumberFormat('en-US', {{style: 'currency', currency: 'USD'}}).format(eq.price)}}</div>
                    <div style="font-size: 11px;">${{eq.specs[0].toFixed(1)}}'W × ${{eq.specs[1].toFixed(1)}}'H × ${{eq.specs[2].toFixed(1)}}'D</div>
                    ${{eq.original_quantity > 1 ? `<div style="font-size: 11px;">Instance ${{eq.instance}} of ${{eq.original_quantity}}</div>` : ''}}
                `;
            }}

            function updateEquipmentListSelection(selectedId) {{
                document.querySelectorAll('.equipment-item').forEach(item => {{
                    item.classList.toggle('selected-item', item.dataset.equipmentId == selectedId);
                    if (item.dataset.equipmentId == selectedId) item.scrollIntoView({{behavior: 'smooth', block: 'nearest'}});
                }});
            }}

            function updateEquipmentList() {{
                const list = document.getElementById('equipmentList');
                list.innerHTML = avEquipment.map((eq, i) => `
                    <div class="equipment-item" data-equipment-id="${{eq.id}}">
                        <div class="equipment-name">${{eq.name}}</div>
                        <div class="equipment-details">${{eq.brand}} | ${{new Intl.NumberFormat('en-US', {{style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0}}).format(eq.price)}} ${{eq.original_quantity > 1 ? `| #${{eq.instance}}` : ''}}</div>
                    </div>`).join('');
                list.addEventListener('click', e => {{
                    const item = e.target.closest('.equipment-item');
                    if(item) {{
                        const eqId = parseInt(item.dataset.equipmentId);
                        const obj = scene.children.find(c => c.userData.equipment && c.userData.equipment.id === eqId);
                        if(obj) selectEquipment(obj);
                    }}
                }});
            }}

            function zoomToObject(obj) {{
                const box = new THREE.Box3().setFromObject(obj);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const camDist = maxDim / (2 * Math.tan(camera.fov * Math.PI / 360));
                const direction = camera.position.clone().sub(center).normalize();
                animateCamera(center.clone().addScaledVector(direction, camDist * 2), center);
            }}

            function animateCamera(targetPosition, lookAtTarget) {{
                const startPos = camera.position.clone();
                const startLookAt = new THREE.Vector3().sub(camera.position).normalize();
                const endLookAt = new THREE.Vector3().copy(lookAtTarget).sub(targetPosition).normalize();
                let progress = 0;
                const duration = 750;
                const startTime = Date.now();
                function anim() {{
                    const elapsed = Date.now() - startTime;
                    progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1-progress, 3);
                    camera.position.lerpVectors(startPos, targetPosition, eased);
                    const currentLookAt = new THREE.Vector3().lerpVectors(startLookAt, endLookAt, eased).add(camera.position);
                    camera.lookAt(currentLookAt);
                    if (progress < 1) requestAnimationFrame(anim);
                }}
                anim();
            }}

            function setView(viewType, animate = true, element) {{
                document.querySelectorAll('.control-btn').forEach(b => b.classList.remove('active'));
                element?.classList.add('active');
                
                let targetPosition, lookAt = new THREE.Vector3(0, toUnits(roomDims.height/4), 0);
                switch(viewType) {{
                    case 'overview': targetPosition = new THREE.Vector3(toUnits(roomDims.length * 0.7), toUnits(roomDims.height * 0.9), toUnits(roomDims.width * 0.9)); break;
                    case 'front': targetPosition = new THREE.Vector3(0, toUnits(roomDims.height/2), toUnits(roomDims.width)); break;
                    case 'side': targetPosition = new THREE.Vector3(toUnits(roomDims.length), toUnits(roomDims.height/2), 0); break;
                    case 'top': targetPosition = new THREE.Vector3(0.01, toUnits(roomDims.height + 15), 0); lookAt.set(0,0,0); break;
                    default: return;
                }}
                if (animate) animateCamera(targetPosition, lookAt);
                else {{ camera.position.copy(targetPosition); camera.lookAt(lookAt); }}
            }}
            
            function zoomToSelected() {{ if (selectedObject) zoomToObject(selectedObject); }}
            function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
            function handleResize() {{
                const container = document.getElementById('container');
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            }}
            window.addEventListener('resize', handleResize);
            init();
        </script>
    </body>
    </html>
    """;
    
    components.html(html_content, height=670, scrolling=False)


# --- Main Application ---
def main():
    if 'boq_items' not in st.session_state:
        st.session_state.boq_items = []
    if 'boq_content' not in st.session_state:
        st.session_state.boq_content = ""
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = {}
    
    product_df, guidelines, data_issues = load_and_validate_data()
    
    if data_issues:
        with st.expander("Data Quality Issues", expanded=False):
            for issue in data_issues:
                st.warning(issue)
    
    if product_df is None:
        st.error("Fatal Error: master_product_catalog.csv not found. The application cannot continue.")
        return
        
    model = setup_gemini()
    if not model:
        st.error("Fatal Error: Could not connect to Gemini API. Please check your API key.")
        return
        
    project_id, quote_valid_days = create_project_header()
    
    with st.sidebar:
        st.header("Project Configuration")
        client_name = st.text_input("Client Name", key="client_name_input")
        project_name = st.text_input("Project Name", key="project_name_input")
        currency = st.selectbox("Currency", ["USD", "INR"], index=1, key="currency_select")
        st.session_state['currency'] = currency
        st.markdown("---")
        room_type = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Typical Area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display Size: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
        st.caption(f"Budget: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}")

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Room Analysis", "⚙️ Requirements", "📋 Generate & Edit BOQ", "🖼️ 3D Visualization"])
    
    with tab1:
        room_area, ceiling_height = create_room_calculator()
        
    with tab2:
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified, recording capability'", height=100, key="features_text_area")
        technical_reqs = create_advanced_requirements()
        
    with tab3:
        if st.button("Generate Professional BOQ", type="primary", use_container_width=True, key="generate_boq_button"):
            generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)
        
        if st.session_state.boq_content or st.session_state.boq_items:
            st.markdown("---")
            display_boq_results(
                st.session_state.boq_content,
                st.session_state.validation_results,
                project_id,
                quote_valid_days,
                product_df
            )
        else:
            st.info("Click 'Generate Professional BOQ' to begin, or use the editor below to build one manually.")
            st.markdown("---")
            create_interactive_boq_editor(product_df)

    with tab4:
        create_3d_visualization()

def generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Generate BOQ and save results to session_state."""
    with st.spinner("Engineering professional BOQ with technical validation..."):
        prompt = create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)
        try:
            response = generate_with_retry(model, prompt)
            if response and response.text:
                boq_content = response.text
                boq_items = extract_boq_items_from_response(boq_content, product_df)
                
                validator = BOQValidator(ROOM_SPECS, product_df)
                issues, warnings = validator.validate_technical_requirements(boq_items, room_type, room_area)
                
                avixa_warnings = validate_against_avixa(model, guidelines, boq_items)
                warnings.extend(avixa_warnings)
                
                st.session_state.boq_content = boq_content
                st.session_state.boq_items = boq_items
                st.session_state.validation_results = {"issues": issues, "warnings": warnings}
                
                if not boq_items:
                    st.warning("⚠️ AI generated a BOQ, but no items could be parsed. Check the raw output or try again.")
                else:
                    st.success(f"✅ Successfully generated and loaded {len(boq_items)} items!")
                # After generating, we need to update the markdown content to be sure it matches the parsed items
                update_boq_content_with_current_items()

        except Exception as e:
            st.error(f"BOQ generation failed: {str(e)}")

def create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Create comprehensive prompt for BOQ generation."""
    room_spec = ROOM_SPECS[room_type]
    product_catalog_string = product_df.head(150).to_csv(index=False)
    
    prompt = f"""
You are a Professional AV Systems Engineer with 15+ years of experience. Your task is to create a professional, accurate, and production-ready Bill of Quantities (BOQ).

**PROJECT SPECIFICATIONS:**
- Room Type: {room_type}
- Room Area: {room_area:.0f} sq ft
- Budget Tier: {budget_tier}
- Special Requirements: {features if features else "None specified"}
- Infrastructure Details: {technical_reqs}

**TECHNICAL CONSTRAINTS & GUIDELINES:**
- Adhere strictly to the provided AVIXA standards for all design choices.
- Recommended Display Size: {room_spec['recommended_display_size'][0]}" - {room_spec['recommended_display_size'][1]}"
- Primary Viewing Distance: {room_spec['viewing_distance_ft'][0]} - {room_spec['viewing_distance_ft'][1]} ft
- Audio Coverage Goal: {room_spec['audio_coverage']}
- Target Budget Range (for hardware): ${room_spec['typical_budget_range'][0]:,} - ${room_spec['typical_budget_range'][1]:,}

**MANDATORY INSTRUCTIONS:**
1.  **Use ONLY products from the provided product catalog sample.** Do not invent products. If a required product type (e.g., a specific mount) is not available, select the closest alternative and make a note.
2.  **Ensure Component Compatibility:** Verify that components work together (e.g., mounts are suitable for the selected display size, speakers are compatible with the amplifier).
3.  **Include All Ancillary Items:** You MUST include all necessary supporting hardware, such as mounting brackets, a suitable quantity of cabling (HDMI, USB, Ethernet), and basic power distribution units (PDUs).
4.  **Add Service Line Items:** Include the following three line items AFTER all hardware, calculated as a percentage of the total hardware cost (subtotal):
    - 'Installation & Commissioning Labor' (15%)
    - 'System Warranty (3 Years)' (5%)
    - 'Project Contingency' (10%)

**OUTPUT FORMAT (STRICT):**
-   Begin with a concise 2-3 sentence 'System Design Summary'.
-   Immediately following the summary, provide the BOQ in a clean markdown table with these exact columns:
    | Category | Brand | Product Name | Quantity | Unit Price (USD) | Total (USD) |

**PRODUCT CATALOG SAMPLE:**
```csv
{product_catalog_string}
