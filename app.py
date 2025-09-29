# app.py

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

# --- New Dependencies ---
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as ExcelImage
import requests
from PIL import Image as PILImage

# --- Import from components directory ---
try:
    from components.visualizer import create_3d_visualization, ROOM_SPECS
except ImportError:
    st.warning("Could not import 3D visualizer. Assuming dummy data for ROOM_SPECS.")
    ROOM_SPECS = {
        'Small Huddle Room (2-4 People)': {'area_sqft': (100, 200), 'recommended_display_size': (55, 65)},
        'Standard Conference Room (6-8 People)': {'area_sqft': (200, 400), 'recommended_display_size': (65, 75)},
        'Large Boardroom (10-16 People)': {'area_sqft': (400, 700), 'recommended_display_size': (75, 98)},
        'Training Room (20+ People)': {'area_sqft': (700, 1200), 'recommended_display_size': (86, 110)},
    }
    def create_3d_visualization():
        st.info("3D Visualization component not found.")

# --- ★★★ NEW: PRODUCTION-READY ROOM REQUIREMENTS ENGINE ★★★ ---
ROOM_TYPE_REQUIREMENTS = {
    'Small Huddle Room (2-4 People)': {
        'min_display_size': 50,
        'max_display_size': 65,
        'min_system_value': 3000,
        'max_system_value': 8000,
        'required_components': ['display', 'video_conferencing', 'mount', 'cables'],
        'video_conf_type': 'huddle_bar',
        'control_complexity': 'simple'
    },
    'Standard Conference Room (6-8 People)': {
        'min_display_size': 65,
        'max_display_size': 75,
        'min_system_value': 6000,
        'max_system_value': 15000,
        'required_components': ['display', 'video_conferencing', 'audio', 'control', 'mount', 'cables'],
        'video_conf_type': 'standard_bar',
        'control_complexity': 'medium'
    },
    'Large Boardroom (10-16 People)': {
        'min_display_size': 75,
        'max_display_size': 98,
        'min_system_value': 12000,
        'max_system_value': 30000,
        'required_components': ['display', 'video_conferencing', 'audio', 'control', 'mount', 'cables', 'infrastructure'],
        'video_conf_type': 'premium_system',
        'control_complexity': 'advanced'
    },
    'Training Room (20+ People)': {
        'min_display_size': 86,
        'max_display_size': 110,
        'min_system_value': 15000,
        'max_system_value': 50000,
        'required_components': ['display', 'video_conferencing', 'audio', 'control', 'mount', 'cables', 'infrastructure'],
        'video_conf_type': 'enterprise_system',
        'control_complexity': 'enterprise'
    }
}


# --- Page Configuration (Moved to login) ---

# --- Currency Conversion ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_usd_to_inr_rate():
    """Get current USD to INR exchange rate. Falls back to approximate rate if API fails."""
    try:
        # You can integrate a free API like exchangerate-api.com here
        # For now, using approximate rate
        return 83.5  # Approximate USD to INR rate - update this or use real API
    except:
        return 83.5  # Fallback rate

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
    
    # Filter out products with unrealistic prices (likely test data)
    # Keep products with prices between $100 and $50,000
    df = df[(df['price'] >= 100) & (df['price'] <= 50000)]
    
    # Clean category names - standardize to match your expected categories
    category_mapping = {
        'Displays & Projectors': 'Displays',
        'UC & Collaboration Devices': 'Video Conferencing', 
        'PTZ & Pro Video Cameras': 'Video Conferencing',
        'Audio: Microphones & Conferencing': 'Audio',
        'Audio: Speakers': 'Audio',
        'Audio: DSP': 'Audio',
        'Audio: Amplifiers': 'Audio',
        'Video Conferencing': 'Video Conferencing',
        'Control Systems & Processing': 'Control',
        'AV over IP': 'Control',
        'Video Equipment': 'Control',
        'Mounts & Racks': 'Mounts',
        'Cables & Connectivity': 'Cables',
        'Networking': 'Infrastructure',
        'Installation & Services': 'Services',
        'Wireless Presentation': 'Control',
        'Room Scheduling': 'Control',
        'Digital Signage': 'Displays',
        'Projection Screens': 'Displays'
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
            df['image_url'] = ''  # Will be populated later or manually
            validation_issues.append("Image URL column missing - images won't display in Excel")
            
        if 'gst_rate' not in df.columns:
            df['gst_rate'] = 18  # Default 18% GST for electronics
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
            model = genai.GenerativeModel('gemini-2.0-flash-lite-001')
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
            time.sleep(2 ** attempt)  # Exponential backoff
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
    detailed_screen_size = detailed_screen_height_ft * 12 / 0.49  # 16:9 conversion
    
    # For basic viewing (video): Screen height = viewing distance / 4  
    basic_screen_height_ft = max_viewing_distance / 4
    basic_screen_size = basic_screen_height_ft * 12 / 0.49
    
    # Audio Power Requirements (Enhanced)
    base_power_per_cubic_ft = 0.5
    if 'training' in room_type.lower() or 'presentation' in room_type.lower():
        base_power_per_cubic_ft = 0.75  # Higher for presentation spaces
    elif 'executive' in room_type.lower() or 'boardroom' in room_type.lower():
        base_power_per_cubic_ft = 1.0   # Highest for critical spaces
        
    audio_power_needed = int(room_volume * base_power_per_cubic_ft)
    
    # Lighting Requirements (AVIXA Standards)
    if 'conference' in room_type.lower():
        ambient_lighting = 200  # Lux
        presentation_lighting = 150  # Dimmed for displays
    elif 'training' in room_type.lower():
        ambient_lighting = 300  # Higher for note-taking
        presentation_lighting = 200
    else:
        ambient_lighting = 250  # General meeting spaces
        presentation_lighting = 175
    
    # Network Bandwidth (Realistic Calculations)
    estimated_people = min(room_area // 20, 50) if room_area > 0 else 1 # 20 sq ft per person max
    
    # Per-person bandwidth requirements
    hd_video_mbps = 2.5   # 1080p video conferencing
    uhd_video_mbps = 8.0   # 4K video conferencing  
    content_sharing_mbps = 5.0  # Wireless presentation
    
    recommended_bandwidth = int((hd_video_mbps * estimated_people) + content_sharing_mbps + 10)  # 10Mbps buffer
    
    # Power Load Calculations
    display_power = 250 if detailed_screen_size < 75 else 400  # Watts per display
    audio_system_power = 150 + (audio_power_needed * 0.3)  # Amplifiers + processing
    camera_power = 25
    network_power = 100  # Switches and codecs
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
    display_runs = 2  # HDMI + Power per display
    audio_runs = max(1, estimated_people // 3)  # Microphone coverage
    network_runs = 3 + max(1, estimated_people // 6)  # Control + cameras + wireless APs
    power_runs = 2 + max(1, total_av_power // 1000)  # Based on power zones
    
    # UPS Requirements (Based on Room Criticality)
    if 'executive' in room_type.lower() or 'boardroom' in room_type.lower():
        ups_runtime_minutes = 30
    elif 'training' in room_type.lower() or 'conference' in room_type.lower():
        ups_runtime_minutes = 15
    else:
        ups_runtime_minutes = 10
        
    ups_va_required = int(total_av_power * 1.4)  # 40% overhead for UPS sizing
    
    return {
        'detailed_viewing_display_size': int(detailed_screen_size),
        'basic_viewing_display_size': int(basic_screen_size),
        'max_viewing_distance': max_viewing_distance,
        'recommended_display_count': 2 if room_area > 300 else 1,
        'audio_power_needed': audio_power_needed,
        'microphone_coverage_zones': max(2, estimated_people // 4),
        'speaker_zones_required': max(2, int(room_area // 150)) if room_area > 0 else 1,
        'ambient_lighting_lux': ambient_lighting,
        'presentation_lighting_lux': presentation_lighting,
        'lighting_zones_required': max(2, int(room_area // 200)) if room_area > 0 else 1,
        'estimated_occupancy': estimated_people,
        'recommended_bandwidth_mbps': recommended_bandwidth,
        'total_power_load_watts': total_av_power,
        'circuit_requirement': circuit_requirement,
        'ups_va_required': ups_va_required,
        'ups_runtime_minutes': ups_runtime_minutes,
        'cable_runs': {'cat6a_network': network_runs, 'hdmi_video': display_runs, 'xlr_audio': audio_runs, 'power_circuits': power_runs},
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
    
    display_size = avixa_calcs['detailed_viewing_display_size']
    display_count = avixa_calcs['recommended_display_count']
    
    if display_size <= 55: display_type = "Commercial LED Display"
    elif display_size <= 75: display_type = "Large Format Display"  
    elif display_size <= 86: display_type = "Professional Large Format Display"
    else: display_type = "Video Wall or Laser Projector"
    
    requirements['displays'] = {
        'type': display_type,
        'size_inches': display_size,
        'quantity': display_count,
        'resolution': '4K' if display_size > 43 else '1080p',
        'mounting': 'Wall Mount' if display_size < 75 else 'Heavy Duty Wall Mount'
    }
    
    room_volume = (avixa_calcs['audio_power_needed'] / 0.5) if avixa_calcs['audio_power_needed'] > 0 else 1
    ceiling_height = technical_reqs.get('ceiling_height', 10)
    
    if room_volume < 2000:
        requirements['audio_system'] = {'type': 'All-in-One Video Bar', 'microphones': 'Integrated Beamforming Array', 'speakers': 'Integrated Speakers', 'dsp_required': False}
    elif room_volume < 5000:
        mic_solution = 'Tabletop Microphones' if ceiling_height < 9 else 'Ceiling Microphone Array'
        requirements['audio_system'] = {'type': 'Distributed Audio System', 'microphones': mic_solution, 'microphone_count': avixa_calcs['microphone_coverage_zones'], 'speakers': 'Ceiling Speakers', 'speaker_count': avixa_calcs['speaker_zones_required'], 'amplifier': 'Multi-Channel Amplifier', 'dsp_required': True, 'dsp_type': 'Basic DSP with AEC'}
    else:
        requirements['audio_system'] = {'type': 'Professional Audio System', 'microphones': 'Steerable Ceiling Array', 'microphone_count': avixa_calcs['microphone_coverage_zones'], 'speakers': 'Distributed Ceiling System', 'speaker_count': avixa_calcs['speaker_zones_required'], 'amplifier': 'Networked Amplifier System', 'dsp_required': True, 'dsp_type': 'Advanced DSP with Dante/AVB', 'voice_lift': room_volume > 8000}
    
    if avixa_calcs['estimated_occupancy'] <= 6: camera_type = 'Fixed Wide-Angle Camera'
    elif avixa_calcs['estimated_occupancy'] <= 12: camera_type = 'PTZ Camera with Auto-Framing'
    else: camera_type = 'Multi-Camera System with Tracking'
    requirements['video_system'] = {'camera_type': camera_type, 'camera_count': 1 if avixa_calcs['estimated_occupancy'] <= 12 else 2, '4k_required': avixa_calcs['estimated_occupancy'] > 8}
    
    if room_volume < 2000: control_type = 'Native Room System Control'
    elif room_volume < 5000: control_type = 'Touch Panel Control'
    else: control_type = 'Advanced Programmable Control System'
    requirements['control_system'] = {'type': control_type, 'touch_panel_size': '7-inch' if room_volume < 3000 else '10-inch', 'integration_required': room_volume > 5000}
    
    requirements['infrastructure'] = {'equipment_rack': 'Wall-Mount' if room_volume < 3000 else 'Floor-Standing', 'rack_size': '6U' if room_volume < 3000 else '12U' if room_volume < 8000 else '24U', 'cooling_required': avixa_calcs['total_power_load_watts'] > 1500, 'ups_required': True, 'cable_management': 'Standard' if room_volume < 5000 else 'Professional'}
    
    if avixa_calcs['requires_ada_compliance']: requirements['compliance'].extend(['ADA Compliant Touch Panels (15-48" height)', 'Visual Notification System'])
    if avixa_calcs['requires_hearing_loop']: requirements['compliance'].append('Hearing Loop System')
    if avixa_calcs['requires_assistive_listening']: requirements['compliance'].append('FM/IR Assistive Listening (4% of capacity)')
    
    return requirements

# --- HELPER FUNCTIONS FOR ENHANCED BOQ GENERATION ---
def get_curated_products_by_category(product_df, category, max_products=15):
    """Get curated, realistic products for a specific category."""
    if product_df is None or len(product_df) == 0:
        return pd.DataFrame()
    
    cat_df = product_df[product_df['category'] == category].copy()
    if len(cat_df) == 0:
        return pd.DataFrame()
    
    known_brands = ['Samsung', 'LG', 'Sony', 'Poly', 'Logitech', 'Cisco', 'Shure', 'QSC', 'Extron', 'Crestron', 'Chief', 'Kramer', 'Biamp']
    cat_df['brand_score'] = cat_df['brand'].apply(lambda x: known_brands.index(x) if x in known_brands else 999)
    cat_df = cat_df.sort_values(['brand_score', 'price'])
    return cat_df.head(max_products)

def validate_essential_components(boq_items):
    """Validate that BOQ has essential components for a functional AV system."""
    if not boq_items:
        return False
    categories_found = [item.get('category', '').lower() for item in boq_items]
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

# --- ★★★ NEW: PRODUCTION-READY VALIDATION & GENERATION FUNCTIONS (REPLACED) ★★★ ---
def validate_boq_completeness_and_pricing(boq_items, product_df, room_type, budget_tier):
    """Comprehensive BOQ validation for production deployment."""
    issues = []
    warnings = []
    corrected_items = []
    
    # Get room requirements
    room_reqs = ROOM_TYPE_REQUIREMENTS.get(room_type, {})
    
    # Price validation by category (stricter ranges)
    price_ranges = {
        'Displays': {'min': 900, 'max': 12000},
        'Video Conferencing': {'min': 400, 'max': 7000}, 
        'Audio': {'min': 60, 'max': 2500},
        'Control': {'min': 200, 'max': 4000},
        'Mounts': {'min': 80, 'max': 600},
        'Cables': {'min': 15, 'max': 150},  # Much stricter cable pricing
        'Infrastructure': {'min': 150, 'max': 1500}
    }
    
    # Budget tier multipliers
    tier_multipliers = {
        'Economy': 0.8,
        'Standard': 1.0,
        'Premium': 1.4,
        'Enterprise': 1.8
    }
    multiplier = tier_multipliers.get(budget_tier, 1.0)
    
    total_value = 0
    categories_present = set()
    
    for item in boq_items:
        category = item.get('category', 'General')
        price = item.get('price', 0)
        name = item.get('name', '')
        brand = item.get('brand', '')
        quantity = item.get('quantity', 1)
        
        categories_present.add(category.lower())
        
        # Validate pricing against realistic ranges
        if category in price_ranges:
            min_price = price_ranges[category]['min']
            max_price = price_ranges[category]['max'] * multiplier
            
            if price < min_price or price > max_price:
                replacement = find_suitable_replacement(category, name, brand, product_df, min_price, max_price)
                if replacement:
                    corrected_items.append({
                        **item,
                        'name': replacement['name'],
                        'brand': replacement['brand'],
                        'price': replacement['price'],
                        'specifications': replacement.get('features', item.get('specifications', '')),
                        'matched': True
                    })
                    warnings.append(f"Replaced {name} (${price:,.0f}) with {replacement['name']} (${replacement['price']:,.0f})")
                else:
                    issues.append(f"CRITICAL: No suitable replacement found for {name} - price ${price:,.0f} unrealistic")
                    corrected_items.append(item)
            else:
                corrected_items.append(item)
        else:
            corrected_items.append(item)
        
        total_value += price * quantity
    
    # Validate system completeness based on room type
    required_components = room_reqs.get('required_components', [])
    for req_component in required_components:
        component_found = False
        for category in categories_present:
            if req_component in category or any(req_component in cat for cat in ['display', 'video', 'audio', 'control', 'mount', 'cable', 'infrastructure']):
                component_found = True
                break
        
        if not component_found:
            issues.append(f"CRITICAL: Missing required component for {room_type}: {req_component}")
    
    # Validate total system value
    min_value = room_reqs.get('min_system_value', 2000) * multiplier
    max_value = room_reqs.get('max_system_value', 50000) * multiplier
    
    if total_value < min_value:
        warnings.append(f"System value ${total_value:,.0f} seems low for {room_type} (expected ${min_value:,.0f}+)")
    elif total_value > max_value:
        warnings.append(f"System value ${total_value:,.0f} seems high for {room_type} (expected <${max_value:,.0f})")
    
    # Validate display size for room type
    display_items = [item for item in corrected_items if 'display' in item.get('category', '').lower()]
    if display_items:
        for display in display_items:
            size_match = re.search(r'(\d+)"', display.get('name', ''))
            if size_match:
                size = int(size_match.group(1))
                min_size = room_reqs.get('min_display_size', 40)
                max_size = room_reqs.get('max_display_size', 100)
                
                if size < min_size:
                    issues.append(f"CRITICAL: Display size {size}\" too small for {room_type} (minimum {min_size}\")")
                elif size > max_size:
                    warnings.append(f"Display size {size}\" may be too large for {room_type} (recommended max {max_size}\")")
    
    return corrected_items, issues, warnings, total_value

def find_suitable_replacement(category, original_name, original_brand, product_df, min_price, max_price):
    """Find appropriate replacement products with intelligent matching."""
    if product_df is None or len(product_df) == 0:
        return None
    
    # Filter suitable products
    suitable = product_df[
        (product_df['category'] == category) & 
        (product_df['price'] >= min_price) & 
        (product_df['price'] <= max_price)
    ].copy()
    
    if len(suitable) == 0:
        return None
    
    # Prioritize by brand match, then by price similarity
    if original_brand and original_brand != 'Unknown':
        brand_matches = suitable[suitable['brand'].str.contains(original_brand, case=False, na=False)]
        if len(brand_matches) > 0:
            return brand_matches.iloc[0].to_dict()
    
    # For displays, match size if possible
    if category == 'Displays' and original_name:
        size_match = re.search(r'(\d+)"', original_name)
        if size_match:
            target_size = int(size_match.group(1))
            for _, product in suitable.iterrows():
                product_size_match = re.search(r'(\d+)"', product['name'])
                if product_size_match and abs(int(product_size_match.group(1)) - target_size) <= 10:
                    return product.to_dict()
    
    # Return closest price match
    return suitable.iloc[0].to_dict()

def build_room_appropriate_catalog(product_df, room_type, budget_tier, equipment_reqs):
    """Build a curated catalog appropriate for the specific room type and budget."""
    catalog = ""
    
    # Display size filtering based on room requirements
    room_reqs = ROOM_TYPE_REQUIREMENTS.get(room_type, {})
    min_display_size = room_reqs.get('min_display_size', 40)
    max_display_size = room_reqs.get('max_display_size', 100)
    
    # Get displays in appropriate size range
    displays = product_df[product_df['category'] == 'Displays'].copy()
    suitable_displays = []
    
    for _, display in displays.iterrows():
        size_match = re.search(r'(\d+)"', display['name'])
        if size_match:
            size = int(size_match.group(1))
            if min_display_size <= size <= max_display_size:
                suitable_displays.append(display)
    
    if suitable_displays:
        catalog += "\n--- DISPLAYS (ROOM-APPROPRIATE SIZES) ---\n"
        for display in suitable_displays[:5]:  # Top 5 options
            catalog += f"• {display['brand']} - {display['name']} - ${display['price']:.0f}\n"
    
    # Video conferencing based on room type
    vc_products = get_curated_products_by_category(product_df, 'Video Conferencing', 8)
    if len(vc_products) > 0:
        catalog += "\n--- VIDEO CONFERENCING ---\n"
        for _, vc in vc_products.iterrows():
            catalog += f"• {vc['brand']} - {vc['name']} - ${vc['price']:.0f}\n"
    
    # Other essential categories
    for category in ['Audio', 'Control', 'Mounts', 'Cables']:
        products = get_curated_products_by_category(product_df, category, 5)
        if len(products) > 0:
            catalog += f"\n--- {category.upper()} ---\n"
            for _, product in products.iterrows():
                catalog += f"• {product['brand']} - {product['name']} - ${product['price']:.0f}\n"
    
    return catalog

def create_comprehensive_fallback_boq(product_df, room_type, equipment_reqs, avixa_calcs):
    """Create a comprehensive fallback BOQ that meets all room requirements."""
    items = []
    room_reqs = ROOM_TYPE_REQUIREMENTS.get(room_type, {})
    
    # Essential display
    displays = get_curated_products_by_category(product_df, 'Displays', 10)
    target_size = equipment_reqs['displays']['size_inches']
    min_size = room_reqs.get('min_display_size', 50)
    max_size = room_reqs.get('max_display_size', 100)
    
    best_display = None
    for _, display in displays.iterrows():
        size_match = re.search(r'(\d+)"', display['name'])
        if size_match:
            size = int(size_match.group(1))
            if min_size <= size <= max_size:
                best_display = display
                break
    
    if best_display is not None:
        items.append({
            'category': 'Displays', 'name': best_display['name'], 'brand': best_display['brand'], 'quantity': 1, 'price': float(best_display['price']),
            'justification': f'Primary display for {room_type}', 'specifications': best_display.get('features', ''), 'matched': True
        })
    
    # Video conferencing based on room complexity
    vc_products = get_curated_products_by_category(product_df, 'Video Conferencing', 10)
    occupancy = avixa_calcs['estimated_occupancy']
    
    best_vc = None
    if occupancy <= 6:
        for _, vc in vc_products.iterrows():
            if any(term in vc['name'].lower() for term in ['x30', 'huddle', 'small']):
                best_vc = vc; break
    elif occupancy <= 12:
        for _, vc in vc_products.iterrows():
            if any(term in vc['name'].lower() for term in ['x52', 'rally bar', 'a30']):
                best_vc = vc; break
    else:
        for _, vc in vc_products.iterrows():
            if any(term in vc['name'].lower() for term in ['x70', 'plus', 'enterprise', 'codec']):
                best_vc = vc; break
    
    if best_vc is None and len(vc_products) > 0:
        best_vc = vc_products.iloc[0]
    
    if best_vc is not None:
        items.append({
            'category': 'Video Conferencing', 'name': best_vc['name'], 'brand': best_vc['brand'], 'quantity': 1, 'price': float(best_vc['price']),
            'justification': f'Video conferencing for {occupancy}-person room', 'specifications': best_vc.get('features', ''), 'matched': True
        })
    
    # Add essential accessories
    for category, justification in [('Mounts', 'Display mounting'), ('Cables', 'System connectivity'), ('Control', 'Room control interface')]:
        products = get_curated_products_by_category(product_df, category, 5)
        if len(products) > 0:
            product = products.iloc[0]
            items.append({
                'category': category, 'name': product['name'], 'brand': product['brand'], 'quantity': 1, 'price': float(product['price']),
                'justification': justification, 'specifications': product.get('features', ''), 'matched': True
            })
    
    return items

def perform_final_quality_check(boq_items, room_type, budget_tier):
    """Perform final quality check before marking BOQ as production-ready."""
    errors = []
    warnings = []
    
    room_reqs = ROOM_TYPE_REQUIREMENTS.get(room_type, {})
    total_value = sum(item.get('price', 0) * item.get('quantity', 1) for item in boq_items)
    
    if len(boq_items) < 4: errors.append(f"BOQ too incomplete - only {len(boq_items)} items (minimum 4 required)")
    
    min_value = room_reqs.get('min_system_value', 2000)
    max_value = room_reqs.get('max_system_value', 50000)
    
    if total_value < min_value * 0.8: errors.append(f"System value too low: ${total_value:,.0f} (minimum ${min_value:,.0f})")
    elif total_value > max_value * 1.5: errors.append(f"System value too high: ${total_value:,.0f} (maximum ${max_value:,.0f})")
    
    categories = {item.get('category', '').lower() for item in boq_items}
    required_categories = ['displays', 'video conferencing']
    
    for req_cat in required_categories:
        if not any(req_cat in cat for cat in categories):
            errors.append(f"Missing essential category: {req_cat}")
    
    for item in boq_items:
        price = item.get('price', 0)
        category = item.get('category', '')
        if category == 'Cables' and price > 200: errors.append(f"Cable pricing unrealistic: ${price:,.0f}")
        elif category == 'Mounts' and price > 1000: errors.append(f"Mount pricing unrealistic: ${price:,.0f}")
        elif price > 15000: errors.append(f"Individual item price too high: ${price:,.0f}")
    
    return {'production_ready': len(errors) == 0, 'errors': errors, 'warnings': warnings, 'total_value': total_value, 'item_count': len(boq_items)}

def generate_production_ready_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Production-ready BOQ generation with comprehensive validation."""
    
    clean_df = clean_and_validate_product_data(product_df)
    if clean_df is None or len(clean_df) == 0:
        st.error("Invalid product catalog - cannot generate BOQ")
        return None, [], None, None
    
    length = room_area**0.5 if room_area > 0 else 20
    width = room_area / length if length > 0 else 16
    avixa_calcs = calculate_avixa_recommendations(length, width, technical_reqs.get('ceiling_height', 10), room_type)
    equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    
    room_reqs = ROOM_TYPE_REQUIREMENTS.get(room_type, {})
    
    curated_catalog = build_room_appropriate_catalog(clean_df, room_type, budget_tier, equipment_reqs)
    
    if not curated_catalog:
        st.error("Insufficient product catalog for selected room type")
        return None, [], avixa_calcs, equipment_reqs
    
    enhanced_prompt = f"""
You are an AV systems engineer designing a complete system for a {room_type}.

ROOM SPECIFICATIONS:
- Area: {room_area} sq ft ({avixa_calcs['estimated_occupancy']} people)
- Required display size: {equipment_reqs['displays']['size_inches']}"
- Budget tier: {budget_tier}
- Must include: {', '.join(room_reqs.get('required_components', []))}

AVAILABLE PRODUCTS (USE EXACT NAMES AND PRICES):
{curated_catalog}

REQUIREMENTS:
1. Create a COMPLETE functional AV system
2. Use ONLY products from the list above
3. Include ALL required components for the room type
4. Match exact product names and pricing
5. System must be worth ${room_reqs.get('min_system_value', 3000)} - ${room_reqs.get('max_system_value', 15000)}

MANDATORY TABLE FORMAT:
| Category | Make | Model No. | Specifications | Qty | Unit Price (USD) | Remarks |
|---|---|---|---|---|---|---|

Generate a complete professional BOQ now:
"""
    
    try:
        response = generate_with_retry(model, enhanced_prompt)
        if response and response.text:
            boq_content = response.text.strip()
            boq_items = extract_enhanced_boq_items(boq_content, clean_df)
            
            corrected_items, issues, warnings, total_value = validate_boq_completeness_and_pricing(
                boq_items, clean_df, room_type, budget_tier
            )
            
            if issues:
                st.error("CRITICAL BOQ ISSUES - NOT PRODUCTION READY:")
                for issue in issues: st.write(f"- {issue}")
                st.write("**System requires manual review before client delivery**")
            
            if warnings:
                st.warning("BOQ Warnings:")
                for warning in warnings: st.write(f"- {warning}")
            
            if len(corrected_items) < len(room_reqs.get('required_components', [])):
                st.info("Adding missing essential components...")
                fallback_items = create_comprehensive_fallback_boq(clean_df, room_type, equipment_reqs, avixa_calcs)
                corrected_items.extend(fallback_items)
                corrected_items = remove_duplicate_boq_items(corrected_items)
            
            final_validation = perform_final_quality_check(corrected_items, room_type, budget_tier)
            if not final_validation['production_ready']:
                st.error("BOQ FAILED FINAL QUALITY CHECK - NOT READY FOR PRODUCTION")
                for error in final_validation['errors']: st.write(f"- {error}")
            else:
                st.success(f"BOQ passed quality checks - Production ready with {len(corrected_items)} items")
            
            return boq_content, corrected_items, avixa_calcs, equipment_reqs
            
    except Exception as e:
        st.error(f"BOQ generation failed: {str(e)}")
    
    fallback_items = create_comprehensive_fallback_boq(clean_df, room_type, equipment_reqs, avixa_calcs)
    return None, fallback_items, avixa_calcs, equipment_reqs

# --- BOQ Validation & Data Extraction ---
class BOQValidator:
    def __init__(self, room_specs, product_df):
        self.room_specs = room_specs
        self.product_df = product_df
    
    def validate_technical_requirements(self, boq_items, room_type, room_area=None):
        issues = []
        warnings = []
        
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            room_spec = self.room_specs.get(room_type, {})
            recommended_size = room_spec.get('recommended_display_size', (32, 98))
            for display in displays:
                size_match = re.search(r'(\d+)"', display.get('name', ''))
                if size_match:
                    size = int(size_match.group(1))
                    if size < recommended_size[0]: warnings.append(f"Display size {size}\" may be too small for {room_type}")
                    elif size > recommended_size[1]: warnings.append(f"Display size {size}\" may be too large for {room_type}")
        
        essential_categories = ['display', 'audio', 'control']
        found_categories = [item.get('category', '').lower() for item in boq_items]
        for essential in essential_categories:
            if not any(essential in cat for cat in found_categories):
                issues.append(f"Missing essential component: {essential}")
        
        total_estimated_power = len(boq_items) * 150
        if total_estimated_power > 1800:
            warnings.append("System may require a dedicated 20A circuit")
        
        return issues, warnings

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

def validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs):
    """Validate BOQ against AVIXA standards and compliance requirements."""
    issues = []
    warnings = []
    
    displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
    if not displays:
        issues.append("CRITICAL: No display found in BOQ")
    else:
        for display in displays:
            size_match = re.search(r'(\d+)"', display.get('name', ''))
            if size_match:
                size = int(size_match.group(1))
                recommended_size = avixa_calcs['detailed_viewing_display_size']
                if abs(size - recommended_size) > 10:
                    warnings.append(f"Display size {size}\" deviates from AVIXA calculation ({recommended_size}\")")
    
    has_dsp = any('dsp' in item.get('name', '').lower() or 'processor' in item.get('name', '').lower() for item in boq_items)
    if equipment_reqs['audio_system'].get('dsp_required') and not has_dsp:
        issues.append("CRITICAL: DSP required but not found in BOQ")
    
    total_estimated_power = sum(item.get('power_draw', 150) * item.get('quantity', 1) for item in boq_items if 'service' not in item.get('category', '').lower())
    if total_estimated_power > avixa_calcs['total_power_load_watts'] * 1.2:
        warnings.append(f"Power consumption ({total_estimated_power}W) exceeds AVIXA calculation")
    
    has_ups = any('ups' in item.get('name', '').lower() for item in boq_items)
    if avixa_calcs['ups_va_required'] > 1000 and not has_ups:
        issues.append("CRITICAL: UPS system required but not found in BOQ")
    
    cable_categories = ['cable', 'wire', 'connect']
    has_adequate_cables = any(any(cable_cat in item.get('category', '').lower() for cable_cat in cable_categories) for item in boq_items)
    if not has_adequate_cables:
        warnings.append("Cable infrastructure may be inadequate for calculated runs")
    
    if avixa_calcs['requires_ada_compliance']:
        ada_items = [item for item in boq_items if any(term in item.get('name', '').lower() for term in ['assistive', 'ada', 'hearing', 'loop'])]
        if not ada_items:
            issues.append("CRITICAL: ADA compliance required but no assistive devices in BOQ")
    
    return {
        'avixa_issues': issues, 'avixa_warnings': warnings, 'compliance_score': max(0, 100 - (len(issues) * 25) - (len(warnings) * 5)),
        'avixa_calculations_used': avixa_calcs, 'equipment_requirements_met': equipment_reqs
    }

def estimate_power_draw(category, name):
    """Estimate power draw based on equipment category and name."""
    name_lower = name.lower(); category_lower = category.lower()
    if 'display' in category_lower:
        if any(size in name_lower for size in ['55', '60', '65']): return 200
        elif any(size in name_lower for size in ['70', '75', '80']): return 300
        elif any(size in name_lower for size in ['85', '90', '95', '98']): return 400
        else: return 150
    elif 'audio' in category_lower:
        if 'amplifier' in name_lower: return 300
        elif 'speaker' in name_lower: return 60
        elif 'microphone' in name_lower: return 15
        else: return 50
    elif 'video conferencing' in category_lower:
        if 'rally' in name_lower or 'bar' in name_lower: return 90
        elif 'camera' in name_lower: return 25
        else: return 40
    elif 'control' in category_lower: return 75
    else: return 25

# --- Enhanced BOQ Item Extraction ---
def extract_enhanced_boq_items(boq_content, product_df):
    """Extract BOQ items from AI response based on new company format."""
    items = []
    lines = boq_content.split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        if '|' in line and any(keyword in line.lower() for keyword in ['category', 'make', 'model', 'specifications']):
            in_table = True; continue
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 6:
                category = parts[0]; brand = parts[1]; product_name = parts[2]; specifications = parts[3]; remarks = parts[6] if len(parts) > 6 else "Essential AV system component."
                try: quantity = int(parts[4])
                except (ValueError, IndexError): quantity = 1
                try: price = float(parts[5].replace('$', '').replace(',', ''))
                except (ValueError, IndexError): price = 0
                
                matched_product = match_product_in_database(product_name, brand, product_df)
                if matched_product is not None:
                    price = float(matched_product.get('price', price)); actual_brand = matched_product.get('brand', brand)
                    actual_category = matched_product.get('category', category); actual_name = matched_product.get('name', product_name)
                    image_url = matched_product.get('image_url', ''); gst_rate = matched_product.get('gst_rate', 18)
                else:
                    actual_brand = brand; actual_category = normalize_category(category, product_name); actual_name = product_name
                    image_url = ''; gst_rate = 18
                
                items.append({
                    'category': actual_category, 'name': actual_name, 'brand': actual_brand, 'quantity': quantity, 'price': price,
                    'justification': remarks, 'specifications': specifications, 'image_url': image_url, 'gst_rate': gst_rate,
                    'matched': matched_product is not None, 'power_draw': estimate_power_draw(actual_category, actual_name)
                })
            elif in_table and not line.startswith('|'):
                in_table = False
    return items

# --- Enhanced Product Matching ---
def match_product_in_database(product_name, brand, product_df):
    """Enhanced product matching with better validation."""
    if product_df is None or len(product_df) == 0: return None
    try:
        safe_product_name = str(product_name).strip() if product_name else ""
        safe_brand = str(brand).strip() if brand else ""
        if not safe_product_name and not safe_brand: return None
        if safe_product_name:
            exact_matches = product_df[product_df['name'].astype(str).str.lower() == safe_product_name.lower()]
            if len(exact_matches) > 0: return exact_matches.iloc[0].to_dict()
        if safe_brand and safe_product_name:
            brand_matches = product_df[product_df['brand'].astype(str).str.lower() == safe_brand.lower()]
            if len(brand_matches) > 0:
                name_matches = brand_matches[brand_matches['name'].astype(str).str.contains(re.escape(safe_product_name.split()[0]), case=False, na=False)]
                if len(name_matches) > 0: return name_matches.iloc[0].to_dict()
        if safe_product_name and len(safe_product_name) > 3:
            key_terms = safe_product_name.lower().split()[:3]
            for term in key_terms:
                if len(term) > 3:
                    matches = product_df[product_df['name'].astype(str).str.contains(re.escape(term), case=False, na=False)]
                    if len(matches) > 0: return matches.iloc[0].to_dict()
        return None
    except Exception as e: return None

def normalize_category(category_text, product_name):
    """Normalize category names to standard categories."""
    category_lower = category_text.lower(); product_lower = product_name.lower()
    if any(term in category_lower or term in product_lower for term in ['display', 'monitor', 'screen', 'projector', 'tv']): return 'Displays'
    elif any(term in category_lower or term in product_lower for term in ['audio', 'speaker', 'microphone', 'sound', 'amplifier']): return 'Audio'
    elif any(term in category_lower or term in product_lower for term in ['video', 'conferencing', 'camera', 'codec', 'rally']): return 'Video Conferencing'
    elif any(term in category_lower or term in product_lower for term in ['control', 'processor', 'switch', 'matrix']): return 'Control'
    elif any(term in category_lower or term in product_lower for term in ['mount', 'bracket', 'rack', 'stand']): return 'Mounts'
    elif any(term in category_lower or term in product_lower for term in ['cable', 'connect', 'wire', 'hdmi', 'usb']): return 'Cables'
    else: return 'General'

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
        recommended_type = None
        for room_type, specs in ROOM_SPECS.items():
            if specs["area_sqft"][0] <= room_area <= specs["area_sqft"][1]:
                recommended_type = room_type; break
        if recommended_type: st.success(f"Recommended Room Type: {recommended_type}")
        else: st.warning("Room size is outside typical ranges")
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


# --- Multi-Room Interface ---
def create_multi_room_interface():
    """Interface for managing multiple rooms in a project."""
    st.subheader("Multi-Room Project Management")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1: room_name = st.text_input("New Room Name", value=f"Room {len(st.session_state.project_rooms) + 1}")
    with col2:
        st.write(""); st.write("")
        if st.button("➕ Add New Room to Project", type="primary", use_container_width=True):
            new_room = {
                'name': room_name, 'type': st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)'),
                'area': st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16),
                'boq_items': [], 'features': st.session_state.get('features_text_area', ''), 'technical_reqs': {}
            }
            st.session_state.project_rooms.append(new_room)
            st.success(f"Added '{room_name}' to the project."); st.rerun()
    with col3:
        st.write(""); st.write("")
        if st.session_state.project_rooms:
            excel_data = generate_company_excel(rooms_data=st.session_state.project_rooms)
            project_name = st.session_state.get('project_name_input', 'Multi_Room_Project')
            filename = f"{project_name}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
            st.download_button(label="📊 Download Full Project BOQ", data=excel_data, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")

    if st.session_state.project_rooms:
        st.markdown("---"); st.write("**Current Project Rooms:**")
        previous_room_index = st.session_state.current_room_index
        if previous_room_index < len(st.session_state.project_rooms):
            st.session_state.project_rooms[previous_room_index]['boq_items'] = st.session_state.boq_items
        room_options = [room['name'] for room in st.session_state.project_rooms]
        try: current_index = st.session_state.current_room_index
        except (AttributeError, IndexError): current_index = 0; st.session_state.current_room_index = 0
        if current_index >= len(room_options): current_index = 0; st.session_state.current_room_index = 0
        selected_room_name = st.selectbox("Select a room to view or edit its BOQ:", options=room_options, index=current_index, key="room_selector")
        new_index = room_options.index(selected_room_name)
        if new_index != st.session_state.current_room_index:
            st.session_state.current_room_index = new_index
            selected_room_boq = st.session_state.project_rooms[new_index].get('boq_items', [])
            st.session_state.boq_items = selected_room_boq
            update_boq_content_with_current_items(); st.rerun()
        selected_room = st.session_state.project_rooms[st.session_state.current_room_index]
        st.info(f"You are currently editing **{selected_room['name']}**. Any generated or edited BOQ will be saved for this room.")
        if st.button(f"🗑️ Remove '{selected_room['name']}' from Project", type="secondary"):
            st.session_state.project_rooms.pop(st.session_state.current_room_index)
            st.session_state.current_room_index = 0
            st.session_state.boq_items = st.session_state.project_rooms[0].get('boq_items', []) if st.session_state.project_rooms else []
            st.rerun()


# --- BOQ Display and Editing ---
def update_boq_content_with_current_items():
    """Update the BOQ content in session state to reflect current items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.session_state.boq_content = "## Bill of Quantities\n\nNo items added yet."; return
    boq_content = "## Bill of Quantities\n\n| Category | Make | Model No. | Specifications | Qty | Unit Price (USD) | Remarks |\n|---|---|---|---|---|---|---|\n"
    total_cost = 0
    for item in st.session_state.boq_items:
        quantity = item.get('quantity', 1); price = item.get('price', 0); total_cost += quantity * price
        boq_content += f"| {item.get('category', 'N/A')} | {item.get('brand', 'N/A')} | {item.get('name', 'N/A')} | {item.get('specifications', '')} | {quantity} | ${price:,.2f} | {item.get('justification', '')} |\n"
    st.session_state.boq_content = boq_content

def display_boq_results(boq_content, validation_results, project_id, quote_valid_days, product_df):
    """Display BOQ results with interactive editing capabilities."""
    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    st.subheader(f"Generated Bill of Quantities ({item_count} items)")
    if validation_results and validation_results.get('issues'):
        st.error("Critical Issues Found:"); [st.write(f"- {issue}") for issue in validation_results['issues']]
    if validation_results and validation_results.get('warnings'):
        st.warning("Technical Recommendations & Compliance Notes:"); [st.write(f"- {warning}") for warning in validation_results['warnings']]
    if boq_content: st.markdown(boq_content)
    else: st.info("No BOQ content generated yet. Use the interactive editor below.")
    if 'boq_items' in st.session_state and st.session_state.boq_items:
        currency = st.session_state.get('currency', 'USD')
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
        if currency == 'INR':
            display_total = convert_currency(total_cost * 1.30, 'INR')
            st.metric("Estimated Project Total", format_currency(display_total, 'INR'), help="Includes installation, warranty, and contingency")
        else: st.metric("Estimated Project Total", format_currency(total_cost * 1.30, 'USD'), help="Includes installation, warranty, and contingency")
    st.markdown("---"); create_interactive_boq_editor(product_df)

def create_interactive_boq_editor(product_df):
    """Create interactive BOQ editing interface."""
    st.subheader("Interactive BOQ Editor")
    item_count = len(st.session_state.boq_items) if 'boq_items' in st.session_state else 0
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Items in BOQ", item_count)
    with col2:
        if 'boq_items' in st.session_state and st.session_state.boq_items:
            total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in st.session_state.boq_items)
            currency = st.session_state.get('currency', 'USD')
            if currency == 'INR':
                display_total = convert_currency(total_cost, 'INR'); st.metric("Hardware Subtotal", format_currency(display_total, 'INR'))
            else: st.metric("Hardware Subtotal", format_currency(total_cost, 'USD'))
        else: st.metric("Subtotal", "₹0" if st.session_state.get('currency', 'USD') == 'INR' else "$0")
    with col3:
        if st.button("🔄 Refresh BOQ Display", help="Update the main BOQ display with current items"):
            update_boq_content_with_current_items(); st.rerun()
    if product_df is None: st.error("Cannot load product catalog for editing."); return
    currency = st.session_state.get('currency', 'USD')
    tabs = st.tabs(["Edit Current BOQ", "Add Products", "Product Search"])
    with tabs[0]: edit_current_boq(currency)
    with tabs[1]: add_products_interface(product_df, currency)
    with tabs[2]: product_search_interface(product_df, currency)

def edit_current_boq(currency):
    """Interface for editing current BOQ items."""
    if 'boq_items' not in st.session_state or not st.session_state.boq_items:
        st.info("No BOQ items loaded. Generate a BOQ or add products manually."); return
    st.write(f"**Current BOQ Items ({len(st.session_state.boq_items)} items):**")
    items_to_remove = []
    for i, item in enumerate(st.session_state.boq_items):
        with st.expander(f"{str(item.get('category', 'General'))} - {str(item.get('name', 'Unknown'))[:50]}..."):
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
                try: safe_quantity = max(1, int(float(item.get('quantity', 1))))
                except (ValueError, TypeError): safe_quantity = 1
                new_quantity = st.number_input("Quantity", min_value=1, value=safe_quantity, key=f"qty_{i}")
                try: current_price = float(item.get('price', 0))
                except (ValueError, TypeError): current_price = 0
                display_price = convert_currency(current_price, 'INR') if currency == 'INR' else current_price
                new_price = st.number_input(f"Unit Price ({currency})", min_value=0.0, value=float(display_price), key=f"price_{i}")
                stored_price = new_price / get_usd_to_inr_rate() if currency == 'INR' else new_price
            with col4:
                total_price = stored_price * new_quantity
                display_total = convert_currency(total_price, 'INR') if currency == 'INR' else total_price
                st.metric("Total", format_currency(display_total, currency))
                if st.button("Remove", key=f"remove_{i}", type="secondary"): items_to_remove.append(i)
            st.session_state.boq_items[i].update({'name': new_name, 'brand': new_brand, 'category': new_category, 'quantity': new_quantity, 'price': stored_price})
    if items_to_remove:
        for index in sorted(items_to_remove, reverse=True): st.session_state.boq_items.pop(index)
        st.rerun()

def add_products_interface(product_df, currency):
    """Interface for adding new products to BOQ."""
    st.write("**Add Products to BOQ:**"); col1, col2 = st.columns([2, 1])
    with col1:
        categories = ['All'] + sorted(list(product_df['category'].unique()))
        selected_category = st.selectbox("Filter by Category", categories, key="add_category_filter")
        filtered_df = product_df[product_df['category'] == selected_category] if selected_category != 'All' else product_df
        product_options = [f"{row['brand']} - {row['name']}" for _, row in filtered_df.iterrows()]
        if not product_options: st.warning("No products found."); return
        selected_product_str = st.selectbox("Select Product", product_options, key="add_product_select")
        selected_product = next((row for _, row in filtered_df.iterrows() if f"{row['brand']} - {row['name']}" == selected_product_str), None)
    with col2:
        if selected_product is not None:
            quantity = st.number_input("Quantity", min_value=1, value=1, key="add_product_qty")
            base_price = float(selected_product.get('price', 0))
            display_price = convert_currency(base_price, 'INR') if currency == 'INR' else base_price
            st.metric("Unit Price", format_currency(display_price, currency)); st.metric("Total", format_currency(display_price * quantity, currency))
            if st.button("Add to BOQ", type="primary"):
                new_item = {
                    'category': selected_product.get('category', 'General'), 'name': selected_product.get('name', ''), 'brand': selected_product.get('brand', ''), 'quantity': quantity, 'price': base_price,
                    'justification': 'Manually added component.', 'specifications': selected_product.get('features', ''), 'image_url': selected_product.get('image_url', ''), 'gst_rate': selected_product.get('gst_rate', 18), 'matched': True
                }
                st.session_state.boq_items.append(new_item); update_boq_content_with_current_items()
                st.success(f"Added {quantity}x {selected_product['name']}!"); st.rerun()

def product_search_interface(product_df, currency):
    """Advanced product search interface."""
    st.write("**Search Product Catalog:**")
    search_term = st.text_input("Search products...", placeholder="Enter name, brand, or features", key="search_term_input")
    if search_term:
        search_cols = ['name', 'brand', 'features']
        mask = product_df[search_cols].apply(lambda x: x.astype(str).str.contains(search_term, case=False, na=False)).any(axis=1)
        search_results = product_df[mask]
        st.write(f"Found {len(search_results)} products:")
        for i, product in search_results.head(10).iterrows():
            with st.expander(f"{product.get('brand', '')} - {product.get('name', '')[:60]}..."):
                col_a, col_b, col_c = st.columns([2, 1, 1])
                with col_a:
                    st.write(f"**Category:** {product.get('category', 'N/A')}")
                    if pd.notna(product.get('features')): st.write(f"**Features:** {str(product['features'])[:100]}...")
                with col_b:
                    price = float(product.get('price', 0))
                    display_price = convert_currency(price, 'INR') if currency == 'INR' else price
                    st.metric("Price", format_currency(display_price, currency))
                with col_c:
                    add_qty = st.number_input("Qty", min_value=1, value=1, key=f"search_qty_{i}")
                    if st.button("Add", key=f"search_add_{i}"):
                        new_item = {
                            'category': product.get('category', 'General'), 'name': product.get('name', ''), 'brand': product.get('brand', ''), 'quantity': add_qty, 'price': price,
                            'justification': 'Added via search.', 'specifications': product.get('features', ''), 'image_url': product.get('image_url', ''), 'gst_rate': product.get('gst_rate', 18), 'matched': True
                        }
                        st.session_state.boq_items.append(new_item); update_boq_content_with_current_items()
                        st.success(f"Added {add_qty}x {product['name']}!"); st.rerun()

# --- COMPANY STANDARD EXCEL GENERATION ---
def _define_styles():
    """Defines reusable styles for the Excel sheet."""
    return {"header": Font(size=16, bold=True, color="FFFFFF"), "header_fill": PatternFill(start_color="002060", end_color="002060", fill_type="solid"), "table_header": Font(bold=True, color="FFFFFF"), "table_header_fill": PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid"), "bold": Font(bold=True), "group_header_fill": PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid"), "total_fill": PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid"), "grand_total_font": Font(size=12, bold=True, color="FFFFFF"), "grand_total_fill": PatternFill(start_color="002060", end_color="002060", fill_type="solid"), "currency_format": "₹ #,##0", "thin_border": Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))}

def _add_product_image_to_excel(sheet, row_num, image_url, column='P'):
    """Add product image to Excel cell if URL is valid."""
    if not image_url or not isinstance(image_url, str) or image_url.strip() == '': return
    try:
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            pil_image = PILImage.open(io.BytesIO(response.content)); pil_image.thumbnail((100, 100), PILImage.Resampling.LANCZOS)
            img_buffer = io.BytesIO(); pil_image.save(img_buffer, format='PNG'); img_buffer.seek(0)
            excel_img = ExcelImage(img_buffer); excel_img.width = 80; excel_img.height = 80
            sheet.add_image(excel_img, f'{column}{row_num}'); sheet.row_dimensions[row_num].height = 60
    except Exception as e: sheet[f'{column}{row_num}'] = "Image unavailable"

def _populate_company_boq_sheet(sheet, items, room_name, styles):
    """Helper function to populate a single Excel sheet with BOQ data in the new company format."""
    sheet.merge_cells('A3:P3'); header_cell = sheet['A3']; header_cell.value = "All Wave AV Systems Pvt. Ltd."; header_cell.font = styles["header"]; header_cell.fill = styles["header_fill"]; header_cell.alignment = Alignment(horizontal='center', vertical='center')
    sheet['C5'] = "Room Name / Room Type"; sheet['E5'] = room_name; sheet['C6'] = "Floor"; sheet['C7'] = "Number of Seats"; sheet['C8'] = "Number of Rooms"
    headers1 = ['Sr. No.', 'Description of Goods / Services', 'Specifications', 'Make', 'Model No.', 'Qty.', 'Unit Rate (INR)', 'Total', 'SGST\n( In Maharastra)', None, 'CGST\n( In Maharastra)', None, 'Total (TAX)', 'Total Amount (INR)', 'Remarks', 'Reference image']
    headers2 = [None, None, None, None, None, None, None, None, 'Rate', 'Amt', 'Rate', 'Amt', None, None, None, None]
    sheet.append(headers1); sheet.append(headers2); header_start_row = sheet.max_row - 1
    sheet.merge_cells(start_row=header_start_row, start_column=9, end_row=header_start_row, end_column=10); sheet.merge_cells(start_row=header_start_row, start_column=11, end_row=header_start_row, end_column=12)
    for row in sheet.iter_rows(min_row=header_start_row, max_row=sheet.max_row, min_col=1, max_col=len(headers1)):
        for cell in row: cell.font = styles["table_header"]; cell.fill = styles["table_header_fill"]; cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    grouped_items = {}
    for item in items:
        cat = item.get('category', 'General');
        if cat not in grouped_items: grouped_items[cat] = []
        grouped_items[cat].append(item)
    total_before_gst_hardware = 0; total_gst_hardware = 0; item_s_no = 1
    category_letters = [chr(ord('A') + i) for i in range(len(grouped_items))]
    for i, (category, cat_items) in enumerate(grouped_items.items()):
        sheet.append([f"{category_letters[i]}", category]); cat_row_idx = sheet.max_row; sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=16)
        sheet[f'A{cat_row_idx}'].font = styles['bold']; sheet[f'B{cat_row_idx}'].font = styles['bold']; sheet[f'A{cat_row_idx}'].fill = styles['group_header_fill']; sheet[f'B{cat_row_idx}'].fill = styles['group_header_fill']
        for item in cat_items:
            unit_price_inr = convert_currency(item.get('price', 0), 'INR'); subtotal = unit_price_inr * item.get('quantity', 1); gst_rate = item.get('gst_rate', 18)
            sgst_rate = gst_rate / 2; cgst_rate = gst_rate / 2; sgst_amount = subtotal * (sgst_rate / 100); cgst_amount = subtotal * (cgst_rate / 100)
            total_tax = sgst_amount + cgst_amount; total_with_gst = subtotal + total_tax; total_before_gst_hardware += subtotal; total_gst_hardware += total_tax
            row_data = [item_s_no, None, item.get('specifications', item.get('name', '')), item.get('brand', 'Unknown'), item.get('name', 'Unknown'), item.get('quantity', 1), unit_price_inr, subtotal, f"{sgst_rate}%", sgst_amount, f"{cgst_rate}%", cgst_amount, total_tax, total_with_gst, item.get('justification', ''), None]
            sheet.append(row_data); current_row = sheet.max_row; _add_product_image_to_excel(sheet, current_row, item.get('image_url', ''), 'P'); item_s_no += 1
    services = [("Installation & Commissioning", 0.15), ("System Warranty (3 Years)", 0.05), ("Project Management", 0.10)]
    services_letter = chr(ord('A') + len(grouped_items))
    if services and total_before_gst_hardware > 0:
        sheet.append([services_letter, "Services"]); cat_row_idx = sheet.max_row; sheet.merge_cells(start_row=cat_row_idx, start_column=2, end_row=cat_row_idx, end_column=16)
        sheet[f'A{cat_row_idx}'].font = styles['bold']; sheet[f'B{cat_row_idx}'].font = styles['bold']; sheet[f'A{cat_row_idx}'].fill = styles['group_header_fill']; sheet[f'B{cat_row_idx}'].fill = styles['group_header_fill']
    total_before_gst_services = 0; total_gst_services = 0
    services_gst_rate = st.session_state.gst_rates.get('Services', 18)
    for service_name, percentage in services:
        if total_before_gst_hardware > 0:
            service_amount_inr = total_before_gst_hardware * percentage; sgst_rate = services_gst_rate / 2; cgst_rate = services_gst_rate / 2
            service_sgst = service_amount_inr * (sgst_rate / 100); service_cgst = service_amount_inr * (cgst_rate / 100); service_total_tax = service_sgst + service_cgst
            service_total = service_amount_inr + service_total_tax; total_before_gst_services += service_amount_inr; total_gst_services += service_total_tax
            sheet.append([item_s_no, None, "Certified professional service for system deployment", "AllWave AV", service_name, 1, service_amount_inr, service_amount_inr, f"{sgst_rate}%", service_sgst, f"{cgst_rate}%", service_cgst, service_total_tax, service_total, "As per standard terms", ""]); item_s_no += 1
    sheet.append([]); hardware_total_row = ["", "Total for Hardware (A)", "", "", "", "", "", total_before_gst_hardware, "", "", "", "", total_gst_hardware, total_before_gst_hardware + total_gst_hardware]
    sheet.append(hardware_total_row); [cell.fill for cell in sheet[sheet.max_row] if (cell.font := styles['bold'])]; [cell.fill for cell in sheet[sheet.max_row] if (cell.fill := styles['total_fill'])]
    if total_before_gst_services > 0:
        services_total_row = ["", f"Total for Services ({services_letter})", "", "", "", "", "", total_before_gst_services, "", "", "", "", total_gst_services, total_before_gst_services + total_gst_services]
        sheet.append(services_total_row); [cell.fill for cell in sheet[sheet.max_row] if (cell.font := styles['bold'])]; [cell.fill for cell in sheet[sheet.max_row] if (cell.fill := styles['total_fill'])]
    grand_total = (total_before_gst_hardware + total_gst_hardware) + (total_before_gst_services + total_gst_services)
    sheet.append([]); grand_total_row_idx = sheet.max_row + 1
    sheet[f'M{grand_total_row_idx}'] = "Grand Total (INR)"; sheet[f'N{grand_total_row_idx}'] = grand_total
    sheet[f'M{grand_total_row_idx}'].font = styles["grand_total_font"]; sheet[f'N{grand_total_row_idx}'].font = styles["grand_total_font"]; sheet[f'M{grand_total_row_idx}'].fill = styles["grand_total_fill"]; sheet[f'N{grand_total_row_idx}'].fill = styles["grand_total_fill"]
    sheet[f'M{grand_total_row_idx}'].alignment = Alignment(horizontal='center'); sheet[f'N{grand_total_row_idx}'].alignment = Alignment(horizontal='center')
    column_widths = {'A': 8, 'B': 35, 'C': 45, 'D': 20, 'E': 30, 'F': 6, 'G': 15, 'H': 15, 'I': 10, 'J': 15, 'K': 10, 'L': 15, 'M': 15, 'N': 18, 'O': 40, 'P': 20}
    for col, width in column_widths.items(): sheet.column_dimensions[col].width = width
    for row in sheet.iter_rows(min_row=header_start_row + 2, max_row=sheet.max_row):
        for cell in row:
            if cell.value is not None: cell.border = styles['thin_border']
            if cell.column >= 7 and cell.column <= 14: cell.number_format = styles['currency_format']
    return total_before_gst_hardware + total_before_gst_services, total_gst_hardware + total_gst_services, grand_total

def add_proposal_summary_sheet(workbook, rooms_data, styles):
    """Adds the Proposal Summary sheet."""
    sheet = workbook.create_sheet("Proposal Summary"); sheet.merge_cells('A3:H3'); header_cell = sheet['A3']; header_cell.value = "Proposal Summary"; header_cell.font = styles["header"]; header_cell.fill = styles["header_fill"]; header_cell.alignment = Alignment(horizontal='center', vertical='center')
    headers = ["Sr. No", "Description", "Total Qty", "Rate w/o TAX", "Amount w/o TAX", "Total TAX Amount", "Amount with Tax"]; sheet.append(headers); header_row = sheet.max_row
    for cell in sheet[header_row]: cell.font = styles["bold"]; cell.fill = styles["group_header_fill"]
    grand_total_with_tax = 0
    for i, room in enumerate(rooms_data, 1):
        if room.get('boq_items'):
            subtotal = room.get('subtotal', 0); gst = room.get('gst', 0); total = room.get('total', 0); grand_total_with_tax += total
            sheet.append([i, room['name'], 1, subtotal, subtotal, gst, total])
    total_row = sheet.max_row + 2; sheet[f'F{total_row}'] = "GRAND TOTAL (INR)"; sheet[f'G{total_row}'] = grand_total_with_tax
    sheet[f'F{total_row}'].font = styles["grand_total_font"]; sheet[f'G{total_row}'].font = styles["grand_total_font"]; sheet[f'F{total_row}'].fill = styles["grand_total_fill"]; sheet[f'G{total_row}'].fill = styles["grand_total_fill"]
    terms_start_row = sheet.max_row + 3; sheet[f'B{terms_start_row}'] = "Commercial Terms"; sheet[f'B{terms_start_row}'].font = Font(size=14, bold=True)
    for col in ['D', 'E', 'F', 'G']:
        for cell in sheet[col]: cell.number_format = styles['currency_format']

def add_scope_of_work_sheet(workbook):
    """Adds the static Scope of Work sheet."""
    sheet = workbook.create_sheet("Scope of Work"); sheet['A1'] = "Scope of Work"; sheet['A1'].font = Font(size=16, bold=True)
    sheet['A3'] = "1. Site Coordination and Prerequisites Clearance."; sheet['A4'] = "2. Detailed schematic drawings according to the design."

def add_version_control_sheet(workbook, project_name, client_name):
    """Adds the Version Control sheet."""
    sheet = workbook.create_sheet("Version Control"); sheet['B4'] = "Version Control"; sheet['E4'] = "Contact Details"
    sheet['B6'] = "Date of First Draft"; sheet['C6'] = datetime.now().strftime('%Y-%m-%d'); sheet['E6'] = "Design Engineer"
    sheet['E8'] = "Client Name"; sheet['F8'] = client_name; sheet['B10'] = "Version No."; sheet['C10'] = "1.0"

def add_terms_conditions_sheet(workbook):
    """Add Terms & Conditions sheet with standard clauses."""
    sheet = workbook.create_sheet("Terms & Conditions")
    terms_content = [("COMMERCIAL TERMS & CONDITIONS", "header"), ("", ""), ("1. VALIDITY", "section"), ("This quotation is valid for 30 days from the date of issue.", "text"), ("", ""), ("2. PAYMENT TERMS", "section"), ("• 30% advance payment with purchase order", "text"), ("• 40% payment on material delivery at site", "text"), ("• 30% payment on completion of installation & commissioning", "text"), ("", ""), ("3. DELIVERY & INSTALLATION", "section"), ("• Delivery: 4-6 weeks from receipt of advance payment", "text"), ("• Installation will be completed within 2 weeks of delivery", "text"), ("• Site readiness as per AllWave AV specifications required", "text"), ("", ""), ("4. WARRANTY", "section"), ("• 3 years comprehensive warranty on all equipment", "text"), ("• On-site support within 24-48 hours", "text"), ("• Remote support available 24x7", "text")]
    styles = _define_styles()
    for i, (content, style_type) in enumerate(terms_content, 1):
        cell = sheet[f'A{i}']; cell.value = content
        if style_type == "header": cell.font = Font(size=16, bold=True, color="FFFFFF"); cell.fill = PatternFill(start_color="002060", end_color="002060", fill_type="solid"); cell.alignment = Alignment(horizontal='center')
        elif style_type == "section": cell.font = Font(size=12, bold=True, color="002060")
        elif style_type == "text": cell.font = Font(size=11)
        cell.alignment = Alignment(wrap_text=True, vertical='top')
    sheet.column_dimensions['A'].width = 80

def generate_company_excel(rooms_data=None):
    """Generate Excel file in the new company standard format."""
    if not rooms_data and ('boq_items' not in st.session_state or not st.session_state.boq_items):
        st.error("No BOQ items to export. Generate a BOQ first."); return None
    workbook = openpyxl.Workbook(); styles = _define_styles()
    project_name = st.session_state.get('project_name_input', 'AV Installation'); client_name = st.session_state.get('client_name_input', 'Valued Client')
    if rooms_data:
        for room in rooms_data:
            if room.get('boq_items'):
                safe_room_name = re.sub(r'[\\/*?:"<>|]', '', room['name'])[:30]; room_sheet = workbook.create_sheet(title=safe_room_name)
                subtotal, gst, total = _populate_company_boq_sheet(room_sheet, room['boq_items'], room['name'], styles)
                room['subtotal'] = subtotal; room['gst'] = gst; room['total'] = total
        add_proposal_summary_sheet(workbook, rooms_data, styles)
    else:
        sheet = workbook.active; room_name = "BOQ"
        if st.session_state.project_rooms: room_name = st.session_state.project_rooms[st.session_state.current_room_index]['name']
        sheet.title = re.sub(r'[\\/*?:"<>|]', '', room_name)[:30]
        subtotal, gst, total = _populate_company_boq_sheet(sheet, st.session_state.boq_items, room_name, styles)
        single_room_summary = [{'name': room_name, 'subtotal': subtotal, 'gst': gst, 'total': total, 'boq_items': True}]
        add_proposal_summary_sheet(workbook, single_room_summary, styles)
    add_scope_of_work_sheet(workbook); add_version_control_sheet(workbook, project_name, client_name); add_terms_conditions_sheet(workbook)
    if "Sheet" in workbook.sheetnames and len(workbook.sheetnames) > 1: del workbook["Sheet"]
    excel_buffer = BytesIO(); workbook.save(excel_buffer); excel_buffer.seek(0)
    return excel_buffer.getvalue()

# --- Main Application ---
def get_sample_product_data():
    """Provide comprehensive sample products with AVIXA-relevant specifications."""
    return [{'name': 'Samsung 55" QM55R 4K Display', 'brand': 'Samsung', 'category': 'Displays', 'price': 1200, 'features': '55" 4K UHD, 500-nit brightness, 16/7 operation, TIZEN 4.0', 'image_url': 'https://images.samsung.com/is/image/samsung/assets/sg/business-images/qm55r/qm55r_001_front_black.png', 'gst_rate': 18, 'power_draw': 180}]

def show_login_page():
    """Simple login page for internal users."""
    st.set_page_config(page_title="AllWave AV - BOQ Generator", page_icon="⚡")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏢 AllWave AV & GS"); st.subheader("Design & Estimation Portal"); st.markdown("---")
        with st.form("login_form"):
            email = st.text_input("Email ID", placeholder="yourname@allwaveav.com or yourname@allwavegs.com")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Login", type="primary", use_container_width=True)
            if submit:
                if (email.endswith(("@allwaveav.com", "@allwavegs.com"))) and len(password) > 3:
                    st.session_state.authenticated = True; st.session_state.user_email = email
                    st.success("Login successful!"); st.rerun()
                else: st.error("Please use your AllWave AV or AllWave GS email and a valid password")
        st.markdown("---"); st.info("Phase 1 Internal Tool - Contact IT for access issues")

#--- ★★★ FINAL WRAPPER FUNCTION (REPLACED) ★★★ ---
def generate_boq_with_justifications(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """Main BOQ generation function - now production ready."""
    return generate_production_ready_boq(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area)

def main():
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if not st.session_state.authenticated: show_login_page(); return
    st.set_page_config(page_title="Professional AV BOQ Generator", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = None
    if 'project_rooms' not in st.session_state: st.session_state.project_rooms = []
    if 'current_room_index' not in st.session_state: st.session_state.current_room_index = 0
    if 'gst_rates' not in st.session_state: st.session_state.gst_rates = {'Electronics': 18, 'Services': 18, 'Default': 18}
    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues", expanded=False): [st.warning(issue) for issue in data_issues]
    if product_df is None: return
    model = setup_gemini(); project_id, quote_valid_days = create_project_header()
    with st.sidebar:
        st.markdown(f"👤 **Logged in as:** {st.session_state.get('user_email', 'Unknown')}")
        if st.button("Logout", type="secondary"): st.session_state.clear(); st.rerun()
        st.markdown("---"); st.header("Project Configuration")
        client_name = st.text_input("Client Name", key="client_name_input"); project_name = st.text_input("Project Name", key="project_name_input")
        st.markdown("---"); st.subheader("🇮🇳 Indian Business Settings")
        currency = st.selectbox("Currency Display", ["INR", "USD"], index=0, key="currency_select"); st.session_state['currency'] = currency
        electronics_gst = st.number_input("Hardware GST (%)", value=18, min_value=0, max_value=28, key="electronics_gst")
        services_gst = st.number_input("Services GST (%)", value=18, min_value=0, max_value=28, key="services_gst")
        st.session_state.gst_rates['Electronics'] = electronics_gst; st.session_state.gst_rates['Services'] = services_gst
        st.markdown("---"); st.subheader("Room Design Settings")
        room_type_key = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium", "Enterprise"], value="Standard", key="budget_tier_slider")
        room_spec = ROOM_SPECS[room_type_key]; st.markdown("#### Room Guidelines"); st.caption(f"Area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft"); st.caption(f"Display: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Multi-Room Project", "Room Analysis", "Requirements", "Generate & Edit BOQ", "3D Visualization"])
    with tab1: create_multi_room_interface()
    with tab2: room_area, ceiling_height = create_room_calculator()
    with tab3:
        features = st.text_area("Specific Requirements & Features:", placeholder="e.g., 'Dual displays, wireless presentation, Zoom certified'", height=100, key="features_text_area")
        technical_reqs = create_advanced_requirements(); technical_reqs['ceiling_height'] = st.session_state.get('ceiling_height_input', 10)
    with tab4:
        st.subheader("Professional BOQ Generation"); col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🚀 Generate BOQ with Justifications", type="primary", use_container_width=True):
                if not model: st.error("AI Model is not available. Please check API key.")
                else:
                    with st.spinner("Generating and validating professional BOQ..."):
                        room_area_val = st.session_state.get('room_length_input', 24) * st.session_state.get('room_width_input', 16)
                        boq_content, boq_items, avixa_calcs, equipment_reqs = generate_boq_with_justifications(model, product_df, guidelines, room_type_key, budget_tier, features, technical_reqs, room_area_val)
                        if boq_items:
                            st.session_state.boq_items = boq_items; update_boq_content_with_current_items()
                            if st.session_state.project_rooms: st.session_state.project_rooms[st.session_state.current_room_index]['boq_items'] = boq_items
                            avixa_validation = validate_avixa_compliance(boq_items, avixa_calcs, equipment_reqs)
                            validator = BOQValidator(ROOM_SPECS, product_df); issues, warnings = validator.validate_technical_requirements(boq_items, room_type_key, room_area_val)
                            avixa_warnings_old = validate_against_avixa(model, guidelines, boq_items)
                            all_issues = issues + avixa_validation['avixa_issues']; all_warnings = warnings + avixa_warnings_old + avixa_validation['avixa_warnings']
                            st.session_state.validation_results = {"issues": all_issues, "warnings": all_warnings, "avixa_compliance_score": avixa_validation['compliance_score']}
                            st.rerun()
                        else: st.error("Failed to generate BOQ. Please check product catalog and try again.")
        with col2:
            if 'boq_items' in st.session_state and st.session_state.boq_items:
                excel_data = generate_company_excel(); room_name = "CurrentRoom"
                if st.session_state.project_rooms: room_name = st.session_state.project_rooms[st.session_state.current_room_index]['name']
                filename = f"{st.session_state.get('project_name_input', 'Project')}_{room_name}_BOQ_{datetime.now().strftime('%Y%m%d')}.xlsx"
                st.download_button(label="📊 Download Current Room BOQ", data=excel_data, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, type="secondary")
        if st.session_state.boq_content or st.session_state.boq_items:
            st.markdown("---"); display_boq_results(st.session_state.boq_content, st.session_state.validation_results, project_id, quote_valid_days, product_df)
    with tab5: create_3d_visualization()

if __name__ == "__main__":
    main()
