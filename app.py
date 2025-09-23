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
    if not st.session_state.boq_items:
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

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days):
    """Display BOQ results with interactive editing capabilities."""
    
    # Show current BOQ item count at the top
    item_count = len(st.session_state.boq_items) if st.session_state.boq_items else 0
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
    if st.session_state.boq_items:
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
    create_interactive_boq_editor()
    
    # Add download functionality
    col1, col2 = st.columns(2)
    
    with col1:
        if boq_content and st.session_state.boq_items:
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
        if st.session_state.boq_items:
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

def create_interactive_boq_editor():
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    
    # Real-time status indicator
    item_count = len(st.session_state.boq_items) if st.session_state.boq_items else 0
    col_status1, col_status2, col_status3 = st.columns(3)
    
    with col_status1:
        st.metric("Items in BOQ", item_count)
    
    with col_status2:
        if st.session_state.boq_items:
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

def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ."""
    st.write("**Add Products to BOQ:**")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Category filter
        categories = ['All'] + sorted(list(product_df['category'].unique())) if 'category' in product_df.columns else ['All']
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
                
                # FIX: Force update the BOQ content to reflect new items
                update_boq_content_with_current_items()
                
                st.success(f"Added {quantity}x {selected_product['name']} to BOQ!")
                # Remove the sleep and rerun - let Streamlit handle the update naturally
                st.rerun()

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
                            
                            # FIX: Force update the BOQ content to reflect new items
                            update_boq_content_with_current_items()
                            
                            st.success(f"Added {add_qty}x {product['name']} to BOQ!")
                            st.rerun()

# --- ORIGINAL FUNCTIONS (UNCHANGED) ---

def edit_current_boq(currency):
    """Interface for editing current BOQ items."""
    if not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ first or add products manually.")
        return
    
    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    
    # Create editable table
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        with st.expander(f"{item.get('category', 'General')} - {item.get('name', 'Unknown')[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
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
                # FIX: Ensure quantity is at least 1 and handle potential float/invalid values
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
    if st.session_state.boq_items:
        st.markdown("---")
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        if currency == 'INR':
            display_total = convert_currency(total_cost, 'INR')
            st.markdown(f"### **Total Project Cost: {format_currency(display_total, 'INR')}**")
        else:
            st.markdown(f"### **Total Project Cost: {format_currency(total_cost, 'USD')}**")

# --- UTILITY FUNCTIONS FOR VISUALIZATION ---

def map_equipment_type(category):
    """Map product category to equipment type for 3D visualization."""
    category_lower = category.lower() if category else ''
    
    # Map categories to 3D equipment types
    if any(term in category_lower for term in ['display', 'monitor', 'screen', 'projector', 'tv']):
        return 'display'
    elif any(term in category_lower for term in ['speaker', 'audio']):
        return 'audio_speaker'
    elif any(term in category_lower for term in ['microphone', 'mic']):
        return 'audio_microphone'
    elif any(term in category_lower for term in ['camera', 'video']):
        return 'camera'
    elif any(term in category_lower for term in ['control', 'processor', 'switch']):
        return 'control'
    elif any(term in category_lower for term in ['rack', 'cabinet']):
        return 'rack'
    elif any(term in category_lower for term in ['mount', 'bracket']):
        return 'mount'
    elif any(term in category_lower for term in ['cable', 'wire']):
        return 'cable'
    else:
        return None  # Skip items that don't map to visual equipment

def get_equipment_specs(equipment_type, product_name):
    """Get realistic specifications for equipment based on type and name."""
    
    # Default specifications by equipment type (width, height, depth in feet)
    default_specs = {
        'display': [4, 2.5, 0.2],
        'audio_speaker': [0.6, 1.0, 0.6],
        'audio_microphone': [0.2, 0.1, 0.2],
        'camera': [0.6, 0.4, 0.6],
        'control': [1.2, 0.6, 0.2],
        'rack': [1.5, 5, 1.5],
        'mount': [0.3, 0.3, 0.8],
        'cable': [0.1, 0.1, 2]
    }
    
    base_spec = default_specs.get(equipment_type, [1, 1, 1])
    
    # Try to extract size from product name for displays
    if equipment_type == 'display' and product_name:
        import re
        size_match = re.search(r'(\d+)"', product_name)
        if size_match:
            size_inches = int(size_match.group(1))
            # Convert diagonal size to approximate width/height (16:9 ratio)
            width_inches = size_inches * 0.87
            height_inches = size_inches * 0.49
            return [width_inches / 12, height_inches / 12, 0.2]  # Convert to feet
    
    # Scale based on product name keywords for other equipment
    if equipment_type == 'audio_speaker' and product_name:
        if any(term in product_name.lower() for term in ['large', 'big', 'tower']):
            return [base_spec[0] * 1.5, base_spec[1] * 1.5, base_spec[2] * 1.5]
        elif any(term in product_name.lower() for term in ['small', 'compact', 'mini']):
            return [base_spec[0] * 0.7, base_spec[1] * 0.7, base_spec[2] * 0.7]
    
    return base_spec

# --- ENHANCED 3D VISUALIZATION FUNCTION ---
def create_3d_visualization():
    """Create a more realistic 3D room visualization using Three.js in Streamlit."""
    st.subheader("3D Room Visualization")
    
    # Get current BOQ items for visualization
    equipment_data = st.session_state.get('boq_items', [])
    
    if not equipment_data:
        st.info("No BOQ items to visualize. Generate a BOQ first or add items manually.")
        return
    
    # Convert ALL BOQ items to JavaScript format with realistic specifications
    js_equipment = []
    for item in equipment_data:
        equipment_type = map_equipment_type(item.get('category', ''))
        if not equipment_type:
            equipment_type = 'control'
        
        specs = get_equipment_specs(equipment_type, item.get('name', ''))
        
        quantity = int(item.get('quantity', 1))
        for i in range(quantity):
            js_equipment.append({
                'id': len(js_equipment) + 1,
                'type': equipment_type,
                'name': item.get('name', 'Unknown'),
                'brand': item.get('brand', 'Unknown'),
                'quantity': 1,
                'original_quantity': quantity,
                'instance': i + 1,
                'price': item.get('price', 0),
                'specs': specs
            })
    
    # Get room dimensions
    room_length = st.session_state.get('room_length', 24)
    room_width = st.session_state.get('room_width', 16)
    room_height = st.session_state.get('room_height', 9)
    
    # The f-string now escapes all JS/CSS curly braces with {{ }}
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body {{ margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a1a; }}
            #container {{ width: 100%; height: 600px; position: relative; }}
            #info {{ 
                position: absolute; top: 15px; left: 15px; color: #ffffff; 
                background: linear-gradient(135deg, rgba(0,0,0,0.9), rgba(20,20,20,0.8));
                padding: 15px; border-radius: 12px; backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1); min-width: 300px; max-height: 450px; overflow-y: auto;
            }}
            #controls {{ 
                position: absolute; bottom: 15px; left: 15px; color: #ffffff;
                background: linear-gradient(135deg, rgba(0,0,0,0.9), rgba(20,20,20,0.8));
                padding: 12px; border-radius: 10px; backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1);
            }}
            #performance {{ 
                position: absolute; top: 15px; right: 15px; color: #ffffff;
                background: linear-gradient(135deg, rgba(0,0,0,0.9), rgba(20,20,20,0.8));
                padding: 10px; border-radius: 8px; backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.1); font-size: 12px;
            }}
            .metric {{ margin: 5px 0; }}
            .metric-value {{ color: #4FC3F7; font-weight: bold; }}
            .equipment-item {{ margin: 6px 0; padding: 6px; background: rgba(255,255,255,0.05); border-radius: 4px; }}
            .equipment-name {{ color: #FFD54F; font-weight: bold; font-size: 12px; }}
            .equipment-details {{ color: #ccc; font-size: 11px; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="info">
                <h3 style="margin-top: 0; color: #4FC3F7; font-size: 16px;">Conference Room Layout</h3>
                <div class="metric">Room: <span class="metric-value">{room_length}' × {room_width}' × {room_height}'</span></div>
                <div class="metric">Equipment: <span class="metric-value" id="equipmentCount">{len(js_equipment)}</span></div>
                <div class="metric">Unique Items: <span class="metric-value">{len(equipment_data)}</span></div>
                <div id="selectedItem">
                    <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2);">
                        <strong>Click equipment to inspect details</strong>
                    </div>
                </div>
            </div>
            <div id="controls">
                <div style="font-weight: bold; margin-bottom: 5px;">Navigation:</div>
                <div style="font-size: 12px;">• Left Click + Drag: Orbit</div>
                <div style="font-size: 12px;">• Mouse Wheel: Zoom</div>
                <div style="font-size: 12px;">• Right Click: Pan</div>
                <div style="font-size: 12px;">• Double Click: Reset</div>
            </div>
            <div id="performance">
                <div>FPS: <span id="fps">--</span></div>
                <div>Objects: <span id="objectCount">0</span></div>
            </div>
        </div>
        
        <script>
            let scene, camera, renderer, raycaster, mouse;
            let animationId, lastTime = performance.now(), frameCount = 0, selectedObject = null;
            
            const roomConfig = {{
                length: {room_length}, width: {room_width}, height: {room_height}, scale: 0.4
            }};
            
            const toUnits = (feet) => feet * roomConfig.scale;
            
            let avEquipment = {js_equipment};
            
            // --- REALISM ENHANCEMENTS: PROCEDURAL TEXTURES ---
            function createFloorTexture() {{
                const canvas = document.createElement('canvas');
                canvas.width = 512;
                canvas.height = 512;
                const context = canvas.getContext('2d');
                
                context.fillStyle = '#6e5a47'; // Dark wood color
                context.fillRect(0, 0, 512, 512);
                context.strokeStyle = '#5c4a37'; // Darker lines
                context.lineWidth = 4;
                
                for (let i = 0; i < 512; i += 32) {{
                    context.beginPath();
                    context.moveTo(i, 0);
                    context.lineTo(i, 512);
                    context.stroke();
                }}
                
                return new THREE.CanvasTexture(canvas);
            }}

            function createCeilingTexture() {{
                const canvas = document.createElement('canvas');
                canvas.width = 256;
                canvas.height = 256;
                const context = canvas.getContext('2d');
                
                context.fillStyle = '#cccccc';
                context.fillRect(0, 0, 256, 256);
                context.strokeStyle = '#bbbbbb';
                context.lineWidth = 2;
                context.strokeRect(0, 0, 256, 256);

                return new THREE.CanvasTexture(canvas);
            }}

            function init() {{
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x334455);
                scene.fog = new THREE.Fog(0x334455, toUnits(20), toUnits(100));
                
                const container = document.getElementById('container');
                camera = new THREE.PerspectiveCamera(50, container.clientWidth / 600, 0.1, 1000);
                camera.position.set(toUnits(-roomConfig.length * 0.1), toUnits(roomConfig.height * 0.8), toUnits(roomConfig.width * 1.1));
                camera.lookAt(0, toUnits(roomConfig.height * 0.2), 0);
                
                renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
                renderer.setSize(container.clientWidth, 600);
                renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer.shadowMap.enabled = true;
                renderer.shadowMap.type = THREE.PCFSoftShadowMap;
                renderer.outputEncoding = THREE.sRGBEncoding;
                renderer.toneMapping = THREE.ACESFilmicToneMapping;
                renderer.toneMappingExposure = 1.0;
                container.appendChild(renderer.domElement);
                
                raycaster = new THREE.Raycaster();
                mouse = new THREE.Vector2();
                
                createRealisticRoom();
                createRealisticLighting();
                createRoomFurniture();
                createAllEquipmentObjects();
                createInteractiveControls();
                
                updateObjectCount();
                animate();
            }}
            
            function createRealisticRoom() {{
                const roomGroup = new THREE.Group();
                
                // --- REALISM ENHANCEMENTS: Use PBR materials and textures ---
                const floorTexture = createFloorTexture();
                floorTexture.wrapS = THREE.RepeatWrapping;
                floorTexture.wrapT = THREE.RepeatWrapping;
                floorTexture.repeat.set(roomConfig.length / 4, roomConfig.width / 4);

                const ceilingTexture = createCeilingTexture();
                ceilingTexture.wrapS = THREE.RepeatWrapping;
                ceilingTexture.wrapT = THREE.RepeatWrapping;
                ceilingTexture.repeat.set(roomConfig.length / 2, roomConfig.width / 2);

                const materials = {{
                    floor: new THREE.MeshStandardMaterial({{ map: floorTexture, roughness: 0.7, metalness: 0.1 }}),
                    wall: new THREE.MeshStandardMaterial({{ color: 0xddeeff, roughness: 0.9, metalness: 0.0 }}),
                    ceiling: new THREE.MeshStandardMaterial({{ map: ceilingTexture, roughness: 0.8 }})
                }};
                
                const wallHeight = toUnits(roomConfig.height);

                // Floor
                const floor = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomConfig.length), toUnits(roomConfig.width)), materials.floor);
                floor.rotation.x = -Math.PI / 2;
                floor.receiveShadow = true;
                roomGroup.add(floor);
                
                // Walls (only 3 for better viewing)
                const backWall = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomConfig.length), wallHeight), materials.wall);
                backWall.position.set(0, wallHeight/2, -toUnits(roomConfig.width/2));
                backWall.receiveShadow = true;
                roomGroup.add(backWall);

                const leftWall = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomConfig.width), wallHeight), materials.wall);
                leftWall.position.set(-toUnits(roomConfig.length/2), wallHeight/2, 0);
                leftWall.rotation.y = Math.PI/2;
                leftWall.receiveShadow = true;
                roomGroup.add(leftWall);

                // Ceiling
                const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomConfig.length), toUnits(roomConfig.width)), materials.ceiling);
                ceiling.position.y = wallHeight;
                ceiling.rotation.x = Math.PI / 2;
                roomGroup.add(ceiling);
                
                scene.add(roomGroup);
            }}

            function createRealisticLighting() {{
                // --- REALISM ENHANCEMENTS: Advanced lighting setup ---
                // Soft ambient light
                scene.add(new THREE.HemisphereLight(0x8899aa, 0x555555, 0.8));

                // Main light source simulating window or overheads
                const dirLight = new THREE.DirectionalLight(0xffeedd, 0.7);
                dirLight.position.set(toUnits(-5), toUnits(8), toUnits(5));
                dirLight.castShadow = true;
                dirLight.shadow.mapSize.width = 1024;
                dirLight.shadow.mapSize.height = 1024;
                dirLight.shadow.camera.top = toUnits(12);
                dirLight.shadow.camera.bottom = toUnits(-12);
                dirLight.shadow.camera.left = toUnits(-12);
                dirLight.shadow.camera.right = toUnits(12);
                scene.add(dirLight);

                // Small fill light
                const fillLight = new THREE.PointLight(0xaaaaff, 0.2, toUnits(20));
                fillLight.position.set(toUnits(roomConfig.length * 0.3), toUnits(3), toUnits(roomConfig.width * 0.3));
                scene.add(fillLight);
            }}

            function createRoomFurniture() {{
                // --- REALISM ENHANCEMENTS: More detailed furniture ---
                const furnitureGroup = new THREE.Group();
                const tableMaterial = new THREE.MeshStandardMaterial({{ color: 0x4d3a2a, roughness: 0.6, metalness: 0.2 }});

                // Table Top
                const tableTop = new THREE.Mesh(new THREE.BoxGeometry(toUnits(12), toUnits(0.2), toUnits(5)), tableMaterial);
                tableTop.position.y = toUnits(2.5);
                tableTop.castShadow = true;
                tableTop.receiveShadow = true;
                furnitureGroup.add(tableTop);

                // Table Legs
                const legGeo = new THREE.BoxGeometry(toUnits(0.4), toUnits(2.4), toUnits(0.4));
                const legPositions = [[-5, 1.25, -2], [5, 1.25, -2], [-5, 1.25, 2], [5, 1.25, 2]];
                legPositions.forEach(pos => {{
                    const leg = new THREE.Mesh(legGeo, tableMaterial);
                    leg.position.set(toUnits(pos[0]), toUnits(pos[1]), toUnits(pos[2]));
                    leg.castShadow = true;
                    furnitureGroup.add(leg);
                }});

                // Chairs
                const chairMaterial = new THREE.MeshStandardMaterial({{ color: 0x222222, roughness: 0.5 }});
                const seatGeo = new THREE.BoxGeometry(toUnits(1.5), toUnits(0.15), toUnits(1.5));
                const backGeo = new THREE.BoxGeometry(toUnits(1.5), toUnits(2), toUnits(0.15));

                for (let i = 0; i < 8; i++) {{
                    const chair = new THREE.Group();
                    const seat = new THREE.Mesh(seatGeo, chairMaterial);
                    seat.position.y = toUnits(1.5);
                    seat.castShadow = true;

                    const back = new THREE.Mesh(backGeo, chairMaterial);
                    back.position.y = toUnits(2.5);
                    back.position.z = toUnits(-0.7);
                    back.castShadow = true;
                    
                    chair.add(seat);
                    chair.add(back);

                    const side = i < 4 ? -1 : 1;
                    const spacing = i % 4;
                    chair.position.set(toUnits(-4.5 + spacing * 3), 0, toUnits(4 * side));
                    chair.rotation.y = side > 0 ? Math.PI : 0;
                    furnitureGroup.add(chair);
                }}

                scene.add(furnitureGroup);
            }}

            function createAllEquipmentObjects() {{
                avEquipment.forEach((item, index) => {{
                    const equipmentGroup = createEquipmentMesh(item, index);
                    if (equipmentGroup) scene.add(equipmentGroup);
                }});
            }}

            function createEquipmentMesh(item, index) {{
                const group = new THREE.Group();
                const size = item.specs;
                let geometry, material;

                switch(item.type) {{
                    case 'display':
                        material = new THREE.MeshStandardMaterial({{ color: 0x050505, roughness: 0.3, metalness: 0.5 }});
                        const bezel = new THREE.Mesh(new THREE.BoxGeometry(toUnits(size[0]), toUnits(size[1]), toUnits(size[2])), material);
                        
                        const screenGeo = new THREE.PlaneGeometry(toUnits(size[0] * 0.9), toUnits(size[1] * 0.9));
                        const screenMat = new THREE.MeshBasicMaterial({{ color: 0x1a1a2e }});
                        const screen = new THREE.Mesh(screenGeo, screenMat);
                        screen.position.z = toUnits(size[2]/2 + 0.01);
                        bezel.add(screen);
                        group.add(bezel);
                        break;
                    default:
                        material = new THREE.MeshStandardMaterial({{ color: 0x333333, roughness: 0.5, metalness: 0.1 }});
                        geometry = new THREE.BoxGeometry(toUnits(size[0]), toUnits(size[1]), toUnits(size[2]));
                        const mesh = new THREE.Mesh(geometry, material);
                        group.add(mesh);
                }}

                group.traverse(obj => {{ if(obj.isMesh) obj.castShadow = true; }});

                const position = getSmartPosition(item.type, item.instance -1, size, item.original_quantity);
                group.position.set(position.x, position.y, position.z);
                if (position.rotation !== undefined) group.rotation.y = position.rotation;
                
                group.userData = item;
                group.name = `equipment_${{item.id}}`;
                return group;
            }}

            function getSmartPosition(type, instanceIndex, size, quantity) {{
                // Simplified positioning logic for clarity
                let x = 0, y = 0, z = 0, rotation = 0;
                const spacing = toUnits(size[0] + 0.5);

                switch(type) {{
                    case 'display':
                        x = toUnits(- (quantity - 1) * size[0] / 2) + (instanceIndex * spacing);
                        y = toUnits(roomConfig.height * 0.6);
                        z = -toUnits(roomConfig.width/2 - 0.2);
                        break;
                    case 'audio_speaker':
                        x = toUnits((-roomConfig.length/2 + 2) + (instanceIndex * 4));
                        y = toUnits(roomConfig.height - 0.5);
                        z = toUnits(roomConfig.width/4 * (instanceIndex % 2 === 0 ? 1 : -1));
                        break;
                    case 'control':
                    case 'audio_microphone':
                        x = toUnits(-3 + (instanceIndex * 3));
                        y = toUnits(2.6); // On table
                        z = 0;
                        break;
                    default:
                        x = toUnits(roomConfig.length/2 - 1.5);
                        y = toUnits(1 + instanceIndex * 2);
                        z = toUnits(-roomConfig.width/4);
                        rotation = -Math.PI/2;
                }}
                return {{ x, y, z, rotation }};
            }}

            function createInteractiveControls() {{
                renderer.domElement.addEventListener('click', onMouseClick);
                renderer.domElement.addEventListener('dblclick', resetCamera);
                
                let isMouseDown = false, mouseX = 0, mouseY = 0, isPanning = false;
                let cameraTheta = Math.atan2(camera.position.z, camera.position.x);
                let cameraPhi = Math.acos(camera.position.y / camera.position.length());
                let cameraRadius = camera.position.length();
                
                renderer.domElement.addEventListener('mousedown', (e) => {{
                    isMouseDown = true; isPanning = e.button === 2; mouseX = e.clientX; mouseY = e.clientY; e.preventDefault();
                }});
                renderer.domElement.addEventListener('mouseup', () => {{ isMouseDown = false; isPanning = false; }});
                renderer.domElement.addEventListener('contextmenu', (e) => e.preventDefault());
                
                renderer.domElement.addEventListener('mousemove', (e) => {{
                    if (!isMouseDown) return;
                    const deltaX = e.clientX - mouseX, deltaY = e.clientY - mouseY;
                    if (isPanning) {{
                        const factor = cameraRadius * 0.001;
                        camera.translateX(-deltaX * factor);
                        camera.translateY(deltaY * factor);
                    }} else {{
                        cameraTheta -= deltaX * 0.005;
                        cameraPhi = Math.max(0.1, Math.min(Math.PI - 0.1, cameraPhi + deltaY * 0.005));
                        camera.position.x = cameraRadius * Math.sin(cameraPhi) * Math.cos(cameraTheta);
                        camera.position.y = cameraRadius * Math.cos(cameraPhi);
                        camera.position.z = cameraRadius * Math.sin(cameraPhi) * Math.sin(cameraTheta);
                        camera.lookAt(0, toUnits(roomConfig.height * 0.3), 0);
                    }}
                    mouseX = e.clientX; mouseY = e.clientY;
                }});
                
                renderer.domElement.addEventListener('wheel', (e) => {{
                    cameraRadius *= (e.deltaY > 0 ? 1.1 : 0.9);
                    cameraRadius = Math.max(toUnits(5), Math.min(toUnits(50), cameraRadius));
                    camera.position.x = cameraRadius * Math.sin(cameraPhi) * Math.cos(cameraTheta);
                    camera.position.y = cameraRadius * Math.cos(cameraPhi);
                    camera.position.z = cameraRadius * Math.sin(cameraPhi) * Math.sin(cameraTheta);
                    e.preventDefault();
                }});
            }}
            
            function onMouseClick(event) {{
                const rect = renderer.domElement.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                
                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);
                
                if (selectedObject) {{
                    selectedObject.traverse(child => {{ if (child.isMesh) child.material.emissive.setHex(0x000000); }});
                }}
                
                for (let intersect of intersects) {{
                    let obj = intersect.object;
                    while (obj.parent && !obj.userData.name) {{ obj = obj.parent; }}
                    if (obj.userData && obj.userData.name) {{
                        selectedObject = obj;
                        obj.traverse(child => {{ if (child.isMesh) child.material.emissive.setHex(0x555555); }});
                        
                        const item = obj.userData;
                        const instanceText = item.original_quantity > 1 ? ` (Instance ${{item.instance}}/${{item.original_quantity}})` : '';
                        document.getElementById('selectedItem').innerHTML = `
                            <div style="margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2);">
                                <div class="equipment-name">${{item.name}}${{instanceText}}</div>
                                <div class="equipment-details"><strong>Brand:</strong> ${{item.brand}}</div>
                            </div>`;
                        break;
                    }}
                }}
            }}
            
            function resetCamera() {{
                 camera.position.set(toUnits(-roomConfig.length * 0.1), toUnits(roomConfig.height * 0.8), toUnits(roomConfig.width * 1.1));
                 camera.lookAt(0, toUnits(roomConfig.height * 0.2), 0);
            }}
            
            function updateObjectCount() {{ document.getElementById('objectCount').textContent = scene.children.length; }}
            
            function animate() {{
                animationId = requestAnimationFrame(animate);
                renderer.render(scene, camera);
            }}
            
            window.addEventListener('load', init);
            window.addEventListener('beforeunload', () => cancelAnimationFrame(animationId));
        </script>
    </body>
    </html>
    """
    
    components.html(html_content, height=620)


# --- Main Application ---
def main():
    # SOLVED: Initialize session state for all generated content to prevent it from disappearing on rerun.
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
    tab1, tab2, tab3, tab4 = st.tabs(["Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])
    
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
                # This function now saves results to session_state instead of directly displaying them.
                generate_boq(model, product_df, guidelines, room_type, budget_tier, features, 
                             technical_reqs, room_area)
        
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
        
        # SOLVED: Display results from session_state. This ensures they persist on reruns.
        if st.session_state.boq_content or st.session_state.boq_items:
            st.markdown("---")
            display_boq_results(
                st.session_state.boq_content,
                st.session_state.validation_results,
                project_id,
                quote_valid_days
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
                
                # NEW: Add AI-powered AVIXA compliance validation
                avixa_warnings = validate_against_avixa(model, guidelines, boq_items)
                warnings.extend(avixa_warnings)
                
                validation_results = {"issues": issues, "warnings": warnings}
                
                # SOLVED: Store all generated content in session_state to persist across reruns.
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
