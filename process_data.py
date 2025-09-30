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

def extract_engineering_data(description):
    """Uses regular expressions to find engineering specs in text."""
    text = str(description).lower()
    data = {
        'rack_units': 0,
        'power_draw_watts': 0,
        'hdmi_in': 0,
        'hdmi_out': 0
    }
    
    ru_match = re.search(r'(\d+)\s?ru', text) or re.search(r'(\d+)u rack', text)
    if ru_match:
        data['rack_units'] = int(ru_match.group(1))

    watt_match = re.search(r'(\d+)\s?w', text)
    if watt_match:
        data['power_draw_watts'] = int(watt_match.group(1))

    hdmi_in_match = re.search(r'(\d+)\s?x\s?hdmi\s?(in|input)', text)
    if hdmi_in_match:
        data['hdmi_in'] = int(hdmi_in_match.group(1))

    hdmi_out_match = re.search(r'(\d+)\s?x\s?hdmi\s?(out|output)', text)
    if hdmi_out_match:
        data['hdmi_out'] = int(hdmi_out_match.group(1))

    return data

def categorize_and_tag_product(description, model):
    """
    Analyzes product info to assign a precise sub-category and generate useful metadata tags.
    """
    text_to_search = (str(description) + ' ' + str(model)).lower()

    # CRITICAL: Order matters - most specific rules first
# In categorize_and_tag_product function, update category_rules:
category_rules = [
    # Video Conferencing - Most specific first
    ('Video Conferencing', ['video bar', 'rally bar', 'studio x', 'meetup', 'studio bar'], []),
    ('Video Conferencing', ['codec', 'g7500', 'roommate', 'sx80', 'codec plus'], []),
    ('Video Conferencing', ['ptz', 'camera', 'eagleeye', 'webcam'], ['mount', 'shelf', 'bracket', 'kit']),
    
    # Control Systems
    ('Control', ['touch panel', 'touch screen', 'tsw-', 'tsd-', 'ts-', 'tap', 'ctp18'], ['scheduler', 'home os']),
    ('Control', ['control processor', 'dmps', 'cp4', 'mc4'], ['home os']),
    ('Control', ['matrix', 'switcher', 'hd-md', 'dm-md'], []),
    
    # Audio - Very specific
    ('Audio', ['microphone', 'mic array', 'mxa9', 'ceiling mic', 'table mic'], ['cable', 'adapter', 'kit']),
    ('Audio', ['speaker', 'loudspeaker', 'ceiling speaker'], ['cable', 'mount', 'baffle', 'kit']),
    ('Audio', ['amplifier', ' amp ', 'power amp'], ['summing', 'tile', 'bridge', 'kit']),
    ('Audio', ['dsp', 'tesira', 'q-sys core', 'biamp', 'digital signal'], ['tile', 'bridge']),
    
    # Displays - Exclude accessories and peripherals
    ('Displays', ['display', 'monitor', 'screen', 'interactive', 'flip', 'board'], ['mount', 'cable', 'bracket', 'keyboard', 'mouse']),
    ('Displays', ['projector'], ['mount', 'screen']),
    
    # Mounts - Be specific
    ('Mounts', ['display mount', 'wall mount', 'flat panel mount'], ['camera', 'tile', 'bezel']),
    ('Mounts', ['camera mount', 'camera shelf'], []),
    ('Mounts', ['rack mount', 'rack shelf'], ['bezel']),
    
    # Cables - Only actual cables
    ('Cables', ['cable', 'hdmi', 'displayport', 'usb cable', 'cat6', 'patch cord'], ['bezel', 'kit']),
    
    # Infrastructure
    ('Infrastructure', ['rack', 'enclosure', 'cabinet'], ['mount', 'shelf', 'bezel']),
    ('Infrastructure', ['pdu', 'power distribution'], []),
]
    
    category = 'General'
    for rule in category_rules:
        cat = rule[0]
        include_keywords = rule[1]
        exclude_keywords = rule[2] if len(rule) > 2 else []
        
        # Must match at least one include keyword
        has_include = any(keyword in text_to_search for keyword in include_keywords)
        # Must NOT match any exclude keyword
        has_exclude = any(keyword in text_to_search for keyword in exclude_keywords)
        
        if has_include and not has_exclude:
            category = cat
            break

    # Feature tagging
    tags = {'feature': set(), 'tech_spec': set(), 'compatibility': set()}
    
    feature_rules = [
        ('wireless_presentation', ['wireless', 'clickshare', 'airtame', 'solstice']),
        ('interactive', ['interactive', 'touch display', 'flip']),
        ('4k', ['4k', 'uhd', '3840']),
        ('dante', ['dante']),
        ('usb_c', ['usb-c', 'usb type-c']),
        ('poe', ['poe', 'power over ethernet']),
        ('zoom_certified', ['zoom certified', 'zoom room']),
        ('teams_certified', ['teams certified', 'microsoft teams']),
    ]
    
    for tag, keywords in feature_rules:
        if any(keyword in text_to_search for keyword in keywords):
            if tag in ['wireless_presentation', 'interactive', '4k']:
                tags['feature'].add(tag)
            elif tag in ['dante', 'usb_c', 'poe']:
                tags['tech_spec'].add(tag)
            else:
                tags['compatibility'].add(tag)

    return category, ','.join(sorted(tags['feature'])), ','.join(sorted(tags['tech_spec'])), ','.join(sorted(tags['compatibility']))

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
            
            main_category, feature_tags, tech_spec_tags, compatibility_tags = categorize_and_tag_product(desc, model)
            eng_data = extract_engineering_data(desc)
            
            name = f"{model} - {desc.splitlines()[0]}" if desc else model
            
            all_products.append({
                'category': main_category,
                'brand': brand,
                'name': name,
                'price': price if pd.notna(price) else 0.0,
                'features': desc,
                'feature_tags': feature_tags,
                'tech_spec_tags': tech_spec_tags,
                'compatibility_tags': compatibility_tags,
                'rack_units': eng_data['rack_units'],
                'power_draw_watts': eng_data['power_draw_watts'],
                'hdmi_in': eng_data['hdmi_in'],
                'hdmi_out': eng_data['hdmi_out'],
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
