import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
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


class IntelligentProductSelector:
    """
    Advanced product selection with multi-stage filtering and validation
    Compatible with new dataset generation script categories
    """
    
    def __init__(self, product_df, client_preferences=None, budget_tier='Standard'):
        self.product_df = product_df
        self.client_preferences = client_preferences or {}
        self.budget_tier = budget_tier
        self.selection_log = []  # For debugging/reporting
        self.existing_selections = [] # For ecosystem checks
        
        # Normalize category names in the dataframe
        self._normalize_dataframe_categories()
    
    def _normalize_dataframe_categories(self):
        """Ensure consistent category naming"""
        if 'category' in self.product_df.columns:
            # Map any variations to standard names
            category_mapping = {
                'primary_category': 'category',
                'main_category': 'category'
            }
            for old_col, new_col in category_mapping.items():
                if old_col in self.product_df.columns and new_col not in self.product_df.columns:
                    self.product_df.rename(columns={old_col: new_col}, inplace=True)
        
        # If using 'primary_category' from dataset generation script
        if 'primary_category' in self.product_df.columns and 'category' not in self.product_df.columns:
            self.product_df['category'] = self.product_df['primary_category']
    
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

        # STAGE 5.5: Brand Ecosystem Check
        candidates = self._check_brand_ecosystem(candidates, requirement, self.existing_selections)
        
        # STAGE 6: Budget-Aware Selection
        selected = self._select_by_budget(candidates, requirement)
        
        if selected is not None:
            self.log(f"✅ Selected: {selected['brand']} {selected['model_number']} - ${selected['price_usd']:.2f}")
            # STAGE 7: Compatibility Validation
            if not self._validate_compatibility(selected, requirement):
                self.log(f"⚠️ Product may have compatibility issues")
        
        return selected
    
    def _filter_by_category(self, req: ProductRequirement):
        """Stage 1: Filter by category - ENHANCED for new dataset structure"""
        
        # Handle "General AV" category - try to match by sub_category keywords
        if req.category == 'General AV':
            # Search across all products using sub_category as keyword
            df = self.product_df[
                self.product_df['name'].str.contains(req.sub_category, case=False, na=False) |
                self.product_df['description'].str.contains(req.sub_category, case=False, na=False)
            ].copy()
        elif req.sub_category:
            # Standard category + sub_category filtering
            df = self.product_df[
                (self.product_df['category'] == req.category) &
                (self.product_df['sub_category'] == req.sub_category)
            ].copy()
        else:
            # Category only filtering
            df = self.product_df[self.product_df['category'] == req.category].copy()
        
        # ADD: Apply minimum price if specified
        if hasattr(req, 'min_price') and req.min_price:
            df = df[df['price_usd'] >= req.min_price]
            self.log(f"Applied minimum price filter (${req.min_price}): {len(df)} products")
        
        return df
    
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
                  (df['price_usd'] < 100))]
        
        return df
    
    def _apply_keyword_filters(self, df, req: ProductRequirement):
        """Stage 3: Apply required and blacklist keywords - ENHANCED"""
        
        # Required keywords (product MUST contain at least one)
        if req.required_keywords:
            pattern = '|'.join([re.escape(kw) for kw in req.required_keywords])
            df = df[df['name'].str.contains(pattern, case=False, na=False, regex=True)]
            
            self.log(f"After required keywords filter: {len(df)} products")
        
        # Blacklist keywords (product MUST NOT contain any)
        if req.blacklist_keywords:
            for keyword in req.blacklist_keywords:
                before_count = len(df)
                df = df[~df['name'].str.contains(re.escape(keyword), case=False, na=False, regex=True)]
                after_count = len(df)
                if before_count != after_count:
                    self.log(f"Blacklist '{keyword}' removed {before_count - after_count} products")
        
        # CRITICAL ADDITIONAL FILTERS BY CATEGORY
        if req.category == 'Mounts' and 'Display Mount' in req.sub_category:
            # MUST contain mount-specific terms
            df = df[df['name'].str.contains(
                r'(wall.*mount|ceiling.*mount|floor.*stand|display.*mount|tv.*mount|large.*format.*mount)',
                case=False, na=False, regex=True
            )]
            # MUST NOT contain touch panel terms
            df = df[~df['name'].str.contains(
                r'(tlp|tsw-|touch|panel|controller|ipad)',
                case=False, na=False, regex=True
            )]
            self.log(f"Display mount specific filter: {len(df)} products")
        
        elif req.category == 'Cables & Connectivity' and 'AV Cable' in req.sub_category:
            # MUST be network cables for modern systems
            df = df[df['name'].str.contains(
                r'(cat6|cat7|ethernet|network.*cable|patch.*cable)',
                case=False, na=False, regex=True
            )]
            # EXCLUDE obsolete cables
            df = df[~df['name'].str.contains(
                r'(vga|svideo|composite|component)',
                case=False, na=False, regex=True
            )]
            self.log(f"Network cable filter: {len(df)} products")
        
        elif req.category == 'Infrastructure' and 'Power' in req.sub_category:
            # EXCLUDE low-cost consumer PDUs
            df = df[df['price_usd'] > 100]
            # REQUIRE rackmount
            df = df[df['name'].str.contains(
                r'(rack.*mount|1u|2u|metered|switched)',
                case=False, na=False, regex=True
            )]
            self.log(f"Professional PDU filter: {len(df)} products")
        
        elif req.category == 'Audio' and req.sub_category == 'Amplifier':
            # MUST be power amplifier
            df = df[df['name'].str.contains(
                r'(power.*amp|multi.*channel|spa\d+|xpa\d+|\d+w)',
                case=False, na=False, regex=True
            )]
            # EXCLUDE conferencing amps
            df = df[~df['name'].str.contains(
                r'(conferenc|poe\+|dante.*amp|amp.*dante)',
                case=False, na=False, regex=True
            )]
            self.log(f"Power amplifier filter: {len(df)} products")
        
        # ADD: PTZ Camera specific filtering
        elif req.category == 'Video Conferencing' and 'PTZ Camera' in req.sub_category:
            # MUST have PTZ indicators
            df = df[df['name'].str.contains(
                r'(ptz|pan.*tilt.*zoom|eagleeye.*iv|eagleeye.*director|eptz)',
                case=False, na=False, regex=True
            )]
            
            # EXCLUDE USB webcams and consumer cameras
            df = df[~df['name'].str.contains(
                r'(webcam|usb.*camera|c920|c930|brio)',
                case=False, na=False, regex=True
            )]
            
            # MINIMUM PRICE for professional PTZ
            df = df[df['price_usd'] > 1000]  # Professional PTZ cameras cost $1000+
            
            self.log(f"Professional PTZ camera filter: {len(df)} products")
        
        # ADD: Handle Peripherals & Accessories category
        elif req.category == 'Peripherals & Accessories':
            if 'Input Devices' in req.sub_category:
                df = df[df['name'].str.contains(
                    r'(keyboard|mouse|trackpad|presenter|remote)',
                    case=False, na=False, regex=True
                )]
            elif 'Document Camera' in req.sub_category:
                df = df[df['name'].str.contains(
                    r'(document.*camera|visualizer|overhead.*camera)',
                    case=False, na=False, regex=True
                )]
            elif 'KVM' in req.sub_category or 'USB Hub' in req.sub_category:
                df = df[df['name'].str.contains(
                    r'(kvm|usb.*hub|docking.*station|port.*replicator)',
                    case=False, na=False, regex=True
                )]
        
        return df
    
    def _match_specifications(self, df, req: ProductRequirement):
        """Stage 4: Match technical specifications - ENHANCED"""
        
        # Display size matching
        if req.size_requirement:
            size_range = range(int(req.size_requirement) - 3, int(req.size_requirement) + 4)
            size_pattern = '|'.join([f'{s}"' for s in size_range])
            size_matches = df[df['name'].str.contains(size_pattern, na=False, regex=True)]
            if not size_matches.empty:
                df = size_matches
        
        # CRITICAL: Mounting type matching with SIZE consideration
        if req.mounting_type:
            if 'wall' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\bwall\b', case=False, na=False, regex=True)]
                
                # CRITICAL: For large displays (85"+), require large/heavy-duty mounts
                if req.size_requirement and req.size_requirement >= 85:
                    self.log(f"Large display ({req.size_requirement}\") - filtering for heavy-duty mounts")
                    
                    # Validate actual capacity
                    df = self._validate_mount_capacity(df, req)
                    
                    # EXCLUDE small/medium mounts by model number
                    df = df[~df['model_number'].str.contains(
                        r'(mtm\d|msm\d|xsm\d)',  # Medium/Small mount codes
                        case=False, na=False, regex=True
                    )]
                    
            elif 'ceiling' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\bceiling\b', case=False, na=False, regex=True)]
            elif 'floor' in req.mounting_type.lower():
                df = df[df['name'].str.contains(r'\b(floor|stand|cart|mobile)\b', case=False, na=False, regex=True)]
        
        # Connectivity type matching
        if req.connectivity_type:
            df = df[df['name'].str.contains(re.escape(req.connectivity_type), case=False, na=False, regex=True)]
        
        return df
        
    def _validate_mount_capacity(self, df, req: ProductRequirement):
        """Validate mount can actually support the display"""
        if not req.size_requirement or req.size_requirement < 85:
            return df  # Standard validation sufficient for smaller displays
        
        # For 85"+ displays, require explicit large format capability
        validated_mounts = []
        
        for idx, product in df.iterrows():
            name = product.get('name', '').lower()
            
            # Check both 'specifications' and 'full_specifications' columns
            specs = ''
            if 'specifications' in product:
                specs = str(product.get('specifications', '')).lower()
            elif 'full_specifications' in product:
                specs = str(product.get('full_specifications', '')).lower()
            
            combined = f"{name} {specs}"
            
            # Check for large format indicators
            has_large_support = any(term in combined for term in [
                '85"', '90"', '95"', '98"', '100"',
                'large format', 'video wall', 'commercial display',
                '150 lbs', '175 lbs', '200 lbs', '250 lbs',
                'vesa 800', 'vesa 1000'
            ])
            
            # Check for small mount exclusions
            is_small_mount = any(term in combined for term in [
                'up to 80"', 'max 70"', 'vesa 400 max',
                'medium', 'small', 'compact'
            ])
            
            if has_large_support and not is_small_mount:
                validated_mounts.append(product)
        
        if validated_mounts:
            self.log(f"✅ {len(validated_mounts)} mounts validated for {req.size_requirement}\" display")
            return pd.DataFrame(validated_mounts)
        else:
            self.log(f"⚠️ WARNING: No mounts found with validated capacity for {req.size_requirement}\" display")
            return df  # Return original if no validated mounts found
            
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

    def _check_brand_ecosystem(self, df, req: ProductRequirement, existing_selections):
        """
        Stage 5.5: Ensure brand ecosystem compatibility
        """
        # If video conferencing category, check what else has been selected
        if req.category in ['Audio', 'Video Conferencing']:
            # Find primary video system brand
            vc_brand = None
            for selected in existing_selections:
                if selected.get('category') == 'Video Conferencing':
                    if 'Video Bar' in selected.get('sub_category', '') or \
                       'Room Kit' in selected.get('sub_category', ''):
                        vc_brand = selected.get('brand', '').lower()
                        break
            
            if vc_brand:
                # Prioritize same brand for accessories
                if req.category == 'Audio' and any(term in req.sub_category for term in ['Microphone', 'Expansion']):
                    brand_matches = df[df['brand'].str.lower() == vc_brand]
                    if not brand_matches.empty:
                        self.log(f"✅ Prioritizing {vc_brand} accessories for ecosystem compatibility")
                        return brand_matches
        
        return df

    def _select_by_budget(self, df, req: ProductRequirement):
        """Stage 6: Select based on budget tier"""
        
        if df.empty:
            return None
        
        # Sort by price - handle both 'price' and 'price_usd' columns
        price_col = 'price_usd' if 'price_usd' in df.columns else 'price'
        df_sorted = df.sort_values(price_col)
        
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
        
        # Check both possible specification column names
        product_specs = ''
        if 'specifications' in product:
            product_specs = str(product.get('specifications', '')).lower()
        elif 'full_specifications' in product:
            product_specs = str(product.get('full_specifications', '')).lower()
        
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
