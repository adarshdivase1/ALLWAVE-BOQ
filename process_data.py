import pandas as pd
import os
import re
from typing import List, Dict, Any

# --- CONFIGURATION ---
DATA_FOLDER = 'data'
OUTPUT_FILENAME = 'master_product_catalog.csv'
HEADER_KEYWORDS = ['description', 'model', 'part', 'price', 'sku', 'item', 'mrp']
DEFAULT_GST_RATE = 18
FALLBACK_INR_TO_USD = 83.5

# --- HELPER FUNCTIONS ---

def find_header_row(file_path: str, keywords: List[str], max_rows: int = 20) -> int:
    encodings_to_try = ['utf-8', 'latin1', 'cp1252']
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= max_rows: break
                    if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                        return i
        except Exception:
            continue
    return 0

def clean_price(price_str: Any) -> float:
    if pd.isna(price_str): return 0.0
    price_str = str(price_str).strip()
    price_str = re.sub(r'[^\d.]', '', price_str)
    if not price_str: return 0.0
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def extract_warranty(description: str) -> str:
    if not isinstance(description, str): return "Not Specified"
    description = description.lower()
    match = re.search(r'(\d+)\s*[-]?\s*y(ea)?r[s]?', description)
    if match:
        years = match.group(1)
        return f"{years} Year{'s' if int(years) > 1 else ''}"
    if 'lifetime' in description: return "Lifetime"
    return "Not Specified"

def clean_model_number(model_str: Any) -> str:
    if pd.isna(model_str): return ""
    model_str = str(model_str).strip().replace('\n', ' ')
    potential_models = re.findall(r'([a-zA-Z0-9]+(?:[-/.][a-zA-Z0-9]+)+)', model_str)
    if potential_models:
        return max(potential_models, key=len)
    return model_str.split(' ')[0]

def clean_filename_brand(filename: str) -> str:
    base_name = re.sub(r'Master List 2\.0.*-|\.csv|\.xlsx', '', filename, flags=re.IGNORECASE).strip()
    if '&' in base_name: return base_name.split('&')[0].strip()
    if ' and ' in base_name: return base_name.split(' and ')[0].strip()
    return base_name

# --- CATEGORIZATION ENGINE ---

def categorize_product_comprehensively(description: str, model: str) -> Dict[str, str]:
    text_to_search = (str(description) + ' ' + str(model)).lower()
    category_rules = [
        ('Peripherals', 'Keyboard / Mouse', ['keyboard', 'mouse', 'km3322w']),
        ('Peripherals', 'PC / Compute', ['nuc', 'ops', 'mini-pc', 'optiplex', 'desktop']),
        ('Video Conferencing', 'Collaboration Display', ['dten', 'surface hub', 'collaboration display', 'meetingboard', 'avocor', 'interactive touch moniter']),
        ('Video Conferencing', 'Video Bar', ['video bar', 'rally bar', 'poly studio', 'meetup', 'cisco room bar', 'panacast 50', 'uvc40', 'uvc34']),
        ('Video Conferencing', 'Room Kit / Codec', ['room kit', 'codec', 'g7500', 'cs-kit', 'spark kit', 'plus kit', 'mvc400']),
        ('Video Conferencing', 'PTZ Camera', ['ptz camera', 'e-ptz', 'ptz4k', 'eagleeye', 'unicam', 'rally camera']),
        ('Video Conferencing', 'Webcam / Personal Camera', ['webcam', 'brio', 'c930', 'personal video']),
        ('Video Conferencing', 'Touch Controller', ['touch controller', 'tap ip', 'tc8', 'tc10', 'crestron mercury', 'ctp18']),
        ('Video Conferencing', 'Scheduling Panel', ['scheduler', 'room booking', 'tap scheduler', 'tss-770', '6511330']),
        ('Video Conferencing', 'Wireless Presentation', ['clickshare', 'airtame', 'via connect', 'wireless presentation', 'wpp30']),
        ('Audio', 'DSP / Processor', ['dsp', 'digital signal processor', 'tesira', 'q-sys core', 'biamp', 'p300', 'intellimix']),
        ('Audio', 'Ceiling Microphone', ['ceiling mic', 'mxa910', 'mxa920', 'tcc2', 'tcm-x']),
        ('Audio', 'Table Microphone', ['table mic', 'boundary mic', 'mxw6', 'conference phone', 'speak 750', 'cs-mic-table']),
        ('Audio', 'Gooseneck Microphone', ['gooseneck', 'podium mic']),
        ('Audio', 'Wireless Microphone System', ['wireless mic', 'bodypack', 'handheld transmitter', 'lavalier', 'headworn', 'ulxd']),
        ('Audio', 'Amplifier', ['amplifier', 'amp', 'poweramp', 'ma2120', 'pa-120z']),
        ('Audio', 'Loudspeaker', ['speaker', 'soundbar', 'ceiling speaker', 'pendant speaker', 'control 16c', 'mask6ct']),
        ('Audio', 'Audio Interface / Expander', ['dante interface', 'ex-ubt', 'usb expander', 'qio-ml4i']),
        ('Displays', 'Interactive Display', ['interactive', 'touch display', 'smart board', 'flip', 'benq rp', 'newline']),
        ('Displays', 'Professional Display', ['display', 'monitor', 'uhd signage', 'bravia', 'commercial monitor', 'large format display']),
        ('Displays', 'Video Wall Display', ['video wall display', 'un552v']),
        ('Displays', 'Direct-View LED', ['led wall', 'dvled', 'absen', 'direct view', 'curved led']),
        ('Displays', 'Projector', ['projector', 'dlp', 'lcd projector', 'eb-l530u']),
        ('Video Processing', 'Annotation Processor', ['annotation processor']),
        ('Video Processing', 'Video Wall Controller', ['video wall controller', 'g44', 'seada']),
        ('Video Processing', 'Media Player / Signage', ['brightsign', 'media player', 'signage player']),
        ('Video Processing', 'Capture & Streaming', ['capture card', 'capture dongle', 'pearl nano', 'epiphan']),
        ('Control Systems', 'Control Processor', ['control processor', 'dmps', 'cp4n', 'core 110f']),
        ('Control Systems', 'Touch Panel', ['touch panel', 'touch screen', 'tsw-', 'ts-1070']),
        ('Control Systems', 'Keypad', ['keypad', 'seetouch', 'audio control panel']),
        ('Signal Management', 'Matrix Switcher', ['matrix', 'switcher', 'dm-md', 'vm0808']),
        ('Signal Management', 'Extender (TX/RX)', ['extender', 'transmitter', 'receiver', 'dtp', 'xtp', 'hdbaset']),
        ('Cables & Connectivity', 'AV Cable', ['hdmi cable', 'usb-c cable', 'active optical', 'aoc', 'usb 3.2', 'vga', 'audio cable', 'rs-232', 'fiber optic', 'displayport']),
        ('Cables & Connectivity', 'Wall & Table Plate', ['wall plate', 'tbus', 'hydraport', 'cable cubby', 'faceplate']),
        ('Infrastructure', 'AV Rack', ['rack', 'enclosure', 'credenza', 'ptrk', r'\d+u rack', 'heckler av cart', 'av frames']),
        ('Infrastructure', 'Network Switch', ['switch', 'network switch', 'poe switch', 'sg350-10']),
        ('Infrastructure', 'Power (PDU/UPS)', ['pdu', 'ups', 'power strip', 'power distribution', 'power conditioner', '465569']),
        ('Mounts', 'Display Mount / Cart', ['wall mount', 'display mount', 'trolley', 'cart', 'floor stand', 'fusion', 'mobile stand']),
        ('Mounts', 'Camera Mount', ['camera mount', 'cam-mount', 'brkt-qcam-wmk']),
        ('Services', 'Commissioning & Integration', ['commissioning', 'integration', '03-024-01']),
    ]
    for primary, sub, patterns in category_rules:
        if any(re.search(pattern, text_to_search, re.IGNORECASE) for pattern in patterns):
            return {'primary_category': primary, 'sub_category': sub}
    return {'primary_category': 'General AV', 'sub_category': 'Uncategorized'}

# --- MAIN SCRIPT EXECUTION ---

def main():
    all_products: List[Dict] = []
    if not os.path.exists(DATA_FOLDER):
        print(f"❌ Error: The '{DATA_FOLDER}' directory was not found. Please create it and add your source CSV files.")
        return

    csv_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    print(f"🚀 Found {len(csv_files)} CSV files to process...")

    for filename in csv_files:
        file_path = os.path.join(DATA_FOLDER, filename)
        file_brand = clean_filename_brand(filename)
        print(f"\nProcessing: '{filename}' (Brand: {file_brand})")

        try:
            header_row = find_header_row(file_path, HEADER_KEYWORDS)
            df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip', dtype=str)
            df.dropna(how='all', inplace=True)
            df.columns = [str(col).lower().strip() for col in df.columns]

            model_col = next((c for c in df.columns if any(k in c for k in ['model no', 'part no', 'sku', 'model'])), None)
            desc_col = next((c for c in df.columns if 'desc' in c), None)
            inr_price_col = next((c for c in df.columns if any(k in c for k in ['inr', 'mrp', 'buy price'])), None)
            usd_price_col = next((c for c in df.columns if 'usd' in c), None)

            if not model_col or not desc_col:
                print(f"  ⚠️ Warning: Could not map Model/Description columns in {filename}. Skipping.")
                continue
            
            for _, row in df.iterrows():
                raw_model = row.get(model_col, '')
                if pd.isna(raw_model) or not str(raw_model).strip(): continue

                model_clean = clean_model_number(raw_model)
                description = str(row.get(desc_col, '')).strip()
                
                categories = categorize_product_comprehensively(description, model_clean)
                price_inr = clean_price(row.get(inr_price_col, 0))
                price_usd = clean_price(row.get(usd_price_col, 0))

                final_price_usd = 0.0
                if price_usd > 0:
                    final_price_usd = price_usd
                elif price_inr > 0:
                    final_price_usd = price_inr / FALLBACK_INR_TO_USD
                
                if final_price_usd <= 1: continue

                # **FIXED**: Create a clean, descriptive name from the start.
                descriptive_name = f"{model_clean} - {description.splitlines()[0]}" if description else model_clean

                all_products.append({
                    'brand': file_brand,
                    'name': f"{file_brand} {descriptive_name}", # This is the final name.
                    'primary_category': categories['primary_category'],
                    'sub_category': categories['sub_category'],
                    'price': final_price_usd,
                    'warranty': extract_warranty(description),
                    'features': description,
                    'gst_rate': DEFAULT_GST_RATE,
                    'image_url': '',
                })
        except Exception as e:
            print(f"  ❌ CRITICAL ERROR processing {filename}: {e}")

    if not all_products:
        print("\nNo products with valid prices were found. Exiting.")
        return

    final_df = pd.DataFrame(all_products)
    print(f"\n✅ Successfully processed {len(final_df)} total product entries.")

    initial_rows = len(final_df)
    # **FIXED**: Deduplication is done on the unique 'name' column.
    final_df.drop_duplicates(subset=['name'], keep='last', inplace=True)
    final_rows = len(final_df)
    print(f"🧹 De-duplication complete. Removed {initial_rows - final_rows} duplicate entries.")

    # **FIXED**: The bug that created duplicate 'name' columns is removed.
    # The dataframe is now clean before being saved.
    final_df.to_csv(OUTPUT_FILENAME, index=False)
    print(f"\n✨ Success! Created new master catalog '{OUTPUT_FILENAME}' with {final_rows} unique products.")

if __name__ == "__main__":
    main()
