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
    
    def generate_custom_room_blueprint(self, room_characteristics: Dict, 
                                       room_dimensions: Dict, 
                                       client_preferences: Any) -> List:
        """
        Generate equipment blueprint for custom room based on AI analysis
        Uses AVIXA standards but adapts to unique requirements
        """
        from components.intelligent_product_selector import ProductRequirement
        
        blueprint = []
        
        # Extract characteristics
        capacity = room_characteristics.get('capacity', 8)
        audio_req = room_characteristics.get('audio_requirements', {})
        video_req = room_characteristics.get('video_requirements', {})
        control_req = room_characteristics.get('control_requirements', {})
        
        # 1. DISPLAY SYSTEM (based on AI analysis)
        display_type = video_req.get('display_type', 'Single Large')
        
        if display_type == 'Video Wall':
            blueprint.append(ProductRequirement(
                category='Displays',
                sub_category='Video Wall Display',
                quantity=4,  # 2x2 video wall
                priority=1,
                justification='AI-determined video wall configuration for high-impact presentation',
                min_price=1000,
                strict_category_match=True
            ))
        elif display_type == 'LED Wall':
            blueprint.append(ProductRequirement(
                category='Displays',
                sub_category='Direct-View LED',
                quantity=1,
                priority=1,
                justification='AI-determined LED wall for immersive content',
                min_price=5000,
                strict_category_match=True
            ))
        elif display_type == 'Dual':
            blueprint.append(ProductRequirement(
                category='Displays',
                sub_category='Professional Display',
                quantity=2,
                priority=1,
                justification='AI-determined dual display configuration',
                min_price=800,
                strict_category_match=True
            ))
        else:
            # Calculate display size based on room dimensions
            from components.av_designer import AVIXADesigner
            designer = AVIXADesigner()
            display_calcs = designer.calculate_display_size_discas(
                room_dimensions['length'],
                room_dimensions['width'],
                content_type='BDM'
            )
            
            blueprint.append(ProductRequirement(
                category='Displays',
                sub_category='Professional Display',
                quantity=1,
                priority=1,
                justification=f'AVIXA DISCAS: {display_calcs["selected_size_inches"]}" display',
                size_requirement=display_calcs['selected_size_inches'],
                min_price=500,
                strict_category_match=True
            ))
        
        # 2. VIDEO SYSTEM (based on AI analysis)
        camera_type = video_req.get('camera_type', 'Video Bar')
        
        if camera_type == 'Broadcast' or camera_type == 'Multi-camera':
            blueprint.append(ProductRequirement(
                category='Video Conferencing',
                sub_category='PTZ Camera',
                quantity=2,
                priority=2,
                justification='AI-determined multi-camera broadcast setup',
                min_price=1500,
                strict_category_match=True
            ))
            
            blueprint.append(ProductRequirement(
                category='Signal Management',
                sub_category='Matrix Switcher',
                quantity=1,
                priority=3,
                justification='Video switching for multi-camera setup',
                min_price=1000,
                strict_category_match=True
            ))
        elif camera_type == 'PTZ':
            blueprint.append(ProductRequirement(
                category='Video Conferencing',
                sub_category='PTZ Camera',
                quantity=1,
                priority=2,
                justification='AI-determined PTZ camera for flexible coverage',
                min_price=1000,
                strict_category_match=True
            ))
        else:  # Video Bar
            blueprint.append(ProductRequirement(
                category='Video Conferencing',
                sub_category='Video Bar',
                quantity=1,
                priority=2,
                justification='AI-determined all-in-one video bar solution',
                min_price=800,
                strict_category_match=True
            ))
        
        # 3. AUDIO SYSTEM (based on AI analysis and AVIXA A102.01)
        mic_type = audio_req.get('microphone_type', 'Table')
        speaker_type = audio_req.get('speaker_type', 'Ceiling')
        dsp_required = audio_req.get('dsp_required', True)
        
        # Calculate speaker coverage
        from components.av_designer import AVIXADesigner
        designer = AVIXADesigner()
        audio_calcs = designer.calculate_audio_coverage_a102(
            room_dimensions['area'],
            room_dimensions['ceiling_height'],
            room_characteristics['room_type_category'],
            capacity
        )
        
        # Microphones
        if mic_type == 'Ceiling':
            mic_count = max(2, int(room_dimensions['area'] / 150))
            blueprint.append(ProductRequirement(
                category='Audio',
                sub_category='Ceiling Microphone',
                quantity=mic_count,
                priority=4,
                justification=f'AI-determined ceiling mic array ({mic_count} units for {room_dimensions["area"]:.0f} sq ft)',
                min_price=400,
                strict_category_match=True
            ))
        elif mic_type == 'Wireless':
            blueprint.append(ProductRequirement(
                category='Audio',
                sub_category='Wireless Microphone System',
                quantity=2,
                priority=4,
                justification='AI-determined wireless microphone system for presenter mobility',
                min_price=600,
                strict_category_match=True
            ))
        else:  # Table
            mic_count = max(2, int(room_dimensions['area'] / 80))
            blueprint.append(ProductRequirement(
                category='Audio',
                sub_category='Table/Boundary Microphone',
                quantity=mic_count,
                priority=4,
                justification=f'AI-determined table microphones ({mic_count} units)',
                min_price=150,
                strict_category_match=True
            ))
        
        # DSP (if required)
        if dsp_required:
            blueprint.append(ProductRequirement(
                category='Audio',
                sub_category='DSP / Audio Processor / Mixer',
                quantity=1,
                priority=5,
                justification='AI-determined DSP for acoustic echo cancellation and audio processing',
                min_price=1500,
                strict_category_match=True
            ))
        
        # Speakers
        speaker_count = audio_calcs['speakers_needed']
        
        if speaker_type == 'Line Array':
            blueprint.append(ProductRequirement(
                category='Audio',
                sub_category='Loudspeaker / Speaker',
                quantity=2,
                priority=6,
                justification='AI-determined line array speakers for large space coverage',
                min_price=2000,
                strict_category_match=True
            ))
        elif speaker_type == 'Wall':
            blueprint.append(ProductRequirement(
                category='Audio',
                sub_category='Wall-mounted Loudspeaker',
                quantity=speaker_count,
                priority=6,
                justification=f'AVIXA A102.01: {speaker_count} wall speakers for uniform coverage',
                min_price=200,
                strict_category_match=True
            ))
        else:  # Ceiling (most common)
            blueprint.append(ProductRequirement(
                category='Audio',
                sub_category='Ceiling Loudspeaker',
                quantity=speaker_count,
                priority=6,
                justification=f'AVIXA A102.01: {speaker_count} ceiling speakers (±3dB uniformity)',
                min_price=100,
                strict_category_match=True
            ))
        
        # Amplifier
        spl_calcs = designer.calculate_required_amplifier_power(
            room_dimensions['area'] * room_dimensions['ceiling_height'],
            75  # Standard SPL target
        )
        
        blueprint.append(ProductRequirement(
            category='Audio',
            sub_category='Amplifier',
            quantity=1,
            priority=7,
            justification=f'AVIXA SPL: {spl_calcs["recommended_power_watts"]:.0f}W amplifier required',
            min_price=500,
            strict_category_match=True
        ))
        
        # 4. CONTROL SYSTEM (based on complexity)
        control_complexity = control_req.get('complexity', 'Standard')
        
        if control_complexity == 'Advanced' or control_complexity == 'Custom':
            blueprint.append(ProductRequirement(
                category='Control Systems',
                sub_category='Control Processor',
                quantity=1,
                priority=8,
                justification='AI-determined advanced control processor for complex system',
                min_price=1000,
                strict_category_match=True
            ))
            
            blueprint.append(ProductRequirement(
                category='Control Systems',
                sub_category='Touch Panel',
                quantity=1,
                priority=9,
                justification='AI-determined touch panel for advanced control',
                min_price=500,
                strict_category_match=True
            ))
        else:
            # Use native VC control
            blueprint.append(ProductRequirement(
                category='Video Conferencing',
                sub_category='Touch Controller / Panel',
                quantity=1,
                priority=8,
                justification='AI-determined native touch controller for VC system',
                min_price=300,
                strict_category_match=True
            ))
        
        # 5. INFRASTRUCTURE (based on needs)
        infrastructure_needs = room_characteristics.get('infrastructure_needs', [])
        
        # Always add essential infrastructure
        blueprint.append(ProductRequirement(
            category='Networking',
            sub_category='Network Switch',
            quantity=1,
            priority=10,
            justification='Managed PoE switch for AV endpoints',
            required_keywords=['switch', 'poe', 'managed'],
            min_price=300,
            strict_category_match=True
        ))
        
        # Add rack if complex system
        if control_complexity in ['Advanced', 'Custom'] or dsp_required:
            blueprint.append(ProductRequirement(
                category='Infrastructure',
                sub_category='AV Rack',
                quantity=1,
                priority=11,
                justification='Equipment rack for centralized AV components',
                min_price=500,
                strict_category_match=True
            ))
        
        # Connectivity
        blueprint.append(ProductRequirement(
            category='Cables & Connectivity',
            sub_category='Wall & Table Plate Module',
            quantity=1,
            priority=12,
            justification='Table connectivity for laptop input',
            required_keywords=['table', 'connectivity', 'hdmi', 'usb-c'],
            min_price=200,
            strict_category_match=True
        ))
        
        blueprint.append(ProductRequirement(
            category='Cables & Connectivity',
            sub_category='AV Cable',
            quantity=6,
            priority=13,
            justification='HDMI and network cables for system interconnection',
            required_keywords=['cable', 'hdmi'],
            min_price=20,
            strict_category_match=True
        ))
        
        # Display mounts
        display_mount_qty = blueprint[0].quantity if blueprint else 1
        blueprint.append(ProductRequirement(
            category='Mounts',
            sub_category='Display Mount / Cart',
            quantity=display_mount_qty,
            priority=14,
            justification=f'Wall mounts for {display_mount_qty} display(s)',
            mounting_type='wall',
            size_requirement=blueprint[0].size_requirement if blueprint and hasattr(blueprint[0], 'size_requirement') else None,
            min_price=150,
            strict_category_match=True
        ))
        
        return blueprint


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
        # AI-powered custom room analysis
        st.info("🤖 Generating custom BOQ using AI analysis + AVIXA standards...")
        
        room_chars = analysis['room_characteristics']
        
        # Generate custom blueprint
        blueprint = analyzer.generate_custom_room_blueprint(
            room_chars,
            room_dimensions,
            client_requirements
        )
        
        # Use intelligent product selector
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
        
        # Validate
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
