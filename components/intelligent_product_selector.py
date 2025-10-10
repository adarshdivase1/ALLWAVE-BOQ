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
    OPTIMIZED: Advanced product selection with vectorized validation for speed.
    """
    
    def __init__(self, product_df, client_preferences=None, budget_tier='Standard'):
        self.product_df = product_df.copy()
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
        if 'price' not in self.product_df.columns:
            if 'price_usd' in self.product_df.columns: self.product_df.rename(columns={'price_usd': 'price'}, inplace=True)
            elif 'price_inr' in self.product_df.columns: self.product_df.rename(columns={'price_inr': 'price'}, inplace=True)
    
    def _normalize_dataframe_categories(self):
        """Ensure consistent category naming"""
        if 'primary_category' in self.product_df.columns and 'category' not in self.product_df.columns:
            self.product_df.rename(columns={'primary_category': 'category'}, inplace=True)
    
    def _build_category_validators(self):
        """
        Build strict validation rules for each category.
        This prevents products from wrong categories being selected.
        """
        self.category_validators = {
            'Displays': {'must_contain': ['display', 'monitor', 'screen', 'panel'], 'must_not_contain': ['mount', 'bracket', 'stand'], 'price_range': (200, 30000)},
            'Mounts': {'must_contain': ['mount', 'bracket', 'stand', 'cart'], 'must_not_contain': ['display', 'monitor', 'camera'], 'price_range': (50, 3000)},
            'Video Conferencing': {'must_contain': ['video', 'camera', 'codec', 'conference', 'bar', 'touch', 'controller'], 'must_not_contain': ['audio only'], 'price_range': (300, 20000),
                'sub_category_validators': {
                    'Touch Controller / Panel': {'must_contain': ['touch', 'controller', 'panel'], 'must_not_contain': ['receiver', 'transmitter', 'extender', 'scaler', 'switcher', 'room kit', 'codec'], 'override_category_validation': True}
                }},
            'Audio': {'must_contain': ['audio', 'speaker', 'microphone', 'mic', 'amplifier', 'dsp'], 'must_not_contain': ['video', 'display'], 'price_range': (50, 10000)},
            'Control Systems': {'must_contain': ['control', 'controller', 'processor', 'panel'], 'must_not_contain': [], 'price_range': (100, 15000)},
            'Signal Management': {'must_contain': ['switcher', 'matrix', 'scaler', 'extender'], 'must_not_contain': ['mount'], 'price_range': (100, 20000)},
            'Infrastructure': {'must_contain': ['rack', 'cabinet', 'enclosure', 'pdu', 'power'], 'must_not_contain': ['display', 'camera'], 'price_range': (50, 5000),
                'sub_category_validators': {
                    'AV Rack': {'must_contain': ['rack', 'cabinet', 'enclosure'], 'must_not_contain': ['mount', 'bracket', 'shelf only']}
                }},
            'Cables & Connectivity': {'must_contain': ['cable', 'connectivity', 'plate', 'hdmi'], 'must_not_contain': [], 'price_range': (5, 500)}
        }

    def select_product(self, requirement: ProductRequirement) -> Optional[Dict]:
        """
        OPTIMIZED: Multi-stage product selection with vectorized validation.
        """
        self.log(f"\n{'='*60}\n🎯 Selecting product for: {requirement.sub_category} ({requirement.category})")
        
        # STAGE 1: Category & Price Filter
        candidates = self._filter_by_category(requirement)
        if candidates.empty:
            self.log(f"❌ No products found in category: {requirement.category}/{requirement.sub_category}")
            return None
        
        # STAGE 2: Keyword & Spec Filters
        candidates = self._apply_keyword_filters(candidates, requirement)
        candidates = self._match_specifications(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ No products passed keyword/spec filters")
            return None
        
        # STAGE 3: Strict Validation (VECTORIZED FOR SPEED)
        candidates = self._apply_strict_validation(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ No products passed strict validation for {requirement.category}")
            return None
        
        # STAGE 4: Preference & Ecosystem Weighting
        candidates = self._apply_client_preferences(candidates, requirement)
        candidates = self._check_brand_ecosystem(candidates, self.existing_selections)
        
        # STAGE 5: Budget-Aware Selection
        selected = self._select_by_budget(candidates, requirement)
        
        if selected is not None:
            self.log(f"✅ SELECTED: {selected['brand']} {selected['model_number']} | Price: ${selected.get('price', 0):.2f}")
        
        return selected

    def _apply_strict_validation(self, df: pd.DataFrame, req: ProductRequirement) -> pd.DataFrame:
        """
        OPTIMIZED VECTORIZED VERSION: Apply strict category validation to all candidates at once.
        """
        if df.empty:
            return df

        self.log(f"    Stage 3 - Applying strict validation to {len(df)} candidates...")
        
        product_name_lower = df['name'].str.lower().fillna('')
        
        # Start with a mask of all True
        mask = pd.Series(True, index=df.index)

        validators = self.category_validators.get(req.category, {})
        sub_validators = validators.get('sub_category_validators', {}).get(req.sub_category, {})
        skip_parent_validation = sub_validators.get('override_category_validation', False)

        # 1. Category match
        if req.strict_category_match:
            mask &= (df['category'] == req.category)

        # 2. Parent category keywords (if not overridden)
        if not skip_parent_validation:
            must_contain = validators.get('must_contain', [])
            if must_contain:
                pattern = '|'.join(map(re.escape, must_contain))
                mask &= product_name_lower.str.contains(pattern, na=False)
        
        # 3. Parent must_not_contain keywords
        must_not_contain = validators.get('must_not_contain', [])
        if must_not_contain:
            pattern = '|'.join(map(re.escape, must_not_contain))
            mask &= ~product_name_lower.str.contains(pattern, na=False)

        # 4. Sub-category specific validators
        if sub_validators:
            sub_must_contain = sub_validators.get('must_contain', [])
            if sub_must_contain:
                pattern = '|'.join(map(re.escape, sub_must_contain))
                mask &= product_name_lower.str.contains(pattern, na=False)
            
            sub_must_not_contain = sub_validators.get('must_not_contain', [])
            if sub_must_not_contain:
                pattern = '|'.join(map(re.escape, sub_must_not_contain))
                mask &= ~product_name_lower.str.contains(pattern, na=False)
        
        # 5. Price range
        price_range = validators.get('price_range')
        if price_range:
            min_price, max_price = price_range
            mask &= (df['price'] >= min_price) & (df['price'] <= max_price)

        validated_df = df[mask]
        
        rejected_count = len(df) - len(validated_df)
        if rejected_count > 0:
            self.log(f"    - Validation rejected {rejected_count} products.")
        
        self.log(f"    - {len(validated_df)} products passed strict validation.")
        return validated_df
    
    def _filter_by_category(self, req: ProductRequirement) -> pd.DataFrame:
        """Stage 1: Filter by category and price range"""
        df = self.product_df[self.product_df['category'] == req.category]
        if req.sub_category:
            df = df[df['sub_category'] == req.sub_category]
        
        if req.min_price: df = df[df['price'] >= req.min_price]
        if req.max_price: df = df[df['price'] <= req.max_price]
        
        self.log(f"    Stage 1 - Category filter: {len(df)} products")
        return df
    
    def _apply_keyword_filters(self, df: pd.DataFrame, req: ProductRequirement) -> pd.DataFrame:
        """Stage 2a: Apply required and blacklist keywords"""
        if df.empty: return df
        
        name_lower = df['name'].str.lower().fillna('')
        
        if req.required_keywords:
            pattern = '|'.join([re.escape(kw) for kw in req.required_keywords])
            df = df[name_lower.str.contains(pattern, na=False)]
        
        if req.blacklist_keywords:
            pattern = '|'.join([re.escape(kw) for kw in req.blacklist_keywords])
            df = df[~name_lower.str.contains(pattern, na=False)]
            
        return df

    def _match_specifications(self, df: pd.DataFrame, req: ProductRequirement) -> pd.DataFrame:
        """Stage 2b: Match technical specifications"""
        if df.empty: return df
        
        if req.size_requirement:
            size_range = range(int(req.size_requirement) - 3, int(req.size_requirement) + 4)
            size_pattern = '|'.join([f'{s}"' for s in size_range])
            size_matches = df[df['name'].str.contains(size_pattern, na=False)]
            if not size_matches.empty:
                return size_matches
        
        return df
    
    def _apply_client_preferences(self, df: pd.DataFrame, req: ProductRequirement) -> pd.DataFrame:
        """Stage 4a: Weight products by client preferences"""
        if df.empty: return df

        category_map = {
            'Displays': 'displays', 'Video Conferencing': 'video_conferencing', 'Audio': 'audio',
            'Control Systems': 'control', 'Signal Management': 'control'
        }
        pref_key = category_map.get(req.category)
        preferred_brand = self.client_preferences.get(pref_key) if pref_key else None
        
        if preferred_brand:
            preferred_matches = df[df['brand'].str.lower() == preferred_brand.lower()]
            if not preferred_matches.empty:
                self.log(f"    - Found {len(preferred_matches)} preferred brand products: {preferred_brand}")
                return preferred_matches
        
        return df

    def _check_brand_ecosystem(self, df: pd.DataFrame, existing_selections: List[Dict]) -> pd.DataFrame:
        """Stage 4b: Ensure brand ecosystem compatibility"""
        if df.empty: return df
        
        vc_brand = None
        for item in existing_selections:
            if item.get('category') == 'Video Conferencing':
                vc_brand = item.get('brand', '').lower()
                break
        
        if vc_brand and not df.empty and 'Audio' in df['category'].unique():
            brand_matches = df[df['brand'].str.lower() == vc_brand]
            if not brand_matches.empty:
                self.log(f"    - Prioritizing {vc_brand.capitalize()} accessories for ecosystem compatibility.")
                return brand_matches
                
        return df
    
    def _select_by_budget(self, df: pd.DataFrame, req: ProductRequirement) -> Optional[Dict]:
        """Stage 5: Select based on budget tier"""
        if df.empty: return None
        
        df_sorted = df.sort_values('price').reset_index(drop=True)
        
        if self.budget_tier in ['Premium', 'Executive']:
            idx = int(len(df_sorted) * 0.8) # Top 20%
        elif self.budget_tier == 'Economy':
            idx = int(len(df_sorted) * 0.2) # Bottom 20%
        else: # Standard
            idx = len(df_sorted) // 2 # Middle
        
        # Ensure index is within bounds
        idx = min(idx, len(df_sorted) - 1)
        
        return df_sorted.iloc[idx].to_dict()

    def log(self, message: str):
        """Add to selection log"""
        self.selection_log.append(message)
    
    def get_selection_report(self) -> str:
        """Get detailed selection report"""
        return "\n".join(self.selection_log)

    def get_validation_warnings(self) -> List[Dict]:
        """Get all validation warnings"""
        return self.validation_warnings
