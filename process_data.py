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
        with open(file_path, 'r', encoding='latin1', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_rows:
                    break
                if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                    return i
    return 0

def clean_brand_name(filename):
    """Extracts a clean brand name from the filename."""
    base_name = re.sub(r'Master List 2\.0.*-|\.csv', '', filename).strip()
    return base_name

# MODIFIED: Corrected category names to be plural to match your app
def categorize_product(description):
    """Analyzes the description to determine category."""
    description_lower = str(description).lower()
    
    # These keys now EXACTLY match your Streamlit app's essential_categories list
    category_keywords = {
        'Displays': ['display', 'screen', 'monitor', 'touch', 'led wall', 'projector', 'interactive'],
        'Audio': ['audio', 'microphone', 'speaker', 'sound', 'headset', 'mixer', 'amplifier'],
        'Video Conferencing': ['camera', 'ptz', 'video bar', 'conferencing', 'codec'],
        'Control': ['control', 'processor', 'switch', 'matrix', 'touch panel', 'controller'],
        'Mounts': ['mount', 'wall mount', 'trolley', 'stand', 'bracket', 'rack'],
        'Cables': ['cable', 'adapter', 'extender', 'hdmi', 'connector'],
        'Infrastructure': ['ups', 'pdu', 'infrastructure']
    }

    for cat, keywords in category_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            return cat
            
    return 'General' # Default if no keywords match


# --- Main Script ---
new_data_folder = 'data'
existing_master_file = 'master_product_catalog.csv'
output_filename = 'master_product_catalog.csv'
all_new_products = []
header_keywords = ['description', 'model', 'part', 'price', 'sku', 'item']

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

        model_col = next((col for col in df.columns if any(kw in str(col).lower() for kw in ['model', 'part', 'sku', 'item no'])), None)
        desc_col = next((col for col in df.columns if 'desc' in str(col).lower()), None)
        price_col = next((col for col in df.columns if any(kw in str(col).lower() for kw in ['price', 'msrp', 'cost', 'rate'])), None)

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

            if pd.isna(model) or model.lower() in ['nan', ''] or not model:
                continue

            category = categorize_product(desc)
            full_name = f"{model} - {desc.splitlines()[0]}" if desc else model

            product_data = {
                'category': category,
                'brand': brand,
                'name': full_name,
                'price': row.get('Price', 0.0),
                'features': desc,
                'tier': 'Standard',
                'use_case_tags': '',
                'compatibility_tags': ''
            }
            all_new_products.append(product_data)

    except Exception as e:
        print(f"  -> CRITICAL ERROR processing {filename}: {e}")

# Step 3 & 4: Combine, De-duplicate, and Save
if not all_new_products and existing_df.empty:
    print("\n❌ No existing data and no new products were found. Exiting.")
else:
    new_products_df = pd.DataFrame(all_new_products)
    print(f"  -> Processed {len(all_new_products)} new products from CSV files")
    
    combined_df = pd.concat([existing_df, new_products_df], ignore_index=True)
    
    if 'name' in combined_df.columns:
        initial_rows = len(combined_df)
        combined_df.drop_duplicates(subset=['name'], keep='last', inplace=True)
        final_rows = len(combined_df)
        print(f"De-duplication complete. Removed {initial_rows - final_rows} old or duplicate entries.")

    combined_df.to_csv(output_filename, index=False)
    print(f"\n✅ Success! Updated master catalog with {len(combined_df)} total products.")
