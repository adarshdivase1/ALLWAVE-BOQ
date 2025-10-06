# components/data_handler.py

import pandas as pd
import streamlit as st
import re

@st.cache_data
def load_and_validate_data():
    """
    Loads the master product catalog, validates essential columns, renames them for
    internal consistency, and performs crucial data cleaning and type coercion.
    """
    data_issues = []
    try:
        df = pd.read_csv("master_product_catalog.csv")

        # --- Column Validation and Renaming Schema ---
        # This schema defines the expected source column and the new name inside the app.
        required_cols = {
            'name': 'name',
            'brand': 'brand',
            'primary_category': 'category',
            'sub_category': 'sub_category',
            'price_usd': 'price',
            'description': 'features',
            'model_number': 'model_number',
            'warranty': 'warranty',
            'lead_time_days': 'lead_time_days',
            'gst_rate': 'gst_rate',
            'image_url': 'image_url',
            'data_quality_score': 'quality_score' # Added quality score
        }

        # Check for missing columns, add them with default values if necessary, and rename
        for original, new in required_cols.items():
            if original not in df.columns:
                # Assign sensible defaults based on expected data type
                if any(k in original for k in ['price', 'rate', 'score', 'days']):
                    df[original] = 0
                else:
                    df[original] = ''
                data_issues.append(f"Source file is missing expected column: '{original}'. Using default values.")
        
        df = df.rename(columns=required_cols)

        # --- Data Type Coercion and Cleaning ---
        # Ensure numeric columns are numeric and string columns are strings, filling NaNs
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        df['gst_rate'] = pd.to_numeric(df['gst_rate'], errors='coerce').fillna(18)
        df['quality_score'] = pd.to_numeric(df['quality_score'], errors='coerce').fillna(0)
        df['lead_time_days'] = pd.to_numeric(df['lead_time_days'], errors='coerce').fillna(14)
        
        for col in ['name', 'brand', 'category', 'sub_category', 'features', 'model_number', 'warranty', 'image_url']:
            df[col] = df[col].astype(str).fillna('')

        # Filter out products with zero price, as they are not useful for BOQs
        initial_count = len(df)
        df = df[df['price'] > 0].copy()
        if initial_count > len(df):
            data_issues.append(f"Removed {initial_count - len(df)} products with a price of $0.")

        # Load supplementary guidelines file
        try:
            with open("avixa_guidelines.md", "r", encoding='utf-8') as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found."
            data_issues.append("AVIXA guidelines file missing (avixa_guidelines.md)")

        return df.reset_index(drop=True), guidelines, data_issues

    except FileNotFoundError:
        st.error("FATAL: 'master_product_catalog.csv' not found. Please run the data processing script first.")
        return None, None, ["'master_product_catalog.csv' is missing."]
    except Exception as e:
        st.error(f"A critical error occurred during data loading: {e}")
        return None, None, [f"An unexpected error occurred: {str(e)}"]

def match_product_in_database(product_name: str, brand: str | None, model_number: str, product_df: pd.DataFrame) -> dict | None:
    """
    Finds the best product match in the database, prioritizing model number, then brand + name.
    """
    if product_df is None or product_df.empty:
        return None

    # Sanitize inputs for reliable matching
    safe_model = str(model_number).strip().lower() if pd.notna(model_number) and model_number else None
    safe_name = str(product_name).strip().lower() if pd.notna(product_name) else None

    # --- Matching Strategy 1: Exact Model Number (Highest Confidence) ---
    if safe_model:
        # This is the most reliable way to find a unique product
        model_match = product_df[product_df['model_number'].str.lower() == safe_model]
        if not model_match.empty:
            # Return the highest quality score if multiple matches exist (e.g., from different suppliers)
            return model_match.sort_values('quality_score', ascending=False).iloc[0].to_dict()

    # --- Matching Strategy 2: Fuzzy Name Match (Lower Confidence, Fallback) ---
    # This is useful if the AI provides a name but an incorrect model number
    if safe_name:
        name_match = product_df[product_df['name'].str.lower().str.contains(re.escape(safe_name), na=False)]
        if not name_match.empty:
            return name_match.sort_values('quality_score', ascending=False).iloc[0].to_dict()
    
    return None
