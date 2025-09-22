import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
import json
from datetime import datetime
from io import BytesIO
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(
    page_title="Enterprise AV BOQ Generator Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enhanced AVIXA Compliance Framework ---
# Note: This class remains the same as it validates the generated BOQ.
class AVIXAComplianceEngine:
    """Comprehensive AVIXA standards compliance engine"""

    def __init__(self):
        self.compliance_rules = {
            'displays': {
                'viewing_distance_multiplier': 2.0,
                'brightness_requirements': {'huddle_room': 300, 'conference_room': 400, 'training_room': 500},
            },
            'audio': {'microphone_pickup_radius': 3},
            'infrastructure': {'power_safety_factor': 1.25, 'cooling_requirements': 3414},
        }

    def validate_system_design(self, boq_items, room_specs):
        compliance_report = {'compliant': True, 'warnings': [], 'errors': [], 'recommendations': []}
        if not boq_items: return compliance_report

        # Simplified validation checks for demonstration
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            display_validation = self._validate_displays(displays, room_specs)
            compliance_report['warnings'].extend(display_validation.get('warnings', []))

        audio_items = [item for item in boq_items if 'audio' in item.get('category', '').lower()]
        if not any('dsp' in item.get('name', '').lower() or 'processor' in item.get('name', '').lower() for item in audio_items):
             compliance_report['errors'].append("Missing essential DSP/Audio Processor.")

        compliance_report['compliance_score'] = self._calculate_compliance_score(compliance_report)
        if compliance_report['errors']:
            compliance_report['compliant'] = False
        return compliance_report

    def _validate_displays(self, displays, room_specs):
        report = {'warnings': []}
        room_length = room_specs.get('length', 16)
        for display in displays:
            size_match = re.search(r'(\d+)"', display.get('name', ''))
            if size_match:
                diagonal_size = int(size_match.group(1))
                screen_height = diagonal_size * 0.49
                min_distance = screen_height * self.compliance_rules['displays']['viewing_distance_multiplier']
                if room_length < min_distance:
                    report['warnings'].append(f"Display may be oversized for room length based on AVIXA standards.")
        return report

    def _calculate_compliance_score(self, compliance_report):
        score = 100 - (len(compliance_report['errors']) * 20) - (len(compliance_report['warnings']) * 5)
        return max(0, score)

# --- Documentation Generator ---
# Note: This class remains largely the same, using the generated data.
class ProfessionalDocumentGenerator:
    """Generate industry-standard documentation packages"""
    def generate_complete_boq_package(self, boq_data, project_info, compliance_report):
        return {
            'executive_summary': self._create_executive_summary(boq_data, project_info),
            'compliance_report': self._format_compliance_report(compliance_report),
        }

    def _create_executive_summary(self, boq_data, project_info):
        total_cost = sum(
            item.get('price', 0) * item.get('quantity', 1)
            for category_items in boq_data.values()
            for item in (category_items if isinstance(category_items, list) else [])
        )
        return f"""
# EXECUTIVE SUMMARY
**Project:** {project_info.get('name', 'Professional AV System Integration')}
**Date:** {datetime.now().strftime('%B %d, %Y')}
## SYSTEM OVERVIEW
This document outlines a proposed audiovisual solution engineered to meet your organization's requirements, based on the specifications provided.
### **TOTAL ESTIMATED PROJECT INVESTMENT: ${total_cost:,.2f}**
"""

    def _format_compliance_report(self, compliance_report):
        report = f"""
# AVIXA COMPLIANCE REPORT
**Compliance Score**: {compliance_report.get('compliance_score', 0)}/100
**Status**: {'✓ COMPLIANT' if compliance_report.get('compliant') else '⚠ ISSUES IDENTIFIED'}
"""
        if compliance_report.get('errors'):
            report += "\n### Critical Issues\n" + "\n".join(f"- {e}" for e in compliance_report['errors'])
        if compliance_report.get('warnings'):
            report += "\n### Warnings\n" + "\n".join(f"- {w}" for w in compliance_report['warnings'])
        return report

# --- NEW: Function to parse the Gemini API response ---
def parse_gemini_response(response_text):
    """
    Parses the JSON response from the Gemini API and converts it into a structured BOQ.
    """
    try:
        # Find the JSON block in the response text
        match = re.search(r"```json\n(.*)\n```", response_text, re.DOTALL)
        if not match:
            st.error("Error: Could not find a JSON block in the model's response.")
            return None
            
        json_str = match.group(1)
        
        # Load the JSON string into a Python dictionary
        data = json.loads(json_str)
        
        # Basic validation to ensure it's a BOQ
        required_keys = ['displays', 'audio', 'control', 'services']
        if not all(key in data for key in required_keys):
            st.warning("Warning: The generated BOQ is missing some standard categories.")

        # Ensure all values are lists of dictionaries
        for key, value in data.items():
            if not isinstance(value, list):
                st.error(f"Data integrity error: The value for '{key}' is not a list.")
                return None
            for item in value:
                if not isinstance(item, dict):
                    st.error(f"Data integrity error: An item in '{key}' is not a dictionary.")
                    return None
                # Ensure price and quantity are numbers
                item['price'] = float(item.get('price', 0))
                item['quantity'] = int(item.get('quantity', 1))

        return data

    except json.JSONDecodeError:
        st.error("Error: Failed to decode the JSON from the model's response. The format is invalid.")
        st.text("Raw Response:")
        st.code(response_text)
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred during parsing: {e}")
        st.text("Raw Response:")
        st.code(response_text)
        return None

# --- Streamlit Application Interface ---
def main():
    """Main Streamlit application"""
    st.markdown("""
    <style>
    .main-header { background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 2rem; border-radius: 10px; text-align: center; margin-bottom: 2rem; }
    .metric-card { background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #2a5298; }
    .compliance-pass { color: #28a745; font-weight: bold; }
    .compliance-warning { color: #ffc107; font-weight: bold; }
    .compliance-error { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-header"><h1>⚡ Enterprise AV BOQ Generator Pro</h1><p>Live Audiovisual System Design & Documentation Platform</p></div>', unsafe_allow_html=True)

    # Initialize session state
    for key in ['boq_generated', 'current_boq', 'project_info', 'room_specs']:
        if key not in st.session_state:
            st.session_state[key] = {} if 'info' in key or 'specs' in key else False if 'generated' in key else None

    with st.sidebar:
        st.header("🎯 Project Configuration")
        
        # API Key Handling from secrets
        api_key_loaded = False
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            if api_key:
                genai.configure(api_key=api_key)
                st.success("✓ AI Engine Connected")
                api_key_loaded = True
            else:
                st.error("❌ Gemini API key is empty in your secrets.")
        except KeyError:
            st.error("❌ Gemini API key not found in Streamlit secrets.")
        except Exception as e:
            st.error(f"API Configuration Error: {str(e)}")

        st.subheader("Project Details")
        project_name = st.text_input("Project Name", value="Enterprise AV Integration")
        client_name = st.text_input("Client Organization", value="Professional Client")
        st.session_state.project_info = {'name': project_name, 'client': client_name}

        st.subheader("System Parameters")
        budget_tier = st.selectbox("Quality Tier", ['economy', 'standard', 'premium', 'enterprise'], index=1)
        max_budget = st.number_input("Maximum Budget ($)", min_value=1000, max_value=500000, value=25000, step=1000)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏗️ System Design", "📊 BOQ Generation", "✅ Compliance Check", "📋 Documentation", "📈 Analytics"])

    with tab1:
        st.header("Professional System Design")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Room Specifications")
            room_type = st.selectbox("Room Type", ['huddle_room', 'conference_room', 'training_room', 'boardroom'], index=1)
            room_length = st.number_input("Room Length (ft)", min_value=8, max_value=100, value=20)
            room_width = st.number_input("Room Width (ft)", min_value=6, max_value=80, value=15)
        with col2:
            st.subheader("Usage Requirements")
            max_occupancy = st.number_input("Maximum Occupancy", min_value=2, max_value=200, value=10)
            usage_patterns = st.multiselect("Primary Uses", ['Video Conferencing', 'Presentations', 'Training', 'Collaboration'], default=['Video Conferencing', 'Presentations'])
            
        st.session_state.room_specs = {
            'type': room_type, 'length': room_length, 'width': room_width, 'area': room_length * room_width,
            'occupancy': max_occupancy, 'usage_patterns': usage_patterns
        }

        if st.button("🎯 Generate System Design", type="primary"):
            if api_key_loaded:
                with st.spinner("Calling Gemini API to generate system design... Please wait."):
                    # --- MODIFIED: Live API Call and Parsing ---
                    # Refined prompt asking for a JSON response
                    system_prompt = f"""
                    You are an expert AV (Audiovisual) system designer creating a Bill of Quantities (BOQ).
                    Based on the following requirements, generate a complete and logical BOQ.

                    Requirements:
                    - Room Type: {room_type}
                    - Dimensions: {room_length}' x {room_width}'
                    - Maximum Occupancy: {max_occupancy} people
                    - Primary Uses: {', '.join(usage_patterns)}
                    - Quality Tier: {budget_tier}
                    - Maximum Budget: ${max_budget:,}

                    Instructions:
                    1.  Create a list of equipment and services divided into the following categories: 'displays', 'audio', 'video_conferencing', 'control', 'infrastructure', 'cabling', and 'services'.
                    2.  For each item, provide a 'name', 'brand', 'model', 'quantity', and estimated 'price'. The price should be a number without currency symbols.
                    3.  Ensure the total cost is reasonably close to the specified budget.
                    4.  The equipment choices must be logical for the room type and usage patterns. For example, a boardroom needs higher-end equipment than a small huddle room.
                    5.  Crucially, format the entire output as a single JSON object. The keys should be the category names, and the values should be a list of item dictionaries. Do not include any text or markdown outside of the JSON block itself.

                    Example of a single item:
                    {{ "name": "86-inch 4K Display", "brand": "LG", "model": "86UM3C", "quantity": 1, "price": 4500 }}
                    
                    Now, generate the complete BOQ in a JSON block.
                    ```json
                    {{ ... your JSON output ... }}
                    ```
                    """
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(system_prompt)
                        
                        # Call the new parsing function
                        live_boq = parse_gemini_response(response.text)
                        
                        if live_boq:
                            st.session_state.current_boq = live_boq
                            st.session_state.boq_generated = True
                            st.success("✓ Live system design generated and parsed successfully!")
                        else:
                            st.error("Failed to generate or parse a valid BOQ from the API response.")
                            st.session_state.boq_generated = False
                            
                    except Exception as e:
                        st.error(f"An error occurred while calling the Gemini API: {e}")
            else:
                st.warning("Cannot generate design. Please ensure your Gemini API key is configured in the secrets.")
    
    # The following tabs will only render if a BOQ was successfully generated
    if st.session_state.boq_generated and st.session_state.current_boq:
        boq_data = st.session_state.current_boq
        all_items = [item for sublist in boq_data.values() if isinstance(sublist, list) for item in sublist]

        with tab2:
            st.header("Generated Bill of Quantities (BOQ)")
            total_project_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in all_items)
            st.metric("Total Project Cost", f"${total_project_cost:,.2f}")
            
            for category_name, items in boq_data.items():
                if items:
                    st.subheader(f"{category_name.replace('_', ' ').title()}")
                    df = pd.DataFrame(items)
                    df['Unit Price'] = df['price'].apply(lambda x: f"${x:,.2f}")
                    df['Total'] = (df['quantity'] * df['price']).apply(lambda x: f"${x:,.2f}")
                    st.dataframe(df[['name', 'brand', 'model', 'quantity', 'Unit Price', 'Total']], use_container_width=True, hide_index=True)

        with tab3:
            st.header("AVIXA Compliance Validation")
            engine = AVIXAComplianceEngine()
            report = engine.validate_system_design(all_items, st.session_state.room_specs)
            score = report.get('compliance_score', 0)
            st.markdown(f"### Compliance Score: {score}/100")
            if report.get('errors'):
                st.error("Critical Issues Found:")
                for e in report['errors']: st.write(f"- {e}")
            if report.get('warnings'):
                st.warning("Warnings:")
                for w in report['warnings']: st.write(f"- {w}")

        with tab4:
            st.header("Professional Documentation Package")
            doc_gen = ProfessionalDocumentGenerator()
            engine = AVIXAComplianceEngine()
            compliance_report = engine.validate_system_design(all_items, st.session_state.room_specs)
            doc_package = doc_gen.generate_complete_boq_package(boq_data, st.session_state.project_info, compliance_report)
            for name, content in doc_package.items():
                with st.expander(f"📄 {name.replace('_', ' ').title()}", expanded=True):
                    st.markdown(content)

        with tab5:
            st.header("Project Analytics & Insights")
            costs_by_category = {cat: sum(item['price'] * item['quantity'] for item in items) for cat, items in boq_data.items() if items}
            if costs_by_category:
                fig = px.pie(
                    values=list(costs_by_category.values()),
                    names=[k.replace('_', ' ').title() for k in costs_by_category.keys()],
                    title="Cost Breakdown by Category"
                )
                st.plotly_chart(fig, use_container_width=True)

def create_excel_export(boq_data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        all_items_data = []
        for category, items in boq_data.items():
            for item in items:
                item_data = item.copy()
                item_data['Main Category'] = category.replace('_', ' ').title()
                all_items_data.append(item_data)
        
        if all_items_data:
            df = pd.DataFrame(all_items_data)
            df['Total Price'] = df['quantity'] * df['price']
            df.to_excel(writer, sheet_name='Detailed BOQ', index=False)
    output.seek(0)
    return output.getvalue()


if __name__ == "__main__":
    main()
