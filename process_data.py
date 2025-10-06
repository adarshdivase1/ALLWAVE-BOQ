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

# --- ENHANCED V6.0 CATEGORIZATION ENGINE ---

def categorize_product_comprehensively(description: str, model: str) -> Dict[str, Any]:
    """
    Enhanced categorization with broader pattern matching and better fallback logic.
    Priority order matters - most specific rules first.
    """
    text_to_search = (str(description) + ' ' + str(model)).lower()
    
    # Helper function for pattern matching
    def matches_any(patterns):
        return any(re.search(pattern, text_to_search, re.IGNORECASE) for pattern in patterns)
    
    # PRIORITY 1: Software & Services (Must be caught first)
    if matches_any([r'\d+\s*y(ea)?r.*warranty', r'\d+\s*y(ea)?r.*support', 'poly\+', 'partner premier', 
                    'jumpstart', 'onsite support', r'\bcon-snt\b', r'\bcon-ecdn\b', 'smartcare',
                    'maintenance contract', 'support contract', 'extended warranty']):
        # Whitelist known hardware that has warranty in description
        hardware_brands = ['extron', 'biamp', 'qsc', 'crestron', 'shure']
        if not any(brand in text_to_search for brand in hardware_brands):
            return {'primary_category': 'Software & Services', 'sub_category': 'Support & Warranty', 'needs_review': False}
    
    if matches_any(['license', 'licensing', 'saas', 'software license', 'subscription', 'annual license',
                    r'l-kit\w+-ms', 'cloud license']):
        return {'primary_category': 'Software & Services', 'sub_category': 'Software License', 'needs_review': False}
    
    if matches_any(['cloud service', 'cloud platform', 'bsn.cloud', 'xiocloud', 'cloud management']):
        return {'primary_category': 'Software & Services', 'sub_category': 'Cloud Service', 'needs_review': False}

    # PRIORITY 2: Video Conferencing (Before cameras/displays to catch room systems)
    if matches_any(['meetingboard', 'collaboration display', 'deskvision', 'surface hub', 'dten d7',
                    r'mb\d{2}-', 'smart collaboration whiteboard', 'all-in-one smart whiteboard',
                    'neat board', 'interactive whiteboard.*teams', 'teams board']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'Collaboration Display', 'needs_review': False}
    
    if matches_any(['video bar', 'meeting bar', 'collaboration bar', 'rally bar', 'poly studio.*bar',
                    'meetup', r'a\d{2}-\d{3}', r'\buvc(34|40)\b', 'smartvision', 'conferencecam',
                    'meetingbar', 'neat bar', 'panacast 50', 'all-in-one.*conferencing',
                    'soundbar.*video', 'videobar']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'Video Bar', 'needs_review': False}
    
    if matches_any(['room kit', 'codec(?!.*cable)', r'mvc\d+', 'mcorekit', 'teams rooms system',
                    'vc system', 'video conferencing system', r'mvcs\d+', 'g7500', 'thinksmart core',
                    'uc-engine', r'cs-kit\w+', 'room system', 'conferencing system', 'teams room']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'needs_review': False}
    
    if matches_any(['ptz camera', 'pan.*tilt.*zoom', 'optical zoom camera', 'tracking camera',
                    r'uvc8\d', r'mb-camera', 'eagleeye', 'ptz pro', 'e70 camera', 'e60 camera',
                    'precision 60', 'huddly.*camera', r'iv-cam-\w+', r'nc-12x80', r'nc-20x60',
                    'ptz pro', 'conference camera.*zoom']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'PTZ Camera', 'needs_review': False}
    
    if matches_any(['webcam', 'brio', r'c9\d{2}', 'personal video', 'usb camera(?!.*ptz)',
                    'poly studio p15', 'usb.*webcam', 'hd camera(?!.*ptz)', '4k camera(?!.*ptz)']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'Webcam / Personal Camera', 'needs_review': False}
    
    if matches_any(['touch controller(?!.*lighting)', 'touch panel.*conferenc', 'tap ip', r'tc\d+\b',
                    r'ctp\d+\b', 'collaboration touch', 'mtouch', 'gc8', 'neat pad', 'touch 10',
                    'vc.*touch.*panel', 'teams.*controller']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'Touch Controller / Panel', 'needs_review': False}
    
    if matches_any(['scheduler', 'room booking', 'scheduling panel', 'room panel', r'tss-\d+',
                    'tap scheduler', 'meeting room panel', 'booking panel']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'Scheduling Panel', 'needs_review': False}
    
    if matches_any(['trio c60', r'mp\d{2}', 'team phone', 'conference phone', 'voip.*video',
                    'video phone', 'sip.*video.*phone']):
        return {'primary_category': 'Video Conferencing', 'sub_category': 'VC Phone', 'needs_review': False}

    # PRIORITY 3: Audio Equipment
    if matches_any(['ceiling mic', r'mxa9\d0', 'tcc-2', 'tcc2', r'vcm3\d', r'cm\d{2}\b',
                    r'tcm-x\b', 'ceiling.*microphone', 'overhead mic', 'pendant mic']):
        return {'primary_category': 'Audio', 'sub_category': 'Ceiling Microphone', 'needs_review': False}
    
    if matches_any(['table mic', 'boundary mic', r'mxa3\d\d', 'rally mic pod', 'ip table microphone',
                    r'vcm35', 'table array', r'cs-mic-table', 'conference.*microphone', 'tabletop mic']):
        return {'primary_category': 'Audio', 'sub_category': 'Table/Boundary Microphone', 'needs_review': False}
    
    if matches_any(['wireless mic', 'wireless microphone', r'vcm\d+w', 'handheld transmitter',
                    'bodypack transmitter', 'lavalier system', 'sl mcr', 'ulxd', 'mxwapt',
                    r'blx\d+', 'uhf.*mic', 'rf.*microphone']):
        return {'primary_category': 'Audio', 'sub_category': 'Wireless Microphone System', 'needs_review': False}
    
    if matches_any(['gooseneck', r'meg \d+', 'gooseneck.*mic', 'flexible.*mic']):
        return {'primary_category': 'Audio', 'sub_category': 'Gooseneck Microphone', 'needs_review': False}
    
    if matches_any(['headset', 'earset', 'zone wireless', r'h\d{3}e', 'lavalier(?!.*system)',
                    'headworn', 'head.*mic', 'earbud.*mic']):
        return {'primary_category': 'Audio', 'sub_category': 'Headset / Wearable Mic', 'needs_review': False}
    
    if matches_any(['speakerphone', 'poly sync', r'speak \d+', 'mobile speakerphone', 'usb.*speakerphone',
                    'bluetooth.*speaker.*phone', 'conference speaker']):
        return {'primary_category': 'Audio', 'sub_category': 'Speakerphone', 'needs_review': False}

    if matches_any(['dsp(?!.*cable)', 'digital signal processor', 'audio processor', 'tesira',
                    'q-sys core', 'biamp', r'p300\b', 'intellimix', 'audio conferencing processor',
                    r'dmp \d+', 'bss blu', 'avhub', 'sound processor']):
        return {'primary_category': 'Audio', 'sub_category': 'DSP / Audio Processor / Mixer', 'needs_review': False}

    if matches_any(['audio mixer', 'mixing console', 'mixer(?!.*dsp)']) and not matches_any(['dsp', 'processor']):
        return {'primary_category': 'Audio', 'sub_category': 'DSP / Audio Processor / Mixer', 'needs_review': False}
    
    # FIXED: Summing amplifiers (signal processors, NOT power amps)
    if matches_any(['summing.*amplifier', 'active.*summing', 'quad.*active.*amplifier',
                    'line.*driver', 'audio.*summing']):
        return {'primary_category': 'Audio', 'sub_category': 'Audio Interface / Extender', 'needs_review': False}

    # FIXED: Power amplifiers only
    if matches_any([r'\bpower\s*amplifier\b', r'\bpoweramp\b', r'\d+\s*x\s*\d+w',
                    'multi.*channel.*amp', 'netpa', r'xpa\s*\d+', r'spa\s*\d+', r'ma\d{4}',
                    '70v.*amp', '100v.*amp', r'\d+\s*channel.*amplifier']):
        return {'primary_category': 'Audio', 'sub_category': 'Amplifier', 'needs_review': False}

    if matches_any(['ceiling speaker', 'in-ceiling speaker', 'pendant speaker', 'ceiling.*loudspeaker',
                    r'ad-c\d+', r'control \d+c']):
        return {'primary_category': 'Audio', 'sub_category': 'Ceiling Loudspeaker', 'needs_review': False}

    if matches_any(['wall.*speaker', 'surface mount speaker', 'wall.*loudspeaker', 
                    r'ad-s\d+', 'surface.*speaker']):
        return {'primary_category': 'Audio', 'sub_category': 'Wall-mounted Loudspeaker', 'needs_review': False}

    if matches_any(['speaker(?!.*phone)', 'soundbar(?!.*video)', 'loudspeaker', 
                    'column speaker', 'line array', r'\bms speaker\b']):
        return {'primary_category': 'Audio', 'sub_category': 'Loudspeaker / Speaker', 'needs_review': False}
    
    if matches_any(['dante interface', 'audio.*extender', 'audio interface', r'axi \d+',
                    'usb.*audio.*bridge', 'audio.*over.*ip', 'aes67']):
        return {'primary_category': 'Audio', 'sub_category': 'Audio Interface / Extender', 'needs_review': False}
    
    if matches_any(['intercom', 'freespeak', 'communication.*system', 'talkback']):
        return {'primary_category': 'Audio', 'sub_category': 'Intercom System', 'needs_review': False}
    
    if matches_any(['antenna(?!.*wifi)', 'combiner', 'rf.*splitter', r'ua\d+', 'rf.*combiner']):
        return {'primary_category': 'Audio', 'sub_category': 'RF & Antenna', 'needs_review': False}
    
    if matches_any(['charging station', r'mxwncs\d', r'chg\d\w+', 'charger.*mic', 'battery.*charger']):
        return {'primary_category': 'Audio', 'sub_category': 'Charging Station', 'needs_review': False}

    # PRIORITY 4: Displays & Projectors
    if matches_any(['led wall', 'dvled', 'direct.*view.*led', 'absen', 'fine.*pitch.*led',
                    'micro.*led', 'cob.*led']):
        return {'primary_category': 'Displays', 'sub_category': 'Direct-View LED', 'needs_review': False}
    
    if matches_any(['video wall(?!.*processor|.*mount)', 'videowall display', 'video.*wall.*display',
                    'multi.*display.*wall', 'lcd.*wall']):
        return {'primary_category': 'Displays', 'sub_category': 'Video Wall Display', 'needs_review': False}
    
    if matches_any(['interactive display', 'touch display(?!.*controller)', 'smart board', 
                    'interactive.*monitor', r'ifp\d+', r'rp\d{4}', 'touch.*screen.*display',
                    'interactive.*flat.*panel', 'interactive.*whiteboard(?!.*teams)']):
        return {'primary_category': 'Displays', 'sub_category': 'Interactive Display', 'needs_review': False}
    
    if matches_any(['projector', 'dlp(?!.*cable)', '3lcd', 'laser projector', r'eb-l\d+',
                    r'vpl-\w+', r'ls\d{3}', 'short.*throw.*projector', 'ultra.*short.*throw']):
        return {'primary_category': 'Displays', 'sub_category': 'Projector', 'needs_review': False}
    
    if matches_any(['display(?!.*mount|.*port.*cable)', 'monitor(?!.*mount|.*arm)', 'signage',
                    'bravia', 'commercial monitor', 'professional display', 'lfd', 
                    r'\b(qb|qm|uh|fw-)\d{2}\b', r'me\d{2}\b', 'digital signage', 'flat.*panel',
                    r'\d{2}["\'].*display', r'\d{2}["\'].*monitor', 'lcd.*display', 'led.*display(?!.*wall)']):
        return {'primary_category': 'Displays', 'sub_category': 'Professional Display', 'needs_review': False}

    # PRIORITY 5: Signal Management
    if matches_any(['matrix', 'video.*switcher', 'av.*switcher', 'presentation.*switcher',
                    'dmps', 'crosspoint', r'vm\d{4}', r'vs\d{3}(?!a)', 'dxp hd', 'seamless.*switcher',
                    r'\d+x\d+.*matrix', 'hdmi.*matrix']):
        return {'primary_category': 'Signal Management', 'sub_category': 'Matrix Switcher', 'needs_review': False}
    
    if matches_any(['extender(?!.*cable)', 'transmitter(?!.*wireless.*mic)', 'receiver(?!.*wireless.*mic)',
                    'hdbaset', r'tx/rx\b', r'hd-tx\d*', r'hd-rx\d*', 'dphd', 'tps-tx', 'tps-rx',
                    'dtp(?!.*cable)', r'tp-\d+r', 'balun', r'\d+m.*extender']):
        return {'primary_category': 'Signal Management', 'sub_category': 'Extender (TX/RX)', 'needs_review': False}
    
    if matches_any(['video wall processor', 'multi screen controller', 'video.*wall.*controller',
                    'display.*wall.*processor']):
        return {'primary_category': 'Signal Management', 'sub_category': 'Video Wall Processor', 'needs_review': False}
    
    if matches_any(['brightsign', 'media player', 'digital signage player', 'content.*player']):
        return {'primary_category': 'Signal Management', 'sub_category': 'Digital Signage Player', 'needs_review': False}
    
    if matches_any(['scaler', 'converter(?!.*fiber)', 'scan converter', r'dsc \d+', 'signal processor',
                    'edid', 'embedder', 'de-embedder', 'annotation processor', 'video capture',
                    'format.*converter', 'resolution.*converter', 'hdmi.*scaler']):
        return {'primary_category': 'Signal Management', 'sub_category': 'Scaler / Converter / Processor', 'needs_review': False}
    
    if matches_any(['distribution amplifier', r'da\dhd', r'hd-da\d+', 'hdmi splitter', r'vs\d{3}a',
                    'signal.*splitter', r'1x\d+.*splitter', 'video.*splitter']):
        return {'primary_category': 'Signal Management', 'sub_category': 'Distribution Amplifier / Splitter', 'needs_review': False}
    
    if matches_any(['av over ip', 'dm nvx', 'encoder(?!.*audio)', 'decoder', r'nav e \d+',
                    r'nav sd \d+', 'network.*video', 'streaming.*encoder', 'sdi.*encoder']):
        return {'primary_category': 'Signal Management', 'sub_category': 'AV over IP (Encoder/Decoder)', 'needs_review': False}

    # PRIORITY 6: Control Systems
    if matches_any(['control system', 'control processor', r'cp\d-r', r'rmc\d', 'netlinx',
                    'ipcp pro', r'nx-\d+', 'automation.*processor', 'av.*control.*processor']):
        return {'primary_category': 'Control Systems', 'sub_category': 'Control Processor', 'needs_review': False}
    
    if matches_any(['touch panel(?!.*collaboration|.*conferenc)', 'touch screen(?!.*display)',
                    'modero', r'tsw-\d+', r'tst-\d+', r'\d+["\'].*touch.*panel',
                    'control.*touch.*screen']):
        return {'primary_category': 'Control Systems', 'sub_category': 'Touch Panel', 'needs_review': False}
    
    if matches_any(['keypad', r'c2n-\w+', r'hz-kp\w+', 'ebus button panel', 'button.*panel',
                    'wall.*keypad', 'control.*keypad']):
        return {'primary_category': 'Control Systems', 'sub_category': 'Keypad', 'needs_review': False}
    
    if matches_any(['interface(?!.*audio)', 'gateway', r'exb-io\d', r'cen-io', r'inet-ioex',
                    'relay.*module', 'io.*module', 'control.*interface']):
        return {'primary_category': 'Control Systems', 'sub_category': 'I/O Interface / Gateway', 'needs_review': False}
    
    if matches_any(['sensor(?!.*mic)', 'occupancy', 'daylight', 'gls-', 'motion.*sensor',
                    'presence.*detect', 'ambient.*light.*sensor']):
        return {'primary_category': 'Control Systems', 'sub_category': 'Sensor', 'needs_review': False}

    # PRIORITY 7: Infrastructure & Connectivity
    if matches_any(['faceplate', 'button cap', 'bezel', 'wall plate', 'table plate', 'cable cubby',
                    'tbus', 'hydraport', 'fliptop', 'mud ring', 'floor.*box', 'connectivity.*box',
                    'table.*box', 'grommet', 'aap', 'retractor.*box']):
        
        # ENHANCED: Separate complete connectivity solutions from mounting hardware
        if matches_any(['mounting.*frame', 'blank.*plate', 'frame.*only', 'housing.*only', 
                        'enclosure.*only', 'bracket.*only']):
            return {'primary_category': 'Infrastructure', 'sub_category': 'Mounting Hardware', 'needs_review': False}
        
        return {'primary_category': 'Cables & Connectivity', 'sub_category': 'Wall & Table Plate Module', 'needs_review': False}

    if matches_any([r'\d+u.*rack', r'\d+u\s*enclosure', 'equipment rack', 'valrack', 'netshelter',
                    'server.*rack', 'relay.*rack', 'cabinet.*rack']):
        return {'primary_category': 'Infrastructure', 'sub_category': 'AV Rack', 'needs_review': False}

    if matches_any(['pdu', 'ups', 'power distribution', 'rackmount.*power', 'rack.*power.*distribution']):
        return {'primary_category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'needs_review': False}

    if matches_any(['power strip', 'power conditioner', 'power supply(?!.*camera)', 'poe injector', 
                    'power pack', r'pw-\d+', r'qs-ps-', 'csa-pws', 'battery.*backup', 'surge.*protect']):
        return {'primary_category': 'Infrastructure', 'sub_category': 'Power Management', 'needs_review': False}

    # PRIORITY 8: Mounts - SPECIFIC FIRST
    # Video conferencing equipment mounts (NOT display mounts)
    if matches_any([r'poly.*x\d{2}', r'studio.*x\d{2}', r'x\d{2}.*vesa', 
                    'rally.*mount', 'video.*bar.*mount', 'soundbar.*mount',
                    'bar.*mount.*kit', 'codec.*mount']):
        return {'primary_category': 'Mounts', 'sub_category': 'Camera Mount', 'needs_review': False}
    
    if matches_any(['projector mount', 'projector ceiling mount', 'ceiling.*mount.*projector']):
        return {'primary_category': 'Mounts', 'sub_category': 'Projector Mount', 'needs_review': False}
    
    if matches_any(['camera mount(?!.*projector)', 'cam-mount', 'camera bracket', 'wall.*mount.*camera',
                    'ceiling.*mount.*camera', 'camera.*mounting']):
        return {'primary_category': 'Mounts', 'sub_category': 'Camera Mount', 'needs_review': False}
    
    if matches_any(['speaker mount(?!.*display)', 'mic mount', 'microphone suspension',
                    'pendant mount(?!.*speaker)', 'wall.*mount.*speaker', 'ceiling.*mount.*speaker']):
        return {'primary_category': 'Mounts', 'sub_category': 'Speaker/Mic Mount', 'needs_review': False}
    
    if matches_any(['rack shelf', 'rackmount kit', 'component storage', 'mounting shelf',
                    'mounting kit(?!.*display|.*tv|.*camera)', 'shelf.*bracket', 'equipment.*shelf']):
        return {'primary_category': 'Mounts', 'sub_category': 'Component / Rack Mount', 'needs_review': False}
    
    if matches_any(['tv mount', 'display mount', 'wall mount(?!.*camera|.*speaker)', 'trolley',
                    'av cart', 'floor stand', 'fusion mount', 'chief', 'vesa', 'videowall mount',
                    'ceiling mount(?!.*mic|.*speak|.*proj|.*camera)', r'bt\d+', r'lpa\d+',
                    'steelcase.*mount', 'heckler.*cart', 'display.*cart', 'tv.*cart', 'mobile.*stand',
                    'tilting.*mount', 'fixed.*mount', 'articulating.*mount']):
        return {'primary_category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'needs_review': False}

    # PRIORITY 9: Cables & Connectivity
    if matches_any(['retractor', 'cable caddy', 'cable ring', 'cable organizer', 'cable bag',
                    'cable.*management', 'cable.*wrap']):
        return {'primary_category': 'Cables & Connectivity', 'sub_category': 'Cable Retractor / Management', 'needs_review': False}
    
    if matches_any(['bulk cable', 'spool', 'reel', r'1000ft', r'305m', 'speaker wire', r'coax.*cable',
                    r'\d+m.*cable.*spool', 'roll.*cable']):
        return {'primary_category': 'Cables & Connectivity', 'sub_category': 'Bulk Cable / Wire', 'needs_review': False}
    
    if matches_any(['fiber optic', 'sfp', 'lc-lc', 'om4', 'singlemode', 'multimode.*fiber',
                    'optical.*cable', 'fiber.*patch']):
        return {'primary_category': 'Cables & Connectivity', 'sub_category': 'Fiber Optic', 'needs_review': False}
    
    if matches_any(['adapter(?!.*power)', 'connector(?!.*power)', 'dongle', 'gender changer',
                    'terminator', 'coupler', 'adapter ring', 'capture dongle', 'usb capture',
                    'hdmi.*adapter', 'usb.*adapter', 'converter.*cable']):
        return {'primary_category': 'Cables & Connectivity', 'sub_category': 'Connectors, Adapters & Dongles', 'needs_review': False}
    
    if matches_any(['cable(?!.*caddy|.*organ|.*retract)', 'cord', 'lead', 'patch', r'\d+ft', r'\d+m\b',
                    'hdmi', 'usb-c', 'displayport', 'vga', 'audio.*cable', 'video.*cable',
                    'power.*cord', 'iec.*cable', 'xlr.*cable', 'trs.*cable', 'cat\d',
                    'ethernet', 'network.*cable']):
        return {'primary_category': 'Cables & Connectivity', 'sub_category': 'AV Cable', 'needs_review': False}

    # PRIORITY 10: Lighting
    if matches_any(['lighting control', 'dimmer', 'lutron', 'dali', 'qsne', 'light.*sensor',
                    'dmx', 'architectural.*lighting']):
        return {'primary_category': 'Lighting', 'sub_category': 'Lighting Control', 'needs_review': False}

    # PRIORITY 11: Networking
    if matches_any(['switch(?!.*video|.*matrix)', 'network switch', 'managed switch', 'poe.*switch',
                    r'sg\d{3}', 'cisco.*switch', 'netgear.*switch', 'ethernet.*switch']):
        return {'primary_category': 'Networking', 'sub_category': 'Network Switch', 'needs_review': False}
    
    if matches_any(['router', 'wireless.*access.*point', r'\bwap\b', 'wifi.*access',
                    'access point', 'mesh.*network']):
        return {'primary_category': 'Networking', 'sub_category': 'Router / Access Point', 'needs_review': False}

    # PRIORITY 12: Computers
    if matches_any(['desktop', 'optiplex', 'mini conference pc', 'compute stick', 'nuc',
                    'workstation', 'pc(?!.*module)', 'computer(?!.*mount)']):
        return {'primary_category': 'Computers', 'sub_category': 'Desktop / SFF PC', 'needs_review': False}
    
    if matches_any(['ipad', 'tablet', 'surface pro', 'galaxy tab']):
        return {'primary_category': 'Computers', 'sub_category': 'Tablet', 'needs_review': False}
    
    if matches_any([r'\bops\b', 'pc module', 'slot.*pc', 'compute module']):
        return {'primary_category': 'Computers', 'sub_category': 'OPS Module', 'needs_review': False}

    # PRIORITY 13: Furniture
    if matches_any(['podium', 'lectern', 'presentation.*furniture']):
        return {'primary_category': 'Furniture', 'sub_category': 'Podium / Lectern', 'needs_review': False}
    
    if matches_any(['credenza', 'logic pod', 'av.*furniture', 'media.*cabinet']):
        return {'primary_category': 'Furniture', 'sub_category': 'AV Credenza / Stand', 'needs_review': False}

    # FALLBACK: If nothing matches
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
