import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import json
import time

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

        # Check for zero/missing prices
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
            zero_price_count = (df['price'] == 0.0).sum()
            if zero_price_count > 100:  # Allow some zero prices for accessories
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

        # Features column
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
        "area_sqft": (50, 120), "recommended_display_size": (43, 65), "viewing_distance_ft": (4, 8),
        "audio_coverage": "Integrated Mic/Speaker Bar", "camera_type": "Fixed wide-angle ePTZ",
        "power_requirements": "Standard 15A circuit", "typical_budget_range": (5000, 15000)
    },
    "Medium Conference Room (5-10 People)": {
        "area_sqft": (150, 300), "recommended_display_size": (65, 85), "viewing_distance_ft": (8, 14),
        "audio_coverage": "Video bar with mic pod extensions", "camera_type": "PTZ or wide-angle with tracking",
        "power_requirements": "20A dedicated circuit recommended", "typical_budget_range": (15000, 35000)
    },
    "Executive Boardroom": {
        "area_sqft": (300, 600), "recommended_display_size": (85, 98), "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling or table microphones", "camera_type": "Intelligent multi-camera system",
        "power_requirements": "30A dedicated circuit with power conditioning", "typical_budget_range": (40000, 90000)
    },
    "Training Room": {
        "area_sqft": (400, 800), "recommended_display_size": (75, 98), "viewing_distance_ft": (10, 20),
        "audio_coverage": "Distributed ceiling speakers with wireless presenter mics", "camera_type": "Presenter tracking camera",
        "power_requirements": "20A circuit with UPS backup", "typical_budget_range": (30000, 70000)
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
    def __init__(self, room_specs):
        self.room_specs = room_specs

    def validate_technical_requirements(self, boq_items, room_type):
        issues = []
        warnings = []
        room_spec = self.room_specs.get(room_type, {})
        
        # Check for essential components
        categories = {item.get('category', '').lower() for item in boq_items}
        if not any('display' in cat for cat in categories):
            issues.append("Missing essential component: Display")
        if not any('audio' in cat for cat in categories):
            issues.append("Missing essential component: Audio System")
        if not any('video conferencing' in cat for cat in categories):
            issues.append("Missing essential component: Video Conferencing System")

        # Check display size
        for item in boq_items:
            if 'display' in item.get('category', '').lower():
                size_match = re.search(r'(\d+)"', item.get('name', ''))
                if size_match and room_spec:
                    size = int(size_match.group(1))
                    min_size, max_size = room_spec.get('recommended_display_size', (0, 100))
                    if not (min_size <= size <= max_size):
                        warnings.append(f"Display size of {size}\" is outside the recommended range ({min_size}\" - {max_size}\") for a {room_type}.")
        
        return issues, warnings

# --- Enhanced UI Components ---
def create_project_header():
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("Professional AV BOQ Generator")
        st.caption("Production-ready Bill of Quantities with AI-powered logical validation")
    with col2:
        project_id = st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}")
    with col3:
        quote_valid_days = st.number_input("Quote Valid (Days)", 15, 90, 30)
    return project_id, quote_valid_days

def create_room_calculator():
    st.subheader("Room Analysis & Specifications")
    col1, col2 = st.columns(2)
    with col1:
        room_length = st.number_input("Room Length (ft)", 8.0, 60.0, 24.0)
        room_width = st.number_input("Room Width (ft)", 6.0, 40.0, 15.0)
    with col2:
        room_area = room_length * room_width
        st.metric("Room Area", f"{room_area:.0f} sq ft")
        recommended_type = next((rt for rt, spec in ROOM_SPECS.items() if spec["area_sqft"][0] <= room_area <= spec["area_sqft"][1]), None)
        if recommended_type:
            st.success(f"Recommended Space Type: {recommended_type}")
        else:
            st.warning("Room size is outside typical ranges.")
    return room_area

def create_advanced_requirements():
    st.subheader("Technical & Compliance Requirements")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Infrastructure**")
        has_dedicated_circuit = st.checkbox("Dedicated 20A+ Circuit Available")
        network_capability = st.selectbox("Network Infrastructure", ["Standard 1Gb", "10Gb Capable", "Fiber Available"])
        cable_management = st.selectbox("Cable Management", ["Conduit", "Raised Floor", "Drop Ceiling", "Exposed"])
    with col2:
        st.write("**Compliance & Standards**")
        ada_compliance = st.checkbox("ADA Compliance Required")
        security_clearance = st.selectbox("Security Level", ["Standard", "Restricted", "Classified"])
    return {"dedicated_circuit": has_dedicated_circuit, "network_capability": network_capability,
            "cable_management": cable_management, "ada_compliance": ada_compliance, "security_clearance": security_clearance}

# --- BOQ Item Extraction & Normalization ---
def extract_boq_items_from_response(boq_content, product_df):
    items = []
    lines = boq_content.split('\n')
    in_table = False
    for line in lines:
        line = line.strip()
        if '|' in line and any(keyword in line.lower() for keyword in ['category', 'product', 'brand']):
            in_table = True
            continue
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 3:
                category, brand, product_name = parts[0], parts[1], parts[2]
                quantity = next((int(p) for p in parts if p.isdigit()), 1)
                
                matched_product = match_product_in_database(product_name, brand, product_df)
                price = float(matched_product['price']) if matched_product else 0
                
                items.append({
                    'category': matched_product.get('category', normalize_category(category, product_name)),
                    'name': matched_product.get('name', product_name),
                    'brand': matched_product.get('brand', brand),
                    'quantity': quantity,
                    'price': price,
                    'matched': matched_product is not None
                })
        elif in_table and not line.startswith('|'):
            in_table = False
    return items

def match_product_in_database(product_name, brand, product_df):
    if product_df is None or product_df.empty: return None
    brand_matches = product_df[product_df['brand'].str.contains(brand, case=False, na=False)]
    if not brand_matches.empty:
        name_matches = brand_matches[brand_matches['name'].str.contains(product_name[:20], case=False, na=False)]
        if not name_matches.empty: return name_matches.iloc[0].to_dict()
    name_matches = product_df[product_df['name'].str.contains(product_name[:15], case=False, na=False)]
    return name_matches.iloc[0].to_dict() if not name_matches.empty else None

def normalize_category(category_text, product_name):
    cat_lower, prod_lower = category_text.lower(), product_name.lower()
    if any(term in cat_lower or term in prod_lower for term in ['display', 'monitor', 'screen']): return 'Displays'
    if any(term in cat_lower or term in prod_lower for term in ['audio', 'speaker', 'mic', 'amp']): return 'Audio'
    if any(term in cat_lower or term in prod_lower for term in ['video', 'cam', 'codec']): return 'Video Conferencing'
    if any(term in cat_lower or term in prod_lower for term in ['control', 'processor', 'switch']): return 'Control'
    if any(term in cat_lower or term in prod_lower for term in ['mount', 'rack', 'stand']): return 'Mounts'
    if any(term in cat_lower or term in prod_lower for term in ['cable', 'connect', 'wire']): return 'Cables'
    return 'General'

# --- Main Application ---
def main():
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = None

    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=True):
            for issue in data_issues: st.warning(issue)
    if product_df is None:
        st.error("Cannot load product catalog. Please check data files.")
        return

    model = setup_gemini()
    if not model: return

    project_id, quote_valid_days = create_project_header()

    with st.sidebar:
        st.header("Project Configuration")
        currency = st.selectbox("Currency", ["USD", "INR"], index=1)
        st.session_state['currency'] = currency
        st.markdown("---")
        room_type = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), index=2)
        budget_tier = st.select_slider("Budget Tier:", options=["Standard", "Premium", "Enterprise"], value="Premium")
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Display: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
        st.caption(f"Audio: {room_spec['audio_coverage']}")
        st.caption(f"Budget: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}")

    tab1, tab2, tab3, tab4 = st.tabs(["Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])

    with tab1:
        room_area = create_room_calculator()
    with tab2:
        features = st.text_area("Specific Requirements & Features:",
                                placeholder="e.g., 'Dual 98\" displays, voice-activated controls, seamless integration with existing room scheduling panels, must be certified for both Microsoft Teams and Zoom.'",
                                height=100)
        technical_reqs = create_advanced_requirements()

    with tab3:
        st.subheader("BOQ Generation")
        if st.button("🚀 Generate Powerful & Logical BOQ", type="primary", use_container_width=True):
            generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)

        if st.session_state.boq_content:
            st.markdown("---")
            display_boq_results(st.session_state.boq_content, st.session_state.validation_results, project_id, quote_valid_days)

    with tab4:
        create_3d_visualization_placeholder()

def generate_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    with st.spinner("Engineering a cohesive AV solution..."):
        prompt = create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)
        try:
            response = generate_with_retry(model, prompt)
            if response and response.text:
                boq_content = response.text
                boq_items = extract_boq_items_from_response(boq_content, product_df)
                validator = BOQValidator(ROOM_SPECS)
                issues, warnings = validator.validate_technical_requirements(boq_items, room_type)
                
                st.session_state.boq_content = boq_content
                st.session_state.boq_items = boq_items
                st.session_state.validation_results = {"issues": issues, "warnings": warnings}
                
                st.success(f"✅ Successfully engineered a logical BOQ with {len(boq_items)} items!")
            else:
                st.error("Failed to generate a response from the model.")
        except Exception as e:
            st.error(f"BOQ generation failed: {str(e)}")

def create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    room_spec = ROOM_SPECS[room_type]
    product_catalog_string = product_df.head(150).to_csv(index=False)
    
    return f"""
You are a world-class AV Systems Design Engineer. Your task is to create a powerful, logical, and fully integrated Bill of Quantities (BOQ). The system must be coherent; every component must be chosen to work together as a seamless solution. **Do not simply list expensive parts; create a cohesive system.**

**CRITICAL DESIGN PHILOSOPHY:**
- For **Huddle/Medium Rooms**, prioritize high-quality all-in-one video bars (like Poly Studio series) for simplicity and performance.
- For **Executive Boardrooms/Training Rooms**, you MUST design a **modular system**. Use a dedicated video codec (like Poly G7500), pair it with a separate, high-performance camera (like Poly E70), and a dedicated audio system (ceiling mics, DSP, amps). **Do not use an all-in-one video bar in a premium modular design.**

**PROJECT SPECIFICATIONS:**
- **Room Type:** {room_type} ({budget_tier} Tier)
- **Room Area:** Approx. {room_area:.0f} sq ft
- **User Requirements:** {features}
- **Infrastructure:** {technical_reqs}

**OUTPUT REQUIREMENTS (Strictly follow this order):**
1.  **Executive Summary:** Start with a confident 2-3 sentence paragraph explaining the design philosophy and the value it brings to the user.
2.  **Technical Validation & AVIXA Standards Compliance:** Write a brief section explaining HOW your design choices (e.g., display size, audio solution) align with AVIXA standards for the specified room type. Be specific.
3.  **Itemized Bill of Quantities:** Provide a markdown table with these exact columns: | Category | Brand | Product Name | Qty | Unit Price (USD) | Total (USD) |
4.  **Project Cost Summary:** Create a second, simple markdown table for soft costs.
5.  **Mandatory Inclusions:** Your design must include an equipment rack, power management/conditioning, and a line item for professional programming (Crestron/Q-SYS) if applicable. For ADA compliance, include an Assistive Listening System (ALS).

**PRODUCT CATALOG SAMPLE & GUIDELINES:**
- You can only use products from this catalog:
{product_catalog_string}
- Adhere to these guidelines:
{guidelines}

Generate the BOQ now.
"""

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days):
    st.subheader("Generated Bill of Quantities")
    
    if validation_results and validation_results.get('issues'):
        st.error("Critical Design Issues Found:")
        for issue in validation_results['issues']: st.write(f"- {issue}")
    if validation_results and validation_results.get('warnings'):
        st.warning("Design Recommendations:")
        for warning in validation_results['warnings']: st.write(f"- {warning}")
        
    st.markdown(boq_content)
    st.markdown("---")
    create_interactive_boq_editor()

    col1, col2 = st.columns(2)
    with col1:
        doc_content = f"# BOQ: {project_id}\n\n{boq_content}"
        st.download_button("Download BOQ (Markdown)", doc_content, f"{project_id}_BOQ.md", "text/markdown")
    with col2:
        if st.session_state.boq_items:
            df_to_download = pd.DataFrame(st.session_state.boq_items)
            df_to_download['total'] = pd.to_numeric(df_to_download['price']) * pd.to_numeric(df_to_download['quantity'])
            csv_data = df_to_download[['category', 'brand', 'name', 'quantity', 'price', 'total']].to_csv(index=False).encode('utf-8')
            st.download_button("Download BOQ (CSV)", csv_data, f"{project_id}_BOQ.csv", "text/csv")

def create_interactive_boq_editor():
    st.subheader("Interactive BOQ Editor")
    product_df, _, _ = load_and_validate_data()
    if product_df is None:
        st.error("Cannot load product catalog for editing.")
        return
    
    currency = st.session_state.get('currency', 'USD')
    tabs = st.tabs(["Edit Current BOQ", "Add Products", "Product Search"])
    
    with tabs[0]: edit_current_boq(currency)
    with tabs[1]: add_products_interface(product_df, currency)
    with tabs[2]: product_search_interface(product_df, currency)

def edit_current_boq(currency):
    if not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ first or add products manually.")
        return
    
    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        with st.expander(f"{item.get('category', 'General')} - {item.get('name', 'Unknown')[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                item['name'] = st.text_input("Product Name", item.get('name', ''), key=f"name_{i}")
                item['brand'] = st.text_input("Brand", item.get('brand', ''), key=f"brand_{i}")
            with col2:
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_cat = item.get('category', 'General')
                item['category'] = st.selectbox("Category", category_list, index=category_list.index(current_cat) if current_cat in category_list else 6, key=f"category_{i}")
            with col3:
                item['quantity'] = st.number_input("Quantity", 1, value=int(item.get('quantity', 1)), key=f"qty_{i}")
                display_price = convert_currency(item.get('price', 0), currency) if currency == 'INR' else item.get('price', 0)
                new_price = st.number_input(f"Unit Price ({currency})", 0.0, value=float(display_price), key=f"price_{i}")
                item['price'] = new_price / get_usd_to_inr_rate() if currency == 'INR' else new_price
            with col4:
                total_price = item['price'] * item['quantity']
                display_total = convert_currency(total_price, currency)
                st.metric("Total", format_currency(display_total, currency))
                if st.button("Remove", key=f"remove_{i}", type="secondary"): items_to_remove.append(i)

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()

    if st.session_state.boq_items:
        st.markdown("---")
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        st.markdown(f"### **Total Project Cost: {format_currency(convert_currency(total_cost, currency), currency)}**")

def add_products_interface(product_df, currency):
    st.write("**Add Products to BOQ:**")
    col1, col2 = st.columns([2, 1])
    with col1:
        categories = ['All'] + sorted(list(product_df['category'].unique()))
        selected_category = st.selectbox("Filter by Category", categories)
        filtered_df = product_df[product_df['category'] == selected_category] if selected_category != 'All' else product_df
        product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
        if not product_options:
            st.warning("No products found.")
            return
        selected_product_str = st.selectbox("Select Product", product_options)
        selected_product = next((row for _, row in filtered_df.iterrows() if f"{row['brand']} - {row['name']}" == selected_product_str), None)
    
    with col2:
        if selected_product is not None:
            quantity = st.number_input("Quantity", 1, value=1, key="add_qty")
            base_price = float(selected_product.get('price', 0))
            display_price = convert_currency(base_price, currency)
            st.metric("Unit Price", format_currency(display_price, currency))
            if st.button("Add to BOQ", type="primary"):
                st.session_state.boq_items.append({
                    'category': selected_product.get('category', 'General'), 'name': selected_product.get('name', ''),
                    'brand': selected_product.get('brand', ''), 'quantity': quantity, 'price': base_price, 'matched': True
                })
                st.success(f"Added {quantity}x {selected_product['name']} to BOQ!")
                time.sleep(1)
                st.rerun()

def product_search_interface(product_df, currency):
    st.write("**Search Product Catalog:**")
    search_term = st.text_input("Search products...", placeholder="Enter name, brand, or features")
    if search_term:
        search_cols = ['name', 'brand', 'features']
        mask = product_df[search_cols].apply(lambda x: x.astype(str).str.contains(search_term, case=False, na=False)).any(axis=1)
        search_results = product_df[mask]
        st.write(f"Found {len(search_results)} products:")
        for i, product in search_results.head(10).iterrows():
            with st.expander(f"{product.get('brand', 'Unknown')} - {product.get('name', 'Unknown')[:60]}..."):
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    st.write(f"**Category:** {product.get('category', 'N/A')}")
                    st.write(f"**Features:** {str(product.get('features', ''))[:100]}...")
                with col_b:
                    price = float(product.get('price', 0))
                    display_price = convert_currency(price, currency)
                    st.metric("Price", format_currency(display_price, currency))
                with col_c:
                    add_qty = st.number_input("Qty", 1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        st.session_state.boq_items.append({
                            'category': product.get('category', 'General'), 'name': product.get('name', ''),
                            'brand': product.get('brand', ''), 'quantity': add_qty, 'price': price, 'matched': True
                        })
                        st.success(f"Added {add_qty}x {product['name']} to BOQ!")
                        time.sleep(1)
                        st.rerun()

def create_3d_visualization_placeholder():
    st.subheader("3D Room Visualization")
    st.info("🚧 3D visualization feature coming soon!")
    
    st.markdown("""
    **Planned Features:**
    - Interactive 3D room layout & equipment placement
    - Cable routing simulation and sight line analysis
    - Basic acoustic modeling preview
    """)
    if st.session_state.boq_items:
        st.markdown("**Equipment for Visualization:**")
        for item in st.session_state.boq_items:
            st.write(f"• {item.get('quantity')}x {item.get('name', 'Unknown')[:40]}...")

if __name__ == "__main__":
    main()
