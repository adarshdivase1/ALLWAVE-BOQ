import pandas as pd
import streamlit as st

@st.cache_data
def load_and_validate_data():
    """
    Loads the pre-cleaned and validated master product catalog.
    """
    try:
        # The CSV is now expected to be clean from the process_data.py script
        df = pd.read_csv("master_product_catalog.csv")
        validation_issues = []

        # Simple validation checks on the pre-cleaned data
        required_columns = ['name', 'brand', 'primary_category', 'sub_category', 'price', 'features']
        for col in required_columns:
            if col not in df.columns:
                validation_issues.append(f"CRITICAL: Required column '{col}' is missing from master catalog.")
        
        if df['price'].isnull().any() or (df['price'] == 0).all():
             validation_issues.append("CRITICAL: Price column contains null or all-zero values.")

        if validation_issues:
             # Add the first critical issue to the main error to be more descriptive
             st.error(f"Fatal data error: {validation_issues[0]}")

        # Rename for compatibility with the rest of the app
        if 'primary_category' in df.columns:
             df.rename(columns={'primary_category': 'category'}, inplace=True)

        try:
            with open("avixa_guidelines.md", "r") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found."
            validation_issues.append("AVIXA guidelines file missing.")

        return df, guidelines, validation_issues

    except FileNotFoundError:
        st.warning("Master product catalog not found. Please run the `process_data.py` script. Using sample data.")
        return pd.DataFrame(get_sample_product_data()), "Guidelines not found.", ["Using sample data."]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]

def get_sample_product_data():
    """Provides a fallback sample product."""
    return [{
        'name': 'Samsung 55" Display', 'brand': 'Samsung', 'category': 'Displays',
        'sub_category': 'Professional Display', 'price': 1200.0, 'features': '55" 4K UHD'
    }]
