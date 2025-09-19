import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import hashlib
import json
import time
from io import BytesIO
import base64

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

# --- Room Specifications Database ---
ROOM_SPECS = {
    "Huddle Room (2-4 People)": {
        "area_sqft": (50, 120),
        "recommended_display_size": (32, 55),
        "viewing_distance_ft": (4, 8),
        "audio_coverage": "Near-field",
        "camera_type": "Fixed wide-angle",
        "power_requirements": "Standard 15A circuit",
        "network_ports": 2,
        "typical_budget_range": (5000, 15000)
    },
    "Medium Conference Room (5-10 People)": {
        "area_sqft": (150, 300),
        "recommended_display_size": (55, 75),
        "viewing_distance_ft": (8, 14),
        "audio_coverage": "Room-wide with expansion mics",
        "camera_type": "PTZ or wide-angle with tracking",
        "power_requirements": "20A dedicated circuit recommended",
        "network_ports": 3,
        "typical_budget_range": (15000, 35000)
    },
    "Executive Boardroom": {
        "area_sqft": (300, 600),
        "recommended_display_size": (75, 98),
        "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling or table mics",
        "camera_type": "Multiple cameras with auto-switching",
        "power_requirements": "30A dedicated circuit",
        "network_ports": 4,
        "typical_budget_range": (35000, 80000)
    },
    "Training Room": {
        "area_sqft": (200, 500),
        "recommended_display_size": (65, 86),
        "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed with wireless mic support",
        "camera_type": "Fixed or PTZ for presenter tracking",
        "power_requirements": "20A circuit with UPS backup",
        "network_ports": 3,
        "typical_budget_range": (20000, 50000)
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

# --- Enhanced UI Components ---
def create_project_header():
    """Create professional project header."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("Professional AV BOQ Generator")
        st.caption("Production-ready Bill of Quantities with technical validation")
    
    with col2:
        project_id = st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}")
    
    with col3:
        quote_valid_days = st.number_input("Quote Valid (Days)", min_value=15, max_value=90, value=30)
    
    return project_id, quote_valid_days

def create_room_calculator():
    """Room size calculator and validator."""
    st.subheader("Room Analysis & Specifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        room_length = st.number_input("Room Length (ft)", min_value=8.0, max_value=50.0, value=16.0)
        room_width = st.number_input("Room Width (ft)", min_value=6.0, max_value=30.0, value=12.0)
        ceiling_height = st.number_input("Ceiling Height (ft)", min_value=8.0, max_value=20.0, value=9.0)
    
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
        has_dedicated_circuit = st.checkbox("Dedicated 20A Circuit Available")
        network_capability = st.selectbox("Network Infrastructure", 
                                            ["Standard 1Gb", "10Gb Capable", "Fiber Available"])
        cable_management = st.selectbox("Cable Management", 
                                          ["Exposed", "Conduit", "Raised Floor", "Drop Ceiling"])
    
    with col2:
        st.write("**Compliance & Standards**")
        ada_compliance = st.checkbox("ADA Compliance Required")
        fire_code_compliance = st.checkbox("Fire Code Compliance Required")
        security_clearance = st.selectbox("Security Level", 
                                            ["Standard", "Restricted", "Classified"])
    
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
        doc_content += "**⚡ Technical Recommendations:**\n"
        for warning in validation_results['warnings']:
            doc_content += f"- {warning}\n"
        doc_content += "\n"
    
    doc_content += "---\n\n"
    
    return doc_content

# --- FIXED: Enhanced BOQ Item Extraction ---
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

# --- Main Application ---
def main():
    # Initialize session state for BOQ items if not exists
    if 'boq_items' not in st.session_state:
        st.session_state.boq_items = []
    
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
        
        client_name = st.text_input("Client Name", value="")
        project_name = st.text_input("Project Name", value="")
        
        # Currency selection
        currency = st.selectbox("Currency", ["USD", "INR"], index=1 if "India" in st.session_state.get('user_location', 'India') else 0)
        st.session_state['currency'] = currency  # Store in session state
        
        st.markdown("---")
        
        room_type = st.selectbox(
            "Primary Space Type:",
            list(ROOM_SPECS.keys())
        )
        
        budget_tier = st.select_slider(
            "Budget Tier:",
            options=["Economy", "Standard", "Premium", "Enterprise"],
            value="Standard"
        )
        
        # Display room specifications
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Typical area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display size: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
        st.caption(f"Budget range: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}")
    
    # Main content areas
    tab1, tab2, tab3, tab4 = st.tabs(["Room Analysis", "Requirements", "Generate BOQ", "3D Visualization"])
    
    with tab1:
        room_area, ceiling_height = create_room_calculator()
    
    with tab2:
        features = st.text_area(
            "Specific Requirements & Features:",
            placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified, recording capability'",
            height=100
        )
        
        technical_reqs = create_advanced_requirements()
    
    with tab3:
        st.subheader("BOQ Generation")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("Generate Professional BOQ", type="primary", use_container_width=True):
                generate_boq(model, product_df, guidelines, room_type, budget_tier, features, 
                             technical_reqs, room_area, project_id, quote_valid_days)
    
        with col2:
            st.markdown("**Product Stats:**")
            st.metric("Total Products", len(product_df))
            st.metric("Brands", product_df['brand'].nunique())
            if 'price' in product_df.columns:
                try:
                    # Convert price column to numeric, handling errors
                    numeric_prices = pd.to_numeric(product_df['price'], errors='coerce')
                    valid_prices = numeric_prices[numeric_prices > 0]
                    avg_price_usd = valid_prices.mean() if len(valid_prices) > 0 else None
                    
                    if avg_price_usd and not pd.isna(avg_price_usd):
                        # Get currency preference from session state
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
    
    with tab4:
        create_3d_visualization_placeholder()

def generate_boq(model, product_df, guidelines, room_type, budget_tier, features, 
                 technical_reqs, room_area, project_id, quote_valid_days):
    """Enhanced BOQ generation with validation."""
    
    with st.spinner("Engineering professional BOQ with technical validation..."):
        
        # Create enhanced prompt
        prompt = create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, 
                                        features, technical_reqs, room_area)
        
        try:
            # Generate BOQ with retry logic
            response = generate_with_retry(model, prompt)
            
            if response:
                # Parse and validate response
                boq_content = response.text
                
                # FIXED: Extract structured data and load into session state
                boq_items = extract_boq_items_from_response(boq_content, product_df)
                
                # Load items into session state for editor
                st.session_state.boq_items = boq_items
                
                # Validate BOQ
                validator = BOQValidator(ROOM_SPECS, product_df)
                issues, warnings = validator.validate_technical_requirements(
                    boq_items, room_type, room_area
                )
                
                validation_results = {"issues": issues, "warnings": warnings}
                
                # Display results
                display_boq_results(boq_content, validation_results, project_id, quote_valid_days)
                
                # Show success message about loading items
                if boq_items:
                    st.success(f"✅ Successfully loaded {len(boq_items)} items into BOQ editor!")
                
        except Exception as e:
            st.error(f"BOQ generation failed: {str(e)}")
            with st.expander("Technical Details"):
                st.code(str(e))

def create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Create comprehensive prompt for BOQ generation."""
    
    room_spec = ROOM_SPECS[room_type]
    product_catalog_string = product_df.to_csv(index=False)
    
    prompt = f"""
You are a Professional AV Systems Engineer with 15+ years experience. Create a production-ready BOQ.

**PROJECT SPECIFICATIONS:**
- Room Type: {room_type}
- Room Area: {room_area:.0f} sq ft
- Budget Tier: {budget_tier}
- Special Requirements: {features}
- Infrastructure: {technical_reqs}

**TECHNICAL CONSTRAINTS:**
- Display size range: {room_spec['recommended_display_size'][0]}"-{room_spec['recommended_display_size'][1]}"
- Viewing distance: {room_spec['viewing_distance_ft'][0]}-{room_spec['viewing_distance_ft'][1]} ft
- Audio coverage: {room_spec['audio_coverage']}
- Power requirements: {room_spec['power_requirements']}
- Budget target: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}

**MANDATORY REQUIREMENTS:**
1. ONLY use products from the provided catalog
2. Verify all components are compatible
3. Include proper mounting and cabling
4. Add installation labor estimates
5. Ensure system meets AVIXA standards
6. Include 3-year warranty costs
7. Add 15% contingency for unforeseen issues

**OUTPUT FORMAT REQUIREMENT:**
Please provide your response in a clear table format using markdown tables. Make sure to include:
| Category | Brand | Product Name | Quantity | Unit Price | Total |

**PRODUCT CATALOG:**
{product_catalog_string}

Generate the BOQ now:
"""
    
    return prompt

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days):
    """Display BOQ results with interactive editing capabilities."""
    
    st.subheader("Generated Bill of Quantities")
    
    # Show validation results first
    if validation_results['issues']:
        st.error("Critical Issues Found:")
        for issue in validation_results['issues']:
            st.write(f"- {issue}")
    
    if validation_results['warnings']:
        st.warning("Technical Recommendations:")
        for warning in validation_results['warnings']:
            st.write(f"- {warning}")
    
    # Display BOQ content
    st.markdown(boq_content)
    
    # Add interactive BOQ editor
    st.markdown("---")
    create_interactive_boq_editor()
    
    # Add download functionality
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Generate PDF-ready content
        pdf_content = generate_professional_boq_document(
            {'design_summary': boq_content}, 
            {'project_id': project_id, 'quote_valid_days': quote_valid_days},
            validation_results
        )
        
        st.download_button(
            label="Download BOQ (Markdown)",
            data=pdf_content,
            file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )
    
    with col2:
        # Generate CSV for further processing
        if st.session_state.boq_items:
            csv_data = "Category,Brand,Product,Quantity,Unit Price,Total\n"
            for item in st.session_state.boq_items:
                total = item.get('price', 0) * item.get('quantity', 1)
                csv_data += f"{item.get('category', '')},{item.get('brand', '')},{item.get('name', '')},{item.get('quantity', 1)},{item.get('price', 0)},{total}\n"
        else:
            csv_data = "Category,Brand,Product,Quantity,Unit Price,Total\n"
        
        st.download_button(
            label="Download BOQ (CSV)",
            data=csv_data,
            file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col3:
        if st.button("Generate Revised BOQ", help="Generate new BOQ with validation feedback"):
            st.experimental_rerun()

def create_interactive_boq_editor():
    """FIXED: Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    
    # Get product data for editing
    product_df, _, _ = load_and_validate_data()
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

def edit_current_boq(currency):
    """FIXED: Interface for editing current BOQ items."""
    if not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ first.")
        return
    
    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    
    # Create editable table
    for i, item in enumerate(st.session_state.boq_items):
        with st.expander(f"{item.get('category', 'General')} - {item.get('name', 'Unknown')[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                new_name = st.text_input(f"Product Name", value=item.get('name', ''), key=f"name_{i}")
                new_brand = st.text_input(f"Brand", value=item.get('brand', ''), key=f"brand_{i}")
            
            with col2:
                new_category = st.selectbox(
                    "Category", 
                    ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General'],
                    index=['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General'].index(
                        item.get('category', 'General') if item.get('category', 'General') in 
                        ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General'] else 'General'
                    ),
                    key=f"category_{i}"
                )
            
            with col3:
                new_quantity = st.number_input(
                    "Quantity", 
                    min_value=1, 
                    value=int(item.get('quantity', 1)), 
                    key=f"qty_{i}"
                )
                
                # Price input with currency conversion
                current_price = item.get('price', 0)
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
                    stored_price = new_price / get_usd_to_inr_rate()
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
                    st.session_state.boq_items.pop(i)
                    st.experimental_rerun()
            
            # Update item if changed
            st.session_state.boq_items[i].update({
                'name': new_name,
                'brand': new_brand,
                'category': new_category,
                'quantity': new_quantity,
                'price': stored_price
            })
    
    # Summary
    if st.session_state.boq_items:
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        if currency == 'INR':
            display_total = convert_currency(total_cost, 'INR')
            st.markdown(f"### **Total Project Cost: {format_currency(display_total, 'INR')}**")
        else:
            st.markdown(f"### **Total Project Cost: {format_currency(total_cost, 'USD')}**")

def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ."""
    st.write("**Add Products to BOQ:**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Category filter
        categories = ['All'] + list(product_df['category'].unique()) if 'category' in product_df.columns else ['All']
        selected_category = st.selectbox("Filter by Category", categories)
        
        # Filter products
        if selected_category != 'All':
            filtered_df = product_df[product_df['category'] == selected_category]
        else:
            filtered_df = product_df
        
        # Product selection
        product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
        if product_options:
            selected_product_str = st.selectbox("Select Product", product_options)
            
            # Find selected product
            for _, row in filtered_df.iterrows():
                if f"{row['brand']} - {row['name']}" == selected_product_str:
                    selected_product = row
                    break
        else:
            st.warning("No products found in selected category")
            return
    
    with col2:
        if product_options:
            quantity = st.number_input("Quantity", min_value=1, value=1)
            
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
                st.success(f"Added {quantity}x {selected_product['name']} to BOQ!")
                st.experimental_rerun()

def product_search_interface(product_df, currency):
    """Advanced product search interface."""
    st.write("**Search Product Catalog:**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input("Search products...", placeholder="Enter product name, brand, or features")
        
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
            for _, product in search_results.head(10).iterrows():  # Limit to first 10 results
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
                        add_qty = st.number_input(f"Qty", min_value=1, value=1, key=f"search_qty_{product.name}")
                        if st.button(f"Add", key=f"search_add_{product.name}"):
                            new_item = {
                                'category': product.get('category', 'General'),
                                'name': product.get('name', ''),
                                'brand': product.get('brand', ''),
                                'quantity': add_qty,
                                'price': price,
                                'matched': True
                            }
                            st.session_state.boq_items.append(new_item)
                            st.success(f"Added {add_qty}x {product['name']} to BOQ!")

def create_3d_visualization_placeholder():
    """Placeholder for 3D room visualization."""
    st.subheader("3D Room Visualization")
    st.info("🚧 3D visualization feature coming soon!")
    
    # Placeholder for future 3D visualization using Three.js
    st.markdown("""
    **Planned Features:**
    - Interactive 3D room layout
    - Equipment placement visualization  
    - Cable routing planning
    - Sight line analysis
    - Acoustic modeling preview
    """)
    
    # Simple 2D room layout mockup
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**2D Room Layout Preview:**")
        # This would be replaced with actual 3D visualization
        st.image("https://via.placeholder.com/600x400/e0e0e0/333333?text=3D+Room+Visualization+Coming+Soon", 
                caption="Interactive 3D room visualization will be available in future updates")
    
    with col2:
        st.markdown("**Equipment List:**")
        if st.session_state.boq_items:
            for item in st.session_state.boq_items[:5]:  # Show first 5 items
                st.write(f"• {item.get('name', 'Unknown')[:30]}...")
            if len(st.session_state.boq_items) > 5:
                st.write(f"• ... and {len(st.session_state.boq_items) - 5} more items")
        else:
            st.write("Generate a BOQ first to see equipment list")

# Run the application
if __name__ == "__main__":
    main()
