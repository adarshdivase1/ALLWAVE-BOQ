# components/ui_components.py
# COMPLETE ENHANCED VERSION - Aligned with boq_generator.py v2.0

import streamlit as st
import pandas as pd
from datetime import datetime

try:
    from components.room_profiles import ROOM_SPECS
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

# ==================== MAIN UI SECTION BUILDERS ====================

def create_project_header():
    """Create professional project header with branding."""
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("🎯 AllWave AV BOQ Generator")
        st.caption("AVIXA Standards-Compliant Design & Validation Engine")
    with col2:
        project_id = st.text_input(
            "Project ID", 
            value=f"AVP-{datetime.now().strftime('%Y%m%d')}", 
            key="project_id_input"
        )
    with col3:
        quote_valid_days = st.number_input(
            "Quote Valid (Days)", 
            min_value=15, 
            max_value=90, 
            value=30, 
            key="quote_days_input"
        )
    return project_id, quote_valid_days


def create_room_calculator():
    """Room size calculator with AVIXA recommendations."""
    st.subheader("📐 Room Analysis & Specifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        room_length = st.number_input(
            "Room Length (ft)", 
            min_value=10.0, 
            max_value=80.0, 
            value=28.0, 
            key="room_length_input"
        )
        room_width = st.number_input(
            "Room Width (ft)", 
            min_value=8.0, 
            max_value=50.0, 
            value=20.0, 
            key="room_width_input"
        )
        ceiling_height = st.number_input(
            "Ceiling Height (ft)", 
            min_value=8.0, 
            max_value=20.0, 
            value=10.0, 
            key="ceiling_height_input"
        )
    
    with col2:
        room_area = room_length * room_width
        st.metric("Room Area", f"{room_area:.0f} sq ft")
        
        # Find recommended room type
        recommended_type = None
        for rt, specs in ROOM_SPECS.items():
            area_range = specs.get("area_sqft", (0, 0))
            if area_range[0] <= room_area <= area_range[1]:
                recommended_type = rt
                break
        
        if recommended_type:
            st.success(f"✅ Recommended: {recommended_type}")
        else:
            st.warning("⚠️ Room size outside typical ranges")
        
        # Calculate viewer distance recommendation
        farthest_viewer = room_length * 0.9
        recommended_display = farthest_viewer / 4 * 12 * 2.22  # AVIXA formula
        st.info(f"💡 Suggested Display: {recommended_display:.0f}\" (based on viewing distance)")
    
    return room_area, ceiling_height


def create_advanced_requirements():
    """Advanced technical requirements input."""
    st.subheader("⚙️ Technical Requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**🔌 Infrastructure**")
        has_dedicated_circuit = st.checkbox(
            "Dedicated 20A Circuit Available", 
            key="dedicated_circuit_checkbox"
        )
        network_capability = st.selectbox(
            "Network Infrastructure", 
            ["Standard 1Gb", "10Gb Capable", "Fiber Available"], 
            key="network_capability_select"
        )
        cable_management = st.selectbox(
            "Cable Management", 
            ["Exposed", "Conduit", "Raised Floor", "Drop Ceiling"], 
            key="cable_management_select"
        )
    
    with col2:
        st.write("**📋 Compliance & Standards**")
        ada_compliance = st.checkbox(
            "ADA Compliance Required", 
            key="ada_compliance_checkbox"
        )
        fire_code_compliance = st.checkbox(
            "Fire Code Compliance Required", 
            key="fire_code_compliance_checkbox"
        )
        security_clearance = st.selectbox(
            "Security Level", 
            ["Standard", "Restricted", "Classified"], 
            key="security_clearance_select"
        )
    
    return {
        "dedicated_circuit": has_dedicated_circuit,
        "network_capability": network_capability,
        "cable_management": cable_management,
        "ada_compliance": ada_compliance,
        "fire_code_compliance": fire_code_compliance,
        "security_clearance": security_clearance
    }


def create_multi_room_interface():
    """Interface for managing multiple rooms in a project."""
    st.markdown("---")
    st.subheader("🏢 Multi-Room Project Management")
    
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        room_name = st.text_input(
            "New Room Name", 
            value=f"Room {len(st.session_state.project_rooms) + 1}",
            key="new_room_name_input"
        )
    
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Add Room to Project", type="primary", use_container_width=True):
            new_room = {
                'name': room_name,
                'type': st.session_state.get('room_type_select', list(ROOM_SPECS.keys())[0]),
                'area': st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16),
                'boq_items': [],
                'features': st.session_state.get('features_text_area', ''),
                'technical_reqs': {}
            }
            st.session_state.project_rooms.append(new_room)
            st.success(f"✅ Added '{room_name}' to project")
            st.rerun()
    
    with col3:
        st.write("")
        st.write("")
        if st.session_state.project_rooms:
            project_details = {
                'Project Name': st.session_state.get('project_name_input', 'Multi_Room_Project'),
                'Client Name': st.session_state.get('client_name_input', 'Valued Client'),
                'Location': st.session_state.get('location_input', ''),
                'Design Engineer': st.session_state.get('design_engineer_input', ''),
                'Account Manager': st.session_state.get('account_manager_input', ''),
                'Key Client Personnel': st.session_state.get('client_personnel_input', ''),
                'Key Comments': st.session_state.get('comments_input', ''),
                'gst_rates': st.session_state.get('gst_rates', {})
            }
            
            excel_data = generate_company_excel(
                project_details=project_details,
                rooms_data=st.session_state.project_rooms,
                usd_to_inr_rate=get_usd_to_inr_rate()
            )
            
            if excel_data:
                filename = f"{project_details['Project Name']}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                st.download_button(
                    label="📊 Download Full Project BOQ",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary"
                )

    # Room selection and management
    if st.session_state.project_rooms:
        st.markdown("---")
        st.write("**Current Project Rooms:**")

        # Save current room's BOQ items before switching
        previous_room_index = st.session_state.current_room_index
        if previous_room_index < len(st.session_state.project_rooms):
            st.session_state.project_rooms[previous_room_index]['boq_items'] = st.session_state.boq_items

        room_options = [room['name'] for room in st.session_state.project_rooms]
        current_index = st.session_state.current_room_index if st.session_state.current_room_index < len(room_options) else 0

        selected_room_name = st.selectbox(
            "Select room to view/edit:",
            options=room_options,
            index=current_index,
            key="room_selector"
        )

        new_index = room_options.index(selected_room_name)
        if new_index != st.session_state.current_room_index:
            st.session_state.current_room_index = new_index
            st.session_state.boq_items = st.session_state.project_rooms[new_index].get('boq_items', [])
            update_boq_content_with_current_items()
            st.rerun()

        selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
        st.info(f"📍 Currently editing: **{selected_room['name']}**")

        if st.button(f"🗑️ Remove '{selected_room['name']}'", type="secondary"):
            st.session_state.project_rooms.pop(st.session_state.current_room_index)
            st.session_state.current_room_index = 0
            st.session_state.boq_items = st.session_state.project_rooms[0].get('boq_items', []) if st.session_state.project_rooms else []
            st.rerun()


# ==================== BOQ DISPLAY AND EDITING ====================

def update_boq_content_with_current_items():
    """Update BOQ content in session state to reflect current items."""
    if not st.session_state.get('boq_items'):
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items generated yet."
        return

    boq_content = "## Bill of Quantities\n\n"
    boq_content += "| Category | Sub-Category | Brand | Model | Name | Qty | Unit Price (USD) | Remarks |\n"
    boq_content += "|---|---|---|---|---|---|---|---|\n"

    for item in st.session_state.boq_items:
        remarks = item.get('justification', '')
        if not item.get('matched'):
            remarks = f"⚠️ **VERIFY**<br>{remarks}"

        boq_content += (
            f"| {item.get('category', 'N/A')} "
            f"| {item.get('sub_category', 'N/A')} "
            f"| {item.get('brand', 'N/A')} "
            f"| {item.get('model_number', 'N/A')} "
            f"| {item.get('name', 'N/A')} "
            f"| {item.get('quantity', 1)} "
            f"| ${item.get('price', 0):,.2f} "
            f"| {remarks} |\n"
        )
    
    st.session_state.boq_content = boq_content


def display_boq_results(product_df, project_details):
    """Display BOQ results with interactive editing and validation feedback."""
    boq_content = st.session_state.get('boq_content')
    validation_results = st.session_state.get('validation_results', {})
    item_count = len(st.session_state.get('boq_items', []))
    
    st.subheader(f"📋 Generated Bill of Quantities ({item_count} items)")

    # Display validation results prominently
    if validation_results.get('issues') or validation_results.get('warnings'):
        with st.container(border=True):
            if validation_results.get('issues'):
                st.error("🚨 **Critical System Gaps Identified**")
                for issue in validation_results['issues']:
                    st.write(f"- {issue}")
            
            if validation_results.get('warnings'):
                st.warning("💡 **Design Recommendations**")
                for warning in validation_results['warnings']:
                    st.write(f"- {warning}")

    # Display BOQ content
    if boq_content:
        st.markdown(boq_content, unsafe_allow_html=True)
    else:
        st.info("No BOQ content generated yet. Use the editor below to build your BOQ.")

    # Summary metrics and download
    if st.session_state.get('boq_items'):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            currency = st.session_state.get('currency', 'USD')
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            
            # Add 30% for services (installation, warranty, PM)
            display_total = convert_currency(total_cost * 1.30, currency)
            st.metric(
                "Estimated Project Total",
                format_currency(display_total, currency),
                help="Includes installation, warranty, and project management"
            )
        
        with col2:
            # Generate Excel for current room
            if st.session_state.project_rooms and st.session_state.current_room_index < len(st.session_state.project_rooms):
                current_room_name = st.session_state.project_rooms[st.session_state.current_room_index]['name']
            else:
                current_room_name = "Current_Room"
            
            single_room_data = [{'name': current_room_name, 'boq_items': st.session_state.boq_items}]

            excel_data_current = generate_company_excel(
                project_details=project_details,
                rooms_data=single_room_data,
                usd_to_inr_rate=get_usd_to_inr_rate()
            )
            
            if excel_data_current:
                filename = f"{project_details.get('Project Name', 'Project')}_{current_room_name}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                st.write("")
                st.write("")
                st.download_button(
                    label="📄 Download Current Room BOQ",
                    data=excel_data_current,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
    
    st.markdown("---")
    create_interactive_boq_editor(product_df)


def create_interactive_boq_editor(product_df):
    """Create interactive BOQ editing interface with add/edit/search capabilities."""
    st.subheader("🛠️ Interactive BOQ Editor")
    
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
        if st.button("🔄 Refresh BOQ Display", help="Update main BOQ display with current items"):
            update_boq_content_with_current_items()
            st.rerun()

    if product_df is None:
        st.error("Cannot load product catalog for editing.")
        return

    currency = st.session_state.get('currency', 'USD')
    tabs = st.tabs(["✏️ Edit Current BOQ", "➕ Add Products", "🔍 Product Search"])

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
        with st.expander(f"{item.get('category', 'General')} - {item.get('brand', '')} {item.get('model_number', '')}"):
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                item['name'] = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                item['brand'] = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")
                item['model_number'] = st.text_input("Model No.", value=item.get('model_number', ''), key=f"model_{i}")
            
            with col2:
                category_list = sorted(list(st.session_state.product_df['category'].unique()))
                current_category = item.get('category', 'General AV')
                try:
                    cat_index = category_list.index(current_category)
                except ValueError:
                    cat_index = 0
                item['category'] = st.selectbox("Category", category_list, index=cat_index, key=f"category_{i}")
                
                # Sub-category selection
                sub_cats = sorted(list(st.session_state.product_df[
                    st.session_state.product_df['category'] == item['category']
                ]['sub_category'].unique()))
                current_sub = item.get('sub_category', '')
                try:
                    sub_index = sub_cats.index(current_sub) if current_sub in sub_cats else 0
                except:
                    sub_index = 0
                item['sub_category'] = st.selectbox("Sub-Category", sub_cats, index=sub_index, key=f"subcat_{i}")
            
            with col3:
                item['quantity'] = st.number_input("Quantity", min_value=1, value=int(item.get('quantity', 1)), key=f"qty_{i}")
                
                current_price_usd = float(item.get('price', 0))
                display_price = convert_currency(current_price_usd, currency)
                new_display_price = st.number_input(
                    f"Unit Price ({currency})",
                    min_value=0.0,
                    value=display_price,
                    key=f"price_{i}"
                )
                item['price'] = new_display_price / get_usd_to_inr_rate() if currency == 'INR' else new_display_price
            
            with col4:
                total_usd = item['price'] * item['quantity']
                st.metric("Total", format_currency(convert_currency(total_usd, currency), currency))
                
                if st.button("Remove", key=f"remove_{i}", type="secondary"):
                    items_to_remove.append(i)
            
            # Justification
            item['justification'] = st.text_area(
                "Justification",
                value=item.get('justification', ''),
                height=60,
                key=f"just_{i}"
            )

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()


def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ with cascading filters."""
    st.write("**Add Products to BOQ:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        primary_categories = ['All'] + sorted(list(product_df['category'].unique()))
        selected_primary = st.selectbox(
            "Filter by Primary Category",
            primary_categories,
            key="add_primary_cat_filter"
        )

    with col2:
        if selected_primary != 'All':
            sub_categories = ['All'] + sorted(list(
                product_df[product_df['category'] == selected_primary]['sub_category'].unique()
            ))
            selected_sub = st.selectbox(
                "Filter by Sub-Category",
                sub_categories,
                key="add_sub_cat_filter"
            )
        else:
            selected_sub = 'All'

    # Apply filters
    if selected_primary != 'All':
        filtered_df = product_df[product_df['category'] == selected_primary]
        if selected_sub != 'All':
            filtered_df = filtered_df[filtered_df['sub_category'] == selected_sub]
    else:
        filtered_df = product_df

    col_prod, col_details = st.columns([2, 1])
    
    with col_prod:
        product_options = [
            f"{row['brand']} - {row['name']} ({row['model_number']})"
            for _, row in filtered_df.iterrows()
        ]
        
        if not product_options:
            st.warning("No products found for the selected filters.")
            return
        
        selected_product_str = st.selectbox(
            "Select Product",
            product_options,
            key="add_product_select"
        )
        
        selected_product_series = filtered_df[filtered_df.apply(
            lambda row: f"{row['brand']} - {row['name']} ({row['model_number']})" == selected_product_str,
            axis=1
        )]
        
        if selected_product_series.empty:
            st.error("Selected product not found in dataframe.")
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
                'justification': 'Manually added component',
                'specifications': selected_product.get('specifications', ''),
                'image_url': selected_product.get('image_url', ''),
                'gst_rate': selected_product.get('gst_rate', 18),
                'warranty': selected_product.get('warranty', 'Not Specified'),
                'lead_time_days': selected_product.get('lead_time_days', 14),
                'matched': True
            }
            st.session_state.boq_items.append(new_item)
            update_boq_content_with_current_items()
            st.success(f"✅ Added {quantity}x {selected_product['name']}!")
            st.rerun()


def product_search_interface(product_df, currency):
    """Advanced product search interface."""
    st.write("**Search Product Catalog:**")
    
    search_term = st.text_input(
        "Search products...",
        placeholder="Enter name, brand, model, or features",
        key="search_term_input"
    )

    if search_term:
        mask = product_df.apply(
            lambda row: search_term.lower() in str(row['name']).lower() or
                       search_term.lower() in str(row['brand']).lower() or
                       search_term.lower() in str(row['model_number']).lower() or
                       search_term.lower() in str(row['specifications']).lower(),
            axis=1
        )
        search_results = product_df[mask]
        
        st.write(f"Found {len(search_results)} products:")

        for i, (idx, product) in enumerate(search_results.head(10).iterrows()):
            with st.expander(f"{product.get('brand', '')} - {product.get('name', '')[:60]}..."):
                col_a, col_b, col_c = st.columns([2, 1, 1])
                
                with col_a:
                    st.write(f"**Category:** {product.get('category', 'N/A')}")
                    st.write(f"**Sub-Category:** {product.get('sub_category', 'N/A')}")
                    st.write(f"**Model:** {product.get('model_number', 'N/A')}")
                    
                    if pd.notna(product.get('specifications')):
                        st.write(f"**Specs:** {str(product['specifications'])[:150]}...")
                
                with col_b:
                    price = float(product.get('price', 0))
                    display_price = convert_currency(price, currency)
                    st.metric("Price", format_currency(display_price, currency))
                    st.write(f"**Warranty:** {product.get('warranty', 'N/A')}")
                
                with col_c:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{idx}")
                    
                    if st.button("Add", key=f"search_add_{idx}"):
                        new_item = {
                            'category': product.get('category', 'General'),
                            'sub_category': product.get('sub_category', ''),
                            'name': product.get('name', ''),
                            'brand': product.get('brand', ''),
                            'model_number': product.get('model_number', ''),
                            'quantity': add_qty,
                            'price': price,
                            'justification': 'Added via search',
                            'specifications': product.get('specifications', ''),
                            'image_url': product.get('image_url', ''),
                            'gst_rate': product.get('gst_rate', 18),
                            'warranty': product.get('warranty', 'Not Specified'),
                            'lead_time_days': product.get('lead_time_days', 14),
                            'matched': True
                        }
                        st.session_state.boq_items.append(new_item)
                        update_boq_content_with_current_items()
                        st.success(f"✅ Added {add_qty}x {product['name']}!")
                        st.rerun()
