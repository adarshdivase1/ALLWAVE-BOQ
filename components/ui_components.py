# components/ui_components.py
# COMPLETE ENHANCED VERSION - Aligned with boq_generator.py v2.0

import streamlit as st
import pandas as pd
from datetime import datetime

try:
    from components.room_profiles import ROOM_SPECS
    from components.utils import convert_currency, format_currency, get_usd_to_inr_rate
    from components.excel_generator import generate_company_excel
    # This specific import is now used in the UI, so it needs to be available
    from components.boq_generator import extract_top_3_reasons
    from components.multi_room_optimizer import MultiRoomOptimizer
except ImportError:
    ROOM_SPECS = {'Standard Conference Room': {'area_sqft': (250, 400)}}
    def get_usd_to_inr_rate(): return 83.5
    def convert_currency(amount, to_currency="INR"): return amount * (83.5 if to_currency == "INR" else 1)
    def format_currency(amount, currency="INR"): return f"₹{amount:,.0f}" if currency == "INR" else f"${amount:,.2f}"
    def generate_company_excel(*args, **kwargs):
        st.error("Excel component unavailable.")
        return None
    def extract_top_3_reasons(*args, **kwargs):
        return ["Feature 1", "Feature 2", "Feature 3"]
    # Mock class for optimizer if import fails
    class MultiRoomOptimizer:
        def optimize_multi_room_project(self, rooms):
            st.warning("Optimizer component not found. Running without optimization.")
            return {'rooms': rooms, 'optimization': 'none'}


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
            # VALIDATION: Check for duplicate room names
            existing_room_names = [room['name'].lower() for room in st.session_state.project_rooms]
            
            if room_name.lower() in existing_room_names:
                st.error(f"⛔ Room named '{room_name}' already exists. Please use a unique name.")
            else:
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

            # ✅ CRITICAL: Validate rooms before passing
            valid_rooms = [
                room for room in st.session_state.project_rooms
                if room.get('boq_items') and len(room['boq_items']) > 0
            ]

            if not valid_rooms:
                st.warning("No rooms with BOQ items to export.")
            else:
                try:
                    # Import here to avoid circular dependency
                    from components.excel_generator import generate_company_excel
                    from components.utils import get_usd_to_inr_rate
                    
                    # ✅ ADD OPTIMIZATION CALL HERE:
                    from components.multi_room_optimizer import MultiRoomOptimizer
                    optimizer = MultiRoomOptimizer()
                    optimized_result = optimizer.optimize_multi_room_project(valid_rooms)
                    
                    # Show optimization summary
                    if optimized_result.get('optimization') == 'multi-room' and len(valid_rooms) >= 3:
                        st.info(
                            f"🔧 Multi-Room Optimization Applied\n\n"
                            f"**Cost Savings:** {optimized_result['savings_pct']:.1f}%\n\n"
                            f"**Shared Infrastructure:**\n"
                            f"- Centralized network switch\n"
                            f"- Consolidated equipment racks\n"
                            f"- Eliminates {optimized_result['shared_infrastructure']['network']['eliminates_individual_switches']} individual switches"
                        )
                    
                    excel_data = generate_company_excel(
                        project_details=project_details,
                        rooms_data=optimized_result['rooms'],  # ✅ Use optimized rooms
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
                    else:
                        st.error("❌ Failed to generate Excel file. Check excel_generator.py")
                        
                except ImportError as e:
                    st.error(f"❌ Excel generation failed: Missing component - {e}")
                    st.info("Please ensure excel_generator.py and multi_room_optimizer.py are in the components folder")
                except Exception as e:
                    st.error(f"❌ Excel generation error: {e}")
                    import traceback
                    with st.expander("🔍 Technical Details"):
                        st.code(traceback.format_exc())

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

def display_validation_summary(validation_results, selector):
    """Display comprehensive validation report"""
    
    with st.expander("📊 System Validation Report", expanded=bool(validation_results.get('issues'))):
        
        # Brand Compliance
        if validation_results.get('brand_compliance'):
            st.success("**✅ Brand Compliance**")
            for item in validation_results['brand_compliance']:
                st.markdown(f"- {item}")
            st.markdown("---")
        
        # Critical Issues
        if validation_results.get('issues'):
            st.error(f"**🚨 Critical Issues ({len(validation_results['issues'])})**")
            for issue in validation_results['issues']:
                st.markdown(f"- {issue}")
            st.markdown("---")
        
        # Warnings
        if validation_results.get('warnings'):
            st.warning(f"**💡 Recommendations ({len(validation_results['warnings'])})**")
            for warning in validation_results['warnings']:
                st.markdown(f"- {warning}")
            st.markdown("---")
        
        # Selector Warnings (Product Selection Issues)
        if hasattr(selector, 'validation_warnings') and selector.validation_warnings:
            st.info(f"**ℹ️ Product Selection Notes ({len(selector.validation_warnings)})**")
            for warning in selector.validation_warnings:
                severity_emoji = {
                    'CRITICAL': '🚨',
                    'HIGH': '⚠️',
                    'MEDIUM': '💡',
                    'LOW': 'ℹ️'
                }.get(warning.get('severity', 'LOW'), 'ℹ️')
                
                st.markdown(
                    f"{severity_emoji} **{warning['component']}**: {warning['issue']}"
                )

def update_boq_content_with_current_items():
    """Update BOQ content in session state - ensures top_3_reasons exist."""
    if not st.session_state.get('boq_items'):
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items generated yet."
        return

    # CRITICAL: Ensure all items have top_3_reasons field
    for item in st.session_state.boq_items:
        if 'top_3_reasons' not in item or not item['top_3_reasons']:
            # Generate reasons from justification or category
            justification = item.get('justification', '')
            category = item.get('category', 'General')
            
            # Use the already imported helper function
            item['top_3_reasons'] = extract_top_3_reasons(justification, category)
    
    st.session_state.boq_content = f"BOQ with {len(st.session_state.boq_items)} items"


def display_boq_results(product_df, project_details):
    """Display BOQ results with EXPANDABLE CARDS showing Top 3 Reasons - PRODUCTION READY."""
    item_count = len(st.session_state.get('boq_items', []))

    st.subheader(f"📋 Generated Bill of Quantities ({item_count} items)")

    # === DISPLAY BOQ ===
    if st.session_state.get('boq_items'):
        currency = st.session_state.get('currency_select', 'USD')
        
        # Show a summary table (compact view)
        st.markdown("### 📊 Quick Summary")
        summary_data = []
        for item in st.session_state.boq_items:
            match_icon = "✅" if item.get('matched') else "⚠️"
            total_price = item.get('price', 0) * item.get('quantity', 1)
            
            summary_data.append({
                '': match_icon,
                'Category': item.get('category', 'N/A'),
                'Brand': item.get('brand', 'N/A'),
                'Model': item.get('model_number', 'N/A'),
                'Product': item.get('name', 'N/A')[:40] + '...' if len(item.get('name', '')) > 40 else item.get('name', 'N/A'),
                'Qty': item.get('quantity', 1),
                'Unit Price': f"${item.get('price', 0):,.2f}",
                'Total': f"${total_price:,.2f}"
            })
        
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            height=min(400, len(summary_data) * 35 + 38)  # Auto height
        )
        
        # === AVIXA COMPLIANCE CHECKS ===
        if st.session_state.get('validation_results', {}).get('avixa_calculations'):
            avixa_calcs = st.session_state.validation_results['avixa_calculations']
            
            with st.expander("🎯 AVIXA Standards Compliance", expanded=False):
                st.markdown("#### Display Sizing (DISCAS)")
                
                # Check if display size matches AVIXA recommendation
                display_items = [item for item in st.session_state.boq_items if item.get('category') == 'Displays']
                
                if display_items and avixa_calcs.get('display'):
                    actual_size = display_items[0].get('size_requirement', 0)
                    recommended_size = avixa_calcs['display']['selected_size_inches']
                    viewing_distance = avixa_calcs['display']['max_viewing_distance_ft']
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Viewing Distance", f"{viewing_distance:.1f} ft")
                    
                    with col2:
                        st.metric("AVIXA Recommended", f"{recommended_size}\"")
                    
                    with col3:
                        size_diff = actual_size - recommended_size
                        delta_color = "normal" if abs(size_diff) <= 5 else "inverse"
                        st.metric("Selected Size", f"{actual_size}\"", 
                                    f"{size_diff:+.0f}\"", delta_color=delta_color)
                    
                    if abs(size_diff) <= 5:
                        st.success("✅ Display size is AVIXA DISCAS compliant")
                    elif size_diff < -5:
                        st.warning(f"⚠️ Display is {abs(size_diff):.0f}\" smaller than AVIXA recommendation")
                    else:
                        st.info(f"ℹ️ Display is {size_diff:.0f}\" larger than minimum AVIXA requirement")
        
        st.markdown("---")
        st.markdown("### 📋 Detailed View (Click to expand for reasons & specs)")
        
        # Expandable cards with full details
        for i, item in enumerate(st.session_state.boq_items):
            match_icon = "✅" if item.get('matched') else "⚠️"
            total_price = item.get('price', 0) * item.get('quantity', 1)
            
            # Create expander title
            brand = item.get('brand', 'N/A')
            model = item.get('model_number', 'N/A')
            name = item.get('name', 'N/A')
            expander_title = f"{match_icon} **{brand}** {model} - {name[:50]}{'...' if len(name) > 50 else ''}"
            
            with st.expander(expander_title, expanded=False):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Category:** {item.get('category', 'N/A')} / {item.get('sub_category', 'N/A')}")
                    st.write(f"**Product Name:** {name}")
                    st.write(f"**Brand:** {brand}")
                    st.write(f"**Model:** {model}")
                
                with col2:
                    st.metric("Quantity", item.get('quantity', 1))
                    display_price = convert_currency(item.get('price', 0), currency)
                    st.metric("Unit Price", format_currency(display_price, currency))
                
                with col3:
                    display_total = convert_currency(total_price, currency)
                    st.metric("Line Total", format_currency(display_total, currency))
                    st.write(f"**Warranty:** {item.get('warranty', 'N/A')}")
                    st.write(f"**Lead Time:** {item.get('lead_time_days', 14)} days")
                
                st.markdown("---")
                
                # === CRITICAL: TOP 3 REASONS DISPLAY ===
                st.markdown("#### 🎯 Top 3 Reasons for Selecting This Product")
                
                top_3_reasons = item.get('top_3_reasons', [])
                
                # ROBUST PARSING
                reasons_list = []
                if isinstance(top_3_reasons, list):
                    reasons_list = top_3_reasons
                elif isinstance(top_3_reasons, str):
                    # Parse string format
                    for line in top_3_reasons.split('\n'):
                        line = line.strip()
                        if line:
                            # Remove leading numbers/bullets
                            clean_line = line.lstrip('0123456789.•-* ')
                            if len(clean_line) > 5:
                                reasons_list.append(clean_line)
                
                # If still no reasons, generate from category
                if not reasons_list or len(reasons_list) == 0:
                    reasons_list = extract_top_3_reasons(
                        item.get('justification', ''),
                        item.get('category', 'General')
                    )
                    # Update item for next time
                    item['top_3_reasons'] = reasons_list
                
                # Display reasons with nice formatting
                if reasons_list and len(reasons_list) > 0:
                    for idx, reason in enumerate(reasons_list[:3], 1):
                        if reason and len(reason.strip()) > 0:
                            st.markdown(f"**{idx}.** {reason.strip()}")
                else:
                    st.info("ℹ️ Standard component selected for this room configuration")
                
                # Technical justification
                if item.get('justification') and len(item.get('justification', '')) > 10:
                    with st.expander("📝 Technical Justification (Internal Notes)", expanded=False):
                        st.write(item.get('justification'))
                
                # Specifications
                if item.get('specifications'):
                    with st.expander("📐 Product Specifications", expanded=False):
                        st.write(item.get('specifications'))
    
    else:
        st.info("No BOQ content generated yet. Use the form above to generate a BOQ.")

    # Call the new validation summary function
    if st.session_state.get('boq_selector'):
        display_validation_summary(
            st.session_state.get('validation_results', {}),
            st.session_state.boq_selector
        )

    # === SUMMARY METRICS AND DOWNLOAD ===
    if st.session_state.get('boq_items'):
        st.markdown("---")
        col1, col2 = st.columns([1, 1])

        with col1:
            currency = st.session_state.get('currency_select', 'USD')
            total_cost_hardware = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)

            # Add 30% for services
            total_with_services = total_cost_hardware * 1.30

            # Discount for existing customers
            is_existing = st.session_state.get('is_existing_customer', False)
            if is_existing:
                discount_rate = 0.05
                discount_amount = total_with_services * discount_rate
                final_total = total_with_services - discount_amount

                display_final_total = convert_currency(final_total, currency)
                discount_display = format_currency(convert_currency(discount_amount, currency), currency)
                
                st.metric(
                    "💰 Estimated Project Total (Discounted)",
                    format_currency(display_final_total, currency),
                    help=f"Includes installation, warranty, and project management. 5% existing customer discount applied (-{discount_display})."
                )
            else:
                final_total = total_with_services
                display_final_total = convert_currency(final_total, currency)
                st.metric(
                    "💰 Estimated Project Total",
                    format_currency(display_final_total, currency),
                    help="Hardware + Services (Installation 15%, Warranty 5%, Project Management 10%)"
                )

        with col2:
            # Generate Excel
            if st.session_state.project_rooms and st.session_state.current_room_index < len(st.session_state.project_rooms):
                current_room_name = st.session_state.project_rooms[st.session_state.current_room_index]['name']
            else:
                current_room_name = "Current_Room"

            single_room_data = [{'name': current_room_name, 'boq_items': st.session_state.boq_items}]

            # ✅ ADD OPTIMIZATION CALL HERE (for single room, it's a no-op but keeps code consistent)
            optimizer = MultiRoomOptimizer()
            optimized_data = optimizer.optimize_multi_room_project(single_room_data)
            
            # If optimization occurred, show savings
            if optimized_data.get('optimization') == 'multi-room':
                st.success(f"💰 Optimization: {optimized_data['savings_pct']:.1f}% cost reduction via shared infrastructure")
            
            excel_data_current = generate_company_excel(
                project_details=project_details,
                rooms_data=optimized_data['rooms'],  # ✅ Use optimized rooms
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
            currency = st.session_state.get('currency_select', 'USD')
            display_total = convert_currency(total_cost, currency)
            st.metric("Hardware Subtotal", format_currency(display_total, currency))
        else:
            st.metric("Subtotal", "₹0" if st.session_state.get('currency_select', 'USD') == 'INR' else "$0")

    with col3:
        if st.button("🔄 Refresh BOQ Display", help="Update main BOQ display with current items"):
            update_boq_content_with_current_items()
            st.rerun()

    if product_df is None:
        st.error("Cannot load product catalog for editing.")
        return

    currency = st.session_state.get('currency_select', 'USD')
    tabs = st.tabs(["✏️ Edit Current BOQ", "➕ Add Products", "🔍 Product Search", "🔄 Compare Alternatives"])

    with tabs[0]:
        edit_current_boq(product_df, currency)

    with tabs[1]:
        add_products_interface(product_df, currency)

    with tabs[2]:
        product_search_interface(product_df, currency)

    with tabs[3]:
        create_boq_comparison_interface(product_df)


def edit_current_boq(product_df, currency):
    """Interface for editing current BOQ items."""
    if not st.session_state.get('boq_items'):
        st.info("No BOQ items loaded. Generate a BOQ or add products manually.")
        return

    # ✅ DEFENSIVE FIX: Verify required columns exist
    if product_df is None or product_df.empty:
        st.error("Product catalog is empty or not loaded.")
        return
    
    # Check for category column (handle both 'category' and 'primary_category')
    if 'category' not in product_df.columns:
        if 'primary_category' in product_df.columns:
            product_df = product_df.copy()
            product_df['category'] = product_df['primary_category']
        else:
            st.error("Product catalog is missing 'category' column. Please regenerate the product catalog.")
            st.write("Available columns:", product_df.columns.tolist())
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
                category_list = sorted(list(product_df['category'].unique()))
                current_category = item.get('category', 'General AV')
                try:
                    cat_index = category_list.index(current_category)
                except ValueError:
                    cat_index = 0
                item['category'] = st.selectbox("Category", category_list, index=cat_index, key=f"category_{i}")

                sub_cats = sorted(list(product_df[
                    product_df['category'] == item['category']
                ]['sub_category'].unique()))
                
                if not sub_cats:
                    sub_cats = ['General']
                
                current_sub = item.get('sub_category', '')
                try:
                    sub_index = sub_cats.index(current_sub) if current_sub in sub_cats else 0
                except:
                    sub_index = 0
                item['sub_category'] = st.selectbox("Sub-Category", sub_cats, index=sub_index, key=f"subcat_{i}")

                # Show AVIXA recommendation if available
                if item.get('category') == 'Displays' and st.session_state.get('validation_results', {}).get('avixa_calculations'):
                    avixa_display = st.session_state.validation_results['avixa_calculations'].get('display', {})
                    recommended_size = avixa_display.get('selected_size_inches', 0)
                    
                    if recommended_size > 0:
                        current_size = item.get('size_requirement', 0)
                        if abs(current_size - recommended_size) > 5:
                            st.warning(f"💡 AVIXA recommends {recommended_size}\" for optimal viewing")

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

            # Show Top 3 Reasons (read-only display)
            st.markdown("**Top 3 Reasons for This Product:**")
            reasons = item.get('top_3_reasons', [])
            if reasons:
                for idx, reason in enumerate(reasons, 1):
                    st.markdown(f"{idx}. {reason}")
            else:
                st.info("No reasons generated yet")
            
            # Technical justification (editable)
            item['justification'] = st.text_area(
                "Technical Justification (Internal Notes)",
                value=item.get('justification', ''),
                height=60,
                key=f"just_{i}",
                help="Internal technical notes - not shown to client"
            )

    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True):
            st.session_state.boq_items.pop(index)
        st.rerun()


def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ with cascading filters."""
    st.write("**Add Products to BOQ:**")

    # ✅ DEFENSIVE FIX
    if product_df is None or product_df.empty:
        st.error("Product catalog is empty or not loaded.")
        return
    
    if 'category' not in product_df.columns:
        if 'primary_category' in product_df.columns:
            product_df = product_df.copy()
            product_df['category'] = product_df['primary_category']
        else:
            st.error("Product catalog is missing 'category' column.")
            return

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

def create_boq_comparison_interface(product_df):
    """
    Allow users to compare current BOQ with alternatives
    """
    
    st.subheader("🔄 Product Alternatives & Comparison")
    
    if not st.session_state.get('boq_items'):
        st.info("Generate a BOQ first to see alternatives")
        return
    
    # Let user select an item to explore alternatives
    item_names = [
        f"{item.get('category')} - {item.get('brand')} {item.get('model_number')}"
        for item in st.session_state.boq_items
    ]
    
    if not item_names:
        return
    
    selected_item_name = st.selectbox(
        "Select component to view alternatives:",
        item_names,
        key="comparison_item_select"
    )
    
    selected_index = item_names.index(selected_item_name)
    selected_item = st.session_state.boq_items[selected_index]
    
    # Display selected item details
    st.markdown("### 📌 Current Selection")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write(f"**Brand:** {selected_item.get('brand')}")
        st.write(f"**Model:** {selected_item.get('model_number')}")
    
    with col2:
        st.metric("Unit Price", f"${selected_item.get('price', 0):,.2f}")
        st.write(f"**Warranty:** {selected_item.get('warranty', 'N/A')}")
    
    with col3:
        st.metric("Quantity", selected_item.get('quantity', 1))
        total = selected_item.get('price', 0) * selected_item.get('quantity', 1)
        st.metric("Line Total", f"${total:,.2f}")
    
    # Show top 3 reasons
    if selected_item.get('top_3_reasons'):
        with st.expander("🎯 Why This Product?", expanded=True):
            for idx, reason in enumerate(selected_item.get('top_3_reasons', []), 1):
                st.markdown(f"**{idx}.** {reason}")
    
    st.markdown("---")
    
    # Generate alternatives
    if st.button("🔍 Find Alternative Products", key="find_alternatives_btn"):
        with st.spinner("Searching for alternatives..."):
            from components.intelligent_product_selector import ProductRequirement, IntelligentProductSelector
            
            # Create a requirement from the selected item
            requirement = ProductRequirement(
                category=selected_item.get('category'),
                sub_category=selected_item.get('sub_category'),
                quantity=selected_item.get('quantity', 1),
                priority=1,
                justification="Alternative search",
                size_requirement=selected_item.get('size_requirement'),
                client_preference_weight=0.0  # Ignore brand preference for alternatives
            )
            
            selector = IntelligentProductSelector(
                product_df=product_df,
                client_preferences={},
                budget_tier='Standard'
            )
            
            alternatives = selector.suggest_alternatives(selected_item, requirement, count=3)
            
            if alternatives:
                st.markdown("### 🔄 Alternative Options")
                
                for i, alt in enumerate(alternatives, 1):
                    with st.expander(f"Option {i}: {alt.get('brand')} {alt.get('model_number')}"):
                        col_a, col_b, col_c = st.columns([2, 1, 1])
                        
                        with col_a:
                            st.write(f"**Product:** {alt.get('name', '')[:60]}...")
                            st.write(f"**Brand:** {alt.get('brand')}")
                            st.write(f"**Model:** {alt.get('model_number')}")
                        
                        with col_b:
                            st.metric("Price", f"${alt.get('price', 0):,.2f}")
                            
                            diff = alt.get('price_difference', 0)
                            diff_pct = alt.get('price_difference_pct', 0)
                            
                            if diff > 0:
                                st.markdown(f"🔺 **+${abs(diff):,.2f}** ({abs(diff_pct):.1f}% more)")
                            elif diff < 0:
                                st.markdown(f"🔻 **-${abs(diff):,.2f}** ({abs(diff_pct):.1f}% less)")
                            else:
                                st.markdown("➡️ **Same price**")
                        
                        with col_c:
                            if st.button(f"Use This Instead", key=f"swap_{i}_{alt.get('model_number')}"):
                                # Replace the item in BOQ
                                st.session_state.boq_items[selected_index] = {
                                    **alt,
                                    'quantity': selected_item.get('quantity', 1),
                                    'justification': f"Alternative selected by user (replaced {selected_item.get('brand')} {selected_item.get('model_number')})",
                                    'top_3_reasons': selected_item.get('top_3_reasons', []),
                                    'matched': True
                                }
                                
                                st.success(f"✅ Replaced with {alt.get('brand')} {alt.get('model_number')}")
                                st.rerun()
            else:
                st.info("No suitable alternatives found in the catalog")

# ==================== ALSO ADD THIS DEBUG VIEW (OPTIONAL) ====================
def show_boq_debug_info():
    """Debug view to check top_3_reasons data - remove in production."""
    if st.session_state.get('boq_items'):
        with st.expander("🔧 Debug: Top 3 Reasons Data", expanded=False):
            for i, item in enumerate(st.session_state.boq_items):
                st.write(f"**Item {i+1}: {item.get('name', 'Unknown')[:30]}**")
                st.write(f"Type: {type(item.get('top_3_reasons'))}")
                st.write(f"Content: {item.get('top_3_reasons')}")
                st.write("---")
