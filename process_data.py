# components/process_data.py

import pandas as pd
import os
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
DATA_FOLDER = 'data'
OUTPUT_FILENAME = 'master_product_catalog.csv'
VALIDATION_REPORT = 'data_quality_report_final.txt'
HEADER_KEYWORDS = ['description', 'model', 'part', 'price', 'sku', 'item', 'mrp']
DEFAULT_GST_RATE = 18
FALLBACK_INR_TO_USD = 83.5

# --- QUALITY THRESHOLDS ---
MIN_DESCRIPTION_LENGTH = 15
MAX_PRICE_USD = 75000
MIN_PRICE_USD = 1.0
REJECTION_SCORE_THRESHOLD = 40

# --- HELPER FUNCTIONS (No changes needed here) ---

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
    desc_lower = description.lower()
    match = re.search(r'(\d+)\s*[-]?\s*y(ea)?r[s]?\s*(warranty|wty)', desc_lower)
    if match: return f"{match.group(1)} Year{'s' if int(match.group(1)) > 1 else ''}"
    if 'lifetime' in desc_lower: return "Lifetime"
    match = re.search(r'(\d+)\s*month[s]?\s*(warranty|wty)', desc_lower)
    if match: return f"{match.group(1)} Month{'s' if int(match.group(1)) > 1 else ''}"
    return "Not Specified"

def clean_model_number(model_str: Any) -> str:
    if pd.isna(model_str): return ""
    model_str = str(model_str).strip().replace('\n', ' ')
    potential_models = re.findall(r'[a-zA-Z]{1,4}[- ]?\d+[- ]?[a-zA-Z0-9-]*', model_str)
    if potential_models: return max(potential_models, key=len).strip()
    potential_models = re.findall(r'([a-zA-Z0-9]+(?:[-/.][a-zA-Z0-9]+)+)', model_str)
    if potential_models: return max(potential_models, key=len).strip()
    return model_str.split(' ')[0]

def clean_filename_brand(filename: str) -> str:
    base_name = re.sub(r'Master List.*-|\.csv|\.xlsx', '', filename, flags=re.IGNORECASE).strip()
    base_name = re.split(r'\s*&\s*|\s+and\s+', base_name, flags=re.IGNORECASE)[0]
    return base_name.strip()

def create_clean_description(raw_desc: str, brand: str, max_length: int = 200) -> str:
    if not isinstance(raw_desc, str): return ""
    desc = ' '.join(raw_desc.split())
    desc = re.sub(r'^(product|item|description|desc)\s*[:\-]\s*', '', desc, flags=re.IGNORECASE)
    if desc.lower().startswith(brand.lower()): desc = desc[len(brand):].lstrip(' -:')
    if desc.lower() in [brand.lower(), 'black', 'white', 'gray', 'silver', 'na', 'n/a']: return ""
    if len(desc) > max_length: desc = desc[:max_length].rsplit(' ', 1)[0] + '...'
    return desc.strip()

def generate_product_name(brand: str, model: str, description: str) -> str:
    name_parts = [brand]
    if model and model.lower() not in brand.lower(): name_parts.append(model)
    if description:
        combined_lower = (brand + ' ' + model).lower()
        if description.lower() not in combined_lower: name_parts.append(f"- {description}")
    return ' '.join(name_parts)

def infer_unit_of_measure(description: str, category: str) -> str:
    desc_lower = str(description).lower()
    if any(word in desc_lower for word in ['spool', 'reel', 'box of', '1000ft', '305m', 'bulk']): return 'spool'
    if 'cable' in desc_lower and re.search(r'\d+\s*(ft|feet|m|meter|inch|\'|\")', desc_lower): return 'piece'
    if 'kit' in desc_lower or 'system' in desc_lower: return 'set'
    if 'pair' in desc_lower and 'cable' not in desc_lower: return 'pair'
    if 'pack' in desc_lower or 'pack of' in desc_lower: return 'pack'
    return 'piece'

def estimate_lead_time(category: str, sub_category: str) -> int:
    if 'Commissioning' in sub_category: return 45
    if 'Video Wall' in sub_category or 'Direct-View LED' in category: return 30
    if category in ['Control Systems', 'Video Processing', 'DSP']: return 21
    if category in ['Video Conferencing', 'Audio', 'Displays']: return 14
    if category in ['Cables & Connectivity', 'Mounts', 'Infrastructure']: return 7
    return 14

# --- CATEGORIZATION ENGINE (ENHANCED) ---

def categorize_product_comprehensively(description: str, model: str) -> Dict[str, Any]:
    text_to_search = (str(description) + ' ' + str(model)).lower()
    
    # Accessory detection (keep this first)
    accessory_keywords = ['mount', 'bracket', 'adapter', 'plate', 'frame', 'stand', 'kit', 'housing', 
                          'chassis', 'faceplate', 'pendant', 'cable', 'cord', 'wire']
    is_likely_accessory = any(re.search(r'\b' + keyword + r'\b', text_to_search) for keyword in accessory_keywords)

    # Priority-ordered categorization rules (more specific first)
    category_rules = [
        # VIDEO CONFERENCING - Most specific patterns first
        ('Video Conferencing', 'Collaboration Display', [
            'meetingboard', 'collaboration display', 'dten', 'surface hub', 
            'interactive display', 'touch display.*collaboration', 'smart.*whiteboard'
        ]),
        
        ('Video Conferencing', 'Video Bar', [
            'video bar', 'meeting bar', 'collaboration bar', 'rally bar', 'poly studio',
            'meetup', 'all-in-one.*video', 'aio.*video', r'\ba\d{2}-\d{3}\b', # Yealink A-series
            'uvc\d{2}', 'smartvision', 'intelligent.*usb.*video'
        ]),
        
        ('Video Conferencing', 'Room Kit / Codec', [
            'room kit', 'codec', 'mvc\d+', 'mcore', 'mini-pc', 'teams rooms system',
            'vc system', 'video conferencing system', 'mtouch', 'base bundle',
            r'\bmvc[s]?\d+\b', 'avhub', 'audio.*video processor'
        ]),
        
        ('Video Conferencing', 'PTZ Camera', [
            'ptz camera', 'pan.*tilt.*zoom', 'optical zoom camera', 'tracking camera',
            'uvc8[46]', r'\d+x.*optical.*zoom', 'dual-eye tracking', 'auto.*framing'
        ]),
        
        ('Video Conferencing', 'Webcam / Personal Camera', [
            'webcam', 'brio', 'c930', 'usb camera', 'desktop camera'
        ]),
        
        ('Video Conferencing', 'Touch Controller', [
            'touch controller', 'touch panel', 'tap ip', 'tc\d+', 'ctp\d+',
            'collaboration touch', 'control panel', 'android.*touch'
        ]),
        
        ('Video Conferencing', 'Scheduling Panel', [
            'scheduler', 'room booking', 'scheduling panel', 'room panel',
            'tss-', 'meeting room.*panel', 'room schduling'
        ]),
        
        ('Video Conferencing', 'Wireless Presentation', [
            'clickshare', 'airtame', 'via connect', 'wpp\d+', 'wireless presentation',
            'screen sharing', 'presentation pod', 'room cast', 'byod.*extender',
            'mshare', 'sharing box', 'vch\d+'
        ]),
        
        # AUDIO - More specific patterns
        ('Audio', 'Ceiling Microphone', [
            'ceiling mic', 'mxa9[012]0', 'tcc2', 'vcm\d+', 'cm\d+',
            r'\btcm-x\b(?!.*(hole|saw|driver|install|kit))', 
            'ceiling.*microphone.*array', 'ceiling.*mic.*array'
        ]),
        
        ('Audio', 'Table Microphone', [
            'table mic', 'boundary mic', 'conference phone', 'speakerphone',
            'tabletop.*mic', 'desktop.*mic', 'vcm\d+.*wireless', 'ms speaker'
        ]),
        
        ('Audio', 'Ceiling Speaker', [
            'ceiling speaker', 'in-ceiling', 'coaxial.*ceiling', 'cs\d+.*ceiling',
            'skysound', 'network.*ceiling.*speaker'
        ]),
        
        ('Audio', 'DSP / Processor', [
            'dsp', 'digital signal processor', 'tesira', 'q-sys core', 'biamp',
            'p300', 'audio mixer', 'audio processor', 'dante.*processor'
        ]),
        
        ('Audio', 'Amplifier', [
            'amplifier', r'\bamp\b', 'poweramp', r'\d+\s*x\s*\d+w', 'power.*amplifier'
        ]),
        
        ('Audio', 'Loudspeaker', [
            'speaker', 'soundbar', 'loudspeaker', 'pendant speaker',
            '(?!ceiling).*speaker(?!phone)'
        ]),
        
        ('Audio', 'Audio Kit', [
            'cmkit', 'audio.*kit', 'microphone.*speaker.*kit'
        ]),
        
        # DISPLAYS
        ('Displays', 'Interactive Display', [
            'interactive(?!.*whiteboard)', 'touch display(?!.*collaboration)', 
            'smart board', 'interactive.*monitor'
        ]),
        
        ('Displays', 'Professional Display', [
            'display(?!.*mount)', 'monitor(?!.*mount)', 'signage', 'bravia', 
            'commercial monitor', 'professional.*display', 'flat panel'
        ]),
        
        ('Displays', 'Video Wall Display', [
            'video wall'
        ]),
        
        ('Displays', 'Direct-View LED', [
            'led wall', 'dvled', 'direct.*view.*led'
        ]),
        
        ('Displays', 'Projector', [
            'projector', 'dlp', 'laser projector'
        ]),
        
        # MOUNTS (check after identifying core products)
        ('Mounts', 'Display Mount / Cart', [
            'tv mount', 'display mount', 'wall mount', 'trolley', 'cart', 
            'floor stand', 'fusion', 'chief', 'vcs-tvmount', 'floorstand'
        ]),
        
        ('Mounts', 'Camera Mount', [
            'camera mount', 'cam-mount', 'camera bracket'
        ]),
        
        ('Mounts', 'Rack Accessory', [
            'rack shelf', 'blanking panel', 'rack rail'
        ]),
        
        # INFRASTRUCTURE
        ('Infrastructure', 'Network Switch', [
            'switch', 'poe switch', 'managed.*switch', 'rch\d+', 'ethernet switch',
            r'\d+-port.*switch'
        ]),
        
        ('Infrastructure', 'AV Rack', [
            r'\d+u rack', r'\d+u\s*enclosure', 'equipment rack'
        ]),
        
        ('Infrastructure', 'Power (PDU/UPS)', [
            'pdu', 'ups', 'power distribution'
        ]),
        
        # SIGNAL MANAGEMENT
        ('Signal Management', 'Matrix Switcher', [
            'matrix', 'switcher(?!.*network|.*poe)', 'video.*switcher'
        ]),
        
        ('Signal Management', 'Extender (TX/RX)', [
            'extender', 'transmitter', 'receiver', 'hdbaset', 'tx/rx', 'usb.*extender'
        ]),
        
        # CABLES & CONNECTIVITY
        ('Cables & Connectivity', 'Wall & Table Plate Frame', [
            'mounting frame', 'aap frame', 'wall plate.*frame'
        ]),
        
        ('Cables & Connectivity', 'Wall & Table Plate Module', [
            'aap module', 'hdmi plate', 'usb plate', 'keystone', 'wall.*module'
        ]),
        
        ('Cables & Connectivity', 'Network Cable', [
            'cat6', 'cat5e', 'utp', 'patch cable', 'ethernet cable'
        ]),
        
        ('Cables & Connectivity', 'Control Cable', [
            'rs-232', 'serial cable', 'control.*cable'
        ]),
        
        ('Cables & Connectivity', 'AV Cable', [
            'hdmi(?!.*plate)', 'usb-c(?!.*plate)', 'aoc', 'vga', 'audio cable', 
            'displayport', 'av.*cable'
        ]),
        
        ('Cables & Connectivity', 'Bulk Cable / Wire', [
            'bulk', 'spool', 'reel', r'\d+ft.*cable', r'\d+m.*cable'
        ]),
    ]

    # Apply rules in order
    for primary, sub, patterns in category_rules:
        # Skip mount/accessory categories if this is a core product
        if primary in ['Mounts', 'Cables & Connectivity'] and not is_likely_accessory:
            # Unless the description is REALLY about mounts/cables
            if not any(mount_word in text_to_search for mount_word in ['mount', 'cable', 'plate', 'bracket', 'stand']):
                continue
        
        # Check if any pattern matches
        for pattern in patterns:
            if re.search(r'\b' + pattern + r'\b', text_to_search, re.IGNORECASE):
                return {'primary_category': primary, 'sub_category': sub, 'needs_review': False}

    # If nothing matched, flag for review
    return {'primary_category': 'General AV', 'sub_category': 'Needs Classification', 'needs_review': True}


# --- DATA QUALITY SCORING ---

def score_product_quality(product: Dict[str, Any]) -> Tuple[int, List[str]]:
    score = 100
    issues = []
    if len(product.get('description', '')) < MIN_DESCRIPTION_LENGTH:
        score -= 20; issues.append(f"Description too short")
    price = product.get('price_usd', 0)
    if price < MIN_PRICE_USD:
        score -= 50; issues.append(f"Price is zero or too low")
    elif price > MAX_PRICE_USD:
        score -= 10; issues.append(f"Price unusually high")
    if not product.get('name'):
        score -= 40; issues.append("Missing generated product name")
    if not product.get('model_number'):
        score -= 20; issues.append("Missing model number")
    if product.get('needs_review', False):
        score -= 25; issues.append("Category could not be classified")
    return max(0, score), issues


# --- MAIN SCRIPT EXECUTION ---

def main():
    all_products: List[Dict] = []
    validation_log = []
    stats = {'files_processed': 0, 'products_found': 0, 'products_valid': 0, 'products_flagged': 0, 'products_rejected': 0}

    if not os.path.exists(DATA_FOLDER):
        print(f"Error: The '{DATA_FOLDER}' directory was not found."); return

    csv_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith('.csv')]
    print(f"Starting BOQ dataset generation...\nFound {len(csv_files)} CSV files to process.\n")

    for filename in csv_files:
        file_path = os.path.join(DATA_FOLDER, filename)
        file_brand = clean_filename_brand(filename)
        print(f"Processing: '{filename}' (Brand: {file_brand})")

        try:
            header_row = find_header_row(file_path, HEADER_KEYWORDS)
            df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip', dtype=str)
            df.dropna(how='all', inplace=True)
            df.columns = [str(col).lower().strip() for col in df.columns]

            model_col = next((c for c in df.columns if any(k in c for k in ['model no', 'part no', 'sku', 'model'])), None)
            desc_col = next((c for c in df.columns if any(k in c for k in ['description', 'desc', 'product name'])), None)
            inr_price_col = next((c for c in df.columns if any(k in c for k in ['inr', 'mrp', 'buy price'])), None)
            usd_price_col = next((c for c in df.columns if 'usd' in c), None)

            if not model_col or not desc_col:
                print(f"  Warning: Could not map required Model/Description columns. Skipping."); continue
            stats['files_processed'] += 1

            for _, row in df.iterrows():
                stats['products_found'] += 1
                raw_model = row.get(model_col, '');
                if pd.isna(raw_model) or not str(raw_model).strip(): continue

                model_clean = clean_model_number(raw_model)
                raw_description = str(row.get(desc_col, '')).strip()
                clean_desc = create_clean_description(raw_description, file_brand)
                categories = categorize_product_comprehensively(raw_description, model_clean)
                price_inr = clean_price(row.get(inr_price_col, 0))
                price_usd = clean_price(row.get(usd_price_col, 0))
                final_price_usd = price_usd if price_usd > 0 else (price_inr / FALLBACK_INR_TO_USD)

                product = {
                    'brand': file_brand, 'name': generate_product_name(file_brand, model_clean, clean_desc),
                    'model_number': model_clean, 'primary_category': categories['primary_category'],
                    'sub_category': categories['sub_category'], 'price_usd': round(final_price_usd, 2),
                    'warranty': extract_warranty(raw_description), 'description': clean_desc,
                    'full_specifications': raw_description, 'unit_of_measure': infer_unit_of_measure(raw_description, categories['primary_category']),
                    'min_order_quantity': 1, 'lead_time_days': estimate_lead_time(categories['primary_category'], categories['sub_category']),
                    'gst_rate': DEFAULT_GST_RATE, 'image_url': '', 'needs_review': categories['needs_review'], 'source_file': filename,
                }
                score, issues = score_product_quality(product)
                product['data_quality_score'] = score

                if score < REJECTION_SCORE_THRESHOLD:
                    stats['products_rejected'] += 1; continue
                if issues:
                    stats['products_flagged'] += 1
                    validation_log.append({'product': product['name'], 'score': score, 'issues': ', '.join(issues)})
                else:
                    stats['products_valid'] += 1
                all_products.append(product)
        except Exception as e:
            print(f"  Error processing {filename}: {e}")

    if not all_products:
        print("\nNo valid products could be processed. Exiting."); return

    final_df = pd.DataFrame(all_products)
    initial_rows = len(final_df)
    final_df.drop_duplicates(subset=['brand', 'model_number'], keep='last', inplace=True)
    final_rows = len(final_df)

    print(f"\n{'='*60}\nProcessing Summary:\n{'='*60}")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Total Products Found: {stats['products_found']}")
    print(f"Products Accepted (Score >= {REJECTION_SCORE_THRESHOLD}): {final_rows}")
    print(f"  - Valid (Score 100): {stats['products_valid']}")
    print(f"  - Flagged for Review: {stats['products_flagged']}")
    # --- THIS IS THE FIX ---
    print(f"Products Rejected (Score < {REJECTION_SCORE_THRESHOLD}): {stats['products_rejected']}")
    print(f"Duplicates Removed: {initial_rows - final_rows}")
    print(f"\nTop 10 Category Distribution:")
    category_counts = final_df['primary_category'].value_counts()
    for cat, count in category_counts.head(10).items(): print(f"  - {cat:<25}: {count} products")

    final_df.to_csv(OUTPUT_FILENAME, index=False)
    print(f"\n✅ Created Master Catalog: '{OUTPUT_FILENAME}' with {final_rows} products")

    if validation_log:
        with open(VALIDATION_REPORT, 'w') as f:
            f.write(f"Data Quality Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Items Flagged: {len(validation_log)}\n{'='*60}\n\n")
            for entry in sorted(validation_log, key=lambda x: x['score']):
                f.write(f"Product: {entry['product']}\nScore: {entry['score']}\nIssues: {entry['issues']}\n\n")
        print(f"ℹ️  Created Validation Report: '{VALIDATION_REPORT}'")
    print(f"\n{'='*60}\nBOQ dataset generation complete!\n{'='*60}\n")

if __name__ == "__main__":
    main()
