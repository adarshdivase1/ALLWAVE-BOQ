# NEW FILE: components/nlp_requirements_parser.py

import re
from typing import Dict, List, Tuple
import streamlit as st

class NLPRequirementsParser:
    """
    Parse natural language client requirements using pattern matching and NLP
    """
    
    def __init__(self):
        # Brand recognition patterns
        self.brand_patterns = {
            'displays': {
                'samsung': r'\b(samsung|qb|qm|uh|fw-)\b',
                'lg': r'\b(lg|uh5|ur|ut)\b',
                'sony': r'\b(sony|bravia|fw-)\b',
                'nec': r'\b(nec|multisync)\b',
                'sharp': r'\b(sharp|aquos)\b'
            },
            'video_conferencing': {
                'poly': r'\b(poly|polycom|studio|x30|x50|x70|rally)\b',
                'cisco': r'\b(cisco|webex|room kit|codec)\b',
                'logitech': r'\b(logitech|rally|meetup|tap)\b',
                'yealink': r'\b(yealink|mvc|a\d{2})\b',
                'crestron': r'\b(crestron|flex|mercury)\b',
                'neat': r'\b(neat|neat bar|neat board)\b',
                'zoom': r'\b(zoom rooms)\b'
            },
            'audio': {
                'shure': r'\b(shure|mxa|microflex)\b',
                'biamp': r'\b(biamp|tesira|parlé)\b',
                'qsc': r'\b(qsc|q-sys|core)\b',
                'sennheiser': r'\b(sennheiser|teamconnect)\b',
                'bose': r'\b(bose|edgew|frees)\b'
            },
            'control': {
                'crestron': r'\b(crestron|cp4|cp3|tsw|tst)\b',
                'extron': r'\b(extron|ipcp|tlp)\b',
                'amx': r'\b(amx|netlinx|modero)\b'
            }
        }
        
        # Feature patterns
        self.feature_patterns = {
            'display_features': {
                'dual_display': r'\b(dual|two|2)\s*(display|screen|monitor)',
                'large_format': r'\b(large|big|85|90|95|98)["\']?\s*(display|screen)',
                'touch_enabled': r'\b(touch|interactive)\s*(display|screen)',
                '4k': r'\b(4k|uhd|ultra\s*hd)\b',
                '8k': r'\b(8k)\b'
            },
            'audio_features': {
                'ceiling_audio': r'\b(ceiling|overhead)\s*(mic|speaker|audio)',
                'voice_reinforcement': r'\b(voice\s*reinforcement|voice\s*lift|presenter\s*mic)',
                'wireless_mic': r'\b(wireless|cordless)\s*mic',
                'dsp': r'\b(dsp|digital\s*signal\s*processor)\b'
            },
            'video_features': {
                'ptz': r'\b(ptz|pan\s*tilt\s*zoom)\b',
                'auto_tracking': r'\b(auto\s*track|smart\s*track|speaker\s*track)',
                'dual_camera': r'\b(dual|two|2)\s*camera',
                '4k_camera': r'\b4k\s*camera\b'
            },
            'connectivity_features': {
                'wireless_presentation': r'\b(wireless\s*present|byod|airplay|miracast)',
                'usbc': r'\b(usb\s*c|usb-c)\b',
                'hdmi': r'\b(hdmi)\b',
                'cable_management': r'\b(cable\s*manag|cable\s*tidy|neat\s*cable)'
            },
            'control_features': {
                'automation': r'\b(automat|smart|intelligent)\s*control',
                'scheduling': r'\b(schedul|booking|calendar)\s*integrat',
                'mobile_control': r'\b(mobile|app|phone)\s*control'
            }
        }
        
        # Quantitative patterns
        self.quantity_patterns = {
            'participants': r'\b(\d+)\s*(person|people|seat|participant)',
            'displays': r'\b(\d+)\s*(display|screen|monitor)',
            'cameras': r'\b(\d+)\s*(camera|cam)',
            'microphones': r'\b(\d+)\s*(mic|microphone)'
        }
        
        # Budget patterns
        self.budget_patterns = {
            'economy': r'\b(budget|economy|cost\s*effect|afford|cheap|low\s*cost)\b',
            'standard': r'\b(standard|normal|typical|average)\b',
            'premium': r'\b(premium|high\s*end|luxury|top|best|flagship)\b',
            'executive': r'\b(executive|boardroom|c-suite|vip)\b'
        }
        
        # Compliance patterns
        self.compliance_patterns = {
            'ada': r'\b(ada|accessibility|hearing\s*loop|assistive)\b',
            'iso': r'\b(iso\s*\d+|quality\s*standard)\b',
            'leed': r'\b(leed|green\s*build|sustainab)\b'
        }
    
    def parse(self, requirements_text: str) -> Dict:
        """
        Main parsing function - extracts ALL information from requirements text
        """
        if not requirements_text:
            return {}
        
        text_lower = requirements_text.lower()
        
        parsed = {
            'raw_text': requirements_text,
            'client_preferences': self._extract_brand_preferences(text_lower),
            'features': self._extract_features(text_lower),
            'quantities': self._extract_quantities(text_lower),
            'budget_tier': self._detect_budget_tier(text_lower),
            'compliance': self._extract_compliance(text_lower),
            'special_requirements': self._extract_special_requirements(text_lower),
            'confidence_score': 0.0
        }
        
        # Calculate confidence score
        parsed['confidence_score'] = self._calculate_confidence(parsed)
        
        return parsed
    
    def _extract_brand_preferences(self, text: str) -> Dict[str, str]:
        """Extract brand preferences from text"""
        preferences = {}
        
        for category, brands in self.brand_patterns.items():
            for brand, pattern in brands.items():
                if re.search(pattern, text, re.IGNORECASE):
                    preferences[category] = brand.capitalize()
                    break  # Take first match
        
        return preferences
    
    def _extract_features(self, text: str) -> Dict[str, List[str]]:
        """Extract feature requirements"""
        features = {}
        
        for category, patterns in self.feature_patterns.items():
            detected = []
            for feature, pattern in patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    detected.append(feature)
            if detected:
                features[category] = detected
        
        return features
    
    def _extract_quantities(self, text: str) -> Dict[str, int]:
        """Extract quantity specifications"""
        quantities = {}
        
        for item, pattern in self.quantity_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                quantities[item] = int(match.group(1))
        
        return quantities
    
    def _detect_budget_tier(self, text: str) -> str:
        """Detect budget tier from text"""
        for tier, pattern in self.budget_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return tier.capitalize()
        return 'Standard'  # Default
    
    def _extract_compliance(self, text: str) -> List[str]:
        """Extract compliance requirements"""
        compliance = []
        for standard, pattern in self.compliance_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                compliance.append(standard.upper())
        return compliance
    
    # Continuing from where the document was cut off in nlp_requirements_parser.py

    def _extract_special_requirements(self, text: str) -> List[str]:
        """Extract special/unique requirements"""
        special = []
        
        # Recording/streaming
        if re.search(r'\b(record|streaming|capture|lecture\s*capture)\b', text, re.IGNORECASE):
            special.append('Recording/Streaming Required')
        
        # Lighting control
        if re.search(r'\b(lighting|light\s*control|dimmer)\b', text, re.IGNORECASE):
            special.append('Lighting Control Integration')
        
        # Digital signage
        if re.search(r'\b(digital\s*signage|wayfinding|menu\s*board)\b', text, re.IGNORECASE):
            special.append('Digital Signage Required')
        
        # Interpretation
        if re.search(r'\b(interpretation|translation|multi.*language)\b', text, re.IGNORECASE):
            special.append('Language Interpretation System')
        
        # Voting/polling
        if re.search(r'\b(voting|polling|audience\s*response)\b', text, re.IGNORECASE):
            special.append('Audience Response System')
        
        # Video walls
        if re.search(r'\b(video\s*wall|multi.*display|display\s*array)\b', text, re.IGNORECASE):
            special.append('Video Wall Configuration')
        
        # Confidence monitoring
        if re.search(r'\b(confidence|preview|program.*monitor)\b', text, re.IGNORECASE):
            special.append('Confidence Monitoring')
        
        # Matrix switching
        if re.search(r'\b(matrix|multiple\s*sources|source\s*switch)\b', text, re.IGNORECASE):
            special.append('Matrix Switching Required')
        
        # Dante/AoIP
        if re.search(r'\b(dante|audio.*over.*ip|networked\s*audio)\b', text, re.IGNORECASE):
            special.append('Networked Audio (Dante/AoIP)')
        
        # Room combining
        if re.search(r'\b(divisible|partition|room\s*combin|wall\s*open)\b', text, re.IGNORECASE):
            special.append('Divisible Room Configuration')
        
        return special
    
    def _calculate_confidence(self, parsed: Dict) -> float:
        """Calculate confidence score for parsed requirements"""
        confidence = 0.0
        max_score = 100.0
        
        # Brand preferences found (+20 points)
        if parsed.get('client_preferences'):
            confidence += 20.0 * (len(parsed['client_preferences']) / 4)  # Max 4 categories
        
        # Features detected (+30 points)
        if parsed.get('features'):
            feature_count = sum(len(v) for v in parsed['features'].values())
            confidence += min(30.0, feature_count * 5)
        
        # Quantities specified (+20 points)
        if parsed.get('quantities'):
            confidence += min(20.0, len(parsed['quantities']) * 5)
        
        # Budget tier detected (+10 points)
        if parsed.get('budget_tier') and parsed['budget_tier'] != 'Standard':
            confidence += 10.0
        
        # Compliance requirements (+10 points)
        if parsed.get('compliance'):
            confidence += min(10.0, len(parsed['compliance']) * 5)
        
        # Special requirements (+10 points)
        if parsed.get('special_requirements'):
            confidence += min(10.0, len(parsed['special_requirements']) * 2)
        
        return min(confidence, max_score) / max_score  # Normalize to 0-1
    
    def generate_summary_report(self, parsed: Dict) -> str:
        """Generate human-readable summary of parsed requirements"""
        if not parsed:
            return "No requirements provided."
        
        report = ["=== PARSED REQUIREMENTS SUMMARY ===\n"]
        
        # Client Preferences
        if parsed.get('client_preferences'):
            report.append("🎯 CLIENT BRAND PREFERENCES:")
            for category, brand in parsed['client_preferences'].items():
                report.append(f"  • {category.replace('_', ' ').title()}: {brand}")
            report.append("")
        
        # Budget Tier
        report.append(f"💰 BUDGET TIER: {parsed.get('budget_tier', 'Standard')}\n")
        
        # Features
        if parsed.get('features'):
            report.append("✨ DETECTED FEATURES:")
            for category, features in parsed['features'].items():
                report.append(f"  {category.replace('_', ' ').title()}:")
                for feature in features:
                    report.append(f"    - {feature.replace('_', ' ').title()}")
            report.append("")
        
        # Quantities
        if parsed.get('quantities'):
            report.append("📊 SPECIFIED QUANTITIES:")
            for item, qty in parsed['quantities'].items():
                report.append(f"  • {item.title()}: {qty}")
            report.append("")
        
        # Compliance
        if parsed.get('compliance'):
            report.append("📋 COMPLIANCE REQUIREMENTS:")
            for standard in parsed['compliance']:
                report.append(f"  • {standard}")
            report.append("")
        
        # Special Requirements
        if parsed.get('special_requirements'):
            report.append("⚡ SPECIAL REQUIREMENTS:")
            for req in parsed['special_requirements']:
                report.append(f"  • {req}")
            report.append("")
        
        # Confidence Score
        confidence_pct = parsed.get('confidence_score', 0) * 100
        report.append(f"🎯 PARSING CONFIDENCE: {confidence_pct:.1f}%")
        
        return "\n".join(report)


# ==================== INTEGRATION HELPER FUNCTIONS ====================

def extract_room_specific_requirements(requirements_text: str) -> Dict:
    """
    High-level function to extract room-specific requirements from text
    
    Returns a structured dict that can be used by the BOQ generator
    """
    parser = NLPRequirementsParser()
    parsed = parser.parse(requirements_text)
    
    # Convert parsed results to equipment requirements format
    equipment_overrides = {}
    
    # Display overrides
    if 'display_features' in parsed.get('features', {}):
        equipment_overrides['displays'] = {}
        
        if 'dual_display' in parsed['features']['display_features']:
            equipment_overrides['displays']['quantity'] = 2
        
        if 'large_format' in parsed['features']['display_features']:
            # Extract size if mentioned
            size_match = re.search(r'\b(85|90|95|98)["\']?\s*(display|screen)', 
                                  requirements_text, re.IGNORECASE)
            if size_match:
                equipment_overrides['displays']['size_inches'] = int(size_match.group(1))
        
        if 'touch_enabled' in parsed['features']['display_features']:
            equipment_overrides['displays']['type'] = 'Interactive Touch Display'
    
    # Audio overrides
    if 'audio_features' in parsed.get('features', {}):
        equipment_overrides['audio_system'] = {}
        
        if 'ceiling_audio' in parsed['features']['audio_features']:
            equipment_overrides['audio_system']['microphone_type'] = 'Ceiling Microphone'
            equipment_overrides['audio_system']['speaker_type'] = 'Ceiling Loudspeaker'
        
        if 'voice_reinforcement' in parsed['features']['audio_features']:
            equipment_overrides['audio_system']['type'] = 'Voice Reinforcement System'
            equipment_overrides['audio_system']['dsp_required'] = True
        
        if 'dsp' in parsed['features']['audio_features']:
            equipment_overrides['audio_system']['dsp_required'] = True
    
    # Video overrides
    if 'video_features' in parsed.get('features', {}):
        equipment_overrides['video_system'] = {}
        
        if 'ptz' in parsed['features']['video_features']:
            equipment_overrides['video_system']['camera_type'] = 'PTZ Camera'
        
        if 'dual_camera' in parsed['features']['video_features']:
            equipment_overrides['video_system']['camera_count'] = 2
        
        if 'auto_tracking' in parsed['features']['video_features']:
            equipment_overrides['video_system']['camera_type'] = 'PTZ with Auto-Tracking'
    
    # Connectivity overrides
    if 'connectivity_features' in parsed.get('features', {}):
        if 'wireless_presentation' in parsed['features']['connectivity_features']:
            equipment_overrides['content_sharing'] = {'type': 'Wireless Presentation System'}
    
    # Quantity overrides from detected quantities
    if 'quantities' in parsed:
        if 'displays' in parsed['quantities']:
            if 'displays' not in equipment_overrides:
                equipment_overrides['displays'] = {}
            equipment_overrides['displays']['quantity'] = parsed['quantities']['displays']
        
        if 'cameras' in parsed['quantities']:
            if 'video_system' not in equipment_overrides:
                equipment_overrides['video_system'] = {}
            equipment_overrides['video_system']['camera_count'] = parsed['quantities']['cameras']
        
        if 'microphones' in parsed['quantities']:
            if 'audio_system' not in equipment_overrides:
                equipment_overrides['audio_system'] = {}
            equipment_overrides['audio_system']['microphone_count'] = parsed['quantities']['microphones']
    
    return {
        'parsed_requirements': parsed,
        'equipment_overrides': equipment_overrides,
        'client_preferences': parsed.get('client_preferences', {}),
        'budget_tier': parsed.get('budget_tier', 'Standard'),
        'special_requirements': parsed.get('special_requirements', []),
        'compliance': parsed.get('compliance', [])
    }


def merge_equipment_requirements(base_requirements: Dict, nlp_overrides: Dict) -> Dict:
    """
    Merge NLP-extracted requirements with base room profile requirements
    
    Args:
        base_requirements: Equipment requirements from room profile
        nlp_overrides: Overrides extracted from NLP parsing
    
    Returns:
        Merged equipment requirements dict
    """
    import copy
    merged = copy.deepcopy(base_requirements)
    
    # Merge each equipment category
    for category, overrides in nlp_overrides.items():
        if category in merged:
            # Update existing category
            if isinstance(merged[category], dict) and isinstance(overrides, dict):
                merged[category].update(overrides)
            else:
                merged[category] = overrides
        else:
            # Add new category
            merged[category] = overrides
    
    return merged


# ==================== EXAMPLE USAGE ====================

def example_usage():
    """Example of how to use the NLP parser"""
    
    # Sample client requirements text
    sample_text = """
    We need a premium boardroom setup with dual 85" Samsung displays.
    The room should have Poly video conferencing with dual PTZ cameras.
    Audio should be Shure ceiling microphones with a Biamp DSP.
    We need wireless presentation capability and ADA compliance.
    The room will seat 12 people and requires recording capability.
    """
    
    # Parse requirements
    parser = NLPRequirementsParser()
    parsed = parser.parse(sample_text)
    
    # Generate summary report
    summary = parser.generate_summary_report(parsed)
    print(summary)
    
    # Extract structured requirements
    structured = extract_room_specific_requirements(sample_text)
    
    print("\n=== EQUIPMENT OVERRIDES ===")
    print(structured['equipment_overrides'])
    
    print("\n=== CLIENT PREFERENCES ===")
    print(structured['client_preferences'])


if __name__ == "__main__":
    example_usage()
