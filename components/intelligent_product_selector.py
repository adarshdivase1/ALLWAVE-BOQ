# NEW FILE: components/intelligent_product_selector.py

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import streamlit as st

@dataclass
class ProductRequirement:
    """Structured requirement for a component"""
    category: str
    sub_category: str
    quantity: int
    priority: int
    justification: str
    
    # NEW: Detailed specifications
    size_requirement: Optional[float] = None
    power_requirement: Optional[int] = None
    connectivity_type: Optional[str] = None
    mounting_type: Optional[str] = None
    compatibility_requirements: List[str] = None
    
    # NEW: Must-have keywords (product MUST contain these)
    required_keywords: List[str] = None
    # NEW: Blacklist keywords (product MUST NOT contain these)
    blacklist_keywords: List[str] = None
    
    # NEW: Client preference weight (0-1, higher = more important)
    client_preference_weight: float = 0.5


class IntelligentProductSelector:
    """
    Advanced product selection with multi-stage filtering and validation
    """
    
    def __init__(self, product_df, client_preferences=None, budget_tier='Standard'):
        self.product_df = product_df
        self.client_preferences = client_preferences or {}
        self.budget_tier = budget_tier
        self.selection_log = []  # For debugging/reporting
    
    def select_product(self, requirement: ProductRequirement) -> Optional[Dict]:
        """
        Multi-stage product selection with validation
        """
        self.log(f"Selecting product for: {requirement.sub_category}")
        
        # STAGE 1: Category Filter
        candidates = self._filter_by_category(requirement)
        if candidates.empty:
            self.log(f"❌ No products found in category: {requirement.category}/{requirement.sub_category}")
            return None
        
        # STAGE 2: Service Contract Filter (CRITICAL)
        candidates = self._filter_service_contracts(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ All products were service contracts")
            return None
        
        # STAGE 3: Keyword Filters
        candidates = self._apply_keyword_filters(candidates, requirement)
        if candidates.empty:
            self.log(f"❌ No products passed keyword filters")
            return None
        
        # STAGE 4: Specification Matching
        candidates = self._match_specifications(candidates, requirement)
        if candidates.empty:
            self.log(f"⚠️ No products matched specifications, using broader search")
            # Retry without strict spec matching
            candidates = self._filter_by_category(requirement)
            candidates = self._filter_service_contracts(candidates, requirement)
            candidates = self._apply_keyword_filters(candidates, requirement)
        
        # STAGE 5: Client Preference Weighting
        candidates = self._apply_client_preferences(candidates, requirement)
        
        # STAGE 6: Budget-Aware Selection
        selected = self._select_by_budget(candidates, requirement)
        
        if selected is not None:
            self.log(f"✅ Selected: {selected['brand']} {selected['model_number']} - ${selected['price']:.2f}")
            # STAGE 7: Compatibility Validation
            if not self._validate_compatibility(selected, requirement):
                self.log(f"⚠️ Product may have compatibility issues")
        
        return selected
    
    def _filter_by_category(self, req: ProductRequirement):
        """Stage 1: Filter by category"""
        if req.sub_category:
            return self.product_df[
                (self.product_df['category'] == req.category) &
                (self.product_df['sub_category'] == req.sub_category)
            ].copy()
        return self.product_df[self.product_df['category'] == req.category].copy()
    
    def _filter_service_contracts(self, df, req: ProductRequirement):
        """Stage 2: AGGRESSIVE service contract filter"""
        if req.category == 'Software & Services':
            return df  # Keep service contracts for this category
        
        # Comprehensive service contract patterns
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
        
        # Additional heuristic: if "warranty" or "service" in name AND price < $100
        df = df[~((df['name'].str.contains(r'\b(warranty|service|support)\b', case=False, regex=True)) & 
                  (df['price'] < 100))]
        
        return df
    
    def _apply_keyword_filters(self, df, req: ProductRequirement):
        """Stage 3: Apply required and blacklist keywords"""
        
        # Required keywords (product MUST contain at least one)
        if req.required_keywords:
            pattern = '|'.join([re.escape(kw) for kw in req.required_keywords])
            df = df[df['name'].str.contains(pattern, case=False, na=False, regex=True)]
        
        # Blacklist keywords (product MUST NOT contain any)
        if req.blacklist_keywords:
            for keyword in req.blacklist_keywords:
                df = df[~df['name'].str.contains(re.escape(keyword), case=False, na=False, regex=True)]
        
        return df
    
    def _match_specifications(self, df, req: ProductRequirement):
        """Stage 4: Match technical specifications"""
        
        # Display size matching
        if req.size_requirement:
            size_range = range(int(req.size_requirement) - 3, int(req.size_requirement) + 4)
            size_pattern = '|'.join([f'{s}"' for s in size_range])
            size_matches = df[df['name'].str.contains(size_pattern, na=False, regex=True)]
            if not size_matches.empty:
                df = size_matches
        
        # Mounting type matching
        if req.mounting_type:
            if 'wall' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\bwall\b', case=False, na=False, regex=True)]
            elif 'ceiling' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\bceiling\b', case=False, na=False, regex=True)]
            elif 'floor' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\b(floor|stand|cart|mobile)\b', case=False, na=False, regex=True)]
        
        # Connectivity type matching
        if req.connectivity_type:
            df = df[df['name'].str.contains(re.escape(req.connectivity_type), case=False, na=False, regex=True)]
        
        return df
    
    def _apply_client_preferences(self, df, req: ProductRequirement):
        """Stage 5: Weight products by client preferences"""
        
        preferred_brand = None
        
        # Map requirement category to preference category
        if req.category == 'Displays':
            preferred_brand = self.client_preferences.get('displays')
        elif req.category == 'Video Conferencing':
            preferred_brand = self.client_preferences.get('video_conferencing')
        elif req.category == 'Audio':
            preferred_brand = self.client_preferences.get('audio')
        elif req.category in ['Control Systems', 'Signal Management']:
            preferred_brand = self.client_preferences.get('control')
        
        if preferred_brand:
            # Add a 'preference_score' column
            df['preference_score'] = df['brand'].str.lower().apply(
                lambda x: req.client_preference_weight if x == preferred_brand.lower() else 0
            )
            
            # Sort by preference score (higher is better)
            df = df.sort_values('preference_score', ascending=False)
            
            # If we have preferred brand matches, prioritize them heavily
            preferred_matches = df[df['preference_score'] > 0]
            if not preferred_matches.empty:
                self.log(f"✅ Found {len(preferred_matches)} products from preferred brand: {preferred_brand}")
                return preferred_matches
        
        return df
    
    def _select_by_budget(self, df, req: ProductRequirement):
        """Stage 6: Select based on budget tier"""
        
        if df.empty:
            return None
        
        # Sort by price
        df_sorted = df.sort_values('price')
        
        # Budget tier selection logic
        if self.budget_tier in ['Premium', 'Executive']:
            # Top 25% (most expensive)
            start_idx = int(len(df_sorted) * 0.75)
            selection_pool = df_sorted.iloc[start_idx:]
        elif self.budget_tier == 'Economy':
            # Bottom 40% (least expensive)
            end_idx = int(len(df_sorted) * 0.4)
            selection_pool = df_sorted.iloc[:end_idx] if end_idx > 0 else df_sorted
        else:  # Standard
            # Middle 50%
            start_idx = int(len(df_sorted) * 0.25)
            end_idx = int(len(df_sorted) * 0.75)
            selection_pool = df_sorted.iloc[start_idx:end_idx] if end_idx > start_idx else df_sorted
        
        if selection_pool.empty:
            selection_pool = df_sorted
        
        # Select middle product from pool (most representative)
        selected_idx = len(selection_pool) // 2
        return selection_pool.iloc[selected_idx].to_dict()
    
    def _validate_compatibility(self, product: Dict, req: ProductRequirement) -> bool:
        """Stage 7: Validate product compatibility"""
        
        if not req.compatibility_requirements:
            return True
        
        product_name = product.get('name', '').lower()
        product_specs = product.get('specifications', '').lower()
        combined_text = f"{product_name} {product_specs}"
        
        # Check if product mentions any required compatibility
        for compat in req.compatibility_requirements:
            if compat.lower() not in combined_text:
                self.log(f"⚠️ Missing compatibility requirement: {compat}")
                return False
        
        return True
    
    def log(self, message: str):
        """Add to selection log"""
        self.selection_log.append(message)
    
    def get_selection_report(self) -> str:
        """Get detailed selection report for debugging"""
        return "\n".join(self.selection_log)
