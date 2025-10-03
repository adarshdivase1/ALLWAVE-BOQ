import pandas as pd
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
DATA_FOLDER = 'data'
OUTPUT_FILENAME = 'master_product_catalog_revised.csv'
VALIDATION_REPORT = 'data_quality_report_revised.txt'
HEADER_KEYWORDS = ['description', 'model', 'part', 'price', 'sku', 'item', 'mrp']
DEFAULT_GST_RATE = 18
FALLBACK_INR_TO_USD = 83.5  # Update this regularly or fetch from API

# --- QUALITY THRESHOLDS (REVISED) ---
MIN_DESCRIPTION_LENGTH = 20  # Increased for more meaningful descriptions
MAX_PRICE_USD = 50000
MIN_PRICE_USD = 1.0
REJECTION_SCORE_THRESHOLD = 40 # Products below this score will be dropped

# --- HELPER FUNCTIONS ---

def find_header_row(file_path: str, keywords: List[str], max_rows: int = 20) -> int:
    """Intelligently find the header row in CSV files."""
    encodings_to_try = ['utf-8', 'latin1', 'cp1252']
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= max_rows: break
                    # Require at least 2 keywords for a confident match
                    if sum(keyword.lower() in line.lower() for keyword in keywords) >= 2:
                        return i
        except Exception:
            continue
    return 0 # Default to the first row if no header is found

def clean_price(price_str: Any) -> float:
    """Extract and clean price values."""
    if pd.isna(price_str): return 0.0
    price_str = str(price_str).strip()
    # Remove currency symbols, commas, etc., but keep the decimal point
    price_str = re.sub(r'[^\d.]', '', price_str)
    if not price_str: return 0.0
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def extract_warranty(description: str) -> str:
    """Extract warranty information from product description."""
    if not isinstance(description, str): return "Not Specified"
    desc_lower = description.lower()

    # More specific regex to avoid capturing random numbers
    match = re.search(r'(\d+)\s*[-]?\s*y(ea)?r[s]?\s*(warranty|wty)', desc_lower)
    if match:
        years = match.group(1)
        return f"{years} Year{'s' if int(years) > 1 else ''}"

    if 'lifetime' in desc_lower:
        return "Lifetime"

    match = re.search(r'(\d+)\s*month[s]?\s*(warranty|wty)', desc_lower)
    if match:
        months = match.group(1)
        return f"{months} Month{'s' if int(months) > 1 else ''}"

    return "Not Specified"

def clean_model_number(model_str: Any) -> str:
    """Extract and clean model numbers."""
    if pd.isna(model_str): return ""
    model_str = str(model_str).strip().replace('\n', ' ')
    
    # Prioritize patterns with letters and numbers, common in AV
    potential_models = re.findall(r'[a-zA-Z]{1,4}[- ]?\d+[- ]?[a-zA-Z0-9-]*', model_str)
    if potential_models:
        # Return the longest, most specific match
        return max(potential_models, key=len).strip()
        
    # Fallback for purely numeric or different patterns
    potential_models = re.findall(r'([a-zA-Z0-9]+(?:[-/.][a-zA-Z0-9]+)+)', model_str)
    if potential_models:
        return max(potential_models, key=len).strip()

    return model_str.split(' ')[0]

def clean_filename_brand(filename: str) -> str:
    """Extract a clean brand name from the filename."""
    # Remove common prefixes, suffixes, and extensions
    base_name = re.sub(r'Master List.*-|\.csv|\.xlsx', '', filename, flags=re.IGNORECASE).strip()
    
    # Handle multiple brands separated by '&' or 'and'
    base_name = re.split(r'\s*&\s*|\s+and\s+', base_name, flags=re.IGNORECASE)[0]
    
    return base_name.strip()

def create_clean_description(raw_desc: str, brand: str, max_length: int = 200) -> str:
    """Create a clean, concise, and meaningful description."""
    if not isinstance(raw_desc, str): return ""

    # Remove excessive whitespace and normalize
    desc = ' '.join(raw_desc.split())
    
    # Remove repetitive prefixes
    desc = re.sub(r'^(product|item|description|desc)\s*[:\-]\s*', '', desc, flags=re.IGNORECASE)

    # Remove the brand name if it's just a prefix to avoid redundancy
    if desc.lower().startswith(brand.lower()):
        desc = desc[len(brand):].lstrip(' -:')

    # Check for unhelpful descriptions (e.g., just a color or brand name)
    if desc.lower() in [brand.lower(), 'black', 'white', 'gray', 'silver', 'na', 'n/a']:
        return "" # Return empty string if description is not useful

    # Truncate long descriptions gracefully
    if len(desc) > max_length:
        desc = desc[:max_length].rsplit(' ', 1)[0] + '...'
        
    return desc.strip()

def generate_product_name(brand: str, model: str, description: str) -> str:
    """Generate a clean, professional product name, avoiding brand repetition."""
    name_parts = [brand]
    
    # Add model number if it exists and is not already in the brand name
    if model and model.lower() not in brand.lower():
        name_parts.append(model)
        
    # Add description if it exists and is not redundant
    if description:
        # Check if description is already covered by brand/model
        combined_lower = (brand + ' ' + model).lower()
        if description.lower() not in combined_lower:
            name_parts.append(f"- {description}")
            
    return ' '.join(name_parts)

def infer_unit_of_measure(description: str, category: str) -> str:
    """
    Revised UoM logic to correctly identify pieces vs. bulk items.
    This is critical for accurate BOQ generation.
    """
    desc_lower = str(description).lower()
    
    # 1. Bulk Cable/Wire sold by length
    if 'spool' in desc_lower or 'reel' in desc_lower or 'box of' in desc_lower:
        return 'spool'
    
    # 2. Pre-terminated cables (individual items)
    # This regex looks for patterns like 10ft, 10 ft, 12', 3m, 3 m etc.
    if 'cable' in desc_lower and re.search(r'\d+\s*(ft|feet|m|meter|inch|\'|\")', desc_lower):
        return 'piece'
        
    # 3. Kits, Sets, or Pairs
    if 'kit' in desc_lower or 'system' in desc_lower:
        return 'set'
    if 'pair' in desc_lower:
        return 'pair'
    if 'pack' in desc_lower or 'pack of' in desc_lower:
        return 'pack'
        
    # 4. Default for all other electronics, mounts, and accessories is 'piece'
    return 'piece'

def estimate_lead_time(category: str, sub_category: str) -> int:
    """Estimate lead time in days based on product category."""
    if 'Commissioning' in sub_category or 'Integration' in sub_category: return 45
    if 'Video Wall' in sub_category or 'Direct-View LED' in category: return 30
    if category in ['Control Systems', 'Video Processing', 'DSP']: return 21
    if category in ['Video Conferencing', 'Audio', 'Displays']: return 14
    if category in ['Cables & Connectivity', 'Mounts', 'Infrastructure']: return 7
    return 14 # Default lead time

# --- CATEGORIZATION ENGINE (ENHANCED) ---

def categorize_product_comprehensively(description: str, model: str) -> Dict[str, Any]:
    """Enhanced categorization with more rules and better fallback handling."""
    text_to_search = (str(description) + ' ' + str(model)).lower()
    
    # More extensive ruleset
    category_rules = [
        # Peripherals
        ('Peripherals', 'Keyboard / Mouse', ['keyboard', 'mouse', 'km3322w', 'wireless combo']),
        ('Peripherals', 'PC / Compute', ['nuc', 'ops', 'mini-pc', 'optiplex', 'desktop', 'compute stick', 'thinkcentre']),
        
        # Video Conferencing
        ('Video Conferencing', 'Collaboration Display', ['dten', 'surface hub', 'collaboration display', 'meetingboard', 'webex board']),
        ('Video Conferencing', 'Video Bar', ['video bar', 'rally bar', 'poly studio', 'meetup', 'cisco room bar', 'panacast 50', 'uvc40']),
        ('Video Conferencing', 'Room Kit / Codec', ['room kit', 'codec', 'g7500', 'cs-kit', 'spark kit', 'plus kit', 'mvc']),
        ('Video Conferencing', 'PTZ Camera', ['ptz camera', 'e-ptz', 'ptz4k', 'eagleeye', 'unicam', 'rally camera', 'uvc84', 'uvc86']),
        ('Video Conferencing', 'Webcam / Personal Camera', ['webcam', 'brio', 'c930', 'personal video', 'c920', 'logi dock']),
        ('Video Conferencing', 'Touch Controller', ['touch controller', 'tap ip', 'tc8', 'tc10', 'crestron mercury', 'ctp18', 'webex navigator']),
        ('Video Conferencing', 'Scheduling Panel', ['scheduler', 'room booking', 'tap scheduler', 'tss-770', 'g-10t']),
        ('Video Conferencing', 'Wireless Presentation', ['clickshare', 'cse-200', 'c-10', 'airtame', 'via connect', 'wpp30', 'instashow']),
        
        # Audio
        ('Audio', 'DSP / Processor', ['dsp', 'digital signal processor', 'tesira', 'q-sys core', 'biamp', 'p300', 'intellimix', 'dm-dsp']),
        ('Audio', 'Ceiling Microphone', ['ceiling mic', 'mxa910', 'mxa920', 'tcc2', 'tcm-x', 'parle tcm']),
        ('Audio', 'Table Microphone', ['table mic', 'boundary mic', 'conference phone', 'speak 750', 'cs-mic-table', 'mxa310', 'poly sync']),
        ('Audio', 'Amplifier', ['amplifier', 'amp', 'poweramp', 'xpa', 'net-amps']),
        ('Audio', 'Loudspeaker', ['speaker', 'soundbar', 'ceiling speaker', 'pendant speaker', 'saros', 'control 16c', 'ds16']),
        ('Audio', 'Audio Interface / Expander', ['dante interface', 'ex-ubt', 'usb expander', 'qio-ml4i', 'anav-4z-df']),
        
        # Displays
        ('Displays', 'Interactive Display', ['interactive', 'touch display', 'smart board', 'flip', 'benq rp', 'viewboard']),
        ('Displays', 'Professional Display', ['display', 'monitor', 'signage', 'bravia', 'commercial monitor', 'lfd', 'large format']),
        ('Displays', 'Video Wall Display', ['video wall', 'un552v', 'th-55lfv']),
        ('Displays', 'Direct-View LED', ['led wall', 'dvled', 'absen', 'direct view', 'crystal led']),
        ('Displays', 'Projector', ['projector', 'dlp', 'lcd projector', 'eb-l530u', 'pt-vz']),
        
        # Signal Management
        ('Signal Management', 'Matrix Switcher', ['matrix', 'switcher', 'dm-md', 'dmp 128', 'at-ome-ms']),
        ('Signal Management', 'Extender (TX/RX)', ['extender', 'transmitter', 'receiver', 'dtp', 'xtp', 'hdbaset', 'dm tx', 'dm rmc']),
        ('Signal Management', 'Distribution Amplifier', ['da2 hd', 'distribution amp', 'hdmi splitter']),
        ('Signal Management', 'Scaler / Converter', ['scaler', 'converter', 'hd-sdi to hdmi', 'dsc 301']),
        
        # Cables & Connectivity
        ('Cables & Connectivity', 'AV Cable', ['hdmi', 'usb-c', 'aoc', 'vga', 'audio cable', 'rs-232', 'fiber optic', 'displayport', 'cat6', 'rg6']),
        ('Cables & Connectivity', 'Bulk Cable / Wire', ['bulk', 'spool', 'reel', '24-4p-gy-1000']),
        ('Cables & Connectivity', 'Wall & Table Plate', ['wall plate', 'tbus', 'hydraport', 'cable cubby', 'faceplate', 'aap plate']),
        
        # Infrastructure
        ('Infrastructure', 'AV Rack', ['rack', 'enclosure', 'credenza', 'ptrk', r'\d+u rack', 'av cart', 'av frame']),
        ('Infrastructure', 'Network Switch', ['switch', 'poe switch', 'sg350-10', 'cbs250']),
        ('Infrastructure', 'Power (PDU/UPS)', ['pdu', 'ups', 'power strip', 'power distribution', 'power conditioner']),
        
        # Mounts
        ('Mounts', 'Display Mount / Cart', ['wall mount', 'display mount', 'trolley', 'cart', 'floor stand', 'fusion', 'chief']),
    ]
    
    for primary, sub, patterns in category_rules:
        if any(re.search(r'\b' + pattern + r'\b', text_to_search, re.IGNORECASE) for pattern in patterns):
            return {'primary_category': primary, 'sub_category': sub, 'needs_review': False}
    
    # Fallback with review flag
    return {'primary_category': 'General AV', 'sub_category': 'Needs Classification', 'needs_review': True}

# --- DATA QUALITY SCORING (REVISED) ---

def score_product_quality(product: Dict[str, Any]) -> Tuple[int, List[str]]:
    """Scores product data quality out of 100 and returns issues."""
    score = 100
    issues = []
    
    description = product.get('description', '')
    if len(description) < MIN_DESCRIPTION_LENGTH:
        score -= 20
        issues.append(f"Description too short ({len(description)} chars)")

    price = product.get('price_usd', 0)
    if price < MIN_PRICE_USD:
        score -= 50
        issues.append(f"Price is zero or too low (${price:.2f})")
    elif price > MAX_PRICE_USD:
        score -= 10 # Flag, but don't penalize heavily
        issues.append(f"Price unusually high (${price:.2f}) - needs review")
        
    if not product.get('name'):
        score -= 40
        issues.append("Missing generated product name")
        
    if not product.get('model_number'):
        score -= 20
        issues.append("Missing model number")

    if product.get('needs_review', False):
        score -= 25
        issues.append("Category could not be classified")
        
    return max(0, score), issues

# --- MAIN SCRIPT EXECUTION ---

def main():
    all_products: List[Dict] = []
    validation_log = []
    stats = {
        'files_processed': 0, 'products_found': 0, 'products_valid': 0,
        'products_flagged': 0, 'products_rejected': 0
    }
    
    if not os.path.exists(DATA_FOLDER):
        print(f"Error: The '{DATA_FOLDER}' directory was not found.")
        return

    csv_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith('.csv')]
    print(f"Starting BOQ dataset generation...")
    print(f"Found {len(csv_files)} CSV files to process.\n")

    for filename in csv_files:
        file_path = os.path.join(DATA_FOLDER, filename)
        file_brand = clean_filename_brand(filename)
        print(f"Processing: '{filename}' (Brand: {file_brand})")

        try:
            header_row = find_header_row(file_path, HEADER_KEYWORDS)
            df = pd.read_csv(file_path, header=header_row, encoding='latin1', on_bad_lines='skip', dtype=str)
            df.dropna(how='all', inplace=True)
            df.columns = [str(col).lower().strip() for col in df.columns]

            # Dynamic column mapping
            model_col = next((c for c in df.columns if any(k in c for k in ['model no', 'part no', 'sku', 'model'])), None)
            desc_col = next((c for c in df.columns if any(k in c for k in ['description', 'desc', 'product name'])), None)
            inr_price_col = next((c for c in df.columns if any(k in c for k in ['inr', 'mrp', 'buy price'])), None)
            usd_price_col = next((c for c in df.columns if 'usd' in c), None)

            if not model_col or not desc_col:
                print(f"  Warning: Could not map required Model/Description columns. Skipping.")
                continue
            
            stats['files_processed'] += 1
            
            for _, row in df.iterrows():
                stats['products_found'] += 1
                
                raw_model = row.get(model_col, '')
                if pd.isna(raw_model) or not str(raw_model).strip():
                    continue

                # --- Data Extraction and Cleaning ---
                model_clean = clean_model_number(raw_model)
                raw_description = str(row.get(desc_col, '')).strip()
                clean_desc = create_clean_description(raw_description, file_brand)
                
                # --- Categorization ---
                categories = categorize_product_comprehensively(raw_description, model_clean)
                
                # --- Price Handling ---
                price_inr = clean_price(row.get(inr_price_col, 0))
                price_usd = clean_price(row.get(usd_price_col, 0))
                final_price_usd = price_usd if price_usd > 0 else (price_inr / FALLBACK_INR_TO_USD)
                
                # --- Product Record Creation ---
                product = {
                    'brand': file_brand,
                    'name': generate_product_name(file_brand, model_clean, clean_desc),
                    'model_number': model_clean,
                    'primary_category': categories['primary_category'],
                    'sub_category': categories['sub_category'],
                    'price_usd': round(final_price_usd, 2),
                    'warranty': extract_warranty(raw_description),
                    'description': clean_desc,
                    'full_specifications': raw_description,
                    'unit_of_measure': infer_unit_of_measure(raw_description, categories['primary_category']),
                    'min_order_quantity': 1,
                    'lead_time_days': estimate_lead_time(categories['primary_category'], categories['sub_category']),
                    'gst_rate': DEFAULT_GST_RATE,
                    'image_url': '',
                    'needs_review': categories['needs_review'],
                    'source_file': filename,
                }
                
                # --- Validation and Scoring ---
                score, issues = score_product_quality(product)
                product['data_quality_score'] = score
                
                if score < REJECTION_SCORE_THRESHOLD:
                    stats['products_rejected'] += 1
                    continue
                
                if issues:
                    stats['products_flagged'] += 1
                    validation_log.append({
                        'product': product['name'],
                        'score': score,
                        'issues': ', '.join(issues)
                    })
                else:
                    stats['products_valid'] += 1

                all_products.append(product)
                
        except Exception as e:
            print(f"  Error processing {filename}: {e}")

    if not all_products:
        print("\nNo valid products could be processed. Exiting.")
        return

    # --- Final DataFrame Assembly ---
    final_df = pd.DataFrame(all_products)
    
    # --- Deduplication ---
    initial_rows = len(final_df)
    # Deduplicate based on a combination of brand and model number for better accuracy
    final_df.drop_duplicates(subset=['brand', 'model_number'], keep='last', inplace=True)
    final_rows = len(final_df)
    
    # --- Reporting ---
    print(f"\n{'='*60}")
    print(f"Processing Summary:")
    print(f"{'='*60}")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Total Products Found: {stats['products_found']}")
    print(f"Products Accepted (Score >= {REJECTION_SCORE_THRESHOLD}): {final_rows}")
    print(f"  - Valid (Score 100): {stats['products_valid']}")
    print(f"  - Flagged for Review: {stats['products_flagged']}")
    print(f"Products Rejected (Score < {REJECTION_SCORE_THRESHOLD}): {stats['products_rejected']}")
    print(f"Duplicates Removed: {initial_rows - final_rows}")

    print(f"\nTop 10 Category Distribution:")
    category_counts = final_df['primary_category'].value_counts()
    for cat, count in category_counts.head(10).items():
        print(f"  - {cat:<25}: {count} products")

    # --- Save Outputs ---
    final_df.to_csv(OUTPUT_FILENAME, index=False)
    print(f"\n✅ Created Master Catalog: '{OUTPUT_FILENAME}' with {final_rows} products")

    if validation_log:
        with open(VALIDATION_REPORT, 'w') as f:
            f.write("Data Quality Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Items Flagged: {len(validation_log)}\n")
            f.write("="*60 + "\n\n")
            for entry in sorted(validation_log, key=lambda x: x['score']):
                f.write(f"Product: {entry['product']}\n")
                f.write(f"Score: {entry['score']}\n")
                f.write(f"Issues: {entry['issues']}\n\n")
        print(f"ℹ️  Created Validation Report: '{VALIDATION_REPORT}'")

    print(f"\n{'='*60}")
    print("BOQ dataset generation complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
