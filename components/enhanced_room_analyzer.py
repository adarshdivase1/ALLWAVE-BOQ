# components/enhanced_room_analyzer.py
"""
HYBRID ROOM ANALYSIS SYSTEM
Combines predefined room profiles with AI-powered custom room analysis
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import re

@dataclass
class RoomCharacteristics:
    """Extracted characteristics from AI analysis"""
    room_type_category: str  # Training, Conference, Presentation, etc.
    capacity: int
    primary_functions: List[str]
    special_features: List[str]
    technical_complexity: str  # Simple, Standard, Complex, Advanced
    audio_requirements: Dict[str, Any]
    video_requirements: Dict[str, Any]
    control_requirements: Dict[str, Any]
    infrastructure_needs: List[str]
    budget_indication: str  # Economy, Standard, Premium, Custom
    avixa_considerations: List[str]


class EnhancedRoomAnalyzer:
    """
    Intelligent room analyzer that decides:
    1. Use predefined profile (if standard room)
    2. Use AI analysis (if custom/complex room)
    3. Hybrid approach (use profile as base, AI for customization)
    """
    
    def __init__(self, gemini_model, product_df):
        self.model = gemini_model
        self.product_df = product_df
        
        # Standard room types that have proven profiles
        self.STANDARD_ROOM_TYPES = [
            'Small Huddle Room (2-3 People)',
            'Medium Huddle Room (4-6 People)',
            'Standard Conference Room (6-8 People)',
            'Large Conference Room (8-12 People)',
            'Executive Boardroom (10-16 People)',
            'Training Room (15-25 People)',
            'Large Training/Presentation Room (25-40 People)',
            'Multipurpose Event Room (40+ People)',
            'Video Production Studio',
            'Telepresence Suite'
        ]
        
        # NEW: Extended room types (to be added to room_profiles.py)
        self.EXTENDED_ROOM_TYPES = [
            'Amphitheater / Lecture Hall',
            'Divisible Training Room',
            'Corporate Lobby with Digital Signage',
            'Control Room / NOC',
            'Worship Space',
            'Medical Simulation Lab',
            'Call Center Training',
            'Executive Briefing Center',
            'Virtual Production Studio',
            'Esports Arena',
            'Corporate TV Studio'
        ]
    
    def analyze_room_type(self, room_description: str, room_dimensions: Dict) -> Dict[str, Any]:
        """
        Main entry point: Determines if room is standard or custom
        Returns: analysis type and data
        """
        
        # Check if user selected a predefined room type
        if room_description in self.STANDARD_ROOM_TYPES:
            return {
                'analysis_type': 'PREDEFINED_PROFILE',
                'room_type': room_description,
                'confidence': 1.0,
                'use_optimized_generator': True
            }
        
        # Check if it's a simple variation of a standard room
        simple_mapping = self._map_to_standard_room(room_description)
        if simple_mapping and simple_mapping['confidence'] > 0.85:
            return {
                'analysis_type': 'MAPPED_TO_STANDARD',
                'room_type': simple_mapping['mapped_to'],
                'original_description': room_description,
                'confidence': simple_mapping['confidence'],
                'use_optimized_generator': True,
                'customizations': simple_mapping['customizations']
            }
        
        # Custom room - use AI analysis
        st.info("🤖 This is a custom room type. Using AI-powered analysis...")
        
        ai_analysis = self._ai_analyze_custom_room(room_description, room_dimensions)
        
        return {
            'analysis_type': 'AI_CUSTOM_ANALYSIS',
            'room_characteristics': ai_analysis,
            'confidence': ai_analysis.get('confidence', 0.0),
            'use_optimized_generator': False,  # Use AI-generated blueprint
            'fallback_profile': ai_analysis.get('closest_standard_profile')
        }
    
    def _map_to_standard_room(self, description: str) -> Optional[Dict]:
        """
        Quick rule-based mapping for simple variations
        e.g., "12 person boardroom" -> Executive Boardroom
        """
        desc_lower = description.lower()
        
        # Capacity-based mapping
        capacity_match = re.search(r'(\d+)[-\s]*(person|people|seat)', desc_lower)
        if capacity_match:
            capacity = int(capacity_match.group(1))
            
            if capacity <= 3:
                return {'mapped_to': 'Small Huddle Room (2-3 People)', 'confidence': 0.9, 'customizations': []}
            elif capacity <= 6:
                return {'mapped_to': 'Medium Huddle Room (4-6 People)', 'confidence': 0.9, 'customizations': []}
            elif capacity <= 8:
                return {'mapped_to': 'Standard Conference Room (6-8 People)', 'confidence': 0.9, 'customizations': []}
            elif capacity <= 12:
                return {'mapped_to': 'Large Conference Room (8-12 People)', 'confidence': 0.9, 'customizations': []}
            elif capacity <= 16:
                return {'mapped_to': 'Executive Boardroom (10-16 People)', 'confidence': 0.9, 'customizations': []}
            elif capacity <= 25:
                return {'mapped_to': 'Training Room (15-25 People)', 'confidence': 0.85, 'customizations': []}
            elif capacity <= 40:
                return {'mapped_to': 'Large Training/Presentation Room (25-40 People)', 'confidence': 0.85, 'customizations': []}
            else:
                return {'mapped_to': 'Multipurpose Event Room (40+ People)', 'confidence': 0.8, 'customizations': []}
        
        # Keyword-based mapping
        if any(word in desc_lower for word in ['huddle', 'small meeting', 'focus room']):
            return {'mapped_to': 'Medium Huddle Room (4-6 People)', 'confidence': 0.85, 'customizations': []}
        
        if any(word in desc_lower for word in ['boardroom', 'executive', 'c-suite']):
            return {'mapped_to': 'Executive Boardroom (10-16 People)', 'confidence': 0.9, 'customizations': []}
        
        if any(word in desc_lower for word in ['training', 'classroom', 'learning']):
            return {'mapped_to': 'Training Room (15-25 People)', 'confidence': 0.85, 'customizations': []}
        
        if any(word in desc_lower for word in ['telepresence', 'immersive', 'high-end video']):
            return {'mapped_to': 'Telepresence Suite', 'confidence': 0.9, 'customizations': []}
        
        return None
    
    def _ai_analyze_custom_room(self, description: str, room_dimensions: Dict) -> Dict:
        """
        Use Gemini AI to analyze custom room requirements
        """
        
        prompt = f"""
You are an expert AV system designer with deep knowledge of AVIXA standards.

Analyze this custom room requirement and extract structured information:

ROOM DESCRIPTION:
{description}

ROOM DIMENSIONS:
- Length: {room_dimensions.get('length', 'Not specified')} ft
- Width: {room_dimensions.get('width', 'Not specified')} ft
- Ceiling Height: {room_dimensions.get('ceiling_height', 'Not specified')} ft
- Area: {room_dimensions.get('area', 'Not specified')} sq ft

TASK:
Extract and structure the following information in JSON format:

1. room_type_category: Primary category (Conference, Training, Presentation, Production, Specialized)
2. capacity: Estimated number of people (if not specified, calculate from area at 25 sq ft per person)
3. primary_functions: List of main room functions (e.g., ["Video Conferencing", "Presentations", "Collaboration"])
4. special_features: List of unique requirements (e.g., ["Divisible space", "Recording capability", "Immersive display"])
5. technical_complexity: Rate as Simple, Standard, Complex, or Advanced
6. audio_requirements:
   - microphone_type: (Ceiling, Table, Wireless, Hybrid)
   - speaker_type: (Ceiling, Wall, Line Array, Integrated)
   - dsp_required: true/false
   - special_audio: List any special audio needs
7. video_requirements:
   - display_type: (Single Large, Dual, Video Wall, Projector, LED Wall)
   - camera_type: (Video Bar, PTZ, Multi-camera, Broadcast)
   - recording_streaming: true/false
8. control_requirements:
   - complexity: (Basic, Standard, Advanced, Custom)
   - automation_level: (Manual, Semi-automated, Fully-automated)
9. infrastructure_needs: List infrastructure requirements (e.g., ["High-bandwidth network", "Redundant power", "Acoustic treatment"])
10. budget_indication: Estimate budget tier (Economy, Standard, Premium, Custom/High-end)
11. avixa_considerations: List AVIXA standards that are critical for this room
12. closest_standard_profile: Which standard room type is this most similar to?
13. confidence: Your confidence in this analysis (0.0 to 1.0)

Return ONLY valid JSON, no other text.
"""
        
        try:
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = re.sub(r'```json\n?|```\n?', '', response_text)
            
            analysis = json.loads(response_text)
            
            return analysis
            
        except Exception as e:
            st.error(f"AI analysis failed: {e}")
            
            # Fallback to basic analysis
            return {
                'room_type_category': 'Specialized',
                'capacity': int(room_dimensions.get('area', 400) / 25),
                'primary_functions': ['General AV'],
                'special_features': [],
                'technical_complexity': 'Standard',
                'audio_requirements': {
                    'microphone_type': 'Table',
                    'speaker_type': 'Ceiling',
                    'dsp_required': True
                },
                'video_requirements': {
                    'display_type': 'Single Large',
                    'camera_type': 'Video Bar'
                },
                'control_requirements': {
                    'complexity': 'Standard'
                },
                'infrastructure_needs': ['Standard network', 'Standard power'],
                'budget_indication': 'Standard',
                'avixa_considerations': ['DISCAS', 'A102.01'],
                'closest_standard_profile': 'Standard Conference Room (6-8 People)',
                'confidence': 0.5
            }

    # --------------------------------------------------------------------
    # CHANGE 1.1 (DELETE)
    # The 'generate_custom_room_blueprint' function has been deleted.
    # --------------------------------------------------------------------


    # --------------------------------------------------------------------
    # CHANGE 1.1 (ADD)
    # New function to replace 'generate_custom_room_blueprint'.
    # This converts AI analysis into tags for the unified blueprint generator.
    # --------------------------------------------------------------------
    def extract_requirements_tags(self, room_characteristics: Dict, room_dimensions: Dict) -> Dict:
        """
        NEW METHOD: Convert AI analysis into structured tags for the blueprint generator.
        This REPLACES generate_custom_room_blueprint.
        """
        
        capacity = room_characteristics.get('capacity', 8)
        audio_req = room_characteristics.get('audio_requirements', {})
        video_req = room_characteristics.get('video_requirements', {})
        control_req = room_characteristics.get('control_requirements', {})
        
        tags = {
            'capacity': capacity,
            'room_type_category': room_characteristics.get('room_type_category', 'Conference'),
            
            # Display tags
            'display_quantity': 2 if video_req.get('display_type') == 'Dual' else 1,
            'display_type': video_req.get('display_type', 'Single Large'),
            'needs_video_wall': 'Video Wall' in video_req.get('display_type', ''),
            'needs_led_wall': 'LED Wall' in video_req.get('display_type', ''),
            
            # Video tags
            'camera_type': video_req.get('camera_type', 'Video Bar'),
            'camera_count': 2 if 'Multi-camera' in video_req.get('camera_type', '') else 1,
            'needs_broadcast_cameras': 'Broadcast' in video_req.get('camera_type', ''),
            'needs_matrix_switcher': 'Multi-camera' in video_req.get('camera_type', ''),
            
            # Audio tags
            'microphone_type': audio_req.get('microphone_type', 'Table'),
            'speaker_type': audio_req.get('speaker_type', 'Ceiling'),
            'needs_dsp': audio_req.get('dsp_required', True),
            'needs_voice_reinforcement': room_dimensions.get('area', 0) > 800,
            
            # Control tags
            'control_complexity': control_req.get('complexity', 'Standard'),
            'needs_advanced_control': control_req.get('complexity') in ['Advanced', 'Custom'],
            
            # Infrastructure tags
            'needs_rack': room_dimensions.get('area', 0) > 400 or audio_req.get('dsp_required'),
            'needs_wireless_presentation': True,  # Default
            
            # Special features
            'special_features': room_characteristics.get('special_features', []),
        }
        
        return tags


# ============================================================================
# INTEGRATION WITH EXISTING BOQ GENERATOR
# ============================================================================

def generate_boq_with_enhanced_room_analysis(
    gemini_model,
    product_df,
    room_description: str,
    room_dimensions: Dict,
    client_requirements: Any
) -> tuple:
    """
    Main entry point that integrates enhanced room analysis
    with existing BOQ generation
    
    Returns: (boq_items, validation_results, analysis_metadata)
    """
    
    analyzer = EnhancedRoomAnalyzer(gemini_model, product_df)
    
    # Ensure dimensions have defaults
    room_dimensions.setdefault('length', 20.0)
    room_dimensions.setdefault('width', 15.0)
    room_dimensions.setdefault('ceiling_height', 10.0)
    room_dimensions.setdefault('area', room_dimensions['length'] * room_dimensions['width'])
    
    # Analyze room type
    analysis = analyzer.analyze_room_type(room_description, room_dimensions)
    
    if analysis['analysis_type'] in ['PREDEFINED_PROFILE', 'MAPPED_TO_STANDARD']:
        # Use existing optimized BOQ generator
        st.success(f"✅ Using proven system for: {analysis['room_type']}")
        
        from components.optimized_boq_generator import OptimizedBOQGenerator
        
        generator = OptimizedBOQGenerator(
            product_df=product_df,
            client_requirements=client_requirements
        )
        
        boq_items, validation_results = generator.generate_boq_for_room(
            room_type=analysis['room_type'],
            room_length=room_dimensions['length'],
            room_width=room_dimensions['width'],
            ceiling_height=room_dimensions['ceiling_height']
        )
        
        # Add customizations if mapped
        if analysis.get('customizations'):
            validation_results['customizations'] = analysis['customizations']
        
        return boq_items, validation_results, analysis
    
    else:
        # --------------------------------------------------------------------
        # CHANGE 1.4 (MODIFY)
        # This block is modified to use the new unified blueprint generator
        # --------------------------------------------------------------------
        
        # AI-powered custom room analysis
        st.info("🤖 Generating custom BOQ using AI analysis + AVIXA standards...")
        
        room_chars = analysis['room_characteristics']
        
        # NEW: Convert AI analysis to tags (CHANGE 1.4)
        tags = analyzer.extract_requirements_tags(room_chars, room_dimensions)

        # NEW: Calculate AVIXA standards to pass to the unified blueprint generator
        # (This logic was moved from the deleted 'generate_custom_room_blueprint' function
        # to satisfy the dependency of the new '_build_blueprint_from_tags' method)
        from components.av_designer import AVIXADesigner
        designer = AVIXADesigner()
        
        display_calcs = designer.calculate_display_size_discas(
            room_dimensions['length'],
            room_dimensions['width'],
            content_type='BDM'
        )
        audio_calcs = designer.calculate_audio_coverage_a102(
            room_dimensions['area'],
            room_dimensions['ceiling_height'],
            room_chars.get('room_type_category', 'Conference'),
            room_chars.get('capacity', 8)
        )
        spl_calcs = designer.calculate_required_amplifier_power(
            room_dimensions['area'] * room_dimensions['ceiling_height'],
            75  # Standard SPL target
        )
        # Estimate mic calcs based on deleted logic
        mic_type = room_chars.get('audio_requirements', {}).get('microphone_type', 'Table')
        if mic_type == 'Ceiling':
            mics_needed = max(2, int(room_dimensions['area'] / 150))
        else: # Table or other
            mics_needed = max(2, int(room_dimensions['area'] / 80))
        mic_calcs = {'mics_needed': mics_needed}
        
        avixa_calcs = {
            'display': display_calcs,
            'audio': audio_calcs,
            'spl': spl_calcs,
            'microphones': mic_calcs
        }

        # NEW: Use the SAME blueprint generator (CHANGE 1.4)
        from components.optimized_boq_generator import OptimizedBOQGenerator
        
        generator = OptimizedBOQGenerator(
            product_df=product_df,
            client_requirements=client_requirements
        )
        
        # NEW: Generate blueprint using tags (CHANGE 1.4)
        # This calls the new function from Step 1.2 (in the other file)
        blueprint_dict = generator._build_blueprint_from_tags(
            tags,
            room_dimensions['area'],
            room_dimensions['ceiling_height'],
            avixa_calcs
        )
        # Convert blueprint dict to list for the selector loop
        blueprint = list(blueprint_dict.values())
        
        # Use intelligent product selector (Original code)
        from components.intelligent_product_selector import IntelligentProductSelector
        
        selector = IntelligentProductSelector(
            product_df=product_df,
            client_preferences=client_requirements.get_brand_preferences(),
            budget_tier=client_requirements.budget_level
        )
        
        boq_items = []
        for requirement in blueprint:
            product = selector.select_product_with_fallback(requirement)
            
            if product:
                product.update({
                    'quantity': requirement.quantity,
                    'justification': requirement.justification,
                    'top_3_reasons': [
                        f"AI-optimized for {room_chars['room_type_category']} space",
                        f"Meets AVIXA standards for {room_chars.get('capacity', 'custom')} person capacity",
                        f"Addresses special requirements: {', '.join(room_chars.get('special_features', ['Standard setup'])[:2])}"
                    ],
                    'avixa_compliant': True,
                    'matched': True
                })
                
                boq_items.append(product)
        
        # Validate (Original code)
        validation_results = {
            'ai_analysis_used': True,
            'room_characteristics': room_chars,
            'confidence': analysis['confidence'],
            'issues': [],
            'warnings': []
        }
        
        if analysis['confidence'] < 0.7:
            validation_results['warnings'].append(
                f"⚠️ AI confidence is {analysis['confidence']:.1%}. "
                f"Consider using closest standard profile: {room_chars.get('closest_standard_profile')}"
            )
        
        return boq_items, validation_results, analysis
