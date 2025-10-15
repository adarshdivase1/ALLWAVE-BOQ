import re
from typing import Dict, List, Optional, Tuple, Any
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

# CRITICAL FIX: Enhanced Brand Compatibility & Ecosystem Logic
class BrandEcosystemManager:
    """
    Manages brand compatibility, ecosystem consistency, and intelligent fallbacks
    """
    
    def __init__(self):
        # Brand family relationships (ecosystem consistency)
        self.brand_ecosystems = {
            'microsoft': {
                'primary': 'Microsoft',
                'vc_partners': ['Yealink', 'Poly', 'Cisco', 'Logitech'],
                'audio_partners': ['Shure', 'QSC', 'Biamp'],
                'control_partners': ['Crestron', 'Extron', 'AMX'],
                'ecosystem_score': 0.8  # How much we penalize switching
            },
            'zoom': {
                'primary': 'Zoom',
                'vc_partners': ['Poly', 'Logitech', 'Yealink'],
                'audio_partners': ['Bose', 'Shure', 'QSC'],
                'control_partners': ['Crestron'],
                'ecosystem_score': 0.75
            },
            'cisco': {
                'primary': 'Cisco',
                'vc_partners': ['Cisco', 'Polycom'],
                'audio_partners': ['QSC', 'Shure'],
                'control_partners': ['Crestron', 'Extron'],
                'ecosystem_score': 0.85
            }
        }
        
        # Brand substitution matrix (when preferred brand unavailable)
        self.brand_substitutions = {
            'displays': {
                'Samsung': ['LG', 'Sony', 'NEC'],
                'LG': ['Samsung', 'Sony'],
                'Sony': ['Samsung', 'LG', 'NEC'],
                'NEC': ['Sharp', 'Panasonic']
            },
            'video_conferencing': {
                'Yealink': ['Poly', 'Logitech'],  # Compatible, similar quality tier
                'Poly': ['Yealink', 'Logitech'],
                'Cisco': ['Polycom'],
                'Logitech': ['Poly', 'Yealink']
            },
            'audio': {
                'QSC': ['Biamp', 'Shure'],
                'Biamp': ['QSC'],
                'Shure': ['Sennheiser'],
                'Bose': ['Shure']
            },
            'control': {
                'Crestron': ['Extron', 'AMX'],
                'Extron': ['Crestron', 'Kramer'],
                'AMX': ['Crestron']
            }
        }
    
    def get_substitute_brands(self, category, preferred_brand):
        """Get ordered list of acceptable substitute brands"""
        # The category in brand_substitutions might not perfectly match the product category
        # e.g., 'Control Systems' -> 'control'
        category_key_map = {
            'Displays': 'displays',
            'Video Conferencing': 'video_conferencing',
            'Audio': 'audio',
            'Control Systems': 'control',
            'Signal Management': 'control'
        }
        lookup_key = category_key_map.get(category, category.lower())
        category_subs = self.brand_substitutions.get(lookup_key, {})
        return category_subs.get(preferred_brand, [])
    
    def is_ecosystem_compatible(self, vc_platform, audio_brand, control_brand):
        """Check if brands form a compatible ecosystem"""
        vc_lower = vc_platform.lower()
        
        for ecosystem_key, ecosystem in self.brand_ecosystems.items():
            if ecosystem_key in vc_lower:
                audio_compatible = audio_brand in ecosystem.get('audio_partners', [])
                control_compatible = control_brand in ecosystem.get('control_partners', [])
                
                if audio_compatible and control_compatible:
                    return True, 1.0  # Perfect match
                elif audio_compatible or control_compatible:
                    return True, 0.8  # Partial match
                else:
                    return False, 0.5  # Mismatch
        
        return True, 0.7  # Default: assume compatible


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
                'must_not_contain': ['camera', 'microphone', 'speaker', 'menu', 'menu board', 'food service'],
                'price_range': (50, 3000),
                'sub_category_validators': {
                    'Display Mount / Cart': {
                        'must_contain': ['wall', 'ceiling', 'floor', 'stand', 'cart', 'mobile', 'display', 'tv', 'video wall'],
                        'must_not_contain': ['camera', 'mic', 'speaker', 'touch', 'panel', 'controller', 'menu', 'menu board']
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
            },
            # Add this new validator for AVIXA compliance
            'AVIXA_Display_Sizing': {
                'min_size_for_distance': {
                    # viewing_distance_ft: min_display_inches
                    10: 43,
                    15: 55,
                    20: 65,
                    25: 75,
                    30: 85,
                    35: 98
                }
            },
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
        ENHANCED: Multi-stage product selection with strict validation and detailed logging
        """
        self.log(f"\n{'='*60}")
        self.log(f"🎯 Selecting product for: {requirement.sub_category}")
        self.log(f"    Category: {requirement.category}")
        self.log(f"    Quantity: {requirement.quantity}")
        self.log(f"    Required Keywords: {requirement.required_keywords}")
        self.log(f"    Blacklist: {requirement.blacklist_keywords}")
        self.log(f"    Min Price: ${requirement.min_price}")
        
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
        selected = self._select_by_budget(candidates, requirement, self.existing_selections)
        
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

            # STAGE 7.5: AVIXA Display Sizing Validation
            if selected and selected.get('category') == 'Displays' and hasattr(self, 'requirements_context'):
                room_context = self.requirements_context
                is_avixa_compliant, avixa_msg = self._validate_avixa_display_sizing(selected, room_context)
                
                if not is_avixa_compliant:
                    self.log(f"    ⚠️ AVIXA WARNING: {avixa_msg}")
                    self.validation_warnings.append({
                        'component': requirement.sub_category,
                        'product': selected.get('name'),
                        'issue': avixa_msg,
                        'severity': 'HIGH'
                    })
            
            price = selected.get('price', 0)
            self.log(f"✅ SELECTED: {selected['brand']} {selected['model_number']}")
            self.log(f"    Price: ${price:.2f}")
            self.log(f"    Score: {selected.get('data_quality_score', 'N/A')}")
            self.log(f"    Product: {selected['name'][:80]}")
            
            # Compatibility check
            if not self._validate_compatibility(selected, requirement):
                self.log(f"⚠️ Product may have compatibility issues")
        
        else:
            self.log(f"❌ SELECTION FAILED - No matching products found after all filters")
            self.validation_warnings.append({
                'component': requirement.sub_category,
                'issue': 'No products matched all criteria',
                'severity': 'CRITICAL'
            })

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
                    selected = self._select_by_budget(fallback_candidates, requirement, self.existing_selections)
        
        return selected
    
    def select_product_with_fallback(self, requirement: ProductRequirement) -> Optional[Dict]:
        """
        ENHANCED: Try strict selection first, then intelligent fallbacks
        """
        
        # Attempt 1: Strict selection
        selected = self.select_product(requirement)
        
        if selected:
            return selected
        
        # Attempt 2: Relax brand preference if nothing found
        if requirement.client_preference_weight == 1.0:
            self.log(f"    🔄 No products found with strict brand preference, trying alternates...")
            requirement.client_preference_weight = 0.5
            selected = self.select_product(requirement)
            
            if selected:
                self.validation_warnings.append({
                    'component': requirement.sub_category,
                    'issue': f'Client-preferred brand not available, using {selected.get("brand")}',
                    'severity': 'MEDIUM'
                })
                return selected
        
        # Attempt 3: Broaden category search
        self.log(f"    🔄 Attempting broader category search...")
        
        if requirement.category == 'Video Conferencing' and 'PTZ Camera' in requirement.sub_category:
            # Try room kits that include cameras
            requirement.sub_category = 'Room Kit / Codec'
            requirement.required_keywords = ['room kit', 'camera', 'system']
            selected = self.select_product(requirement)
            
            if selected:
                self.validation_warnings.append({
                    'component': requirement.sub_category,
                    'issue': 'Using room kit instead of standalone PTZ camera',
                    'severity': 'LOW'
                })
                return selected
        
        # Attempt 4: Log failure for manual intervention
        self.log(f"    ❌ FAILED: Could not find suitable product for {requirement.sub_category}")
        self.validation_warnings.append({
            'component': requirement.sub_category,
            'issue': f'No suitable products found in catalog',
            'severity': 'CRITICAL'
        })
        
        return None
    
    def suggest_alternatives(self, selected_product: Dict, requirement: ProductRequirement, count: int = 3) -> List[Dict]:
        """
        Suggest alternative products if client wants options
        """
        
        alternatives = []
        
        # Get similar products
        similar_products = self.product_df[
            (self.product_df['category'] == requirement.category) &
            (self.product_df['sub_category'] == requirement.sub_category)
        ].copy()
        
        # Remove the selected product
        similar_products = similar_products[
            similar_products['model_number'] != selected_product.get('model_number')
        ]
        
        if similar_products.empty:
            return []
        
        # Score alternatives based on:
        # 1. Price similarity (±20%)
        # 2. Brand reputation
        # 3. Feature richness
        
        selected_price = selected_product.get('price', 0)
        
        similar_products['price_similarity'] = similar_products['price'].apply(
            lambda x: 100 - abs(x - selected_price) / selected_price * 100 if selected_price > 0 else 0
        )
        
        # Sort by quality score and price similarity
        similar_products = similar_products.sort_values(
            by=['data_quality_score', 'price_similarity'],
            ascending=[False, False]
        )
        
        # Return top alternatives
        for _, product in similar_products.head(count).iterrows():
            alt = product.to_dict()
            alt['price_difference'] = product['price'] - selected_price
            alt['price_difference_pct'] = (alt['price_difference'] / selected_price * 100) if selected_price > 0 else 0
            alternatives.append(alt)
        
        return alternatives

    def _validate_avixa_display_sizing(self, product: Dict, room_context: Dict) -> Tuple[bool, str]:
        """
        Validates display size against AVIXA DISCAS standards
        """
        if product.get('category') != 'Displays':
            return True, "N/A"
        
        # Extract display size
        display_size = self._extract_display_size_from_product(product)
        if not display_size:
            return True, "Cannot validate - size unknown"
        
        # Get room viewing distance
        viewing_distance = room_context.get('avixa_calcs', {}).get('display', {}).get('max_viewing_distance_ft', 0)
        if viewing_distance == 0:
            return True, "No viewing distance available"
        
        # Check against AVIXA standards
        validators = self.category_validators.get('AVIXA_Display_Sizing', {})
        min_size_map = validators.get('min_size_for_distance', {})
        
        # Find closest viewing distance bracket
        distance_brackets = sorted(min_size_map.keys())
        closest_bracket = min([d for d in distance_brackets if d >= viewing_distance], default=distance_brackets[-1])
        min_recommended = min_size_map.get(closest_bracket, 55)
        
        if display_size < min_recommended - 5:  # 5" tolerance
            return False, f"Display {display_size}\" undersized for {viewing_distance:.1f}ft viewing distance (AVIXA min: {min_recommended}\")"
        
        return True, f"AVIXA compliant for {viewing_distance:.1f}ft viewing distance"

    def _extract_display_size_from_product(self, product: Dict) -> Optional[int]:
        """Extract display size in inches from product name or specs"""
        import re
        
        text = f"{product.get('name', '')} {product.get('model_number', '')} {product.get('specifications', '')}"
        
        # ENHANCED: Try multiple patterns
        patterns = [
            r'(\d{2,3})["\']',           # 65" or 65'
            r'(\d{2,3})\s*inch',          # 65 inch
            r'(\d{2,3})-inch',            # 65-inch
            r'\b(\d{2,3})\s*"',           # 65 "
            r'QH(\d{2,3})',               # Samsung QH43 format
            r'-(\d{2,3})[A-Z]',           # -43C format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    size = int(match.group(1))
                    if 40 <= size <= 120:  # Reasonable range
                        return size
                except (ValueError, IndexError):
                    continue
        
        return None

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
        
        elif req.category == 'Audio' and req.sub_category == 'DSP / Audio Processor / Mixer':
            # CRITICAL: Exclude powered speakers and portable systems
            df = df[df['name'].str.contains(
                r'(dsp|processor|mixer|tesira|biamp|qsc.*core|dante|avhub|intellimix)',
                case=False, na=False, regex=True
            )]
            df = df[~df['name'].str.contains(
                r'(speaker|loudspeaker|portable|active.*speaker|powered.*speaker|cp\d+|k\d+\.\d+)',
                case=False, na=False, regex=True
            )]
            df = df[df['price'] > 800]  # Real DSPs cost more than $800
            
            self.log(f"    🔍 Filtered for actual DSP/processors: {len(df)} products")
        
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
        """FIXED: More flexible large display validation"""
        if not req.size_requirement or req.size_requirement < 85:
            return df
        
        validated_mounts = []
        
        for idx, product in df.iterrows():
            name = product.get('name', '').lower()
            specs = str(product.get('specifications', '')).lower()
            combined = f"{name} {specs}"
            
            # CRITICAL FIX: Accept if ANY of these conditions are true:
            has_large_support = any(term in combined for term in [
                f'{int(req.size_requirement)}"',
                'large format', 'video wall', 'videowall',
                '150 lbs', '175 lbs', '200 lbs', '225 lbs',
                'vesa 800', 'vesa 1000',
                'up to 98"', 'up to 100"', 'up to 110"',
                '85" and above', '90" and above'
            ])
            
            # Only reject if EXPLICITLY too small
            is_explicitly_small = any(term in combined for term in [
                'max 55"', 'max 60"', 'max 65"', 'max 70"',
                'small format only', 'lightweight only'
            ])
            
            # ACCEPT IF: large support OR (not explicitly small AND is video wall mount)
            is_video_wall_mount = 'video wall' in combined or 'videowall' in combined
            
            if has_large_support or (not is_explicitly_small and is_video_wall_mount):
                validated_mounts.append(product)
        
        if validated_mounts:
            self.log(f"    ✅ {len(validated_mounts)} mounts validated for {req.size_requirement}\" display")
            return pd.DataFrame(validated_mounts)
        else:
            # FALLBACK: If strict validation finds nothing, return all candidates
            self.log(f"    ⚠️ Strict validation found no mounts - using all candidates")
            return df

    def _apply_client_preferences(self, df, req: ProductRequirement):
        """
        STRICT brand preference enforcement with intelligent fallbacks.
        Does NOT silently return random products.
        """
    
        if df.empty:
            return df
    
        # Get preferred brand for this category
        preferred_brand = self._get_client_preference_for_category(req.category)
    
        if not preferred_brand or preferred_brand == 'No Preference':
            self.log(f"     ℹ️ No brand preference for {req.category}")
            return df  # Return all candidates if no preference
    
        # ============ ATTEMPT 1: Exact brand match ============
        exact_matches = df[df['brand'].str.lower() == preferred_brand.lower()]
    
        if not exact_matches.empty:
            self.log(f"     ✅ EXACT BRAND MATCH: {len(exact_matches)} {preferred_brand} products found")
            return exact_matches
    
        # ============ ATTEMPT 2: Tier-equivalent substitutes ============
        self.log(f"     ⚠️ BRAND NOT FOUND: '{preferred_brand}' not in {req.category}")
    
        ecosystem_mgr = BrandEcosystemManager()
        substitute_brands = ecosystem_mgr.get_substitute_brands(req.category, preferred_brand)
    
        if substitute_brands:
            self.log(f"     🔄 Searching tier-equivalent substitutes: {', '.join(substitute_brands)}")
    
            for substitute in substitute_brands:
                sub_matches = df[df['brand'].str.lower() == substitute.lower()]
    
                if not sub_matches.empty:
                    self.log(f"     ✅ SUBSTITUTE FOUND: {substitute} ({len(sub_matches)} options)")
    
                    # Flag this for the validation report
                    self.validation_warnings.append({
                        'component': req.sub_category,
                        'issue': f"CLIENT REQUESTED: '{preferred_brand}' — NOT AVAILABLE. Substituting '{substitute}' (equivalent tier)",
                        'severity': 'HIGH'
                    })
    
                    return sub_matches
    
        # ============ ATTEMPT 3: Last resort - flag critical ============
        self.log(f"     ❌ CRITICAL: No {preferred_brand} found AND no tier equivalents available")
    
        self.validation_warnings.append({
            'component': req.sub_category,
            'issue': f"🚨 CLIENT REQUESTED BRAND NOT IN CATALOG: '{preferred_brand}' for {req.category}. No substitutes available. Using best available.",
            'severity': 'CRITICAL'
        })
    
        # Return best quality product as fallback
        if 'data_quality_score' in df.columns:
            best = df.nlargest(1, 'data_quality_score').iloc[0]
            fallback_brand = best.get('brand', 'Unknown')
            self.log(f"     ⚠️ FALLBACK: Using {fallback_brand} (highest quality score)")
            return df.nlargest(1, 'data_quality_score')
    
        return df.head(1)

    def _get_client_preference_for_category(self, category: str) -> str:
        """Helper to get preferred brand for category"""
        if category == 'Displays':
            return self.client_preferences.get('displays', 'No Preference')
        elif category == 'Video Conferencing':
            return self.client_preferences.get('video_conferencing', 'No Preference')
        elif category == 'Audio':
            return self.client_preferences.get('audio', 'No Preference')
        elif category in ['Control Systems', 'Signal Management', 'Lighting']:
            return self.client_preferences.get('control', 'No Preference')
        return 'No Preference'

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

    def _select_by_budget(self, df, req: ProductRequirement, existing_selections=None):
        """
        ENHANCED: Select product by budget but also consider ecosystem consistency
        """
        
        if df.empty:
            return None
        
        # Check if this brand has already been selected in same category
        existing_brand_for_category = None
        if existing_selections:
            for sel in existing_selections:
                if sel.get('category') == req.category:
                    existing_brand_for_category = sel.get('brand')
                    break
        
        # Prefer products from already-selected brands (ecosystem consistency)
        if existing_brand_for_category:
            brand_consistency = df[df['brand'].str.lower() == existing_brand_for_category.lower()]
            if not brand_consistency.empty:
                df = brand_consistency
                self.log(f"    ✅ ECOSYSTEM CONSISTENCY: Selecting from {existing_brand_for_category} to match previous selections")
        
        # Now apply budget tier selection
        df_sorted = df.sort_values('price')
        
        if self.budget_tier in ['Premium', 'Executive', 'Enterprise']:
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

    def validate_ecosystem_consistency(self, boq_items: List[Dict]) -> Dict[str, Any]:
        """
        NEW: Validate that selected brands form a coherent ecosystem
        """
        ecosystem_mgr = BrandEcosystemManager()
        
        # Extract selected brands by category
        selected_brands = {}
        vc_platform = None
        
        for item in boq_items:
            category = item.get('category', '')
            brand = item.get('brand', '')
            
            if category not in selected_brands:
                selected_brands[category] = brand
            
            # This logic assumes self.requirements exists, which might need to be set
            # during the BOQ generation process.
            if 'Video Conferencing' in category and hasattr(self, 'requirements') and hasattr(self.requirements, 'vc_platform'):
                vc_platform = self.requirements.vc_platform
        
        # Check ecosystem compatibility
        audio_brand = selected_brands.get('Audio', '')
        control_brand = selected_brands.get('Control Systems', '')
        compatible = True  # Default to true if not enough info
        
        if vc_platform and audio_brand and control_brand:
            compatible, score = ecosystem_mgr.is_ecosystem_compatible(
                vc_platform, audio_brand, control_brand
            )
            
            if not compatible:
                self.log(f"    ⚠️ WARNING: Ecosystem mismatch detected")
                self.log(f"        VC Platform: {vc_platform}")
                self.log(f"        Audio: {audio_brand} (score: {score})")
                self.log(f"        Control: {control_brand}")
        
        return {
            'selected_brands': selected_brands,
            'ecosystem_compatible': compatible
        }

    def _validate_cross_component_compatibility(self, boq_items: List[Dict]) -> List[str]:
        """
        ✅ NEW: Check compatibility between selected components in the final BOQ
        """
        warnings = []
        
        # Check 1: Codec and Camera Brand Matching
        codecs = [item for item in boq_items if 'Codec' in item.get('sub_category', '')]
        cameras = [item for item in boq_items if 'Camera' in item.get('sub_category', '')]
        
        if codecs and cameras:
            codec_brand = codecs[0].get('brand', '').lower()
            camera_brand = cameras[0].get('brand', '').lower()
            
            # Cisco codec should have Cisco camera
            if 'cisco' in codec_brand and 'cisco' not in camera_brand:
                warnings.append(
                    f"⚠️ Cisco codec typically pairs best with Cisco cameras. "
                    f"Selected: {cameras[0].get('brand')} camera"
                )
        
        # Check 2: DSP and Microphone Ecosystem
        dsps = [item for item in boq_items if 'DSP' in item.get('sub_category', '')]
        mics = [item for item in boq_items if 'Microphone' in item.get('sub_category', '')]
        
        if dsps and mics:
            dsp_brand = dsps[0].get('brand', '').lower()
            mic_brands = set(mic.get('brand', '').lower() for mic in mics)
            
            # QSC DSP works best with QSC mics
            if 'qsc' in dsp_brand and 'qsc' not in mic_brands:
                warnings.append(
                    f"💡 QSC DSP recommended with QSC microphones for optimal integration"
                )
        
        # Check 3: Control System and VC Platform
        controls = [item for item in boq_items if 'Control' in item.get('category', '')]
        
        if controls and hasattr(self, 'requirements'):
            vc_platform = self.requirements.vc_platform.lower()
            control_brand = controls[0].get('brand', '').lower()
            
            # Teams Rooms requires specific control brands
            if 'teams' in vc_platform and control_brand not in ['crestron', 'logitech', 'poly']:
                warnings.append(
                    f"⚠️ Microsoft Teams Rooms certification requires Crestron, Logitech, or Poly control. "
                    f"Selected: {controls[0].get('brand')}"
                )
        
        return warnings

    def log(self, message: str):
        """Add to selection log"""
        self.selection_log.append(message)
    
    def get_selection_report(self) -> str:
        """Get detailed selection report"""
        return "\n".join(self.selection_log)
    
    def get_validation_warnings(self) -> List[Dict]:
        """Get all validation warnings"""
        return self.validation_warnings
