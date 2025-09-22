import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
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
class AVIXAComplianceEngine:
    """Comprehensive AVIXA standards compliance engine"""

    def __init__(self):
        self.compliance_rules = {
            'displays': {
                'viewing_distance_multiplier': 2.0,  # Screen height × 2 minimum
                'max_viewing_angle': 30,  # degrees from center
                'brightness_requirements': {
                    'huddle_room': 300,  # cd/m²
                    'conference_room': 400,
                    'training_room': 500,
                    'auditorium': 600
                },
                'contrast_ratio_min': 1000,
                'resolution_standards': {
                    'small_room': '1920x1080',
                    'medium_room': '3840x2160',
                    'large_room': '3840x2160'
                }
            },
            'audio': {
                'spl_requirements': {
                    'conference': 70,  # dB SPL
                    'presentation': 75,
                    'auditorium': 80
                },
                'coverage_overlap': 0.1,  # 10% overlap between speakers
                'microphone_pickup_radius': 3,  # feet
                'echo_cancellation': True,
                'noise_reduction': True,
                'frequency_response': '20Hz-20kHz ±3dB'
            },
            'infrastructure': {
                'power_safety_factor': 1.25,  # 25% safety margin
                'cooling_requirements': 3414,  # BTU per kW
                'cable_category_min': 'Cat6A',
                'fiber_requirements': {
                    'distance_threshold': 328,  # feet
                    'bandwidth_min': '10Gb'
                },
                'ups_backup_minutes': 15
            },
            'accessibility': {
                'ada_compliance': True,
                'hearing_loop_required': False,
                'control_height_max': 48,  # inches AFF
                'visual_indicators': True,
                'tactile_feedback': True
            },
            'environmental': {
                'operating_temperature': (32, 104),  # Fahrenheit
                'operating_humidity': (10, 80),  # Percent RH
                'noise_rating_max': 35,  # dB-A
                'heat_dissipation_factor': 0.85
            }
        }

    def validate_system_design(self, boq_items, room_specs):
        """Comprehensive AVIXA compliance validation"""
        compliance_report = {
            'compliant': True,
            'warnings': [],
            'errors': [],
            'recommendations': [],
            'compliance_score': 0
        }

        # Validate each subsystem
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            display_validation = self._validate_displays(displays, room_specs)
            compliance_report['warnings'].extend(display_validation.get('warnings', []))
            compliance_report['errors'].extend(display_validation.get('errors', []))
            compliance_report['recommendations'].extend(display_validation.get('recommendations', []))

        audio_items = [item for item in boq_items if 'audio' in item.get('category', '').lower()]
        if audio_items:
            audio_validation = self._validate_audio_system(audio_items, room_specs)
            compliance_report['warnings'].extend(audio_validation.get('warnings', []))
            compliance_report['errors'].extend(audio_validation.get('errors', []))
            compliance_report['recommendations'].extend(audio_validation.get('recommendations', []))

        infrastructure_validation = self._validate_infrastructure(boq_items, room_specs)
        compliance_report['warnings'].extend(infrastructure_validation.get('warnings', []))
        compliance_report['errors'].extend(infrastructure_validation.get('errors', []))
        compliance_report['recommendations'].extend(infrastructure_validation.get('recommendations', []))

        accessibility_validation = self._validate_accessibility(boq_items, room_specs)
        compliance_report['warnings'].extend(accessibility_validation.get('warnings', []))
        compliance_report['errors'].extend(accessibility_validation.get('errors', []))
        compliance_report['recommendations'].extend(accessibility_validation.get('recommendations', []))

        # Calculate overall compliance score
        compliance_report['compliance_score'] = self._calculate_compliance_score(compliance_report)

        if compliance_report['errors']:
            compliance_report['compliant'] = False

        return compliance_report

    def _validate_displays(self, displays, room_specs):
        """Validate display sizing and positioning per AVIXA standards"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        room_length = room_specs.get('length', 16)
        room_type = room_specs.get('type', 'conference_room')

        for display in displays:
            size_match = re.search(r'(\d+)"', display.get('name', ''))
            if size_match:
                diagonal_size = int(size_match.group(1))
                screen_height = diagonal_size * 0.49  # For 16:9 aspect ratio

                # AVIXA 2H rule validation
                min_distance = screen_height * self.compliance_rules['displays']['viewing_distance_multiplier']
                max_distance = screen_height * 8

                if room_length < min_distance:
                    report['errors'].append(
                        f"AVIXA Violation: Room too small for {diagonal_size}\" display. "
                        f"Minimum viewing distance (2H rule): {min_distance:.1f} ft, Room length: {room_length} ft"
                    )
                elif room_length > max_distance:
                    report['warnings'].append(
                        f"Display may be undersized. {diagonal_size}\" display at {room_length} ft "
                        f"exceeds 8H maximum viewing distance ({max_distance:.1f} ft)"
                    )

                # Brightness requirements
                required_brightness = self.compliance_rules['displays']['brightness_requirements'].get(
                    room_type.lower(), 400
                )
                brightness_match = re.search(r'(\d+)\s*(?:cd/m²|nits)', display.get('specifications', ''), re.I)
                if brightness_match:
                    actual_brightness = int(brightness_match.group(1))
                    if actual_brightness < required_brightness:
                        report['warnings'].append(
                            f"Display brightness {actual_brightness} cd/m² below recommended "
                            f"{required_brightness} cd/m² for {room_type}"
                        )
                else:
                    report['recommendations'].append(
                        f"Verify display brightness meets {required_brightness} cd/m² requirement for {room_type}"
                    )
        return report

    def _validate_audio_system(self, audio_items, room_specs):
        """Validate audio system per AVIXA standards"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        room_area = room_specs.get('area', 200)

        # Validate microphone coverage
        microphones = [item for item in audio_items if 'mic' in item.get('name', '').lower()]
        speakers = [item for item in audio_items if any(word in item.get('name', '').lower()
                                                        for word in ['speaker', 'loudspeaker', 'ceiling'])]
        if microphones:
            mic_radius = self.compliance_rules['audio']['microphone_pickup_radius']
            total_coverage = sum(item.get('quantity', 1) for item in microphones) * (3.14159 * mic_radius**2)
            if total_coverage < room_area:
                report['warnings'].append(
                    f"Insufficient microphone coverage. Current: {total_coverage:.0f} sq ft, "
                    f"Required: {room_area:.0f} sq ft"
                )

        if speakers:
            speaker_count = sum(item.get('quantity', 1) for item in speakers)
            recommended_speakers = max(2, int(room_area / 150))
            if speaker_count < recommended_speakers:
                report['recommendations'].append(
                    f"Consider additional speakers. Current: {speaker_count}, "
                    f"Recommended for {room_area:.0f} sq ft: {recommended_speakers}"
                )

        # Check for essential audio components
        has_dsp = any('dsp' in item.get('name', '').lower() or 'processor' in item.get('name', '').lower()
                      for item in audio_items)
        if not has_dsp:
            report['errors'].append(
                "Missing DSP/Audio Processor - Required for professional AV systems per AVIXA standards"
            )
        return report

    def _validate_infrastructure(self, boq_items, room_specs):
        """Validate infrastructure requirements"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        total_power = 0
        power_estimates = {'display': 200, 'audio': 100, 'control': 50, 'video': 150}

        for item in boq_items:
            category = item.get('category', '').lower()
            quantity = item.get('quantity', 1)
            for cat_key, power in power_estimates.items():
                if cat_key in category:
                    total_power += power * quantity
                    break

        total_power_with_safety = total_power * self.compliance_rules['infrastructure']['power_safety_factor']
        standard_circuit_capacity = 1800  # 15A at 120V
        dedicated_circuit_capacity = 2400  # 20A at 120V

        if total_power_with_safety > standard_circuit_capacity:
            if total_power_with_safety <= dedicated_circuit_capacity:
                report['warnings'].append(
                    f"System requires dedicated 20A circuit. Total power: {total_power_with_safety:.0f}W "
                    f"(with 25% safety factor)"
                )
            else:
                report['errors'].append(
                    f"Power requirements exceed single circuit capacity. "
                    f"Total: {total_power_with_safety:.0f}W requires multiple circuits or 30A service"
                )

        cooling_btus = (total_power / 1000) * self.compliance_rules['infrastructure']['cooling_requirements']
        if cooling_btus > 5000:
            report['recommendations'].append(
                f"HVAC consideration required. System heat load: {cooling_btus:.0f} BTU/hr"
            )

        network_devices = len([item for item in boq_items if any(term in item.get('name', '').lower()
                                                                for term in ['switch', 'codec', 'control', 'display'])])
        if network_devices > 4:
            report['recommendations'].append(
                f"Consider managed network switch for {network_devices} networked devices"
            )
        return report

    def _validate_accessibility(self, boq_items, room_specs):
        """Validate ADA and accessibility compliance"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        if room_specs.get('ada_compliance', False):
            control_items = [item for item in boq_items if 'control' in item.get('category', '').lower()]
            touch_panels = [item for item in control_items if 'touch' in item.get('name', '').lower()]
            if touch_panels and not any('accessible' in item.get('name', '').lower() for item in touch_panels):
                report['warnings'].append("ADA compliance: Consider accessible control interface options")

            assistive_listening = any('loop' in item.get('name', '').lower() or
                                      'assistive' in item.get('name', '').lower() for item in boq_items)
            if not assistive_listening:
                report['recommendations'].append(
                    "ADA compliance: Consider assistive listening system for hearing accessibility"
                )
        return report

    def _calculate_compliance_score(self, compliance_report):
        """Calculate overall compliance score (0-100)"""
        error_count = len(compliance_report.get('errors', []))
        warning_count = len(compliance_report.get('warnings', []))
        score = 100 - (error_count * 20) - (warning_count * 5)
        return max(0, score)


# --- Professional Documentation Generator ---
class ProfessionalDocumentGenerator:
    """Generate industry-standard documentation packages"""
    def generate_complete_boq_package(self, boq_data, project_info, compliance_report):
        package = {
            'executive_summary': self._create_executive_summary(boq_data, project_info),
            'technical_specifications': self._create_detailed_tech_specs(),
            'installation_timeline': self._create_installation_schedule(),
            'compliance_report': self._format_compliance_report(compliance_report),
            'training_program': self._create_training_curriculum(),
            'warranty_matrix': self._create_warranty_schedule(),
            'maintenance_plan': self._create_maintenance_program()
        }
        return package

    def _create_executive_summary(self, boq_data, project_info):
        total_cost = sum(
            item.get('price', 0) * item.get('quantity', 1)
            for category_items in boq_data.values()
            for item in (category_items if isinstance(category_items, list) else [])
        )
        return f"""
# EXECUTIVE SUMMARY
**Project:** {project_info.get('name', 'Professional AV System Integration')}
**Client:** {project_info.get('client', 'Enterprise Client')}
**Date:** {datetime.now().strftime('%B %d, %Y')}

## SYSTEM OVERVIEW
This comprehensive audiovisual solution is engineered to meet your organization's collaboration and communication requirements while maintaining strict compliance with AVIXA industry standards.

## INVESTMENT SUMMARY
- **Equipment & Materials**: ${total_cost * 0.70:,.2f}
- **Professional Services**: ${total_cost * 0.30:,.2f}
### **TOTAL PROJECT INVESTMENT: ${total_cost:,.2f}**

## PROJECT TIMELINE
- **Procurement & Staging**: 4-6 weeks
- **Installation & Commissioning**: 3-5 business days
### **Total Project Duration: 8-12 weeks from approval**
"""

    def _create_detailed_tech_specs(self):
        return """
# TECHNICAL SPECIFICATIONS
## VIDEO SUBSYSTEM
- **Resolution**: Native 4K (3840x2160) throughout signal chain
- **HDCP**: HDCP 2.2 compliance for content protection
## AUDIO SUBSYSTEM
- **Frequency Response**: 20Hz - 20kHz ±3dB
- **Echo Cancellation**: Full-duplex with 128ms tail length
## CONTROL SUBSYSTEM
- **Response Time**: <200ms for all commands
- **Network Protocol**: TCP/IP with SSL encryption
"""

    def _create_installation_schedule(self):
        return """
# INSTALLATION SCHEDULE
## Day 1: Infrastructure & Mounting
- Install display mounting hardware, run cabling, and install equipment rack.
## Day 2: Equipment Installation
- Install and connect all electronic components in the rack and at display/table locations.
## Day 3: Programming & Commissioning
- Load control system code, tune audio DSP, and calibrate video system.
- Perform comprehensive system testing and obtain client sign-off.
"""

    def _format_compliance_report(self, compliance_report):
        if not compliance_report:
            return "# COMPLIANCE REPORT\n\nCompliance validation pending system finalization."
        report = f"""
# AVIXA COMPLIANCE REPORT
**Compliance Score**: {compliance_report.get('compliance_score', 0)}/100
**Status**: {'✓ COMPLIANT' if compliance_report.get('compliant', False) else '⚠ ISSUES IDENTIFIED'}
"""
        if compliance_report.get('errors'):
            report += "### Critical Issues (Must Address)\n"
            for error in compliance_report['errors']:
                report += f"- ❌ {error}\n"
        if compliance_report.get('warnings'):
            report += "### Warnings (Recommended Action)\n"
            for warning in compliance_report['warnings']:
                report += f"- ⚠️ {warning}\n"
        if compliance_report.get('recommendations'):
            report += "### Optimization Recommendations\n"
            for rec in compliance_report['recommendations']:
                report += f"- 💡 {rec}\n"
        return report

    def _create_training_curriculum(self):
        return """
# USER TRAINING CURRICULUM
## SESSION 1: BASIC OPERATIONS (1 hour)
- System Startup & Shutdown
- Content sharing from laptops
- Video conferencing basics
"""

    def _create_warranty_schedule(self):
        return """
# WARRANTY & SUPPORT MATRIX
- **Display Systems**: 3 Years Parts & Labor
- **Audio Equipment**: 5 Years Parts & Labor
- **Control Systems**: 3 Years Hardware
- **Installation Workmanship**: 1 Year
"""

    def _create_maintenance_program(self):
        return """
# PREVENTIVE MAINTENANCE PROGRAM
## QUARTERLY MAINTENANCE
- Complete system diagnostic scan and error log analysis.
- Physical inspection and cleaning of all accessible components.
- Installation of approved firmware updates.
"""


# --- Streamlit Application Interface ---

def main():
    """Main Streamlit application"""
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298); color: white; padding: 2rem;
        border-radius: 10px; text-align: center; margin-bottom: 2rem;
    }
    .metric-card {
        background: white; padding: 1rem; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #2a5298;
    }
    .compliance-pass { color: #28a745; font-weight: bold; }
    .compliance-warning { color: #ffc107; font-weight: bold; }
    .compliance-error { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="main-header">
        <h1>⚡ Enterprise AV BOQ Generator Pro</h1>
        <p>Professional Audiovisual System Design & Documentation Platform</p>
        <p><i>AVIXA Standards Compliant | Enterprise Grade Solutions</i></p>
    </div>
    """, unsafe_allow_html=True)

    if 'boq_generated' not in st.session_state:
        st.session_state.boq_generated = False
    if 'current_boq' not in st.session_state:
        st.session_state.current_boq = {}
    if 'project_info' not in st.session_state:
        st.session_state.project_info = {}
    if 'room_specs' not in st.session_state:
        st.session_state.room_specs = {}

    with st.sidebar:
        st.header("🎯 Project Configuration")
        
        # --- MODIFIED: API Key Handling ---
        st.subheader("AI Configuration")
        api_key_loaded = False
        try:
            # This line reads from the secrets manager on the cloud OR your local .streamlit/secrets.toml file
            api_key = st.secrets["GEMINI_API_KEY"]
            if api_key:
                genai.configure(api_key=api_key)
                st.success("✓ AI Engine Connected")
                api_key_loaded = True
            else:
                st.error("❌ Gemini API key is empty in your secrets.")
        except KeyError:
            st.error("❌ Gemini API key not found. Please add it to your Streamlit secrets.")
        except Exception as e:
            st.error(f"API Configuration Error: {str(e)}")
        # --- END MODIFICATION ---

        st.subheader("Project Details")
        project_name = st.text_input("Project Name", value="Enterprise AV Integration")
        client_name = st.text_input("Client Organization", value="Professional Client")
        st.session_state.project_info = {
            'name': project_name,
            'client': client_name,
            'date': datetime.now().strftime('%Y-%m-%d')
        }

        st.subheader("System Parameters")
        budget_tier = st.selectbox(
            "Quality Tier",
            ['economy', 'standard', 'premium', 'enterprise'],
            index=1,
            help="Select quality/performance tier for equipment selection"
        )
        max_budget = st.number_input(
            "Maximum Budget ($)",
            min_value=1000, max_value=500000, value=25000, step=1000
        )

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏗️ System Design", "📊 BOQ Generation", "✅ Compliance Check", "📋 Documentation", "📈 Analytics"
    ])

    with tab1:
        st.header("Professional System Design")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Room Specifications")
            room_type = st.selectbox("Room Type", ['huddle_room', 'conference_room', 'training_room', 'boardroom'], index=1)
            room_length = st.number_input("Room Length (ft)", min_value=8, max_value=100, value=16)
            room_width = st.number_input("Room Width (ft)", min_value=6, max_value=80, value=12)
            room_area = room_length * room_width
            st.metric("Room Area", f"{room_area:,} sq ft")
        with col2:
            st.subheader("Usage Requirements")
            max_occupancy = st.number_input("Maximum Occupancy", min_value=2, max_value=200, value=12)
            usage_patterns = st.multiselect("Primary Uses", ['Video Conferencing', 'Presentations', 'Training'], default=['Video Conferencing', 'Presentations'])
            ada_compliance = st.checkbox("ADA Compliance Required", value=False)
        
        st.session_state.room_specs = {
            'type': room_type, 'length': room_length, 'width': room_width, 'area': room_area,
            'occupancy': max_occupancy, 'usage_patterns': usage_patterns, 'ada_compliance': ada_compliance
        }

        if st.button("🎯 Generate System Design", type="primary"):
            # --- MODIFIED: Button Logic Check ---
            if api_key_loaded:
                with st.spinner("Generating professional system design..."):
                    system_prompt = f"""
                    You are a professional AV system designer. Generate a comprehensive BOQ for the following room:
                    Room Type: {room_type}, Dimensions: {room_length}' x {room_width}', Occupancy: {max_occupancy} people,
                    Usage: {', '.join(usage_patterns)}, Budget Tier: {budget_tier}, Max Budget: ${max_budget:,}.
                    Generate a detailed equipment list with categories, quantities, and estimated pricing.
                    Format as structured data.
                    """
                    try:
                        # For demonstration, generate a structured BOQ directly.
                        # In a real app, you would parse the response from the model.
                        # model = genai.GenerativeModel('gemini-pro')
                        # response = model.generate_content(system_prompt)
                        demo_boq = generate_demo_boq(st.session_state.room_specs, budget_tier, max_budget)
                        st.session_state.current_boq = demo_boq
                        st.session_state.boq_generated = True
                        st.success("✓ Professional system design generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating design: {str(e)}")
            else:
                st.warning("Please ensure your Gemini API key is configured correctly in the secrets.")
            # --- END MODIFICATION ---

    if st.session_state.boq_generated and st.session_state.current_boq:
        boq_data = st.session_state.current_boq
        all_items = [item for sublist in boq_data.values() if isinstance(sublist, list) for item in sublist]

        with tab2:
            st.header("Professional BOQ Generation")
            total_equipment_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in all_items if 'service' not in item.get('category','').lower())
            total_services_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in all_items if 'service' in item.get('category','').lower())
            total_project_cost = total_equipment_cost + total_services_cost
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Project Cost", f"${total_project_cost:,.0f}")
            col2.metric("Equipment Cost", f"${total_equipment_cost:,.0f}")
            col3.metric("Services Cost", f"${total_services_cost:,.0f}")
            col4.metric("Total Line Items", len(all_items))
            
            for category_name, items in boq_data.items():
                if isinstance(items, list) and items:
                    st.subheader(f"{category_name.replace('_', ' ').title()}")
                    df = pd.DataFrame(items)
                    display_cols = ['name', 'brand', 'model', 'quantity', 'price']
                    df_display = df[display_cols].copy()
                    df_display['price'] = df_display['price'].apply(lambda x: f"${x:,.0f}")
                    st.dataframe(df_display.rename(columns={'name': 'Item', 'brand': 'Brand', 'model': 'Model', 'quantity': 'Qty', 'price': 'Unit Price'}), use_container_width=True, hide_index=True)
            
            st.subheader("Export Options")
            col5, col6 = st.columns(2)
            with col5:
                excel_data = create_excel_export(boq_data, st.session_state.project_info)
                st.download_button(
                    label="📊 Download Excel BOQ", data=excel_data,
                    file_name=f"BOQ_{project_name.replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        with tab3:
            st.header("AVIXA Compliance Validation")
            compliance_engine = AVIXAComplianceEngine()
            compliance_report = compliance_engine.validate_system_design(all_items, st.session_state.room_specs)
            score = compliance_report.get('compliance_score', 0)
            score_color = "compliance-pass" if score >= 90 else "compliance-warning" if score >= 70 else "compliance-error"
            status_icon = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
            
            st.markdown(f"""
            <div class="metric-card">
                <h2>{status_icon} Compliance Score: <span class="{score_color}">{score}/100</span></h2>
            </div>
            """, unsafe_allow_html=True)
            
            if compliance_report.get('errors'):
                st.subheader("❌ Critical Issues")
                for error in compliance_report['errors']: st.error(error)
            if compliance_report.get('warnings'):
                st.subheader("⚠️ Warnings")
                for warning in compliance_report['warnings']: st.warning(warning)
            if compliance_report.get('recommendations'):
                st.subheader("💡 Recommendations")
                for rec in compliance_report['recommendations']: st.info(rec)

        with tab4:
            st.header("Professional Documentation Package")
            doc_generator = ProfessionalDocumentGenerator()
            compliance_engine = AVIXAComplianceEngine()
            compliance_report = compliance_engine.validate_system_design(all_items, st.session_state.room_specs)
            doc_package = doc_generator.generate_complete_boq_package(boq_data, st.session_state.project_info, compliance_report)
            
            for doc_name, doc_content in doc_package.items():
                with st.expander(f"📄 {doc_name.replace('_', ' ').title()}", expanded=(doc_name == 'executive_summary')):
                    st.markdown(doc_content)
        
        with tab5:
            st.header("Project Analytics & Insights")
            categories = []
            costs = []
            for category, items in boq_data.items():
                if isinstance(items, list):
                    category_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
                    categories.append(category.replace('_', ' ').title())
                    costs.append(category_cost)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("💰 Cost Breakdown by Category")
                if categories and costs:
                    fig_pie = px.pie(values=costs, names=categories, title="Project Cost Distribution")
                    st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                st.subheader("📈 Cost Analysis")
                total_cost = sum(costs)
                room_area = st.session_state.room_specs.get('area', 1)
                equipment_cost = sum(c for cat, c in zip(categories, costs) if 'service' not in cat.lower())
                services_cost = total_cost - equipment_cost
                
                st.metric("Cost per Sq Ft", f"${total_cost/room_area:.0f}")
                st.metric("Equipment %", f"{(equipment_cost/total_cost)*100:.0f}%")
                st.metric("Services %", f"{(services_cost/total_cost)*100:.0f}%")


def generate_demo_boq(room_specs, budget_tier, max_budget):
    """Generate a comprehensive demo BOQ"""
    tier_multipliers = {'economy': 0.7, 'standard': 1.0, 'premium': 1.4, 'enterprise': 1.8}
    multiplier = tier_multipliers.get(budget_tier, 1.0)
    
    room_area = room_specs.get('area', 200)
    occupancy = room_specs.get('occupancy', 12)
    view_dist = room_specs.get('length', 16)
    
    # Simple display size calculation based on viewing distance
    display_size = max(55, min(98, int(view_dist * 4)))

    boq = {
        'displays': [{'category': 'Primary Display', 'name': f'Professional {display_size}" 4K Display', 'brand': 'Samsung', 'model': f'QM{display_size}H', 'quantity': 1, 'price': int(1500 * multiplier * (display_size / 65)), 'specifications': f'{display_size}" 4K UHD, 400 cd/m²'}],
        'audio': [
            {'category': 'Audio DSP', 'name': 'Professional Audio Processor', 'brand': 'Biamp', 'model': 'TesiraFORTE', 'quantity': 1, 'price': int(1800 * multiplier)},
            {'category': 'Ceiling Speakers', 'name': 'Ceiling Mount Speakers', 'brand': 'JBL', 'model': 'Control 26CT', 'quantity': max(2, int(room_area / 100)), 'price': int(250 * multiplier)},
            {'category': 'Microphone System', 'name': 'Tabletop Microphone', 'brand': 'Shure', 'model': 'MXA310', 'quantity': max(1, int(occupancy / 8)), 'price': int(1200 * multiplier)}
        ],
        'video_conferencing': [{'category': 'Video Codec', 'name': 'Video Conferencing System', 'brand': 'Poly', 'model': 'Studio X50', 'quantity': 1, 'price': int(3500 * multiplier)}],
        'control': [
            {'category': 'Control Processor', 'name': 'AV Control System', 'brand': 'Extron', 'model': 'IPCP Pro 250', 'quantity': 1, 'price': int(1500 * multiplier)},
            {'category': 'Touch Panel', 'name': '7" Touch Panel', 'brand': 'Extron', 'model': 'TLP Pro 725T', 'quantity': 1, 'price': int(1600 * multiplier)}
        ],
        'infrastructure': [
            {'category': 'Display Mount', 'name': 'Fixed Wall Mount', 'brand': 'Chief', 'model': 'LSM1U', 'quantity': 1, 'price': int(250 * multiplier)},
            {'category': 'Network Switch', 'name': '8-Port PoE+ Switch', 'brand': 'Netgear', 'model': 'GS108PP', 'quantity': 1, 'price': int(200 * multiplier)},
            {'category': 'UPS Battery Backup', 'name': '1500VA UPS', 'brand': 'APC', 'model': 'SMT1500', 'quantity': 1, 'price': int(600 * multiplier)}
        ],
        'cabling': [{'category': 'Structured Cabling', 'name': 'Cabling & Connectors', 'brand': 'Belden/Extron', 'model': 'Bulk', 'quantity': 1, 'price': int(800 * multiplier)}],
        'services': [
            {'category': 'System Design & Engineering', 'name': 'System Design Services', 'brand': 'Pro Services', 'model': 'DESIGN-01', 'quantity': 1, 'price': int(1500 * multiplier)},
            {'category': 'Installation Labor', 'name': 'Complete System Installation', 'brand': 'Pro Services', 'model': 'INSTALL-01', 'quantity': 1, 'price': int(3500 * multiplier)},
            {'category': 'System Programming', 'name': 'Control System Programming', 'brand': 'Pro Services', 'model': 'PROG-01', 'quantity': 1, 'price': int(2500 * multiplier)},
            {'category': 'Project Management', 'name': 'Project Management', 'brand': 'Pro Services', 'model': 'PM-01', 'quantity': 1, 'price': int(1200 * multiplier)}
        ]
    }
    return boq


def create_excel_export(boq_data, project_info):
    """Create Excel export of BOQ data"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        all_items_data = []
        for category, items in boq_data.items():
            if isinstance(items, list):
                for item in items:
                    item_data = item.copy()
                    item_data['Main Category'] = category.replace('_', ' ').title()
                    all_items_data.append(item_data)
        
        if all_items_data:
            df = pd.DataFrame(all_items_data)
            df['Total Price'] = df['quantity'] * df['price']
            cols_order = ['Main Category', 'name', 'brand', 'model', 'quantity', 'price', 'Total Price', 'specifications']
            df = df[[col for col in cols_order if col in df.columns]]
            df.to_excel(writer, sheet_name='Detailed BOQ', index=False)
    output.seek(0)
    return output.getvalue()


if __name__ == "__main__":
    main()
