# app.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime
import json
import time

# --- Import from components directory ---
from components.visualizer import create_3d_visualization, ROOM_SPECS
## --- CHANGE 4: Refactor Excel Generation ---
# Import the new Excel generator module
from components.excel_generator import generate_company_excel

# --- All other non-UI and non-Excel functions remain here ---
# (e.g., get_usd_to_inr_rate, format_currency, load_and_validate_data, setup_gemini,
# calculate_avixa_recommendations, determine_equipment_requirements, generate_boq_with_justifications,
# BOQValidator, extract_enhanced_boq_items, etc.)
# ... These functions are unchanged from your original code ...

# --- NEW: State Management for Room Switching ---
def save_current_room_data():
    """Saves the current state of the BOQ editor to the selected room."""
    if 'project_rooms' in st.session_state and st.session_state.project_rooms:
        current_index = st.session_state.current_room_index
        if 0 <= current_index < len(st.session_state.project_rooms):
            st.session_state.project_rooms[current_index]['boq_items'] = st.session_state.get('boq_items', [])
            st.session_state.project_rooms[current_index]['avixa_calcs'] = st.session_state.get('avixa_calcs')
            st.session_state.project_rooms[current_index]['validation_results'] = st.session_state.get('validation_results')


def switch_to_selected_room():
    """Loads the data for the newly selected room from the dropdown."""
    if 'room_selector' in st.session_state and 'project_rooms' in st.session_state:
        selected_name = st.session_state.room_selector
        # Find the index of the selected room
        new_index = next((i for i, room in enumerate(st.session_state.project_rooms) if room['name'] == selected_name), None)

        if new_index is not None:
            st.session_state.current_room_index = new_index
            selected_room = st.session_state.project_rooms[new_index]
            
            # Load the selected room's data into the main session state for the editor
            st.session_state.boq_items = selected_room.get('boq_items', [])
            st.session_state.avixa_calcs = selected_room.get('avixa_calcs')
            st.session_state.validation_results = selected_room.get('validation_results')
            update_boq_content_with_current_items()


# --- UI Components ---
def create_project_header():
    """Create professional project header."""
    ## --- CHANGE 1: Centralized Project Details ---
    with st.expander("📝 Project & Client Details", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.text_input("Project Name", key="project_name_input", value="New AV Project")
        with col2:
            st.text_input("Client Name", key="client_name_input", value="Valued Client")
        with col3:
            st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}", key="project_id_input")
        with col4:
            st.number_input("Quote Valid (Days)", min_value=15, max_value=90, value=30, key="quote_days_input")


def create_multi_room_interface():
    """Interface for managing multiple rooms in a project."""
    st.subheader("Multi-Room Project Management")

    col1, col2 = st.columns([2, 1])
    with col1:
        room_name = st.text_input("New Room Name", value=f"Room {len(st.session_state.project_rooms) + 1}", key="new_room_name")
    with col2:
        st.write("") # Spacer
        if st.button("➕ Add New Room to Project", type="primary", use_container_width=True):
            if room_name and room_name not in [r['name'] for r in st.session_state.project_rooms]:
                new_room = {
                    'name': room_name,
                    'type': st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)'),
                    'area': st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16),
                    'boq_items': [],
                    'avixa_calcs': None,
                    'validation_results': None,
                    'features': st.session_state.get('features_text_area', ''),
                    'technical_reqs': {}
                }
                st.session_state.project_rooms.append(new_room)
                st.success(f"Added '{room_name}' to the project.")
                # Automatically switch to the new room
                save_current_room_data() # Save before switching
                st.session_state.current_room_index = len(st.session_state.project_rooms) - 1
                switch_to_selected_room()
                st.rerun()
            else:
                st.error("Please provide a unique name for the new room.")

    if st.session_state.project_rooms:
        st.markdown("---")
        
        room_options = [room['name'] for room in st.session_state.project_rooms]
        current_room_name = room_options[st.session_state.current_room_index]
        
        ## --- CHANGE 2: Improved Multi-Room Workflow ---
        st.selectbox(
            "Select a room to view or edit its BOQ:",
            options=room_options,
            index=st.session_state.current_room_index,
            key="room_selector",
            on_change=lambda: (save_current_room_data(), switch_to_selected_room()) # Save and then switch
        )
        
        selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
        st.info(f"You are currently editing **{selected_room['name']}**. Any generated or edited BOQ will be saved for this room.")

        if st.button(f"🗑️ Remove '{selected_room['name']}' from Project", type="secondary"):
            st.session_state.project_rooms.pop(st.session_state.current_room_index)
            st.session_state.current_room_index = 0
            switch_to_selected_room() if st.session_state.project_rooms else st.session_state.clear()
            st.rerun()

## --- CHANGE 3: Project Dashboard ---
def create_project_dashboard():
    """Displays a dashboard with key metrics for the current room."""
    st.subheader("📊 Project Dashboard")

    if not st.session_state.project_rooms:
        st.info("Add a room to the project to see the dashboard.")
        return

    selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
    st.markdown(f"**Showing details for: `{selected_room['name']}`**")

    avixa_calcs = st.session_state.get('avixa_calcs')
    validation = st.session_state.get('validation_results')
    boq_items = st.session_state.get('boq_items', [])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in boq_items)
        total_cost_inr = convert_currency(total_cost * 1.30, 'INR') # Includes services
        st.metric("💰 Est. Project Total (INR)", f"₹{total_cost_inr:,.0f}")
        
    with col2:
        score = validation.get('avixa_compliance_score', 0) if validation else 0
        st.metric("✅ AVIXA Compliance Score", f"{score}/100")
        
    with col3:
        display_size = avixa_calcs.get('detailed_viewing_display_size', 'N/A') if avixa_calcs else 'N/A'
        st.metric("🖥️ Recommended Display", f'{display_size}"')
        
    with col4:
        power_load = avixa_calcs.get('total_power_load_watts', 'N/A') if avixa_calcs else 'N/A'
        st.metric("⚡ Total Power Load", f"{power_load} W")

    if validation and (validation.get('avixa_issues') or validation.get('avixa_warnings')):
        with st.expander("View Compliance Details"):
            for issue in validation.get('avixa_issues', []):
                st.error(f"**Issue:** {issue}")
            for warning in validation.get('avixa_warnings', []):
                st.warning(f"**Warning:** {warning}")


# --- Main Application ---
def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        show_login_page()
        return

    st.set_page_config(page_title="Professional AV BOQ Generator", layout="wide")

    # Session State Initialization
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = None
    if 'avixa_calcs' not in st.session_state: st.session_state.avixa_calcs = None
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state:
        st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    # Data Loading
    product_df, guidelines, data_issues = load_and_validate_data()
    # ... (rest of data loading logic is the same) ...

    model = setup_gemini()
    if not model: return

    # --- Sidebar ---
    # ... (Sidebar code is largely the same, but client/project name inputs are removed) ...

    # --- Main Content ---
    create_project_header() # New centralized header
    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Project Dashboard", "Multi-Room Setup", "Room Design", "Generate & Edit BOQ", "3D Visualization"])

    with tab1:
        create_project_dashboard() # New dashboard tab

    with tab2:
        create_multi_room_interface()

    with tab3:
        st.subheader("Room Design & Requirements")
        c1, c2 = st.columns(2)
        with c1:
            room_area, ceiling_height = create_room_calculator()
        with c2:
            features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified'", height=100, key="features_text_area")
        st.markdown("---")
        technical_reqs = create_advanced_requirements()
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)

    with tab4:
        st.subheader("BOQ Generation & Editing")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("🚀 Generate/Update BOQ for Current Room", type="primary", use_container_width=True):
                # ... (BOQ generation logic is the same) ...
                if boq_items:
                    # Save all results to session state
                    st.session_state.boq_content = boq_content
                    st.session_state.boq_items = boq_items
                    st.session_state.avixa_calcs = avixa_calcs
                    # ... (Validation logic is the same) ...
                    st.session_state.validation_results = { ... }
                    
                    # Save results to the specific room object
                    save_current_room_data()
                    st.success(f"✅ Generated BOQ for '{st.session_state.project_rooms[st.session_state.current_room_index]['name']}'!")
                    st.rerun()

        with col2:
            if st.session_state.project_rooms:
                project_details = {
                    'project_name': st.session_state.get('project_name_input', 'AV Project'),
                    'client_name': st.session_state.get('client_name_input', 'Valued Client'),
                }
                excel_data = generate_company_excel(project_details, st.session_state.project_rooms, st.session_state.gst_rates)
                
                if excel_data:
                    filename = f"{project_details['project_name']}_Full_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                    st.download_button(
                        label="📊 Download Full Project BOQ (All Rooms)",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        
        if st.session_state.boq_content or st.session_state.boq_items:
            st.markdown("---")
            display_boq_results(st.session_state.boq_content, st.session_state.validation_results, "", 0, product_df)

    with tab5:
        create_3d_visualization()

if __name__ == "__main__":
    main()
