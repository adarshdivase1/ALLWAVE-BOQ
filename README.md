# AllWave AV BOQ Generator 
## 📋 Project Overview

The **AllWave AV BOQ Generator** is an enterprise-grade, AI-powered Bill of Quantities (BOQ) generation system for professional audio-visual system design. Built with Streamlit and integrated with Google's Gemini AI, it automates the complex process of AV system design while ensuring AVIXA standards compliance.

### Key Features

- ✅ **AVIXA Standards Compliance** - Automated display sizing, audio coverage, and equipment selection based on industry standards
- 🤖 **AI-Powered Product Selection** - Intelligent product matching with justification using Google Gemini AI
- 🏢 **Multi-Room Project Management** - Design and manage multiple rooms within a single project
- 📊 **Advanced Product Database** - 10,000+ products with comprehensive categorization and specifications
- 💰 **Smart Pricing Engine** - Support for INR/USD with automatic currency conversion and GST calculation
- 📄 **Professional Excel Export** - Generate client-ready proposals with product images and top 3 selection reasons
- 🔐 **User Authentication** - Secure Firebase-based project storage and retrieval
- 🎨 **Interactive 3D Visualization** - Three.js powered room layout planning
- 🔍 **NLP Requirements Parser** - Extract client preferences and technical requirements from natural language

---

## 🏗️ Architecture Overview

### Tech Stack

```
Frontend:
├── Streamlit 1.32+          # UI Framework
├── Three.js r128            # 3D Visualization
└── Custom CSS               # Glassmorphism Design

Backend:
├── Python 3.10+
├── Pandas                   # Data Processing
├── NumPy                    # Numerical Operations
└── Pillow (PIL)            # Image Generation

AI/ML:
├── Google Gemini API       # AI Justification Engine
└── scikit-learn            # Product Matching Algorithms

Database:
├── Firebase Firestore      # Project Storage
├── CSV Database            # Product Catalog
└── Session State           # Runtime Data

Export:
└── openpyxl               # Excel Generation
```

### Project Structure

```
allwave-av-boq-generator/
│
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── avixa_guidelines.md             # AVIXA design standards
├── master_product_catalog.csv      # Product database
├── process_data.py                 # Data preprocessing script
│
├── components/                     # Core modules
│   ├── av_designer.py             # AVIXA calculations & equipment determination
│   ├── boq_generator.py           # BOQ generation engine with AI justifications
│   ├── data_handler.py            # Product database operations
│   ├── database_handler.py        # Firebase integration
│   ├── excel_generator.py         # Professional Excel export
│   ├── gemini_handler.py          # Google Gemini AI integration
│   ├── intelligent_product_selector.py  # Advanced product matching
│   ├── nlp_requirements_parser.py # Natural language processing
│   ├── product_image_generator.py # Product card image generation
│   ├── room_profiles.py           # Room type specifications
│   ├── ui_components.py           # Reusable UI components
│   ├── utils.py                   # Utility functions
│   └── visualizer.py              # 3D room visualization
│
├── assets/                         # Static resources
│   ├── style.css                  # Custom styling
│   ├── company_logo.png           # Company branding
│   ├── crestron_logo.png          # Partner logos
│   ├── avixa_logo.png
│   └── iso_logo.png
│
├── data/                           # Raw product data
│   ├── Master List - Poly.csv
│   ├── Master List - Logitech.csv
│   └── [Additional vendor CSVs]
│
└── .streamlit/                     # Streamlit configuration
    └── secrets.toml               # API keys (not in repo)
```

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.10 or higher
- Google Gemini API key
- Firebase project credentials (for database features)

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/allwave-av-boq-generator.git
cd allwave-av-boq-generator
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure API Keys

Create `.streamlit/secrets.toml`:

```toml
# Google Gemini API
GEMINI_API_KEY = "your_gemini_api_key_here"

# Firebase Configuration
[firebase_credentials]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "firebase-adminsdk@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

### Step 4: Prepare Product Database

```bash
# Place vendor CSV files in data/ folder
python process_data.py
```

This generates `master_product_catalog.csv` with 10,000+ products.

### Step 5: Run Application

```bash
streamlit run app.py
```

Access at: `http://localhost:8501`

---

## 📚 Core Components Documentation

### 1. BOQ Generator (`boq_generator.py`)

**Purpose:** AI-powered BOQ generation with intelligent product selection and justification.

**Key Functions:**

```python
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, 
                         features, technical_reqs, room_area)
    """
    Main BOQ generation pipeline with 8 stages:
    1. NLP Requirements Parsing
    2. AVIXA Calculations
    3. Equipment Requirements Determination
    4. Component Blueprint Building
    5. Intelligent Product Selection with AI Justifications
    6. Compatibility & Redundancy Checking
    7. Validation & Quality Scoring
    8. Final Assembly & Export Preparation
    
    Returns: (boq_items, avixa_calcs, equipment_reqs, validation_results)
    """
```

**AI Justification System:**

```python
def generate_ai_product_justification(model, product_info, room_context, avixa_calcs)
    """
    Generates:
    - Technical justification (internal documentation)
    - Top 3 client-facing reasons (10-15 words each)
    - Confidence score (0-1)
    
    Uses Gemini AI with structured JSON output.
    """
```

**Critical Features:**

- **Service Contract Filtering** - Prevents selection of warranty/support contracts
- **Video Bar Integration Detection** - Removes redundant audio components
- **Brand Ecosystem Matching** - Prioritizes compatible accessories
- **Price Range Validation** - Enforces minimum/maximum thresholds
- **Display Size Validation** - Warns about unusual multi-display configurations

---

### 2. Intelligent Product Selector (`intelligent_product_selector.py`)

**Purpose:** Advanced multi-stage product selection with strict validation.

**Selection Pipeline:**

```python
1. Category Filter          # Filter by primary category
2. Service Contract Filter  # Remove warranty items
3. Keyword Filters          # Required/blacklist keywords
4. Specification Matching   # Size, power, mounting requirements
5. Strict Category Validation # Prevent cross-category contamination
6. Client Preference Weighting # Brand preference prioritization
7. Budget-Aware Selection   # Price tier matching
8. Final Compatibility Check # Integration verification
```

**ProductRequirement Dataclass:**

```python
@dataclass
class ProductRequirement:
    category: str
    sub_category: str
    quantity: int
    priority: int
    justification: str
    size_requirement: Optional[float]
    power_requirement: Optional[int]
    mounting_type: Optional[str]
    required_keywords: List[str]
    blacklist_keywords: List[str]
    min_price: Optional[float]
    max_price: Optional[float]
    strict_category_match: bool
```

**Category Validators:**

```python
self.category_validators = {
    'Displays': {
        'must_contain': ['display', 'monitor', 'screen'],
        'must_not_contain': ['mount', 'bracket'],
        'price_range': (200, 30000)
    },
    'Mounts': {
        'must_contain': ['mount', 'bracket', 'stand'],
        'must_not_contain': ['display', 'camera'],
        'price_range': (50, 3000)
    },
    # ... additional categories
}
```

---

### 3. NLP Requirements Parser (`nlp_requirements_parser.py`)

**Purpose:** Extract structured requirements from natural language input.

**Capabilities:**

```python
# Brand Recognition
"Need Poly video conferencing with Shure microphones"
→ {'video_conferencing': 'Poly', 'audio': 'Shure'}

# Feature Detection
"Dual 85-inch displays with wireless presentation"
→ {'display_features': ['dual_display', 'large_format'],
    'connectivity_features': ['wireless_presentation']}

# Quantity Extraction
"Room for 12 people with 2 cameras"
→ {'participants': 12, 'cameras': 2}

# Compliance Requirements
"ADA compliant with hearing loop"
→ {'compliance': ['ADA'], 'special_requirements': ['hearing_loop']}
```

**Pattern Matching Engine:**

```python
self.brand_patterns = {
    'displays': {
        'samsung': r'\b(samsung|qb|qm)\b',
        'lg': r'\b(lg|uh5)\b',
        # ... more brands
    }
}

self.feature_patterns = {
    'display_features': {
        'dual_display': r'\b(dual|two|2)\s*(display|screen)',
        '4k': r'\b(4k|uhd|ultra\s*hd)\b'
    }
}
```

---

### 4. Excel Generator (`excel_generator.py`)

**Purpose:** Generate professional client-ready Excel proposals.

**Sheet Structure:**

```
1. Version Control           # Project metadata, contacts
2. Scope of Work            # Installation scope, exclusions
3. Proposal Summary         # Multi-room cost rollup
4. Terms & Conditions       # Payment terms, warranties
5. BOQ - [Room Name]        # Detailed room BOQ (one per room)
```

**Product Image Integration:**

```python
def generate_product_info_card(product_name, brand, model, category, size_inches)
    """
    Creates visual product cards with:
    - Category-specific icons (displays, cameras, audio, etc.)
    - Brand and model information
    - Size specifications (for displays)
    - Professional color-coded design
    
    Returns: BytesIO PNG image buffer
    """
```

**Top 3 Reasons Display:**

```python
# In Excel BOQ sheet (Column Q: "Top 3 Reasons")
1. AVIXA-compliant display sizing for optimal viewing distance
2. Professional-grade 4K resolution for clarity and detail
3. Commercial warranty and enterprise reliability
```

**Financial Calculations:**

```python
# Hardware + Services
Subtotal = Hardware Cost
Installation (15%) = Subtotal × 0.15
Warranty (5%) = Subtotal × 0.05
Project Management (10%) = Subtotal × 0.10

# GST
SGST (9%) = (Subtotal + Services) × 0.09
CGST (9%) = (Subtotal + Services) × 0.09

Grand Total = Subtotal + Services + SGST + CGST
```

---

### 5. AV Designer (`av_designer.py`)

**Purpose:** AVIXA-compliant calculations and equipment determination.

**Display Sizing (AVIXA DISCAS):**

```python
def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    """
    AVIXA Formula for Detailed Viewing:
    Screen Height = Viewing Distance ÷ 6
    
    For 16:9 aspect ratio:
    Diagonal = Screen Height × 2.22
    
    Example:
    - Room: 28ft × 20ft
    - Farthest viewer: 28ft × 0.9 = 25.2ft
    - Screen height: 25.2ft ÷ 4 = 6.3ft = 75.6 inches
    - Diagonal: 75.6 × 2.22 = 168 inches → Snap to 85"
    """
```

**Audio Coverage Calculation:**

```python
# Speaker Coverage
speakers_needed = max(2, int(room_area / 200) + 1)

# Microphone Coverage
mic_count = max(2, int(room_area / 150))

# Example: 560 sq ft room
# Speakers: int(560/200) + 1 = 3 + 1 = 4 speakers
# Microphones: int(560/150) = 3 + 1 = 4 mics
```

**Equipment Determination Matrix:**

```python
Room Size    | Display        | Audio System              | Video System
-------------|----------------|---------------------------|------------------
< 150 sqft   | 43-55"        | Integrated (Video Bar)    | All-in-One Bar
150-400 sqft | 55-75"        | Table Mics + DSP          | Video Bar / Codec
400-800 sqft | 75-98"        | Ceiling Audio + DSP       | Codec + PTZ Camera
> 800 sqft   | 2× 85-98"     | Pro Audio System          | Multi-Camera System
```

---

### 6. Data Processing (`process_data.py`)

**Purpose:** Transform raw vendor CSV files into unified product database.

**Categorization Engine (V7.0):**

```python
def categorize_product_comprehensively(description, model)
    """
    Enhanced V7.0 with 14 primary categories:
    
    1. Software & Services (Support, Licenses, Cloud)
    2. Video Conferencing (Bars, Codecs, Cameras, Controllers)
    3. Audio (Mics, Speakers, DSP, Amplifiers, Processors)
    4. Displays (Professional, Interactive, LED, Projectors)
    5. Signal Management (Matrix, Extenders, Scalers, AV over IP)
    6. Control Systems (Processors, Touch Panels, Keypads)
    7. Infrastructure (Racks, PDUs, Power Management)
    8. Cables & Connectivity (AV Cables, Fiber, Plates, Adapters)
    9. Mounts (Display, Camera, Speaker, Projector)
    10. Lighting (Control Systems, Sensors)
    11. Networking (Switches, Routers, Access Points)
    12. Computers (Desktops, Tablets, OPS Modules)
    13. Furniture (Podiums, Credenzas)
    14. Peripherals (Keyboards, Document Cameras, KVM)
    
    Returns: {'primary_category': str, 'sub_category': str, 'needs_review': bool}
    """
```

**Data Quality Scoring:**

```python
def score_product_quality(product):
    """
    100-point quality score system:
    
    Deductions:
    - Missing/short description: -20 points
    - Zero/invalid price: -50 points
    - Price > $200,000: -10 points
    - Missing product name: -40 points
    - Missing model number: -15 points
    - Unclassified category: -30 points
    
    Rejection threshold: < 30 points
    """
```

**Processing Pipeline:**

```bash
Input: 50+ vendor CSV files
↓
1. Header Detection (finds column mappings)
2. Price Cleaning (INR → USD conversion)
3. Model Number Extraction (regex patterns)
4. Brand Extraction (from filename)
5. Categorization (AI-powered classification)
6. Warranty Extraction (from description)
7. Quality Scoring (0-100 scale)
8. Deduplication (by brand + model)
↓
Output: master_product_catalog.csv (10,000+ products)
```

---

### 7. 3D Visualizer (`visualizer.py`)

**Purpose:** Interactive Three.js room layout planner.

**Features:**

```javascript
- Realistic room rendering (floor, walls, ceiling, furniture)
- Drag-and-drop equipment placement
- AVIXA-compliant positioning suggestions
- Space analytics (coverage, power load, cable runs)
- Multiple camera views (overview, front, side, top)
- Collision detection and boundary constraints
```

**Room Furniture Generation:**

```python
def createRoomFurniture():
    """
    Generates room-specific furniture:
    - Conference rooms: Center table + chairs
    - Training rooms: Student desks in rows
    - Boardrooms: Executive table + credenza
    - Production studios: Control console + racks
    - Event rooms: Stage platform
    """
```

**Space Analytics Engine:**

```javascript
class SpaceAnalytics {
    calculateMetrics() {
        - Total Room Area (length × width)
        - Usable Floor Space (total - furniture)
        - Equipment Footprint (sum of placed items)
        - Wall Space Used (percentage)
        - Remaining Floor Space
        - Total Power Load (watts)
        - Cable Runs Required (estimated)
    }
}
```

---

## 🔧 Configuration Files

### Room Profiles (`room_profiles.py`)

```python
ROOM_SPECS = {
    'Small Huddle Room (2-3 People)': {
        'area_sqft': (100, 150),
        'capacity': (2, 3),
        'typical_dims_ft': (12, 10),
        'displays': {'quantity': 1, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Integrated in Video Bar'},
        'video_system': {'type': 'All-in-one Video Bar'},
        'control_system': {'type': 'Touch Controller'}
    },
    # ... 10 total room types
}
```

### AVIXA Guidelines (`avixa_guidelines.md`)

**Key Standards:**

```markdown
## Display Sizing (DISCAS)
- Detailed Viewing: Screen Height = Distance ÷ 6
- Basic Viewing: Screen Height = Distance ÷ 4

## Audio Coverage
- Speakers: 1 per 200 sq ft (minimum 2)
- Microphones: 1 per 150 sq ft (minimum 2)
- SPL: 70-75 dB at seating positions

## Network Requirements
- Small Huddle: 10 Mbps minimum
- Medium Conference: 25 Mbps minimum
- Large Boardroom: 50+ Mbps minimum

## Power Requirements
- Small systems: 300-500W (15A circuit)
- Medium systems: 800-1,500W (20A circuit)
- Large systems: 2,000-5,000W (multiple 20A circuits)
```

---

## 💾 Database Schema

### Firebase Firestore Structure

```
users/
└── {user_email}/
    └── projects/
        └── {project_name}/
            ├── name: string
            ├── last_saved: timestamp
            ├── project_name_input: string
            ├── client_name_input: string
            ├── location_input: string
            ├── design_engineer_input: string
            ├── account_manager_input: string
            ├── room_type_select: string
            ├── room_length_input: float
            ├── room_width_input: float
            ├── budget_tier_slider: string
            ├── features_text_area: string
            ├── currency_select: string
            ├── gst_rates: map
            │   ├── Electronics: int
            │   └── Services: int
            ├── rooms: array
            │   └── {room}/
            │       ├── name: string
            │       ├── type: string
            │       ├── area: float
            │       └── boq_items: array
            │           └── {item}/
            │               ├── category: string
            │               ├── name: string
            │               ├── brand: string
            │               ├── model_number: string
            │               ├── quantity: int
            │               ├── price: float
            │               ├── justification: string
            │               ├── top_3_reasons: array
            │               └── ... (additional fields)
            └── current_room_index: int
```

### Product Catalog CSV Schema

```csv
name,brand,model_number,primary_category,sub_category,price_usd,price_inr,
warranty,description,full_specifications,unit_of_measure,lead_time_days,
gst_rate,image_url,data_quality_score
```

---

## 🎨 UI/UX Design System

### Color Palette

```css
--bg-dark: #002250;           /* Dark Blue (Brand Primary) */
--glow-primary: #f07d00;      /* Orange (Brand Accent) */
--glow-secondary: #1e397e;    /* Blue (Brand Secondary) */
--text-primary: #f4f2f1;      /* Grey (Brand Text) */
```

### Component Library

```python
# Glass Container
background: rgba(0, 34, 80, 0.75)
backdrop-filter: blur(25px) saturate(180%)
border: 1px solid rgba(244, 242, 241, 0.2)

# Interactive Card (Hover)
transform: perspective(1500px) rotateX(3deg) scale3d(1.02)
box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7)

# Buttons (Primary)
background: linear-gradient(135deg, #d32f2f, #f07d00)
box-shadow: 0 0 35px rgba(211, 47, 47, 0.7)
```

---

## 🔐 Security & Authentication

### User Authentication

```python
# Login Validation
- Email domain check: @allwaveav.com or @allwavegs.com
- Minimum password length: 4 characters
- Session-based authentication (Streamlit session_state)

# User Context Storage
st.session_state.authenticated = True
st.session_state.user_email = email
st.session_state.is_psni_referral = boolean
st.session_state.client_is_local = boolean
```

### Firebase Security Rules (Recommended)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/projects/{projectId} {
      allow read, write: if request.auth != null && request.auth.token.email == userId;
    }
  }
}
```

---

## 📊 Performance Optimization

### Caching Strategy

```python
@st.cache_data
def load_and_validate_data():
    # Product database loaded once per session
    
@st.cache_data(ttl=3600)
def get_usd_to_inr_rate():
    # Exchange rate cached for 1 hour
    
@st.cache_resource
def initialize_firebase():
    # Firebase connection reused across sessions
```

### Data Processing Optimizations

```python
# Pandas optimizations
df.dropna(how='all', inplace=True)  # Remove empty rows
df['model_lower'] = df['model'].str.lower()  # Vectorized string operations
df.drop_duplicates(subset=['brand', 'model_lower'], inplace=True)

# Memory management
del df['temporary_column']  # Free memory after use
gc.collect()  # Force garbage collection for large datasets
```

---

## 🧪 Testing Guidelines

### Unit Tests (Recommended Structure)

```python
# tests/test_av_designer.py
def test_avixa_display_sizing():
    result = calculate_avixa_recommendations(28, 20, 10, "Standard Conference")
    assert 65 <= result['recommended_display_size_inches'] <= 75

# tests/test_product_selector.py
def test_display_mount_selection():
    req = ProductRequirement(
        category='Mounts',
        sub_category='Display Mount / Cart',
        size_requirement=85
    )
    product = selector.select_product(req)
    assert product is not None
    assert 'mount' in product['name'].lower()
```

### Integration Tests

```bash
# Test full BOQ generation
python -m pytest tests/test_boq_generation.py

# Test Excel export
python -m pytest tests/test_excel_output.py

# Test Firebase connectivity
python -m pytest tests/test_database.py
```

---

## 🐛 Known Issues & Limitations

### Current Limitations

1. **Image Generation**
   - Product images are generated programmatically (no real product photos)
   - Solution: Integrate with vendor image APIs

2. **Exchange Rate**
   - Uses hardcoded INR/USD rate (83.5)
   - Solution: Integrate live exchange rate API

3. **Offline Mode**
   - Requires internet for Gemini AI and Firebase
   - Solution: Implement local LLM fallback

4. **Product Database Updates**
   - Manual CSV updates required
   - Solution: Automated vendor catalog sync

### Troubleshooting

**Issue: "Gemini API Error"**
```python
# Solution: Check API key in secrets.toml
# Verify quota limits in Google Cloud Console
```

**Issue: "Firebase Authentication Failed"**
```python
# Solution: Regenerate Firebase service account key
# Ensure private_key newlines are escaped: \n → \\n
```

**Issue: "Product Not Found"**
```python
# Solution: Run process_data.py to rebuild catalog
# Check data/ folder for vendor CSV files
```

---

## 🚢 Deployment

### Streamlit Cloud Deployment

```bash
# 1. Push to GitHub
git add .
git commit -m "Deploy to Streamlit Cloud"
git push origin main

# 2. Connect repository in Streamlit Cloud dashboard
# 3. Configure secrets (Settings → Secrets)
# 4. Deploy (Streamlit will auto-detect app.py)
```

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501"]
```

```bash
# Build and run
docker build -t allwave-boq .
docker run -p 8501:8501 -v $(pwd)/.streamlit:/app/.streamlit allwave-boq
```

---

## 📝 Contributing Guidelines

### Code Style

```python
# Follow PEP 8
# Use type hints
def calculate_price(quantity: int, unit_price: float) -> float:
    return quantity * unit_price

# Docstrings for all functions
def complex_function(param1, param2):
    """
    Brief description.
    
    Args:
        param1 (str): Description
        param2 (int): Description
    
    Returns:
        dict: Description of return value
    """
```

### Commit Messages

```bash
# Format: [Component] Brief description
git commit -m "[BOQ Generator] Add AI justification caching"
git commit -m "[Excel Export] Fix product image alignment"
git commit -m "[UI] Update sidebar styling"
```

---

## 📄 License

This project is proprietary software owned by **AllWave Audio Visual & General Services Pvt. Ltd.**

**Copyright © 2025 AllWave AV & GS. All Rights Reserved.**

---

## 👥 Authors & Credits

**Development Team:**
- Lead Developer: AllWave AV Engineering Team
- AI Integration: Gemini API Team
- UI/UX Design: AllWave Design Studio

**Special Thanks:**
- AVIXA for industry standards
- Crestron, Poly, Logitech, Shure for product specifications
- PSNI Global Alliance for partnership

---

## 📞 Support

**Technical Support:**
- Email: support@allwaveav.com
- Phone: +91 (022) XXXX XXXX

**Documentation:**
- Internal Wiki: [Company Intranet]
- API Docs: https://docs.allwaveav.com

**Bug Reports:**
- GitHub Issues: [Repository URL]
- Internal Tracker: [JIRA/Asana Link]

---

## 🔄 Version History

### v2.0.0 (Current)
- ✅ AI-powered product justifications
- ✅ Multi-room project management
- ✅ 3D visualization with drag-drop
- ✅ NLP requirements parsing
- ✅ Professional Excel export with images

### v1.5.0
- ✅ Firebase project storage
- ✅ Intelligent product selector
- ✅ AVIXA compliance validation

### v1.0.0
- ✅ Initial release
- ✅ Basic BOQ generation
- ✅ Product database integration

---

**End of Documentation**

*Last Updated: January 2025*
