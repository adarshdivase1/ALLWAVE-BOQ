import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import streamlit as st
import pandas as pd

@dataclass
class ProductRequirement:
    """Structured requirement for a component"""
    category: str
    sub_category: str
    quantity: int
    priority: int
    justification: str
    
    # Detailed specifications
    size_requirement: Optional[float] = None
    power_requirement: Optional[int] = None
    connectivity_type: Optional[str] = None
    mounting_type: Optional[str] = None
    compatibility_requirements: List[str] = None
    
    # Must-have keywords (product MUST contain these)
    required_keywords: List[str] = None
    # Blacklist keywords (product MUST NOT contain these)
    blacklist_keywords: List[str] = None
    
    # Client preference weight (0-1, higher = more important)
    client_preference_weight: float = 0.5
    
    # Minimum price for initial filtering
    min_price: Optional[float] = None
    
    # NEW: Maximum price for filtering (prevents selecting overpriced items)
    max_price: Optional[float] = None
    
    # NEW: Strict category validation (prevents cross-category contamination)
    strict_category_match: bool = True


class IntelligentProductSelector:
    """
    ENHANCED: Advanced product selection with strict validation and safeguards
    """
    
    def __init__(self, product_df, client_preferences=None, budget_tier='Standard'):
        self.product_df = product_df.copy()
        self.client_preferences = client_preferences or {}
        self.budget_tier = budget_tier
        self.selection_log = []
        self.existing_selections = []
        self.validation_warnings = []  # NEW: Track validation issues
        
        # Standardize columns
        self._standardize_price_column()
        self._normalize_dataframe_categories()
        
        # NEW: Build category validation database
        self._build_category_validators()
    
    def _standardize_price_column(self):
        """Ensure consistent 'price' column"""
        price_columns = [col for col in self.product_df.columns if 'price' in col.lower()]
        
        if 'price' not in self.product_df.columns:
            if 'price_usd' in self.product_df.columns:
                self.product_df['price'] = self.product_df['price_usd']
                self.log("✅ Standardized column: 'price_usd' → 'price'")
            elif 'price_inr' in self.product_df.columns:
                self.product_df['price'] = self.product_df['price_inr']
                self.log("✅ Standardized column: 'price_inr' → 'price'")
            elif len(price_columns) > 0:
                self.product_df['price'] = self.product_df[price_columns[0]]
                self.log(f"✅ Standardized column: '{price_columns[0]}' → 'price'")
    
    def _normalize_dataframe_categories(self):
        """Ensure consistent category naming"""
        if 'primary_category' in self.product_df.columns and 'category' not in self.product_df.columns:
            self.product_df['category'] = self.product_df['primary_category']
    
    def _build_category_validators(self):
        """
        NEW: Build strict validation rules for each category
        This prevents products from wrong categories being selected
        """
        self.category_validators = {
            'Displays': {
                'must_contain': ['display', 'monitor', 'screen', 'panel', 'lcd', 'led', 'oled'],
                'must_not_contain': ['mount', 'bracket', 'stand', 'arm', 'cable', 'adapter'],
                'price_range': (200, 30000)
            },
            'Mounts': {
                'must_contain': ['mount', 'bracket', 'stand', 'cart', 'rack'],
                'must_not_contain': ['display', 'monitor', 'camera', 'microphone', 'speaker'],
                'price_range': (50, 3000),
                'sub_category_validators': {
                    'Display Mount / Cart': {
                        'must_contain': ['wall', 'ceiling', 'floor', 'stand', 'cart', 'mobile'],
                        'must_not_contain': ['camera', 'mic', 'speaker', 'touch', 'panel', 'controller']
                    }
                }
            },
            'Video Conferencing': {
                'must_contain': ['video', 'camera', 'codec', 'conference', 'conferencing', 'bar', 'room kit', 'ptz', 'touch', 'controller', 'panel'], # ADDED touch/controller/panel
                'must_not_contain': ['audio only', 'speaker only'],
                'price_range': (300, 20000),
                'sub_category_validators': {
                    'Touch Controller / Panel': {
                        'must_contain': ['touch', 'controller', 'panel'], # REMOVED 'control' (too generic)
                        'must_not_contain': ['receiver', 'transmitter', 'extender', 'scaler', 'switcher', 'matrix', 'room kit', 'codec', 'bar', 'camera system'], # ADDED more exclusions
                        'override_category_validation': True # NEW FLAG: Skip parent category validation
                    },
                    'PTZ Camera': {
                        'must_contain': ['camera', 'ptz', 'pan', 'tilt', 'zoom'],
                        'must_not_contain': ['mount', 'bracket', 'accessory', 'cable']
                    }
                }
            },
            'Audio': {
                'must_contain': ['audio', 'speaker', 'microphone', 'mic', 'amplifier', 'dsp', 'processor'],
                'must_not_contain': ['video', 'display'],
                'price_range': (50, 10000),
                'sub_category_validators': {
                    'Amplifier': {
                        'must_contain': ['amplifier', 'amp', 'power', 'channel', 'watts'],
                        'must_not_contain': ['dsp', 'processor', 'mixer', 'interface', 'summing']
                    }
                }
            },
            'Control Systems': {
                'must_contain': ['control', 'controller', 'processor', 'automation', 'touch', 'panel'],
                'must_not_contain': [],
                'price_range': (100, 15000)
            },
            'Signal Management': {
                'must_contain': ['switcher', 'matrix', 'scaler', 'extender', 'distribution', 'routing'],
                'must_not_contain': ['mount', 'bracket'],
                'price_range': (100, 20000)
            },
            'Infrastructure': {
                'must_contain': ['rack', 'cabinet', 'enclosure', 'pdu', 'power', 'ups'],
                'must_not_contain': ['display', 'monitor', 'camera'],
                'price_range': (50, 5000),
                'sub_category_validators': {
                    'AV Rack': {
                        'must_contain': ['rack', 'cabinet', 'enclosure', 'frame'],
                        'must_not_contain': ['mount', 'bracket', 'shelf only', 'camera', 'display']
                    }
                }
            },
            'Cables & Connectivity': {
                'must_contain': ['cable', 'connectivity', 'plate', 'module', 'hdmi', 'ethernet', 'cat'],
                'must_not_contain': [],
                'price_range': (5, 500)
            }
        }
    
    def _validate_product_category(self, product: Dict, req: ProductRequirement) -> Tuple[bool, List[str]]:
        """
        NEW: Strict validation that product actually belongs to the requested category
        Returns: (is_valid, list_of_issues)
        """
        issues = []
        product_name = product.get('name', '').lower()
        product_category = product.get('category', '')
        product_subcategory = product.get('sub_category', '')
        
        validators = self.category_validators.get(req.category, {})
        
        # NEW: Check if sub-category has override flag
        sub_validators = validators.get('sub_category_validators', {}).get(req.sub_category, {})
        skip_parent_validation = sub_validators.get('override_category_validation', False)
        
        # Check category match
        if product_category != req.category and req.strict_category_match:
            issues.append(f"Category mismatch: Expected '{req.category}', got '{product_category}'")
            return False, issues
        
        # Check parent category keywords ONLY if not overridden
        if not skip_parent_validation: # NEW CONDITION
            must_contain = validators.get('must_contain', [])
            if must_contain:
                has_required = any(keyword in product_name for keyword in must_contain)
                if not has_required:
                    issues.append(f"Missing required keywords for {req.category}: {must_contain}")
                    return False, issues
        
        # Check must_not_contain keywords (contamination check)
        must_not_contain = validators.get('must_not_contain', [])
        if must_not_contain:
            has_forbidden = any(keyword in product_name for keyword in must_not_contain)
            if has_forbidden:
                forbidden_found = [kw for kw in must_not_contain if kw in product_name]
                issues.append(f"Contains forbidden keywords: {forbidden_found}")
                return False, issues
        
        # Check sub-category specific validators
        if sub_validators:
            sub_must_contain = sub_validators.get('must_contain', [])
            if sub_must_contain:
                has_sub_required = any(keyword in product_name for keyword in sub_must_contain)
                if not has_sub_required:
                    issues.append(f"Missing sub-category keywords for {req.sub_category}: {sub_must_contain}")
                    return False, issues
            
            sub_must_not_contain = sub_validators.get('must_not_contain', [])
            if sub_must_not_contain:
                has_sub_forbidden = any(keyword in product_name for keyword in sub_must_not_contain)
                if has_sub_forbidden:
                    forbidden_found = [kw for kw in sub_must_not_contain if kw in product_name]
                    issues.append(f"Contains sub-category forbidden keywords: {forbidden_found}")
                    return False, issues
        
        # Check price range
        price_range = validators.get('price_range')
        if price_range:
            min_price, max_price = price_range
            product_price = product.get('price', 0)
            if product_price < min_price or product_price > max_price:
                issues.append(f"Price ${product_price:.2f} outside expected range ${min_price}-${max_price}")
                return False, issues
        
        return True, []
    
    def select_product(self, requirement: ProductRequirement) -> Optional[Dict]:
        """
        ENHANCED: Multi-stage product selection with strict validation
        """
        self.log(f"\n{'='*60}")
        self.log(f"🎯 Selecting product for: {requirement.sub_category}")
        self.log(f"    Category: {requirement.category}")
        self.log(f"    Quantity: {requirement.quantity}")
        
        # STAGE 1: Category Filter
        candidates = self._filter_by_category(requirement)
        if candidates.empty:
            self.log(f"❌ No products found in category: {requirement.category}/{requirement.sub_category}")
            return None
        
        # STAGE 2: Service Contract Filter
        candidates = self._filter_service_contracts(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ All products were service contracts")
            return None
        
        # STAGE 3: Keyword Filters
        candidates = self._apply_keyword_filters(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ No products passed keyword filters")
            return None
        
        # STAGE 4: Specification Matching (with size validation)
        candidates = self._match_specifications(candidates, requirement)
        if candidates.empty:
            self.log(f"⚠️ No products matched specifications, using broader search")
            candidates = self._filter_by_category(requirement)
            candidates = self._filter_service_contracts(candidates, requirement)
            candidates = self._apply_keyword_filters(candidates, requirement)
        
        # NEW STAGE 4.5: Strict Category Validation
        candidates = self._apply_strict_validation(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ No products passed strict validation for {requirement.category}")
            return None
        
        # STAGE 5: Client Preference Weighting
        candidates = self._apply_client_preferences(candidates, requirement)
        
        # STAGE 5.5: Brand Ecosystem Check
        candidates = self._check_brand_ecosystem(candidates, requirement, self.existing_selections)
        
        # STAGE 6: Budget-Aware Selection
        selected = self._select_by_budget(candidates, requirement)
        
        if selected is not None:
            # STAGE 7: Final Validation
            is_valid, validation_issues = self._validate_product_category(selected, requirement)
            
            if not is_valid:
                self.log(f"❌ VALIDATION FAILED:")
                for issue in validation_issues:
                    self.log(f"    - {issue}")
                self.validation_warnings.append({
                    'component': requirement.sub_category,
                    'product': selected.get('name'),
                    'issues': validation_issues
                })
                return None
            
            price = selected.get('price', 0)
            self.log(f"✅ SELECTED: {selected['brand']} {selected['model_number']}")
            self.log(f"    Price: ${price:.2f}")
            self.log(f"    Product: {selected['name'][:80]}")
            
            # Compatibility check
            if not self._validate_compatibility(selected, requirement):
                self.log(f"⚠️ Product may have compatibility issues")
        
        # NEW STAGE 8: Fallback for hard-to-find items
        if selected is None and requirement.sub_category in ['Room Scheduling Display', 'Touch Controller / Panel']:
            self.log(f"    🔄 Attempting fallback search for {requirement.sub_category}")
            
            # Try broader category search
            fallback_candidates = self.product_df[
                self.product_df['category'].isin(['Control Systems', 'Video Conferencing', 'Displays'])
            ].copy()
            
            # Apply relaxed keywords
            fallback_keywords = {
                'Room Scheduling Display': ['scheduling', 'calendar', 'room panel', 'booking'],
                'Touch Controller / Panel': ['touch', 'panel', 'controller', '10"', 'ipad']
            }
            
            keywords = fallback_keywords.get(requirement.sub_category, [])
            if keywords:
                pattern = '|'.join([re.escape(kw) for kw in keywords])
                fallback_candidates = fallback_candidates[
                    fallback_candidates['name'].str.contains(pattern, case=False, na=False, regex=True)
                ]
                
                if not fallback_candidates.empty:
                    self.log(f"    ✅ Found {len(fallback_candidates)} fallback candidates")
                    selected = self._select_by_budget(fallback_candidates, requirement)
        
        return selected
    
    def _apply_strict_validation(self, df, req: ProductRequirement):
        """
        NEW STAGE: Apply strict category validation to all candidates
        """
        validated_products = []
        
        for idx, product in df.iterrows():
            is_valid, issues = self._validate_product_category(product, req)
            if is_valid:
                validated_products.append(product)
            else:
                self.log(f"    ⚠️ Rejected: {product.get('name', 'Unknown')[:60]}")
                for issue in issues[:2]:  # Show first 2 issues
                    self.log(f"         Reason: {issue}")
        
        if validated_products:
            self.log(f"✅ {len(validated_products)} products passed strict validation")
            return pd.DataFrame(validated_products)
        else:
            self.log(f"❌ No products passed strict validation")
            return pd.DataFrame()
    
    def _filter_by_category(self, req: ProductRequirement):
        """Stage 1: Filter by category"""
        
        if req.category == 'General AV':
            df = self.product_df[
                self.product_df['name'].str.contains(req.sub_category, case=False, na=False) |
                self.product_df['description'].str.contains(req.sub_category, case=False, na=False)
            ].copy()
        elif req.sub_category:
            df = self.product_df[
                (self.product_df['category'] == req.category) &
                (self.product_df['sub_category'] == req.sub_category)
            ].copy()
        else:
            df = self.product_df[self.product_df['category'] == req.category].copy()
        
        # Apply minimum/maximum price if specified
        if hasattr(req, 'min_price') and req.min_price:
            df = df[df['price'] >= req.min_price]
        if hasattr(req, 'max_price') and req.max_price:
            df = df[df['price'] <= req.max_price]
        
        self.log(f"    Stage 1 - Category filter: {len(df)} products")
        return df
    
    def _filter_service_contracts(self, df, req: ProductRequirement):
        """Stage 2: Filter out service contracts"""
        if req.category == 'Software & Services':
            return df
        
        service_patterns = [
            r'\b(support.*contract|maintenance.*contract|extended.*service)\b',
            r'\b(extended.*warranty|con-snt|con-ecdn|smartcare.*contract)\b',
            r'\b(jumpstart.*service|carepack|care\s*pack|premier.*support)\b',
            r'\b(advanced.*replacement|onsite.*support|warranty.*extension)\b',
            r'\b(service.*agreement|service.*plan|support.*plan)\b',
            r'\b(annual.*support|yearly.*support|subscription.*support)\b'
        ]
        
        for pattern in service_patterns:
            df = df[~df['name'].str.contains(pattern, case=False, na=False, regex=True)]
        
        df = df[~((df['name'].str.contains(r'\b(warranty|service|support)\b', case=False, regex=True)) &
                  (df['price'] < 100))]
        
        self.log(f"    Stage 2 - Service filter: {len(df)} products")
        return df
    
    def _apply_keyword_filters(self, df, req: ProductRequirement):
        """Stage 3: Apply required and blacklist keywords"""
        
        # Required keywords
        if req.required_keywords:
            pattern = '|'.join([re.escape(kw) for kw in req.required_keywords])
            df = df[df['name'].str.contains(pattern, case=False, na=False, regex=True)]
            self.log(f"    Stage 3a - Required keywords: {len(df)} products")
        
        # Blacklist keywords
        if req.blacklist_keywords:
            for keyword in req.blacklist_keywords:
                before = len(df)
                df = df[~df['name'].str.contains(re.escape(keyword), case=False, na=False, regex=True)]
                removed = before - len(df)
                if removed > 0:
                    self.log(f"    Stage 3b - Blacklist '{keyword}': removed {removed}")
        
        # Category-specific filters
        df = self._apply_category_specific_filters(df, req)
        
        self.log(f"    Stage 3 - Keyword filter: {len(df)} products")
        return df
    
    def _apply_category_specific_filters(self, df, req: ProductRequirement):
        """Enhanced category-specific filtering"""
        
        if req.category == 'Mounts' and 'Display Mount' in req.sub_category:
            df = df[df['name'].str.contains(
                r'(wall.*mount|ceiling.*mount|floor.*stand|display.*mount|tv.*mount|large.*format.*mount)',
                case=False, na=False, regex=True
            )]
            df = df[~df['name'].str.contains(
                r'(tlp|tsw-|touch|panel|controller|ipad|camera|speaker|mic)',
                case=False, na=False, regex=True
            )]
        
        elif req.category == 'Cables & Connectivity' and 'AV Cable' in req.sub_category:
            df = df[df['name'].str.contains(
                r'(cat6|cat7|ethernet|network.*cable|patch.*cable)',
                case=False, na=False, regex=True
            )]
            df = df[~df['name'].str.contains(
                r'(vga|svideo|composite|component)',
                case=False, na=False, regex=True
            )]
        
        elif req.category == 'Infrastructure' and 'Power' in req.sub_category:
            df = df[df['price'] > 100]
            df = df[df['name'].str.contains(
                r'(rack.*mount|1u|2u|metered|switched)',
                case=False, na=False, regex=True
            )]
        
        elif req.category == 'Audio' and req.sub_category == 'Amplifier':
            df = df[df['name'].str.contains(
                r'(power.*amp|multi.*channel|spa\d+|xpa\d+|\d+w)',
                case=False, na=False, regex=True
            )]
            df = df[~df['name'].str.contains(
                r'(conferenc|poe\+|dante.*amp|amp.*dante)',
                case=False, na=False, regex=True
            )]
        
        elif req.category == 'Video Conferencing' and 'PTZ Camera' in req.sub_category:
            df = df[df['name'].str.contains(
                r'(ptz|pan.*tilt.*zoom|eagleeye.*iv|eagleeye.*director|eptz)',
                case=False, na=False, regex=True
            )]
            df = df[~df['name'].str.contains(
                r'(webcam|usb.*camera|c920|c930|brio)',
                case=False, na=False, regex=True
            )]
            df = df[df['price'] > 1000]
        
        elif req.category == 'Infrastructure' and 'AV Rack' in req.sub_category:
            # CRITICAL: Ensure we get actual racks, not shelves
            df = df[df['name'].str.contains(
                r'(\d+u.*rack|\d+u.*cabinet|\d+u.*enclosure|equipment.*rack|relay.*rack|wall.*mount.*rack|open.*frame.*rack)',
                case=False, na=False, regex=True
            )]
            
            # NEW: Explicitly exclude shelves and small accessories
            df = df[~df['name'].str.contains(
                r'(shelf|bracket|mount(?!.*rack)|camera|wall.*mount(?!.*rack)|1u(?!.*rack)|2u(?!.*rack))',
                case=False, na=False, regex=True
            )]
            
            # NEW: Price validation - real racks cost more
            df = df[df['price'] > 300]  # Minimum $300 for actual rack
            
            self.log(f"    🔍 Filtered for actual racks (not shelves): {len(df)} products")
        
        return df
    
    def _match_specifications(self, df, req: ProductRequirement):
        """Stage 4: Match technical specifications"""
        
        # Display size matching with tolerance
        if req.size_requirement:
            size_range = range(int(req.size_requirement) - 3, int(req.size_requirement) + 4)
            size_pattern = '|'.join([f'{s}"' for s in size_range])
            size_matches = df[df['name'].str.contains(size_pattern, na=False, regex=True)]
            if not size_matches.empty:
                df = size_matches
                self.log(f"    Stage 4a - Size matching ({req.size_requirement}\"): {len(df)} products")
        
        # Mounting type matching
        if req.mounting_type:
            if 'wall' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\bwall\b', case=False, na=False, regex=True)]
                
                if req.size_requirement and req.size_requirement >= 85:
                    df = self._validate_mount_capacity(df, req)
                    df = df[~df['model_number'].str.contains(
                        r'(mtm\d|msm\d|xsm\d)',
                        case=False, na=False, regex=True
                    )]
            elif 'ceiling' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\bceiling\b', case=False, na=False, regex=True)]
            elif 'floor' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\b(floor|stand|cart|mobile)\b', case=False, na=False, regex=True)]
        
        self.log(f"    Stage 4 - Specification match: {len(df)} products")
        return df
    
    def _validate_mount_capacity(self, df, req: ProductRequirement):
        """Validate mount can support the display size"""
        if not req.size_requirement or req.size_requirement < 85:
            return df
        
        validated_mounts = []
        
        for idx, product in df.iterrows():
            name = product.get('name', '').lower()
            specs = str(product.get('specifications', '')).lower()
            combined = f"{name} {specs}"
            
            # ENHANCED: More flexible large display indicators
            has_large_support = any(term in combined for term in [
                f'{int(req.size_requirement)}"', 
                f'{int(req.size_requirement)-5}"', # Wider tolerance
                f'{int(req.size_requirement)+5}"', # Cover range
                'large format', 'video wall', 'videowall',
                '150 lbs', '175 lbs', '200 lbs', '225 lbs', '250 lbs',
                'vesa 800', 'vesa 1000', 'vesa 900',
                'up to 98"', 'up to 100"', 'up to 110"', # NEW
                '85" and above', '90" and above', # NEW
                'xlarge', 'x-large', 'xxl' # NEW
            ])
            
            # STRICT: Only reject if explicitly too small
            is_explicitly_small = any(term in combined for term in [
                'up to 55"', 'up to 60"', 'up to 65"', 'up to 70"',
                'max 55"', 'max 60"', 'max 65"', 'max 70"',
                'small format', 'compact only', 'lightweight only'
            ])
            
            # Accept if large support OR (not explicitly small AND not video wall mount)
            is_video_wall_mount = 'video wall' in combined or 'videowall' in combined
            
            if has_large_support or (not is_explicitly_small and is_video_wall_mount):
                validated_mounts.append(product)
        
        if validated_mounts:
            self.log(f"    ✅ {len(validated_mounts)} mounts validated for {req.size_requirement}\" display")
            return pd.DataFrame(validated_mounts)
        else:
            self.log(f"    ⚠️ No validated mounts for {req.size_requirement}\" - using all candidates")
            return df
    
    def _apply_client_preferences(self, df, req: ProductRequirement):
        """Stage 5: Weight products by client preferences"""
        
        preferred_brand = None
        
        if req.category == 'Displays':
            preferred_brand = self.client_preferences.get('displays')
        elif req.category == 'Video Conferencing':
            preferred_brand = self.client_preferences.get('video_conferencing')
        elif req.category == 'Audio':
            preferred_brand = self.client_preferences.get('audio')
        elif req.category in ['Control Systems', 'Signal Management']:
            preferred_brand = self.client_preferences.get('control')
        
        if preferred_brand:
            df['preference_score'] = df['brand'].str.lower().apply(
                lambda x: req.client_preference_weight if x == preferred_brand.lower() else 0
            )
            df = df.sort_values('preference_score', ascending=False)
            
            preferred_matches = df[df['preference_score'] > 0]
            if not preferred_matches.empty:
                self.log(f"    ✅ Found {len(preferred_matches)} preferred brand products: {preferred_brand}")
                return preferred_matches
        
        return df
    
    def _check_brand_ecosystem(self, df, req: ProductRequirement, existing_selections):
        """Stage 5.5: Ensure brand ecosystem compatibility"""
        
        if req.category in ['Audio', 'Video Conferencing']:
            vc_brand = None
            for selected in existing_selections:
                if selected.get('category') == 'Video Conferencing':
                    if 'Video Bar' in selected.get('sub_category', '') or \
                       'Room Kit' in selected.get('sub_category', ''):
                        vc_brand = selected.get('brand', '').lower()
                        break
            
            if vc_brand:
                if req.category == 'Audio' and any(term in req.sub_category for term in ['Microphone', 'Expansion']):
                    brand_matches = df[df['brand'].str.lower() == vc_brand]
                    if not brand_matches.empty:
                        self.log(f"    ✅ Prioritizing {vc_brand} accessories for ecosystem")
                        return brand_matches
        
        return df
    
    def _select_by_budget(self, df, req: ProductRequirement):
        """Stage 6: Select based on budget tier"""
        
        if df.empty:
            return None
        
        df_sorted = df.sort_values('price')
        
        if self.budget_tier in ['Premium', 'Executive']:
            start_idx = int(len(df_sorted) * 0.75)
            selection_pool = df_sorted.iloc[start_idx:]
        elif self.budget_tier == 'Economy':
            end_idx = int(len(df_sorted) * 0.4)
            selection_pool = df_sorted.iloc[:end_idx] if end_idx > 0 else df_sorted
        else:  # Standard
            start_idx = int(len(df_sorted) * 0.25)
            end_idx = int(len(df_sorted) * 0.75)
            selection_pool = df_sorted.iloc[start_idx:end_idx] if end_idx > start_idx else df_sorted
        
        if selection_pool.empty:
            selection_pool = df_sorted
        
        selected_idx = len(selection_pool) // 2
        return selection_pool.iloc[selected_idx].to_dict()
    
    def _validate_compatibility(self, product: Dict, req: ProductRequirement) -> bool:
        """Stage 7: Validate product compatibility"""
        
        if not req.compatibility_requirements:
            return True
        
        product_name = product.get('name', '').lower()
        product_specs = str(product.get('specifications', '')).lower()
        combined_text = f"{product_name} {product_specs}"
        
        # NEW: Special handling for display mounts
        if req.category == 'Mounts' and 'Display Mount' in req.sub_category:
            # Video wall mounts are inherently compatible with large displays
            if any(term in combined_text for term in ['video wall', 'videowall', 'large format']):
                self.log(f"    ✅ Video wall mount - compatible with large displays")
                return True
            
            # Check for explicit size compatibility
            for compat in req.compatibility_requirements:
                if str(compat) in combined_text or f'up to {compat}' in combined_text:
                    return True
            
            # If mount doesn't explicitly exclude the size, assume compatible
            size_req = req.size_requirement if hasattr(req, 'size_requirement') else 0
            if size_req:
                exclusion_patterns = [f'up to {s}"' for s in range(40, int(size_req)-10)]
                is_explicitly_incompatible = any(pattern in combined_text for pattern in exclusion_patterns)
                
                if not is_explicitly_incompatible:
                    self.log(f"    ✅ No size exclusions found - assuming compatible")
                    return True
        
        # Original compatibility check for other categories
        for compat in req.compatibility_requirements:
            if compat.lower() not in combined_text:
                self.log(f"    ⚠️ Missing compatibility: {compat}")
                return False
        
        return True
    
    def log(self, message: str):
        """Add to selection log"""
        self.selection_log.append(message)
    
    def get_selection_report(self) -> str:
        """Get detailed selection report"""
        return "\n".join(self.selection_log)
    
    def get_validation_warnings(self) -> List[Dict]:
        """Get all validation warnings"""
        return self.validation_warnings
