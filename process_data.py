import pandas as pd
import os
import re

def find_header_row(file_path, keywords, max_rows=20):
    """Tries to find the correct header row in a messy CSV."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_rows:
                    break
                if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                    return i
    except Exception as e:
        print(f"  -> Could not read file {file_path} with utf-8, trying latin1. Error: {e}")
        # Fallback for different encodings
        with open(file_path, 'r', encoding='latin1', errors='ignore') as f:
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
new_data_folder = 'data'
existing_master_file = 'master_product_catalog.csv'
output_filename = 'master_product_catalog.csv'  # Changed: Output directly to main catalog file
all_new_products = []
header_keywords = ['description', 'model', 'part', 'price']

# Step 1: Read the existing master catalog if it exists
if os.path.exists(existing_master_file):
    print(f"Reading existing data from {existing_master_file}...")
    try:
        existing_df = pd.read_csv(existing_master_file)
        print(f"  -> Found {len(existing_df)} existing products in catalog")
    except Exception as e:
        print(f"  -> Warning: Could not read existing master file. Starting fresh. Error: {e}")
        existing_df = pd.DataFrame()
else:
    print(f"No existing {existing_master_file} found. Starting with a blank slate.")
    existing_df = pd.DataFrame()

# Step 2: Process all the new files
if not os.path.exists(new_data_folder):
    print(f"Error: The '{new_data_folder}' directory was not found. Please create it and add your new CSV files.")
    exit()

csv_files = [f for f in os.listdir(new_data_folder) if f.endswith('.csv')]
print(f"Found {len(csv_files)} new CSV files to process in the '{new_data_folder}' folder...")

for filename in csv_files:
    file_path = os.path.join(new_data_folder, filename)
    brand = clean_brand_name(filename)
    print(f"Processing: {filename} (Brand: {brand})")
    try:
        header_row = find_header_row(file_path, header_keywords)
        df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip')

        model_col = next((col for col in df.columns if 'model' in col.lower() or 'part' in col.lower()), None)
        desc_col = next((col for col in df.columns if 'desc' in col.lower()), None)
        price_col = next((col for col in df.columns if 'price' in col.lower()), None)

        if not model_col or not desc_col:
            print(f"  -> Warning: Could not find 'Model' or 'Description' columns in {filename}. Skipping.")
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
            all_new_products.append(product_data)

    except Exception as e:
        print(f"  -> CRITICAL ERROR processing {filename}: {e}")

# Step 3: Combine old and new data
if not all_new_products and existing_df.empty:
    print("\n❌ No existing data and no new products were found. Exiting.")
else:
    new_products_df = pd.DataFrame(all_new_products)
    print(f"  -> Processed {len(all_new_products)} new products from CSV files")
    
    # Combine the existing and new dataframes
    combined_df = pd.concat([existing_df, new_products_df], ignore_index=True)
    
    # Step 4: De-duplicate, keeping the last (newest) entry for any duplicates
    # This ensures new data overwrites old data if a product already exists.
    if 'name' in combined_df.columns:
        initial_rows = len(combined_df)
        combined_df.drop_duplicates(subset=['name'], keep='last', inplace=True)
        final_rows = len(combined_df)
        print(f"De-duplication complete. Removed {initial_rows - final_rows} old or duplicate entries.")

    # Save the combined and cleaned data directly to the main catalog file
    combined_df.to_csv(output_filename, index=False)
    print(f"\n✅ Success! Updated master catalog with {len(combined_df)} total products.")
    print(f"✅ Streamlit app will now automatically use the latest product data.")
