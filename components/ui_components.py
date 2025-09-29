# components/ui_components.py

import streamlit as st
from datetime import datetime
from components.visualizer import ROOM_SPECS # Assuming visualizer.py has ROOM_SPECS
from components.utils import convert_currency, format_currency, get_usd_to_inr_rate
from components.excel_generator import generate_company_excel

def create_project_header():
    """Create professional project header."""
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("Professional AV BOQ Generator")
        st.caption("Production-ready Bill of Quantities with technical validation")
    with col2:
        st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}", key="project_id_input")
    with col3:
        st.number_input("Quote Valid (Days)", min_value=15, max_value=90, value=30, key="quote_days_input")

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
    return {"dedicated_circuit": has_dedicated_circuit, "network_capability": network_capability, "cable_management": cable_management, "ada_compliance": ada_compliance, "fire_code_compliance": fire_code_compliance, "security_clearance": security_clearance}

def create_multi_room_interface():
    """Interface for managing multiple rooms in a project."""
    st.subheader("Multi-Room Project Management")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        room_name = st.text_input("New Room Name", value=f"Room {len(st.session_state.project_rooms) + 1}")

    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Add New Room to Project", type="primary", use_container_width=True):
            new_room = {
                'name': room_name,
                'type': st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)'),
                'area': st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16),
                'boq_items': [],
                'features': st.session_state.get('features_text_area', ''),
                'technical_reqs': {}
            }
            st.session_state.project_rooms.append(new_room)
            st.success(f"Added '{room_name}' to the project.")
            st.rerun()

    with col3:
        st.write("")
        st.write("")
        if st.session_state.project_rooms:
            # ★★★ UPDATED CALL ★★★
            # 1. Prepare project details dictionary
            project_details = {
                'project_name': st.session_state.get('project_name_input', 'Multi_Room_Project'),
                'client_name': st.session_state.get('client_name_input', 'Valued Client'),
                'gst_rates': st.session_state.get('gst_rates', {})
            }
            # 2. Get the currency rate
            usd_to_inr_rate = get_usd_to_inr_rate()

            # 3. Call the new component function
            excel_data = generate_company_excel(
                project_details=project_details,
                rooms_data=st.session_state.project_rooms,
                usd_to_inr_rate=usd_to_inr_rate
            )

            if excel_data:
                filename = f"{project_details['project_name']}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                st.download_button(
                    label="📊 Download Full Project BOQ",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="secondary"
                )

    # Display current rooms
    if st.session_state.project_rooms:
        st.markdown("---")
        st.write("**Current Project Rooms:**")

        # --- FIX: SAVE STATE BEFORE SWITCHING ---
        previous_room_index = st.session_state.current_room_index
        if previous_room_index < len(st.session_state.project_rooms):
            st.session_state.project_rooms[previous_room_index]['boq_items'] = st.session_state.boq_items
        # --- END FIX ---

        room_options = [room['name'] for room in st.session_state.project_rooms]

        try:
            current_index = st.session_state.current_room_index
        except (AttributeError, IndexError):
            current_index = 0
            st.session_state.current_room_index = 0

        # Ensure index is valid
        if current_index >= len(room_options):
            current_index = 0
            st.session_state.current_room_index = 0

        selected_room_name = st.selectbox(
            "Select a room to view or edit its BOQ:",
            options=room_options,
            index=current_index,
            key="room_selector"
        )

        new_index = room_options.index(selected_room_name)
        if new_index != st.session_state.current_room_index:
            st.session_state.current_room_index = new_index
            # Now, we load the data from the newly selected room into the editor state.
            selected_room_boq = st.session_state.project_rooms[new_index].get('boq_items', [])
            st.session_state.boq_items = selected_room_boq
            update_boq_content_with_current_items()
            st.rerun()

        selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
        st.info(f"You are currently editing **{selected_room['name']}**. Any generated or edited BOQ will be saved for this room.")

        if st.button(f"🗑️ Remove '{selected_room['name']}' from Project", type="secondary"):
            st.session_state.project_rooms.pop(st.session_state.current_room_index)
            # Reset index and clear the editor to avoid errors
            st.session_state.current_room_index = 0
            if st.session_state.project_rooms:
                st.session_state.boq_items = st.session_state.project_rooms[0].get('boq_items', [])
            else:
                st.session_state.boq_items = []
            st.rerun()
    # This is also self-contained UI code.
    pass # Placeholder for brevity

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days, product_df):
    """Display BOQ results with interactive editing capabilities."""

    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    st.subheader(f"Generated Bill of Quantities ({item_count} items)")

    # Validation results
    if validation_results and validation_results.get('issues'):
        st.error("Critical Issues Found:")
        for issue in validation_results['issues']: st.write(f"- {issue}")

    if validation_results and validation_results.get('warnings'):
        st.warning("Technical Recommendations & Compliance Notes:")
        for warning in validation_results['warnings']: st.write(f"- {warning}")

    # Display BOQ content
    if boq_content:
        st.markdown(boq_content)
    else:
        st.info("No BOQ content generated yet. Use the interactive editor below.")

    # Totals
    if 'boq_items' in st.session_state and st.session_state.boq_items:
        currency = st.session_state.get('currency', 'USD')
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)

        if currency == 'INR':
            display_total = convert_currency(total_cost * 1.30, 'INR') # Include services
            st.metric("Estimated Project Total", format_currency(display_total, 'INR'), help="Includes installation, warranty, and contingency")
        else:
            st.metric("Estimated Project Total", format_currency(total_cost * 1.30, 'USD'), help="Includes installation, warranty, and contingency")

    # Interactive Editor
    st.markdown("---")
    create_interactive_boq_editor(product_df)
    pass # Placeholder for brevity

# And so on for other UI functions like create_interactive_boq_editor, etc.
# The goal is to move all `st.` calls that build the interface into this file.
