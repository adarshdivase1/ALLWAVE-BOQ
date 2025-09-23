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
        
        if not boq_items:
            issues.append("No BOQ items found to validate")
            return issues, warnings
        
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            room_spec = self.room_specs.get(room_type, {})
            recommended_size = room_spec.get('recommended_display_size', (32, 98))
            
            for display in displays:
                try:
                    product_name = display.get('name', '')
                    if not isinstance(product_name, str):
                        product_name = str(product_name) if product_name is not None else ''
                    
                    if product_name:
                        size_match = re.search(r'(\d+)"', product_name)
                        if size_match:
                            size = int(size_match.group(1))
                            if size < recommended_size[0]:
                                warnings.append(f"Display size {size}\" may be too small for {room_type}")
                            elif size > recommended_size[1]:
                                warnings.append(f"Display size {size}\" may be too large for {room_type}")
                except (re.error, ValueError, AttributeError) as e:
                    print(f"Error validating display size for {display.get('name', 'Unknown')}: {e}")
                    continue
        
        essential_categories = ['display', 'audio', 'control']
        found_categories = [item.get('category', '').lower() for item in boq_items]
        
        for essential in essential_categories:
            if not any(essential in cat for cat in found_categories):
                issues.append(f"Missing essential component: {essential}")
        
        total_estimated_power = len(boq_items) * 150
        if total_estimated_power > 1800:
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
            if "no specific compliance issues" in response.text.lower():
                return []
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
    
    if validation_results.get('issues'):
        doc_content += "**⚠️ Critical Issues:**\n"
        for issue in validation_results['issues']:
            doc_content += f"- {issue}\n"
        doc_content += "\n"
    
    if validation_results.get('warnings'):
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
    
    if not boq_content:
        return items
    
    lines = boq_content.split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        
        if '|' in line and any(keyword in line.lower() for keyword in ['category', 'product', 'brand', 'item', 'description']):
            in_table = True
            continue
            
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
            
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            try:
                parts = [part.strip() for part in line.split('|') if part.strip()]
                if len(parts) >= 3:
                    category = parts[0].lower() if len(parts) > 0 else 'general'
                    brand = parts[1] if len(parts) > 1 else 'Unknown'
                    product_name = parts[2] if len(parts) > 2 else parts[1] if len(parts) > 1 else 'Unknown'
                    
                    quantity = 1
                    for part in parts:
                        if part.isdigit():
                            quantity = int(part)
                            break
                    
                    matched_product = match_product_in_database(product_name, brand, product_df)
                    if matched_product is not None:
                        price = float(matched_product.get('price', 0))
                        actual_brand = matched_product.get('brand', brand)
                        actual_category = matched_product.get('category', category)
                        actual_name = matched_product.get('name', product_name)
                    else:
                        price = 0
                        actual_brand = brand
                        actual_category = normalize_category(category, product_name)
                        actual_name = product_name
                    
                    items.append({
                        'category': actual_category, 'name': actual_name, 'brand': actual_brand,
                        'quantity': quantity, 'price': price, 'matched': matched_product is not None
                    })
            except Exception as e:
                print(f"Error processing table row: {line}. Error: {e}")
                continue
                
        elif in_table and not line.startswith('|'):
            in_table = False
    
    return items

def match_product_in_database(product_name, brand, product_df):
    """Try to match a product name and brand with the database."""
    if product_df is None or len(product_df) == 0:
        return None
    
    brand_matches = product_df[product_df['brand'].str.contains(brand, case=False, na=False)]
    if len(brand_matches) > 0:
        name_matches = brand_matches[brand_matches['name'].str.contains(product_name[:20], case=False, na=False)]
        if len(name_matches) > 0:
            return name_matches.iloc[0].to_dict()
    
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

def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if not st.session_state.boq_items:
        st.session_state.boq_content = ""
        return
    
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
    
    boq_content += f"|||||**SUBTOTAL**|**${total_cost:,.2f}**|\n"
    boq_content += f"|||||Installation & Labor (15%)|**${total_cost * 0.15:,.2f}**|\n"
    boq_content += f"|||||System Warranty (5%)|**${total_cost * 0.05:,.2f}**|\n"
    boq_content += f"|||||Project Contingency (10%)|**${total_cost * 0.10:,.2f}**|\n"
    boq_content += f"|||||**TOTAL PROJECT COST**|**${total_cost * 1.30:,.2f}**|\n"
    
    st.session_state.boq_content = boq_content

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days):
    """Display BOQ results with interactive editing capabilities."""
    item_count = len(st.session_state.boq_items) if st.session_state.boq_items else 0
    st.subheader(f"Generated Bill of Quantities ({item_count} items)")
    
    if validation_results and validation_results.get('issues'):
        st.error("Critical Issues Found:")
        for issue in validation_results['issues']:
            st.write(f"- {issue}")
    
    if validation_results and validation_results.get('warnings'):
        st.warning("Technical Recommendations & Compliance Notes:")
        for warning in validation_results['warnings']:
            st.write(f"- {warning}")
    
    if boq_content:
        st.markdown(boq_content)
    else:
        st.info("No BOQ content generated yet. Use the interactive editor below to add items manually.")
    
    if st.session_state.boq_items:
        currency = st.session_state.get('currency', 'USD')
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        
        if currency == 'INR':
            display_total = convert_currency(total_cost, 'INR')
            st.metric("Current BOQ Total", format_currency(display_total * 1.30, 'INR'), help="Includes installation, warranty, and contingency")
        else:
            st.metric("Current BOQ Total", format_currency(total_cost * 1.30, 'USD'), help="Includes installation, warranty, and contingency")
    
    st.markdown("---")
    create_interactive_boq_editor()
    
    col1, col2 = st.columns(2)
    with col1:
        if boq_content and st.session_state.boq_items:
            doc_content = generate_professional_boq_document(
                {'design_summary': boq_content.split('---')[0] if '---' in boq_content else boq_content[:200]}, 
                {'project_id': project_id, 'quote_valid_days': quote_valid_days},
                validation_results or {}
            )
            final_doc = doc_content + "\n" + boq_content
            st.download_button("Download BOQ (Markdown)", final_doc, f"{project_id}_BOQ.md", "text/markdown")
        else:
            st.button("Download BOQ (Markdown)", disabled=True)
    
    with col2:
        if st.session_state.boq_items:
            df_to_download = pd.DataFrame(st.session_state.boq_items)
            df_to_download['price'] = pd.to_numeric(df_to_download['price'], errors='coerce').fillna(0)
            df_to_download['quantity'] = pd.to_numeric(df_to_download['quantity'], errors='coerce').fillna(0)
            df_to_download['total'] = df_to_download['price'] * df_to_download['quantity']
            csv_data = df_to_download[['category', 'brand', 'name', 'quantity', 'price', 'total']].to_csv(index=False).encode('utf-8')
            st.download_button("Download BOQ (CSV)", csv_data, f"{project_id}_BOQ.csv", "text/csv")
        else:
            st.button("Download BOQ (CSV)", disabled=True)

def create_interactive_boq_editor():
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    
    item_count = len(st.session_state.boq_items) if st.session_state.boq_items else 0
    col_status1, col_status2, col_status3 = st.columns(3)
    
    with col_status1:
        st.metric("Items in BOQ", item_count)
    
    with col_status2:
        currency = st.session_state.get('currency', 'USD')
        if st.session_state.boq_items:
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            display_total = convert_currency(total_cost, 'INR') if currency == 'INR' else total_cost
            st.metric("Subtotal", format_currency(display_total, currency))
        else:
            st.metric("Subtotal", format_currency(0, currency))
    
    with col_status3:
        if st.button("🔄 Refresh BOQ Display"):
            update_boq_content_with_current_items()
            st.success("BOQ display updated!")
            st.rerun()
    
    product_df, _, _ = load_and_validate_data()
    if product_df is None:
        st.error("Cannot load product catalog for editing")
        return
    
    tabs = st.tabs(["Edit Current BOQ", "Add Products", "Product Search"])
    with tabs[0]: edit_current_boq(currency)
    with tabs[1]: add_products_interface(product_df, currency)
    with tabs[2]: product_search_interface(product_df, currency)

def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ."""
    st.write("**Add Products to BOQ:**")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        categories = ['All'] + sorted(list(product_df['category'].unique()))
        selected_category = st.selectbox("Filter by Category", categories)
        filtered_df = product_df[product_df['category'] == selected_category] if selected_category != 'All' else product_df
        
        product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
        if not product_options:
            st.warning("No products found in selected category")
            return
            
        selected_product_str = st.selectbox("Select Product", product_options)
        selected_product = filtered_df[filtered_df.apply(lambda row: f"{row['brand']} - {row['name']}" == selected_product_str, axis=1)].iloc[0]
    
    with col2:
        quantity = st.number_input("Quantity", min_value=1, value=1, key="add_product_qty")
        base_price = float(selected_product.get('price', 0))
        display_price = convert_currency(base_price, 'INR') if currency == 'INR' else base_price
        st.metric("Unit Price", format_currency(display_price, currency))
        
        if st.button("Add to BOQ", type="primary"):
            st.session_state.boq_items.append({
                'category': selected_product.get('category', 'General'), 'name': selected_product.get('name', ''),
                'brand': selected_product.get('brand', ''), 'quantity': quantity, 'price': base_price, 'matched': True
            })
            update_boq_content_with_current_items()
            st.success(f"Added {quantity}x {selected_product['name']} to BOQ!")
            st.rerun()

def product_search_interface(product_df, currency):
    """Advanced product search interface."""
    st.write("**Search Product Catalog:**")
    search_term = st.text_input("Search products...", placeholder="Enter product name, brand, or features")
    
    if search_term:
        search_cols = ['name', 'brand', 'features']
        mask = product_df[search_cols].apply(lambda x: x.astype(str).str.contains(search_term, case=False, na=False)).any(axis=1)
        search_results = product_df[mask]
        st.write(f"Found {len(search_results)} products:")
        
        for i, product in search_results.head(10).iterrows():
            with st.expander(f"{product.get('brand', 'Unknown')} - {product.get('name', 'Unknown')[:60]}..."):
                col_a, col_b, col_c = st.columns([2, 1, 1])
                with col_a:
                    st.write(f"**Category:** {product.get('category', 'N/A')}")
                with col_b:
                    price = float(product.get('price', 0))
                    display_price = convert_currency(price, 'INR') if currency == 'INR' else price
                    st.metric("Price", format_currency(display_price, currency))
                with col_c:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        st.session_state.boq_items.append({
                            'category': product.get('category', 'General'), 'name': product.get('name', ''),
                            'brand': product.get('brand', ''), 'quantity': add_qty, 'price': price, 'matched': True
                        })
                        update_boq_content_with_current_items()
                        st.success(f"Added {add_qty}x {product['name']} to BOQ!")
                        st.rerun()

def edit_current_boq(currency):
    """Interface for editing current BOQ items."""
    if not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ first or add products manually.")
        return
    
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        with st.expander(f"{item.get('category', 'General')} - {item.get('name', 'Unknown')[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                new_name = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                new_brand = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")
            with col2:
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_category = item.get('category', 'General')
                cat_index = category_list.index(current_category) if current_category in category_list else len(category_list) - 1
                new_category = st.selectbox("Category", category_list, index=cat_index, key=f"category_{i}")
            with col3:
                safe_quantity = max(1, int(float(item.get('quantity', 1))))
                new_quantity = st.number_input("Quantity", min_value=1, value=safe_quantity, key=f"qty_{i}")
                current_price = float(item.get('price', 0))
                display_price = convert_currency(current_price, 'INR') if currency == 'INR' else current_price
                new_price = st.number_input(f"Unit Price ({currency})", min_value=0.0, value=display_price, key=f"price_{i}")
                stored_price = new_price / get_usd_to_inr_rate() if currency == 'INR' else new_price
            with col4:
                display_total = new_price * new_quantity
                st.metric("Total", format_currency(display_total, currency))
                if st.button("Remove", key=f"remove_{i}", type="secondary"):
                    items_to_remove.append(i)
            
            st.session_state.boq_items[i].update({
                'name': new_name, 'brand': new_brand, 'category': new_category, 'quantity': new_quantity, 'price': stored_price
            })

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()

# --- BOQ Generation Logic ---
def generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Generates the BOQ using the Gemini model and validates the result."""
    with st.spinner("🤖 Generating professional BOQ... This may take a moment."):
        try:
            if not model or product_df is None or product_df.empty:
                st.error("Model or product data not available.")
                return
            
            room_spec = ROOM_SPECS.get(room_type, {})
            sample_size = min(100, len(product_df))
            product_catalog_sample_df = product_df.sample(n=sample_size, random_state=1)
            
            if 'features' not in product_catalog_sample_df.columns:
                product_catalog_sample_df['features'] = product_catalog_sample_df['name']
            
            product_catalog_string = product_catalog_sample_df[['category', 'brand', 'name', 'price', 'features']].to_string()

            prompt = f"""
            You are a Professional AV Systems Engineer. Create a production-ready BOQ.
            **PROJECT SPECIFICATIONS:**
            - Room Type: {room_type} ({room_area:.0f} sq ft), Budget: {budget_tier}
            - Requirements: {features}, Infrastructure: {json.dumps(technical_reqs)}
            **GUIDELINES:**
            - Use products from the catalog sample ONLY.
            - Include all necessary mounts, cables, and power components.
            - Add line items for 'Installation Labor' (15%), 'System Warranty' (5%), and 'Project Contingency' (10%).
            **OUTPUT FORMAT:**
            - Start with a 2-sentence 'System Design Summary'.
            - Then, provide a markdown table: | Category | Brand | Product Name | Quantity | Unit Price (USD) | Total (USD) |
            **PRODUCT CATALOG SAMPLE:**
            {product_catalog_string}
            **AVIXA GUIDELINES:**
            {guidelines}
            Generate the BOQ now:
            """
            
            response = generate_with_retry(model, prompt)
            
            if response and response.text:
                boq_content = response.text
                boq_items = extract_boq_items_from_response(boq_content, product_df)
                
                validator = BOQValidator(ROOM_SPECS, product_df)
                tech_issues, tech_warnings = validator.validate_technical_requirements(boq_items, room_type, room_area)
                avixa_warnings = validate_against_avixa(model, guidelines, boq_items)
                
                st.session_state.boq_content = boq_content
                st.session_state.boq_items = boq_items
                st.session_state.validation_results = {'issues': tech_issues, 'warnings': tech_warnings + avixa_warnings}
                st.success("✅ BOQ Generated and Validated Successfully!")
            else:
                st.error("Failed to generate BOQ content from the AI model.")
                st.session_state.boq_items, st.session_state.validation_results = [], None

        except Exception as e:
            st.error(f"An error occurred during BOQ generation: {e}")
            st.session_state.boq_items, st.session_state.validation_results = [], None

# --- 3D Visualization ---
def map_equipment_type(category):
    """Map BOQ categories to 3D visualization equipment types."""
    category_lower = category.lower()
    if 'display' in category_lower or 'monitor' in category_lower or 'screen' in category_lower: return 'display'
    if 'audio' in category_lower or 'speaker' in category_lower or 'microphone' in category_lower: return 'audio'
    if 'video' in category_lower or 'camera' in category_lower: return 'camera'
    if 'control' in category_lower: return 'control'
    return 'general'

def create_3d_visualization():
    """Create production-ready 3D room visualization with realistic AV equipment."""
    st.subheader("3D Room Visualization")
    
    equipment_data = st.session_state.get('boq_items', [])
    if not equipment_data:
        st.info("🛋️ No equipment in the BOQ to visualize. Please generate a BOQ first.")
        return

    js_equipment = [{
        'id': i + 1, 'type': map_equipment_type(item.get('category', '')),
        'name': item.get('name', 'Unknown'), 'brand': item.get('brand', 'Unknown'),
        'quantity': item.get('quantity', 1), 'price': item.get('price', 0),
        'category': item.get('category', 'General')
    } for i, item in enumerate(equipment_data)]
    
    # SOLVED: Embed the JSON data directly and safely as a JavaScript literal
    js_equipment_json = json.dumps(js_equipment)

    html_content = f"""
    <!DOCTYPE html><html><head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
        <style>
            body {{ margin: 0; font-family: sans-serif; background: #111; overflow: hidden; }}
            #container {{ width: 100%; height: 700px; position: relative; }}
            .overlay {{ position: absolute; color: white; background: rgba(0,0,0,0.7); padding: 15px; border-radius: 10px; backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.1); font-size: 14px; pointer-events: none; }}
            #info {{ top: 20px; left: 20px; min-width: 280px; }}
            #controls-info {{ bottom: 20px; left: 20px; font-size: 12px; }}
            #equipment-details {{ top: 20px; right: 20px; max-width: 300px; display: none; }}
            .metric {{ display: flex; justify-content: space-between; margin: 6px 0; padding-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
            .metric:last-child {{ border-bottom: none; }}
            .metric-label {{ color: #bbb; }}
            h3 {{ margin: 0 0 10px 0; font-size: 18px; }}
        </style>
    </head><body>
        <div id="container">
            <div id="info" class="overlay">
                <h3>Professional AV Room</h3>
                <div class="metric"><span class="metric-label">Room Dimensions:</span><span>24' × 16' × 10'</span></div>
                <div class="metric"><span class="metric-label">Total Cost:</span><span id="totalCost">Calculating...</span></div>
            </div>
            <div id="equipment-details" class="overlay">
                <h3 id="equipmentName">Details</h3>
                <div class="metric"><span class="metric-label">Brand:</span><span id="equipmentBrand">-</span></div>
                <div class="metric"><span class="metric-label">Quantity:</span><span id="equipmentQuantity">-</span></div>
                <div class="metric"><span class="metric-label">Unit Price:</span><span id="equipmentPrice">-</span></div>
            </div>
            <div id="controls-info" class="overlay">
                <strong>Controls:</strong> Drag to orbit, Scroll to zoom, Right-drag to pan
            </div>
        </div>
        <script>
            let scene, camera, renderer, controls, raycaster, mouse;
            let selectedObject = null;
            const equipmentGroups = [];
            const roomConfig = {{ length: 24, width: 16, height: 10 }};
            // SOLVED: Directly assign the valid JSON object. No parsing needed.
            const avEquipment = {js_equipment_json};
            
            function init() {{
                const container = document.getElementById('container');
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x222233);
                
                camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000);
                camera.position.set(18, 12, 18);
                
                renderer = new THREE.WebGLRenderer({{ antialias: true }});
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.shadowMap.enabled = true;
                renderer.shadowMap.type = THREE.PCFSoftShadowMap;
                container.appendChild(renderer.domElement);
                
                controls = new THREE.OrbitControls(camera, renderer.domElement);
                controls.target.set(0, 4, 0);
                controls.enableDamping = true;
                controls.minDistance = 10;
                controls.maxDistance = 50;
                controls.maxPolarAngle = Math.PI / 2;

                raycaster = new THREE.Raycaster();
                mouse = new THREE.Vector2();
                
                createScene();
                updateTotalCost();
                
                renderer.domElement.addEventListener('click', onObjectClick);
                animate();
            }}
            
            function createScene() {{
                const floor = new THREE.Mesh(
                    new THREE.PlaneGeometry(roomConfig.length, roomConfig.width),
                    new THREE.MeshStandardMaterial({{ color: 0x4a4a4a, roughness: 0.8 }})
                );
                floor.rotation.x = -Math.PI / 2;
                floor.receiveShadow = true;
                scene.add(floor);
                
                const wallMaterial = new THREE.MeshStandardMaterial({{ color: 0xcccccc, roughness: 0.9 }});
                const backWall = new THREE.Mesh(new THREE.PlaneGeometry(roomConfig.length, roomConfig.height), wallMaterial);
                backWall.position.set(0, roomConfig.height / 2, -roomConfig.width / 2);
                backWall.receiveShadow = true;
                scene.add(backWall);

                const leftWall = new THREE.Mesh(new THREE.PlaneGeometry(roomConfig.width, roomConfig.height), wallMaterial);
                leftWall.position.set(-roomConfig.length / 2, roomConfig.height / 2, 0);
                leftWall.rotation.y = Math.PI / 2;
                leftWall.receiveShadow = true;
                scene.add(leftWall);
                
                // Lighting
                scene.add(new THREE.AmbientLight(0xffffff, 0.4));
                const mainLight = new THREE.DirectionalLight(0xffffff, 0.7);
                mainLight.position.set(10, 20, 10);
                mainLight.castShadow = true;
                mainLight.shadow.mapSize.set(2048, 2048);
                scene.add(mainLight);

                // Equipment and Furniture
                createConferenceTable();
                avEquipment.forEach(item => createEquipment(item));
            }}

            function createEquipment(item) {{
                 const group = new THREE.Group();
                 const material = new THREE.MeshStandardMaterial({{ color: 0x333333, roughness: 0.4 }});
                 let geometry;

                 switch(item.type) {{
                    case 'display':
                        geometry = new THREE.BoxGeometry(6, 3.5, 0.2);
                        group.position.set(0, 5.5, -roomConfig.width / 2 + 0.2);
                        break;
                    case 'camera':
                        geometry = new THREE.BoxGeometry(0.8, 0.5, 0.6);
                        group.position.set(0, 7.5, -roomConfig.width / 2 + 0.5);
                        break;
                    case 'audio':
                        geometry = new THREE.CylinderGeometry(0.7, 0.7, 0.3);
                        group.position.set(0, roomConfig.height - 0.15, 0);
                        break;
                    default:
                        geometry = new THREE.BoxGeometry(1, 1, 1);
                        group.position.set(-6, 0.5, 4);
                 }}
                const mesh = new THREE.Mesh(geometry, material);
                group.add(mesh);
                group.traverse(child => {{ child.castShadow = true; child.receiveShadow = true; }});
                group.userData = item;
                equipmentGroups.push(group);
                scene.add(group);
            }}

            function createConferenceTable() {{
                const tableMaterial = new THREE.MeshStandardMaterial({{ color: 0x755c48, roughness: 0.6 }});
                const tableTop = new THREE.Mesh(new THREE.BoxGeometry(10, 0.2, 4), tableMaterial);
                tableTop.position.y = 2.5;
                const tableBase = new THREE.Mesh(new THREE.BoxGeometry(4, 2.5, 2), tableMaterial);
                tableBase.position.y = 1.25;
                const table = new THREE.Group();
                table.add(tableTop, tableBase);
                table.traverse(child => {{ child.castShadow = true; child.receiveShadow = true; }});
                scene.add(table);
            }}

            function onObjectClick(event) {{
                const rect = renderer.domElement.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(equipmentGroups, true);
                
                if (selectedObject) selectedObject.children[0].material.emissive.setHex(0x000000);
                
                if (intersects.length > 0) {{
                    selectedObject = intersects[0].object.parent; // The group
                    selectedObject.children[0].material.emissive.setHex(0x555555);
                    showEquipmentDetails(selectedObject.userData);
                }} else {{
                    selectedObject = null;
                    document.getElementById("equipment-details").style.display = "none";
                }}
            }}

            function showEquipmentDetails(item) {{
                const detailsPanel = document.getElementById("equipment-details");
                detailsPanel.style.display = "block";
                document.getElementById("equipmentName").textContent = item.name;
                document.getElementById("equipmentBrand").textContent = item.brand;
                document.getElementById("equipmentQuantity").textContent = item.quantity;
                document.getElementById("equipmentPrice").textContent = "$" + item.price.toLocaleString();
            }}
            
            function updateTotalCost() {{
                const total = avEquipment.reduce((sum, item) => sum + item.quantity * item.price, 0);
                document.getElementById('totalCost').textContent = '$' + total.toLocaleString(undefined, {{minimumFractionDigits: 2}});
            }}
            
            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                renderer.render(scene, camera);
            }}
            
            init();
        </script>
    </body></html>
    """
    st.components.v1.html(html_content, height=720, scrolling=False)
    
    st.subheader("Equipment Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Items", sum(item.get('quantity', 0) for item in equipment_data))
    with col2:
        total_cost = sum(item.get('quantity', 0) * item.get('price', 0) for item in equipment_data)
        st.metric("Hardware Cost", f"${total_cost:,.2f}")
    with col3:
        categories = set(item.get('category', 'General') for item in equipment_data)
        st.metric("Categories", len(categories))

# --- Main Application ---
def main():
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = None
    
    product_df, guidelines, data_issues = load_and_validate_data()
    
    if data_issues:
        with st.expander("⚠️ Data Quality Issues"):
            for issue in data_issues: st.warning(issue)
    
    if product_df is None:
        st.error("Cannot load product catalog. Please check data files.")
        return
    
    model = setup_gemini()
    if not model: return
    
    project_id, quote_valid_days = create_project_header()
    
    with st.sidebar:
        st.header("Project Configuration")
        st.text_input("Client Name")
        st.text_input("Project Name")
        currency = st.selectbox("Currency", ["USD", "INR"])
        st.session_state['currency'] = currency
        
        st.markdown("---")
        room_type = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()))
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard")
        
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
        st.caption(f"Budget: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}")
    
    # SOLVED: Corrected the language in the tab headers
    tab1, tab2, tab3, tab4 = st.tabs(["Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])
    
    with tab1:
        room_area, _ = create_room_calculator()
    with tab2:
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified'", height=100)
        technical_reqs = create_advanced_requirements()
    with tab3:
        st.subheader("BOQ Generation")
        if st.button("Generate Professional BOQ", type="primary", use_container_width=True):
            generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)
        
        if st.session_state.get('boq_content') or st.session_state.get('boq_items'):
            st.markdown("---")
            display_boq_results(st.session_state.boq_content, st.session_state.validation_results, project_id, quote_valid_days)
    with tab4:
        create_3d_visualization()

if __name__ == "__main__":
    main()
