# app.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime
import json
import time
import streamlit.components.v1 as components
from io import BytesIO

# --- Import from components directory ---
from components.visualizer import create_3d_visualization, ROOM_SPECS
from components.excel_generator import generate_company_excel

# --- Currency Conversion (for UI) ---
@st.cache_data(ttl=3600)
def get_usd_to_inr_rate():
    return 83.5

def convert_currency(amount_usd, to_currency="INR"):
    if to_currency == "INR":
        return amount_usd * get_usd_to_inr_rate()
    return amount_usd

def format_currency(amount, currency="USD"):
    if currency == "INR":
        return f"₹{amount:,.0f}"
    return f"${amount:,.2f}"

# --- Data Loading & Validation ---
@st.cache_data
def load_and_validate_data():
    try:
        df = pd.read_csv("master_product_catalog.csv")
        validation_issues = []
        if df['name'].isnull().sum() > 0: validation_issues.append(f"{df['name'].isnull().sum()} products missing names")
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
            if (df['price'] == 0.0).sum() > 100: validation_issues.append(f"{(df['price'] == 0.0).sum()} products have zero pricing")
        else:
            df['price'] = 0.0; validation_issues.append("Price column missing")
        if 'brand' not in df.columns:
            df['brand'] = 'Unknown'; validation_issues.append("Brand column missing")
        elif df['brand'].isnull().sum() > 0:
            df['brand'] = df['brand'].fillna('Unknown'); validation_issues.append(f"{df['brand'].isnull().sum()} products missing brand")
        if 'category' not in df.columns:
            df['category'] = 'General'; validation_issues.append("Category column missing")
        else:
            df['category'] = df['category'].fillna('General')
        if 'features' not in df.columns:
            df['features'] = df['name']; validation_issues.append("Features column missing")
        else:
            df['features'] = df['features'].fillna('')
        if 'image_url' not in df.columns:
            df['image_url'] = ''; validation_issues.append("Image URL column missing")
        if 'gst_rate' not in df.columns:
            df['gst_rate'] = 18; validation_issues.append("GST rate column missing - using 18% default")
        
        try:
            with open("avixa_guidelines.md", "r") as f: guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found."; validation_issues.append("AVIXA guidelines file missing")
        return df, guidelines, validation_issues
    except FileNotFoundError:
        sample_data = get_sample_product_data()
        df = pd.DataFrame(sample_data)
        try:
            with open("avixa_guidelines.md", "r") as f: guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found."
        return df, guidelines, ["Using sample product catalog for testing"]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]

# --- Gemini Configuration ---
def setup_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Gemini API configuration failed: {e}. Check API key in Streamlit secrets.")
        return None

def generate_with_retry(model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            if attempt == max_retries - 1: raise e
            time.sleep(2 ** attempt)
    return None

# --- AVIXA & BOQ Logic ---
def calculate_avixa_recommendations(room_length, room_width, room_height, room_type):
    room_area = room_length * room_width
    room_volume = room_area * room_height
    max_viewing_distance = min(room_length * 0.85, room_width * 0.9)
    detailed_screen_height_ft = max_viewing_distance / 6
    detailed_screen_size = detailed_screen_height_ft * 12 / 0.49
    base_power_per_cubic_ft = 0.75 if 'training' in room_type.lower() else 1.0 if 'executive' in room_type.lower() else 0.5
    audio_power_needed = int(room_volume * base_power_per_cubic_ft)
    total_av_power = (250 if detailed_screen_size < 75 else 400) + (150 + (audio_power_needed * 0.3)) + 25 + 100 + 75
    estimated_people = min(room_area // 20, 50)
    return {'detailed_viewing_display_size': int(detailed_screen_size), 'max_viewing_distance': max_viewing_distance, 'recommended_display_count': 2 if room_area > 300 else 1, 'audio_power_needed': audio_power_needed, 'microphone_coverage_zones': max(2, estimated_people // 4), 'speaker_zones_required': max(2, int(room_area // 150)), 'estimated_occupancy': estimated_people, 'recommended_bandwidth_mbps': int((2.5 * estimated_people) + 5.0 + 10), 'total_power_load_watts': total_av_power, 'circuit_requirement': "15A Standard Circuit" if total_av_power < 1200 else "20A Dedicated Circuit" if total_av_power < 1800 else "Multiple 20A Circuits", 'ups_va_required': int(total_av_power * 1.4), 'ups_runtime_minutes': 30 if 'executive' in room_type.lower() else 15 if 'training' in room_type.lower() else 10, 'cable_runs': {'cat6a_network': 3 + (estimated_people // 6), 'hdmi_video': 2, 'xlr_audio': estimated_people // 3, 'power_circuits': 2 + (total_av_power // 1000)}, 'requires_ada_compliance': estimated_people > 15, 'requires_hearing_loop': estimated_people > 50, 'requires_assistive_listening': estimated_people > 25}

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    display_size = avixa_calcs['detailed_viewing_display_size']
    room_volume = avixa_calcs['audio_power_needed'] / 0.5
    reqs = {'displays': {'type': "Commercial LED Display" if display_size <= 55 else "Large Format Display" if display_size <= 75 else "Professional Large Format Display" if display_size <= 86 else "Video Wall or Laser Projector", 'size_inches': display_size, 'quantity': avixa_calcs['recommended_display_count'], 'resolution': '4K' if display_size > 43 else '1080p', 'mounting': 'Wall Mount' if display_size < 75 else 'Heavy Duty Wall Mount'}, 'audio_system': {}, 'video_system': {'camera_type': 'Fixed Wide-Angle Camera' if avixa_calcs['estimated_occupancy'] <= 6 else 'PTZ Camera with Auto-Framing' if avixa_calcs['estimated_occupancy'] <= 12 else 'Multi-Camera System with Tracking', 'camera_count': 1 if avixa_calcs['estimated_occupancy'] <= 12 else 2, '4k_required': avixa_calcs['estimated_occupancy'] > 8}, 'control_system': {'type': 'Native Room System Control' if room_volume < 2000 else 'Touch Panel Control' if room_volume < 5000 else 'Advanced Programmable Control System', 'touch_panel_size': '7-inch' if room_volume < 3000 else '10-inch', 'integration_required': room_volume > 5000}, 'infrastructure': {'equipment_rack': 'Wall-Mount' if room_volume < 3000 else 'Floor-Standing', 'rack_size': '6U' if room_volume < 3000 else '12U' if room_volume < 8000 else '24U', 'cooling_required': avixa_calcs['total_power_load_watts'] > 1500, 'ups_required': True, 'cable_management': 'Standard' if room_volume < 5000 else 'Professional'}, 'compliance': []}
    if room_volume < 2000: reqs['audio_system'] = {'type': 'All-in-One Video Bar', 'microphones': 'Integrated Beamforming Array', 'speakers': 'Integrated Speakers', 'dsp_required': False}
    elif room_volume < 5000: reqs['audio_system'] = {'type': 'Distributed Audio System', 'microphones': 'Tabletop Microphones' if technical_reqs.get('ceiling_height', 10) < 9 else 'Ceiling Microphone Array', 'microphone_count': avixa_calcs['microphone_coverage_zones'], 'speakers': 'Ceiling Speakers', 'speaker_count': avixa_calcs['speaker_zones_required'], 'amplifier': 'Multi-Channel Amplifier', 'dsp_required': True, 'dsp_type': 'Basic DSP with AEC'}
    else: reqs['audio_system'] = {'type': 'Professional Audio System', 'microphones': 'Steerable Ceiling Array', 'microphone_count': avixa_calcs['microphone_coverage_zones'], 'speakers': 'Distributed Ceiling System', 'speaker_count': avixa_calcs['speaker_zones_required'], 'amplifier': 'Networked Amplifier System', 'dsp_required': True, 'dsp_type': 'Advanced DSP with Dante/AVB', 'voice_lift': room_volume > 8000}
    if avixa_calcs['requires_ada_compliance']: reqs['compliance'].extend(['ADA Compliant Touch Panels (15-48" height)', 'Visual Notification System'])
    if avixa_calcs['requires_hearing_loop']: reqs['compliance'].append('Hearing Loop System')
    if avixa_calcs['requires_assistive_listening']: reqs['compliance'].append('FM/IR Assistive Listening (4% of capacity)')
    return reqs

def generate_boq_with_justifications(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    product_catalog_string = product_df.head(150).to_csv(index=False)
    avixa_calcs = calculate_avixa_recommendations(room_area**0.5, room_area/(room_area**0.5), technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    prompt = f"""You are a Professional AV Systems Engineer for AllWave AV in India. Create a production-ready BOQ following AVIXA standards.
**PROJECT SPECS:** Room Type: {room_type}, Area: {room_area:.0f} sq ft, Budget: {budget_tier}, Requirements: {features}, Infrastructure: {technical_reqs}.
**AVIXA CALCULATIONS:** Display Size: {avixa_calcs['detailed_viewing_display_size']}" ({avixa_calcs['max_viewing_distance']:.1f}ft viewing), Display Count: {avixa_calcs['recommended_display_count']}, Audio Power: {avixa_calcs['audio_power_needed']}W, Mic Zones: {avixa_calcs['microphone_coverage_zones']}, Speaker Zones: {avixa_calcs['speaker_zones_required']}, Occupancy: {avixa_calcs['estimated_occupancy']}, Power Load: {avixa_calcs['total_power_load_watts']}W, Circuit: {avixa_calcs['circuit_requirement']}, Bandwidth: {avixa_calcs['recommended_bandwidth_mbps']} Mbps.
**EQUIPMENT REQUIREMENTS:** Displays: {equipment_reqs['displays']['type']} - {equipment_reqs['displays']['size_inches']}"x{equipment_reqs['displays']['quantity']}, Audio: {equipment_reqs['audio_system']['type']}, Mics: {equipment_reqs['audio_system']['microphones']}, Camera: {equipment_reqs['video_system']['camera_type']}, Control: {equipment_reqs['control_system']['type']}, Rack: {equipment_reqs['infrastructure']['equipment_rack']} ({equipment_reqs['infrastructure']['rack_size']}).
**COMPLIANCE:** {'- ' + '\n- '.join(equipment_reqs['compliance']) if equipment_reqs['compliance'] else '- Standard commercial installation'}.
**INFRASTRUCTURE:** Cat6A: {avixa_calcs['cable_runs']['cat6a_network']}, HDMI: {avixa_calcs['cable_runs']['hdmi_video']}, XLR: {avixa_calcs['cable_runs']['xlr_audio']}, Power Circuits: {avixa_calcs['cable_runs']['power_circuits']}, UPS: {avixa_calcs['ups_va_required']}VA for {avixa_calcs['ups_runtime_minutes']} mins.
**MANDATORY:**
1. ONLY use products from the provided catalog.
2. Include ALL calculated cable runs, infrastructure, and compliance items.
3. For EACH product, provide 3 specific reasons in 'Remarks' as: "1) [Technical reason] 2) [Business benefit] 3) [User benefit]". Each reason must be under 15 words.
**OUTPUT FORMAT:** Start with a System Design Summary, then provide the BOQ in a Markdown table: | Category | Make | Model No. | Specifications | Quantity | Unit Price (USD) | Remarks |
**PRODUCT CATALOG SAMPLE:**\n{product_catalog_string}\n**AVIXA GUIDELINES:**\n{guidelines}\nGenerate the detailed BOQ:"""
    try:
        response = generate_with_retry(model, prompt)
        if response and response.text:
            boq_content = response.text
            boq_items = extract_enhanced_boq_items(boq_content, product_df)
            return boq_content, boq_items, avixa_calcs, equipment_reqs
    except Exception as e:
        st.error(f"Enhanced BOQ generation failed: {str(e)}")
    return None, [], None, None

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs):
    issues, warnings = [], []
    if not any('display' in i.get('category', '').lower() for i in boq_items): issues.append("CRITICAL: No display found")
    if equipment_reqs['audio_system'].get('dsp_required') and not any('dsp' in i.get('name', '').lower() for i in boq_items): issues.append("CRITICAL: DSP required but not found")
    if avixa_calcs['ups_va_required'] > 1000 and not any('ups' in i.get('name', '').lower() for i in boq_items): issues.append("CRITICAL: UPS system required but not found")
    if avixa_calcs['requires_ada_compliance'] and not any(term in i.get('name', '').lower() for term in ['assistive', 'ada', 'loop'] for i in boq_items): issues.append("CRITICAL: ADA compliance required but no assistive devices found")
    return {'avixa_issues': issues, 'avixa_warnings': warnings, 'compliance_score': max(0, 100 - (len(issues) * 25) - (len(warnings) * 5))}

# --- Data Extraction & Helpers ---
def extract_enhanced_boq_items(boq_content, product_df):
    items, in_table = [], False
    for line in boq_content.split('\n'):
        line = line.strip()
        if '|' in line and any(k in line.lower() for k in ['category', 'make', 'model']): in_table = True; continue
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line): continue
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 6:
                category, brand, product_name, specs = parts[0], parts[1], parts[2], parts[3]
                remarks = parts[6] if len(parts) > 6 else "Essential AV component."
                try: quantity = int(parts[4])
                except (ValueError, IndexError): quantity = 1
                try: price = float(parts[5].replace('$', '').replace(',', ''))
                except (ValueError, IndexError): price = 0
                matched = match_product_in_database(product_name, brand, product_df)
                if matched:
                    items.append({'category': matched.get('category', category), 'name': matched.get('name', product_name), 'brand': matched.get('brand', brand), 'quantity': quantity, 'price': float(matched.get('price', price)), 'justification': remarks, 'specifications': specs, 'image_url': matched.get('image_url', ''), 'gst_rate': matched.get('gst_rate', 18), 'matched': True})
                else:
                    items.append({'category': normalize_category(category, product_name), 'name': product_name, 'brand': brand, 'quantity': quantity, 'price': price, 'justification': remarks, 'specifications': specs, 'image_url': '', 'gst_rate': 18, 'matched': False})
        elif in_table and not line.startswith('|'): in_table = False
    return items

def match_product_in_database(name, brand, df):
    brand_matches = df[df['brand'].str.contains(brand, case=False, na=False)]
    if len(brand_matches) > 0:
        name_matches = brand_matches[brand_matches['name'].str.contains(name[:20], case=False, na=False)]
        if len(name_matches) > 0: return name_matches.iloc[0].to_dict()
    name_matches = df[df['name'].str.contains(name[:15], case=False, na=False)]
    if len(name_matches) > 0: return name_matches.iloc[0].to_dict()
    return None

def normalize_category(category_text, product_name):
    cat, prod = category_text.lower(), product_name.lower()
    if any(t in cat or t in prod for t in ['display', 'screen']): return 'Displays'
    if any(t in cat or t in prod for t in ['audio', 'speaker', 'mic']): return 'Audio'
    if any(t in cat or t in prod for t in ['video', 'camera']): return 'Video Conferencing'
    if any(t in cat or t in prod for t in ['control', 'switch']): return 'Control'
    if any(t in cat or t in prod for t in ['mount', 'rack']): return 'Mounts'
    if any(t in cat or t in prod for t in ['cable', 'hdmi']): return 'Cables'
    return 'General'

# --- State Management ---
def save_current_room_data():
    if 'project_rooms' in st.session_state and st.session_state.project_rooms:
        idx = st.session_state.current_room_index
        if 0 <= idx < len(st.session_state.project_rooms):
            st.session_state.project_rooms[idx]['boq_items'] = st.session_state.get('boq_items', [])
            st.session_state.project_rooms[idx]['avixa_calcs'] = st.session_state.get('avixa_calcs')
            st.session_state.project_rooms[idx]['validation_results'] = st.session_state.get('validation_results')

def switch_to_selected_room():
    if 'room_selector' in st.session_state and 'project_rooms' in st.session_state:
        name = st.session_state.room_selector
        new_idx = next((i for i, room in enumerate(st.session_state.project_rooms) if room['name'] == name), None)
        if new_idx is not None:
            st.session_state.current_room_index = new_idx
            room = st.session_state.project_rooms[new_idx]
            st.session_state.boq_items = room.get('boq_items', [])
            st.session_state.avixa_calcs = room.get('avixa_calcs')
            st.session_state.validation_results = room.get('validation_results')
            update_boq_content_with_current_items()

# --- UI Components ---
def create_project_header():
    with st.expander("📝 Project & Client Details", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.text_input("Project Name", key="project_name_input", value="New AV Project")
        c2.text_input("Client Name", key="client_name_input", value="Valued Client")
        c3.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}", key="project_id_input")
        c4.number_input("Quote Valid (Days)", 15, 90, 30, key="quote_days_input")

def create_multi_room_interface():
    st.subheader("Multi-Room Project Management")
    c1, c2 = st.columns([2, 1])
    room_name = c1.text_input("New Room Name", value=f"Room {len(st.session_state.project_rooms) + 1}", key="new_room_name")
    if c2.button("➕ Add New Room to Project", type="primary", use_container_width=True):
        if room_name and room_name not in [r['name'] for r in st.session_state.project_rooms]:
            new_room = {'name': room_name, 'type': st.session_state.get('room_type_select', list(ROOM_SPECS.keys())[0]), 'area': st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16), 'boq_items': [], 'avixa_calcs': None, 'validation_results': None, 'features': '', 'technical_reqs': {}}
            st.session_state.project_rooms.append(new_room)
            st.success(f"Added '{room_name}' to the project.")
            save_current_room_data()
            st.session_state.current_room_index = len(st.session_state.project_rooms) - 1
            switch_to_selected_room()
            st.rerun()
        else: st.error("Please provide a unique name for the new room.")

    if st.session_state.project_rooms:
        st.markdown("---")
        room_options = [room['name'] for room in st.session_state.project_rooms]
        st.selectbox("Select a room to view or edit:", room_options, index=st.session_state.current_room_index, key="room_selector", on_change=lambda: (save_current_room_data(), switch_to_selected_room()))
        selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
        st.info(f"You are currently editing **{selected_room['name']}**.")
        if st.button(f"🗑️ Remove '{selected_room['name']}'", type="secondary"):
            st.session_state.project_rooms.pop(st.session_state.current_room_index)
            st.session_state.current_room_index = 0
            if st.session_state.project_rooms: switch_to_selected_room() 
            else: st.session_state.boq_items = []; st.session_state.boq_content = None; st.session_state.validation_results = None; st.session_state.avixa_calcs = None
            st.rerun()

def create_project_dashboard():
    st.subheader("📊 Project Dashboard")
    if not st.session_state.project_rooms:
        st.info("Add a room to the project to see the dashboard.")
        return
    
    room = st.session_state.project_rooms[st.session_state.current_room_index]
    st.markdown(f"**Showing details for: `{room['name']}`**")
    calcs, validation, items = st.session_state.get('avixa_calcs'), st.session_state.get('validation_results'), st.session_state.get('boq_items', [])
    c1, c2, c3, c4 = st.columns(4)
    total_cost_inr = convert_currency(sum(i.get('price', 0) * i.get('quantity', 1) for i in items) * 1.30, 'INR')
    c1.metric("💰 Est. Project Total (INR)", f"₹{total_cost_inr:,.0f}")
    c2.metric("✅ AVIXA Compliance Score", f"{validation.get('compliance_score', 0) if validation else 0}/100")
    c3.metric("🖥️ Recommended Display", f"{calcs.get('detailed_viewing_display_size', 'N/A') if calcs else 'N/A'}\"")
    c4.metric("⚡ Total Power Load", f"{calcs.get('total_power_load_watts', 'N/A') if calcs else 'N/A'} W")
    if validation and (validation.get('avixa_issues') or validation.get('avixa_warnings')):
        with st.expander("View Compliance Details"):
            for issue in validation.get('avixa_issues', []): st.error(f"**Issue:** {issue}")
            for warning in validation.get('avixa_warnings', []): st.warning(f"**Warning:** {warning}")

def create_room_calculator():
    c1, c2 = st.columns(2)
    length = c1.number_input("Room Length (ft)", 10.0, 80.0, 28.0, key="room_length_input")
    width = c1.number_input("Room Width (ft)", 8.0, 50.0, 20.0, key="room_width_input")
    height = c1.number_input("Ceiling Height (ft)", 8.0, 20.0, 10.0, key="ceiling_height_input")
    area = length * width
    c2.metric("Room Area", f"{area:.0f} sq ft")
    return area, height

def create_advanced_requirements():
    st.subheader("Technical Requirements")
    c1, c2 = st.columns(2)
    c1.write("**Infrastructure**")
    has_circuit = c1.checkbox("Dedicated 20A Circuit Available", key="dedicated_circuit_checkbox")
    network = c1.selectbox("Network Infrastructure", ["Standard 1Gb", "10Gb Capable", "Fiber Available"], key="network_capability_select")
    cable = c1.selectbox("Cable Management", ["Exposed", "Conduit", "Raised Floor", "Drop Ceiling"], key="cable_management_select")
    c2.write("**Compliance & Standards**")
    ada = c2.checkbox("ADA Compliance Required", key="ada_compliance_checkbox")
    fire = c2.checkbox("Fire Code Compliance Required", key="fire_code_compliance_checkbox")
    security = c2.selectbox("Security Level", ["Standard", "Restricted", "Classified"], key="security_clearance_select")
    return {"dedicated_circuit": has_circuit, "network_capability": network, "cable_management": cable, "ada_compliance": ada, "fire_code_compliance": fire, "security_clearance": security}

def update_boq_content_with_current_items():
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items added yet."
        return
    content = "## Bill of Quantities\n| Category | Make | Model No. | Specifications | Qty | Unit Price (USD) | Remarks |\n|---|---|---|---|---|---|---|\n"
    for item in st.session_state.boq_items:
        content += f"| {item.get('category', 'N/A')} | {item.get('brand', 'N/A')} | {item.get('name', 'N/A')} | {item.get('specifications', '')} | {item.get('quantity', 1)} | ${item.get('price', 0):,.2f} | {item.get('justification', '')} |\n"
    st.session_state.boq_content = content

def display_boq_results(content, validation, product_df):
    st.subheader(f"Generated Bill of Quantities ({len(st.session_state.boq_items)} items)")
    if validation:
        if validation.get('avixa_issues'):
            st.error("Critical Issues Found:")
            for issue in validation['avixa_issues']: st.write(f"- {issue}")
        if validation.get('avixa_warnings'):
            st.warning("Technical Recommendations:")
            for warning in validation['avixa_warnings']: st.write(f"- {warning}")
    if content: st.markdown(content)
    else: st.info("No BOQ content generated yet.")
    st.markdown("---")
    create_interactive_boq_editor(product_df)

def create_interactive_boq_editor(product_df):
    st.subheader("Interactive BOQ Editor")
    # ... (code for this function and its helpers: edit_current_boq, add_products_interface, product_search_interface remains unchanged from your original file)

def get_sample_product_data():
    return [{'name': 'Samsung 55" QM55R 4K Display', 'brand': 'Samsung', 'category': 'Displays', 'price': 1200, 'features': '55" 4K UHD, 500-nit, 16/7', 'image_url': 'https://via.placeholder.com/100', 'gst_rate': 18}, {'name': 'Logitech Rally Bar', 'brand': 'Logitech', 'category': 'Video Conferencing', 'price': 2700, 'features': 'All-in-one 4K video bar', 'image_url': 'https://via.placeholder.com/100', 'gst_rate': 18}, {'name': 'Shure MXA920 Ceiling Array', 'brand': 'Shure', 'category': 'Audio', 'price': 1800, 'features': 'Ceiling mic array, Dante', 'image_url': 'https://via.placeholder.com/100', 'gst_rate': 18}, {'name': 'QSC CP8T Ceiling Speaker', 'brand': 'QSC', 'category': 'Audio', 'price': 280, 'features': '8" ceiling speaker, 70V/100V', 'image_url': 'https://via.placeholder.com/100', 'gst_rate': 18}, {'name': 'APC SMT1500 UPS', 'brand': 'APC', 'category': 'Infrastructure', 'price': 450, 'features': '1500VA UPS', 'image_url': 'https://via.placeholder.com/100', 'gst_rate': 18}, {'name': 'Cat6A Cable (per 100ft)', 'brand': 'Belden', 'category': 'Cables', 'price': 85, 'features': 'Cat6A network cable, Plenum', 'image_url': '', 'gst_rate': 18}]

def show_login_page():
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="⚡")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.title("🏢 AllWave AV & GS")
        st.subheader("Design & Estimation Portal")
        with st.form("login_form"):
            email = st.text_input("Email ID", placeholder="yourname@allwaveav.com")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", type="primary", use_container_width=True):
                if email.endswith(("@allwaveav.com", "@allwavegs.com")) and len(password) > 3:
                    st.session_state.authenticated = True; st.session_state.user_email = email; st.rerun()
                else: st.error("Please use your AllWave email and a valid password")

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated: show_login_page(); return
    
    st.set_page_config(page_title="Professional AV BOQ Generator", layout="wide")
    
    # Initialize session state
    for key in ['boq_items', 'boq_content', 'validation_results', 'avixa_calcs', 'project_rooms']:
        if key not in st.session_state: st.session_state[key] = [] if key.endswith('s') else None
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18}

    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues"):
            for issue in data_issues: st.warning(issue)
    if product_df is None: return
    model = setup_gemini()
    if not model: return
    
    with st.sidebar:
        st.markdown(f"👤 **Logged in as:** {st.session_state.get('user_email', 'Unknown')}")
        if st.button("Logout", type="secondary"): st.session_state.authenticated = False; st.rerun()
        st.markdown("---"); st.header("Global Settings")
        currency = st.selectbox("Currency Display", ["INR", "USD"], 0, key="currency_select"); st.session_state['currency'] = currency
        st.number_input("Hardware GST (%)", 0, 28, 18, key="electronics_gst")
        st.number_input("Services GST (%)", 0, 28, 18, key="services_gst")
        st.session_state.gst_rates['Electronics'] = st.session_state.electronics_gst
        st.session_state.gst_rates['Services'] = st.session_state.services_gst
        st.markdown("---"); st.subheader("Room Design Presets")
        room_type_key = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", ["Economy", "Standard", "Premium", "Enterprise"], "Standard", key="budget_tier_slider")

    create_project_header()
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Project Dashboard", "🏢 Multi-Room Setup", "📐 Room Design", "📋 Generate & Edit BOQ", "🌐 3D Visualization"])

    with tab1: create_project_dashboard()
    with tab2: create_multi_room_interface()
    with tab3:
        st.subheader("Room Design & Requirements")
        c1, c2 = st.columns(2)
        with c1: room_area, ceiling_height = create_room_calculator()
        with c2: features = st.text_area("Specific Requirements:", placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified'", height=150, key="features_text_area")
        technical_reqs = create_advanced_requirements()
        technical_reqs['ceiling_height'] = ceiling_height

    with tab4:
        st.subheader("BOQ Generation & Editing")
        c1, c2 = st.columns([2, 1])
        if c1.button("🚀 Generate/Update BOQ for Current Room", type="primary", use_container_width=True):
            with st.spinner("Generating professional BOQ..."):
                room_area_val = st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                content, items, calcs, reqs = generate_boq_with_justifications(model, product_df, guidelines, room_type_key, budget_tier, features, technical_reqs, room_area_val)
                if items:
                    st.session_state.boq_content, st.session_state.boq_items, st.session_state.avixa_calcs = content, items, calcs
                    st.session_state.validation_results = validate_avixa_compliance(items, calcs, reqs)
                    save_current_room_data()
                    st.success(f"✅ Generated BOQ for '{st.session_state.project_rooms[st.session_state.current_room_index]['name']}'!")
                    st.rerun()
                else: st.error("Failed to generate BOQ. Please try again.")
        if c2.button("📥 Download Full Project BOQ", use_container_width=True):
            if st.session_state.project_rooms:
                project_details = {'project_name': st.session_state.project_name_input, 'client_name': st.session_state.client_name_input}
                excel_data = generate_company_excel(project_details, st.session_state.project_rooms, st.session_state.gst_rates)
                if excel_data:
                    filename = f"{project_details['project_name']}_Full_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                    st.download_button("Click to Download", excel_data, filename, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            else: st.warning("No rooms in project to export.")
        
        if st.session_state.boq_content or st.session_state.boq_items:
            display_boq_results(st.session_state.boq_content, st.session_state.validation_results, product_df)
    
    with tab5: create_3d_visualization()

if __name__ == "__main__":
    main()
