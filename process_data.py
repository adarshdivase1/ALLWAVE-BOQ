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
HEADER_KEYWORDS = ['description', 'model', 'part', 'price', 'sku', 'item', 'mrp', 'buy price', 'inr', 'usd']
DEFAULT_GST_RATE = 18
FALLBACK_INR_TO_USD = 83.5

# --- QUALITY THRESHOLDS ---
MIN_DESCRIPTION_LENGTH = 10
MAX_PRICE_USD = 200000 
MIN_PRICE_USD = 1.0
REJECTION_SCORE_THRESHOLD = 30

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
    price_str = re.sub(r'[₹$,]', '', price_str)
    price_str = re.sub(r'[^\d.]', '', price_str)
    if not price_str: return 0.0
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def extract_warranty(description: str) -> str:
    if not isinstance(description, str): return "Not Specified"
    desc_lower = description.lower()
    match = re.search(r'(\d+)\s*[-]?\s*y(ea)?r[s]?\s*(warranty|wty|support|poly\+)', desc_lower)
    if match: return f"{match.group(1)} Year{'s' if int(match.group(1)) > 1 else ''}"
    if 'lifetime' in desc_lower: return "Lifetime"
    match = re.search(r'(\d+)\s*month[s]?\s*(warranty|wty)', desc_lower)
    if match: return f"{match.group(1)} Month{'s' if int(match.group(1)) > 1 else ''}"
    return "Not Specified"

def clean_model_number(model_str: Any) -> str:
    if pd.isna(model_str): return ""
    model_str = str(model_str).strip().replace('\n', ' ')
    patterns = [
        r'\b[A-Z0-9]{2,}-\d{2,}[A-Z0-9-]*\b', r'\b\w{2,}\d{2,}[A-Z-]*\b',
        r'\b[A-Z]{3,}\d{2,}[A-Z0-9-]*\b', r'\b\d{3}-\d{5}\b',
        r'[a-zA-Z]{1,4}[- ]?\d+[- ]?[a-zA-Z0-9-]*', r'([a-zA-Z0-9]+(?:[-/.][a-zA-Z0-9]+)+)'
    ]
    for pattern in patterns:
        potential_models = re.findall(pattern, model_str)
        if potential_models:
            filtered = [m for m in potential_models if not m.lower() in ['poly', 'yealink', 'logitech', 'version']]
            if filtered:
                return max(filtered, key=len).strip()
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
    if model and model.lower() not in brand.lower().replace(' ', ''): name_parts.append(model)
    if description:
        combined_lower = (brand + ' ' + model).lower()
        short_desc = description.split(',')[0].split(' with ')[0].strip()
        if short_desc and short_desc.lower() not in combined_lower:
            name_parts.append(f"- {short_desc}")
    return ' '.join(name_parts)

def infer_unit_of_measure(description: str, category: str) -> str:
    desc_lower = str(description).lower()
    if any(word in desc_lower for word in ['spool', 'reel', 'box of', '1000ft', '305m', 'bulk']): return 'spool'
    if 'cable' in desc_lower and re.search(r'\d+\s*(ft|feet|m|meter|inch|\'|\")', desc_lower): return 'piece'
    if 'kit' in desc_lower or 'system' in desc_lower: return 'set'
    if 'pair' in desc_lower and 'cable' not in desc_lower: return 'pair'
    if re.search(r'pack of \d+', desc_lower) or 'pack' in desc_lower : return 'pack'
    return 'piece'

def estimate_lead_time(category: str, sub_category: str) -> int:
    if 'Commissioning' in sub_category: return 45
    if any(k in sub_category for k in ['Video Wall', 'Direct-View LED']): return 30
    if category in ['Control Systems', 'Signal Management', 'Audio', 'Lighting']: return 21
    if category in ['Video Conferencing', 'Displays', 'Furniture', 'Computers']: return 14
    if category in ['Cables & Connectivity', 'Mounts', 'Infrastructure', 'Peripherals & Accessories']: return 7
    return 14

# --- V5.0 ULTIMATE CATEGORIZATION ENGINE ---

def categorize_product_comprehensively(description: str, model: str) -> Dict[str, Any]:
    text_to_search = (str(description) + ' ' + str(model)).lower()
    
    category_rules = [
        # 1. Software & Services (Highest Priority)
        ('Software & Services', 'Support & Warranty', [r'\d\s*y(ea)?r.*poly\+', r'\d\s*y(ea)?r.*support', 'jumpstart', 'partner premier', 'onsite support', r'\bcon-snt\b', r'\bcon-ecdn\b']),
        ('Software & Services', 'Software License', ['license', 'saas', 'software license', 'annual license', r'l-kit\w+-ms']),
        ('Software & Services', 'Cloud Service', ['cloud service', 'bsn.cloud', 'xiocloud']),

        # 2. Furniture & Large Structures
        ('Furniture', 'Podium / Lectern', ['podium', 'lectern']),
        ('Furniture', 'AV Credenza / Stand', ['credenza', 'logic pod']),
        
        # 3. Infrastructure (Architectural, Racks, Power)
        ('Infrastructure', 'Architectural / In-Wall', ['faceplate', 'button cap', 'bezel', 'wall plate', 'table plate', 'cable cubby', 'tbus', 'hydraport', 'fliptop', 'mud ring']),
        ('Infrastructure', 'AV Rack', [r'\d+u rack', r'\d+u\s*enclosure', 'equipment rack', 'valrack', 'netshelter']),
        ('Infrastructure', 'Power Management', ['pdu', 'ups', 'power distribution', 'power strip', 'power conditioner', 'power supply', 'poe injector', 'power pack', r'pw-\d+', r'qs-ps-', 'csa-pws']),

        # 4. Mounts
        ('Mounts', 'Display Mount / Cart', ['tv mount', 'display mount', 'wall mount', 'trolley', 'av cart', 'floor stand', 'fusion mount', 'chief', 'vesa', 'videowall mount', 'ceiling mount(?!.*mic|.*speak|.*proj)', r'bt\d+', 'lpa\d+', 'steelcase.*mount', 'heckler.*cart']),
        ('Mounts', 'Projector Mount', ['projector mount', 'projector ceiling mount']),
        ('Mounts', 'Camera Mount', ['camera mount', 'cam-mount', 'camera bracket']),
        ('Mounts', 'Component / Rack Mount', ['rack shelf', 'rackmount kit', 'component storage', 'mounting shelf', 'mounting kit(?!.*display|.*tv)']),
        ('Mounts', 'Speaker/Mic Mount', ['speaker mount', 'mic mount', 'microphone suspension', 'pendant mount']),

        # 5. Peripherals & Accessories
        ('Peripherals & Accessories', 'Keyboard & Mouse', ['keyboard', 'mouse', r'mk\d+', 'mx master', 'combo touch']),
        ('Peripherals & Accessories', 'Docking Station / Hub', ['docking station', 'usb hub', 'logidock', 'mic pod hub', 'usb-c.*hub', 'thunderbolt.*dock']),
        ('Peripherals & Accessories', 'Remote Control', ['remote control', r'\brc\d+', r'hr-\d+', r'rm-ip\d+']),
        ('Peripherals & Accessories', 'Stylus / Pen', ['stylus', 'pen', 'crayon digital pencil']),
        ('Peripherals & Accessories', 'Whiteboard Camera', ['scribe']),
        ('Peripherals & Accessories', 'IR Emitter/Receiver', ['ir emitter', 'ir receiver', 'ir sensor']),
        ('Peripherals & Accessories', 'Card Reader', ['card reader']),

        # 6. Cables & Connectivity
        ('Cables & Connectivity', 'Cable Retractor / Management', ['retractor', 'cable caddy', 'cable ring', 'cable organizer', 'cable bag']),
        ('Cables & Connectivity', 'AV Cable', ['hdmi cable', 'usb-c cable', 'aoc', 'vga cable', 'audio cable', 'displayport cable', 'bnc cable', 'dvi cable', 'sdi cable']),
        ('Cables & Connectivity', 'Network Cable', ['cat6', 'cat5e', 'utp', 'patch cord', 'ethernet cable', 'rj45 cable']),
        ('Cables & Connectivity', 'Bulk Cable / Wire', ['bulk cable', 'spool', 'reel', r'1000ft', r'305m', 'speaker wire', 'coax.*cable']),
        ('Cables & Connectivity', 'Connectors, Adapters & Dongles', ['adapter', 'connector', 'dongle', 'gender changer', 'terminator', 'coupler', 'adapter ring', 'capture dongle', 'usb capture']),
        ('Cables & Connectivity', 'Fiber Optic', ['fiber optic', 'sfp', 'lc-lc', 'om4', 'singlemode']),

        # 7. Video Conferencing
        ('Video Conferencing', 'Collaboration Display', ['meetingboard', 'collaboration display', 'deskvision', 'surface hub', 'dten d7', r'mb\d{2}-', 'smart collaboration whiteboard', 'all-in-one smart whiteboard', 'neat board']),
        ('Video Conferencing', 'Video Bar', ['video bar', 'meeting bar', 'collaboration bar', 'rally bar', 'poly studio', 'meetup', 'all-in-one.*video', r'a\d{2}-\d{3}', r'\buvc(34|40)\b', 'smartvision', 'conferencecam', 'meetingbar', 'neat bar', 'panacast 50']),
        ('Video Conferencing', 'Room Kit / Codec', ['room kit', 'codec(?!.*cable)', r'mvc\d+', 'mcorekit', 'teams rooms system', 'vc system', 'video conferencing system', r'mvcs\d+', 'g7500', 'thinksmart core', 'uc-engine', r'cs-kit\w+']),
        ('Video Conferencing', 'PTZ Camera', ['ptz camera', 'optical zoom camera', 'tracking camera', r'uvc8\d', r'mb-camera', 'eagleeye', 'ptz pro', 'e70 camera', 'e60 camera', 'precision 60', 'huddly', r'iv-cam-\w+', r'nc-12x80', r'nc-20x60']),
        ('Video Conferencing', 'Webcam / Personal Camera', ['webcam', 'brio', 'c9\d{2}', 'personal video', 'usb camera', 'poly studio p15']),
        ('Video Conferencing', 'Touch Controller / Panel', ['touch controller', 'touch panel', 'tap ip', r'tc\d+\b', r'ctp\d+\b', 'collaboration touch', 'mtouch', 'gc8', 'neat pad', 'touch 10']),
        ('Video Conferencing', 'Scheduling Panel', ['scheduler', 'room booking', 'scheduling panel', 'room panel', r'tss-\d+', 'tap scheduler']),
        ('Video Conferencing', 'VC Phone', ['trio c60', r'mp\d{2}', 'team phone']),

        # 8. Audio
        ('Audio', 'Ceiling Microphone', ['ceiling mic', 'mxa9\d0', 'tcc-2', 'tcc2', r'vcm3\d', r'cm\d{2}\b', r'tcm-x\b', 'ceiling.*microphone']),
        ('Audio', 'Table/Boundary Microphone', ['table mic', 'boundary mic', r'mxa3\d\d', 'rally mic pod', 'ip table microphone', r'vcm35', 'table array', r'cs-mic-table']),
        ('Audio', 'Wireless Microphone System', ['wireless mic', 'wireless microphone', r'vcm\d+w', 'handheld transmitter', 'bodypack transmitter', 'lavalier system', 'sl mcr', 'ulxd', 'mxwapt', 'blx\d+']),
        ('Audio', 'Gooseneck Microphone', ['gooseneck', r'meg \d+']),
        ('Audio', 'Headset / Wearable Mic', ['headset', 'earset', 'zone wireless', 'h\d{3}e', 'lavalier(?!.*system)', 'headworn']),
        ('Audio', 'Speakerphone', ['speakerphone', 'poly sync', 'speak \d+', 'mobile speakerphone']),
        ('Audio', 'DSP / Audio Processor / Mixer', ['dsp', 'digital signal processor', 'audio processor', 'tesira', 'q-sys core', 'biamp', 'p300', 'intellimix', 'audio conferencing processor', 'dmp \d+', 'bss blu', 'avhub', 'audio mixer', 'studiomaster mixer']),
        ('Audio', 'Amplifier', ['amplifier', r'\bamp-\b', r'revamp\d+', 'poweramp', r'\d+\s*x\s*\d+w', 'power amplifier', 'netpa', r'xpa \d+', r'ma\d{4}']),
        ('Audio', 'Loudspeaker / Speaker', ['speaker(?!.*phone)', 'soundbar(?!.*video)', 'loudspeaker', 'pendant speaker', 'in-ceiling speaker', 'ceiling speaker', 'surface mount speaker', r'ad-c\d+', r'ad-s\d+', 'saros', 'control \d+c', r'\bms speaker\b']),
        ('Audio', 'Audio Interface / Extender', ['dante interface', 'audio.*extender', 'audio interface', 'axi \d+', 'usb.*audio.*bridge']),
        ('Audio', 'Intercom System', ['intercom', 'freespeak']),
        ('Audio', 'RF & Antenna', ['antenna', 'combiner', 'splitter(?!.*hdmi)', r'ua\d+']),
        ('Audio', 'Charging Station', ['charging station', r'mxwncs\d', r'chg\d\w+']),
        
        # 9. Displays
        ('Displays', 'Direct-View LED', ['led wall', 'dvled', 'direct.*view.*led', 'absen']),
        ('Displays', 'Video Wall Display', ['video wall(?!.*mount)', 'videowall display']),
        ('Displays', 'Interactive Display', ['interactive display', 'touch display', 'smart board', 'interactive.*monitor', 'ifp\d+', r'rp\d{4}']),
        ('Displays', 'Professional Display', ['display(?!.*mount)', 'monitor(?!.*mount)', 'signage', 'bravia', 'commercial monitor', 'professional display', 'lfd', r'\b(qb|qm|uh|fw-)\d{2}\b', r'me\d{2}\b']),
        ('Displays', 'Projector', ['projector', 'dlp', '3lcd', 'laser projector', r'eb-l\d+', r'vpl-\w+', r'ls\d{3}']),
        
        # 10. Signal Management
        ('Signal Management', 'Matrix Switcher', ['matrix', 'switcher', 'presentations.*switcher', 'dmps', 'crosspoint', r'vm\d{4}', r'vs\d{3}', 'dxp hd']),
        ('Signal Management', 'Extender (TX/RX)', ['extender', 'transmitter', 'receiver', 'hdbaset', 'tx/rx', r'hd-tx\d*', r'hd-rx\d*', 'dphd', 'tps-tx', 'tps-rx', 'dtp', 'tp-\d+r']),
        ('Signal Management', 'Video Wall Processor', ['video wall processor', 'multi screen controller']),
        ('Signal Management', 'Digital Signage Player', ['brightsign', 'media player']),
        ('Signal Management', 'Scaler / Converter / Processor', ['scaler', 'converter', 'scan converter', r'dsc \d+', 'signal processor', 'edid', 'embedder', 'de-embedder', 'annotation processor', 'video capture']),
        ('Signal Management', 'Distribution Amplifier / Splitter', ['distribution amplifier', r'da\dhd', r'hd-da\d+', 'hdmi splitter', 'vs\d{3}a']),
        ('Signal Management', 'AV over IP (Encoder/Decoder)', ['av over ip', 'dm nvx', 'encoder', 'decoder', 'nav e \d+', 'nav sd \d+']),
        
        # 11. Control Systems
        ('Control Systems', 'Control Processor', ['control system', 'control processor', r'cp\d-r', r'rmc\d', 'netlinx', 'ipcp pro', r'nx-\d+']),
        ('Control Systems', 'Touch Panel', ['touch panel(?!.*collaboration)', 'touch screen(?!.*display)', 'modero', r'tsw-\d+', r'tst-\d+']),
        ('Control Systems', 'Keypad', ['keypad', r'c2n-\w+', r'hz-kp\w+', 'ebus button panel']),
        ('Control Systems', 'I/O Interface / Gateway', ['interface', 'gateway', r'exb-io\d', r'cen-io', r'inet-ioex']),
        ('Control Systems', 'Sensor', ['sensor', 'occupancy', 'daylight', 'gls-']),

        # 12. Computers
        ('Computers', 'Desktop / SFF PC', ['desktop', 'optiplex', 'mini conference pc', 'asus nuc']),
        ('Computers', 'Tablet', ['ipad']),
        ('Computers', 'OPS Module', [r'\bops\b', 'pc module']),
        
        # 13. Lighting
        ('Lighting', 'Lighting Control', ['dali', 'lutron', 'qsne', 'dimmer module']),
    ]

    for primary, sub, patterns in category_rules:
        if any(re.search(pattern, text_to_search, re.IGNORECASE) for pattern in patterns):
            return {'primary_category': primary, 'sub_category': sub, 'needs_review': False}

    # Final fallback
    return {'primary_category': 'General AV', 'sub_category': 'Needs Classification', 'needs_review': True}


# --- DATA QUALITY SCORING ---

def score_product_quality(product: Dict[str, Any]) -> Tuple[int, List[str]]:
    score = 100
    issues = []
    if len(product.get('description', '')) < MIN_DESCRIPTION_LENGTH and product['primary_category'] not in ['Software & Services', 'Cables & Connectivity']:
        score -= 20; issues.append(f"Description too short")
    price = product.get('price_usd', 0)
    if price < MIN_PRICE_USD:
        score -= 50; issues.append(f"Price is zero or too low")
    elif price > MAX_PRICE_USD:
        score -= 10; issues.append(f"Price unusually high")
    if not product.get('name'):
        score -= 40; issues.append("Missing generated product name")
    if not product.get('model_number') and product.get('primary_category') not in ['Software & Services', 'Cables & Connectivity']:
        score -= 15; issues.append("Missing model number")
    if product.get('needs_review', False):
        score -= 30; issues.append("Category could not be classified")
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
            inr_price_col = next((c for c in df.columns if any(k in c for k in ['inr', 'buy price', 'mrp']) and 'usd' not in c), None)
            usd_price_col = next((c for c in df.columns if 'usd' in c), None)

            if not desc_col: print(f"  Warning: Could not map required Description column. Skipping."); continue
            
            stats['files_processed'] += 1

            for _, row in df.iterrows():
                stats['products_found'] += 1
                raw_model = row.get(model_col, '')
                raw_description = str(row.get(desc_col, '')).strip()
                if pd.isna(raw_description) or not raw_description: continue

                model_clean = clean_model_number(raw_model) if model_col else ""
                clean_desc = create_clean_description(raw_description, file_brand)
                categories = categorize_product_comprehensively(raw_description, model_clean)
                
                price_inr = clean_price(row.get(inr_price_col, 0)) if inr_price_col else 0
                price_usd = clean_price(row.get(usd_price_col, 0)) if usd_price_col else 0
                
                final_price_usd = price_usd if price_usd > 0 else (price_inr / FALLBACK_INR_TO_USD if price_inr > 0 else 0)

                product = {
                    'brand': file_brand, 'name': generate_product_name(file_brand, model_clean, clean_desc),
                    'model_number': model_clean, 'primary_category': categories['primary_category'],
                    'sub_category': categories['sub_category'], 'price_inr': round(price_inr, 2),
                    'price_usd': round(final_price_usd, 2), 'warranty': extract_warranty(raw_description),
                    'description': clean_desc, 'full_specifications': raw_description,
                    'unit_of_measure': infer_unit_of_measure(raw_description, categories['primary_category']),
                    'min_order_quantity': 1,
                    'lead_time_days': estimate_lead_time(categories['primary_category'], categories['sub_category']),
                    'gst_rate': DEFAULT_GST_RATE, 'image_url': '', 'needs_review': categories['needs_review'],
                    'source_file': filename,
                }
                
                score, issues = score_product_quality(product)
                product['data_quality_score'] = score

                if score < REJECTION_SCORE_THRESHOLD:
                    stats['products_rejected'] += 1; continue
                
                if issues:
                    stats['products_flagged'] += 1
                    validation_log.append({'product': product['name'], 'score': score, 'issues': ', '.join(issues), 'source': filename})
                else:
                    stats['products_valid'] += 1
                
                all_products.append(product)
                
        except Exception as e:
            print(f"  Error processing {filename}: {e}")

    if not all_products: print("\nNo valid products could be processed. Exiting."); return

    final_df = pd.DataFrame(all_products)
    initial_rows = len(final_df)
    
    final_df['model_number_lower'] = final_df['model_number'].str.lower().str.strip()
    final_df.drop_duplicates(subset=['brand', 'model_number_lower'], keep='last', inplace=True)
    final_df.drop(columns=['model_number_lower'], inplace=True)
    
    final_rows = len(final_df)

    print(f"\n{'='*60}\nProcessing Summary:\n{'='*60}")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Total Products Found: {stats['products_found']}")
    print(f"Products Accepted (Score >= {REJECTION_SCORE_THRESHOLD}): {initial_rows}")
    print(f"  - Valid (No Issues): {stats['products_valid']}")
    print(f"  - Flagged for Review: {stats['products_flagged']}")
    print(f"Products Rejected (Score < {REJECTION_SCORE_THRESHOLD}): {stats['products_rejected']}")
    print(f"Duplicates Removed: {initial_rows - final_rows}")
    
    print(f"\nCategory Distribution (Top 15):")
    category_counts = final_df['primary_category'].value_counts()
    for cat, count in category_counts.head(15).items():
        print(f"  - {cat:<25}: {count} products")

    final_df.to_csv(OUTPUT_FILENAME, index=False, encoding='utf-8')
    print(f"\n✅ Created Master Catalog: '{OUTPUT_FILENAME}' with {final_rows} products")

    if validation_log:
        with open(VALIDATION_REPORT, 'w', encoding='utf-8') as f:
            f.write(f"Data Quality Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Items Flagged: {len(validation_log)}\n{'='*60}\n\n")
            for entry in sorted(validation_log, key=lambda x: x['score']):
                f.write(f"Source: {entry['source']}\nProduct: {entry['product']}\nScore: {entry['score']}\nIssues: {entry['issues']}\n\n")
        print(f"ℹ️  Created Validation Report: '{VALIDATION_REPORT}'")
    
    print(f"\n{'='*60}\nBOQ dataset generation complete!\n{'='*60}\n")

if __name__ == "__main__":
    main()
