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
        # Fallback to latin1 if utf-8 fails
        with open(file_path, 'r', encoding='latin1', errors='ignore') as f:
            for i, line in enumerate(f):
                if i >= max_rows: break
                if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                    return i
    return 0

# --- UPGRADED: HIERARCHICAL CATEGORIZATION LOGIC ---
def categorize_product_intelligently(description, model):
    """
    Analyzes product info using an ordered, hierarchical system to assign a precise sub-category.
    The order of this list is CRITICAL. More specific rules must come before general ones.
    """
    text_to_search = (str(description) + ' ' + str(model)).lower()
    
    # Ordered rules: (Category, [keywords])
    category_rules = [
        # Control Sub-categories (Specific to General)
        ('Control-Scheduler', ['scheduler']),
        ('Control-InRoom', ['touch panel', 'touch screen', 'tsw-', 'ts-']),
        ('Control-Processor', ['control processor', 'dmps']),
        ('Control-Matrix', ['matrix', 'switcher']),
        
        # Mounts Sub-categories
        ('Mounts-Camera', ['camera mount', 'cam-mount']),
        ('Mounts-Display', ['wall mount', 'display mount', 'flat panel', 'fusion']),
        ('Mounts-Rack', ['rack', 'enclosure', 'credenza']),
        
        # Video Conferencing Sub-categories
        ('VC-Camera', ['camera', 'ptz', 'e-ptz', 'webcam', 'eagleeye']),
        ('VC-Codec', ['codec', 'g7500']),
        ('VC-VideoBar', ['video bar', 'soundbar', 'studi x', 'rally bar']),
        
        # Audio Sub-categories
        ('Audio-DSP', ['dsp', 'digital signal processor', 'tesira', 'q-sys core']),
        ('Audio-Microphone', ['microphone', 'mic', 'mxa9', 'ceiling mic']),
        ('Audio-Amplifier', ['amplifier', 'amp']),
        ('Audio-Speaker', ['speaker', 'soundbar', 'ceiling speaker']),

        # General Categories
        ('Displays', ['display', 'screen', 'monitor', 'interactive', 'projector']),
        ('Cables', ['cable', 'adapter', 'extender', 'hdmi', 'connector']),
        ('Infrastructure', ['ups', 'pdu', 'power', 'switch']),
    ]

    for category, keywords in category_rules:
        if any(keyword in text_to_search for keyword in keywords):
            return category
            
    return 'General' # Fallback for anything that doesn't match

# --- UPGRADED: BRAND DETECTION LOGIC ---
def get_brand(row, filename_brand, columns):
    """Prioritizes finding a 'Brand' or 'Make' column over the filename."""
    brand_col = next((col for col in columns if str(col).lower() in ['brand', 'make']), None)
    if brand_col and pd.notna(row[brand_col]):
        return str(row[brand_col]).strip()
    return filename_brand # Fallback to the brand derived from the filename

def clean_filename_brand(filename):
    """Extracts a clean brand name from the filename."""
    base_name = re.sub(r'Master List 2\.0.*-|\.csv', '', filename, flags=re.IGNORECASE).strip()
    return base_name.split('&')[0].split(' and ')[0].strip()

# --- Main Script ---
new_data_folder = 'data'
output_filename = 'master_product_catalog.csv'
all_products = []
header_keywords = ['description', 'model', 'part', 'price', 'sku', 'item']

if not os.path.exists(new_data_folder):
    print(f"Error: The '{new_data_folder}' directory was not found.")
    exit()

csv_files = [f for f in os.listdir(new_data_folder) if f.endswith('.csv')]
print(f"Found {len(csv_files)} CSV files to process in '{new_data_folder}'...")

for filename in csv_files:
    file_path = os.path.join(new_data_folder, filename)
    filename_brand = clean_filename_brand(filename)
    print(f"Processing: {filename} (Default Brand: {filename_brand})")
    
    try:
        header_row = find_header_row(file_path, header_keywords)
        df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip', dtype=str)
        df.dropna(how='all', inplace=True) # Drop empty rows

        # Identify columns dynamically
        model_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['model', 'part', 'sku', 'item no'])), None)
        desc_col = next((c for c in df.columns if 'desc' in str(c).lower()), None)
        price_col_usd = next((c for c in df.columns if 'usd' in str(c).lower()), None)
        price_col = price_col_usd if price_col_usd else next((c for c in df.columns if any(k in str(c).lower() for k in ['price', 'rate'])), None)

        if not model_col or not desc_col:
            print(f"  -> Warning: Could not find 'Model' or 'Description' columns in {filename}. Skipping.")
            continue

        # --- Process each row ---
        for _, row in df.iterrows():
            model = str(row.get(model_col, '')).strip()
            if not model or model.lower() == 'nan':
                continue

            brand = get_brand(row, filename_brand, df.columns)
            desc = str(row.get(desc_col, '')).strip()
            price = pd.to_numeric(row.get(price_col, 0), errors='coerce')
            
            category = categorize_product_intelligently(desc, model)
            
            # Create a more useful, shorter name
            name = f"{model} - {desc.splitlines()[0]}" if desc else model
            
            all_products.append({
                'category': category,
                'brand': brand,
                'name': name,
                'price': price if pd.notna(price) else 0.0,
                'features': desc,
                'image_url': '', # Placeholder for future use
                'gst_rate': 18 # Default GST rate
            })

    except Exception as e:
        print(f"  -> CRITICAL ERROR processing {filename}: {e}")

if not all_products:
    print("\n❌ No new products were found. Exiting.")
else:
    new_products_df = pd.DataFrame(all_products)
    print(f"\nProcessed {len(new_products_df)} total products from all files.")
    
    # De-duplicate based on the 'name' column, keeping the last entry
    initial_rows = len(new_products_df)
    new_products_df.drop_duplicates(subset=['name'], keep='last', inplace=True)
    final_rows = len(new_products_df)
    print(f"De-duplication complete. Removed {initial_rows - final_rows} duplicate entries.")

    new_products_df.to_csv(output_filename, index=False)
    print(f"\n✅ Success! Created new master catalog '{output_filename}' with {len(new_products_df)} unique products.")
