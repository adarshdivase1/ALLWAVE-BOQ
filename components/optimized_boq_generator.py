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
        blueprint = self._build_questionnaire_based_blueprint(
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
    
    def _build_questionnaire_based_blueprint(
        self, room_type: str, room_area: float, room_profile: Dict,
        ceiling_height: float, avixa_calcs: Dict
    ) -> Dict[str, ProductRequirement]:
        """
        ENHANCED: Intelligent blueprint that adapts to room size
        """
        
        blueprint = {}
        req = self.requirements
        
        # === ROOM SIZE CLASSIFICATION ===
        if room_area < 400:
            room_class = 'SMALL'
        elif room_area < 800:
            room_class = 'MEDIUM'
        elif room_area < 1500:
            room_class = 'LARGE'
        else:
            room_class = 'EXTRA_LARGE'
        
        st.info(f"🏢 Room Classification: {room_class} ({room_area:.0f} sqft)")
        
        # === DISPLAY SYSTEM ===
        display_size = avixa_calcs.get('recommended_display_size_inches', 65)
        display_qty = 2 if req.dual_display_needed else 1
        display_sub_cat = 'Interactive Display' if req.interactive_display_needed else 'Professional Display'
        
        blueprint['primary_display'] = ProductRequirement(
            category='Displays',
            sub_category=display_sub_cat,
            quantity=display_qty,
            priority=1,
            justification=f'AVIXA-calculated {display_size}" display',
            size_requirement=display_size,
            required_keywords=['display', '4k', str(display_size)],
            blacklist_keywords=['mount', 'bracket', 'stand', 'arm'],
            client_preference_weight=1.0,  # FORCE preference
            strict_category_match=True
        )
        
        blueprint['display_mount'] = ProductRequirement(
            category='Mounts',
            sub_category='Display Mount / Cart',
            quantity=display_qty,
            priority=2,
            justification=f'Heavy-duty mount for {display_size}" display',
            size_requirement=display_size,
            required_keywords=['mount', 'wall', 'large format'] if display_size >= 85 else ['mount', 'wall'],
            blacklist_keywords=['camera', 'speaker', 'microphone', 'touch panel', 'ipad'],
            min_price=300 if display_size >= 85 else 150,
            max_price=2000,
            strict_category_match=True
        )
        
        # === VIDEO CONFERENCING (ROOM-SIZE ADAPTIVE) ===
        if room_class in ['SMALL', 'MEDIUM']:
            # Video Bar for small/medium rooms
            st.info(f"✅ Using Video Bar (room size: {room_class})")
            
            blueprint['video_bar'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Video Bar',
                quantity=1,
                priority=3,
                justification=f'All-in-one solution for {room_class} room',
                required_keywords=['bar', 'video', 'conference', 'all-in-one'],
                blacklist_keywords=['mount', 'cable', 'accessory', 'extension'],
                min_price=1500,
                client_preference_weight=1.0
            )
            
        else:
            # LARGE/EXTRA_LARGE: Separate codec + PTZ camera
            st.info(f"✅ Using PTZ Camera System (room size: {room_class})")
            
            blueprint['video_codec'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Room Kit / Codec',
                quantity=1,
                priority=3,
                justification=f'Professional codec for {room_area:.0f} sqft room',
                required_keywords=['codec', 'room kit', 'system'],
                blacklist_keywords=['camera', 'bar', 'mount'],
                min_price=2000,
                client_preference_weight=1.0
            )
            
            # For EXTRA_LARGE rooms, use dual cameras
            camera_count = 2 if room_class == 'EXTRA_LARGE' else 1
            
            blueprint['ptz_camera'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='PTZ Camera',
                quantity=camera_count,
                priority=4,
                justification=f'{camera_count}x PTZ camera(s) for {room_area:.0f} sqft coverage',
                required_keywords=['ptz', 'camera', 'optical zoom'],
                blacklist_keywords=['webcam', 'usb camera', 'mount', 'bracket'],
                min_price=1500,
                client_preference_weight=1.0
            )
        
        # Touch Controller
        blueprint['touch_controller'] = ProductRequirement(
            category='Video Conferencing',
            sub_category='Touch Controller / Panel',
            quantity=1,
            priority=5,
            justification='Dedicated room control interface',
            required_keywords=['touch', 'controller', 'panel', 'room'],
            blacklist_keywords=['scheduling', 'calendar', 'ipad case'],
            min_price=400,
            max_price=1500,
            client_preference_weight=1.0
        )
        
        # === AUDIO SYSTEM (ROOM-SIZE ADAPTIVE) ===
        audio_integrated = (room_class == 'SMALL' and 'Video Bar' in [b.sub_category for b in blueprint.values()])
        
        if not audio_integrated:
            # === MICROPHONES (THE MISSING PIECE!) ===
            if 'Ceiling' in req.microphone_type:
                # Ceiling microphones
                if room_class in ['SMALL', 'MEDIUM']:
                    mic_type = 'Ceiling Microphone'
                    mic_count = max(2, int(room_area / 200))
                else:
                    mic_type = 'Ceiling Microphone'
                    mic_count = max(4, int(room_area / 150))
                
                st.info(f"✅ Adding {mic_count}x ceiling microphones")
                
                blueprint['ceiling_microphones'] = ProductRequirement(
                    category='Audio',
                    sub_category=mic_type,
                    quantity=mic_count,
                    priority=6,
                    justification=f'{mic_count}x ceiling mics for full room coverage',
                    required_keywords=['ceiling', 'microphone', 'array', 'pendant'],
                    blacklist_keywords=['wireless', 'handheld', 'table', 'boundary', 'gooseneck', 'mixer'],
                    min_price=200,
                    client_preference_weight=0.9
                )
                
            else:
                # Table/Boundary microphones
                mic_count = max(2, int(room_area / 250))
                
                st.info(f"✅ Adding {mic_count}x table microphones")
                
                blueprint['table_microphones'] = ProductRequirement(
                    category='Audio',
                    sub_category='Table/Boundary Microphone',
                    quantity=mic_count,
                    priority=6,
                    justification=f'{mic_count}x table mics for conference table',
                    required_keywords=['microphone', 'table', 'boundary', 'conference'],
                    blacklist_keywords=['ceiling', 'wireless', 'handheld', 'gooseneck', 'mixer'],
                    min_price=150,
                    client_preference_weight=0.9
                )
            
            # === DSP (MANDATORY for MEDIUM+ rooms) ===
            if room_class in ['MEDIUM', 'LARGE', 'EXTRA_LARGE']:
                st.info(f"✅ Adding professional DSP for {room_class} room")
                
                blueprint['audio_dsp'] = ProductRequirement(
                    category='Audio',
                    sub_category='DSP / Audio Processor / Mixer',
                    quantity=1,
                    priority=7,
                    justification=f'Professional audio processing for {room_area:.0f} sqft',
                    required_keywords=['dsp', 'processor', 'audio', 'conferencing', 'dante', 'tesira', 'qsc', 'core'],
                    blacklist_keywords=[
                        'amplifier', 'speaker', 'loudspeaker', 'portable', 
                        'active speaker', 'powered speaker', 'cp12', 'cp8', 'k12'
                    ],
                    min_price=1000,
                    max_price=10000,
                    client_preference_weight=1.0,
                    strict_category_match=True
                )
            
            # === SPEAKERS ===
            if 'Ceiling' in req.ceiling_vs_table_audio or room_class in ['LARGE', 'EXTRA_LARGE']:
                speaker_count = max(4, int(room_area / 200))
                
                st.info(f"✅ Adding {speaker_count}x ceiling speakers")
                
                blueprint['ceiling_speakers'] = ProductRequirement(
                    category='Audio',
                    sub_category='Ceiling Loudspeaker',
                    quantity=speaker_count,
                    priority=8,
                    justification=f'{speaker_count}x ceiling speakers for even coverage',
                    required_keywords=['ceiling', 'speaker', 'loudspeaker'],
                    blacklist_keywords=['portable', 'powered', 'active', 'subwoofer'],
                    min_price=100,
                    client_preference_weight=0.9
                )
                
                # === AMPLIFIER (For passive speakers) ===
                blueprint['power_amplifier'] = ProductRequirement(
                    category='Audio',
                    sub_category='Amplifier',
                    quantity=1,
                    priority=9,
                    justification=f'Multi-channel amplifier for {speaker_count} speakers',
                    required_keywords=['amplifier', 'power', 'channel', 'multi-channel'],
                    blacklist_keywords=['dsp', 'mixer', 'processor', 'summing', 'line driver'],
                    min_price=500,
                    client_preference_weight=0.9
                )
        
        # === CONNECTIVITY ===
        if req.wireless_presentation_needed:
            st.info(f"✅ Adding wireless presentation system")
            
            blueprint['wireless_presentation'] = ProductRequirement(
                category='Signal Management',
                sub_category='Scaler / Converter / Processor',
                quantity=1,
                priority=10,
                justification='Wireless BYOD content sharing',
                required_keywords=['wireless', 'presentation', 'clickshare', 'airmedia', 'airplay'],
                min_price=800,
                max_price=3000
            )
        
        # === SCHEDULING PANEL ===
        if req.room_scheduling_needed:
            st.info(f"✅ Adding room scheduling display")
            
            blueprint['room_scheduler'] = ProductRequirement(
                category='Control Systems',
                sub_category='Touch Panel',
                quantity=1,
                priority=11,
                justification='Room booking and scheduling integration',
                required_keywords=['scheduling', 'room panel', 'booking', 'calendar'],
                blacklist_keywords=['controller', 'codec', 'video'],
                min_price=400,
                max_price=1200,
                client_preference_weight=1.0
            )
        
        # === LIGHTING CONTROL ===
        if req.lighting_control_integration:
            st.info(f"✅ Adding lighting control")
            
            blueprint['lighting_control'] = ProductRequirement(
                category='Lighting',
                sub_category='Lighting Control',
                quantity=1,
                priority=12,
                justification='Automated lighting for AV integration',
                required_keywords=['dimmer', 'lighting', 'control', 'channel'],
                min_price=500,
                client_preference_weight=1.0
            )
        
        # === CABLES ===
        component_count = len([b for b in blueprint.values() if b.category not in ['Cables & Connectivity']])
        cable_count = max(10, component_count * 3)
        
        blueprint['network_cables'] = ProductRequirement(
            category='Cables & Connectivity',
            sub_category='AV Cable',
            quantity=cable_count,
            priority=13,
            justification=f'{cable_count}x network cables for system connectivity',
            required_keywords=['cat6', 'cat7', 'ethernet', 'cable'],
            blacklist_keywords=['hdmi', 'usb', 'audio'],
            min_price=15,
            max_price=100
        )
        
        # === INFRASTRUCTURE (MANDATORY for MEDIUM+ rooms) ===
        if room_class in ['MEDIUM', 'LARGE', 'EXTRA_LARGE']:
            st.info(f"✅ Adding equipment rack (room size: {room_class})")
            
            # Calculate rack size based on components
            equipment_count = len([b for b in blueprint.values() 
                                    if b.category in ['Audio', 'Signal Management', 'Control Systems', 'Infrastructure']])
            rack_size = max(12, min(24, equipment_count * 2))
            
            blueprint['equipment_rack'] = ProductRequirement(
                category='Infrastructure',
                sub_category='AV Rack',
                quantity=1,
                priority=14,
                justification=f'{rack_size}U rack for professional component housing',
                required_keywords=['rack', 'cabinet', 'enclosure', f'{rack_size}u'],
                blacklist_keywords=['shelf', 'mount', 'bracket', 'camera'],
                min_price=600,
                strict_category_match=True
            )
            
            blueprint['power_distribution'] = ProductRequirement(
                category='Infrastructure',
                sub_category='Power (PDU/UPS)',
                quantity=1,
                priority=15,
                justification='Rackmount power distribution with monitoring',
                required_keywords=['pdu', 'power', 'distribution', 'rackmount'],
                blacklist_keywords=['ups', 'battery'],
                min_price=200
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
        """
        ENHANCED: Comprehensive validation with brand checking
        """
        
        validation = {
            'issues': [],
            'warnings': [],
            'brand_compliance': []
        }
        
        categories_present = {item.get('category') for item in boq_items}
        sub_categories = [item.get('sub_category', '') for item in boq_items]
        brands = {item.get('category'): item.get('brand') for item in boq_items}
        
        # === BRAND PREFERENCE VALIDATION ===
        pref = self.requirements.get_brand_preferences()
        for category, preferred_brand in pref.items():
            if preferred_brand != 'No Preference':
                category_map = {
                    'displays': 'Displays',
                    'video_conferencing': 'Video Conferencing',
                    'audio': 'Audio',
                    'control': 'Control Systems'
                }
                
                actual_category = category_map.get(category)
                if actual_category in brands:
                    actual_brand = brands[actual_category]
                    if actual_brand.lower() != preferred_brand.lower():
                        validation['issues'].append(
                            f"🚨 BRAND MISMATCH: {actual_category} is {actual_brand}, "
                            f"but client requested {preferred_brand}"
                        )
                    else:
                        validation['brand_compliance'].append(
                            f"✅ {actual_category}: Correctly using {preferred_brand}"
                        )
        
        # === ESSENTIAL COMPONENTS ===
        if 'Displays' not in categories_present:
            validation['issues'].append("🚨 CRITICAL: No display system found")
        
        if 'Video Conferencing' not in categories_present:
            validation['issues'].append("🚨 CRITICAL: No video conferencing equipment")
        
        # === MICROPHONE VALIDATION (THE CRITICAL MISSING PIECE) ===
        has_microphones = any(
            'Microphone' in sub_cat or 'Mic' in sub_cat
            for sub_cat in sub_categories
        )
        
        # Check if audio is integrated in video bar
        has_video_bar = any('Video Bar' in sub_cat for sub_cat in sub_categories)
        audio_integrated = has_video_bar and room_area < 400
        
        if not has_microphones and not audio_integrated:
            validation['issues'].append(
                "🚨 CRITICAL: No microphones found - system cannot capture audio!"
            )
        
        # === DSP VALIDATION ===
        if room_area > 600:
            has_dsp = False
            for item in boq_items:
                if 'DSP' in item.get('sub_category', '') or 'Processor' in item.get('sub_category', ''):
                    name = item.get('name', '').lower()
                    # Verify it's NOT a speaker
                    if any(bad_word in name for bad_word in ['speaker', 'loudspeaker', 'portable', 'cp12', 'k12']):
                        validation['issues'].append(
                            f"🚨 CRITICAL: '{item.get('name')}' is a SPEAKER, not a DSP!"
                        )
                    else:
                        has_dsp = True
                        break
            
            if not has_dsp:
                validation['issues'].append(
                    f"🚨 CRITICAL: Room ({room_area:.0f} sqft) needs professional DSP"
                )
        
        # === MOUNT VALIDATION ===
        display_count = sum(1 for item in boq_items if item.get('category') == 'Displays')
        mount_count = sum(
            1 for item in boq_items 
            if item.get('category') == 'Mounts' and 'Display' in item.get('sub_category', '')
        )
        
        if display_count > mount_count:
            validation['issues'].append(
                f"🚨 MISMATCH: {display_count} displays but only {mount_count} mounts"
            )
        
        # === RACK VALIDATION ===
        if room_area > 600:
            has_rack = any('Rack' in sub_cat for sub_cat in sub_categories)
            if not has_rack:
                validation['issues'].append(
                    "🚨 CRITICAL: Large system needs equipment rack for proper housing"
                )
        
        # === AMPLIFIER VALIDATION (For passive speakers) ===
        has_passive_speakers = any(
            'Ceiling Loudspeaker' in sub_cat or 'Wall-mounted Loudspeaker' in sub_cat
            for sub_cat in sub_categories
        )
        
        if has_passive_speakers:
            has_amplifier = any('Amplifier' in sub_cat for sub_cat in sub_categories)
            if not has_amplifier:
                validation['warnings'].append(
                    "💡 Passive speakers need a power amplifier"
                )
        
        # === CONTROL INTERFACE VALIDATION ===
        has_control = any(
            'Touch Controller' in sub_cat or 'Touch Panel' in sub_cat
            for sub_cat in sub_categories
        )
        if not has_control:
            validation['warnings'].append(
                "💡 Consider adding touch controller for user interface"
            )
        
        return validation
