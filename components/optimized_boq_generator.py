import streamlit as st
from typing import Dict, List, Any, Tuple
import pandas as pd

from components.smart_questionnaire import ClientRequirements
from components.room_profiles import ROOM_SPECS
from components.intelligent_product_selector import IntelligentProductSelector, ProductRequirement
from components.av_designer import calculate_avixa_recommendations


class OptimizedBOQGenerator:
    """
    Rule-based BOQ generator that creates logical, AVIXA-compliant systems
    """
    
    def __init__(self, product_df: pd.DataFrame, client_requirements: ClientRequirements):
        self.product_df = product_df
        self.requirements = client_requirements
        self.selector = IntelligentProductSelector(
            product_df=product_df,
            client_preferences=client_requirements.get_brand_preferences(),
            budget_tier=client_requirements.budget_level
        )
        
    def generate_boq_for_room(
        self, 
        room_type: str, 
        room_length: float, 
        room_width: float, 
        ceiling_height: float
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """Generate complete BOQ for a single room"""
        
        room_area = room_length * room_width
        room_profile = ROOM_SPECS.get(room_type, ROOM_SPECS['Standard Conference Room (6-8 People)'])
        
        # Calculate AVIXA recommendations
        avixa_calcs = calculate_avixa_recommendations(
            room_length, room_width, ceiling_height, room_type
        )
        
        # Build blueprint
        blueprint = self._build_logical_blueprint(
            room_type=room_type,
            room_area=room_area,
            room_profile=room_profile,
            ceiling_height=ceiling_height,
            avixa_calcs=avixa_calcs
        )
        
        # Select products
        boq_items = []
        for component_key, requirement in blueprint.items():
            product = self.selector.select_product(requirement)
            
            if product:
                justification = self._generate_component_justification(
                    component_key, product, room_type, room_area
                )
                
                product.update({
                    'quantity': requirement.quantity,
                    'justification': justification['technical'],
                    'top_3_reasons': justification['reasons'],
                    'justification_confidence': 0.95,
                    'matched': True
                })
                
                boq_items.append(product)
        
        validation_results = self._validate_boq_completeness(boq_items, room_type, room_area)
        
        return boq_items, validation_results
    
    def _build_logical_blueprint(
        self, room_type: str, room_area: float, room_profile: Dict,
        ceiling_height: float, avixa_calcs: Dict
    ) -> Dict[str, ProductRequirement]:
        """Build equipment blueprint based on questionnaire responses"""
        
        blueprint = {}
        req = self.requirements
        
        # === DISPLAY SYSTEM ===
        display_size = avixa_calcs.get('recommended_display_size_inches', 65)
        display_qty = 2 if req.dual_display_needed else 1
        
        blueprint['primary_display'] = ProductRequirement(
            category='Displays',
            sub_category='Interactive Display' if req.interactive_display_needed else 'Professional Display',
            quantity=display_qty,
            priority=1,
            justification=f'AVIXA-calculated {display_size}" display for optimal viewing',
            size_requirement=display_size,
            required_keywords=['display', '4k'],
            blacklist_keywords=['mount', 'bracket'],
            client_preference_weight=0.9
        )
        
        blueprint['display_mount'] = ProductRequirement(
            category='Mounts',
            sub_category='Display Mount / Cart',
            quantity=display_qty,
            priority=8,
            justification=f'Professional mount for {display_size}" display',
            size_requirement=display_size,
            required_keywords=['wall', 'mount'],
            blacklist_keywords=['camera', 'speaker', 'touch', 'panel'],
            min_price=200,
            max_price=2000
        )
        
        # === VIDEO CONFERENCING ===
        if 'All-in-One Video Bar' in req.camera_type_preference:
            blueprint['video_bar'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Video Bar',
                quantity=1,
                priority=2,
                justification='All-in-one video bar with integrated audio',
                required_keywords=['bar', 'video', 'camera'],
                blacklist_keywords=['mount', 'accessory'],
                client_preference_weight=0.9
            )
        else:
            blueprint['video_codec'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Room Kit / Codec',
                quantity=1,
                priority=2,
                justification=f'Video conferencing codec for {req.vc_platform}',
                required_keywords=['codec', 'room kit'],
                client_preference_weight=0.9
            )
            
            blueprint['ptz_camera'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='PTZ Camera',
                quantity=1,
                priority=3,
                justification='PTZ camera for comprehensive room coverage',
                required_keywords=['ptz', 'camera'],
                min_price=1000
            )
        
        # Touch controller
        blueprint['touch_controller'] = ProductRequirement(
            category='Video Conferencing',
            sub_category='Touch Controller / Panel',
            quantity=1,
            priority=4,
            justification='Touch controller for system operation',
            required_keywords=['touch', 'controller', 'panel'],
            blacklist_keywords=['room kit', 'codec', 'bar'],
            min_price=300
        )
        
        # === AUDIO SYSTEM ===
        audio_integrated = 'All-in-One Video Bar' in req.camera_type_preference and room_area < 400
        
        if not audio_integrated:
            # Microphones
            if 'Ceiling' in req.microphone_type:
                mic_count = max(2, int(room_area / 150))
                blueprint['ceiling_microphones'] = ProductRequirement(
                    category='Audio',
                    sub_category='Ceiling Microphone',
                    quantity=mic_count,
                    priority=5,
                    justification=f'{mic_count}x ceiling mics for {room_area:.0f} sqft coverage',
                    required_keywords=['ceiling', 'microphone']
                )
            elif 'Table' in req.microphone_type:
                mic_count = max(1, int(room_area / 200))
                blueprint['table_microphones'] = ProductRequirement(
                    category='Audio',
                    sub_category='Table/Boundary Microphone',
                    quantity=mic_count,
                    priority=5,
                    justification=f'{mic_count}x table microphones',
                    required_keywords=['table', 'boundary', 'microphone']
                )
            
            # DSP for large rooms or complex audio
            if room_area > 400 or req.voice_reinforcement_needed:
                blueprint['audio_dsp'] = ProductRequirement(
                    category='Audio',
                    sub_category='DSP / Audio Processor / Mixer',
                    quantity=1,
                    priority=6,
                    justification='DSP for professional audio processing',
                    required_keywords=['dsp', 'processor'],
                    blacklist_keywords=['amplifier']
                )
            
            # Speakers
            if 'Ceiling' in req.ceiling_vs_table_audio or req.voice_reinforcement_needed:
                speaker_count = max(2, int(room_area / 200))
                blueprint['ceiling_speakers'] = ProductRequirement(
                    category='Audio',
                    sub_category='Ceiling Loudspeaker',
                    quantity=speaker_count,
                    priority=7,
                    justification=f'{speaker_count}x ceiling speakers',
                    required_keywords=['ceiling', 'speaker']
                )
                
                # Add amplifier for passive speakers
                blueprint['power_amplifier'] = ProductRequirement(
                    category='Audio',
                    sub_category='Amplifier',
                    quantity=1,
                    priority=8,
                    justification=f'Power amplifier for {speaker_count} speakers',
                    required_keywords=['amplifier', 'power', 'channel'],
                    blacklist_keywords=['dsp', 'summing']
                )
        
        # === CONNECTIVITY ===
        if req.wireless_presentation_needed:
            blueprint['wireless_presentation'] = ProductRequirement(
                category='Signal Management',
                sub_category='Wireless Presentation',
                quantity=1,
                priority=9,
                justification='Wireless presentation for BYOD',
                required_keywords=['wireless', 'presentation']
            )
        
        # === CABLES ===
        component_count = len(blueprint)
        cable_count = max(5, component_count * 2)
        
        blueprint['network_cables'] = ProductRequirement(
            category='Cables & Connectivity',
            sub_category='AV Cable',
            quantity=cable_count,
            priority=10,
            justification=f'{cable_count}x network cables',
            required_keywords=['cat6', 'cat7', 'ethernet'],
            min_price=10,
            max_price=150
        )
        
        # === INFRASTRUCTURE ===
        if room_area > 400:
            blueprint['equipment_rack'] = ProductRequirement(
                category='Infrastructure',
                sub_category='AV Rack',
                quantity=1,
                priority=11,
                justification='Equipment rack for AV components',
                required_keywords=['rack', 'cabinet'],
                min_price=300
            )
            
            blueprint['power_distribution'] = ProductRequirement(
                category='Infrastructure',
                sub_category='Power (PDU/UPS)',
                quantity=1,
                priority=12,
                justification='Rackmount PDU for power distribution',
                required_keywords=['pdu', 'power']
            )
        
        return blueprint
    
    def _generate_component_justification(
        self, component_key: str, product: Dict, room_type: str, room_area: float
    ) -> Dict[str, Any]:
        """Generate justification for selected component"""
        
        category = product.get('category', 'General')
        
        # Technical justification
        technical = f"Selected {product.get('brand')} {product.get('model_number')} for {room_type} ({room_area:.0f} sqft)"
        
        # Top 3 reasons based on component type
        reasons = []
        
        if 'Display' in category:
            reasons = [
                f"AVIXA-compliant sizing for {room_area:.0f} sqft room ensures optimal viewing",
                "Professional 4K resolution with commercial warranty for reliability",
                f"Certified for {self.requirements.vc_platform} integration"
            ]
        elif 'Video Conferencing' in category:
            reasons = [
                f"Native {self.requirements.vc_platform} certification ensures seamless operation",
                "Auto-framing and speaker tracking enhance remote collaboration",
                f"Ecosystem compatibility with {self.requirements.vc_brand_preference} standards"
            ]
        elif 'Audio' in category:
            reasons = [
                f"Coverage pattern optimized for {room_area:.0f} sqft acoustics",
                "Professional AEC and noise reduction for clear communication",
                "Scalable architecture allows future expansion"
            ]
        else:
            reasons = [
                f"Industry-standard solution for {room_type}",
                "Reliable performance with manufacturer support",
                "Cost-effective for project requirements"
            ]
        
        return {
            'technical': technical,
            'reasons': reasons[:3]
        }
    
    def _validate_boq_completeness(
        self, boq_items: List[Dict], room_type: str, room_area: float
    ) -> Dict[str, Any]:
        """Validate BOQ has all necessary components"""
        
        validation = {
            'issues': [],
            'warnings': []
        }
        
        # Check for essential components
        categories_present = {item.get('category') for item in boq_items}
        
        if 'Displays' not in categories_present:
            validation['issues'].append("🚨 No display found")
        
        if 'Video Conferencing' not in categories_present:
            validation['issues'].append("🚨 No video conferencing equipment")
        
        # Check for control system
        has_control = any(
            'Touch Controller' in item.get('sub_category', '') 
            for item in boq_items
        )
        if not has_control:
            validation['warnings'].append("💡 Consider adding touch controller")
        
        # Check mounts
        display_count = sum(1 for item in boq_items if item.get('category') == 'Displays')
        mount_count = sum(
            1 for item in boq_items 
            if item.get('category') == 'Mounts' and 'Display' in item.get('sub_category', '')
        )
        
        if display_count > mount_count:
            validation['issues'].append(f"🚨 {display_count} displays but only {mount_count} mounts")
        
        return validation
