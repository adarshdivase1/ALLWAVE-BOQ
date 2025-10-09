# FILE: components/intelligent_product_selector.py

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
        # Pre-process names for faster string matching
        if 'name' in self.product_df.columns:
            self.product_df['name_lower'] = self.product_df['name'].str.lower().fillna('')
        else:
            self.product_df['name_lower'] = ''

        self.client_preferences = client_preferences or {}
        self.budget_tier = budget_tier
        self.selection_log = []
        self.existing_selections = []
        self.validation_warnings = []
        
        self._standardize_price_column()
        self._normalize_dataframe_categories()
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
        """Build strict validation rules for each category"""
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
                'must_contain': ['video', 'camera', 'codec', 'conference', 'conferencing', 'bar', 'room kit', 'ptz'],
                'must_not_contain': ['audio only', 'speaker only'],
                'price_range': (300, 20000),
                'sub_category_validators': {
                    # ✅ FIXED: Relaxed the must_contain rule. Model numbers (like TSW, TSS) are now sufficient.
                    'Touch Controller / Panel': {
                        'must_contain': ['touch', 'panel', 'controller', 'control', 'tsw-', 'tss-', 'tap', 'navigator'],
                        'must_not_contain': ['receiver', 'transmitter', 'extender', 'scaler', 'switcher', 'camera', 'codec', 'mount kit']
                    },
                    # ✅ ADDED: A new, specific validator for Scheduling Panels
                    'Scheduling Panel': {
                        'must_contain': ['schedul', 'booking', 'panel', 'tss-', 'tap'],
                        'must_not_contain': ['license', 'software', 'camera', 'codec', 'video bar']
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
                    # ✅ FIXED: Added 'shelf' to the blacklist to prevent selecting accessories.
                    'AV Rack': {
                        'must_contain': ['rack', 'cabinet', 'enclosure', 'frame'],
                        'must_not_contain': ['mount', 'bracket', 'shelf', 'camera', 'display']
                    }
                }
            },
            'Cables & Connectivity': {
                'must_contain': ['cable', 'connectivity', 'plate', 'module', 'hdmi', 'ethernet', 'cat'],
                'must_not_contain': [],
                'price_range': (5, 500)
            }
        }
    
    def _validate_product_category(self, product: pd.Series, req: ProductRequirement) -> Tuple[bool, List[str]]:
        """Strict validation that product actually belongs to the requested category"""
        issues = []
        product_name = product.get('name_lower', '')
        
        validators = self.category_validators.get(req.category, {})
        
        # This check is done at the DataFrame level now for speed.
        # This function can be used for final validation on the single selected item.
        if validators:
            must_contain = validators.get('must_contain', [])
            if must_contain and not any(keyword in product_name for keyword in must_contain):
                issues.append(f"Missing required keywords for {req.category}: {must_contain}")
                return False, issues

            must_not_contain = validators.get('must_not_contain', [])
            if must_not_contain and any(keyword in product_name for keyword in must_not_contain):
                forbidden_found = [kw for kw in must_not_contain if kw in product_name]
                issues.append(f"Contains forbidden keywords: {forbidden_found}")
                return False, issues
        
        return True, []
    
    def select_product(self, requirement: ProductRequirement) -> Optional[Dict]:
        """ENHANCED: Multi-stage product selection with strict validation"""
        self.log(f"\n{'='*60}")
        self.log(f"🎯 Selecting product for: {requirement.sub_category}")
        self.log(f"   Category: {requirement.category}")
        
        # STAGE 1 & 2: Initial Filters (Category & Service Contracts)
        candidates = self._filter_by_category(requirement)
        candidates = self._filter_service_contracts(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ No products found after initial filtering for: {requirement.category}/{requirement.sub_category}")
            return None
        
        # STAGE 3: Keyword Filters
        candidates = self._apply_keyword_filters(candidates, requirement)
        if candidates.empty: self.log(f"❌ No products passed keyword filters"); return None
        
        # STAGE 4: Specification Matching
        candidates = self._match_specifications(candidates, requirement)
        if candidates.empty: self.log(f"❌ No products matched specifications"); return None
        
        # STAGE 4.5: Strict Category Validation (Vectorized for Speed)
        candidates = self._apply_strict_validation(candidates, requirement)
        if candidates.empty: self.log(f"❌ No products passed strict validation for {requirement.category}"); return None
        
        # STAGE 5 & 5.5: Preference & Ecosystem Weighting
        candidates = self._apply_client_preferences(candidates, requirement)
        candidates = self._check_brand_ecosystem(candidates, requirement, self.existing_selections)
        
        # STAGE 6: Budget-Aware Selection
        selected = self._select_by_budget(candidates, requirement)
        
        if selected is not None:
            is_valid, validation_issues = self._validate_product_category(pd.Series(selected), requirement)
            if not is_valid:
                self.log(f"❌ FINAL VALIDATION FAILED: {validation_issues}")
                return None
            
            price = selected.get('price', 0)
            self.log(f"✅ SELECTED: {selected['brand']} {selected['model_number']} at ${price:.2f}")
            self.log(f"   Product: {selected['name'][:80]}")
        
        return selected
    
    # =========================================================================
    # OPTIMIZED VALIDATION FUNCTION
    # =========================================================================
    def _apply_strict_validation(self, df: pd.DataFrame, req: ProductRequirement) -> pd.DataFrame:
        """
        OPTIMIZED STAGE: Apply strict category validation using vectorized operations.
        """
        if df.empty: return df

        validators = self.category_validators.get(req.category, {})
        if not validators: return df
        
        initial_count = len(df)
        
        # Vectorized 'must_contain' check
        must_contain = validators.get('must_contain', [])
        if must_contain:
            pattern = '|'.join([re.escape(kw) for kw in must_contain])
            df = df[df['name_lower'].str.contains(pattern, regex=True)]
            if len(df) < initial_count:
                self.log(f"   Validation (must_contain): Filtered {initial_count - len(df)} products")
                initial_count = len(df)

        # Vectorized 'must_not_contain' check
        must_not_contain = validators.get('must_not_contain', [])
        if must_not_contain:
            pattern = '|'.join([re.escape(kw) for kw in must_not_contain])
            df = df[~df['name_lower'].str.contains(pattern, regex=True)]
            if len(df) < initial_count:
                self.log(f"   Validation (must_not_contain): Filtered {initial_count - len(df)} products")
                initial_count = len(df)
        
        # Sub-category validators (also vectorized)
        sub_validators = validators.get('sub_category_validators', {}).get(req.sub_category, {})
        if sub_validators:
            sub_must_contain = sub_validators.get('must_contain', [])
            if sub_must_contain:
                pattern = '|'.join([re.escape(kw) for kw in sub_must_contain])
                df = df[df['name_lower'].str.contains(pattern, regex=True)]
            
            sub_must_not_contain = sub_validators.get('must_not_contain', [])
            if sub_must_not_contain:
                pattern = '|'.join([re.escape(kw) for kw in sub_must_not_contain])
                df = df[~df['name_lower'].str.contains(pattern, regex=True)]

        # Vectorized price range check
        price_range = validators.get('price_range')
        if price_range:
            min_price, max_price = price_range
            df = df[(df['price'] >= min_price) & (df['price'] <= max_price)]
            if len(df) < initial_count:
                self.log(f"   Validation (price_range): Filtered {initial_count - len(df)} products")

        self.log(f"   Stage 4.5 - Strict validation: {len(df)} products remaining")
        return df

    def _filter_by_category(self, req: ProductRequirement):
        """Stage 1: Filter by category"""
        if req.sub_category:
            df = self.product_df[
                (self.product_df['category'] == req.category) &
                (self.product_df['sub_category'] == req.sub_category)
            ].copy()
        else:
            df = self.product_df[self.product_df['category'] == req.category].copy()
        
        if hasattr(req, 'min_price') and req.min_price: df = df[df['price'] >= req.min_price]
        if hasattr(req, 'max_price') and req.max_price: df = df[df['price'] <= req.max_price]
        
        self.log(f"   Stage 1 - Category filter: {len(df)} products")
        return df
    
    def _filter_service_contracts(self, df, req: ProductRequirement):
        """Stage 2: Filter out service contracts"""
        if req.category == 'Software & Services' or df.empty: return df
        
        service_patterns = r'\b(support|service|warranty|contract|care|pack|premier|agreement|plan|jumpstart|con-snt|con-ecdn)\b'
        df = df[~df['name_lower'].str.contains(service_patterns, regex=True)]
        
        self.log(f"   Stage 2 - Service filter: {len(df)} products")
        return df
    
    def _apply_keyword_filters(self, df, req: ProductRequirement):
        """Stage 3: Apply required and blacklist keywords"""
        if df.empty: return df
        if req.required_keywords:
            pattern = '|'.join([re.escape(kw) for kw in req.required_keywords])
            df = df[df['name_lower'].str.contains(pattern, regex=True)]
        
        if req.blacklist_keywords:
            pattern = '|'.join([re.escape(kw) for kw in req.blacklist_keywords])
            df = df[~df['name_lower'].str.contains(pattern, regex=True)]

        self.log(f"   Stage 3 - Keyword filter: {len(df)} products")
        return df
    
    def _match_specifications(self, df, req: ProductRequirement):
        """Stage 4: Match technical specifications"""
        if df.empty: return df
        if req.size_requirement:
            size_range = range(int(req.size_requirement) - 3, int(req.size_requirement) + 4)
            size_pattern = '|'.join([f'{s}"' for s in size_range])
            size_matches = df[df['name_lower'].str.contains(size_pattern, regex=True)]
            if not size_matches.empty:
                df = size_matches
        
        if req.mounting_type:
            df = df[df['name_lower'].str.contains(r'\b' + re.escape(req.mounting_type.lower()) + r'\b', regex=True)]
        
        self.log(f"   Stage 4 - Specification match: {len(df)} products")
        return df

    def _apply_client_preferences(self, df, req: ProductRequirement):
        """Stage 5: Weight products by client preferences"""
        if df.empty: return df
        
        preferred_brand_map = {
            'Displays': self.client_preferences.get('displays'),
            'Video Conferencing': self.client_preferences.get('video_conferencing'),
            'Audio': self.client_preferences.get('audio'),
            'Control Systems': self.client_preferences.get('control'),
            'Signal Management': self.client_preferences.get('control')
        }
        preferred_brand = preferred_brand_map.get(req.category)

        if preferred_brand:
            preferred_matches = df[df['brand'].str.lower() == preferred_brand.lower()]
            if not preferred_matches.empty:
                self.log(f"   ✅ Found {len(preferred_matches)} preferred brand products: {preferred_brand}")
                return preferred_matches
        return df
    
    def _check_brand_ecosystem(self, df, req: ProductRequirement, existing_selections):
        """Stage 5.5: Ensure brand ecosystem compatibility"""
        if df.empty: return df
        if req.category in ['Audio', 'Video Conferencing'] and any(term in req.sub_category for term in ['Microphone', 'Expansion', 'Touch Controller']):
            vc_brand = next((sel.get('brand', '').lower() for sel in existing_selections if sel.get('category') == 'Video Conferencing'), None)
            if vc_brand:
                brand_matches = df[df['brand'].str.lower() == vc_brand]
                if not brand_matches.empty:
                    self.log(f"   ✅ Prioritizing {vc_brand} accessories for ecosystem")
                    return brand_matches
        return df
    
    def _select_by_budget(self, df, req: ProductRequirement):
        """Stage 6: Select based on budget tier"""
        if df.empty: return None
        
        df_sorted = df.sort_values('price')
        
        if self.budget_tier in ['Premium', 'Executive']:
            idx = int(len(df_sorted) * 0.8) # Top 20%
        elif self.budget_tier == 'Economy':
            idx = int(len(df_sorted) * 0.2) # Bottom 20%
        else: # Standard
            idx = len(df_sorted) // 2 # Middle
        
        return df_sorted.iloc[idx].to_dict()

    def log(self, message: str):
        self.selection_log.append(message)
    
    def get_selection_report(self) -> str:
        return "\n".join(self.selection_log)
    
    def get_validation_warnings(self) -> List[Dict]:
        return self.validation_warnings
