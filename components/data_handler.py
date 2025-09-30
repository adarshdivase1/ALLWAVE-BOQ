# In components/data_handler.py

import streamlit as st
import pandas as pd
from pathlib import Path

def load_and_validate_data():
    """
    Loads the product catalog CSV from the main project directory.
    Returns a DataFrame and any issues found.
    """
    # The name of your data file
    file_name = "master_product_catalog.csv"
    
    # This creates a path to the file in the parent directory (your main repo)
    # CWD (Current Working Directory) is usually the repo root where you run `streamlit run`
    file_path = Path(file_name)
    
    # --- Data Loading and Validation ---
    try:
        # Check 1: Does the file even exist?
        if not file_path.is_file():
            st.error(f"FATAL: The product catalog '{file_name}' was not found in the main repository folder.")
            return None, None, [f"File not found: {file_name}"]

        # Check 2: Try to read the file
        product_df = pd.read_csv(file_path)

        # Check 3: Is the file empty?
        if product_df.empty:
            st.warning("The product catalog file is empty.")
            return None, None, ["Data file is empty."]

        # --- (Optional) Add more data validation checks here ---
        # For example, check for essential columns like 'Model', 'Price', etc.
        required_columns = ['Model Number', 'Description', 'List Price'] # Example columns
        # if not all(col in product_df.columns for col in required_columns):
        #     st.error("The product catalog is missing required columns.")
        #     return None, None, ["Missing required columns."]

        # If all checks pass, return the DataFrame
        # Returning empty lists for guidelines and data_issues for now
        return product_df, [], []

    except Exception as e:
        # This will catch any other errors during file reading (e.g., corrupted file)
        st.error(f"An unexpected error occurred while reading the product catalog: {e}")
        return None, None, [f"File reading error: {str(e)}"]
