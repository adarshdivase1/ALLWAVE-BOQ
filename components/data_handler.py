# components/data_handler.py

import pandas as pd
import streamlit as st
import re
import traceback

@st.cache_data
def load_and_validate_data():
    """
    Loads the master product catalog, validates essential columns, and renames
    columns for internal consistency within the application.
    """
    data_issues = []
    try:
        df = pd.read_csv("master_product_catalog.csv")

        # ========== BULLETPROOF COLUMN NORMALIZATION ==========
        
        # Handle category column (might be 'category' or 'primary_category')
        if 'category' not in df.columns:
            if 'primary_category' in df.columns:
                df['category'] = df['primary_category']
                data_issues.append("Renamed 'primary_category' to 'category'")
            else:
                df['category'] = 'General AV'
                data_issues.append("Created default 'category' column")
        
        # Handle sub_category
        if 'sub_category' not in df.columns:
            df['sub_category'] = 'Uncategorized'
            data_issues.append("Created default 'sub_category' column")
        
        # Handle price (might be 'price', 'price_usd', or missing)
        if 'price' not in df.columns:
            if 'price_usd' in df.columns:
                df['price'] = df['price_usd']
            elif 'price_inr' in df.columns:
                df['price'] = df['price_inr'] / 83.5  # Convert to USD
            else:
                df['price'] = 0
                data_issues.append("Created default 'price' column")
        
        # Handle specifications (might be 'specifications' or 'full_specifications')
        if 'specifications' not in df.columns:
            if 'full_specifications' in df.columns:
                df['specifications'] = df['full_specifications']
            else:
                df['specifications'] = ''
        
        # Handle other essential columns with defaults
        column_defaults = {
            'name': '',
            'brand': '',
            'description': '',
            'model_number': '',
            'warranty': 'Not Specified',
            'lead_time_days': 14,
            'gst_rate': 18,
            'image_url': '',
            'unit_of_measure': 'piece',
            'data_quality_score': 100
        }
        
        for col, default_val in column_defaults.items():
            if col not in df.columns:
                df[col] = default_val
                data_issues.append(f"Created default '{col}' column")

        # ========== DATA TYPE COERCION ==========
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        df['gst_rate'] = pd.to_numeric(df['gst_rate'], errors='coerce').fillna(18)
        df['lead_time_days'] = pd.to_numeric(df['lead_time_days'], errors='coerce').fillna(14)
        df['data_quality_score'] = pd.to_numeric(df['data_quality_score'], errors='coerce').fillna(100)
        
        # String columns
        df['description'] = df['description'].fillna('')
        df['specifications'] = df['specifications'].fillna('')
        df['image_url'] = df['image_url'].fillna('')
        df['model_number'] = df['model_number'].fillna('')
        df['warranty'] = df['warranty'].fillna('Not Specified')
        df['unit_of_measure'] = df['unit_of_measure'].fillna('piece')
        df['name'] = df['name'].fillna('')
        df['brand'] = df['brand'].fillna('')
        
        # Category handling
        df['category'] = df['category'].fillna('General AV')
        df['sub_category'] = df['sub_category'].fillna('Needs Classification')

        # ========== DATA QUALITY FILTERS ==========
        # Filter out products with zero price
        initial_count = len(df)
        df = df[df['price'] > 0].copy()
        if initial_count > len(df):
            data_issues.append(f"Removed {initial_count - len(df)} products with a price of $0.")

        # Filter out low quality products (optional)
        low_quality_count = len(df[df['data_quality_score'] < 50])
        if low_quality_count > 0:
            data_issues.append(f"Found {low_quality_count} products with quality score < 50.")

        # ========== LOAD AVIXA GUIDELINES ==========
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
        traceback.print_exc()
        return None, None, [f"An unexpected error occurred: {str(e)}"]


def match_product_in_database(product_name, brand, model_number, product_df):
    """
    Finds the best product match in the database, prioritizing model number,
    then brand + name, then fuzzy name matching.
    """
    if product_df is None or product_df.empty:
        return None

    safe_model = str(model_number).strip().lower() if pd.notna(model_number) and model_number else None
    safe_name = str(product_name).strip().lower() if pd.notna(product_name) else None
    safe_brand = str(brand).strip().lower() if pd.notna(brand) else None

    # Strategy 1: Exact Model Number match (highest confidence)
    if safe_model and safe_model != '':
        model_match = product_df[product_df['model_number'].str.lower().str.strip() == safe_model]
        if not model_match.empty:
            return model_match.iloc[0].to_dict()

    # Strategy 2: Brand + Partial Name match (good confidence)
    if safe_brand and safe_name:
        brand_matches = product_df[product_df['brand'].str.lower().str.strip() == safe_brand]
        if not brand_matches.empty:
            # Try exact name match first
            exact_name_match = brand_matches[brand_matches['name'].str.lower().str.strip() == safe_name]
            if not exact_name_match.empty:
                return exact_name_match.iloc[0].to_dict()
            
            # Then try partial name match with word boundaries
            try:
                name_pattern = fr'\b{re.escape(safe_name)}\b'
                name_match = brand_matches[brand_matches['name'].str.contains(name_pattern, case=False, na=False, regex=True)]
                if not name_match.empty:
                    return name_match.iloc[0].to_dict()
            except:
                pass

    # Strategy 3: Fuzzy Name match (lower confidence, last resort)
    if safe_name:
        try:
            fuzzy_match = product_df[product_df['name'].str.contains(re.escape(safe_name), case=False, na=False, regex=True)]
            if not fuzzy_match.empty:
                # Return highest quality score match
                return fuzzy_match.nlargest(1, 'data_quality_score').iloc[0].to_dict()
        except:
            pass
    
    return None


def extract_enhanced_boq_items(boq_content, product_df):
    """
    Extracts BOQ items from the AI's markdown table response, including model number.
    This function is kept for backward compatibility but may not be used in the new BOQ generator.
    """
    items = []
    lines = boq_content.split('\n')
    in_table = False
    
    for line in lines:
        line = line.strip()
        if '|' in line and any(keyword in line.lower() for keyword in ['category', 'make', 'model', 'brand']):
            in_table = True
            continue
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
        if in_table and line.startswith('|'):
            parts = [part.strip() for part in line.split('|') if part.strip()]
            # Expecting at least: Category, Brand, Name, Model, Qty
            if len(parts) >= 5:
                try:
                    category, brand, product_name, model_number = parts[0], parts[1], parts[2], parts[3]
                    quantity = int(parts[4])
                    
                    # Match product using model number
                    matched_product = match_product_in_database(product_name, brand, model_number, product_df)
                    
                    if matched_product:
                        items.append({
                            'category': matched_product.get('category', category),
                            'sub_category': matched_product.get('sub_category', ''),
                            'name': matched_product.get('name', product_name),
                            'brand': matched_product.get('brand', brand),
                            'model_number': matched_product.get('model_number', model_number),
                            'quantity': quantity,
                            'price': float(matched_product.get('price', 0)),
                            'justification': "AI Recommended Component",
                            'specifications': matched_product.get('specifications', ''),
                            'description': matched_product.get('description', ''),
                            'image_url': matched_product.get('image_url', ''),
                            'gst_rate': matched_product.get('gst_rate', 18),
                            'warranty': matched_product.get('warranty', 'Not Specified'),
                            'lead_time_days': matched_product.get('lead_time_days', 14),
                            'unit_of_measure': matched_product.get('unit_of_measure', 'piece'),
                            'data_quality_score': matched_product.get('data_quality_score', 100),
                            'matched': True
                        })
                    else:
                        items.append({
                            'category': category,
                            'name': product_name,
                            'brand': brand,
                            'sub_category': 'Needs Classification',
                            'model_number': model_number,
                            'quantity': quantity,
                            'price': 0,
                            'justification': "AI Recommended, but NOT FOUND in catalog",
                            'specifications': 'Model not found in database, please verify',
                            'description': '',
                            'image_url': '',
                            'gst_rate': 18,
                            'warranty': 'N/A',
                            'lead_time_days': 14,
                            'unit_of_measure': 'piece',
                            'data_quality_score': 0,
                            'matched': False
                        })
                except (ValueError, IndexError) as e:
                    continue
    return items


def get_product_by_criteria(product_df, category=None, sub_category=None, brand=None, 
                            min_price=None, max_price=None, quality_threshold=70):
    """
    NEW HELPER: Filter products by multiple criteria
    """
    if product_df is None or product_df.empty:
        return pd.DataFrame()
    
    filtered = product_df.copy()
    
    if category:
        filtered = filtered[filtered['category'] == category]
    
    if sub_category:
        filtered = filtered[filtered['sub_category'] == sub_category]
    
    if brand:
        filtered = filtered[filtered['brand'].str.lower() == brand.lower()]
    
    if min_price is not None:
        filtered = filtered[filtered['price'] >= min_price]
    
    if max_price is not None:
        filtered = filtered[filtered['price'] <= max_price]
    
    if quality_threshold:
        filtered = filtered[filtered['data_quality_score'] >= quality_threshold]
    
    return filtered


def get_categories_and_subcategories(product_df):
    """
    NEW HELPER: Get all unique categories and their subcategories
    """
    if product_df is None or product_df.empty:
        return {}
    
    category_map = {}
    for category in product_df['category'].unique():
        subcats = product_df[product_df['category'] == category]['sub_category'].unique().tolist()
        category_map[category] = sorted(subcats)
    
    return category_map
