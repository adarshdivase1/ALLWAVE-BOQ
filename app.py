import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
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
        return 83.0  # Approximate USD to INR rate
    except Exception:
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

        # Data quality checks (simplified for brevity, your original code is good)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        df['brand'] = df['brand'].fillna('Unknown')
        df['category'] = df['category'].fillna('General')
        df['features'] = df['features'].fillna('')
        df['name'] = df['name'].fillna('Unnamed Product')

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

# --- Room Specifications Database (shortened for brevity) ---
ROOM_SPECS = {
    "Huddle Room (2-4 People)": {"area_sqft": (50, 120), "recommended_display_size": (32, 55), "viewing_distance_ft": (4, 8), "audio_coverage": "Near-field", "power_requirements": "Standard 15A circuit", "typical_budget_range": (5000, 15000)},
    "Medium Conference Room (5-10 People)": {"area_sqft": (150, 300), "recommended_display_size": (55, 75), "viewing_distance_ft": (8, 14), "audio_coverage": "Room-wide", "power_requirements": "20A dedicated circuit", "typical_budget_range": (15000, 35000)},
    "Executive Boardroom": {"area_sqft": (300, 600), "recommended_display_size": (75, 98), "viewing_distance_ft": (12, 20), "audio_coverage": "Distributed mics", "power_requirements": "30A dedicated circuit", "typical_budget_range": (35000, 80000)},
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
        if not boq_items:
            return issues, warnings

        # Example check: Ensure essential components are present
        essential_categories = ['display', 'audio', 'control']
        found_categories = [item.get('category', '').lower() for item in boq_items]
        for essential in essential_categories:
            if not any(essential in cat for cat in found_categories):
                issues.append(f"Missing essential component category: **{essential.capitalize()}**")

        # Example check: Display size validation
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            room_spec = self.room_specs.get(room_type, {})
            min_size, max_size = room_spec.get('recommended_display_size', (32, 98))
            for display in displays:
                size_match = re.search(r'(\d+)"', display.get('name', ''))
                if size_match:
                    size = int(size_match.group(1))
                    if not (min_size <= size <= max_size):
                        warnings.append(f"Display '{display.get('name')}' ({size}\") is outside the recommended size ({min_size}\"-{max_size}\") for a {room_type}.")
        return issues, warnings

# --- ENHANCED: Prompt Creation ---
def create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    product_catalog_string = product_df.to_csv(index=False)
    room_spec = ROOM_SPECS[room_type]
    
    # ENHANCED: Inject the AVIXA guidelines directly into the prompt.
    prompt = f"""
You are a Professional AV Systems Engineer. Create a production-ready BOQ.

**PROJECT SPECIFICATIONS:**
- Room Type: {room_type} ({room_area:.0f} sq ft)
- Budget Tier: {budget_tier}
- Special Requirements: {features or 'None'}
- Infrastructure: {technical_reqs}

**MANDATORY REQUIREMENTS:**
1.  **ONLY use products from the provided catalog.**
2.  The output **MUST be a markdown table** with columns: `Category`, `Brand`, `Product Name`, `Quantity`, `Unit Price`.
3.  Include all necessary components for a complete system (mounts, cables, control, etc.).
4.  Do not include labor, warranty, or contingency in the table. Just list the hardware.
5.  Adhere strictly to the AVIXA standards provided below.

---
**AVIXA STANDARDS TO FOLLOW:**
{guidelines}
---

**PRODUCT CATALOG:**
{product_catalog_string}

Generate the BOQ markdown table now:
"""
    return prompt

# --- ENHANCED: BOQ Item Extraction ---
def extract_boq_items_from_response(boq_content, product_df):
    items = []
    lines = boq_content.split('\n')
    in_table = False
    header = []

    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            in_table = False
            continue

        parts = [p.strip() for p in line.split('|')[1:-1]]
        if '---' in parts[0]: continue

        if not header:
            header = [h.lower().replace(' ', '_') for h in parts]
            in_table = True
        elif len(parts) == len(header):
            item_dict = dict(zip(header, parts))
            
            # Data Cleaning and Type Conversion
            quantity = item_dict.get('quantity', '1')
            price = item_dict.get('unit_price', '0')
            
            try:
                item_dict['quantity'] = int(re.sub(r'[^\d]', '', quantity))
            except (ValueError, TypeError):
                item_dict['quantity'] = 1

            try:
                # Remove currency symbols and commas for reliable conversion
                price_cleaned = re.sub(r'[^\d.]', '', price)
                item_dict['price'] = float(price_cleaned) if price_cleaned else 0.0
            except (ValueError, TypeError):
                item_dict['price'] = 0.0

            # Rename columns to a standard format if they vary
            if 'product_name' in item_dict:
                item_dict['name'] = item_dict.pop('product_name')
            
            # Ensure essential keys exist
            for key in ['category', 'brand', 'name', 'quantity', 'price']:
                if key not in item_dict:
                    item_dict[key] = '' if key != 'quantity' and key != 'price' else (1 if key == 'quantity' else 0.0)

            items.append(item_dict)

    return items

# --- Main Application ---
def main():
    # FIXED: Initialize all state variables at the start.
    if 'boq_content' not in st.session_state:
        st.session_state.boq_content = None
    if 'boq_items' not in st.session_state:
        st.session_state.boq_items = []
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = {"issues": [], "warnings": []}

    # Load Data
    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("Data Quality Issues"):
            for issue in data_issues:
                st.warning(issue)
    if product_df is None:
        st.error("Cannot load product catalog. Application cannot start.")
        return

    # Setup Gemini
    model = setup_gemini()
    if not model:
        return

    # --- UI Layout ---
    st.title("Professional AV BOQ Generator")
    st.caption("AI-powered Bill of Quantities with technical validation")

    with st.sidebar:
        st.header("Project Configuration")
        project_id = st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}")
        quote_valid_days = st.number_input("Quote Valid (Days)", 15, 90, 30)
        currency = st.selectbox("Display Currency", ["USD", "INR"], index=1)
        st.markdown("---")
        room_type = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()))
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium"], value="Standard")
        
        # Display room guidelines
        room_spec = ROOM_SPECS[room_type]
        st.markdown("##### Room Guidelines")
        st.caption(f"Area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft | Display: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")

    # --- Input Tabs ---
    tab1, tab2 = st.tabs(["📊 Room & Requirements", "📋 Product Catalog"])

    with tab1:
        st.subheader("Room Dimensions")
        c1, c2, c3 = st.columns(3)
        room_length = c1.number_input("Room Length (ft)", 8.0, 50.0, 16.0)
        room_width = c2.number_input("Room Width (ft)", 6.0, 30.0, 12.0)
        room_area = room_length * room_width
        c3.metric("Room Area", f"{room_area:.0f} sq ft")

        st.subheader("System Requirements")
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual 85\" displays, wireless presentation, Zoom certified, ceiling microphones'")
        technical_reqs = st.multiselect("Advanced Technical Needs:", ["ADA Compliance", "Fire Code Compliance", "Dedicated 20A Circuit", "10Gb Network"])

    with tab2:
        st.subheader("Product Catalog Viewer")
        st.dataframe(product_df, use_container_width=True, height=400)

    st.markdown("---")

    # --- Action Buttons ---
    b1, b2 = st.columns(2)
    if b1.button("🚀 Generate Professional BOQ", type="primary", use_container_width=True):
        with st.spinner("Engineering professional BOQ with technical validation..."):
            prompt = create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)
            try:
                response = generate_with_retry(model, prompt)
                if response:
                    # FIXED: Store all generated content in session state
                    st.session_state.boq_content = response.text
                    boq_items = extract_boq_items_from_response(response.text, product_df)
                    st.session_state.boq_items = boq_items

                    validator = BOQValidator(ROOM_SPECS)
                    issues, warnings = validator.validate_technical_requirements(boq_items, room_type)
                    st.session_state.validation_results = {"issues": issues, "warnings": warnings}
                    st.success(f"Generated BOQ with {len(boq_items)} items!")
                else:
                    st.error("Failed to get a response from the AI model.")
            except Exception as e:
                st.error(f"An error occurred during BOQ generation: {e}")

    if b2.button("🧹 Clear & Reset", use_container_width=True):
        # FIXED: Explicitly clear state variables and rerun
        st.session_state.boq_content = None
        st.session_state.boq_items = []
        st.session_state.validation_results = {"issues": [], "warnings": []}
        st.rerun()

    # --- FIXED: Display results and editor only if they exist in the session state ---
    if st.session_state.boq_content:
        st.markdown("---")
        st.subheader("Generated Bill of Quantities")

        # Display Validation Results
        validation = st.session_state.validation_results
        if validation["issues"]:
            for issue in validation["issues"]:
                st.error(f"**Critical Issue:** {issue}")
        if validation["warnings"]:
            for warning in validation["warnings"]:
                st.warning(f"**Recommendation:** {warning}")
        
        # ENHANCED: Use st.data_editor for a superior editing experience
        st.subheader("Interactive BOQ Editor")
        st.caption("You can directly edit quantities, prices, or remove items here.")
        
        edited_df = pd.DataFrame(st.session_state.boq_items)
        
        # Reorder columns for better user experience in the editor
        cols_order = ['category', 'brand', 'name', 'quantity', 'price']
        edited_df = edited_df[[col for col in cols_order if col in edited_df.columns]]

        # The data editor widget
        edited_boq = st.data_editor(
            edited_df,
            num_rows="dynamic", # Allows adding/deleting rows
            use_container_width=True,
            column_config={
                "price": st.column_config.NumberColumn(
                    "Unit Price (USD)",
                    help="The price per single unit in USD.",
                    format="$%.2f",
                )
            }
        )
        # FIXED: Persist changes from the data editor back to session state
        st.session_state.boq_items = edited_boq.to_dict('records')

        # --- Summary and Download ---
        st.markdown("---")
        col_summary, col_download = st.columns([1, 2])

        with col_summary:
            st.subheader("Cost Summary")
            total_cost_usd = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            
            if currency == "INR":
                total_cost_display = convert_currency(total_cost_usd, "INR")
                st.metric("Total Project Cost", format_currency(total_cost_display, "INR"))
            else:
                st.metric("Total Project Cost", format_currency(total_cost_usd, "USD"))

        with col_download:
            st.subheader("Download BOQ")
            if not st.session_state.boq_items:
                st.info("BOQ is empty.")
            else:
                csv_data = pd.DataFrame(st.session_state.boq_items).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download BOQ as CSV",
                    data=csv_data,
                    file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

# Run the application
if __name__ == "__main__":
    main()
