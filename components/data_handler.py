# components/data_handler.py

import pandas as pd
import streamlit as st
import re

def clean_and_validate_product_data(product_df):
    """Clean and validate product data before using in BOQ generation."""
    if product_df is None or len(product_df) == 0:
        return product_df

    # Create a copy to avoid modifying original
    df = product_df.copy()

    # Clean price data - remove unrealistic prices
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    
    # Category-specific price filtering
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
        return 100 <= price <= 50000  # Default range
    
    df = df[df.apply(is_valid_price, axis=1)]

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
        'AV over IP': 'Control',
        'Extracted from Project': 'General',
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

    # Remove duplicate products
    df = df.drop_duplicates(subset=['name', 'brand'], keep='first')

    return df.reset_index(drop=True)

@st.cache_data
def load_and_validate_data():
    """Enhanced loads and validates with image URLs and GST data."""
    try:
        df = pd.read_csv("master_product_catalog.csv")
        df = clean_and_validate_product_data(df)
        validation_issues = []

        # Check for missing critical data
        if 'name' not in df.columns or df['name'].isnull().sum() > 0:
            validation_issues.append(f"{df['name'].isnull().sum()} products missing names")

        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
            zero_price_count = (df['price'] == 0.0).sum()
            if zero_price_count > 100:
                validation_issues.append(f"{zero_price_count} products have zero pricing")
        else:
            df['price'] = 0.0
            validation_issues.append("Price column missing - using default values")

        if 'brand' not in df.columns:
            df['brand'] = 'Unknown'
            validation_issues.append("Brand column missing - using default values")
        elif df['brand'].isnull().sum() > 0:
            df['brand'] = df['brand'].fillna('Unknown')
            validation_issues.append(f"{df['brand'].isnull().sum()} products missing brand information")

        if 'category' not in df.columns:
            df['category'] = 'General'
            validation_issues.append("Category column missing - using default values")
        else:
            df['category'] = df['category'].fillna('General')

        if 'features' not in df.columns:
            df['features'] = df['name']
            validation_issues.append("Features column missing - using product names for search")
        else:
            df['features'] = df['features'].fillna('')
            
        if 'image_url' not in df.columns:
            df['image_url'] = ''
            validation_issues.append("Image URL column missing - images won't display in Excel")

        if 'gst_rate' not in df.columns:
            df['gst_rate'] = 18
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
        guidelines = "AVIXA guidelines not found. Using basic industry standards."
        return df, guidelines, ["Using sample product catalog for testing"]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]

def get_sample_product_data():
    """Provide comprehensive sample products with AVIXA-relevant specifications."""
    return [
        {
            'name': 'Samsung 55" QM55R 4K Display', 'brand': 'Samsung', 'category': 'Displays',
            'price': 1200, 'features': '55" 4K UHD, 500-nit brightness, 16/7 operation, TIZEN 4.0',
            'image_url': 'https://images.samsung.com/is/image/samsung/assets/sg/business-images/qm55r/qm55r_001_front_black.png',
            'gst_rate': 18, 'power_draw': 180
        },
        # Add more sample data here if needed
    ]

def match_product_in_database(product_name, brand, product_df):
    """Enhanced product matching with better validation."""
    if product_df is None or len(product_df) == 0:
        return None
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
    except Exception as e:
        return None
