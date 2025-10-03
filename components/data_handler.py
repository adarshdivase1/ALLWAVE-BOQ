# components/data_handler.py

import pandas as pd
import streamlit as st
import re

@st.cache_data
def load_and_validate_data():
    """
    Loads the master product catalog, validates essential columns, and renames
    columns for internal consistency within the application.
    """
    data_issues = []
    try:
        # --- CHANGE START: Simplified data loading ---
        df = pd.read_csv("master_product_catalog.csv")

        # --- Data Validation and Column Renaming ---
        required_cols = {
            'name': 'name',
            'brand': 'brand',
            'primary_category': 'category', # Renaming for internal use
            'sub_category': 'sub_category',
            'price_usd': 'price',           # Renaming for internal use
            'description': 'features',      # Renaming for internal use
            'model_number': 'model_number',
            'warranty': 'warranty',
            'lead_time_days': 'lead_time_days',
            'gst_rate': 'gst_rate',
            'image_url': 'image_url'
        }

        # Check for missing columns and rename
        for original, new in required_cols.items():
            if original not in df.columns:
                df[original] = '' if original not in ['price_usd', 'gst_rate'] else 0
                data_issues.append(f"Source file is missing expected column: '{original}'. Using default values.")
        
        df = df.rename(columns=required_cols)

        # Data Type Coercion and Cleaning
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        df['gst_rate'] = pd.to_numeric(df['gst_rate'], errors='coerce').fillna(18)
        df['features'] = df['features'].fillna('')
        df['image_url'] = df['image_url'].fillna('')
        df['category'] = df['category'].fillna('General AV')
        df['sub_category'] = df['sub_category'].fillna('Needs Classification')

        # Filter out products with zero price as they are not useful for BOQs
        initial_count = len(df)
        df = df[df['price'] > 0].copy()
        if initial_count > len(df):
            data_issues.append(f"Removed {initial_count - len(df)} products with a price of $0.")

        # --- CHANGE END ---

        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found."
            data_issues.append("AVIXA guidelines file missing (avixa_guidelines.md)")

        return df.reset_index(drop=True), guidelines, data_issues

    except FileNotFoundError:
        st.error("FATAL: 'master_product_catalog.csv' not found. The application cannot start without the product database.")
        return None, None, ["'master_product_catalog.csv' is missing."]
    except Exception as e:
        st.error(f"A critical error occurred during data loading: {e}")
        return None, None, [f"An unexpected error occurred: {str(e)}"]

def match_product_in_database(product_name, brand, model_number, product_df):
    """
    Finds the best product match in the database, prioritizing model number,
    then brand + name, then fuzzy name matching.
    """
    if product_df is None or product_df.empty:
        return None

    safe_model = str(model_number).strip() if pd.notna(model_number) else None
    safe_name = str(product_name).strip() if pd.notna(product_name) else None
    safe_brand = str(brand).strip().lower() if pd.notna(brand) else None

    # --- CHANGE START: Prioritize Model Number Matching ---
    # Strategy 1: Exact Model Number match (highest confidence)
    if safe_model:
        model_match = product_df[product_df['model_number'].str.lower() == safe_model.lower()]
        if not model_match.empty:
            return model_match.iloc[0].to_dict()

    # Strategy 2: Brand + Partial Name match (good confidence)
    if safe_brand and safe_name:
        brand_matches = product_df[product_df['brand'].str.lower() == safe_brand]
        if not brand_matches.empty:
            # Use regex to find the name as a whole word to avoid partial matches like 'pro' in 'projector'
            name_match = brand_matches[brand_matches['name'].str.contains(fr'\b{re.escape(safe_name)}\b', case=False, na=False)]
            if not name_match.empty:
                return name_match.iloc[0].to_dict()

    # Strategy 3: Fuzzy Name match (lower confidence, last resort)
    if safe_name:
        fuzzy_match = product_df[product_df['name'].str.contains(re.escape(safe_name), case=False, na=False)]
        if not fuzzy_match.empty:
            return fuzzy_match.iloc[0].to_dict()
    # --- CHANGE END ---
    
    return None


def extract_enhanced_boq_items(boq_content, product_df):
    """
    Extracts BOQ items from the AI's markdown table response, now including model number.
    """
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
        if in_table and line.startswith('|'):
            parts = [part.strip() for part in line.split('|') if part.strip()]
            # Expecting more parts now: Cat, Brand, Name, Model, Qty, Price, Specs
            if len(parts) >= 5:
                try:
                    # --- CHANGE START: Parsing new AI output format ---
                    category, brand, product_name, model_number = parts[0], parts[1], parts[2], parts[3]
                    quantity = int(parts[4])
                    
                    # Match product using the more reliable model number
                    matched_product = match_product_in_database(product_name, brand, model_number, product_df)
                    
                    if matched_product:
                        # Use data from the database for accuracy
                        items.append({
                            'category': matched_product.get('category', category),
                            'name': matched_product.get('name', product_name),
                            'brand': matched_product.get('brand', brand),
                            'model_number': matched_product.get('model_number', model_number),
                            'quantity': quantity,
                            'price': float(matched_product.get('price', 0)),
                            'justification': "AI Recommended Component.",
                            'specifications': matched_product.get('features', ''),
                            'image_url': matched_product.get('image_url', ''),
                            'gst_rate': matched_product.get('gst_rate', 18),
                            'warranty': matched_product.get('warranty', 'Not Specified'),
                            'lead_time_days': matched_product.get('lead_time_days', 14),
                            'matched': True
                        })
                    else:
                        # Handle cases where the AI might have hallucinated a model
                        items.append({
                            'category': category, 'name': product_name, 'brand': brand,
                            'model_number': model_number, 'quantity': quantity, 'price': 0,
                            'justification': "AI Recommended, but NOT FOUND in catalog.",
                            'specifications': 'Model not found in database, please verify.',
                            'image_url': '', 'gst_rate': 18, 'warranty': 'N/A',
                            'lead_time_days': 14, 'matched': False
                        })
                    # --- CHANGE END ---
                except (ValueError, IndexError) as e:
                    # Skip malformed table rows
                    continue
    return items
