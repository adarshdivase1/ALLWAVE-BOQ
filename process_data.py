import pandas as pd
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
DATA_FOLDER = 'data'
OUTPUT_FILENAME = 'master_product_catalog.csv'
VALIDATION_REPORT = 'data_quality_report.txt'
HEADER_KEYWORDS = ['description', 'model', 'part', 'price', 'sku', 'item', 'mrp']
DEFAULT_GST_RATE = 18
FALLBACK_INR_TO_USD = 83.5  # Update this regularly or fetch from API

# Quality thresholds
MIN_DESCRIPTION_LENGTH = 10
MAX_PRICE_USD = 50000  # Flag items above this
MIN_PRICE_USD = 1.0
PRICE_OUTLIER_THRESHOLD = 3  # Standard deviations

# --- HELPER FUNCTIONS ---

def find_header_row(file_path: str, keywords: List[str], max_rows: int = 20) -> int:
    """Intelligently find the header row in CSV files."""
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
    """Extract and clean price values."""
    if pd.isna(price_str): return 0.0
    price_str = str(price_str).strip()
    price_str = re.sub(r'[^\d.]', '', price_str)
    if not price_str: return 0.0
    try:
        return float(price_str)
    except ValueError:
        return 0.0

def extract_warranty(description: str) -> str:
    """Extract warranty information from product description."""
    if not isinstance(description, str): return "Not Specified"
    description = description.lower()
    
    # Check for year-based warranty
    match = re.search(r'(\d+)\s*[-]?\s*y(ea)?r[s]?\s*(warranty|wty)?', description)
    if match:
        years = match.group(1)
        return f"{years} Year{'s' if int(years) > 1 else ''}"
    
    # Check for lifetime warranty
    if 'lifetime' in description: 
        return "Lifetime"
    
    # Check for month-based warranty
    match = re.search(r'(\d+)\s*month[s]?\s*(warranty|wty)?', description)
    if match:
        months = match.group(1)
        return f"{months} Month{'s' if int(months) > 1 else ''}"
    
    return "Not Specified"

def clean_model_number(model_str: Any) -> str:
    """Extract and clean model numbers."""
    if pd.isna(model_str): return ""
    model_str = str(model_str).strip().replace('\n', ' ')
    
    # Look for alphanumeric patterns with separators
    potential_models = re.findall(r'([a-zA-Z0-9]+(?:[-/.][a-zA-Z0-9]+)+)', model_str)
    if potential_models:
        return max(potential_models, key=len)
    
    # Fallback to first word
    parts = model_str.split()
    return parts[0] if parts else model_str

def clean_filename_brand(filename: str) -> str:
    """Extract brand name from filename."""
    base_name = re.sub(r'Master List 2\.0.*-|\.csv|\.xlsx', '', filename, flags=re.IGNORECASE).strip()
    
    # Handle multiple brands in filename
    if '&' in base_name: 
        return base_name.split('&')[0].strip()
    if ' and ' in base_name.lower(): 
        return base_name.split(' and ')[0].strip()
    
    return base_name

def create_clean_description(raw_desc: str, max_length: int = 200) -> str:
    """Create a clean, concise description."""
    if not isinstance(raw_desc, str):
        return ""
    
    # Remove excessive whitespace and newlines
    desc = ' '.join(raw_desc.split())
    
    # Remove common filler words at the start
    desc = re.sub(r'^(product|item|description|desc):\s*', '', desc, flags=re.IGNORECASE)
    
    # Truncate if too long
    if len(desc) > max_length:
        desc = desc[:max_length].rsplit(' ', 1)[0] + '...'
    
    return desc.strip()

def generate_product_name(brand: str, model: str, description: str) -> str:
    """Generate a clean, professional product name."""
    # Clean the description
    clean_desc = create_clean_description(description, 80)
    
    # Avoid brand repetition in description
    desc_lower = clean_desc.lower()
    brand_lower = brand.lower()
    
    if desc_lower.startswith(brand_lower):
        clean_desc = clean_desc[len(brand):].strip()
    
    # Build the name
    if model and clean_desc and model.lower() not in clean_desc.lower():
        # Brand + Model + Description
        name = f"{brand} {model} - {clean_desc}"
    elif model:
        # Brand + Model only
        name = f"{brand} {model}"
    elif clean_desc:
        # Brand + Description only
        name = f"{brand} - {clean_desc}"
    else:
        # Brand only (fallback)
        name = brand
    
    return name

def infer_unit_of_measure(description: str, category: str) -> str:
    """Infer the unit of measure from description and category."""
    desc_lower = description.lower() if isinstance(description, str) else ""
    
    # Length-based products
    if any(word in desc_lower for word in ['cable', 'wire', 'spool', 'ft', 'feet', 'meter', 'm']):
        if 'spool' in desc_lower or 'reel' in desc_lower:
            return 'spool'
        return 'meter'
    
    # Kit/Set based products
    if any(word in desc_lower for word in ['kit', 'set', 'pair', 'pack']):
        if 'pair' in desc_lower:
            return 'pair'
        return 'set'
    
    # Default to piece for most AV equipment
    return 'piece'

def estimate_lead_time(category: str, sub_category: str) -> int:
    """Estimate lead time in days based on product category."""
    # Complex custom systems
    if 'Commissioning' in sub_category or 'Integration' in sub_category:
        return 45
    
    # Video walls and custom displays
    if 'Video Wall' in sub_category or 'Direct-View LED' in category:
        return 30
    
    # Control systems and processors
    if category in ['Control Systems', 'Video Processing']:
        return 21
    
    # Standard AV equipment
    if category in ['Video Conferencing', 'Audio', 'Displays']:
        return 14
    
    # Cables and accessories
    if category in ['Cables & Connectivity', 'Mounts']:
        return 7
    
    # Default
    return 14

# --- CATEGORIZATION ENGINE ---

def categorize_product_comprehensively(description: str, model: str) -> Dict[str, str]:
    """Enhanced categorization with better fallback handling."""
    text_to_search = (str(description) + ' ' + str(model)).lower()
    
    category_rules = [
        # Peripherals
        ('Peripherals', 'Keyboard / Mouse', ['keyboard', 'mouse', 'km3322w', 'wireless combo']),
        ('Peripherals', 'PC / Compute', ['nuc', 'ops', 'mini-pc', 'optiplex', 'desktop', 'compute stick']),
        
        # Video Conferencing
        ('Video Conferencing', 'Collaboration Display', ['dten', 'surface hub', 'collaboration display', 'meetingboard', 'avocor', 'interactive touch moniter']),
        ('Video Conferencing', 'Video Bar', ['video bar', 'rally bar', 'poly studio', 'meetup', 'cisco room bar', 'panacast 50', 'uvc40', 'uvc34']),
        ('Video Conferencing', 'Room Kit / Codec', ['room kit', 'codec', 'g7500', 'cs-kit', 'spark kit', 'plus kit', 'mvc400']),
        ('Video Conferencing', 'PTZ Camera', ['ptz camera', 'e-ptz', 'ptz4k', 'eagleeye', 'unicam', 'rally camera']),
        ('Video Conferencing', 'Webcam / Personal Camera', ['webcam', 'brio', 'c930', 'personal video', 'c920']),
        ('Video Conferencing', 'Touch Controller', ['touch controller', 'tap ip', 'tc8', 'tc10', 'crestron mercury', 'ctp18']),
        ('Video Conferencing', 'Scheduling Panel', ['scheduler', 'room booking', 'tap scheduler', 'tss-770', '6511330']),
        ('Video Conferencing', 'Wireless Presentation', ['clickshare', 'airtame', 'via connect', 'wireless presentation', 'wpp30']),
        
        # Audio
        ('Audio', 'DSP / Processor', ['dsp', 'digital signal processor', 'tesira', 'q-sys core', 'biamp', 'p300', 'intellimix']),
        ('Audio', 'Ceiling Microphone', ['ceiling mic', 'mxa910', 'mxa920', 'tcc2', 'tcm-x']),
        ('Audio', 'Table Microphone', ['table mic', 'boundary mic', 'mxw6', 'conference phone', 'speak 750', 'cs-mic-table']),
        ('Audio', 'Gooseneck Microphone', ['gooseneck', 'podium mic']),
        ('Audio', 'Wireless Microphone System', ['wireless mic', 'bodypack', 'handheld transmitter', 'lavalier', 'headworn', 'ulxd']),
        ('Audio', 'Amplifier', ['amplifier', 'amp', 'poweramp', 'ma2120', 'pa-120z']),
        ('Audio', 'Loudspeaker', ['speaker', 'soundbar', 'ceiling speaker', 'pendant speaker', 'control 16c', 'mask6ct']),
        ('Audio', 'Audio Interface / Expander', ['dante interface', 'ex-ubt', 'usb expander', 'qio-ml4i']),
        
        # Displays
        ('Displays', 'Interactive Display', ['interactive', 'touch display', 'smart board', 'flip', 'benq rp', 'newline']),
        ('Displays', 'Professional Display', ['display', 'monitor', 'uhd signage', 'bravia', 'commercial monitor', 'large format display']),
        ('Displays', 'Video Wall Display', ['video wall display', 'un552v']),
        ('Displays', 'Direct-View LED', ['led wall', 'dvled', 'absen', 'direct view', 'curved led']),
        ('Displays', 'Projector', ['projector', 'dlp', 'lcd projector', 'eb-l530u']),
        
        # Video Processing
        ('Video Processing', 'Annotation Processor', ['annotation processor']),
        ('Video Processing', 'Video Wall Controller', ['video wall controller', 'g44', 'seada']),
        ('Video Processing', 'Media Player / Signage', ['brightsign', 'media player', 'signage player']),
        ('Video Processing', 'Capture & Streaming', ['capture card', 'capture dongle', 'pearl nano', 'epiphan']),
        
        # Control Systems
        ('Control Systems', 'Control Processor', ['control processor', 'dmps', 'cp4n', 'core 110f']),
        ('Control Systems', 'Touch Panel', ['touch panel', 'touch screen', 'tsw-', 'ts-1070']),
        ('Control Systems', 'Keypad', ['keypad', 'seetouch', 'audio control panel']),
        
        # Signal Management
        ('Signal Management', 'Matrix Switcher', ['matrix', 'switcher', 'dm-md', 'vm0808']),
        ('Signal Management', 'Extender (TX/RX)', ['extender', 'transmitter', 'receiver', 'dtp', 'xtp', 'hdbaset']),
        
        # Cables & Connectivity
        ('Cables & Connectivity', 'AV Cable', ['hdmi cable', 'usb-c cable', 'active optical', 'aoc', 'usb 3.2', 'vga', 'audio cable', 'rs-232', 'fiber optic', 'displayport']),
        ('Cables & Connectivity', 'Wall & Table Plate', ['wall plate', 'tbus', 'hydraport', 'cable cubby', 'faceplate']),
        
        # Infrastructure
        ('Infrastructure', 'AV Rack', ['rack', 'enclosure', 'credenza', 'ptrk', r'\d+u rack', 'heckler av cart', 'av frames']),
        ('Infrastructure', 'Network Switch', ['switch', 'network switch', 'poe switch', 'sg350-10']),
        ('Infrastructure', 'Power (PDU/UPS)', ['pdu', 'ups', 'power strip', 'power distribution', 'power conditioner']),
        
        # Mounts
        ('Mounts', 'Display Mount / Cart', ['wall mount', 'display mount', 'trolley', 'cart', 'floor stand', 'fusion', 'mobile stand']),
        ('Mounts', 'Camera Mount', ['camera mount', 'cam-mount', 'brkt-qcam-wmk']),
        
        # Services
        ('Services', 'Commissioning & Integration', ['commissioning', 'integration', 'installation', 'setup service']),
    ]
    
    for primary, sub, patterns in category_rules:
        if any(re.search(pattern, text_to_search, re.IGNORECASE) for pattern in patterns):
            return {
                'primary_category': primary,
                'sub_category': sub,
                'needs_review': False
            }
    
    # Fallback with review flag
    return {
        'primary_category': 'General AV',
        'sub_category': 'Needs Classification',
        'needs_review': True
    }

def validate_product_quality(product: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate product data quality and return issues."""
    issues = []
    
    # Check description length
    if len(product.get('features', '')) < MIN_DESCRIPTION_LENGTH:
        issues.append("Description too short")
    
    # Check price range
    price = product.get('price', 0)
    if price < MIN_PRICE_USD:
        issues.append(f"Price too low (${price:.2f})")
    elif price > MAX_PRICE_USD:
        issues.append(f"Price unusually high (${price:.2f}) - needs review")
    
    # Check for missing critical fields
    if not product.get('name'):
        issues.append("Missing product name")
    
    if product.get('needs_review', False):
        issues.append("Category needs manual review")
    
    # Determine if product passes validation
    is_valid = len([i for i in issues if 'needs review' not in i.lower()]) == 0
    
    return is_valid, issues

# --- MAIN SCRIPT EXECUTION ---

def main():
    all_products: List[Dict] = []
    validation_log = []
    stats = {
        'files_processed': 0,
        'products_found': 0,
        'products_valid': 0,
        'products_flagged': 0,
        'products_rejected': 0
    }
    
    if not os.path.exists(DATA_FOLDER):
        print(f"Error: The '{DATA_FOLDER}' directory was not found.")
        return

    csv_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    print(f"Starting BOQ dataset generation...")
    print(f"Found {len(csv_files)} CSV files to process\n")

    for filename in csv_files:
        file_path = os.path.join(DATA_FOLDER, filename)
        file_brand = clean_filename_brand(filename)
        print(f"Processing: '{filename}' (Brand: {file_brand})")

        try:
            header_row = find_header_row(file_path, HEADER_KEYWORDS)
            df = pd.read_csv(file_path, header=header_row, encoding='latin1', 
                           on_bad_lines='skip', dtype=str)
            df.dropna(how='all', inplace=True)
            df.columns = [str(col).lower().strip() for col in df.columns]

            # Column mapping
            model_col = next((c for c in df.columns if any(k in c for k in ['model no', 'part no', 'sku', 'model'])), None)
            desc_col = next((c for c in df.columns if 'desc' in c), None)
            inr_price_col = next((c for c in df.columns if any(k in c for k in ['inr', 'mrp', 'buy price'])), None)
            usd_price_col = next((c for c in df.columns if 'usd' in c), None)

            if not model_col or not desc_col:
                print(f"  Warning: Could not map required columns. Skipping.")
                continue
            
            stats['files_processed'] += 1
            
            for _, row in df.iterrows():
                raw_model = row.get(model_col, '')
                if pd.isna(raw_model) or not str(raw_model).strip(): 
                    continue

                stats['products_found'] += 1
                
                # Extract and clean data
                model_clean = clean_model_number(raw_model)
                description = str(row.get(desc_col, '')).strip()
                
                categories = categorize_product_comprehensively(description, model_clean)
                
                # Price handling
                price_inr = clean_price(row.get(inr_price_col, 0))
                price_usd = clean_price(row.get(usd_price_col, 0))
                final_price_usd = price_usd if price_usd > 0 else (price_inr / FALLBACK_INR_TO_USD if price_inr > 0 else 0)
                
                if final_price_usd <= 0: 
                    continue

                # Generate clean product name
                product_name = generate_product_name(file_brand, model_clean, description)
                
                # Create product record
                product = {
                    'brand': file_brand,
                    'name': product_name,
                    'model_number': model_clean,
                    'primary_category': categories['primary_category'],
                    'sub_category': categories['sub_category'],
                    'price_usd': round(final_price_usd, 2),
                    'warranty': extract_warranty(description),
                    'description': create_clean_description(description),
                    'full_specifications': description,
                    'unit_of_measure': infer_unit_of_measure(description, categories['primary_category']),
                    'min_order_quantity': 1,
                    'lead_time_days': estimate_lead_time(categories['primary_category'], categories['sub_category']),
                    'gst_rate': DEFAULT_GST_RATE,
                    'image_url': '',
                    'needs_review': categories['needs_review'],
                    'data_quality_score': 0  # Will be calculated
                }
                
                # Validate product
                is_valid, issues = validate_product_quality(product)
                
                if is_valid:
                    stats['products_valid'] += 1
                    product['data_quality_score'] = 100
                elif issues:
                    stats['products_flagged'] += 1
                    product['data_quality_score'] = 70
                    validation_log.append({
                        'product': product_name,
                        'issues': ', '.join(issues)
                    })
                else:
                    stats['products_rejected'] += 1
                    continue
                
                all_products.append(product)
                
        except Exception as e:
            print(f"  Error processing {filename}: {e}")

    if not all_products:
        print("\nNo valid products found. Exiting.")
        return

    # Create DataFrame
    final_df = pd.DataFrame(all_products)
    print(f"\n{'='*60}")
    print(f"Processing Summary:")
    print(f"{'='*60}")
    print(f"Files processed: {stats['files_processed']}")
    print(f"Products found: {stats['products_found']}")
    print(f"Products valid: {stats['products_valid']}")
    print(f"Products flagged for review: {stats['products_flagged']}")
    print(f"Products rejected: {stats['products_rejected']}")

    # Deduplication
    initial_rows = len(final_df)
    final_df.drop_duplicates(subset=['name'], keep='last', inplace=True)
    final_rows = len(final_df)
    print(f"\nRemoved {initial_rows - final_rows} duplicate entries")

    # Category distribution
    print(f"\nCategory Distribution:")
    category_counts = final_df['primary_category'].value_counts()
    for cat, count in category_counts.head(10).items():
        print(f"  {cat}: {count}")

    # Save main catalog
    final_df.to_csv(OUTPUT_FILENAME, index=False)
    print(f"\nCreated: '{OUTPUT_FILENAME}' with {final_rows} products")

    # Save validation report
    if validation_log:
        with open(VALIDATION_REPORT, 'w') as f:
            f.write("Data Quality Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")
            for entry in validation_log:
                f.write(f"Product: {entry['product']}\n")
                f.write(f"Issues: {entry['issues']}\n\n")
        print(f"Created: '{VALIDATION_REPORT}' with {len(validation_log)} flagged items")

    print(f"\n{'='*60}")
    print("BOQ dataset generation complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
