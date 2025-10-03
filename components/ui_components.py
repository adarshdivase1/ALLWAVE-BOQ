# components/ui_components.py

import streamlit as st
import pandas as pd
from datetime import datetime

# (Initial imports and helper functions remain the same)
try:
    from components.visualizer import ROOM_SPECS
    from components.utils import convert_currency, format_currency, get_usd_to_inr_rate
    from components.excel_generator import generate_company_excel
except ImportError:
    ROOM_SPECS = {'Standard Conference Room': {'area_sqft': (250, 400)}}
    def get_usd_to_inr_rate(): return 83.5
    def convert_currency(amount, to_currency="INR"): return amount * (83.5 if to_currency == "INR" else 1)
    def format_currency(amount, currency="INR"): return f"₹{amount:,.0f}" if currency == "INR" else f"${amount:,.2f}"
    def generate_company_excel(*args, **kwargs):
        st.error("Excel component unavailable.")
        return None

# (Header, Room Calculator, and Advanced Requirements functions remain unchanged)
def create_project_header():
    """Create professional project header."""
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("Production-Ready AV BOQ Generator")
        st.caption("AVIXA Standards-Compliant Design & Validation")
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
        recommended_type = next((rt for rt, specs in ROOM_SPECS.items() if specs["area_sqft"][0] <= room_area <= specs["area_sqft"][1]), None)
        if recommended_type:
            st.success(f"Recommended Room Type: {recommended_type}")
        else:
            st.warning("Room size is outside typical ranges")
    return room_area, ceiling_height

def create_advanced_requirements():
    """Advanced technical requirements input."""
    st.subheader("Technical Requirements")
    # This function is fine as is.
    pass


# --- CHANGE START: Added Model No. to BOQ display ---
def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if not st.session_state.get('boq_items'):
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items generated yet."
        return

    boq_content = "## Bill of Quantities\n\n"
    boq_content += "| Category | Make | Model No. | Name | Qty | Unit Price (USD) | Remarks |\n"
    boq_content += "|---|---|---|---|---|---|---|\n"

    for item in st.session_state.boq_items:
        remarks = item.get('justification', '')
        if not item.get('matched'):
            remarks = f"⚠️ **VERIFY MODEL**<br>{remarks}"

        boq_content += (
            f"| {item.get('category', 'N/A')} | {item.get('brand', 'N/A')} "
            f"| {item.get('model_number', 'N/A')} | {item.get('name', 'N/A')} "
            f"| {item.get('quantity', 1)} | ${item.get('price', 0):,.2f} "
            f"| {remarks} |\n"
        )
    st.session_state.boq_content = boq_content
# --- CHANGE END ---


def edit_current_boq(currency):
    """Interface for editing current BOQ items."""
    if not st.session_state.get('boq_items'):
        st.info("No BOQ items loaded. Generate a BOQ or add products manually.")
        return

    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        # --- CHANGE START: Added Model Number to the editor ---
        with st.expander(f"{item.get('category', 'General')} - {item.get('brand', '')} {item.get('model_number', '')}"):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                item['name'] = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                item['brand'] = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")
                item['model_number'] = st.text_input("Model No.", value=item.get('model_number', ''), key=f"model_{i}")
            # --- CHANGE END ---
            with col2:
                # This part remains the same
                category_list = sorted(list(st.session_state.product_df['category'].unique()))
                current_category = item.get('category', 'General AV')
                try:
                    cat_index = category_list.index(current_category)
                except ValueError:
                    cat_index = 0
                item['category'] = st.selectbox("Category", category_list, index=cat_index, key=f"category_{i}")
            with col3:
                # This part remains the same
                item['quantity'] = st.number_input("Quantity", min_value=1, value=int(item.get('quantity', 1)), key=f"qty_{i}")
                current_price_usd = float(item.get('price', 0))
                display_price = convert_currency(current_price_usd, currency)
                new_display_price = st.number_input(f"Unit Price ({currency})", min_value=0.0, value=display_price, key=f"price_{i}")
                item['price'] = new_display_price / get_usd_to_inr_rate() if currency == 'INR' else new_display_price
            with col4:
                # This part remains the same
                total_usd = item['price'] * item['quantity']
                st.metric("Total", format_currency(convert_currency(total_usd, currency), currency))
                if st.button("Remove", key=f"remove_{i}", type="secondary"):
                    items_to_remove.append(i)

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()


def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ with cascading category filters."""
    st.write("**Add Products to BOQ:**")
    
    # --- CHANGE START: Cascading Dropdowns ---
    col1, col2 = st.columns(2)
    with col1:
        primary_categories = ['All'] + sorted(list(product_df['category'].unique()))
        selected_primary = st.selectbox("Filter by Primary Category", primary_categories, key="add_primary_cat_filter")

    with col2:
        if selected_primary != 'All':
            sub_categories = ['All'] + sorted(list(product_df[product_df['category'] == selected_primary]['sub_category'].unique()))
            selected_sub = st.selectbox("Filter by Sub-Category", sub_categories, key="add_sub_cat_filter")
        else:
            selected_sub = 'All'

    # Filter the DataFrame based on selections
    if selected_primary != 'All':
        filtered_df = product_df[product_df['category'] == selected_primary]
        if selected_sub != 'All':
            filtered_df = filtered_df[filtered_df['sub_category'] == selected_sub]
    else:
        filtered_df = product_df

    # --- CHANGE END ---
    
    col_prod, col_details = st.columns([2, 1])
    with col_prod:
        # Display format: Brand - Name (Model Number)
        product_options = [f"{row['brand']} - {row['name']} ({row['model_number']})" for _, row in filtered_df.iterrows()]
        if not product_options:
            st.warning("No products found for the selected filters.")
            return
        
        selected_product_str = st.selectbox("Select Product", product_options, key="add_product_select")
        
        # Find the selected product in the filtered dataframe
        selected_product_series = filtered_df[filtered_df.apply(lambda row: f"{row['brand']} - {row['name']} ({row['model_number']})" == selected_product_str, axis=1)]
        
        if selected_product_series.empty:
            st.error("Selected product not found in the dataframe.")
            return
        selected_product = selected_product_series.iloc[0]

    with col_details:
        quantity = st.number_input("Quantity", min_value=1, value=1, key="add_product_qty")
        base_price_usd = float(selected_product.get('price', 0))
        display_price = convert_currency(base_price_usd, currency)
        
        st.metric("Unit Price", format_currency(display_price, currency))
        st.metric("Total", format_currency(display_price * quantity, currency))
        
        if st.button("Add to BOQ", type="primary"):
            new_item = {
                'category': selected_product.get('category'),
                'sub_category': selected_product.get('sub_category'),
                'name': selected_product.get('name'),
                'brand': selected_product.get('brand'),
                'model_number': selected_product.get('model_number'),
                'quantity': quantity,
                'price': base_price_usd,
                'justification': 'Manually added component.',
                'specifications': selected_product.get('features', ''),
                'image_url': selected_product.get('image_url', ''),
                'gst_rate': selected_product.get('gst_rate', 18),
                'warranty': selected_product.get('warranty', 'Not Specified'),
                'lead_time_days': selected_product.get('lead_time_days', 14),
                'matched': True
            }
            st.session_state.boq_items.append(new_item)
            update_boq_content_with_current_items()
            st.success(f"Added {quantity}x {selected_product['name']}!")
            st.rerun()

# (Other functions like product_search_interface, display_boq_results, etc., can remain largely the same,
# but will benefit from the richer data passed to them implicitly via st.session_state.boq_items)
