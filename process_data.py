import pandas as pd
import os
import re

def find_header_row(file_path, keywords, max_rows=20):
    """Tries to find the correct header row in a messy CSV."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_rows: break
                if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                    return i
    except Exception:
        with open(file_path, 'r', encoding='latin1', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_rows: break
                if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                    return i
    return 0

def clean_filename_brand(filename):
    """Extracts a clean brand name from the filename."""
    base_name = re.sub(r'Master List 2\.0.*-|\.csv', '', filename, flags=re.IGNORECASE).strip()
    return base_name.split('&')[0].split(' and ')[0].strip()

def get_brand(row, filename_brand, columns):
    """Prioritizes finding a 'Brand' or 'Make' column over the filename."""
    brand_col = next((col for col in columns if str(col).lower() in ['brand', 'make']), None)
    if brand_col and pd.notna(row.get(brand_col)):
        return str(row[brand_col]).strip()
    return filename_brand

def categorize_and_tag_product(description, model):
    """
    Analyzes product info to assign a precise sub-category and generate useful metadata tags.
    The order of this list is CRITICAL. More specific rules must come before general ones.
    """
    text_to_search = (str(description) + ' ' + str(model)).lower()
    
    # --- Part 1: Categorization (Order is Critical) ---
    category_rules = [
        ('Control-Scheduler', ['scheduler']),
        ('Control-InRoom', ['touch panel', 'touch screen', 'tsw-', 'ts-', ' tap']),
        ('Control-Processor', ['control processor', 'dmps']),
        ('Control-Matrix', ['matrix', 'switcher']),
        ('Mounts-Camera', ['camera mount']),
        ('Mounts-Display', ['wall mount', 'display mount']),
        ('Mounts-Rack', ['rack', 'enclosure', 'credenza']),
        ('VC-VideoBar', ['video bar', 'soundbar', 'studio x', 'rally bar']),
        ('VC-Camera', ['camera', 'ptz', 'e-ptz', 'webcam', 'eagleeye']),
        ('VC-Codec', ['codec', 'g7500']),
        ('Audio-DSP', ['dsp', 'digital signal processor', 'tesira', 'q-sys']),
        ('Audio-Microphone', ['microphone', 'mic', 'mxa9']),
        ('Audio-Amplifier', ['amplifier', 'amp']),
        ('Audio-Speaker', ['speaker', 'soundbar']),
        ('Displays', ['display', 'screen', 'monitor', 'interactive', 'projector']),
        ('Cables', ['cable', 'adapter', 'extender', 'hdmi', 'connector']),
        ('Infrastructure', ['ups', 'pdu', 'power', 'switch']),
    ]
    category = 'General'
    for cat, keywords in category_rules:
        if any(keyword in text_to_search for keyword in keywords):
            category = cat
            break

    # --- Part 2: Tag Generation ---
    tag_rules = {
        'feature': [('wireless_presentation', ['wireless', 'clickshare', 'airtame', 'solstice']), ('interactive', ['interactive', 'touch', 'flip']), ('4k', ['4k', 'uhd'])],
        'tech_spec': [('dante', ['dante']), ('usb_c', ['usb-c']), ('poe', ['poe', 'power over ethernet'])],
        'compatibility': [('zoom_certified', ['zoom certified', 'zoom room']), ('teams_certified', ['teams certified', 'microsoft teams']), ('poly_ecosystem', ['poly']), ('logitech_ecosystem', ['logitech']), ('crestron_ecosystem', ['crestron'])]
    }
    
    tags = {'feature': set(), 'tech_spec': set(), 'compatibility': set()}
    for tag_type, rules in tag_rules.items():
        for tag, keywords in rules:
            if any(keyword in text_to_search for keyword in keywords):
                tags[tag_type].add(tag)

    feature_tags = ','.join(sorted(list(tags['feature'])))
    tech_spec_tags = ','.join(sorted(list(tags['tech_spec'])))
    compatibility_tags = ','.join(sorted(list(tags['compatibility'])))

    return category, feature_tags, tech_spec_tags, compatibility_tags

# --- Main Script ---
new_data_folder = 'data'
output_filename = 'master_product_catalog.csv'
all_products = []
header_keywords = ['description', 'model', 'part', 'price', 'sku', 'item']

if not os.path.exists(new_data_folder):
    print(f"Error: The '{new_data_folder}' directory was not found. Please create it and add your new CSV files.")
    exit()

csv_files = [f for f in os.listdir(new_data_folder) if f.endswith('.csv')]
print(f"Found {len(csv_files)} new CSV files to process in the '{new_data_folder}' folder...")

for filename in csv_files:
    file_path = os.path.join(new_data_folder, filename)
    filename_brand = clean_filename_brand(filename)
    print(f"Processing: {filename} (Default Brand: {filename_brand})")
    
    try:
        header_row = find_header_row(file_path, header_keywords)
        df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip', dtype=str)
        df.dropna(how='all', inplace=True)

        model_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['model', 'part', 'sku', 'item no'])), None)
        desc_col = next((c for c in df.columns if 'desc' in str(c).lower()), None)
        price_col_usd = next((c for c in df.columns if 'usd' in str(c).lower()), None)
        price_col = price_col_usd if price_col_usd else next((c for c in df.columns if any(k in str(c).lower() for k in ['price', 'rate'])), None)

        if not model_col or not desc_col:
            print(f"  -> Warning: Could not find 'Model' or 'Description' columns in {filename}. Skipping.")
            continue

        for _, row in df.iterrows():
            model = str(row.get(model_col, '')).strip()
            if not model or model.lower() in ['nan', '']:
                continue

            brand = get_brand(row, filename_brand, df.columns)
            desc = str(row.get(desc_col, '')).strip()
            price = pd.to_numeric(row.get(price_col, 0), errors='coerce')
            
            # Call the new, smarter function to get category and tags
            category, feature_tags, tech_spec_tags, compatibility_tags = categorize_and_tag_product(desc, model)
            
            name = f"{model} - {desc.splitlines()[0]}" if desc else model
            
            # Append the full product data, including new tags
            all_products.append({
                'category': category,
                'brand': brand,
                'name': name,
                'price': price if pd.notna(price) else 0.0,
                'features': desc,
                'feature_tags': feature_tags,
                'tech_spec_tags': tech_spec_tags,
                'compatibility_tags': compatibility_tags,
                'image_url': '',
                'gst_rate': 18
            })

    except Exception as e:
        print(f"  -> CRITICAL ERROR processing {filename}: {e}")

if not all_products:
    print("\n❌ No new products were found. Exiting.")
else:
    new_products_df = pd.DataFrame(all_products)
    print(f"\nProcessed {len(new_products_df)} total product entries from all files.")
    
    initial_rows = len(new_products_df)
    new_products_df.drop_duplicates(subset=['name'], keep='last', inplace=True)
    final_rows = len(new_products_df)
    print(f"De-duplication complete. Removed {initial_rows - final_rows} duplicate entries.")

    new_products_df.to_csv(output_filename, index=False)
    print(f"\n✅ Success! Created new master catalog '{output_filename}' with {len(new_products_df)} unique products.")
