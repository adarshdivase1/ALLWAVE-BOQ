import pandas as pd
import streamlit as st
import re

# NOTE: A fallback rate for converting INR to USD if the price_usd column is missing or zero.
# In a real app, this should come from a more reliable source.
FALLBACK_INR_TO_USD_RATE = 83.5

@st.cache_data
def load_and_validate_data():
    """
    Loads and validates the new, richer master product catalog.
    This function is simplified to trust the clean data from the new compiler script.
    """
    try:
        df = pd.read_csv("master_product_catalog.csv")
        validation_issues = []

        # --- NEW LOGIC TO HANDLE THE NEW DATA STRUCTURE ---

        # 1. Create a single, primary 'price' column in USD for the app to use.
        # The rest of the app assumes the base price is in USD.
        if 'price_usd' in df.columns and pd.to_numeric(df['price_usd'], errors='coerce').fillna(0).gt(0).any():
            df['price'] = pd.to_numeric(df['price_usd'], errors='coerce').fillna(0)
        elif 'price_inr' in df.columns:
            st.warning("USD prices not found, converting from INR. This may be inaccurate.")
            df['price'] = pd.to_numeric(df['price_inr'], errors='coerce').fillna(0) / FALLBACK_INR_TO_USD_RATE
        else:
            df['price'] = 0.0
            validation_issues.append("Neither 'price_usd' nor 'price_inr' columns found.")

        # 2. Create the single 'category' column from the new 'primary_category'.
        if 'primary_category' in df.columns:
            df['category'] = df['primary_category']
        else:
            df['category'] = 'General'
            validation_issues.append("'primary_category' column not found.")

        # 3. Ensure other essential columns exist and are filled.
        if 'name' not in df.columns or df['name'].isnull().sum() > 0:
            validation_issues.append(f"{df['name'].isnull().sum()} products missing names")
        if 'brand' not in df.columns:
            df['brand'] = 'Unknown'
        df['brand'] = df['brand'].fillna('Unknown')
        if 'features' not in df.columns:
            df['features'] = df['name']
        df['features'] = df['features'].fillna('')
        if 'image_url' not in df.columns:
            df['image_url'] = ''
        if 'gst_rate' not in df.columns:
            df['gst_rate'] = 18

        # Load AVIXA guidelines (this part remains the same)
        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found."
            validation_issues.append("AVIXA guidelines file missing")

        return df, guidelines, validation_issues

    except FileNotFoundError:
        st.warning("Master product catalog not found. Using sample data.")
        df = pd.DataFrame(get_sample_product_data())
        return df, "AVIXA guidelines not found.", ["Using sample product catalog."]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]

def get_sample_product_data():
    """Provide a fallback sample product if the main catalog fails to load."""
    return [{
        'name': 'Samsung 55" QM55R 4K Display', 'brand': 'Samsung', 'category': 'Displays',
        'price': 1200, 'features': '55" 4K UHD, 500-nit, 16/7', 'primary_category': 'Displays',
        'sub_category': 'Professional Display', 'image_url': '', 'gst_rate': 18
    }]

def match_product_in_database(product_name, brand, product_df):
    """Finds a product in the dataframe. This function remains useful."""
    if product_df is None or len(product_df) == 0: return None
    try:
        safe_product_name = str(product_name).strip() if product_name else ""
        safe_brand = str(brand).strip() if brand else ""
        if not safe_product_name and not safe_brand: return None
        
        # Exact match on name
        if safe_product_name:
            exact_matches = product_df[product_df['name'].astype(str).str.lower() == safe_product_name.lower()]
            if not exact_matches.empty: return exact_matches.iloc[0].to_dict()
        
        # Brand + partial name match
        if safe_brand and safe_product_name:
            brand_matches = product_df[product_df['brand'].astype(str).str.lower() == safe_brand.lower()]
            if not brand_matches.empty:
                # Use regex to find model numbers at the start of the name
                name_matches = brand_matches[brand_matches['name'].astype(str).str.contains(r'\b' + re.escape(safe_product_name.split()[0]) + r'\b', case=False, na=False)]
                if not name_matches.empty: return name_matches.iloc[0].to_dict()

        return None
    except Exception:
        return None

# --- OBSOLETE FUNCTIONS ---
# The functions below are no longer needed because your new data compiler script
# already handles cleaning and categorization. Keeping them would cause errors.
# - clean_and_validate_product_data
# - normalize_category
# - extract_enhanced_boq_items
