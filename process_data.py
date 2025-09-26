import pandas as pd
import os
import re

# (find_header_row and clean_brand_name functions remain the same)
def find_header_row(file_path, keywords, max_rows=20):
    # ... (no changes needed)
def clean_brand_name(filename):
    # ... (no changes needed)

# NEW: Function to generate tags from description
def generate_tags_from_description(description):
    """Generates structured tags by searching for keywords in the description."""
    desc_lower = str(description).lower()
    
    use_case_tags = []
    if any(k in desc_lower for k in ['huddle', 'small room']): use_case_tags.append('Huddle Room')
    if any(k in desc_lower for k in ['boardroom', 'executive']): use_case_tags.append('Boardroom')
    if any(k in desc_lower for k in ['classroom', 'training']): use_case_tags.append('Classroom')
    if 'auditorium' in desc_lower: use_case_tags.append('Auditorium')

    compatibility_tags = []
    if 'zoom' in desc_lower: compatibility_tags.append('Zoom Certified')
    if 'teams' in desc_lower: compatibility_tags.append('Teams Certified')
    if 'dante' in desc_lower: compatibility_tags.append('Dante')
    if 'avb' in desc_lower: compatibility_tags.append('AVB')
        
    technical_spec_tags = []
    if '4k' in desc_lower: technical_spec_tags.append('4K')
    if 'ptz' in desc_lower: technical_spec_tags.append('PTZ')
    if 'auto-framing' in desc_lower: technical_spec_tags.append('Auto-framing')
    if 'poe' in desc_lower: technical_spec_tags.append('PoE')
    
    return '; '.join(use_case_tags), '; '.join(compatibility_tags), '; '.join(technical_spec_tags)

# --- Main Script ---
# ... (initial setup is the same)
new_data_folder = 'data'
existing_master_file = 'master_product_catalog.csv'
output_filename = 'master_product_catalog.csv'
all_new_products = []
header_keywords = ['description', 'model', 'part', 'price', 'sku', 'item']
# ... (reading existing file is the same)

for filename in csv_files:
    file_path = os.path.join(new_data_folder, filename)
    brand = clean_brand_name(filename)
    print(f"Processing: {filename} (Brand: {brand})")
    try:
        header_row = find_header_row(file_path, header_keywords)
        df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip')

        # --- MODIFIED: More robust column finding ---
        model_col = next((col for col in df.columns if any(kw in col.lower() for kw in ['model', 'part', 'sku'])), None)
        desc_col = next((col for col in df.columns if 'desc' in col.lower()), None)
        price_col = next((col for col in df.columns if any(kw in col.lower() for kw in ['price', 'msrp', 'cost'])), None)
        # NEW: Look for new columns
        gst_col = next((col for col in df.columns if 'gst' in col.lower()), None)
        power_col = next((col for col in df.columns if 'power' in col.lower() or 'watt' in col.lower()), None)
        image_col = next((col for col in df.columns if 'image' in col.lower()), None)

        if not model_col or not desc_col:
            print(f"  -> Warning: Could not find 'Model' or 'Description' columns in {filename}. Skipping.")
            continue

        # Rename core columns
        df = df.rename(columns={model_col: 'Model', desc_col: 'Description'})
        if price_col:
            df = df.rename(columns={price_col: 'Price'})
            df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        # NEW: Rename and clean new columns if they exist
        if gst_col:
            df = df.rename(columns={gst_col: 'gst_rate'})
            df['gst_rate'] = pd.to_numeric(df['gst_rate'].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(18) * 100
        if power_col:
            df = df.rename(columns={power_col: 'power_draw_watts'})
            df['power_draw_watts'] = pd.to_numeric(df['power_draw_watts'], errors='coerce').fillna(0)
        if image_col:
            df = df.rename(columns={image_col: 'image_url'})

        for _, row in df.iterrows():
            model = str(row.get('Model', '')).strip()
            desc = str(row.get('Description', '')).strip()

            if pd.isna(model) or model.lower() == 'nan' or not model:
                continue

            # --- NEW: Generate tags ---
            use_case, compatibility, tech_specs = generate_tags_from_description(desc)

            full_name = f"{model} - {desc.splitlines()[0]}"
            
            product_data = {
                'category': categorize_product(desc)[0], # Using your existing function
                'brand': brand,
                'name': full_name,
                'price': row.get('Price', 0.0),
                'features': desc, # Keep the full description for reference
                'tier': 'Standard', # TODO: Manually update this in your source files
                'use_case_tags': use_case,
                'compatibility_tags': compatibility,
                'technical_spec_tags': tech_specs, # NEW
                'image_url': row.get('image_url', ''), # NEW
                'gst_rate': row.get('gst_rate', 18), # NEW
                'power_draw_watts': row.get('power_draw_watts', 0) # NEW
            }
            all_new_products.append(product_data)

    except Exception as e:
        print(f"  -> CRITICAL ERROR processing {filename}: {e}")

# ... (rest of the script for combining, de-duplicating, and saving remains the same)
