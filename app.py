import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import hashlib
import json
import time
from io import BytesIO
import base64

# --- Page Configuration ---
st.set_page_config(
    page_title="Professional AV BOQ Generator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enhanced Data Loading with Validation ---
@st.cache_data
def load_and_validate_data():
    """Loads and validates the product catalog and guidelines."""
    try:
        df = pd.read_csv("master_product_catalog.csv")
        
        # Data quality validation
        validation_issues = []
        
        # Check for missing critical data
        if df['name'].isnull().sum() > 0:
            validation_issues.append(f"{df['name'].isnull().sum()} products missing names")
        
        # Check for zero/missing prices
        zero_price_count = (df['price'] == 0.0).sum()
        if zero_price_count > 100:  # Allow some zero prices for accessories
            validation_issues.append(f"{zero_price_count} products have zero pricing")
            
        # Brand validation
        if df['brand'].isnull().sum() > 0:
            validation_issues.append(f"{df['brand'].isnull().sum()} products missing brand information")
        
        # Category validation - ensure we have essential categories
        categories = df['category'].value_counts()
        essential_categories = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts']
        missing_categories = [cat for cat in essential_categories if cat not in categories.index]
        if missing_categories:
            validation_issues.append(f"Missing essential categories: {missing_categories}")
        
        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found. Using basic industry standards."
            validation_issues.append("AVIXA guidelines file missing")
        
        return df, guidelines, validation_issues
        
    except FileNotFoundError:
        return None, None, ["Product catalog file not found"]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]

# --- Room Specifications Database ---
ROOM_SPECS = {
    "Huddle Room (2-4 People)": {
        "area_sqft": (50, 120),
        "recommended_display_size": (32, 55),
        "viewing_distance_ft": (4, 8),
        "audio_coverage": "Near-field",
        "camera_type": "Fixed wide-angle",
        "power_requirements": "Standard 15A circuit",
        "network_ports": 2,
        "typical_budget_range": (5000, 15000)
    },
    "Medium Conference Room (5-10 People)": {
        "area_sqft": (150, 300),
        "recommended_display_size": (55, 75),
        "viewing_distance_ft": (8, 14),
        "audio_coverage": "Room-wide with expansion mics",
        "camera_type": "PTZ or wide-angle with tracking",
        "power_requirements": "20A dedicated circuit recommended",
        "network_ports": 3,
        "typical_budget_range": (15000, 35000)
    },
    "Executive Boardroom": {
        "area_sqft": (300, 600),
        "recommended_display_size": (75, 98),
        "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling or table mics",
        "camera_type": "Multiple cameras with auto-switching",
        "power_requirements": "30A dedicated circuit",
        "network_ports": 4,
        "typical_budget_range": (35000, 80000)
    },
    "Training Room": {
        "area_sqft": (200, 500),
        "recommended_display_size": (65, 86),
        "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed with wireless mic support",
        "camera_type": "Fixed or PTZ for presenter tracking",
        "power_requirements": "20A circuit with UPS backup",
        "network_ports": 3,
        "typical_budget_range": (20000, 50000)
    }
}

# --- Enhanced Gemini Configuration with Retry Logic ---
def setup_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model
    except Exception as e:
        st.error(f"Gemini API configuration failed: {e}")
        return None

def generate_with_retry(model, prompt, max_retries=3):
    """Generate content with retry logic and error handling."""
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)  # Exponential backoff
    return None

# --- BOQ Validation Engine ---
class BOQValidator:
    def __init__(self, room_specs, product_df):
        self.room_specs = room_specs
        self.product_df = product_df
    
    def validate_technical_requirements(self, boq_items, room_type, room_area=None):
        """Validate technical requirements and compatibility."""
        issues = []
        warnings = []
        
        # Check display sizing against room specifications
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            room_spec = self.room_specs.get(room_type, {})
            recommended_size = room_spec.get('recommended_display_size', (32, 98))
            
            for display in displays:
                # Extract size from product name (rough heuristic)
                size_match = re.search(r'(\d+)"', display.get('name', ''))
                if size_match:
                    size = int(size_match.group(1))
                    if size < recommended_size[0]:
                        warnings.append(f"Display size {size}\" may be too small for {room_type}")
                    elif size > recommended_size[1]:
                        warnings.append(f"Display size {size}\" may be too large for {room_type}")
        
        # Check for essential components
        essential_categories = ['display', 'audio', 'control']
        found_categories = [item.get('category', '').lower() for item in boq_items]
        
        for essential in essential_categories:
            if not any(essential in cat for cat in found_categories):
                issues.append(f"Missing essential component: {essential}")
        
        # Power consumption estimation (simplified)
        total_estimated_power = len(boq_items) * 150  # Rough estimate
        room_spec = self.room_specs.get(room_type, {})
        if total_estimated_power > 1800:  # 15A circuit limit
            warnings.append("System may require dedicated 20A circuit")
        
        return issues, warnings

# --- Enhanced UI Components ---
def create_project_header():
    """Create professional project header."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("Professional AV BOQ Generator")
        st.caption("Production-ready Bill of Quantities with technical validation")
    
    with col2:
        project_id = st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}")
    
    with col3:
        quote_valid_days = st.number_input("Quote Valid (Days)", min_value=15, max_value=90, value=30)
    
    return project_id, quote_valid_days

def create_room_calculator():
    """Room size calculator and validator."""
    st.subheader("Room Analysis & Specifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        room_length = st.number_input("Room Length (ft)", min_value=8.0, max_value=50.0, value=16.0)
        room_width = st.number_input("Room Width (ft)", min_value=6.0, max_value=30.0, value=12.0)
        ceiling_height = st.number_input("Ceiling Height (ft)", min_value=8.0, max_value=20.0, value=9.0)
    
    with col2:
        room_area = room_length * room_width
        st.metric("Room Area", f"{room_area:.0f} sq ft")
        
        # Recommend room type based on area
        recommended_type = None
        for room_type, specs in ROOM_SPECS.items():
            if specs["area_sqft"][0] <= room_area <= specs["area_sqft"][1]:
                recommended_type = room_type
                break
        
        if recommended_type:
            st.success(f"Recommended: {recommended_type}")
        else:
            st.warning("Room size outside typical ranges")
    
    return room_area, ceiling_height

def create_advanced_requirements():
    """Advanced technical requirements input."""
    st.subheader("Technical Requirements")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Infrastructure**")
        has_dedicated_circuit = st.checkbox("Dedicated 20A Circuit Available")
        network_capability = st.selectbox("Network Infrastructure", 
                                        ["Standard 1Gb", "10Gb Capable", "Fiber Available"])
        cable_management = st.selectbox("Cable Management", 
                                      ["Exposed", "Conduit", "Raised Floor", "Drop Ceiling"])
    
    with col2:
        st.write("**Compliance & Standards**")
        ada_compliance = st.checkbox("ADA Compliance Required")
        fire_code_compliance = st.checkbox("Fire Code Compliance Required")
        security_clearance = st.selectbox("Security Level", 
                                        ["Standard", "Restricted", "Classified"])
    
    return {
        "dedicated_circuit": has_dedicated_circuit,
        "network_capability": network_capability,
        "cable_management": cable_management,
        "ada_compliance": ada_compliance,
        "fire_code_compliance": fire_code_compliance,
        "security_clearance": security_clearance
    }

# --- Professional BOQ Document Generator ---
def generate_professional_boq_document(boq_data, project_info, validation_results):
    """Generate a professional BOQ document with proper formatting."""
    
    # Create document header
    doc_content = f"""
# Professional Bill of Quantities
**Project:** {project_info['project_id']}  
**Date:** {datetime.now().strftime('%B %d, %Y')}  
**Valid Until:** {(datetime.now() + timedelta(days=project_info['quote_valid_days'])).strftime('%B %d, %Y')}

---

## System Design Summary
{boq_data.get('design_summary', 'Professional AV system designed to meet project requirements.')}

## Technical Validation
"""
    
    if validation_results['issues']:
        doc_content += "**⚠️ Critical Issues:**\n"
        for issue in validation_results['issues']:
            doc_content += f"- {issue}\n"
        doc_content += "\n"
    
    if validation_results['warnings']:
        doc_content += "**⚡ Technical Recommendations:**\n"
        for warning in validation_results['warnings']:
            doc_content += f"- {warning}\n"
        doc_content += "\n"
    
    doc_content += "---\n\n"
    
    return doc_content

# --- Main Application ---
def main():
    # Load and validate data
    product_df, guidelines, data_issues = load_and_validate_data()
    
    # Display data quality status
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=len(data_issues) > 3):
            for issue in data_issues:
                st.warning(issue)
    
    if product_df is None:
        st.error("Cannot load product catalog. Please check data files.")
        return
    
    # Setup Gemini
    model = setup_gemini()
    if not model:
        return
    
    # Create professional header
    project_id, quote_valid_days = create_project_header()
    
    # Sidebar for project settings
    with st.sidebar:
        st.header("Project Configuration")
        
        client_name = st.text_input("Client Name", value="")
        project_name = st.text_input("Project Name", value="")
        
        st.markdown("---")
        
        room_type = st.selectbox(
            "Primary Space Type:",
            list(ROOM_SPECS.keys())
        )
        
        budget_tier = st.select_slider(
            "Budget Tier:",
            options=["Economy", "Standard", "Premium", "Enterprise"],
            value="Standard"
        )
        
        # Display room specifications
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Typical area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display size: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
        st.caption(f"Budget range: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}")
    
    # Main content areas
    tab1, tab2, tab3 = st.tabs(["Room Analysis", "Requirements", "Generate BOQ"])
    
    with tab1:
        room_area, ceiling_height = create_room_calculator()
    
    with tab2:
        features = st.text_area(
            "Specific Requirements & Features:",
            placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified, recording capability'",
            height=100
        )
        
        technical_reqs = create_advanced_requirements()
    
    with tab3:
        st.subheader("BOQ Generation")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("Generate Professional BOQ", type="primary", use_container_width=True):
                generate_boq(model, product_df, guidelines, room_type, budget_tier, features, 
                           technical_reqs, room_area, project_id, quote_valid_days)
        
        with col2:
            st.markdown("**Product Stats:**")
            st.metric("Total Products", len(product_df))
            st.metric("Brands", product_df['brand'].nunique())
            if 'price' in product_df.columns:
                avg_price = product_df[product_df['price'] > 0]['price'].mean()
                st.metric("Avg Price", f"${avg_price:.0f}" if not pd.isna(avg_price) else "N/A")

def generate_boq(model, product_df, guidelines, room_type, budget_tier, features, 
                technical_reqs, room_area, project_id, quote_valid_days):
    """Enhanced BOQ generation with validation."""
    
    with st.spinner("Engineering professional BOQ with technical validation..."):
        
        # Create enhanced prompt
        prompt = create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, 
                                      features, technical_reqs, room_area)
        
        try:
            # Generate BOQ with retry logic
            response = generate_with_retry(model, prompt)
            
            if response:
                # Parse and validate response
                boq_content = response.text
                
                # Extract structured data (simplified)
                boq_items = extract_boq_items(boq_content)
                
                # Validate BOQ
                validator = BOQValidator(ROOM_SPECS, product_df)
                issues, warnings = validator.validate_technical_requirements(
                    boq_items, room_type, room_area
                )
                
                validation_results = {"issues": issues, "warnings": warnings}
                
                # Display results
                display_boq_results(boq_content, validation_results, project_id, quote_valid_days)
                
        except Exception as e:
            st.error(f"BOQ generation failed: {str(e)}")
            with st.expander("Technical Details"):
                st.code(str(e))

def create_enhanced_prompt(product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Create comprehensive prompt for BOQ generation."""
    
    room_spec = ROOM_SPECS[room_type]
    product_catalog_string = product_df.to_csv(index=False)
    
    prompt = f"""
You are a Professional AV Systems Engineer with 15+ years experience. Create a production-ready BOQ.

**PROJECT SPECIFICATIONS:**
- Room Type: {room_type}
- Room Area: {room_area:.0f} sq ft
- Budget Tier: {budget_tier}
- Special Requirements: {features}
- Infrastructure: {technical_reqs}

**TECHNICAL CONSTRAINTS:**
- Display size range: {room_spec['recommended_display_size'][0]}"-{room_spec['recommended_display_size'][1]}"
- Viewing distance: {room_spec['viewing_distance_ft'][0]}-{room_spec['viewing_distance_ft'][1]} ft
- Audio coverage: {room_spec['audio_coverage']}
- Power requirements: {room_spec['power_requirements']}
- Budget target: ${room_spec['typical_budget_range'][0]:,}-${room_spec['typical_budget_range'][1]:,}

**MANDATORY REQUIREMENTS:**
1. ONLY use products from the provided catalog
2. Verify all components are compatible
3. Include proper mounting and cabling
4. Add installation labor estimates
5. Ensure system meets AVIXA standards
6. Include 3-year warranty costs
7. Add 15% contingency for unforeseen issues

**PRODUCT CATALOG:**
{product_catalog_string}

**OUTPUT FORMAT:**
Provide a complete system design with:
1. Executive summary
2. Technical specifications compliance
3. Detailed BOQ table with labor
4. Risk assessment and recommendations

Generate the BOQ now:
"""
    
    return prompt

def extract_boq_items(boq_content):
    """Extract structured BOQ items from response (simplified)."""
    # This is a simplified extraction - in production you'd want more robust parsing
    items = []
    
    # Extract table content using regex
    table_pattern = r'\|.*?\|'
    matches = re.findall(table_pattern, boq_content, re.MULTILINE)
    
    for match in matches:
        if 'Category' not in match and 'TOTAL' not in match:
            parts = [part.strip() for part in match.split('|') if part.strip()]
            if len(parts) >= 3:
                items.append({
                    'category': parts[0] if len(parts) > 0 else '',
                    'name': parts[2] if len(parts) > 2 else '',
                    'brand': parts[1] if len(parts) > 1 else ''
                })
    
    return items

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days):
    """Display BOQ results with validation feedback."""
    
    st.subheader("Generated Bill of Quantities")
    
    # Show validation results first
    if validation_results['issues']:
        st.error("Critical Issues Found:")
        for issue in validation_results['issues']:
            st.write(f"- {issue}")
    
    if validation_results['warnings']:
        st.warning("Technical Recommendations:")
        for warning in validation_results['warnings']:
            st.write(f"- {warning}")
    
    # Display BOQ content
    st.markdown(boq_content)
    
    # Add download functionality
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Generate PDF-ready content
        pdf_content = generate_professional_boq_document(
            {'design_summary': boq_content}, 
            {'project_id': project_id, 'quote_valid_days': quote_valid_days},
            validation_results
        )
        
        st.download_button(
            label="Download BOQ (Markdown)",
            data=pdf_content,
            file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )
    
    with col2:
        # Generate CSV for further processing
        csv_data = "Category,Brand,Product,Quantity,Unit Price,Total\n"  # Simplified
        st.download_button(
            label="Download BOQ (CSV)",
            data=csv_data,
            file_name=f"{project_id}_BOQ_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col3:
        st.button("Generate Revised BOQ", help="Generate new BOQ with validation feedback")

if __name__ == "__main__":
    main()
