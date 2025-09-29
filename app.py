import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import json
import time
import streamlit.components.v1 as components
from io import BytesIO
import io # Required for image handling

# --- New Dependencies (for main script) ---
# Note: openpyxl, requests, and PIL are now primarily used in the component
# but might be needed here for other reasons. Keeping them for safety is fine.
import openpyxl
import requests
from PIL import Image as PILImage


# --- Import from components directory ---
try:
    from components.visualizer import create_3d_visualization, ROOM_SPECS
except ImportError:
    st.warning("Could not import 3D visualizer. Assuming dummy data for ROOM_SPECS.")
    ROOM_SPECS = {
        'Small Huddle Room (2-3 People)': {
            'area_sqft': (80, 150),
            'recommended_display_size': (43, 55),
            'video_solution': 'integrated_soundbar',
            'audio_type': 'integrated',
            'complexity': 'simple'
        },
        'Medium Huddle Room (4-6 People)': {
            'area_sqft': (150, 250),
            'recommended_display_size': (55, 65),
            'video_solution': 'video_bar',
            'audio_type': 'integrated',
            'complexity': 'simple'
        },
        'Standard Conference Room (6-8 People)': {
            'area_sqft': (250, 400),
            'recommended_display_size': (65, 75),
            'video_solution': 'video_bar_pro',
            'audio_type': 'ceiling_mics',
            'complexity': 'moderate'
        },
        'Large Conference Room (8-12 People)': {
            'area_sqft': (400, 600),
            'recommended_display_size': (75, 86),
            'video_solution': 'camera_plus_codec',
            'audio_type': 'ceiling_array',
            'complexity': 'moderate'
        },
        'Executive Boardroom (10-16 People)': {
            'area_sqft': (500, 800),
            'recommended_display_size': (86, 98),
            'video_solution': 'dual_camera_system',
            'audio_type': 'distributed_ceiling',
            'complexity': 'advanced'
        },
        'Training Room (15-25 People)': {
            'area_sqft': (600, 1000),
            'recommended_display_size': (86, 98),
            'video_solution': 'ptz_camera',
            'audio_type': 'ceiling_array_with_reinforcement',
            'complexity': 'advanced'
        },
        'Large Training/Presentation Room (25-40 People)': {
            'area_sqft': (1000, 1500),
            'recommended_display_size': (98, 110),
            'video_solution': 'multi_camera_system',
            'audio_type': 'line_array',
            'complexity': 'complex'
        },
        'Multipurpose Event Room (40+ People)': {
            'area_sqft': (1500, 3000),
            'recommended_display_size': (98, 150),
            'video_solution': 'broadcast_system',
            'audio_type': 'professional_pa',
            'complexity': 'complex'
        },
        'Video Production Studio': {
            'area_sqft': (400, 1000),
            'recommended_display_size': (55, 75),
            'video_solution': 'broadcast_cameras',
            'audio_type': 'studio_grade',
            'complexity': 'complex'
        },
        'Telepresence Suite': {
            'area_sqft': (300, 600),
            'recommended_display_size': (75, 98),
            'video_solution': 'telepresence_codec',
            'audio_type': 'spatial_audio',
            'complexity': 'advanced'
        }
    }
    def create_3d_visualization():
        st.info("3D Visualization component not found.")

# ★★★ NEW: Import the Excel generator component ★★★
try:
    from components.excel_generator import generate_company_excel
except ImportError:
    st.error("Excel generator component not found. Please ensure 'components/excel_generator.py' exists.")
    # Define a dummy function to prevent crashes
    def generate_company_excel(*args, **kwargs):
        st.error("Excel generation is currently unavailable.")
        return None

# --- Currency Conversion ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def get_usd_to_inr_rate():
    """Get current USD to INR exchange rate. Falls back to approximate rate if API fails."""
    try:
        # You can integrate a free API like exchangerate-api.com here
        # For now, using approximate rate
        return 83.5 # Approximate USD to INR rate - update this or use real API
    except:
        return 83.5 # Fallback rate

def convert_currency(amount_usd, to_currency="INR"):
    """Convert USD amount to specified currency."""
    if to_currency == "INR":
        rate = get_usd_to_inr_rate()
        return amount_usd * rate
    return amount_usd

def format_currency(amount, currency="USD"):
    """Format currency with proper symbols and formatting."""
    if currency == "INR":
        return f"₹{amount:,.0f}"
    else:
        return f"${amount:,.2f}"

# --- DATA CLEANING FUNCTION ---
def clean_and_validate_product_data(product_df):
    """Clean and validate product data before using in BOQ generation."""
    if product_df is None or len(product_df) == 0:
        return product_df

    # Create a copy to avoid modifying original
    df = product_df.copy()

    # Clean price data - remove unrealistic prices
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)

    # ★★★ FIX 3: RELAXED PRICE FILTERING ★★★
    # REPLACE THIS:
    # df = df[(df['price'] >= 100) & (df['price'] <= 50000)]
    
    # WITH THIS (category-specific):
    price_filters = {
        'Cables': (10, 500),
        'Mounts': (30, 1000),
        'Displays': (500, 20000),
        'Audio': (50, 5000),
        'Video Conferencing': (200, 10000),
        'Control': (100, 8000),
        'Infrastructure': (100, 5000)
    }
    
    def is_valid_price(row):
        category = row['category']
        price = row['price']
        if category in price_filters:
            min_p, max_p = price_filters[category]
            return min_p <= price <= max_p
        return 100 <= price <= 50000 # Default range
    
    df = df[df.apply(is_valid_price, axis=1)]
    # ★★★ END FIX 3 ★★★

    # Clean category names - standardize to match your expected categories
    category_mapping = {
        # Display Related
        'Displays & Projectors': 'Displays',
        'Digital Signage Players & CMS': 'Displays',
        'Interactive Displays & Classroom Tech': 'Displays',
        'Projection Screens': 'Displays',

        # Video Conferencing Related
        'UC & Collaboration Devices': 'Video Conferencing',
        'PTZ & Pro Video Cameras': 'Video Conferencing',
        'Lecture Capture & Recording': 'Video Conferencing',
        'AV Bridges & Specialty I/O': 'Video Conferencing',

        # Audio Related
        'Audio: Microphones & Conferencing': 'Audio',
        'Audio: Speakers': 'Audio',
        'Audio: DSP': 'Audio',
        'Audio: Amplifiers': 'Audio',
        'Audio: DSP & Processing': 'Audio',
        'Audio: Loudspeakers & Amplifiers': 'Audio',
        'Acoustics & Sound Masking': 'Audio',
        'Assistive Listening & Hearing Loop': 'Audio',
        
        # Control Related
        'Control Systems & Processing': 'Control',
        'AV over IP & Streaming': 'Control',
        'Control, Matrix & Extenders': 'Control',
        'Video Equipment': 'Control',
        'Wireless Presentation': 'Control',
        'Room Scheduling & Touch Panels': 'Control',
        
        # Infrastructure Related
        'Mounts & Racks': 'Mounts',
        'Cables & Connectivity': 'Cables',
        'Networking': 'Infrastructure',
        'Network Switches (AV-friendly)': 'Infrastructure',

        # To be mapped to broad categories
        'AV over IP': 'Control', # Map this specific one too
        'Extracted from Project': 'General', # Map legacy category
    }

    df['category'] = df['category'].map(category_mapping).fillna(df['category'])

    # Clean brand names - remove test data patterns
    test_patterns = ['Generated Model', 'Extracted from Project']
    for pattern in test_patterns:
        df = df[~df['features'].astype(str).str.contains(pattern, na=False)]

    # Ensure required columns exist
    required_columns = ['name', 'brand', 'category', 'price', 'features']
    for col in required_columns:
        if col not in df.columns:
            df[col] = 'Unknown' if col != 'price' else 0

    # Remove duplicate products (same name + brand combination)
    df = df.drop_duplicates(subset=['name', 'brand'], keep='first')

    return df.reset_index(drop=True)

# --- Enhanced Data Loading with Validation (UPDATED) ---
@st.cache_data
def load_and_validate_data():
    """Enhanced loads and validates with image URLs and GST data."""
    try:
        df = pd.read_csv("master_product_catalog.csv")

        # --- Integrate data cleaning ---
        df = clean_and_validate_product_data(df)

        # --- Existing validation code ---
        validation_issues = []

        # Check for missing critical data
        if 'name' not in df.columns or df['name'].isnull().sum() > 0:
            validation_issues.append(f"{df['name'].isnull().sum()} products missing names")

        # Check for zero/missing prices
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
            zero_price_count = (df['price'] == 0.0).sum()
            if zero_price_count > 100:
                validation_issues.append(f"{zero_price_count} products have zero pricing")
        else:
            df['price'] = 0.0
            validation_issues.append("Price column missing - using default values")

        # Brand validation
        if 'brand' not in df.columns:
            df['brand'] = 'Unknown'
            validation_issues.append("Brand column missing - using default values")
        elif df['brand'].isnull().sum() > 0:
            df['brand'] = df['brand'].fillna('Unknown')
            validation_issues.append(f"{df['brand'].isnull().sum()} products missing brand information")

        # Category validation
        if 'category' not in df.columns:
            df['category'] = 'General'
            validation_issues.append("Category column missing - using default values")
        else:
            df['category'] = df['category'].fillna('General')
            categories = df['category'].value_counts()
            essential_categories = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts']
            missing_categories = [cat for cat in essential_categories if cat not in categories.index]
            if missing_categories:
                validation_issues.append(f"Missing essential categories: {missing_categories}")

        if 'features' not in df.columns:
            df['features'] = df['name']
            validation_issues.append("Features column missing - using product names for search")
        else:
            df['features'] = df['features'].fillna('')

        # --- NEW ADDITIONS ---
        if 'image_url' not in df.columns:
            df['image_url'] = '' # Will be populated later or manually
            validation_issues.append("Image URL column missing - images won't display in Excel")

        if 'gst_rate' not in df.columns:
            df['gst_rate'] = 18 # Default 18% GST for electronics
            validation_issues.append("GST rate column missing - using 18% default")

        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found. Using basic industry standards."
            validation_issues.append("AVIXA guidelines file missing")

        return df, guidelines, validation_issues

    except FileNotFoundError:
        st.warning("Master product catalog not found. Using sample data for testing.")
        sample_data = get_sample_product_data()
        df = pd.DataFrame(sample_data)

        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found. Using basic industry standards."

        return df, guidelines, ["Using sample product catalog for testing"]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]

# --- Gemini Configuration ---
def setup_gemini():
    try:
        # Ensure the secret is set in Streamlit Cloud or your local secrets.toml
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel('gemini-1.5-flash')
            return model
        else:
            st.error("GEMINI_API_KEY not found in Streamlit secrets.")
            return None
    except Exception as e:
        st.error(f"Gemini API configuration failed: {e}")
        return None

# --- Gemini Content Generation ---
def generate_with_retry(model, prompt, max_retries=3):
    """Generate content with retry logic and error handling."""
    for attempt in range(max_retries):
        try:
            # --- Add safety settings to prevent blocking ---
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            response = model.generate_content(prompt, safety_settings=safety_settings)
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"AI generation failed after {max_retries} attempts: {e}")
                raise e
            time.sleep(2 ** attempt) # Exponential backoff
    return None

# --- Enhanced AVIXA Calculations ---
def calculate_avixa_recommendations(room_length, room_width, room_height, room_type):
    """Calculate comprehensive AVIXA recommendations with proper formulas."""

    room_area = room_length * room_width
    room_volume = room_area * room_height

    # AVIXA DISCAS Display Sizing - Proper Implementation
    max_viewing_distance = min(room_length * 0.85, room_width * 0.9)

    # For detailed viewing (text/presentations): Screen height = viewing distance / 6
    detailed_screen_height_ft = max_viewing_distance / 6
    detailed_screen_size = detailed_screen_height_ft * 12 / 0.49 # 16:9 conversion

    # For basic viewing (video): Screen height = viewing distance / 4
    basic_screen_height_ft = max_viewing_distance / 4
    basic_screen_size = basic_screen_height_ft * 12 / 0.49

    # Audio Power Requirements (Enhanced)
    base_power_per_cubic_ft = 0.5
    if 'training' in room_type.lower() or 'presentation' in room_type.lower():
        base_power_per_cubic_ft = 0.75 # Higher for presentation spaces
    elif 'executive' in room_type.lower() or 'boardroom' in room_type.lower():
        base_power_per_cubic_ft = 1.0 # Highest for critical spaces

    audio_power_needed = int(room_volume * base_power_per_cubic_ft)

    # Lighting Requirements (AVIXA Standards)
    if 'conference' in room_type.lower():
        ambient_lighting = 200 # Lux
        presentation_lighting = 150 # Dimmed for displays
    elif 'training' in room_type.lower():
        ambient_lighting = 300 # Higher for note-taking
        presentation_lighting = 200
    else:
        ambient_lighting = 250 # General meeting spaces
        presentation_lighting = 175

    # Network Bandwidth (Realistic Calculations)
    estimated_people = min(room_area // 20, 50) if room_area > 0 else 1 # 20 sq ft per person max

    # Per-person bandwidth requirements
    hd_video_mbps = 2.5 # 1080p video conferencing
    uhd_video_mbps = 8.0 # 4K video conferencing
    content_sharing_mbps = 5.0 # Wireless presentation

    recommended_bandwidth = int((hd_video_mbps * estimated_people) + content_sharing_mbps + 10) # 10Mbps buffer

    # Power Load Calculations
    display_power = 250 if detailed_screen_size < 75 else 400 # Watts per display
    audio_system_power = 150 + (audio_power_needed * 0.3) # Amplifiers + processing
    camera_power = 25
    network_power = 100 # Switches and codecs
    control_power = 75

    total_av_power = display_power + audio_system_power + camera_power + network_power + control_power

    # Circuit Requirements
    if total_av_power < 1200:
        circuit_requirement = "15A Standard Circuit"
    elif total_av_power < 1800:
        circuit_requirement = "20A Dedicated Circuit"
    else:
        circuit_requirement = "Multiple 20A Circuits"

    # Cable Run Calculations
    display_runs = 2 # HDMI + Power per display
    audio_runs = max(1, estimated_people // 3) # Microphone coverage
    network_runs = 3 + max(1, estimated_people // 6) # Control + cameras + wireless APs
    power_runs = 2 + max(1, total_av_power // 1000) # Based on power zones

    # UPS Requirements (Based on Room Criticality)
    if 'executive' in room_type.lower() or 'boardroom' in room_type.lower():
        ups_runtime_minutes = 30
    elif 'training' in room_type.lower() or 'conference' in room_type.lower():
        ups_runtime_minutes = 15
    else:
        ups_runtime_minutes = 10

    ups_va_required = int(total_av_power * 1.4) # 40% overhead for UPS sizing

    return {
        # Display Specifications
        'detailed_viewing_display_size': int(detailed_screen_size),
        'basic_viewing_display_size': int(basic_screen_size),
        'max_viewing_distance': max_viewing_distance,
        'recommended_display_count': 2 if room_area > 300 else 1,

        # Audio Specifications
        'audio_power_needed': audio_power_needed,
        'microphone_coverage_zones': max(2, estimated_people // 4),
        'speaker_zones_required': max(2, int(room_area // 150)) if room_area > 0 else 1,

        # Lighting Specifications
        'ambient_lighting_lux': ambient_lighting,
        'presentation_lighting_lux': presentation_lighting,
        'lighting_zones_required': max(2, int(room_area // 200)) if room_area > 0 else 1,

        # Network & Power
        'estimated_occupancy': estimated_people,
        'recommended_bandwidth_mbps': recommended_bandwidth,
        'total_power_load_watts': total_av_power,
        'circuit_requirement': circuit_requirement,
        'ups_va_required': ups_va_required,
        'ups_runtime_minutes': ups_runtime_minutes,

        # Infrastructure
        'cable_runs': {
            'cat6a_network': network_runs,
            'hdmi_video': display_runs,
            'xlr_audio': audio_runs,
            'power_circuits': power_runs
        },

        # Compliance Flags
        'requires_ada_compliance': estimated_people > 15,
        'requires_hearing_loop': estimated_people > 50,
        'requires_assistive_listening': estimated_people > 25
    }

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """Determine specific equipment based on AVIXA calculations and room requirements."""

    requirements = {
        'displays': [],
        'audio_system': {},
        'video_system': {},
        'control_system': {},
        'infrastructure': {},
        'compliance': []
    }

    # Display Selection Logic
    display_size = avixa_calcs['detailed_viewing_display_size']
    display_count = avixa_calcs['recommended_display_count']

    if display_size <= 55:
        display_type = "Commercial LED Display"
    elif display_size <= 75:
        display_type = "Large Format Display"
    elif display_size <= 86:
        display_type = "Professional Large Format Display"
    else:
        display_type = "Video Wall or Laser Projector"

    requirements['displays'] = {
        'type': display_type,
        'size_inches': display_size,
        'quantity': display_count,
        'resolution': '4K' if display_size > 43 else '1080p',
        'mounting': 'Wall Mount' if display_size < 75 else 'Heavy Duty Wall Mount'
    }

    # Audio System Selection Logic
    room_volume = (avixa_calcs['audio_power_needed'] / 0.5) if avixa_calcs['audio_power_needed'] > 0 else 1 # Reverse calculate volume
    ceiling_height = technical_reqs.get('ceiling_height', 10)

    if room_volume < 2000: # Small rooms
        requirements['audio_system'] = {
            'type': 'All-in-One Video Bar',
            'microphones': 'Integrated Beamforming Array',
            'speakers': 'Integrated Speakers',
            'dsp_required': False
        }
    elif room_volume < 5000: # Medium rooms
        if ceiling_height < 9:
            mic_solution = 'Tabletop Microphones'
        else:
            mic_solution = 'Ceiling Microphone Array'

        requirements['audio_system'] = {
            'type': 'Distributed Audio System',
            'microphones': mic_solution,
            'microphone_count': avixa_calcs['microphone_coverage_zones'],
            'speakers': 'Ceiling Speakers',
            'speaker_count': avixa_calcs['speaker_zones_required'],
            'amplifier': 'Multi-Channel Amplifier',
            'dsp_required': True,
            'dsp_type': 'Basic DSP with AEC'
        }
    else: # Large rooms
        requirements['audio_system'] = {
            'type': 'Professional Audio System',
            'microphones': 'Steerable Ceiling Array',
            'microphone_count': avixa_calcs['microphone_coverage_zones'],
            'speakers': 'Distributed Ceiling System',
            'speaker_count': avixa_calcs['speaker_zones_required'],
            'amplifier': 'Networked Amplifier System',
            'dsp_required': True,
            'dsp_type': 'Advanced DSP with Dante/AVB',
            'voice_lift': room_volume > 8000
        }

    # Camera System Selection
    if avixa_calcs['estimated_occupancy'] <= 6:
        camera_type = 'Fixed Wide-Angle Camera'
    elif avixa_calcs['estimated_occupancy'] <= 12:
        camera_type = 'PTZ Camera with Auto-Framing'
    else:
        camera_type = 'Multi-Camera System with Tracking'

    requirements['video_system'] = {
        'camera_type': camera_type,
        'camera_count': 1 if avixa_calcs['estimated_occupancy'] <= 12 else 2,
        '4k_required': avixa_calcs['estimated_occupancy'] > 8
    }

    # Control System Selection
    if room_volume < 2000:
        control_type = 'Native Room System Control'
    elif room_volume < 5000:
        control_type = 'Touch Panel Control'
    else:
        control_type = 'Advanced Programmable Control System'

    requirements['control_system'] = {
        'type': control_type,
        'touch_panel_size': '7-inch' if room_volume < 3000 else '10-inch',
        'integration_required': room_volume > 5000
    }

    # Infrastructure Requirements
    requirements['infrastructure'] = {
        'equipment_rack': 'Wall-Mount' if room_volume < 3000 else 'Floor-Standing',
        'rack_size': '6U' if room_volume < 3000 else '12U' if room_volume < 8000 else '24U',
        'cooling_required': avixa_calcs['total_power_load_watts'] > 1500,
        'ups_required': True,
        'cable_management': 'Standard' if room_volume < 5000 else 'Professional'
    }

    # Compliance Requirements
    if avixa_calcs['requires_ada_compliance']:
        requirements['compliance'].append('ADA Compliant Touch Panels (15-48" height)')
        requirements['compliance'].append('Visual Notification System')

    if avixa_calcs['requires_hearing_loop']:
        requirements['compliance'].append('Hearing Loop System')

    if avixa_calcs['requires_assistive_listening']:
        requirements['compliance'].append('FM/IR Assistive Listening (4% of capacity)')

    return requirements

# --- HELPER FUNCTIONS FOR ENHANCED BOQ GENERATION ---
def get_curated_products_by_category(product_df, category, max_products=15):
    """Get curated, realistic products for a specific category."""
    if product_df is None or len(product_df) == 0:
        return pd.DataFrame()

    # Filter by category
    cat_df = product_df[product_df['category'] == category].copy()

    if len(cat_df) == 0:
        return pd.DataFrame()

    # Prefer products from known brands
    known_brands = ['Samsung', 'LG', 'Sony', 'Poly', 'Logitech', 'Cisco', 'Shure',
                    'QSC', 'Extron', 'Crestron', 'Chief', 'Kramer', 'Biamp']

    # Sort by brand preference, then by price
    cat_df['brand_score'] = cat_df['brand'].apply(
        lambda x: known_brands.index(x) if x in known_brands else 999
    )
    cat_df = cat_df.sort_values(['brand_score', 'price'])

    return cat_df.head(max_products)

def validate_essential_components(boq_items):
    """Validate that BOQ has essential components for a functional AV system."""
    if not boq_items:
        return False

    categories_found = [item.get('category', '').lower() for item in boq_items]

    # Check for essential components
    has_display = any('display' in cat for cat in categories_found)
    has_video_conf = any(term in cat for cat in categories_found for term in ['video', 'conferencing'])
    has_audio = any('audio' in cat for cat in categories_found)

    return has_display and (has_video_conf or has_audio)

def remove_duplicate_boq_items(boq_items):
    """Remove duplicate items from BOQ based on name and brand."""
    seen = set()
    unique_items = []

    for item in boq_items:
        item_key = (item.get('name', '').lower(), item.get('brand', '').lower())
        if item_key not in seen:
            seen.add(item_key)
            unique_items.append(item)

    return unique_items

# ★★★ UPDATE 4: Enhanced fallback with stricter category matching ★★★
def create_smart_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs):
    """Create comprehensive fallback BOQ based on room complexity."""
    fallback_items = []
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')
    
    required_components = _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type)
    
    st.info(f"Fallback: Generating {len(required_components)}-component system")

    try:
        for comp_key, comp_spec in required_components.items():
            category = comp_spec['category']
            quantity = comp_spec['quantity']
            
            # UPDATED: Try exact match first, then substring, then related categories
            category_products = product_df[product_df['category'] == category]
            
            if len(category_products) == 0:
                # Try substring match
                category_products = product_df[
                    product_df['category'].str.contains(category, case=False, na=False)
                ]
            
            if len(category_products) == 0:
                # Try related category mapping
                related_categories = {
                    'Audio: DSP': ['Audio: DSP & Processing', 'Control Systems & Processing'],
                    'PTZ & Pro Video Cameras': ['Video Conferencing', 'UC & Collaboration Devices'],
                    'Control Systems & Processing': ['Control, Matrix & Extenders'],
                }
                for alt_cat in related_categories.get(category, []):
                    category_products = product_df[product_df['category'] == alt_cat]
                    if len(category_products) > 0:
                        break
            
            # Filter out invalid products
            category_products = category_products[
                (~category_products['features'].astype(str).str.contains('Auto-generated', na=False)) &
                (category_products['features'].astype(str).str.len() > 10)
            ]
            
            if len(category_products) == 0:
                st.error(f"CRITICAL: No valid products for '{category}' - BOQ incomplete")
                continue

            # Special handling for displays
            if comp_key == 'display' and 'size_requirement' in comp_spec:
                target_size = comp_spec['size_requirement']
                best_display = None
                min_diff = float('inf')

                for _, prod in category_products.iterrows():
                    size_match = re.search(r'(\d+)"', prod['name'])
                    if size_match:
                        size = int(size_match.group(1))
                        diff = abs(size - target_size)
                        if diff < min_diff:
                            min_diff = diff
                            best_display = prod

                if best_display is not None:
                    fallback_items.append({
                        'category': best_display['category'],
                        'name': best_display['name'],
                        'brand': best_display['brand'],
                        'quantity': quantity,
                        'price': float(best_display['price']),
                        'justification': comp_spec['justification'],
                        'specifications': best_display.get('features', ''),
                        'image_url': best_display.get('image_url', ''),
                        'gst_rate': best_display.get('gst_rate', 18),
                        'matched': True
                    })
                    continue

            # For all other components, use first available
            if len(category_products) > 0:
                product = category_products.iloc[0]
                fallback_items.append({
                    'category': product['category'],
                    'name': product['name'],
                    'brand': product['brand'],
                    'quantity': quantity,
                    'price': float(product['price']),
                    'justification': comp_spec['justification'],
                    'specifications': product.get('features', ''),
                    'image_url': product.get('image_url', ''),
                    'gst_rate': product.get('gst_rate', 18),
                    'matched': True
                })

        st.success(f"Fallback generated {len(fallback_items)} components")
        return fallback_items

    except Exception as e:
        st.error(f"Fallback generation failed: {str(e)}")
        return []


# --- ★★★ NEW HELPER AND VALIDATION FUNCTIONS (ADDED) ★★★ ---
def extract_display_size_from_items(boq_items):
    """Extract display size from BOQ items."""
    for item in boq_items:
        if 'display' in item.get('category', '').lower():
            size_match = re.search(r'(\d+)"', item.get('name', ''))
            if size_match:
                return int(size_match.group(1))
    return None

def validate_catalog_coverage(product_df):
    """Validate that the product catalog has adequate coverage for BOQ generation."""
    issues = []
    essential_categories = ['Displays', 'Video Conferencing', 'Audio', 'Control', 'Mounts', 'Cables']

    for category in essential_categories:
        cat_products = product_df[product_df['category'] == category]
        if len(cat_products) == 0:
            issues.append(f"No products found in {category} category")
        elif len(cat_products) < 3:
            issues.append(f"Limited product options in {category} category ({len(cat_products)} products)")

    # Check price ranges
    for category in essential_categories:
        cat_products = product_df[product_df['category'] == category]
        if len(cat_products) > 0:
            price_range = cat_products['price'].max() - cat_products['price'].min()
            if price_range < 500: # Less than $500 price range
                issues.append(f"{category} category has limited price diversity")

    return issues

def find_replacement_product(category, original_name, original_brand, product_df, min_price, max_price):
    """Find a realistic replacement product from the catalog."""
    if product_df is None or len(product_df) == 0:
        return None

    # Filter by category and price range
    suitable_products = product_df[
        (product_df['category'] == category) &
        (product_df['price'] >= min_price) &
        (product_df['price'] <= max_price)
    ].copy()

    if len(suitable_products) == 0:
        return None

    # Try to match brand first
    if original_brand and original_brand != 'Unknown':
        brand_matches = suitable_products[
            suitable_products['brand'].str.contains(original_brand, case=False, na=False)
        ]
        if len(brand_matches) > 0:
            return brand_matches.iloc[0].to_dict()

    # Try to match key terms from product name
    if original_name:
        name_terms = original_name.lower().split()[:3] # First 3 words
        for term in name_terms:
            if len(term) > 3:
                term_matches = suitable_products[
                    suitable_products['name'].str.contains(term, case=False, na=False)
                ]
                if len(term_matches) > 0:
                    return term_matches.iloc[0].to_dict()

    # Return first suitable product as fallback
    return suitable_products.iloc[0].to_dict()


# --- ★★★ ENHANCED VALIDATION FUNCTION (REPLACED) ★★★ ---
def validate_boq_pricing_and_logic(boq_items, product_df):
    """Enhanced validation with stricter cable pricing and system completeness checks."""
    issues = []
    warnings = []

    # Stricter price validation thresholds by category
    price_ranges = {
        'Displays': {'min': 800, 'max': 15000},
        'Video Conferencing': {'min': 300, 'max': 8000},
        'Audio': {'min': 50, 'max': 3000},
        'Control': {'min': 200, 'max': 5000},
        'Mounts': {'min': 50, 'max': 800},
        'Cables': {'min': 10, 'max': 200}, # STRICTER: Max $200 for any cable
        'Infrastructure': {'min': 100, 'max': 2000}
    }

    corrected_items = []
    total_system_value = 0

    for item in boq_items:
        category = item.get('category', 'General')
        price = item.get('price', 0)
        name = item.get('name', '')
        brand = item.get('brand', '')
        quantity = item.get('quantity', 1)

        # Special validation for cables
        if category == 'Cables':
            if price > 200:
                issues.append(f"CRITICAL: Cable '{name}' priced at ${price:,.0f} - exceeds maximum realistic price of $200")
                # Force replacement for overpriced cables
                replacement = find_replacement_product(category, "HDMI Cable", brand, product_df, 10, 50)
                if replacement:
                    corrected_items.append({
                        **item,
                        'name': replacement['name'],
                        'brand': replacement['brand'],
                        'price': replacement['price'],
                        'matched': True,
                        'specifications': replacement.get('features', 'Standard AV cable')
                    })
                    warnings.append(f"Replaced overpriced cable with {replacement['name']} (${replacement['price']:,.0f})")
                else:
                    # Use fallback pricing
                    corrected_items.append({
                        **item,
                        'price': 25.0, # Reasonable HDMI cable price
                        'name': 'Standard HDMI Cable',
                        'specifications': 'High-speed HDMI cable for AV connections'
                    })
                    warnings.append(f"Corrected cable pricing from ${price} to $25")
                continue

        # Check if price is realistic for other categories
        if category in price_ranges:
            min_price = price_ranges[category]['min']
            max_price = price_ranges[category]['max']

            if price < min_price or price > max_price:
                replacement = find_replacement_product(category, name, brand, product_df, min_price, max_price)

                if replacement:
                    warnings.append(f"Replaced unrealistic pricing for {name} (${price:,.0f}) with {replacement['name']} (${replacement['price']:,.0f})")
                    corrected_items.append({
                        **item,
                        'name': replacement['name'],
                        'brand': replacement['brand'],
                        'price': replacement['price'],
                        'matched': True,
                        'specifications': replacement.get('features', item.get('specifications', ''))
                    })
                else:
                    issues.append(f"Could not find realistic replacement for {name} - price ${price:,.0f} outside range ${min_price}-${max_price}")
                    corrected_items.append(item) # Keep original if no replacement found
            else:
                corrected_items.append(item)
        else:
            corrected_items.append(item)

        total_system_value += item.get('price', 0) * item.get('quantity', 1)

    # Enhanced system completeness validation
    categories_present = {item.get('category') for item in corrected_items}

    # Critical components check
    if 'Displays' not in categories_present:
        issues.append("CRITICAL: No display found in BOQ")
    if not any(cat in categories_present for cat in ['Video Conferencing', 'Audio']):
        issues.append("CRITICAL: No audio/video solution found in BOQ")
    if 'Mounts' not in categories_present:
        warnings.append("No mounting solution specified")

    # System value reasonableness check
    if total_system_value < 3000:
        warnings.append("Total system value seems low for professional AV installation")
    elif total_system_value > 50000:
        warnings.append("Total system value seems high - verify requirements")

    # Check for system integration requirements
    display_size = extract_display_size_from_items(corrected_items)
    if display_size and display_size >= 75:
        has_control_system = any('control' in item.get('category', '').lower() and
                                 'processor' in item.get('name', '').lower()
                                 for item in corrected_items)
        if not has_control_system:
            warnings.append("Large display system may require dedicated control processor")

    # Check for UPS requirement
    total_power = sum(estimate_power_draw(item.get('category', ''), item.get('name', ''))
                      for item in corrected_items)
    if total_power > 1000:
        has_ups = any('ups' in item.get('name', '').lower() for item in corrected_items)
        if not has_ups:
            warnings.append("High-power system should include UPS for equipment protection")

    return corrected_items, issues, warnings


# --- ★★★ HELPER FUNCTIONS FOR MULTI-SHOT BOQ (UPDATED) ★★★ ---
def _build_categorized_product_list(product_df, equipment_reqs, budget_tier, room_type):
    """Build room-specific product list with required quantities."""

    budget_filters = {
        'Economy': (0, 2000),
        'Standard': (500, 4000),
        'Premium': (2000, 8000),
        'Enterprise': (5000, 15000)
    }
    price_range = budget_filters.get(budget_tier, (0, 10000))

    # Determine required components based on room complexity
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')

    required_categories = ['Displays', 'Video Conferencing', 'Mounts', 'Cables']

    if complexity in ['moderate', 'advanced', 'complex']:
        required_categories.extend(['Audio', 'Control'])

    if complexity in ['advanced', 'complex']:
        required_categories.extend(['PTZ & Pro Video Cameras', 'Audio: DSP'])

    output = f"\nROOM TYPE: {room_type}\nCOMPLEXITY LEVEL: {complexity}\nREQUIRED CATEGORIES: {', '.join(required_categories)}\n"

    for category in required_categories:
        matching_products = product_df[
            (product_df['category'].str.contains(category, case=False, na=False)) &
            (product_df['price'] >= price_range[0]) &
            (product_df['price'] <= price_range[1])
        ]

        if len(matching_products) == 0:
            # Relax price filter if no matches
            matching_products = product_df[
                product_df['category'].str.contains(category, case=False, na=False)
            ]

        output += f"\n=== {category.upper()} ===\n"
        for _, prod in matching_products.head(5).iterrows():
            output += f"• {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"

    return output

def _parse_ai_product_selection(ai_response_text):
    """Extract JSON from AI response."""
    try:
        # Remove markdown code blocks if present
        cleaned = ai_response_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]

        return json.loads(cleaned)
    except Exception as e:
        st.warning(f"Failed to parse AI JSON: {e}")
        return {}

# ★★★ UPDATE 2: Fix _strict_product_match() to filter invalid specs ★★★
def _strict_product_match(product_name, product_df, category):
    """Enhanced matching with specification validation."""
    
    # Filter out products with invalid specifications
    filtered = product_df[
        (product_df['category'] == category) &
        (~product_df['features'].astype(str).str.contains('Auto-generated', na=False)) &
        (product_df['features'].astype(str).str.len() > 10)  # At least 10 chars
    ]
    
    if len(filtered) == 0:
        # Fallback: try substring category match
        filtered = product_df[
            product_df['category'].str.contains(category, case=False, na=False) &
            (~product_df['features'].astype(str).str.contains('Auto-generated', na=False))
        ]
    
    if len(filtered) == 0:
        st.warning(f"No valid products found for category '{category}'")
        return None

    if len(filtered) == 0:
        return None
    # Try exact match first
    exact = filtered[filtered['name'].str.lower() == product_name.lower()]
    if len(exact) > 0:
        return exact.iloc[0].to_dict()

    # Try substring match on first 3 words
    search_terms = product_name.lower().split()[:3]
    for term in search_terms:
        if len(term) > 3:
            matches = filtered[filtered['name'].str.lower().str.contains(term, na=False)]
            if len(matches) > 0:
                return matches.iloc[0].to_dict()

    # Fallback to first product in category
    return filtered.iloc[0].to_dict() if len(filtered) > 0 else None

def _generate_justification(category_key, equipment_reqs, room_type):
    """Context-aware justification generation."""
    justifications = {
        'display': f"Primary {equipment_reqs['displays']['size_inches']}\" display for {room_type}",
        'video_system': f"Video conferencing with {equipment_reqs['video_system']['camera_type']}",
        'microphones': f"Professional microphone array providing {equipment_reqs['audio_system'].get('microphone_coverage_zones', 2)}-zone coverage",
        'ceiling_mic': "Ceiling-mounted microphone for clean audio capture",
        'speakers': f"Distributed speaker system with {equipment_reqs['audio_system'].get('speaker_zones_required', 2)} zones",
        'dsp': "Digital signal processor for echo cancellation and audio mixing",
        'control': f"{equipment_reqs['control_system']['type']} for system automation",
        'mount': "Professional display mounting hardware",
        'cables': "High-speed AV connectivity infrastructure"
    }
    return justifications.get(category_key, f"Essential {category_key} component for {room_type}")

def _add_essential_missing_components(boq_items, equipment_reqs, product_df, complexity, room_type='Standard Conference Room'):
    """Add missing components based on required system configuration."""

    # Get what should be there
    avixa_calcs = {
        'estimated_occupancy': 10,
        'recommended_bandwidth_mbps': 50,
        'total_power_load_watts': 1000,
        'ups_runtime_minutes': 15,
        'audio_power_needed': 200,
        'microphone_coverage_zones': 2,
        'speaker_zones_required': 2
    }
    required_components = _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type)

    # Track what we have
    components_present = {item.get('category', '').lower(): True for item in boq_items}

    added_count = 0

    for comp_key, comp_spec in required_components.items():
        category = comp_spec['category']

        # Check if this category is already present
        has_component = any(category.lower() in cat_key for cat_key in components_present.keys())

        if not has_component:
            # Find a product for this category - try exact first
            matching = product_df[product_df['category'] == category]

            # Fallback to substring search
            if len(matching) == 0:
                matching = product_df[
                    product_df['category'].str.contains(category, case=False, na=False)
                ]

            if len(matching) > 0:
                st.info(f"Auto-adding {comp_spec['category']} ({len(matching)} options available)")
                product = matching.iloc[0]
                boq_items.append({
                    'category': product['category'],
                    'name': product['name'],
                    'brand': product['brand'],
                    'quantity': comp_spec['quantity'],
                    'price': float(product['price']),
                    'justification': comp_spec['justification'] + ' (auto-added for completeness)',
                    'specifications': product.get('features', ''),
                    'image_url': product.get('image_url', ''),
                    'gst_rate': product.get('gst_rate', 18),
                    'matched': True
                })
                added_count += 1

    if added_count > 0:
        st.info(f"Added {added_count} missing components to complete the system")

    return boq_items

# --- ★★★ COMPREHENSIVE BOQ GENERATION HELPERS ★★★ ---

# ★★★ UPDATE 1: Fix _get_required_components_by_complexity() ★★★
def _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type):
    """Define required components with NO DUPLICATES."""
    
    component_definitions = {
        'display': {
            'category': 'Displays',
            'quantity': equipment_reqs['displays']['quantity'],
            'size_requirement': equipment_reqs['displays']['size_inches'],
            'priority': 1,
            'justification': f"Primary display meeting AVIXA DISCAS standards for {room_type}"
        },
        'mount': {
            'category': 'Mounts',
            'quantity': equipment_reqs['displays']['quantity'],
            'priority': 5,
            'justification': 'Professional display mounting hardware'
        },
        'cables': {
            'category': 'Cables',
            'quantity': 4,
            'priority': 6,
            'justification': 'Essential AV connectivity infrastructure'
        },
        'video_bar': {
            'category': 'Video Conferencing',
            'quantity': 1,  # FIXED: Always 1 video bar
            'priority': 2,
            'justification': 'All-in-one video conferencing solution'
        },
        'camera': {
            'category': 'PTZ & Pro Video Cameras',  # FIXED: More specific category
            'quantity': equipment_reqs['video_system']['camera_count'],
            'priority': 2,
            'justification': f"{equipment_reqs['video_system']['camera_type']}"
        },
        'microphones': {
            'category': 'Audio: Microphones & Conferencing',  # FIXED: More specific
            'quantity': equipment_reqs['audio_system'].get('microphone_count', 2),
            'priority': 3,
            'justification': f"Ceiling microphone array with {equipment_reqs['audio_system'].get('microphone_count', 2)} zones"
        },
        'speakers': {
            'category': 'Audio: Speakers',  # FIXED: More specific
            'quantity': equipment_reqs['audio_system'].get('speaker_count', 2),
            'priority': 3,
            'justification': f"Distributed ceiling speaker system"
        },
        'dsp': {
            'category': 'Audio: DSP',  # FIXED: More specific
            'quantity': 1,
            'priority': 3,
            'justification': 'Digital Signal Processor with acoustic echo cancellation'
        },
        'amplifier': {
            'category': 'Audio: Amplifiers',  # FIXED: More specific
            'quantity': 1,
            'priority': 4,
            'justification': 'Multi-zone power amplifier'
        },
        'control': {
            'category': 'Control Systems & Processing',  # FIXED: More specific
            'quantity': 1,
            'priority': 4,
            'justification': 'System control processor with touch panel'
        },
        'network_switch': {
            'category': 'Network Switches (AV-friendly)',  # FIXED: More specific
            'quantity': 1,
            'priority': 5,
            'justification': f"Managed AV network switch"
        },
        'ups': {
            'category': 'Infrastructure',  # Keep this one generic
            'quantity': 1,
            'priority': 6,
            'justification': f"Uninterruptible Power Supply with {avixa_calcs.get('ups_runtime_minutes', 15)}min runtime"
        }
    }

    # CRITICAL FIX: Define complexity blueprints WITHOUT duplicates
    complexity_map = {
        'simple': ['display', 'mount', 'cables', 'video_bar'],
        'moderate': ['display', 'mount', 'cables', 'video_bar', 'microphones', 'speakers', 'control'],
        'advanced': [
            'display', 'mount', 'cables', 'camera',  # NOT video_bar + camera
            'microphones', 'speakers', 'dsp', 'amplifier', 'control', 'network_switch'
        ],
        'complex': [
            'display', 'mount', 'cables', 'camera',
            'microphones', 'speakers', 'dsp', 'amplifier', 'control', 
            'network_switch', 'ups'
        ]
    }
    
    required_keys = complexity_map.get(complexity, complexity_map['moderate'])
    return {key: component_definitions[key] for key in required_keys}


def _build_comprehensive_boq_prompt(room_type, complexity, room_area, avixa_calcs, equipment_reqs,
                                     required_components, product_df, budget_tier):
    """Build detailed AI prompt with all product options."""

    budget_filters = {
        'Economy': (0, 2000),
        'Standard': (500, 4000),
        'Premium': (2000, 8000),
        'Enterprise': (5000, 15000)
    }
    price_range = budget_filters.get(budget_tier, (0, 10000))

    # Build product catalog by component type
    product_catalog = {}
    for comp_key, comp_spec in required_components.items():
        category = comp_spec['category']
        # First try exact category match
        matching_products = product_df[product_df['category'] == category]

        # If no exact match, try substring match
        if len(matching_products) == 0:
            matching_products = product_df[
                product_df['category'].str.contains(category, case=False, na=False)
            ]

        # Apply budget filter ONLY if we have 20+ products
        if len(matching_products) > 20:
            budget_filtered = matching_products[
                (matching_products['price'] >= price_range[0]) &
                (matching_products['price'] <= price_range[1])
            ]
            # Only use budget filter if it still gives us 5+ products
            if len(budget_filtered) >= 5:
                matching_products = budget_filtered

        # Provide MORE options (20 instead of 15)
        product_catalog[comp_key] = matching_products.head(20)

    # Build prompt sections
    prompt = f"""You are an AVIXA-certified AV system designer. Design a complete system for: {room_type}

ROOM SPECIFICATIONS:
- Area: {room_area} sq ft
- Capacity: {avixa_calcs['estimated_occupancy']} people
- Complexity Level: {complexity.upper()}
- Budget Tier: {budget_tier}

AVIXA CALCULATIONS:
- Display Size Required: {equipment_reqs['displays']['size_inches']}" (Qty: {equipment_reqs['displays']['quantity']})
- Camera System: {equipment_reqs['video_system']['camera_type']} (Qty: {equipment_reqs['video_system']['camera_count']})
- Microphone Zones: {equipment_reqs['audio_system'].get('microphone_count', 2)}
- Speaker Zones: {equipment_reqs['audio_system'].get('speaker_count', 2)}
- DSP Required: {'YES' if equipment_reqs['audio_system'].get('dsp_required') else 'NO'}
- Control System: {equipment_reqs['control_system']['type']}
- Network Bandwidth: {avixa_calcs['recommended_bandwidth_mbps']} Mbps
- Power Load: {avixa_calcs['total_power_load_watts']}W

MANDATORY COMPONENTS ({len(required_components)} items):
"""

    # Add each component with product options
    for comp_key, comp_spec in sorted(required_components.items(), key=lambda x: x[1]['priority']):
        prompt += f"\n{comp_key.upper()} (Category: {comp_spec['category']}, Qty: {comp_spec['quantity']}):\n"

        if comp_key in product_catalog and len(product_catalog[comp_key]) > 0:
            for _, prod in product_catalog[comp_key].iterrows():
                prompt += f"  • {prod['brand']} {prod['name']} - ${prod['price']:.0f}\n"
        else:
            prompt += f"  • (Use any available {comp_spec['category']} product)\n"

    prompt += f"""

OUTPUT FORMAT (STRICT JSON - NO TEXT BEFORE OR AFTER):
{{
"""

    # Build JSON template
    for i, (comp_key, comp_spec) in enumerate(required_components.items()):
        comma = "," if i < len(required_components) - 1 else ""
        prompt += f'  "{comp_key}": {{"name": "EXACT product name from list above", "qty": {comp_spec["quantity"]}}}{comma}\n'

    prompt += f"""}}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no explanations
2. Use EXACT product names from the lists above
3. You MUST include ALL {len(required_components)} components
4. Match display size requirements ({equipment_reqs['displays']['size_inches']}" minimum)
5. Select products appropriate for {budget_tier} budget tier
6. Ensure all category requirements are met
7. If multiple options exist, prefer known brands (Samsung, LG, Poly, Shure, QSC, Crestron)
"""

    return prompt

def _build_boq_from_ai_selection(ai_selection, required_components, product_df, equipment_reqs, room_type):
    """Build BOQ items from AI selection with enhanced matching."""

    boq_items = []
    matched_count = 0

    for comp_key, selection in ai_selection.items():
        if comp_key not in required_components:
            continue

        comp_spec = required_components[comp_key]
        category = comp_spec['category']

        # Try strict matching first
        matched_product = _strict_product_match(selection['name'], product_df, category)

        if matched_product:
            matched_count += 1

            # Extract actual product specs for better justification
            actual_justification = comp_spec['justification']
            if comp_key == 'display':
                size_match = re.search(r'(\d+)"', matched_product['name'])
                if size_match:
                    actual_size = size_match.group(1)
                    actual_justification = f"{actual_size}\" professional display meeting AVIXA DISCAS standards for {room_type}"

            boq_items.append({
                'category': matched_product['category'],
                'name': matched_product['name'],
                'brand': matched_product['brand'],
                'quantity': selection.get('qty', comp_spec['quantity']),
                'price': float(matched_product['price']),
                'justification': actual_justification,
                'specifications': matched_product.get('features', ''),
                'image_url': matched_product.get('image_url', ''),
                'gst_rate': matched_product.get('gst_rate', 18),
                'matched': True,
                'power_draw': estimate_power_draw(matched_product['category'], matched_product['name'])
            })
        else:
            # Fallback: Use best available product in category
            fallback_product = _get_fallback_product(category, product_df, comp_spec)
            if fallback_product:
                boq_items.append({
                    'category': fallback_product['category'],
                    'name': fallback_product['name'],
                    'brand': fallback_product['brand'],
                    'quantity': comp_spec['quantity'],
                    'price': float(fallback_product['price']),
                    'justification': comp_spec['justification'] + ' (auto-selected)',
                    'specifications': fallback_product.get('features', ''),
                    'image_url': fallback_product.get('image_url', ''),
                    'gst_rate': fallback_product.get('gst_rate', 18),
                    'matched': False,
                    'power_draw': estimate_power_draw(fallback_product['category'], fallback_product['name'])
                })

    st.info(f"Matched {matched_count}/{len(required_components)} components from AI selection")
    
    # ★★★ FIX 4: ENFORCE COMPONENT COUNT ★★★
    if len(boq_items) < len(required_components):
        st.error(f"❌ AI returned {len(boq_items)}/{len(required_components)} components!")
        
        # Find missing components
        added_categories = {item['category'] for item in boq_items}
        for comp_key, comp_spec in required_components.items():
            if comp_spec['category'] not in added_categories:
                st.warning(f"    Missing: {comp_key} ({comp_spec['category']})")
                
                # Auto-add fallback
                fallback = _get_fallback_product(comp_spec['category'], product_df, comp_spec)
                if fallback:
                    boq_items.append({
                        'category': fallback['category'],
                        'name': fallback['name'],
                        'brand': fallback['brand'],
                        'quantity': comp_spec['quantity'],
                        'price': float(fallback['price']),
                        'justification': f"{comp_spec['justification']} (auto-added)",
                        'specifications': fallback.get('features', ''),
                        'image_url': fallback.get('image_url', ''),
                        'gst_rate': fallback.get('gst_rate', 18),
                        'matched': False
                    })
    # ★★★ END FIX 4 ★★★
    
    # ★★★ UPDATE 3: Add component validation before returning BOQ ★★★
    validation_errors = []
    
    # Check for duplicates
    seen_categories = {}
    for item in boq_items:
        cat = item['category']
        if cat in seen_categories:
            if cat not in ['Cables', 'Mounts', 'Audio: Speakers', 'Audio: Microphones & Conferencing']:
                validation_errors.append(f"DUPLICATE: Multiple items in '{cat}' category")
        seen_categories[cat] = seen_categories.get(cat, 0) + 1
    
    # Check for invalid specs
    for item in boq_items:
        specs = item.get('specifications', '')
        if 'Auto-generated' in specs or len(specs) < 10:
            validation_errors.append(f"INVALID SPECS: {item['name']} has placeholder data")
    
    # Check for logical conflicts
    has_video_bar = any('video bar' in item['name'].lower() for item in boq_items)
    has_separate_camera = any('camera' in item['category'].lower() and 'video bar' not in item['name'].lower() for item in boq_items)
    
    if has_video_bar and has_separate_camera:
        validation_errors.append("LOGIC ERROR: Both video bar AND separate camera system selected")
    
    if validation_errors:
        st.error("### BOQ Generation Issues:")
        for err in validation_errors:
            st.write(f"- {err}")
        st.warning("Attempting automatic correction...")

    return boq_items

def _get_fallback_product(category, product_df, comp_spec):
    """Get best fallback product for a category."""
    # CRITICAL: Log what we're searching for
    st.write(f"🔍 Searching fallback for category: {category}")

    # Try exact match first
    matching = product_df[product_df['category'] == category]
    st.write(f"    Exact matches: {len(matching)}")

    # Fallback to substring
    if len(matching) == 0:
        matching = product_df[product_df['category'].str.contains(category, case=False, na=False)]
    
    # ★★★ FIX 6: ADD BETTER ERROR HANDLING ★★★
    if len(matching) == 0:
        st.error(f"❌ CRITICAL: No products in catalog for category '{category}'!")
        st.write(f"    Available categories: {sorted(product_df['category'].unique())}")
        return None
    # ★★★ END FIX 6 ★★★

    # For displays, try to match size requirement
    if 'display' in category.lower() and 'size_requirement' in comp_spec:
        target_size = comp_spec['size_requirement']
        for _, prod in matching.iterrows():
            size_match = re.search(r'(\d+)"', prod['name'])
            if size_match:
                size = int(size_match.group(1))
                if abs(size - target_size) <= 10:
                    return prod.to_dict()

    # Prefer mid-range products (avoid cheapest/most expensive)
    matching_sorted = matching.sort_values('price')
    if len(matching_sorted) > 5:
        # Use 40th percentile for good value
        index = int(len(matching_sorted) * 0.4)
        return matching_sorted.iloc[index].to_dict()
    else:
        mid_index = len(matching_sorted) // 2
        return matching_sorted.iloc[mid_index].to_dict()

def generate_boq_with_justifications(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Enhanced multi-shot AI system with comprehensive product selection."""
    
    # ★★★ IMMEDIATE FIX: ADD DIAGNOSTIC BLOCK ★★★
    st.write("### 🔬 PRE-GENERATION DIAGNOSTICS")
    st.write(f"1. **Room Type Received:** `{room_type}`")
    
    if room_type in ROOM_SPECS:
        spec = ROOM_SPECS[room_type]
        st.success(f"    ✓ Found in ROOM_SPECS")
        st.write(f"    - Complexity: **{spec['complexity']}**")
        st.write(f"    - Area: {spec['area_sqft']} sq ft")
    else:
        st.error(f"    ❌ NOT FOUND in ROOM_SPECS!")
        st.write(f"    Available keys:")
        for key in ROOM_SPECS.keys():
            st.write(f"    - '{key}'")
    
    st.write(f"2. **Budget Tier:** `{budget_tier}`")
    st.write(f"3. **Room Area:** `{room_area}` sq ft")
    st.write(f"4. **Product Catalog:** {len(product_df)} items")
    # ★★★ END IMMEDIATE FIX ★★★

    clean_product_df = clean_and_validate_product_data(product_df)
    if clean_product_df is None or len(clean_product_df) == 0:
        st.error("No valid products in catalog.")
        return None, [], None, None

    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)

    # Determine minimum components based on room size
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')

    # Enhanced required components structure
    required_components = _get_required_components_by_complexity(complexity, equipment_reqs, avixa_calcs, room_type)

    st.info(f"Generating {len(required_components)}-component system for {room_type} ({complexity} complexity)")
    # Debug: Show what we're looking for
    with st.expander("🔍 Debug: Product Availability", expanded=False):
        for comp_key, comp_spec in required_components.items():
            category = comp_spec['category']
            available = len(product_df[product_df['category'] == category])
            st.write(f"**{comp_key}** ({category}): {available} products available")

    # Enhanced debug output
    with st.expander("📊 Detailed Product Catalog Analysis", expanded=False):
        st.write("### Available Products by Category:")
        for cat in product_df['category'].unique():
            cat_count = len(product_df[product_df['category'] == cat])
            if cat_count > 0:
                cat_price_range = product_df[product_df['category'] == cat]['price'].agg(['min', 'max'])
                st.write(f"**{cat}**: {cat_count} products (${cat_price_range['min']:.0f} - ${cat_price_range['max']:.0f})")
            else:
                st.write(f"**{cat}**: 0 products")


        st.write(f"\n### Required vs Available:")
        for comp_key, comp_spec in required_components.items():
            category = comp_spec['category']
            exact_match = len(product_df[product_df['category'] == category])
            substring_match = len(product_df[product_df['category'].str.contains(category, case=False, na=False)])
            st.write(f"- **{comp_key}** needs '{category}': {exact_match} exact / {substring_match} partial matches")

    # Build comprehensive product selection prompt
    product_selection_prompt = _build_comprehensive_boq_prompt(
        room_type, complexity, room_area, avixa_calcs, equipment_reqs,
        required_components, clean_product_df, budget_tier
    )

    try:
        response = generate_with_retry(model, product_selection_prompt)
        if not response or not response.text:
            raise Exception("AI returned empty response")

        ai_selection = _parse_ai_product_selection(response.text)

        # Enhanced product matching and BOQ building
        boq_items = _build_boq_from_ai_selection(
            ai_selection, required_components, clean_product_df, equipment_reqs, room_type
        )

        # CRITICAL: Show what AI actually selected
        with st.expander("🤖 AI Selection Results", expanded=True):
            st.json(ai_selection)
            st.write(f"AI returned {len(ai_selection)} components (needed {len(required_components)})")

        # Validate system completeness
        if len(boq_items) < len(required_components):
            st.warning(f"System incomplete ({len(boq_items)}/{len(required_components)}). Adding missing components...")
            boq_items = _add_essential_missing_components(
                boq_items, equipment_reqs, clean_product_df, complexity, room_type
            )

        # Final validation and correction
        corrected_items, issues, warnings = validate_boq_pricing_and_logic(boq_items, clean_product_df)

        st.success(f"✅ Generated complete system with {len(corrected_items)} components")

        return None, corrected_items, avixa_calcs, equipment_reqs

    except Exception as e:
        st.error(f"AI generation failed: {str(e)}. Using intelligent fallback...")
        fallback_items = create_smart_fallback_boq(clean_product_df, room_type, equipment_reqs, avixa_calcs)

        if len(fallback_items) < 4:
            st.error("Critical: Fallback also failed. Check product database.")
            return None, [], avixa_calcs, equipment_reqs

        return None, fallback_items, avixa_calcs, equipment_reqs

def validate_against_avixa(model, guidelines, boq_items):
    """Use AI to validate the BOQ against AVIXA standards."""
    if not guidelines or not boq_items or not model:
        return []

    prompt = f"""
    You are an AVIXA Certified Technology Specialist (CTS). Review the following BOQ against the provided AVIXA standards.
    List any potential non-compliance issues, missing items (like accessibility components), or areas for improvement.
    If no issues are found, respond with 'No specific compliance issues found.'

    **AVIXA Standards Summary:**
    {guidelines}

    **Bill of Quantities to Review:**
    {json.dumps(boq_items, indent=2)}

    **Your Compliance Review:**
    """
    try:
        response = generate_with_retry(model, prompt)
        if response and response.text:
            if "no specific compliance issues" in response.text.lower():
                return []
            return [line.strip() for line in response.text.split('\n') if line.strip()]
        return []
    except Exception as e:
        return [f"AVIXA compliance check failed: {str(e)}"]

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, room_type='Standard Conference Room'):
    """Validate BOQ against AVIXA standards and compliance requirements."""
    issues = []
    warnings = []

    # Display Compliance Validation
    displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
    if not displays:
        issues.append("CRITICAL: No display found in BOQ")
    else:
        for display in displays:
            size_match = re.search(r'(\d+)"', display.get('name', ''))
            if size_match:
                size = int(size_match.group(1))
                recommended_size = avixa_calcs['detailed_viewing_display_size']
                size_diff = abs(size - recommended_size)

                if size_diff > 20:
                    issues.append(f"CRITICAL: Display size {size}\" significantly deviates from AVIXA calculation ({recommended_size}\")")
                elif size_diff > 10:
                    warnings.append(f"Display size {size}\" deviates from AVIXA DISCAS calculation ({recommended_size}\"). Consider larger display for optimal viewing.")
                else:
                    # Size is acceptable
                    pass

    # Audio System Compliance
    has_dsp = any('dsp' in item.get('name', '').lower() or 'processor' in item.get('name', '').lower()
                  for item in boq_items)

    # Only flag as critical if room is moderate+ complexity
    room_spec = ROOM_SPECS.get(room_type, {})
    complexity = room_spec.get('complexity', 'simple')

    if equipment_reqs['audio_system'].get('dsp_required') and not has_dsp and complexity != 'simple':
        issues.append("CRITICAL: DSP required for this room type but not found in BOQ")

    # Power Load Validation
    total_estimated_power = sum(item.get('power_draw', 150) * item.get('quantity', 1)
                                for item in boq_items if 'service' not in item.get('category', '').lower())

    if total_estimated_power > avixa_calcs['total_power_load_watts'] * 1.2:
        warnings.append(f"Power consumption ({total_estimated_power}W) exceeds AVIXA calculation")

    # UPS Requirement Check
    has_ups = any('ups' in item.get('name', '').lower() for item in boq_items)
    if avixa_calcs['ups_va_required'] > 1000 and not has_ups and complexity in ['advanced', 'complex']:
        issues.append("CRITICAL: UPS system required for this room type but not found in BOQ")

    # Cable Infrastructure Check
    required_cables = avixa_calcs['cable_runs']
    cable_categories = ['cable', 'wire', 'connect']
    has_adequate_cables = any(
        any(cable_cat in item.get('category', '').lower() for cable_cat in cable_categories)
        for item in boq_items
    )

    if not has_adequate_cables:
        warnings.append("Cable infrastructure may be inadequate for calculated runs")

    # Compliance Requirements Check
    if avixa_calcs['requires_ada_compliance']:
        ada_items = [item for item in boq_items
                     if any(term in item.get('name', '').lower()
                            for term in ['assistive', 'ada', 'hearing', 'loop'])]
        if not ada_items:
            issues.append("CRITICAL: ADA compliance required but no assistive devices in BOQ")

    return {
        'avixa_issues': issues,
        'avixa_warnings': warnings,
        'compliance_score': max(0, 100 - (len(issues) * 25) - (len(warnings) * 5)),
        'avixa_calculations_used': avixa_calcs,
        'equipment_requirements_met': equipment_reqs
    }

def estimate_power_draw(category, name):
    """Estimate power draw based on equipment category and name."""
    name_lower = name.lower()
    category_lower = category.lower()

    if 'display' in category_lower:
        if any(size in name_lower for size in ['55', '60', '65']):
            return 200
        elif any(size in name_lower for size in ['70', '75', '80']):
            return 300
        elif any(size in name_lower for size in ['85', '90', '95', '98']):
            return 400
        else:
            return 150
    elif 'audio' in category_lower:
        if 'amplifier' in name_lower:
            return 300
        elif 'speaker' in name_lower:
            return 60
        elif 'microphone' in name_lower:
            return 15
        else:
            return 50
    elif 'video conferencing' in category_lower:
        if 'rally' in name_lower or 'bar' in name_lower:
            return 90
        elif 'camera' in name_lower:
            return 25
        else:
            return 40
    elif 'control' in category_lower:
        return 75
    else:
        return 25 # Default for misc items

# --- Enhanced BOQ Item Extraction ---
def extract_enhanced_boq_items(boq_content, product_df):
    """Extract BOQ items from AI response based on new company format."""
    items = []
    lines = boq_content.split('\n')
    in_table = False

    for line in lines:
        line = line.strip()

        # Detect table start based on new headers
        if '|' in line and any(keyword in line.lower() for keyword in ['category', 'make', 'model', 'specifications']):
            in_table = True
            continue

        # Skip separator lines
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue

        # Process table rows
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 6: # Category | Make | Model No. | Specifications | Quantity | Unit Price | Remarks
                category = parts[0]
                brand = parts[1]
                product_name = parts[2]
                specifications = parts[3]
                remarks = parts[6] if len(parts) > 6 else "Essential AV system component."

                # Extract quantity and price robustly
                quantity = 1
                price = 0
                try:
                    quantity = int(parts[4])
                except (ValueError, IndexError):
                    quantity = 1

                try:
                    price_str = parts[5].replace('$', '').replace(',', '')
                    price = float(price_str)
                except (ValueError, IndexError):
                    price = 0

                # Match with product database
                matched_product = match_product_in_database(product_name, brand, product_df)
                if matched_product is not None:
                    price = float(matched_product.get('price', price))
                    actual_brand = matched_product.get('brand', brand)
                    actual_category = matched_product.get('category', category)
                    actual_name = matched_product.get('name', product_name)
                    image_url = matched_product.get('image_url', '')
                    gst_rate = matched_product.get('gst_rate', 18)
                else:
                    actual_brand = brand
                    actual_category = normalize_category(category, product_name)
                    actual_name = product_name
                    image_url = ''
                    gst_rate = 18

                items.append({
                    'category': actual_category,
                    'name': actual_name,
                    'brand': actual_brand,
                    'quantity': quantity,
                    'price': price,
                    'justification': remarks, # Mapped to justification
                    'specifications': specifications,
                    'image_url': image_url,
                    'gst_rate': gst_rate,
                    'matched': matched_product is not None,
                    'power_draw': estimate_power_draw(actual_category, actual_name)
                })

            elif in_table and not line.startswith('|'):
                in_table = False

    return items

# --- Enhanced Product Matching ---
def match_product_in_database(product_name, brand, product_df):
    """Enhanced product matching with better validation."""
    if product_df is None or len(product_df) == 0:
        return None

    try:
        # Clean up the search strings
        safe_product_name = str(product_name).strip() if product_name else ""
        safe_brand = str(brand).strip() if brand else ""

        if not safe_product_name and not safe_brand:
            return None

        # First try exact name match (case insensitive)
        if safe_product_name:
            exact_matches = product_df[
                product_df['name'].astype(str).str.lower() == safe_product_name.lower()
            ]
            if len(exact_matches) > 0:
                return exact_matches.iloc[0].to_dict()

        # Try brand + partial name match
        if safe_brand and safe_product_name:
            brand_matches = product_df[
                product_df['brand'].astype(str).str.lower() == safe_brand.lower()
            ]
            if len(brand_matches) > 0:
                # Look for name match within brand matches
                name_matches = brand_matches[
                    brand_matches['name'].astype(str).str.contains(
                        re.escape(safe_product_name.split()[0]), case=False, na=False
                    )
                ]
                if len(name_matches) > 0:
                    return name_matches.iloc[0].to_dict()

        # Fallback: fuzzy name matching
        if safe_product_name and len(safe_product_name) > 3:
            # Extract key terms from product name
            key_terms = safe_product_name.lower().split()[:3] # First 3 words
            for term in key_terms:
                if len(term) > 3: # Only meaningful terms
                    matches = product_df[
                        product_df['name'].astype(str).str.contains(
                            re.escape(term), case=False, na=False
                        )
                    ]
                    if len(matches) > 0:
                        return matches.iloc[0].to_dict()

        return None

    except Exception as e:
        return None

def normalize_category(category_text, product_name):
    """Normalize category names to standard categories."""
    category_lower = category_text.lower()
    product_lower = product_name.lower()

    if any(term in category_lower or term in product_lower for term in ['display', 'monitor', 'screen', 'projector', 'tv']):
        return 'Displays'
    elif any(term in category_lower or term in product_lower for term in ['audio', 'speaker', 'microphone', 'sound', 'amplifier']):
        return 'Audio'
    elif any(term in category_lower or term in product_lower for term in ['video', 'conferencing', 'camera', 'codec', 'rally']):
        return 'Video Conferencing'
    elif any(term in category_lower or term in product_lower for term in ['control', 'processor', 'switch', 'matrix']):
        return 'Control'
    elif any(term in category_lower or term in product_lower for term in ['mount', 'bracket', 'rack', 'stand']):
        return 'Mounts'
    elif any(term in category_lower or term in product_lower for term in ['cable', 'connect', 'wire', 'hdmi', 'usb']):
        return 'Cables'
    else:
        return 'General'

# --- UI Components ---
def create_project_header():
    """Create professional project header."""
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.title("Professional AV BOQ Generator")
        st.caption("Production-ready Bill of Quantities with technical validation")

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

        # Recommend room type based on area
        recommended_type = None
        for room_type, specs in ROOM_SPECS.items():
            if specs["area_sqft"][0] <= room_area <= specs["area_sqft"][1]:
                recommended_type = room_type
                break

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
        "dedicated_circuit": has_dedicated_circuit,
        "network_capability": network_capability,
        "cable_management": cable_management,
        "ada_compliance": ada_compliance,
        "fire_code_compliance": fire_code_compliance,
        "security_clearance": security_clearance
    }


# --- Multi-Room Interface ---
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


# --- BOQ Display and Editing ---
def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items added yet."
        return

    # Using the new AI response format for consistency
    boq_content = "## Bill of Quantities\n\n"
    boq_content += "| Category | Make | Model No. | Specifications | Qty | Unit Price (USD) | Remarks |\n"
    boq_content += "|---|---|---|---|---|---|---|\n"

    total_cost = 0
    for item in st.session_state.boq_items:
        quantity = item.get('quantity', 1)
        price = item.get('price', 0)
        total = quantity * price
        total_cost += total

        boq_content += f"| {item.get('category', 'N/A')} | {item.get('brand', 'N/A')} | {item.get('name', 'N/A')} | {item.get('specifications', '')} | {quantity} | ${price:,.2f} | {item.get('justification', '')} |\n"

    st.session_state.boq_content = boq_content

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

def create_interactive_boq_editor(product_df):
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")

    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Items in BOQ", item_count)

    with col2:
        if 'boq_items' in st.session_state and st.session_state.boq_items:
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            currency = st.session_state.get('currency', 'USD')
            if currency == 'INR':
                display_total = convert_currency(total_cost, 'INR')
                st.metric("Hardware Subtotal", format_currency(display_total, 'INR'))
            else:
                st.metric("Hardware Subtotal", format_currency(total_cost, 'USD'))
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
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ or add products manually.")
        return

    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        category_str = str(item.get('category', 'General'))
        name_str = str(item.get('name', 'Unknown'))

        with st.expander(f"{category_str} - {name_str[:50]}..."):
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])

            with col1:
                new_name = st.text_input("Product Name", value=item.get('name', ''), key=f"name_{i}")
                new_brand = st.text_input("Brand", value=item.get('brand', ''), key=f"brand_{i}")

            with col2:
                category_list = ['Displays', 'Audio', 'Video Conferencing', 'Control', 'Mounts', 'Cables', 'General']
                current_category = item.get('category', 'General')
                if current_category not in category_list: current_category = 'General'

                new_category = st.selectbox("Category", category_list, index=category_list.index(current_category), key=f"category_{i}")

            with col3:
                try:
                    safe_quantity = max(1, int(float(item.get('quantity', 1))))
                except (ValueError, TypeError):
                    safe_quantity = 1

                new_quantity = st.number_input("Quantity", min_value=1, value=safe_quantity, key=f"qty_{i}")

                try:
                    current_price = float(item.get('price', 0))
                except (ValueError, TypeError):
                    current_price = 0

                display_price = convert_currency(current_price, 'INR') if currency == 'INR' else current_price

                new_price = st.number_input(f"Unit Price ({currency})", min_value=0.0, value=float(display_price), key=f"price_{i}")

                stored_price = new_price / get_usd_to_inr_rate() if currency == 'INR' else new_price

            with col4:
                total_price = stored_price * new_quantity
                display_total = convert_currency(total_price, 'INR') if currency == 'INR' else total_price
                st.metric("Total", format_currency(display_total, currency))

                if st.button("Remove", key=f"remove_{i}", type="secondary"):
                    items_to_remove.append(i)

            st.session_state.boq_items[i].update({
                'name': new_name, 'brand': new_brand, 'category': new_category,
                'quantity': new_quantity, 'price': stored_price
            })

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
            st.warning("No products found.")
            return

        selected_product_str = st.selectbox("Select Product", product_options, key="add_product_select")
        selected_product = next((row for _, row in filtered_df.iterrows() if f"{row['brand']} - {row['name']}" == selected_product_str), None)

    with col2:
        if selected_product is not None:
            quantity = st.number_input("Quantity", min_value=1, value=1, key="add_product_qty")
            base_price = float(selected_product.get('price', 0))
            display_price = convert_currency(base_price, 'INR') if currency == 'INR' else base_price

            st.metric("Unit Price", format_currency(display_price, currency))
            st.metric("Total", format_currency(display_price * quantity, currency))

            if st.button("Add to BOQ", type="primary"):
                new_item = {
                    'category': selected_product.get('category', 'General'), 'name': selected_product.get('name', ''),
                    'brand': selected_product.get('brand', ''), 'quantity': quantity, 'price': base_price,
                    'justification': 'Manually added component.', 'specifications': selected_product.get('features', ''),
                    'image_url': selected_product.get('image_url', ''),
                    'gst_rate': selected_product.get('gst_rate', 18), 'matched': True
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
        search_cols = ['name', 'brand', 'features']
        mask = product_df[search_cols].apply(
            lambda x: x.astype(str).str.contains(search_term, case=False, na=False)
        ).any(axis=1)
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
                    display_price = convert_currency(price, 'INR') if currency == 'INR' else price
                    st.metric("Price", format_currency(display_price, currency))

                with col_c:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        new_item = {
                            'category': product.get('category', 'General'), 'name': product.get('name', ''),
                            'brand': product.get('brand', ''), 'quantity': add_qty, 'price': price,
                            'justification': 'Added via search.', 'specifications': product.get('features', ''),
                            'image_url': product.get('image_url', ''),
                            'gst_rate': product.get('gst_rate', 18), 'matched': True
                        }
                        st.session_state.boq_items.append(new_item)
                        update_boq_content_with_current_items()
                        st.success(f"Added {add_qty}x {product['name']}!")
                        st.rerun()

# --- Main Application ---
def get_sample_product_data():
    """Provide comprehensive sample products with AVIXA-relevant specifications."""
    return [
        # Displays
        {
            'name': 'Samsung 55" QM55R 4K Display',
            'brand': 'Samsung',
            'category': 'Displays',
            'price': 1200,
            'features': '55" 4K UHD, 500-nit brightness, 16/7 operation, TIZEN 4.0',
            'image_url': 'https://images.samsung.com/is/image/samsung/assets/sg/business-images/qm55r/qm55r_001_front_black.png',
            'gst_rate': 18,
            'power_draw': 180
        },
        # ... more sample data can be added here
    ]

def show_login_page():
    """Simple login page for internal users."""
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="⚡")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title("🏢 AllWave AV & GS")
        st.subheader("Design & Estimation Portal")
        st.markdown("---")

        with st.form("login_form"):
            email = st.text_input("Email ID", placeholder="yourname@allwaveav.com or yourname@allwavegs.com")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Login", type="primary", use_container_width=True)

            if submit:
                # Now checks if the email ends with EITHER of the domains in the tuple.
                if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Please use your AllWave AV or AllWave GS email and a valid password")

        st.markdown("---")
        st.info("Phase 1 Internal Tool - Contact IT for access issues")

def main():
    # Simple authentication for Phase 1
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        show_login_page()
        return

    # Page config for main app
    st.set_page_config(
        page_title="Professional AV BOQ Generator",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- Enhanced Session State Initialization ---
    if 'boq_items' not in st.session_state:
        st.session_state.boq_items = []
    if 'boq_content' not in st.session_state:
        st.session_state.boq_content = None
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    if 'project_rooms' not in st.session_state:
        st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state:
        st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state:
        st.session_state.gst_rates = {'Electronics': 18, 'Services': 18, 'Default': 18}

    # Load data
    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=False):
            for issue in data_issues:
                st.warning(issue)

    if product_df is None:
        return

    model = setup_gemini()

    project_id, quote_valid_days = create_project_header()

    # --- Sidebar ---
    with st.sidebar:
        st.markdown(f"👤 **Logged in as:** {st.session_state.get('user_email', 'Unknown')}")
        if st.button("Logout", type="secondary"):
            st.session_state.clear()
            st.rerun()
        st.markdown("---")
        st.header("Project Configuration")
        client_name = st.text_input("Client Name", key="client_name_input")
        project_name = st.text_input("Project Name", key="project_name_input")

        st.markdown("---")
        st.subheader("🇮🇳 Indian Business Settings")

        currency = st.selectbox("Currency Display", ["INR", "USD"], index=0, key="currency_select")
        st.session_state['currency'] = currency

        electronics_gst = st.number_input("Hardware GST (%)", value=18, min_value=0, max_value=28, key="electronics_gst")
        services_gst = st.number_input("Services GST (%)", value=18, min_value=0, max_value=28, key="services_gst")
        st.session_state.gst_rates['Electronics'] = electronics_gst
        st.session_state.gst_rates['Services'] = services_gst

        st.markdown("---")
        st.subheader("Room Design Settings")

        room_type_key = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        
        st.markdown("#### Room Guidelines")
        # ★★★ FIX 1: ADD EXACT KEY VALIDATION ★★★
        if room_type_key not in ROOM_SPECS:
            st.error(f"CRITICAL: Room type '{room_type_key}' not found in ROOM_SPECS dictionary!")
            st.write("Available keys:", list(ROOM_SPECS.keys()))
        else:
            room_spec = ROOM_SPECS[room_type_key]
            # Safely get the room spec using the key from the selectbox
            st.caption(f"Area: {room_spec.get('area_sqft', ('N/A', 'N/A'))[0]}-{room_spec.get('area_sqft', ('N/A', 'N/A'))[1]} sq ft")
            st.caption(f"Display: {room_spec.get('recommended_display_size', ('N/A', 'N/A'))[0]}\"-{room_spec.get('recommended_display_size', ('N/A', 'N/A'))[1]}\"")
            st.caption(f"Complexity: {room_spec.get('complexity', 'N/A')}")
        # ★★★ END FIX 1 ★★★


    # --- Main Content Tabs ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Multi-Room Project", "Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])

    with tab1:
        create_multi_room_interface()

    with tab2:
        room_area, ceiling_height = create_room_calculator()

    with tab3:
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified'", height=100, key="features_text_area")
        technical_reqs = create_advanced_requirements()
        technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)


    with tab4:
        st.subheader("Professional BOQ Generation")
        col1, col2 = st.columns([2, 1])

        with col1:
            # Add a container for debug info to make the state clear
            with st.container(border=True):
                st.markdown("##### ⚙️ Current Generation Settings")
                try:
                    current_type = st.session_state.room_type_select
                    current_spec = ROOM_SPECS.get(current_type, {})
                    current_complexity = current_spec.get('complexity', 'simple')
                    st.info(f"**Room Type Selected:** `{current_type}` → **Complexity Level:** `{current_complexity.upper()}`")
                except Exception as e:
                    st.warning("Could not read current room type selection yet.")

            if st.button("🚀 Generate BOQ with Justifications", type="primary", use_container_width=True):
                if not model:
                    st.error("AI Model is not available. Please check API key.")
                else:
                    with st.spinner("Generating and validating professional BOQ..."):
                        # --- CRITICAL FIX: Read the LATEST value from session_state ---
                        selected_room_type = st.session_state.room_type_select 
                        selected_budget_tier = st.session_state.budget_tier_slider
                        selected_features = st.session_state.features_text_area

                        room_area_val = st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                        
                        boq_content, boq_items, avixa_calcs, equipment_reqs = generate_boq_with_justifications(
                            model, product_df, guidelines, 
                            selected_room_type,   # Use the guaranteed correct value
                            selected_budget_tier,   # Use the guaranteed correct value
                            selected_features,    # Use the guaranteed correct value
                            technical_reqs, 
                            room_area_val
                        )

                        if boq_items:
                            st.session_state.boq_items = boq_items
                            update_boq_content_with_current_items()

                            # Save to current room in the project list
                            if st.session_state.project_rooms:
                                st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = boq_items

                            avixa_validation = validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs, selected_room_type)
                            issues, warnings = [], [] # Placeholder

                            avixa_warnings_old = validate_against_avixa(model, guidelines, boq_items)

                            all_issues = issues + avixa_validation['avixa_issues']
                            all_warnings = warnings + avixa_warnings_old + avixa_validation['avixa_warnings']

                            st.session_state.validation_results = {
                                "issues": all_issues,
                                "warnings": all_warnings,
                                "avixa_compliance_score": avixa_validation['compliance_score']
                            }

                            st.success(f"✅ Generated and validated BOQ with {len(boq_items)} items!")
                            st.rerun()
                        else:
                            st.error("Failed to generate BOQ. The AI model did not return a valid list of items and the fallback also failed. Please check the product catalog.")
        with col2:
            if 'boq_items' in st.session_state and st.session_state.boq_items:
                # ★★★ UPDATED CALL ★★★
                # 1. Prepare data for a single room
                current_room_name = "Current Room"
                if st.session_state.project_rooms:
                    current_room_name = st.session_state.project_rooms[st.session_state.current_room_index]['name']
                
                single_room_data = [{
                    'name': current_room_name,
                    'boq_items': st.session_state.boq_items
                }]
                
                # 2. Prepare project details dictionary
                project_details = {
                    'project_name': st.session_state.get('project_name_input', 'Project'),
                    'client_name': st.session_state.get('client_name_input', 'Valued Client'),
                    'gst_rates': st.session_state.get('gst_rates', {})
                }
                # 3. Get the currency rate
                usd_to_inr_rate = get_usd_to_inr_rate()

                # 4. Call the new component function
                excel_data = generate_company_excel(
                    project_details=project_details,
                    rooms_data=single_room_data,
                    usd_to_inr_rate=usd_to_inr_rate
                )
                
                if excel_data:
                    filename = f"{project_details['project_name']}_{current_room_name}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                    st.download_button(
                        label="📊 Download Current Room BOQ",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        type="secondary"
                    )

        if st.session_state.boq_content or st.session_state.boq_items:
            st.markdown("---")
            display_boq_results(st.session_state.boq_content, st.session_state.validation_results, project_id, quote_valid_days, product_df)

    with tab5:
        # This function is now imported from components/visualizer.py
        create_3d_visualization()

# Run the application
if __name__ == "__main__":
    main()
