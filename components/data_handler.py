import pandas as pd
import streamlit as st
import re
import yaml
from io import StringIO
from pathlib import Path # MODIFIED: Import Path

def clean_and_validate_product_data(product_df):
    """Clean and validate product data before using in BOQ generation."""
    # This function remains the same
    if product_df is None or len(product_df) == 0:
        return product_df
    df = product_df.copy()
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    price_filters = {
        'Cables': (10, 500), 'Mounts': (30, 1000), 'Displays': (500, 20000),
        'Audio': (50, 5000), 'Video Conferencing': (200, 10000),
        'Control': (100, 8000), 'Infrastructure': (100, 5000)
    }
    def is_valid_price(row):
        category = row['category']
        price = row['price']
        if category in price_filters:
            min_p, max_p = price_filters[category]
            return min_p <= price <= max_p
        return 100 <= price <= 50000
    df = df[df.apply(is_valid_price, axis=1)]
    category_mapping = {
        'Displays & Projectors': 'Displays', 'Digital Signage Players & CMS': 'Displays',
        'Interactive Displays & Classroom Tech': 'Displays', 'Projection Screens': 'Displays',
        'UC & Collaboration Devices': 'Video Conferencing', 'PTZ & Pro Video Cameras': 'Video Conferencing',
        'Lecture Capture & Recording': 'Video Conferencing', 'AV Bridges & Specialty I/O': 'Video Conferencing',
        'Audio: Microphones & Conferencing': 'Audio', 'Audio: Speakers': 'Audio', 'Audio: DSP': 'Audio',
        'Audio: Amplifiers': 'Audio', 'Audio: DSP & Processing': 'Audio',
        'Audio: Loudspeakers & Amplifiers': 'Audio', 'Acoustics & Sound Masking': 'Audio',
        'Assistive Listening & Hearing Loop': 'Audio', 'Control Systems & Processing': 'Control',
        'AV over IP & Streaming': 'Control', 'Control, Matrix & Extenders': 'Control',
        'Video Equipment': 'Control', 'Wireless Presentation': 'Control',
        'Room Scheduling & Touch Panels': 'Control', 'Mounts & Racks': 'Mounts',
        'Cables & Connectivity': 'Cables', 'Networking': 'Infrastructure',
        'Network Switches (AV-friendly)': 'Infrastructure', 'AV over IP': 'Control',
        'Extracted from Project': 'General',
    }
    df['category'] = df['category'].map(category_mapping).fillna(df['category'])
    test_patterns = ['Generated Model', 'Extracted from Project']
    for pattern in test_patterns:
        df = df[~df['features'].astype(str).str.contains(pattern, na=False)]
    required_columns = ['name', 'brand', 'category', 'price', 'features']
    for col in required_columns:
        if col not in df.columns:
            df[col] = 'Unknown' if col != 'price' else 0
    df = df.drop_duplicates(subset=['name', 'brand'], keep='first')
    return df.reset_index(drop=True)

@st.cache_data
def load_and_validate_data():
    """MODIFIED: Now uses a robust, absolute path to load files."""
    try:
        # MODIFIED: Create a robust path that works locally and in Streamlit Cloud
        # This assumes this script is in a subdirectory (like 'components/'). It goes up one level to the project root.
        project_root = Path(__file__).parent.parent
        catalog_path = project_root / "master_product_catalog.csv"
        guidelines_path = project_root / "avixa_guidelines.md"

        # MODIFIED: Use the robust path and add error handling for parsing
        try:
            df = pd.read_csv(catalog_path)
        except Exception as csv_error:
            # If the default CSV reader fails, try a more robust but slower one.
            st.warning(f"Standard CSV parser failed: {csv_error}. Trying Python engine.")
            df = pd.read_csv(catalog_path, engine='python')

        df = clean_and_validate_product_data(df)
        validation_issues = []

        # Data validation checks (you can add the full checks back here if needed)
        if 'name' not in df.columns or df['name'].isnull().sum() > 0:
            validation_issues.append(f"{df['name'].isnull().sum()} products missing names")
        # ... (other validation checks remain the same) ...

        # MODIFIED: Use the robust path for the guidelines file
        try:
            with open(guidelines_path, "r", encoding="utf-8") as f:
                content = f.read()

            yaml_blocks = re.findall(r'```yaml(.*?)```', content, re.DOTALL)
            parsed_guidelines = {}
            for block in yaml_blocks:
                documents = yaml.safe_load(StringIO(block))
                if documents:
                    for key, value in documents.items():
                        if key in parsed_guidelines and isinstance(parsed_guidelines[key], list):
                            parsed_guidelines[key].append(value)
                        else:
                            # This logic handles merging multiple 'room_archetype' blocks into a single list
                            if key not in parsed_guidelines:
                                parsed_guidelines[key] = [] if key.endswith('s') or 'archetype' in key else {}
                            if isinstance(parsed_guidelines[key], list):
                                parsed_guidelines[key].append(value)
                            else:
                                parsed_guidelines[key].update(value)

        except FileNotFoundError:
            parsed_guidelines = {}
            validation_issues.append(f"{guidelines_path.name} file missing. Cannot load design rules.")

        return df, parsed_guidelines, validation_issues

    except FileNotFoundError:
        st.warning("Master product catalog not found at the expected path. Using sample data.")
        df = pd.DataFrame([{'name': 'Sample Product', 'brand': 'Sample', 'category': 'General', 'price': 100}])
        return df, {}, ["Using sample product catalog.", "AVIXA guidelines not found."]
    except Exception as e:
        # This will now catch any other error, including the robust parser failing
        return None, None, [f"Data loading error: {str(e)}"]

# --- Other functions remain the same ---

def get_sample_product_data():
    """Provide comprehensive sample products."""
    return [{
        'name': 'Samsung 55" QM55R 4K Display', 'brand': 'Samsung', 'category': 'Displays',
        'price': 1200, 'features': '55" 4K UHD, 500-nit, 16/7',
        'image_url': '', 'gst_rate': 18
    }]

def match_product_in_database(product_name, brand, product_df):
    """Enhanced product matching with better validation."""
    if product_df is None or len(product_df) == 0: return None
    try:
        safe_product_name = str(product_name).strip() if product_name else ""
        safe_brand = str(brand).strip() if brand else ""
        if not safe_product_name and not safe_brand: return None

        # Exact match
        if safe_product_name:
            exact_matches = product_df[product_df['name'].astype(str).str.lower() == safe_product_name.lower()]
            if len(exact_matches) > 0: return exact_matches.iloc[0].to_dict()

        # Brand + partial name match
        if safe_brand and safe_product_name:
            brand_matches = product_df[product_df['brand'].astype(str).str.lower() == safe_brand.lower()]
            if len(brand_matches) > 0:
                name_matches = brand_matches[brand_matches['name'].astype(str).str.contains(re.escape(safe_product_name.split()[0]), case=False, na=False)]
                if len(name_matches) > 0: return name_matches.iloc[0].to_dict()

        # Fuzzy name match
        if safe_product_name and len(safe_product_name) > 3:
            key_terms = safe_product_name.lower().split()[:3]
            for term in key_terms:
                if len(term) > 3:
                    matches = product_df[product_df['name'].astype(str).str.contains(re.escape(term), case=False, na=False)]
                    if len(matches) > 0: return matches.iloc[0].to_dict()
        return None
    except Exception:
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

def extract_enhanced_boq_items(boq_content, product_df):
    """Extract BOQ items from AI response based on markdown table format."""
    from components.utils import estimate_power_draw  # Local import to avoid circular dependency
    items = []
    lines = boq_content.split('\n')
    in_table = False

    for line in lines:
        line = line.strip()
        if '|' in line and any(keyword in line.lower() for keyword in ['category', 'make', 'model']):
            in_table = True
            continue
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 6:
                category, brand, product_name, specifications = parts[0], parts[1], parts[2], parts[3]
                remarks = parts[6] if len(parts) > 6 else "Essential AV system component."
                try:
                    quantity = int(parts[4])
                except (ValueError, IndexError):
                    quantity = 1
                try:
                    price = float(parts[5].replace('$', '').replace(',', ''))
                except (ValueError, IndexError):
                    price = 0

                matched_product = match_product_in_database(product_name, brand, product_df)
                if matched_product:
                    price = float(matched_product.get('price', price))
                    actual_brand = matched_product.get('brand', brand)
                    actual_category = matched_product.get('category', category)
                    actual_name = matched_product.get('name', product_name)
                    image_url = matched_product.get('image_url', '')
                    gst_rate = matched_product.get('gst_rate', 18)
                else:
                    actual_brand, actual_category, actual_name, image_url, gst_rate = brand, normalize_category(category, product_name), product_name, '', 18

                items.append({
                    'category': actual_category, 'name': actual_name, 'brand': actual_brand,
                    'quantity': quantity, 'price': price, 'justification': remarks,
                    'specifications': specifications, 'image_url': image_url, 'gst_rate': gst_rate,
                    'matched': matched_product is not None,
                    'power_draw': estimate_power_draw(actual_category, actual_name)
                })
        elif in_table and not line.startswith('|'):
            in_table = False
    return items
