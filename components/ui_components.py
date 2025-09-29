import streamlit as st
import pandas as pd
from datetime import datetime

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

# --- Main UI Section Builders ---

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
        "dedicated_circuit": has_dedicated_circuit, "network_capability": network_capability,
        "cable_management": cable_management, "ada_compliance": ada_compliance,
        "fire_code_compliance": fire_code_compliance, "security_clearance": security_clearance
    }

def create_multi_room_interface():
    """Interface for managing multiple rooms in a project."""
    st.subheader("Multi-Room Project Management")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        room_name = st.text_input("New Room Name", value=f"Room {len(st.session_state.project_rooms) + 1}")
    with col2:
        st.write(""); st.write("")
        if st.button("➕ Add New Room to Project", type="primary", use_container_width=True):
            new_room = {
                'name': room_name,
                'type': st.session_state.get('room_type_select', list(ROOM_SPECS.keys())[0]),
                'area': st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16),
                'boq_items': [], 'features': st.session_state.get('features_text_area', ''), 'technical_reqs': {}
            }
            st.session_state.project_rooms.append(new_room)
            st.success(f"Added '{room_name}' to the project.")
            st.rerun()
    with col3:
        st.write(""); st.write("")
        if st.session_state.project_rooms:
            project_details = {
                'project_name': st.session_state.get('project_name_input', 'Multi_Room_Project'),
                'client_name': st.session_state.get('client_name_input', 'Valued Client'),
                'gst_rates': st.session_state.get('gst_rates', {})
            }
            excel_data = generate_company_excel(
                project_details=project_details, rooms_data=st.session_state.project_rooms,
                usd_to_inr_rate=get_usd_to_inr_rate()
            )
            if excel_data:
                filename = f"{project_details['project_name']}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                st.download_button(
                    label="📊 Download Full Project BOQ", data=excel_data, file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, type="secondary"
                )

    if st.session_state.project_rooms:
        st.markdown("---")
        st.write("**Current Project Rooms:**")

        previous_room_index = st.session_state.current_room_index
        if previous_room_index < len(st.session_state.project_rooms):
            st.session_state.project_rooms[previous_room_index]['boq_items'] = st.session_state.boq_items

        room_options = [room['name'] for room in st.session_state.project_rooms]
        current_index = st.session_state.current_room_index if st.session_state.current_room_index < len(room_options) else 0

        selected_room_name = st.selectbox(
            "Select a room to view or edit:", options=room_options, index=current_index, key="room_selector"
        )

        new_index = room_options.index(selected_room_name)
        if new_index != st.session_state.current_room_index:
            st.session_state.current_room_index = new_index
            st.session_state.boq_items = st.session_state.project_rooms[new_index].get('boq_items', [])
            update_boq_content_with_current_items()
            st.rerun()

        selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
        st.info(f"You are currently editing **{selected_room['name']}**.")

        if st.button(f"🗑️ Remove '{selected_room['name']}'", type="secondary"):
            st.session_state.project_rooms.pop(st.session_state.current_room_index)
            st.session_state.current_room_index = 0
            st.session_state.boq_items = st.session_state.project_rooms[0].get('boq_items', []) if st.session_state.project_rooms else []
            st.rerun()

# --- BOQ Display and Editing ---
def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if not st.session_state.get('boq_items'):
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items generated yet."
        return

    boq_content = "## Bill of Quantities\n\n"
    boq_content += "| Category | Make | Model No. | Specifications | Qty | Unit Price (USD) | Remarks |\n"
    boq_content += "|---|---|---|---|---|---|---|\n"

    for item in st.session_state.boq_items:
        remarks = item.get('justification', '')
        if item.get('warning'):
            remarks = f"⚠️ **{item['warning']}**<br>{remarks}"

        boq_content += (
            f"| {item.get('category', 'N/A')} | {item.get('brand', 'N/A')} "
            f"| {item.get('name', 'N/A')} | {item.get('specifications', '')} "
            f"| {item.get('quantity', 1)} | ${item.get('price', 0):,.2f} "
            f"| {remarks} |\n"
        )
    st.session_state.boq_content = boq_content

def display_boq_results(product_df):
    """Display BOQ results with interactive editing capabilities."""
    boq_content = st.session_state.get('boq_content')
    validation_results = st.session_state.get('validation_results', {})
    item_count = len(st.session_state.get('boq_items', []))
    st.subheader(f"Generated Bill of Quantities ({item_count} items)")

    if validation_results.get('issues') or validation_results.get('warnings'):
        with st.container(border=True):
            if validation_results.get('issues'):
                st.error("🚨 **Critical System Gaps Identified**")
                for issue in validation_results['issues']: st.write(f"- {issue}")
            if validation_results.get('warnings'):
                st.warning("👀 **Design Recommendations & Compliance Notes**")
                for warning in validation_results['warnings']: st.write(f"- {warning}")

    if boq_content:
        st.markdown(boq_content, unsafe_allow_html=True)
    else:
        st.info("No BOQ content generated yet. Use the interactive editor below.")

    if st.session_state.get('boq_items'):
        currency = st.session_state.get('currency', 'USD')
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        display_total = convert_currency(total_cost * 1.30, currency)
        st.metric("Estimated Project Total", format_currency(display_total, currency), help="Includes installation, warranty, and contingency")
    
    st.markdown("---")
    create_interactive_boq_editor(product_df)

def create_interactive_boq_editor(product_df):
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    item_count = len(st.session_state.get('boq_items', []))
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Items in BOQ", item_count)
    with col2:
        if st.session_state.get('boq_items'):
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            currency = st.session_state.get('currency', 'USD')
            display_total = convert_currency(total_cost, currency)
            st.metric("Hardware Subtotal", format_currency(display_total, currency))
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
    if not st.session_state.get('boq_items'):
        st.info("No BOQ items loaded. Generate a BOQ or add products manually.")
        return

    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        with st.expander(f"{item.get('category', 'General')} - {str(item.get('name', ''))[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                item['name'] = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                item['brand'] = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")
            with col2:
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_category = item.get('category', 'General')
                cat_index = category_list.index(current_category) if current_category in category_list else 6
                item['category'] = st.selectbox("Category", category_list, index=cat_index, key=f"category_{i}")
            with col3:
                item['quantity'] = st.number_input("Quantity", min_value=1, value=int(item.get('quantity', 1)), key=f"qty_{i}")
                current_price = float(item.get('price', 0))
                display_price = convert_currency(current_price, currency)
                new_price = st.number_input(f"Unit Price ({currency})", min_value=0.0, value=display_price, key=f"price_{i}")
                item['price'] = new_price / get_usd_to_inr_rate() if currency == 'INR' else new_price
            with col4:
                total = item['price'] * item['quantity']
                st.metric("Total", format_currency(convert_currency(total, currency), currency))
                if st.button("Remove", key=f"remove_{i}", type="secondary"):
                    items_to_remove.append(i)

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
            st.warning("No products found for this category.")
            return
        selected_product_str = st.selectbox("Select Product", product_options, key="add_product_select")
        selected_product_series = filtered_df[filtered_df.apply(lambda row: f"{row['brand']} - {row['name']}" == selected_product_str, axis=1)]
        if selected_product_series.empty:
            st.error("Selected product not found.")
            return
        selected_product = selected_product_series.iloc[0]

    with col2:
        quantity = st.number_input("Quantity", min_value=1, value=1, key="add_product_qty")
        base_price = float(selected_product.get('price', 0))
        display_price = convert_currency(base_price, currency)
        st.metric("Unit Price", format_currency(display_price, currency))
        st.metric("Total", format_currency(display_price * quantity, currency))
        if st.button("Add to BOQ", type="primary"):
            new_item = {
                'category': selected_product.get('category', 'General'), 'name': selected_product.get('name', ''),
                'brand': selected_product.get('brand', ''), 'quantity': quantity, 'price': base_price,
                'justification': 'Manually added component.', 'specifications': selected_product.get('features', ''),
                'image_url': selected_product.get('image_url', ''), 'gst_rate': selected_product.get('gst_rate', 18), 'matched': True
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
        mask = product_df.apply(lambda row: search_term.lower() in str(row['name']).lower() or
                                             search_term.lower() in str(row['brand']).lower() or
                                             search_term.lower() in str(row['features']).lower(), axis=1)
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
                    display_price = convert_currency(price, currency)
                    st.metric("Price", format_currency(display_price, currency))
                with col_c:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        new_item = {
                            'category': product.get('category', 'General'), 'name': product.get('name', ''),
                            'brand': product.get('brand', ''), 'quantity': add_qty, 'price': price,
                            'justification': 'Added via search.', 'specifications': product.get('features', ''),
                            'image_url': product.get('image_url', ''), 'gst_rate': product.get('gst_rate', 18), 'matched': True
                        }
                        st.session_state.boq_items.append(new_item)
                        update_boq_content_with_current_items()
                        st.success(f"Added {add_qty}x {product['name']}!")
                        st.rerun()
