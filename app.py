# app.py

import streamlit as st
import time
from datetime import datetime
import base64
from pathlib import Path

# --- Component Imports ---
try:
    from components.data_handler import load_and_validate_data
    from components.gemini_handler import setup_gemini
    # --- CHANGE START: Simplified imports, added post_process_boq ---
    from components.boq_generator import generate_boq_from_ai, post_process_boq
    # --- CHANGE END ---
    from components.ui_components import (
        create_project_header, create_room_calculator, create_advanced_requirements,
        create_multi_room_interface, display_boq_results, update_boq_content_with_current_items
    )
    from components.visualizer import create_3d_visualization, ROOM_SPECS
except ImportError as e:
    st.error(f"Failed to import a necessary component: {e}. Please ensure all component files are in the 'components' directory and are complete.")
    st.stop()


# (UI helper functions like load_css, show_login_page, etc. remain unchanged)
def load_css():
    """Reads the style.css file and injects it into the Streamlit app."""
    css_file_path = "assets/style.css"
    try:
        with open(css_file_path, "r") as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"Could not find style.css. Please ensure it is in the '{css_file_path}' directory.")


def main():
    # Set page config and load CSS
    st.set_page_config(page_title="AllWave AV - BOQ Generator", layout="wide", initial_sidebar_state="expanded")
    load_css()
    
    # Initialize session state variables
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    # ... other initializations ...

    # Load data and setup AI model
    with st.spinner("Initializing system modules..."):
        product_df, guidelines, data_issues = load_and_validate_data()
        st.session_state.product_df = product_df
    if product_df is None:
        st.error("Fatal Error: Product catalog could not be loaded."); st.stop()
    model = setup_gemini()
    
    # Render UI components (header, sidebar, tabs)
    # ... (this part of your UI code is fine) ...
    
    # Tab 4: Generate BOQ
    with st.tabs(...)[3]: # Assuming it's the 4th tab
        if st.button("✨ Generate & Validate Production-Ready BOQ", type="primary", use_container_width=True):
            if not model:
                st.error("AI Model is not available. Please check API key.")
            else:
                with st.spinner("Generating initial BOQ with AI..."):
                    # (Code to get room_area and technical_reqs remains the same)
                    room_area = st.session_state.get('room_length_input', 24.0) * st.session_state.get('room_width_input', 16.0)
                    # ...
                    
                    boq_items, avixa_calcs, equipment_reqs = generate_boq_from_ai(
                        model, product_df, guidelines,
                        st.session_state.room_type_select,
                        st.session_state.budget_tier_slider,
                        st.session_state.get('features_text_area', ''),
                        technical_reqs,
                        room_area 
                    )
                
                if boq_items:
                    # --- CHANGE START: Replaced multiple cleanup calls with one master function ---
                    processed_boq = post_process_boq(boq_items, product_df)
                    # --- CHANGE END ---
                    
                    st.session_state.boq_items = processed_boq
                    update_boq_content_with_current_items()
                    
                    # (Rest of the logic to save to session state and show success message)
                    st.success("BOQ Generated and Validated Successfully!")
                else:
                    st.error("Failed to generate BOQ. The AI may have returned an empty response.")
        
        # Display results
        if st.session_state.get('boq_items'):
            # (Your existing display_boq_results call is fine here)
            pass

if __name__ == "__main__":
    main()
