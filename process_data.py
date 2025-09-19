# process_data.py
import pandas as pd
import os
import re

def find_header_row(file_path, keywords, max_rows=20):
    """Tries to find the correct header row in a messy CSV."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= max_rows:
                    break
                if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                    return i
    except Exception:
        with open(file_path, 'r', encoding='latin1') as f:
             for i, line in enumerate(f):
                if i >= max_rows:
                    break
                if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                    return i
    return 0

def clean_brand_name(filename):
    """Extracts a clean brand name from the filename."""
    base_name = filename.replace("Master List 2.0 (1).xlsx - ", "").replace(".csv", "")
    base_name = base_name.split(' & ')[0].split(' and ')[0].strip()
    return base_name

# --- Main Script ---
folder_path = 'data' # ## MODIFIED ## Now specifically looks in the 'data' folder
output_filename = 'new_master_catalog_DRAFT.csv'
all_products = []
header_keywords = ['description', 'model', 'part', 'price']

if not os.path.exists(folder_path):
    print(f"Error: The '{folder_path}' directory was not found. Please create it and add your CSV files.")
    exit()

csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
print(f"Found {len(csv_files)} CSV files to process in the '{folder_path}' folder...")

for filename in csv_files:
    file_path = os.path.join(folder_path, filename)
    brand = clean_brand_name(filename)
    print(f"Processing: {filename} (Brand: {brand})")
    try:
        header_row = find_header_row(file_path, header_keywords)
        df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip')

        model_col = next((col for col in df.columns if 'model' in col.lower() or 'part' in col.lower()), None)
        desc_col = next((col for col in df.columns if 'desc' in col.lower()), None)
        price_col = next((col for col in df.columns if 'price' in col.lower()), None)

        if not model_col or not desc_col:
            print(f"  -> Warning: Could not find 'Model' or 'Description' columns. Skipping.")
            continue

        df = df.rename(columns={model_col: 'Model', desc_col: 'Description'})
        if price_col:
            df = df.rename(columns={price_col: 'Price'})
            df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')

        for _, row in df.iterrows():
            model = str(row.get('Model', '')).strip()
            desc = str(row.get('Description', '')).strip()

            if pd.isna(model) or model.lower() == 'nan' or not model:
                continue

            full_name = f"{model} - {desc}" if desc and not pd.isna(desc) and desc.lower() != 'nan' else model
            product_data = {
                'category': '',
                'brand': brand,
                'name': full_name,
                'price': row.get('Price', 0.0),
                'features': '',
                'tier': 'Standard',
                'use_case_tags': '',
                'compatibility_tags': ''
            }
            all_products.append(product_data)

    except Exception as e:
        print(f"  -> Error processing {filename}: {e}")

if all_products:
    final_df = pd.DataFrame(all_products)
    final_df.to_csv(output_filename, index=False)
    print(f"\n✅ Success! Consolidated {len(final_df)} products into '{output_filename}'.")
else:
    print("\n❌ No products were processed. Please check the CSV files for correct formatting.")
