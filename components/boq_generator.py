# components/boq_generator.py
# PRODUCTION-READY VERSION - FULLY FIXED & ENHANCED WITH AI JUSTIFICATIONS

import streamlit as st
import pandas as pd
import re
import json
import time

# --- Component Imports ---
try:
    from components.gemini_handler import generate_with_retry
    from components.av_designer import calculate_avixa_recommendations, determine_equipment_requirements
    from components.data_handler import match_product_in_database
    
    # NEW IMPORTS - Add these
    from components.intelligent_product_selector import IntelligentProductSelector, ProductRequirement
    from components.nlp_requirements_parser import (
        NLPRequirementsParser, 
        extract_room_specific_requirements,
        merge_equipment_requirements
    )
except ImportError as e:
    st.error(f"BOQ Generator failed to import a component: {e}")
    # Add fallback classes
    class ProductRequirement:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    class IntelligentProductSelector:
        def __init__(self, *args, **kwargs): pass
        def select_product(self, req): return None
        def get_selection_report(self): return "Fallback mode: No report available."
        def get_validation_warnings(self): return [] # Fallback for new function
    class NLPRequirementsParser:
        def parse(self, text): return {}
    def extract_room_specific_requirements(text): return {'equipment_overrides': {}, 'client_preferences': {}}
    def merge_equipment_requirements(base, overrides): return base
    def generate_with_retry(model, prompt): return None
    def calculate_avixa_recommendations(*args): return {}
    def determine_equipment_requirements(*args): return {'displays': {}, 'audio_system': {}, 'video_system': {}}
    def match_product_in_database(*args): return None


# ==================== NEW HELPER FUNCTION ====================
def extract_top_3_reasons(justification, category='General'):
    """
    Extract or generate top 3 reasons from justification text.
    This ensures consistency between app display and Excel export.
    """
    reasons = []
    
    # Method 1: Parse numbered/bulleted list
    for line in justification.split('\n'):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-') or line.startswith('*')):
            clean_line = re.sub(r'^[\d\.\)•\-\*]\s*', '', line).strip()
            if clean_line and len(clean_line) > 5:
                reasons.append(clean_line)
    
    # Method 2: Split by sentences if no structured list
    if not reasons and justification:
        sentences = re.split(r'[.!?]+', justification)
        reasons = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
    
    # Method 3: Generate category-specific defaults
    if not reasons:
        category_defaults = {
            'Displays': [
                "AVIXA-compliant display sizing for optimal viewing distance",
                "Professional-grade 4K resolution for clarity and detail",
                "Commercial warranty and enterprise reliability"
            ],
            'Video Conferencing': [
                "Certified for Microsoft Teams/Zoom enterprise platforms",
                "Auto-framing and speaker tracking technology",
                "Plug-and-play installation with minimal configuration"
            ],
            'Audio': [
                "AVIXA-calculated coverage pattern for room acoustics",
                "Professional AEC and noise reduction processing",
                "Scalable architecture for future expansion"
            ],
            'Control Systems': [
                "Intuitive touch interface for non-technical users",
                "Centralized control of all AV systems",
                "Scheduled automation and energy management"
            ],
            'Mounts': [
                "Engineered load capacity for equipment safety",
                "Flexible positioning for optimal viewing angles",
                "Professional-grade construction and finish"
            ],
            'Cables & Connectivity': [
                "Certified bandwidth for 4K/8K signal transmission",
                "Future-proof infrastructure investment",
                "Reduced signal degradation over distance"
            ],
            'Infrastructure': [
                "Organized equipment management and cooling",
                "Simplified maintenance and troubleshooting access",
                "Professional appearance and cable management"
            ]
        }
        reasons = category_defaults.get(category, [
            "Industry-standard solution for this application",
            "Reliable performance and manufacturer support",
            "Cost-effective for project scope and requirements"
        ])
    
    # Return top 3 reasons only
    return reasons[:3]


# ==================== BRAND COMPATIBILITY & FEATURE CHECKER ====================
def check_component_compatibility(blueprint, selected_products):
    """
    Intelligent compatibility checker that removes redundant components
    and ensures brand compatibility.
    
    Returns: (filtered_blueprint, compatibility_warnings)
    """
    filtered_blueprint = {}
    warnings = []
    
    # === RULE 1: Video Bar = Integrated Audio ===
    has_video_bar = any(
        'Video Bar' in comp.sub_category 
        for comp in blueprint.values() 
        if hasattr(comp, 'sub_category')
    )
    
    if has_video_bar:
        # Check if video bar has integrated audio from product database
        video_bar_product = None
        for comp_key, comp in blueprint.items():
            if hasattr(comp, 'sub_category') and 'Video Bar' in comp.sub_category:
                # Find the actual selected product
                for product in selected_products:
                    if product.get('sub_category') == comp.sub_category:
                        video_bar_product = product
                        break
                break
        
        if video_bar_product:
            product_name = video_bar_product.get('name', '').lower()
            product_specs = video_bar_product.get('specifications', '').lower()
            combined_text = f"{product_name} {product_specs}"
            
            # Check for integrated audio indicators
            has_integrated_mics = any(term in combined_text for term in 
                ['integrated microphone', 'built-in microphone', 'beamforming mic', 
                 'mic array', 'microphone array', 'integrated mic'])
            
            has_integrated_speakers = any(term in combined_text for term in 
                ['integrated speaker', 'built-in speaker', 'full-duplex audio',
                 'speaker array', 'integrated audio'])
            
            if has_integrated_mics or has_integrated_speakers:
                warnings.append(
                    f"ℹ️ {video_bar_product.get('brand')} {video_bar_product.get('model_number')} "
                    f"has integrated audio - removing redundant components"
                )
                
                # Filter out redundant audio components
                for comp_key, comp in blueprint.items():
                    if hasattr(comp, 'category'):
                        # Remove table mics if video bar has integrated mics
                        if has_integrated_mics and comp.category == 'Audio' and 'Table' in comp.sub_category:
                            warnings.append(f"❌ Removed: {comp_key} (video bar has integrated microphones)")
                            continue
                        
                        # Remove DSP if video bar has built-in processing
                        if has_integrated_mics and comp.category == 'Audio' and 'DSP' in comp.sub_category:
                            # Only remove if it's a small room (video bar DSP sufficient)
                            if hasattr(comp, 'justification') and 'small' in comp.justification.lower():
                                warnings.append(f"❌ Removed: {comp_key} (video bar has integrated DSP)")
                                continue
                    
                    filtered_blueprint[comp_key] = comp
            else:
                filtered_blueprint = blueprint.copy()
        else:
            filtered_blueprint = blueprint.copy()
    else:
        filtered_blueprint = blueprint.copy()
    
    # === RULE 2: Brand Ecosystem Compatibility ===
    selected_brands = {}
    for comp_key, comp in filtered_blueprint.items():
        if hasattr(comp, 'category'):
            if comp.category == 'Video Conferencing':
                # Track video conferencing brand
                for product in selected_products:
                    if product.get('category') == 'Video Conferencing':
                        selected_brands['video_conferencing'] = product.get('brand', '').lower()
                        break
    
    # Check for cross-brand incompatibilities
    vc_brand = selected_brands.get('video_conferencing', '')
    
    if vc_brand:
        # If Poly video system, prefer Poly audio accessories
        if 'poly' in vc_brand:
            for comp_key, comp in list(filtered_blueprint.items()):
                if hasattr(comp, 'category') and comp.category == 'Audio':
                    if 'Table' in comp.sub_category or 'Microphone' in comp.sub_category:
                        # Add brand preference
                        comp.client_preference_weight = 0.95
                        comp.required_keywords = comp.required_keywords or []
                        if 'poly' not in [k.lower() for k in comp.required_keywords]:
                            warnings.append(
                                f"ℹ️ Prioritizing Poly audio accessories for {vc_brand} video system compatibility"
                            )
        
        # If Yealink video system, prefer Yealink accessories
        elif 'yealink' in vc_brand:
            for comp_key, comp in list(filtered_blueprint.items()):
                if hasattr(comp, 'category') and comp.category == 'Audio':
                    if 'Table' in comp.sub_category or 'Expansion' in comp.sub_category:
                        comp.client_preference_weight = 0.95
                        warnings.append(
                            f"ℹ️ Prioritizing Yealink audio accessories for {vc_brand} video system compatibility"
                        )
    
    # === RULE 3: DSP Redundancy Check ===
    has_external_dsp = 'audio_dsp' in filtered_blueprint
    has_video_codec_with_dsp = any(
        comp_key in ['video_codec', 'video_conferencing_system'] 
        for comp_key in filtered_blueprint
    )
    
    if has_external_dsp and has_video_codec_with_dsp:
        # Check if codec has built-in DSP capabilities
        for product in selected_products:
            if product.get('category') == 'Video Conferencing':
                product_specs = product.get('specifications', '').lower()
                if any(term in product_specs for term in ['dsp', 'audio processing', 'echo cancellation', 'noise reduction']):
                    warnings.append(
                        "⚠️ Video codec has built-in DSP - external DSP may be redundant for small/medium rooms"
                    )
    
    return filtered_blueprint, warnings


# ==================== NEW AI JUSTIFICATION FUNCTIONS (MODIFIED) ====================
def generate_ai_product_justification(model, product_info, room_context, avixa_calcs):
    """Generate intelligent, context-aware product justification using Gemini AI."""
    
    prompt = f"""You are an AV systems design expert. Generate a professional product justification for a client proposal.

**Room Context:**
- Room Type: {room_context.get('room_type', 'Conference Room')}
- Room Area: {room_context.get('room_area', 300)} sq ft
- Room Dimensions: {room_context.get('length', 24)}ft x {room_context.get('width', 16)}ft
- Ceiling Height: {room_context.get('ceiling_height', 10)}ft
- Primary Use: {room_context.get('primary_use', 'Video conferencing and presentations')}

**Selected Product:**
- Category: {product_info.get('category', 'Unknown')}
- Brand: {product_info.get('brand', 'Unknown')}
- Model: {product_info.get('model_number', 'Unknown')}
- Product Name: {product_info.get('name', 'Unknown')}
- Specifications: {product_info.get('specifications', 'N/A')[:200]}

**AVIXA Design Criteria Met:**
- Recommended Display Size: {avixa_calcs.get('display_size', 'N/A')}"
- Viewing Distance: {avixa_calcs.get('max_viewing_distance', 'N/A')}ft
- Audio Coverage: {avixa_calcs.get('audio_coverage', 'Adequate')}

**Task:**
Generate a concise, professional justification explaining WHY this specific product was selected.

**Output Format (JSON only):**
{{
  "technical_justification": "2-3 sentence internal technical explanation",
  "top_3_reasons": [
    "First client-facing reason (10-15 words max)",
    "Second client-facing reason (10-15 words max)", 
    "Third client-facing reason (10-15 words max)"
  ],
  "confidence": 0.95
}}

Be specific to THIS product and room. Use actual numbers from context."""

    try:
        # SIMPLIFIED: generate_with_retry now returns plain text by default
        response_text = generate_with_retry(model, prompt, return_text_only=True)
        
        if not response_text or not isinstance(response_text, str):
            st.warning("⚠️ AI returned non-text response. Using fallback.")
            return _get_fallback_justification(product_info, room_context)
        
        # Extract JSON from markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        result = json.loads(response_text)
        
        # Validate structure
        if not all(k in result for k in ['technical_justification', 'top_3_reasons', 'confidence']):
            st.warning("⚠️ AI response missing required fields. Using fallback.")
            return _get_fallback_justification(product_info, room_context)
        
        # Ensure exactly 3 reasons
        if len(result['top_3_reasons']) < 3:
            fallback = extract_top_3_reasons('', product_info.get('category', 'General'))
            while len(result['top_3_reasons']) < 3:
                result['top_3_reasons'].append(fallback[len(result['top_3_reasons'])])
        
        result['top_3_reasons'] = result['top_3_reasons'][:3]
        
        return result
        
    except json.JSONDecodeError as e:
        st.warning(f"⚠️ AI returned invalid JSON: {str(e)[:50]}. Using fallback.")
        return _get_fallback_justification(product_info, room_context)
    except Exception as e:
        st.warning(f"⚠️ AI justification generation failed: {str(e)[:50]}. Using fallback.")
        return _get_fallback_justification(product_info, room_context)


def _get_fallback_justification(product_info, room_context):
    """Fallback justification when AI generation fails."""
    category = product_info.get('category', 'General')
    room_type = room_context.get('room_type', 'conference room')
    
    fallback_reasons = extract_top_3_reasons('', category)
    
    return {
        'technical_justification': f"Selected based on {category} requirements for {room_type} application",
        'top_3_reasons': fallback_reasons,
        'confidence': 0.7
    }


# ==================== ENHANCED FALLBACK WITH CLIENT PREFERENCES ====================
def _get_fallback_product_legacy(category, sub_category, product_df, equipment_reqs=None, budget_tier='Standard', client_preferences=None):
    """
    LEGACY fallback - kept for backward compatibility
    Now we use IntelligentProductSelector instead
    """
    if sub_category:
        matches = product_df[
            (product_df['category'] == category) &
            (product_df['sub_category'] == sub_category)
        ].copy()
    else:
        matches = product_df[product_df['category'] == category].copy()

    if matches.empty:
        return None

    # === CRITICAL: STRICT SERVICE CONTRACT FILTER ===
    if category not in ['Software & Services']:
        # More aggressive pattern to catch all service contracts
        service_pattern = r'\b(support.*contract|maintenance.*contract|extended.*service|extended.*warranty|con-snt|con-ecdn|smartcare.*contract|jumpstart.*service|carepack|care\s*pack|premier.*support|advanced.*replacement|onsite.*support|warranty.*extension|service.*agreement)\b'
        matches = matches[~matches['name'].str.contains(service_pattern, case=False, na=False, regex=True)]
        
        # Additional check: if "warranty" or "service" in name but price < $100, likely a service contract
        matches = matches[~((matches['name'].str.contains(r'\b(warranty|service)\b', case=False, regex=True)) & 
                                  (matches['price'] < 100))]

    if matches.empty:
        return None

    # === APPLY CLIENT PREFERENCES FIRST ===
    if client_preferences:
        preferred_brand = None
        
        if category == 'Displays':
            preferred_brand = client_preferences.get('displays')
        elif category == 'Video Conferencing':
            preferred_brand = client_preferences.get('video_conferencing')
        elif category == 'Audio':
            preferred_brand = client_preferences.get('audio')
        elif category in ['Control Systems', 'Signal Management']:
            preferred_brand = client_preferences.get('control')
        
        if preferred_brand:
            brand_matches = matches[matches['brand'].str.lower() == preferred_brand.lower()]
            if not brand_matches.empty:
                matches = brand_matches
                st.info(f"✅ Using client-preferred brand: {preferred_brand} for {category}")

    # === DISPLAY MOUNT FIX ===
    if category == 'Mounts' and sub_category == 'Display Mount / Cart':
        # CRITICAL: Exclude ALL non-mount items
        MOUNT_BLACKLIST = [
            'finishing ring', 'trim ring', 'bezel', 'spacer', 'adapter plate',
            'x70 vesa', 'x50 vesa', 'x30 vesa', 'rally mount', 'studio mount',
            'camera mount', 'microphone mount', 'bracket kit', 'accessory'
        ]
        
        for blacklisted in MOUNT_BLACKLIST:
            matches = matches[~matches['name'].str.contains(blacklisted, case=False, na=False)]
        
        # REQUIRE mount-specific keywords
        mount_keywords = r'(wall.*mount|ceiling.*mount|floor.*stand|mobile.*stand|tv.*mount|display.*mount|fixed.*mount|tilt.*mount|articulating.*mount|cart|trolley)'
        matches = matches[matches['name'].str.contains(mount_keywords, case=False, na=False, regex=True)]
        
        # For large displays (85"+), require heavy-duty
        if equipment_reqs and 'displays' in equipment_reqs:
            req_size = equipment_reqs['displays'].get('size_inches', 65)
            if req_size >= 85:
                matches = matches[matches['name'].str.contains(
                    r'(heavy.*duty|large.*format|commercial|85|90|95|98|100)',
                    case=False, na=False, regex=True
                )]

    # === TABLE CONNECTIVITY FIX ===
    if sub_category == 'Wall & Table Plate Module':
        # Prioritize complete connectivity solutions
        connectivity_priority = r'(aap|table.*box|connectivity.*box|hdmi.*plate|retractor|tbus|hydraport|floor.*box)'
        priority_matches = matches[matches['name'].str.contains(connectivity_priority, case=False, na=False, regex=True)]
        
        if not priority_matches.empty:
            matches = priority_matches
        
        # Exclude mounting-only hardware
        matches = matches[~matches['name'].str.contains(
            r'(mounting.*frame.*only|blank.*plate|housing.*only|bracket.*only|trim.*ring)',
            case=False, na=False, regex=True
        )]

    # === TOUCH CONTROLLER FIX ===
    if 'Touch Controller' in sub_category:
        # STRICT: Must have touch/panel/controller keywords
        matches = matches[matches['name'].str.contains(
            r'(touch.*panel|touch.*controller|control.*panel|scheduling.*panel|room.*panel|tap|navigator)',
            case=False, na=False, regex=True
        )]
        
        # EXCLUDE video conferencing systems
        matches = matches[~matches['name'].str.contains(
            r'\b(room.*kit|codec|bar|camera|ess)\b',
            case=False, na=False, regex=True
        )]

    # === DSP SELECTION FIX ===
    if 'DSP' in sub_category or 'Processor' in sub_category:
        # EXCLUDE amplifiers completely
        matches = matches[~matches['name'].str.contains(
            r'\b(amplifier|amp-|summing|quad.*active|power.*amp)\b',
            case=False, na=False, regex=True
        )]
        
        # REQUIRE DSP indicators
        dsp_matches = matches[matches['name'].str.contains(
            r'(dsp|digital.*signal.*processor|audio.*processor|dante|aec|matrix|tesira|core|q-sys)',
            case=False, na=False, regex=True
        )]
        
        if not dsp_matches.empty:
            matches = dsp_matches

    # === AMPLIFIER SELECTION FIX ===
    if sub_category == 'Amplifier':
        # Phase 1: Exclude non-amplifier categories
        matches = matches[matches['sub_category'] == 'Amplifier']
        
        # Phase 2: Strict blacklist
        AMP_BLACKLIST = ['60-552', '60-553', 'summing', 'quad active', 'line driver', 
                         'audio interface', 'dsp', 'processor', 'mixer']
        for blacklisted in AMP_BLACKLIST:
            matches = matches[~matches['name'].str.contains(blacklisted, case=False, na=False, regex=True)]
        
        # Phase 3: Require power amp indicators
        power_amp_matches = matches[matches['name'].str.contains(
            r'(power.*amp|multi.*channel|70v|100v|watts.*channel|\d+w.*amp|spa\d+|xpa\d+|amplifier)',
            case=False, na=False, regex=True
        )]
        
        if not power_amp_matches.empty:
            matches = power_amp_matches
        else:
            st.warning(f"⚠️ No valid power amplifiers found for passive speakers")
            return None

    # === DISPLAY SIZE MATCHING ===
    if category == 'Displays' and equipment_reqs and 'displays' in equipment_reqs:
        req_size = equipment_reqs['displays'].get('size_inches', 65)
        size_range = range(req_size - 3, req_size + 4)
        size_pattern = '|'.join([f'{s}"' for s in size_range])

        size_matches = matches[matches['name'].str.contains(size_pattern, na=False, regex=True)]
        if not size_matches.empty:
            matches = size_matches

    if matches.empty:
        return None

    # === BUDGET-AWARE SELECTION ===
    sorted_matches = matches.sort_values('price')

    if budget_tier in ['Premium', 'Executive']:
        start_idx = int(len(sorted_matches) * 0.75)
        selection_pool = sorted_matches.iloc[start_idx:]
        if not selection_pool.empty:
            return selection_pool.iloc[len(selection_pool) // 2].to_dict()
    elif budget_tier == 'Economy':
        end_idx = int(len(sorted_matches) * 0.4)
        selection_pool = sorted_matches.iloc[:end_idx] if end_idx > 0 else sorted_matches
        return selection_pool.iloc[len(selection_pool) // 2].to_dict()

    # Standard: Middle 50%
    start_idx = int(len(sorted_matches) * 0.25)
    end_idx = int(len(sorted_matches) * 0.75)
    selection_pool = sorted_matches.iloc[start_idx:end_idx] if end_idx > start_idx else sorted_matches
    
    if selection_pool.empty:
        return sorted_matches.iloc[len(sorted_matches)//2].to_dict()

    return selection_pool.iloc[len(selection_pool) // 2].to_dict()


# ==================== COMPONENT BLUEPRINT WITH CONTROL SYSTEM ====================
def _build_component_blueprint(equipment_reqs, technical_reqs, budget_tier='Standard', room_area=300):
    """
    Enhanced blueprint using the NEW ProductRequirement dataclass
    """
    blueprint = {}
    
    room_length = technical_reqs.get('room_length', (room_area ** 0.5) * 1.2)
    room_width = technical_reqs.get('room_width', room_area / room_length if room_length > 0 else 15)
    ceiling_height = technical_reqs.get('ceiling_height', 10)

    # === DISPLAYS with STRICT REQUIREMENTS ===
    if 'displays' in equipment_reqs:
        display_reqs = equipment_reqs['displays']
        qty = display_reqs.get('quantity', 1)
        size = display_reqs.get('size_inches', 65)

        blueprint['primary_display'] = ProductRequirement(
            category='Displays',
            sub_category='Professional Display',
            quantity=qty,
            priority=1,
            justification=f'{size}" professional 4K display for primary viewing',
            size_requirement=size,
            required_keywords=['display', 'monitor', '4k', 'uhd'],
            blacklist_keywords=['mount', 'bracket', 'stand', 'arm'],
            client_preference_weight=0.8
        )

        # ===========================================================================
        # CHANGE 1: Update Display Mount Section
        # ===========================================================================
        blueprint['display_mount'] = ProductRequirement(
            category='Mounts',
            sub_category='Display Mount / Cart',
            quantity=qty,
            priority=8,
            justification=f'Professional wall/floor mount for {size}" display',
            size_requirement=size,
            mounting_type='wall' if ceiling_height > 9 else 'floor',
            required_keywords=['wall', 'mount', 'display', 'large'] if ceiling_height > 9 else ['cart', 'stand', 'mobile'],
            blacklist_keywords=[
                'ring', 'bezel', 'trim', 'spacer', 'adapter plate',
                'x70', 'x50', 'x30', 'rally', 'studio', 'camera',
                'accessory', 'bracket kit', 'finishing',
                'tlp', 'tsw', 'touch', 'panel', 'controller', 'ipad'
            ],
            compatibility_requirements=[f'{size}"'] if size >= 85 else [],
            min_price=200,  # NEW: Professional mounts start at $200
            max_price=2000, # NEW: Prevent selecting video wall systems
            strict_category_match=True  # NEW: Enforce strict validation
        )

    # === VIDEO SYSTEM ===
    if 'video_system' in equipment_reqs:
        video_reqs = equipment_reqs['video_system']
        video_type = video_reqs.get('type', '')

        if video_type == 'All-in-one Video Bar':
            blueprint['video_conferencing_system'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Video Bar',
                quantity=1,
                priority=2,
                justification='All-in-one video bar with integrated camera, microphones, and speakers',
                required_keywords=['bar', 'video', 'all-in-one', 'camera'],
                blacklist_keywords=['mount', 'accessory', 'bracket', 'replacement'],
                client_preference_weight=0.9
            )
        elif video_type == 'Modular Codec + PTZ Camera':
            blueprint['video_codec'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Room Kit / Codec',
                quantity=1,
                priority=2,
                justification='Video conferencing codec/room system',
                required_keywords=['codec', 'room kit', 'system'],
                blacklist_keywords=['camera only', 'accessory', 'mount', 'license'],
                client_preference_weight=0.9
            )
            
            camera_count = video_reqs.get('camera_count', 1)
            if camera_count > 0:
                blueprint['ptz_camera'] = ProductRequirement(
                    category='Video Conferencing',
                    sub_category='PTZ Camera',
                    quantity=camera_count,
                    priority=2.5,
                    justification=f'{camera_count}x PTZ camera(s) for comprehensive room coverage',
                    required_keywords=['ptz', 'camera', 'zoom', 'eagleeye'],
                    blacklist_keywords=['mount', 'bracket', 'accessory', 'webcam', 'usb'],
                    compatibility_requirements=[video_reqs.get('brand', '')],
                    min_price=1000  # NEW - Professional PTZ minimum price
                )

    # === CONTROL SYSTEM (MANDATORY) - BRAND MATCHED ===
    # NEW: Detect video conferencing brand for ecosystem matching
    vc_brand = None
    if 'video_system' in equipment_reqs:
        video_reqs = equipment_reqs['video_system']
        vc_brand = video_reqs.get('brand', '').lower()

    # ===========================================================================
    # CHANGE 2: Update Touch Controller Section
    # ===========================================================================
    # Build touch panel requirement with brand preference
    touch_panel_keywords = ['touch', 'controller', 'panel', 'control', 'room controller']
    touch_panel_blacklist = [
        'room kit', 'codec', 'bar', 'camera', 'display',
        'monitor', 'ess', 'system', 'video bar',
        'receiver', 'transmitter', 'scaler', 'switcher',  # NEW: Prevent selecting AV equipment
        'dm-', 'hdmi', 'extender', 'matrix'  # NEW: Prevent selecting signal processors
    ]

    # Brand-specific keywords for ecosystem match
    if vc_brand:
        if 'cisco' in vc_brand:
            touch_panel_keywords.extend(['cisco', 'touch 10'])
            st.info(f"🔗 Matching touch panel to Cisco ecosystem")
            touch_panel_blacklist.extend(['poly', 'yealink', 'crestron tss'])
        elif 'poly' in vc_brand:
            touch_panel_keywords.extend(['poly', 'tc8'])
            st.info(f"🔗 Matching touch panel to Poly ecosystem")
        elif 'yealink' in vc_brand:
            touch_panel_keywords.extend(['yealink', 'ctp'])

    blueprint['touch_control_panel'] = ProductRequirement(
        category='Video Conferencing',
        sub_category='Touch Controller / Panel',
        quantity=1,
        priority=3,
        justification=f'Touch control panel for system control (brand-matched to {vc_brand or "video system"})',
        required_keywords=touch_panel_keywords,
        blacklist_keywords=touch_panel_blacklist,
        compatibility_requirements=[vc_brand] if vc_brand else [],
        min_price=300,  # NEW: Touch panels start at $300
        max_price=5000, # NEW: Prevent selecting full control systems
        strict_category_match=True  # NEW: Enforce strict validation
    )
    
    # === ROOM SCHEDULING PANEL (Executive/Large Conference Rooms) ===
    if technical_reqs.get('room_type') in ['Executive Boardroom', 'Large Conference', 'Board Room'] or room_area > 500:
        blueprint['room_scheduling_panel'] = ProductRequirement(
            category='Control Systems',
            sub_category='Touch Panel',  # ✅ CHANGED: Use existing category
            quantity=1,
            priority=13,
            justification='Touch panel for room scheduling and calendar integration',
            required_keywords=['touch', 'panel', 'scheduling', 'room', '10"', 'wall mount'],
            blacklist_keywords=['video conferencing', 'codec', 'camera'],
            min_price=300,
            max_price=2000,
            strict_category_match=False  # Allow broader matching
        )
        st.info("📅 Adding room scheduling panel (executive room detected)")

    # === AUDIO SYSTEM WITH REDUNDANCY CHECK ===
    if 'audio_system' in equipment_reqs:
        audio_reqs = equipment_reqs['audio_system']
        audio_type = audio_reqs.get('type', '')
        needs_dsp = audio_reqs.get('dsp_required', False)
        
        # CRITICAL: Check if audio is integrated in video system
        has_integrated_audio = any(term in audio_type.lower() for term in 
            ['integrated', 'video bar', 'all-in-one'])
        
        # Large room audio is NEVER integrated
        is_large_room_audio = any(x in audio_type.lower() for x in 
            ['ceiling audio', 'pro audio', 'voice reinforcement', 'fully integrated'])
        
        if is_large_room_audio:
            has_integrated_audio = False
            needs_dsp = True
        
        # === NEW: Don't add redundant components for integrated systems ===
        if not has_integrated_audio:
            # Only add DSP if truly needed AND not integrated
            if needs_dsp:
                blueprint['audio_dsp'] = ProductRequirement(
                    category='Audio',
                    sub_category='DSP / Audio Processor / Mixer',
                    quantity=1,
                    priority=4,
                    justification='Digital signal processor for audio management (large room or complex audio)',
                    required_keywords=['dsp', 'processor', 'audio', 'digital'],
                    blacklist_keywords=[
                        'amplifier', 'amp-', 'power amp', 'summing',
                        '60-552', '60-553', 'line driver'
                    ],
                    client_preference_weight=0.7
                )

            # Microphones
            mic_type = audio_reqs.get('microphone_type', '')
            mic_count = audio_reqs.get('microphone_count', 0)
            
            if mic_type and mic_count > 0:
                if 'ceiling' in mic_type.lower():
                    blueprint['ceiling_microphones'] = ProductRequirement(
                        category='Audio',
                        sub_category='Ceiling Microphone',
                        quantity=mic_count,
                        priority=5,
                        justification=f'{mic_count}x ceiling microphones for audio pickup',
                        required_keywords=['ceiling', 'microphone', 'mic'],
                        blacklist_keywords=['mount', 'bracket', 'accessory', 'table']
                    )
                elif 'table' in mic_type.lower():
                    # NEW: Add note that this might be redundant with video bar
                    blueprint['table_microphones'] = ProductRequirement(
                        category='Audio',
                        sub_category='Table/Boundary Microphone',
                        quantity=mic_count,
                        priority=5,
                        justification=f'{mic_count}x table microphones (check for video bar redundancy)',
                        required_keywords=['table', 'boundary', 'microphone'],
                        blacklist_keywords=['ceiling', 'wireless', 'mount']
                    )

            # Speakers (same logic)
            speaker_type = audio_reqs.get('speaker_type', '')
            speaker_count = audio_reqs.get('speaker_count', 0)
            
            if speaker_type and speaker_count > 0:
                if 'ceiling' in speaker_type.lower():
                    blueprint['ceiling_speakers'] = ProductRequirement(
                        category='Audio',
                        sub_category='Ceiling Loudspeaker',
                        quantity=speaker_count,
                        priority=6,
                        justification=f'{speaker_count}x ceiling speakers',
                        required_keywords=['ceiling', 'speaker', 'loudspeaker'],
                        blacklist_keywords=['mount', 'bracket', 'wall', 'portable']
                    )
                    
                    # Add amplifier for passive speakers
                    if speaker_count > 0:
                        blueprint['power_amplifier'] = ProductRequirement(
                            category='Audio',
                            sub_category='Amplifier',
                            quantity=1,
                            priority=7,
                            justification=f'Power amplifier for {speaker_count} passive speakers',
                            power_requirement=speaker_count * 100,
                            required_keywords=['amplifier', 'power', 'channel', 'watts'],
                            blacklist_keywords=[
                                'summing', 'quad active', 'line driver',
                                '60-552', '60-553', 'dsp', 'processor',
                                'mixer', 'interface'
                            ]
                        )
        else:
            # Log that we're skipping audio components due to integration
            st.info(f"ℹ️ Audio system type '{audio_type}' indicates integrated audio - skipping separate audio components")


    # === CONNECTIVITY ===
    if equipment_reqs.get('content_sharing') or 'wireless presentation' in technical_reqs.get('features', '').lower():
        blueprint['table_connectivity'] = ProductRequirement(
            category='Cables & Connectivity',
            sub_category='Wall & Table Plate Module',
            quantity=1,
            priority=9,
            justification='Table connectivity with HDMI, USB-C, and network',
            required_keywords=['table', 'plate', 'connectivity', 'hdmi'],
            blacklist_keywords=['mounting frame only', 'blank plate', 'housing only', 'trim ring']
        )
    
    # === VIDEO SWITCHING (For rooms with multiple sources) ===
    num_displays = equipment_reqs.get('displays', {}).get('quantity', 1)
    has_presentation = 'wireless presentation' in technical_reqs.get('features', '').lower()
    has_multiple_sources = technical_reqs.get('video_sources', 0) > 2
    
    # ===========================================================================
    # CHANGE 4: Update Video Switcher Section
    # ===========================================================================
    # Add switcher if:
    # - Multiple displays OR
    # - Multiple video sources OR  
    # - Large room (>600 sqft)
    if num_displays > 1 or has_multiple_sources or room_area > 600:
        blueprint['video_switcher'] = ProductRequirement(
            category='Signal Management',
            sub_category='Matrix Switcher',  # ✅ MATCHES process_data.py categorization
            quantity=1,
            priority=4,
            justification=f'Video matrix switcher for routing {num_displays} displays and multiple sources',
            required_keywords=['switcher', 'matrix', 'hdmi', 'routing', 'presentation'],
            blacklist_keywords=['cable', 'adapter', 'extender only', 'receiver only', 'mount', 'bracket'],
            min_price=500,
            max_price=15000,
            strict_category_match=True
        )
        st.info(f"📺 Adding video switcher (multi-display or large room detected)")
    
    # === WIRELESS PRESENTATION ===
    if any(term in technical_reqs.get('features', '').lower() for term in 
           ['wireless', 'byod', 'bring your own', 'clickshare', 'airmedia', 'content sharing']):
        blueprint['wireless_presentation'] = ProductRequirement(
            category='Signal Management',
            sub_category='Wireless Presentation',
            quantity=1,
            priority=9,
            justification='Wireless presentation system for BYOD content sharing',
            required_keywords=['wireless', 'presentation', 'clickshare', 'airmedia', 'wePresent'],
            blacklist_keywords=['cable', 'adapter', 'receiver only']
        )
        st.info("📡 Adding wireless presentation system")
        
    # === CABLE CALCULATION (More realistic) ===
    # Base cables: 2 per major component
    component_count = len([k for k in blueprint.keys() if k not in ['network_cables']])
    base_cables = component_count * 2
    
    # Room size factor
    if room_area < 150:  # Small huddle
        size_multiplier = 1.0
    elif room_area < 400:  # Medium rooms
        size_multiplier = 1.5
    else:  # Large rooms
        size_multiplier = 2.0

    cable_count = max(5, int(base_cables * size_multiplier))  # Minimum 5 cables

    # ===========================================================================
    # CHANGE 7: Update Network Cables Section
    # ===========================================================================
    blueprint['network_cables'] = ProductRequirement(
        category='Cables & Connectivity',
        sub_category='AV Cable',
        quantity=cable_count,
        priority=10,
        justification=f'{cable_count}x Cat6/Cat7 cables for equipment connectivity (calculated: {component_count} components × 2 × {size_multiplier:.1f})',
        required_keywords=['cat6', 'cat7', 'ethernet', 'network'],
        blacklist_keywords=['bulk', 'spool', 'reel', 'vga', 'svideo'],
        min_price=10,  # NEW: Individual cables should be at least $10
        max_price=150, # NEW: Prevent selecting cable bundles or spools
        strict_category_match=True  # NEW: Enforce strict validation
    )

    st.info(f"🔌 Cable quantity: {cable_count} (based on {component_count} components and {room_area} sqft room)")

    # === INFRASTRUCTURE ===
    # ===========================================================================
    # CHANGE 3: Update Equipment Rack Section
    # ===========================================================================
    if equipment_reqs.get('housing', {}).get('type') == 'AV Rack':
        blueprint['equipment_rack'] = ProductRequirement(
            category='Infrastructure',
            sub_category='AV Rack',
            quantity=1,
            priority=12,
            justification='Equipment rack for AV components',
            required_keywords=['rack', 'enclosure', 'cabinet', 'frame'],
            blacklist_keywords=[
                'shelf only', 'mount kit', 'accessory', 'bracket',
                'wall mount', 'camera', 'display', 'speaker'  # NEW: Prevent accessories
            ],
            min_price=100,  # NEW: Real racks cost more than $100
            max_price=3000, # NEW: Reasonable upper limit
            strict_category_match=True  # NEW: Enforce strict validation
        )

    if equipment_reqs.get('power_management', {}).get('type') == 'Rackmount PDU':
        blueprint['power_distribution'] = ProductRequirement(
            category='Infrastructure',
            sub_category='Power (PDU/UPS)',
            quantity=1,
            priority=11,
            justification='Rackmount PDU with surge protection and metering',
            required_keywords=['pdu', 'rack', 'metered', 'switched'], # More specific
            blacklist_keywords=['ups battery', 'replacement battery', 'consumer', 'home']
        )

    return blueprint


# ==================== MAIN BOQ GENERATION ====================
def generate_boq_from_ai(model, product_df, guidelines, room_type, budget_tier, features, technical_reqs, room_area):
    """
    PRODUCTION-READY BOQ generation with AI-powered justifications.
    ENHANCED: Check if questionnaire data exists first
    """
    
    # ========== STEP 1: NLP PARSING ==========
    st.info("🧠 Step 1: Parsing client requirements with NLP...")
    
    # NEW: Priority 1 - Use questionnaire data if available
    if st.session_state.get('questionnaire_complete'):
        q_data = st.session_state.questionnaire_data
        
        # Override with questionnaire data
        room_type = q_data['room_type']
        budget_tier = q_data['budget_tier']
        features = q_data['features']
        client_preferences = q_data['client_preferences']
        
        st.info(f"🎯 Using questionnaire data (Confidence: {q_data['questionnaire_confidence']*100:.0f}%)")
        
        # Skip NLP parsing - we already have structured data!
        nlp_results = {
            'client_preferences': client_preferences,
            'equipment_overrides': q_data.get('equipment_overrides', {}),
            'parsed_requirements': {}, # Add empty dict for compatibility
            'confidence_score': q_data['questionnaire_confidence']
        }
    else:
        # Fallback to existing NLP parsing
        nlp_results = extract_room_specific_requirements(features)
    
    client_preferences = nlp_results.get('client_preferences', {})
    equipment_overrides = nlp_results.get('equipment_overrides', {})
    parsed_requirements = nlp_results.get('parsed_requirements', {})
    
    if client_preferences:
        prefs_display = ", ".join([f"{k.replace('_', ' ').title()}: {v}" 
                                   for k, v in client_preferences.items() if v])
        if prefs_display:
            st.success(f"✅ Client Preferences Detected: {prefs_display}")
    
    if parsed_requirements.get('special_requirements'):
        st.info(f"⚡ Special Requirements: {', '.join(parsed_requirements['special_requirements'][:3])}")
    
    confidence = nlp_results.get('confidence_score', 0) * 100
    st.write(f"📊 NLP/Questionnaire Confidence: {confidence:.1f}%")
    
    # ========== STEP 2: AVIXA CALCULATIONS ==========
    st.info("📐 Step 2: Calculating AVIXA-compliant specifications...")
    
    length = (room_area ** 0.5) * 1.2
    width = room_area / length
    
    avixa_calcs = calculate_avixa_recommendations(
        length, width,
        technical_reqs.get('ceiling_height', 10),
        room_type
    )
    
    # ========== STEP 3: EQUIPMENT REQUIREMENTS ==========
    st.info("🔧 Step 3: Determining equipment requirements...")
    
    # Add features and room_type to technical_reqs for use in _build_component_blueprint
    technical_reqs['features'] = features
    technical_reqs['room_type'] = room_type

    base_equipment_reqs = determine_equipment_requirements(avixa_calcs, room_type, technical_reqs)
    equipment_reqs = merge_equipment_requirements(base_equipment_reqs, equipment_overrides)
    
    # ===========================================================================
    # CHANGE 8: Add Display Quantity Validation
    # ===========================================================================
    # NEW: Validate display quantity for room size
    if 'displays' in equipment_reqs:
        display_qty = equipment_reqs['displays'].get('quantity', 1)
        display_size = equipment_reqs['displays'].get('size_inches', 65)
        
        # Warn if multiple large displays in standard room
        if display_qty > 1 and room_area < 800:
            st.warning(
                f"⚠️ Room size ({room_area} sqft) may not require {display_qty}x {display_size}\" displays. "
                f"Standard rooms typically use 1 display. Verify with client requirements."
            )
            
            # Show confirmation
            with st.expander("🔍 Multiple Display Configuration", expanded=True):
                st.info(f"""
                **Current Configuration:**
                - Room Size: {room_area} sqft
                - Displays: {display_qty}x {display_size}"
                
                **Typical Configurations:**
                - Small Rooms (<200 sqft): 1x 55-65" display
                - Medium Rooms (200-500 sqft): 1x 65-75" display
                - Large Rooms (500-800 sqft): 1x 75-98" display
                - Very Large Rooms (>800 sqft): 2x displays or video wall
                
                If this is a video wall configuration, ensure appropriate mounting and processing equipment is included.
                """)
    
    st.write("🔍 **DEBUG: Equipment Requirements**")
    st.json(equipment_reqs) # This will show you what's being passed to blueprint
    
    # ========== STEP 4: BUILD COMPONENT BLUEPRINT ==========
    st.info("📋 Step 4: Building component blueprint...")
    
    required_components = _build_component_blueprint(
        equipment_reqs, 
        technical_reqs, 
        budget_tier, 
        room_area
    )
    
    # Also add after blueprint creation
    st.write("🔍 **DEBUG: Component Blueprint**")
    for key, req in required_components.items():
        st.write(f"- {key}: {req.required_keywords} | Blacklist: {req.blacklist_keywords}")
    
    st.write(f"✅ Blueprint created with {len(required_components)} components")
    
    # ========== STEP 5: INTELLIGENT PRODUCT SELECTION WITH AI JUSTIFICATIONS ==========
    st.info("🎯 Step 5: Selecting products and generating justifications...")
    
    # Initialize selector
    selector = IntelligentProductSelector(
        product_df=product_df,
        client_preferences=client_preferences,
        budget_tier=budget_tier
    )
    
    boq_items = []
    selection_summary = []
    
    # Room context for AI justifications
    room_context = {
        'room_type': room_type,
        'room_area': room_area,
        'length': length,
        'width': width,
        'ceiling_height': technical_reqs.get('ceiling_height', 10),
        'primary_use': features[:100] if features else 'Video conferencing and presentations'
    }
    
    # Sort components by priority
    sorted_components = sorted(
        required_components.items(),
        key=lambda x: x[1].priority if hasattr(x[1], 'priority') else 999
    )
    
    progress_bar = st.progress(0)
    for idx, (comp_key, comp_spec) in enumerate(sorted_components):
        progress = (idx + 1) / len(sorted_components)
        progress_bar.progress(progress, text=f"Selecting {comp_key}...")
        
        # NEW: Pass existing selections for compatibility checking
        selector.existing_selections = boq_items # Add this attribute
        
        # Select product
        product = selector.select_product(comp_spec)
        
        if product:
            # ===========================================================================
            # CHANGE 6: Add Post-Selection Validation
            # ===========================================================================
            # NEW: Additional validation for specific categories
            if comp_spec.category == 'Mounts' and 'Display Mount' in comp_spec.sub_category:
                # Validate mount is appropriate for display size
                if hasattr(comp_spec, 'size_requirement') and comp_spec.size_requirement:
                    mount_name = product.get('name', '').lower()
                    size_indicators = [f'{s}"' for s in range(int(comp_spec.size_requirement) - 5, int(comp_spec.size_requirement) + 5)]
                    has_size_match = any(indicator in mount_name for indicator in size_indicators)
                    
                    if not has_size_match and comp_spec.size_requirement >= 85:
                        st.warning(
                            f"⚠️ Mount '{product.get('brand')} {product.get('model_number')}' "
                            f"may not explicitly support {comp_spec.size_requirement}\" displays. "
                            f"Verify compatibility before ordering."
                        )
            
            if comp_spec.category == 'Infrastructure' and 'AV Rack' in comp_spec.sub_category:
                # Validate this is actually a rack, not a bracket
                rack_name = product.get('name', '').lower()
                if 'bracket' in rack_name or 'mount' in rack_name:
                    st.error(
                        f"❌ CRITICAL: '{product.get('name')}' is not an equipment rack. "
                        f"This is a {product.get('sub_category')}. Product selection failed validation."
                    )
                    product = None  # Reject this product
            
            if comp_spec.category == 'Video Conferencing' and 'Touch Controller' in comp_spec.sub_category:
                # Validate this is actually a touch panel, not a receiver/scaler
                controller_name = product.get('name', '').lower()
                if any(term in controller_name for term in ['receiver', 'transmitter', 'scaler', 'switcher', 'extender']):
                    st.error(
                        f"❌ CRITICAL: '{product.get('name')}' is not a touch controller. "
                        f"This is video processing equipment. Product selection failed validation."
                    )
                    product = None  # Reject this product
            
            # Only proceed if product passed validation
            if product is None:
                selection_summary.append(f"❌ {comp_key}: FAILED VALIDATION")
                continue

            # === AFTER MICROPHONE SELECTION ===
            if 'microphone' in product.get('sub_category', '').lower():
                mic_price = product.get('price', 0)
                mic_qty = comp_spec.quantity
                
                # Validate pricing makes sense
                if mic_price > 2000 and mic_qty > 1:
                    # Likely an array or system - adjust quantity
                    st.warning(
                        f"⚠️ High-priced microphone detected (${mic_price:.0f}). "
                        f"This may be a complete array system. Consider setting quantity to 1."
                    )
                    
                    # Auto-correct if it's clearly an array
                    if any(term in product.get('name', '').lower() for term in 
                           ['array', 'kit', 'system', 'bundle', 'package']):
                        comp_spec.quantity = 1
                        st.info(f"✅ Auto-corrected quantity to 1 (array/system product)")

            # === NEW: Generate AI-powered justification ===
            ai_justification = generate_ai_product_justification(
                model=model,
                product_info=product,
                room_context=room_context,
                avixa_calcs=avixa_calcs
            )
            
            product.update({
                'quantity': comp_spec.quantity,
                'justification': ai_justification.get('technical_justification', comp_spec.justification),
                'top_3_reasons': ai_justification.get('top_3_reasons', []),
                'justification_confidence': ai_justification.get('confidence', 0.8),
                'matched': True
            })
            
            boq_items.append(product)
            
            # Show confidence in selection summary
            confidence_icon = "🟢" if ai_justification.get('confidence', 0) > 0.85 else "🟡" if ai_justification.get('confidence', 0) > 0.7 else "🟠"
            selection_summary.append(
                f"{confidence_icon} {comp_key}: {product.get('brand')} {product.get('model_number')} "
                f"(AI Confidence: {ai_justification.get('confidence', 0)*100:.0f}%)"
            )
        else:
            selection_summary.append(f"❌ {comp_key}: NOT FOUND")
            st.warning(f"⚠️ Could not find suitable product for: {comp_key}")
    
    progress_bar.empty()
    
    # ========== NEW: COMPATIBILITY & REDUNDANCY CHECK ==========
    st.info("🔍 Step 5.5: Checking brand compatibility and feature redundancy...")
    
    filtered_blueprint, compat_warnings = check_component_compatibility(
        required_components, 
        boq_items
    )
    
    # Show compatibility warnings
    if compat_warnings:
        with st.expander("⚠️ Compatibility Analysis", expanded=True):
            for warning in compat_warnings:
                if '❌' in warning:
                    st.success(warning) # Removed redundant component
                elif 'ℹ️' in warning:
                    st.info(warning) # Informational
                else:
                    st.warning(warning)
    
    # Remove items that were filtered out
    filtered_boq_items = []
    for item in boq_items:
        keep_item = True
        for warning in compat_warnings:
            if '❌ Removed:' in warning:
                # Extract component key from warning
                if any(cat in warning for cat in ['table_microphones', 'audio_dsp']):
                    if item.get('sub_category') in ['Table/Boundary Microphone', 'DSP / Audio Processor / Mixer']:
                        # Check if this item should be removed
                        if ('Table' in item.get('sub_category', '') and 'microphone' in warning.lower()) or \
                           ('DSP' in item.get('sub_category', '') and 'dsp' in warning.lower()):
                            keep_item = False
                            break
        
        if keep_item:
            filtered_boq_items.append(item)
    
    boq_items = filtered_boq_items
    
    # Show selection summary
    with st.expander("📊 Product Selection Details", expanded=False):
        st.markdown("### Selection Results with AI Confidence")
        for summary_line in selection_summary:
            st.write(summary_line)
        
        st.write("\n**Detailed Selection Log:**")
        st.code(selector.get_selection_report())
        
        # Show AI justification quality
        avg_confidence = sum(item.get('justification_confidence', 0) for item in boq_items) / len(boq_items) if boq_items else 0
        st.metric("Average AI Justification Quality", f"{avg_confidence*100:.1f}%")

    # ===========================================================================
    # CHANGE 5: Add Validation Report Display
    # ===========================================================================
    # NEW: Display validation warnings if any
    validation_warnings = selector.get_validation_warnings()
    if validation_warnings:
        with st.expander("⚠️ Product Validation Warnings", expanded=True):
            st.warning(f"Found {len(validation_warnings)} products that failed validation:")
            for warning in validation_warnings:
                st.error(f"""
                **Component**: {warning['component']}
                **Product**: {warning['product']}
                **Issues**:
                """)
                for issue in warning['issues']:
                    st.write(f"  - {issue}")
            st.info("💡 These products were automatically rejected and alternatives were selected.")
    
    if not boq_items:
        st.error("❌ No products could be selected. Please check your requirements.")
        return [], {}, {}, {}
    
    # ========== STEP 6: VALIDATION ==========
    st.info("✅ Step 6: Validating BOQ completeness...")
    
    processed_boq, validation_results = post_process_boq(
        boq_items, product_df, avixa_calcs,
        equipment_reqs, room_type, required_components
    )
    
    st.success(f"✅ BOQ generated with {len(processed_boq)} items and AI-powered justifications!")
    
    return processed_boq, avixa_calcs, equipment_reqs, validation_results


# ==================== POST-PROCESSING ====================
def post_process_boq(boq_items, product_df, avixa_calcs, equipment_reqs, room_type, required_components):
    """Enhanced validation with AI justifications for auto-added items."""
    validation_results = {'issues': [], 'warnings': []}
    
    # Check for control system
    has_control = any('Touch Controller' in item.get('sub_category', '') or 
                      'Control' in item.get('category', '') 
                      for item in boq_items)
    
    if not has_control:
        validation_results['warnings'].append("⚠️ No control system found - adding touch controller")
        
        control_product = _get_fallback_product_legacy(
            'Video Conferencing',
            'Touch Controller / Panel',
            product_df,
            equipment_reqs,
            'Standard'
        )
        
        if control_product:
            # Generate AI justification for auto-added component
            control_reasons = [
                "Centralized control simplifies meeting operations for non-technical users",
                "Touch interface provides intuitive system management and scheduling",
                "Essential for professional meeting room functionality and user adoption"
            ]
            
            control_product.update({
                'quantity': 1,
                'justification': 'Touch controller provides centralized system control and meeting room scheduling (Auto-added for complete system functionality)',
                'top_3_reasons': control_reasons,
                'justification_confidence': 0.9,
                'matched': True
            })
            boq_items.append(control_product)
    
    # Validate display mounts
    display_count = sum(1 for item in boq_items if item.get('category') == 'Displays')
    mount_count = sum(1 for item in boq_items if item.get('category') == 'Mounts' and 
                      'Display Mount' in item.get('sub_category', ''))
    
    if display_count > 0 and mount_count == 0:
        validation_results['issues'].append("🚨 CRITICAL: Display present but NO proper mount found")
    elif mount_count > 0:
        for item in boq_items:
            if item.get('category') == 'Mounts':
                if any(word in item.get('name', '').lower() for word in ['ring', 'bezel', 'trim', 'spacer']):
                    validation_results['issues'].append(f"🚨 INVALID MOUNT: {item.get('name')} is not a proper display mount")
    
    return boq_items, validation_results


# Keep existing helper functions (boq_to_dataframe, calculate_boq_summary, etc.)
def boq_to_dataframe(boq_items):
    """Convert BOQ items to DataFrame"""
    if not boq_items:
        return pd.DataFrame()
    
    df = pd.DataFrame(boq_items)
    
    required_columns = [
        'category', 'sub_category', 'name', 'brand', 'model_number',
        'quantity', 'price', 'justification', 'specifications',
        'gst_rate', 'warranty', 'lead_time_days'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''
    
    df['line_total'] = df['quantity'] * df['price']
    df['gst_amount'] = df['line_total'] * (df['gst_rate'] / 100)
    df['total_with_gst'] = df['line_total'] + df['gst_amount']
    
    return df


def calculate_boq_summary(boq_df):
    """Calculate summary statistics"""
    if boq_df.empty:
        return {'total_items': 0, 'total_quantity': 0, 'subtotal': 0, 
                'total_gst': 0, 'grand_total': 0, 'categories': {}}
    
    summary = {
        'total_items': len(boq_df),
        'total_quantity': int(boq_df['quantity'].sum()),
        'subtotal': float(boq_df['line_total'].sum()),
        'total_gst': float(boq_df['gst_amount'].sum()),
        'grand_total': float(boq_df['total_with_gst'].sum()),
        'categories': {}
    }
    
    if 'category' in boq_df.columns:
        summary['categories'] = boq_df.groupby('category').agg({
            'quantity': 'sum',
            'line_total': 'sum',
            'total_with_gst': 'sum'
        }).to_dict('index')
    
    return summary
