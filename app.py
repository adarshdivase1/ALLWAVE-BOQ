import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import json
import time
from io import BytesIO
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
        
        # Add features column if missing
        if 'features' not in df.columns:
            df['features'] = df['name']
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
        "area_sqft": (50, 120), "recommended_display_size": (32, 55), "viewing_distance_ft": (4, 8),
        "audio_coverage": "Near-field", "camera_type": "Fixed wide-angle", "power_requirements": "Standard 15A circuit",
        "network_ports": 2, "typical_budget_range": (5000, 15000)
    },
    "Medium Conference Room (5-10 People)": {
        "area_sqft": (150, 300), "recommended_display_size": (55, 75), "viewing_distance_ft": (8, 14),
        "audio_coverage": "Room-wide with expansion mics", "camera_type": "PTZ or wide-angle with tracking",
        "power_requirements": "20A dedicated circuit recommended", "network_ports": 3, "typical_budget_range": (15000, 35000)
    },
    "Executive Boardroom": {
        "area_sqft": (300, 600), "recommended_display_size": (75, 98), "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling or table mics", "camera_type": "Multiple cameras with auto-switching",
        "power_requirements": "30A dedicated circuit", "network_ports": 4, "typical_budget_range": (35000, 80000)
    },
    "Training Room": {
        "area_sqft": (200, 500), "recommended_display_size": (65, 86), "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed with wireless mic support", "camera_type": "Fixed or PTZ for presenter tracking",
        "power_requirements": "20A circuit with UPS backup", "network_ports": 3, "typical_budget_range": (20000, 50000)
    }
}

# --- Gemini Configuration with Retry Logic ---
def setup_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except Exception as e:
        st.error(f"Gemini API configuration failed: {e}")
        return None

def generate_with_retry(model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)
    return None

# --- BOQ Validation Engine ---
class BOQValidator:
    def __init__(self, room_specs, product_df):
        self.room_specs = room_specs
        self.product_df = product_df
    
    def validate_technical_requirements(self, boq_items, room_type, room_area=None):
        issues = []
        warnings = []
        
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
    if not guidelines or not boq_items:
        return []
    
    prompt = f"""
    You are an AVIXA Certified Technology Specialist (CTS). Review the following Bill of Quantities (BOQ) against the provided AVIXA standards.
    List any potential non-compliance issues or areas for improvement. If there are no issues, respond with 'No specific compliance issues found.'

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

# --- UI Components ---
def create_project_header():
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
    st.subheader("Room Analysis & Specifications")
    col1, col2 = st.columns(2)
    with col1:
        room_length = st.number_input("Room Length (ft)", min_value=8.0, max_value=50.0, value=16.0, key="room_length_input")
        room_width = st.number_input("Room Width (ft)", min_value=6.0, max_value=30.0, value=12.0, key="room_width_input")
        ceiling_height = st.number_input("Ceiling Height (ft)", min_value=8.0, max_value=20.0, value=9.0, key="ceiling_height_input")
    with col2:
        room_area = room_length * room_width
        st.metric("Room Area", f"{room_area:.0f} sq ft")
        recommended_type = next((rt for rt, specs in ROOM_SPECS.items() if specs["area_sqft"][0] <= room_area <= specs["area_sqft"][1]), None)
        if recommended_type:
            st.success(f"Recommended: {recommended_type}")
        else:
            st.warning("Room size outside typical ranges")
    return room_area, ceiling_height

def create_advanced_requirements():
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
        "dedicated_circuit": has_dedicated_circuit, "network_capability": network_capability, "cable_management": cable_management,
        "ada_compliance": ada_compliance, "fire_code_compliance": fire_code_compliance, "security_clearance": security_clearance
    }

# --- BOQ Document & Item Handling ---
def generate_professional_boq_document(boq_data, project_info, validation_results):
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
        doc_content += "**⚠️ Critical Issues:**\n" + "".join(f"- {issue}\n" for issue in validation_results['issues']) + "\n"
    if validation_results.get('warnings'):
        doc_content += "**⚡ Technical Recommendations & Compliance Notes:**\n" + "".join(f"- {warning}\n" for warning in validation_results['warnings']) + "\n"
    doc_content += "---\n\n"
    return doc_content

def extract_boq_items_from_response(boq_content, product_df):
    items = []
    in_table = False
    for line in boq_content.split('\n'):
        line = line.strip()
        if '|' in line and any(k in line.lower() for k in ['category', 'product', 'item']):
            in_table = True
            continue
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 3:
                category, brand = parts[0], parts[1]
                product_name = parts[2] if len(parts) > 2 else parts[1]
                quantity = next((int(p) for p in parts if p.isdigit()), 1)
                matched_product = match_product_in_database(product_name, brand, product_df)
                if matched_product:
                    items.append({
                        'category': matched_product.get('category', category), 'name': matched_product.get('name', product_name),
                        'brand': matched_product.get('brand', brand), 'quantity': quantity,
                        'price': float(matched_product.get('price', 0)), 'matched': True
                    })
                else:
                    items.append({
                        'category': normalize_category(category, product_name), 'name': product_name,
                        'brand': brand, 'quantity': quantity, 'price': 0, 'matched': False
                    })
        elif in_table and not line.startswith('|'):
            in_table = False
    return items

def match_product_in_database(product_name, brand, product_df):
    if product_df is None or product_df.empty:
        return None
    brand_matches = product_df[product_df['brand'].str.contains(brand, case=False, na=False)]
    if not brand_matches.empty:
        name_matches = brand_matches[brand_matches['name'].str.contains(product_name[:20], case=False, na=False)]
        if not name_matches.empty:
            return name_matches.iloc[0].to_dict()
    name_matches = product_df[product_df['name'].str.contains(product_name[:15], case=False, na=False)]
    return name_matches.iloc[0].to_dict() if not name_matches.empty else None

def normalize_category(category_text, product_name):
    search_text = f"{category_text} {product_name}".lower()
    if any(term in search_text for term in ['display', 'monitor', 'screen', 'projector', 'tv']): return 'Displays'
    if any(term in search_text for term in ['audio', 'speaker', 'microphone', 'sound', 'amplifier']): return 'Audio'
    if any(term in search_text for term in ['video', 'conferencing', 'camera', 'codec', 'rally']): return 'Video Conferencing'
    if any(term in search_text for term in ['control', 'processor', 'switch', 'matrix']): return 'Control'
    if any(term in search_text for term in ['mount', 'bracket', 'rack', 'stand']): return 'Mounts'
    if any(term in search_text for term in ['cable', 'connect', 'wire', 'hdmi', 'usb']): return 'Cables'
    return 'General'

def update_boq_content_with_current_items():
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        return
    boq_content = "## Updated Bill of Quantities\n\n| Category | Brand | Product Name | Quantity | Unit Price (USD) | Total (USD) |\n|---|---|---|---|---|---|\n"
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

# --- Main Display & Editing UI ---
def display_boq_results(boq_content, validation_results, project_id, quote_valid_days, product_df):
    item_count = len(st.session_state.get('boq_items', []))
    st.subheader(f"Generated Bill of Quantities ({item_count} items)")
    
    if validation_results and validation_results.get('issues'):
        st.error("Critical Issues Found:")
        for issue in validation_results['issues']: st.write(f"- {issue}")
    if validation_results and validation_results.get('warnings'):
        st.warning("Technical Recommendations & Compliance Notes:")
        for warning in validation_results['warnings']: st.write(f"- {warning}")
    
    st.markdown(boq_content if boq_content else "No BOQ content generated yet. Use the editor below to add items manually.")
    
    if st.session_state.get('boq_items'):
        currency = st.session_state.get('currency', 'USD')
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        display_total = convert_currency(total_cost, 'INR') if currency == 'INR' else total_cost
        st.metric("Current BOQ Total", format_currency(display_total * 1.30, currency), help="Includes installation, warranty, and contingency")
    
    st.markdown("---")
    create_interactive_boq_editor(product_df)
    
    # Download Buttons
    col1, col2 = st.columns(2)
    boq_exists = st.session_state.get('boq_items')
    with col1:
        if boq_exists:
            doc_content = generate_professional_boq_document(
                {'design_summary': boq_content.split('---')[0] if boq_content and '---' in boq_content else ""}, 
                {'project_id': project_id, 'quote_valid_days': quote_valid_days}, validation_results or {}
            )
            final_doc = doc_content + "\n" + (boq_content or "")
            st.download_button("Download BOQ (Markdown)", final_doc, f"{project_id}_BOQ.md", "text/markdown")
        else:
            st.button("Download BOQ (Markdown)", disabled=True)
    with col2:
        if boq_exists:
            df_to_download = pd.DataFrame(st.session_state.boq_items)
            df_to_download['price'] = pd.to_numeric(df_to_download['price'], errors='coerce').fillna(0)
            df_to_download['quantity'] = pd.to_numeric(df_to_download['quantity'], errors='coerce').fillna(0)
            df_to_download['total'] = df_to_download['price'] * df_to_download['quantity']
            csv_data = df_to_download[['category', 'brand', 'name', 'quantity', 'price', 'total']].to_csv(index=False).encode('utf-8')
            st.download_button("Download BOQ (CSV)", csv_data, f"{project_id}_BOQ.csv", "text/csv")
        else:
            st.button("Download BOQ (CSV)", disabled=True)

def create_interactive_boq_editor(product_df):
    st.subheader("Interactive BOQ Editor")
    
    item_count = len(st.session_state.get('boq_items', []))
    col_status1, col_status2, col_status3 = st.columns(3)
    with col_status1:
        st.metric("Items in BOQ", item_count)
    with col_status2:
        if st.session_state.get('boq_items'):
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            currency = st.session_state.get('currency', 'USD')
            display_total = convert_currency(total_cost, 'INR') if currency == 'INR' else total_cost
            st.metric("Subtotal", format_currency(display_total, currency))
        else:
            st.metric("Subtotal", "₹0" if st.session_state.get('currency', 'USD') == 'INR' else "$0")
    with col_status3:
        if st.button("🔄 Refresh BOQ Display"):
            update_boq_content_with_current_items()
            st.rerun()
    
    if product_df is None:
        st.error("Cannot load product catalog for editing")
        return
    
    currency = st.session_state.get('currency', 'USD')
    tabs = st.tabs(["Edit Current BOQ", "Add Products", "Product Search"])
    with tabs[0]:
        edit_current_boq(currency)
    with tabs[1]:
        add_products_interface(product_df, currency)
    with tabs[2]:
        product_search_interface(product_df, currency)

def add_products_interface(product_df, currency):
    st.write("**Add Products to BOQ:**")
    col1, col2 = st.columns([2, 1])
    with col1:
        categories = ['All'] + sorted(list(product_df['category'].unique()))
        selected_category = st.selectbox("Filter by Category", categories, key="add_category_filter")
        filtered_df = product_df[product_df['category'] == selected_category] if selected_category != 'All' else product_df
        product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
        if not product_options:
            st.warning("No products found in selected category")
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
                st.session_state.boq_items.append({
                    'category': selected_product.get('category', 'General'), 'name': selected_product.get('name', ''),
                    'brand': selected_product.get('brand', ''), 'quantity': quantity,
                    'price': base_price, 'matched': True
                })
                update_boq_content_with_current_items()
                st.success(f"Added {quantity}x {selected_product['name']} to BOQ!")
                st.rerun()

def product_search_interface(product_df, currency):
    st.write("**Search Product Catalog:**")
    search_term = st.text_input("Search products...", placeholder="Enter name, brand, or features", key="search_term_input")
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
                    if pd.notna(product.get('features')): st.write(f"**Features:** {str(product['features'])[:100]}...")
                with col_b:
                    price = float(product.get('price', 0))
                    display_price = convert_currency(price, 'INR') if currency == 'INR' else price
                    st.metric("Price", format_currency(display_price, currency))
                with col_c:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        st.session_state.boq_items.append({
                            'category': product.get('category', 'General'), 'name': product.get('name', ''),
                            'brand': product.get('brand', ''), 'quantity': add_qty,
                            'price': price, 'matched': True
                        })
                        update_boq_content_with_current_items()
                        st.success(f"Added {add_qty}x {product['name']} to BOQ!")
                        st.rerun()

def edit_current_boq(currency):
    if not st.session_state.get('boq_items'):
        st.info("No BOQ items to edit. Generate a BOQ or add products manually.")
        return
    
    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    items_to_remove = []
    
    for i, item in enumerate(st.session_state.boq_items):
        category_str = str(item.get('category', 'General'))
        name_str = str(item.get('name', 'Unknown'))
        
        # CORRECTED: Removed invalid `key` argument from st.expander
        with st.expander(f"{category_str} - {name_str[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                new_name = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                new_brand = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")
            with col2:
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_category_idx = category_list.index(item['category']) if item.get('category') in category_list else 6
                new_category = st.selectbox("Category", category_list, index=current_category_idx, key=f"category_{i}")
            with col3:
                try: safe_quantity = max(1, int(float(item.get('quantity', 1))))
                except (ValueError, TypeError): safe_quantity = 1
                new_quantity = st.number_input("Quantity", min_value=1, value=safe_quantity, key=f"qty_{i}")
                
                try: current_price = float(item.get('price', 0))
                except (ValueError, TypeError): current_price = 0
                display_price = convert_currency(current_price, 'INR') if currency == 'INR' else current_price
                new_price = st.number_input(f"Unit Price ({currency})", min_value=0.0, value=display_price, key=f"price_{i}")
                stored_price = new_price / get_usd_to_inr_rate() if currency == 'INR' else new_price
            with col4:
                total_price = stored_price * new_quantity
                display_total = convert_currency(total_price, 'INR') if currency == 'INR' else total_price
                st.metric("Total", format_currency(display_total, currency))
                if st.button("Remove", key=f"remove_{i}"):
                    items_to_remove.append(i)
            
            item.update({'name': new_name, 'brand': new_brand, 'category': new_category, 'quantity': new_quantity, 'price': stored_price})

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        update_boq_content_with_current_items()
        st.rerun()

# --- Visualization Functions ---
def map_equipment_type(category, product_name=""):
    search_text = f"{category} {product_name}".lower()
    if any(term in search_text for term in ['display', 'monitor', 'screen', 'projector', 'tv']): return 'display'
    if any(term in search_text for term in ['speaker', 'audio', 'sound', 'amplifier']): return 'audio_speaker'
    if any(term in search_text for term in ['microphone', 'mic']): return 'audio_microphone'
    if any(term in search_text for term in ['camera', 'video', 'conferencing', 'codec']): return 'camera'
    if any(term in search_text for term in ['switch', 'network', 'poe']): return 'network_switch'
    if any(term in search_text for term in ['access point', 'transceiver', 'wireless', 'ap']): return 'network_device'
    if any(term in search_text for term in ['charging', 'charger', 'battery']): return 'charging_station'
    if any(term in search_text for term in ['scheduler', 'controller', 'touch panel', 'tap']): return 'control_panel'
    if any(term in search_text for term in ['control', 'processor', 'matrix', 'hub']): return 'control'
    if any(term in search_text for term in ['rack', 'cabinet']): return 'rack'
    if any(term in search_text for term in ['mount', 'bracket', 'stand']): return 'mount'
    if any(term in search_text for term in ['cable', 'wire', 'connector']): return 'cable'
    if any(term in search_text for term in ['installation', 'labor', 'service']): return 'service'
    if any(term in search_text for term in ['power', 'ups', 'supply']): return 'power'
    return 'control'

def get_equipment_specs(equipment_type, product_name=""):
    default_specs = {
        'display': [4, 2.5, 0.2], 'audio_speaker': [0.6, 1.0, 0.6], 'audio_microphone': [0.2, 0.1, 0.2],
        'camera': [1.0, 0.4, 0.6], 'control': [1.2, 0.6, 0.2], 'control_panel': [0.8, 0.5, 0.1],
        'network_switch': [1.3, 0.15, 1.0], 'network_device': [0.8, 0.8, 0.3], 'charging_station': [1.0, 0.3, 0.8],
        'rack': [1.5, 5, 1.5], 'mount': [0.3, 0.3, 0.8], 'cable': [0.1, 0.1, 2], 'power': [1.0, 0.4, 0.8], 'service': [0, 0, 0]
    }
    base_spec = default_specs.get(equipment_type, [1, 1, 1])
    if equipment_type == 'display' and product_name:
        size_match = re.search(r'(\d+)"', product_name)
        if size_match:
            size_inches = int(size_match.group(1))
            return [size_inches * 0.87 / 12, size_inches * 0.49 / 12, 0.2]
    return base_spec

def create_3d_visualization():
    st.subheader("3D Room Visualization")
    if not st.session_state.get('boq_items'):
        st.info("No BOQ items to visualize. Generate a BOQ or add items manually.")
        return
    
    js_equipment = []
    for item in st.session_state.boq_items:
        equipment_type = map_equipment_type(item.get('category', ''), item.get('name', ''))
        if equipment_type == 'service': continue
        specs = get_equipment_specs(equipment_type, item.get('name', ''))
        try: quantity = int(item.get('quantity', 1))
        except (ValueError, TypeError): quantity = 1
        for i in range(quantity):
            js_equipment.append({
                'id': len(js_equipment) + 1, 'type': equipment_type,
                'name': item.get('name', 'Unknown'), 'brand': item.get('brand', 'Unknown'),
                'price': float(item.get('price', 0)), 'instance': i + 1,
                'original_quantity': quantity, 'specs': specs
            })
    
    if not js_equipment:
        st.warning("No visualizable equipment found in BOQ.")
        return
    
    room_length = st.session_state.get('room_length', 24)
    room_width = st.session_state.get('room_width', 16)
    room_height = st.session_state.get('room_height', 9)
    st.info(f"Visualizing {len(js_equipment)} equipment instances from BOQ")
    
    html_content = f"""
    <!DOCTYPE html><html><head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body {{ margin: 0; font-family: sans-serif; }} #container {{ width: 100%; height: 600px; position: relative; cursor: grab; }}
            #container:active {{ cursor: grabbing; }} #info {{ position: absolute; top: 15px; left: 15px; color: #fff; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 12px; width: 320px; display: flex; flex-direction: column; max-height: 570px; }}
            .equipment-manifest {{ flex-grow: 1; overflow-y: auto; margin-top: 10px; }} .equipment-item {{ margin: 4px 0; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; border-left: 3px solid transparent; cursor: pointer; transition: all 0.2s ease; }}
            .equipment-item:hover {{ background: rgba(255,255,255,0.15); }} .equipment-item.selected-item {{ background: rgba(79, 195, 247, 0.2); border-left: 3px solid #4FC3F7; }}
            .equipment-name {{ color: #FFD54F; font-weight: bold; font-size: 13px; }} .equipment-details {{ color: #ccc; font-size: 11px; }}
            #selectedItemInfo {{ padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.2); margin-top: 10px; }}
        </style></head><body><div id="container"><div id="info">
            <div><h3 style="margin-top: 0; color: #4FC3F7; font-size: 16px;">Equipment Manifest</h3><div style="font-size: 12px; color: #ccc;">Total Instances: <span style="color: #4FC3F7; font-weight: bold;">{len(js_equipment)}</span></div></div>
            <div class="equipment-manifest" id="equipmentList"></div><div id="selectedItemInfo"><strong>Click an object or list item</strong></div>
        </div></div><script>
            let scene, camera, renderer, raycaster, mouse, selectedObject = null;
            const toUnits = (feet) => feet * 0.4; let avEquipment = {js_equipment};
            function init() {{
                scene = new THREE.Scene(); scene.background = new THREE.Color(0x334455);
                const container = document.getElementById('container');
                camera = new THREE.PerspectiveCamera(50, container.clientWidth / 600, 0.1, 1000);
                camera.position.set(toUnits(-{room_length} * 0.1), toUnits({room_height} * 0.8), toUnits({room_width} * 1.1));
                renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
                renderer.setSize(container.clientWidth, 600); renderer.setPixelRatio(window.devicePixelRatio); renderer.shadowMap.enabled = true;
                container.appendChild(renderer.domElement);
                raycaster = new THREE.Raycaster(); mouse = new THREE.Vector2();
                createRealisticRoom(); createRoomFurniture(); createAllEquipmentObjects(); setupCameraControls(); updateEquipmentList(); animate();
            }}
            function createRealisticRoom() {{
                scene.add(new THREE.HemisphereLight(0x8899aa, 0x555555, 0.8));
                const dirLight = new THREE.DirectionalLight(0xffeedd, 0.7); dirLight.position.set(toUnits(-5), toUnits(8), toUnits(5)); dirLight.castShadow = true; scene.add(dirLight);
                const wallMat = new THREE.MeshStandardMaterial({{ color: 0xddeeff, roughness: 0.9 }});
                const floorMat = new THREE.MeshStandardMaterial({{ color: 0x6e5a47, roughness: 0.7 }});
                const wallH = toUnits({room_height});
                const floor = new THREE.Mesh(new THREE.PlaneGeometry(toUnits({room_length}), toUnits({room_width})), floorMat); floor.rotation.x = -Math.PI/2; floor.receiveShadow = true; scene.add(floor);
                const backWall = new THREE.Mesh(new THREE.PlaneGeometry(toUnits({room_length}), wallH), wallMat); backWall.position.set(0, wallH/2, -toUnits({room_width}/2)); backWall.receiveShadow = true; scene.add(backWall);
                const leftWall = new THREE.Mesh(new THREE.PlaneGeometry(toUnits({room_width}), wallH), wallMat); leftWall.position.set(-toUnits({room_length}/2), wallH/2, 0); leftWall.rotation.y = Math.PI/2; leftWall.receiveShadow = true; scene.add(leftWall);
            }}
            function createRoomFurniture() {{
                const tableMat = new THREE.MeshStandardMaterial({{ color: 0x4d3a2a, roughness: 0.6 }});
                const table = new THREE.Mesh(new THREE.BoxGeometry(toUnits(12), toUnits(0.2), toUnits(5)), tableMat); table.position.y = toUnits(2.5); table.castShadow = true; scene.add(table);
            }}
            function createAllEquipmentObjects() {{ avEquipment.forEach(item => scene.add(createEquipmentMesh(item))); }}
            function createEquipmentMesh(item) {{
                const group = new THREE.Group(); const size = item.specs;
                const mat = new THREE.MeshStandardMaterial({{ color: 0x333333, roughness: 0.5, metalness: 0.1 }});
                const geom = new THREE.BoxGeometry(toUnits(size[0]), toUnits(size[1]), toUnits(size[2]));
                const mesh = new THREE.Mesh(geom, mat); mesh.castShadow = true; group.add(mesh);
                const pos = getSmartPosition(item.type, item.instance - 1, item.original_quantity); group.position.set(pos.x, pos.y, pos.z);
                group.userData = item; group.name = `equipment_${{item.id}}`; return group;
            }}
            function getSmartPosition(type, index, quantity) {{
                let x_ft=0, y_ft=0, z_ft=0;
                if (type === 'display') {{ x_ft = -(quantity - 1) * 4 / 2 + (index * 4); y_ft = {room_height}*0.6; z_ft = -{room_width}/2+0.2; }}
                else if (type === 'camera') {{ y_ft = {room_height} - 0.5; z_ft = -{room_width}/2+1; }}
                else if (type === 'audio_speaker') {{ x_ft=(index % 2 * {room_length}/2) - {room_length}/4; y_ft={room_height}-0.5; z_ft=(Math.floor(index/2)*{room_width}/2)-{room_width}/4; }}
                else {{ x_ft = -{room_length}/3 + (index * 3); y_ft = 1; z_ft = {room_width}/3; }}
                return {{ x: toUnits(x_ft), y: toUnits(y_ft), z: toUnits(z_ft) }};
            }}
            function selectObject(target) {{
                if (selectedObject) {{ selectedObject.traverse(c => {{ if(c.isMesh) c.material.emissive.setHex(0x000000); }}); }}
                document.querySelectorAll('.equipment-item').forEach(li => li.classList.remove('selected-item'));
                selectedObject = target;
                if (!selectedObject) {{ document.getElementById('selectedItemInfo').innerHTML = '<strong>Click an object</strong>'; return; }}
                selectedObject.traverse(c => {{ if(c.isMesh) c.material.emissive.setHex(0x555555); }});
                const item = selectedObject.userData; const i_txt = item.original_quantity > 1 ? ` (${{item.instance}}/${{item.original_quantity}})` : '';
                document.getElementById('selectedItemInfo').innerHTML = `<div class="equipment-name">${{item.name}}${{i_txt}}</div><div class="equipment-details"><div><strong>Brand:</strong> ${{item.brand}}</div><div><strong>Type:</strong> ${{item.type.replace('_', ' ')}}</div><div><strong>Price:</strong> $$${{item.price.toLocaleString()}}</div></div>`;
                const listItem = document.getElementById(`list-item-${{item.id}}`); if (listItem) {{ listItem.classList.add('selected-item'); listItem.scrollIntoView({{block: 'nearest'}}); }}
            }}
            function updateEquipmentList() {{
                let html = ''; avEquipment.forEach(item => {{
                    const i_txt = item.original_quantity > 1 ? ` (${{item.instance}}/${{item.original_quantity}})` : '';
                    html += `<div class="equipment-item" id="list-item-${{item.id}}" onclick="highlightObjectById(${{item.id}})">
                                <div class="equipment-name">${{item.name}}${{i_txt}}</div>
                                <div class="equipment-details">${{item.brand}} - ${{item.type.replace('_',' ')}}</div></div>`;
                }}); document.getElementById('equipmentList').innerHTML = html;
            }}
            function highlightObjectById(id) {{ const obj = scene.getObjectByName(`equipment_${{id}}`); if(obj) selectObject(obj); }}
            function onMouseClick(e) {{
                const rect = renderer.domElement.getBoundingClientRect();
                mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1; mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);
                if (intersects.length > 0) {{
                    let parent = intersects[0].object;
                    while(parent) {{
                        if (parent.userData && parent.userData.id) {{ selectObject(parent); return; }}
                        parent = parent.parent;
                    }}
                }}
            }}
            function setupCameraControls() {{
                let isDragging = false; let prev = {{x:0, y:0}}; const rotSpeed = 0.005; const zoomSpeed = 0.1;
                renderer.domElement.addEventListener('mousedown', (e) => {{ isDragging=true; prev={{x:e.clientX, y:e.clientY}}; }});
                renderer.domElement.addEventListener('mouseup', () => isDragging=false);
                renderer.domElement.addEventListener('mousemove', (e) => {{ if(!isDragging) return;
                    const delta = {{x:e.clientX-prev.x, y:e.clientY-prev.y}};
                    const s = new THREE.Spherical().setFromVector3(camera.position);
                    s.theta -= delta.x*rotSpeed; s.phi = Math.max(0.1, Math.min(Math.PI-0.1, s.phi+delta.y*rotSpeed));
                    camera.position.setFromSpherical(s); camera.lookAt(0, toUnits(4), 0); prev={{x:e.clientX, y:e.clientY}};
                }});
                renderer.domElement.addEventListener('wheel', (e) => {{ e.preventDefault();
                    const factor = e.deltaY > 0 ? 1+zoomSpeed : 1-zoomSpeed; camera.position.multiplyScalar(factor);
                    const dist = camera.position.length();
                    if(dist<toUnits(5)) camera.position.normalize().multiplyScalar(toUnits(5));
                    if(dist>toUnits(50)) camera.position.normalize().multiplyScalar(toUnits(50));
                }});
                renderer.domElement.addEventListener('click', onMouseClick);
            }}
            function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
            init();
        </script></body></html>
    """
    st.components.v1.html(html_content, height=650)

# --- Main Application Logic ---
def main():
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = None
    
    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=len(data_issues) > 2):
            for issue in data_issues: st.warning(issue)
    if product_df is None:
        st.error("Cannot load product catalog. Please check data files and restart.")
        return
    
    model = setup_gemini()
    if not model: return
    
    project_id, quote_valid_days = create_project_header()
    
    with st.sidebar:
        st.header("Project Configuration")
        client_name = st.text_input("Client Name", key="client_name_input")
        project_name = st.text_input("Project Name", key="project_name_input")
        st.session_state['currency'] = st.selectbox("Currency", ["USD", "INR"], index=1, key="currency_select")
        st.markdown("---")
        room_type = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])
    
    with tab1:
        room_area, ceiling_height = create_room_calculator()
        st.session_state.room_length = st.session_state.get('room_length_input', 16.0)
        st.session_state.room_width = st.session_state.get('room_width_input', 12.0)
        st.session_state.room_height = st.session_state.get('ceiling_height_input', 9.0)

    with tab2:
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., Dual displays, wireless presentation, Zoom certified", height=100, key="features_text_area")
        technical_reqs = create_advanced_requirements()
    
    with tab3:
        st.subheader("BOQ Generation")
        if st.button("Generate Professional BOQ", type="primary", use_container_width=True):
            generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)
        
        if st.session_state.get('boq_content') or st.session_state.get('boq_items'):
            display_boq_results(st.session_state.boq_content, st.session_state.validation_results, project_id, quote_valid_days, product_df)
    
    with tab4:
        create_3d_visualization()

def generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    with st.spinner("Engineering professional BOQ with technical validation..."):
        prompt = create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)
        try:
            response = generate_with_retry(model, prompt)
            if response:
                boq_content = response.text
                boq_items = extract_boq_items_from_response(boq_content, product_df)
                validator = BOQValidator(ROOM_SPECS, product_df)
                issues, warnings = validator.validate_technical_requirements(boq_items, room_type, room_area)
                warnings.extend(validate_against_avixa(model, guidelines, boq_items))
                
                st.session_state.boq_content = boq_content
                st.session_state.boq_items = boq_items
                st.session_state.validation_results = {"issues": issues, "warnings": warnings}
                st.success(f"✅ Successfully generated and loaded {len(boq_items)} items!")
        except Exception as e:
            st.error(f"BOQ generation failed: {str(e)}")

def create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    room_spec = ROOM_SPECS[room_type]
    product_catalog_string = product_df.head(100).to_csv(index=False)
    return f"""
You are a Professional AV Systems Engineer. Create a production-ready BOQ.
**PROJECT SPECIFICATIONS:**
- Room Type: {room_type}, Area: {room_area:.0f} sq ft, Budget: {budget_tier}
- Requirements: {features}, Infrastructure: {technical_reqs}
**GUIDELINES:**
- Adhere to AVIXA standards. Display size: {room_spec['recommended_display_size'][0]}"-{room_spec['recommended_display_size'][1]}".
- ONLY use products from the provided catalog sample. Note if a suitable product is missing.
- Include all necessary mounting, cabling, and power hardware.
- Add line items for 'Installation Labor' (15%), 'System Warranty' (5%), and 'Project Contingency' (10%).
**OUTPUT FORMAT:**
- Start with a 2-3 sentence 'System Design Summary'.
- Then, provide the BOQ in a markdown table with columns: | Category | Brand | Product Name | Quantity | Unit Price (USD) | Total (USD) |
**PRODUCT CATALOG SAMPLE:**
{product_catalog_string}
**AVIXA GUIDELINES:**
{guidelines}
Generate the BOQ now:
"""

if __name__ == "__main__":
    main()
