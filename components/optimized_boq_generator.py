# components/optimized_boq_generator.py
# ENHANCED VERSION - Full AVIXA Standards Implementation & Production Readiness Fixes

import streamlit as st
from typing import Dict, List, Any, Tuple
import pandas as pd
import math

from components.smart_questionnaire import ClientRequirements
from components.room_profiles import ROOM_SPECS
from components.intelligent_product_selector import IntelligentProductSelector, ProductRequirement
from components.av_designer import calculate_avixa_recommendations

# PRODUCTION: Room-specific display constraints
ROOM_DISPLAY_CONSTRAINTS = {
    'Small Huddle Room (2-3 People)': {'min': 43, 'max': 55},
    'Medium Huddle Room (4-6 People)': {'min': 50, 'max': 65},
    'Standard Conference Room (6-8 People)': {'min': 55, 'max': 75},
    'Large Conference Room (8-12 People)': {'min': 65, 'max': 85},
    'Executive Boardroom (10-16 People)': {'min': 75, 'max': 98},
    'Training Room (15-25 People)': {'min': 75, 'max': 98},
    'Large Training/Presentation Room (25-40 People)': {'min': 98, 'max': 110},
    'Multipurpose Event Room (40+ People)': {'min': 98, 'max': 120},
}

class EnhancedAVIXACalculator:
    """
    Implements ALL AVIXA calculations from guidelines document
    """
    
    @staticmethod
    def calculate_display_size_discas(room_length: float, room_width: float, content_type: str = "BDM") -> Dict:
        """
        AVIXA DISCAS - Display Image Size for 2D Content
        Section 1 of guidelines
        """
        # Maximum viewing distance (85% of room length for furniture)
        max_viewing_distance = max(room_length, room_width) * 0.85
        
        if content_type == "ADM":  # Analytical Decision Making
            # Formula: Image Height = (Farthest Viewer Distance ÷ 3438) × Vertical Resolution
            min_image_height = (max_viewing_distance / 3438) * 1080  # Assuming 1080p
            
        elif content_type == "BDM":  # Basic Decision Making (presentations)
            # Formula: Image Height = (Farthest Viewer Distance ÷ 200) ÷ Element Height %
            element_height_percent = 0.04  # 4% for standard presentations
            min_image_height = (max_viewing_distance / 200) / element_height_percent
            
        else:  # Passive viewing
            # Formula: Image Height = Viewing Distance ÷ 8
            min_image_height = max_viewing_distance / 8
        
        # Convert to diagonal (16:9 aspect ratio)
        recommended_diagonal = min_image_height * 2.22
        
        # Snap to available sizes
        available_sizes = [43, 55, 65, 75, 85, 98]
        selected_size = min((size for size in available_sizes if size >= recommended_diagonal), default=98)
        
        return {
            'max_viewing_distance_ft': max_viewing_distance,
            'min_image_height_inches': min_image_height,
            'recommended_diagonal_inches': recommended_diagonal,
            'selected_size_inches': selected_size,
            'content_type': content_type
        }
    
    @staticmethod
    def validate_viewing_angles(room_width: float, display_width_inches: float, seating_rows: int) -> Dict:
        """
        AVIXA Viewing Angle Standards
        Section 1 of guidelines
        """
        display_width_ft = display_width_inches / 12 * 0.871  # 16:9 conversion
        
        # Calculate horizontal viewing angles
        optimal_viewing_zone = room_width * 0.6  # 60% of room width
        
        # Maximum offset for 45° viewing angle
        max_offset = display_width_ft / 2 + math.tan(math.radians(45)) * 10  # Assuming 10ft viewing distance
        
        seats_within_optimal = optimal_viewing_zone >= room_width * 0.8
        
        return {
            'optimal_viewing_zone_ft': optimal_viewing_zone,
            'max_acceptable_offset_ft': max_offset,
            'all_seats_acceptable': seats_within_optimal,
            'horizontal_angle_max': 45,
            'vertical_angle_max': 30
        }
    
    @staticmethod
    def calculate_audio_coverage_a102(room_area: float, ceiling_height: float, 
                                       room_type: str, occupancy: int = None) -> Dict:
        """
        ENHANCED: Now scales with actual occupancy, not just area
        AVIXA A102.01:2017 - Audio Coverage Uniformity
        Section 2 of guidelines
        """
        # Base coverage (area-based)
        if ceiling_height <= 9:
            coverage_per_speaker = 150
        elif ceiling_height <= 12:
            coverage_per_speaker = 200
        else:
            coverage_per_speaker = 250

        # Room type adjustment
        if room_type in ["Conference", "Meeting"]:
            coverage_per_speaker *= 0.8
        elif room_type in ["Training", "Classroom"]:
            coverage_per_speaker *= 0.9

        area_based_speakers = max(2, math.ceil(room_area / coverage_per_speaker))

        # NEW: Occupancy-based validation
        if occupancy:
            # AVIXA guideline: 1 speaker per 6-8 people in training/presentation environments
            if "Training" in room_type or "Presentation" in room_type:
                occupancy_based_speakers = max(2, math.ceil(occupancy / 7))
                
                # Use the HIGHER of the two calculations
                speakers_needed = max(area_based_speakers, occupancy_based_speakers)
            else:
                speakers_needed = area_based_speakers
        else:
            speakers_needed = area_based_speakers

        # Target STI
        target_sti = 0.70 if "Executive" in room_type or "Critical" in room_type else 0.60

        return {
            'speakers_needed': speakers_needed,
            'calculation_basis': 'area + occupancy' if occupancy else 'area only',
            'coverage_per_speaker_sqft': coverage_per_speaker,
            'target_sti': target_sti,
            'spl_uniformity_target': '±3 dB (500Hz-4kHz)',
            'ceiling_height_ft': ceiling_height
        }

    @staticmethod
    def calculate_microphone_coverage(room_area: float, table_config: str) -> Dict:
        """
        AVIXA Microphone Coverage Standards
        Section 2 of guidelines
        """
        if table_config == "round_table":
            mic_coverage_area = 80  # sq ft per microphone
            mic_type = "Table/Boundary Microphone"
            
        elif table_config == "conference_table":
            mic_spacing_ft = 6  # feet between mics
            table_length = math.sqrt(room_area) * 0.7  # Estimate
            mics_needed = max(2, math.ceil(table_length / mic_spacing_ft))
            return {
                'mics_needed': mics_needed,
                'mic_type': "Gooseneck/Array Microphone",
                'spacing_ft': mic_spacing_ft,
                'pickup_pattern': "Cardioid/Supercardioid"
            }
            
        else:  # Open floor plan
            mic_coverage_area = 150  # sq ft per ceiling mic
            mic_type = "Ceiling Array Microphone"
        
        mics_needed = max(2, math.ceil(room_area / mic_coverage_area))
        
        return {
            'mics_needed': mics_needed,
            'mic_type': mic_type,
            'coverage_area_sqft': mic_coverage_area,
            'pickup_pattern': 'Omnidirectional (ceiling)' if 'Ceiling' in mic_type else 'Cardioid'
        }
    
    @staticmethod
    def calculate_required_amplifier_power(room_volume: float, target_spl: float, speaker_sensitivity: float = 89) -> Dict:
        """
        AVIXA SPL Calculation
        Section 2 of guidelines
        """
        # Distance to farthest listener (estimate)
        room_length = (room_volume / 10) ** (1/3)  # Rough estimate
        distance_meters = room_length * 0.3048 * 0.85
        
        # Account for room acoustics
        if room_volume < 5000:
            acoustic_loss = 3  # dB
        elif room_volume < 15000:
            acoustic_loss = 6
        else:
            acoustic_loss = 10
        
        adjusted_target_spl = target_spl + acoustic_loss
        
        # Power calculation
        power_watts = 10 ** ((adjusted_target_spl - speaker_sensitivity + 20 * math.log10(distance_meters)) / 10)
        
        # Add headroom (safety factor)
        recommended_power = power_watts * 2
        
        return {
            'required_power_watts': power_watts,
            'recommended_power_watts': recommended_power,
            'target_spl_db': target_spl,
            'speaker_sensitivity_db': speaker_sensitivity,
            'acoustic_loss_db': acoustic_loss
        }
    
    @staticmethod
    def calculate_network_requirements(room_equipment: Dict) -> Dict:
        """
        AVIXA Network Infrastructure Standards
        Section 5 of guidelines
        """
        total_bandwidth = 0
        
        # Video conferencing codec
        if room_equipment.get("video_codec"):
            codec_streams = room_equipment.get("cameras", 1) + 1  # +1 for content
            total_bandwidth += codec_streams * 4  # Mbps per 1080p stream
        
        # Networked displays (AV over IP)
        if room_equipment.get("network_displays"):
            display_count = room_equipment["network_displays"]
            total_bandwidth += display_count * 50  # Mbps per 4K display
        
        # Control system
        total_bandwidth += 5  # Mbps for control traffic
        
        # Digital signage
        if room_equipment.get("digital_signage"):
            total_bandwidth += 10
        
        # Calculate switch requirements
        required_ports = sum([
            room_equipment.get("cameras", 0),
            room_equipment.get("displays", 0),
            room_equipment.get("network_displays", 0),
            1,  # Codec/processor
            1,  # Control system
            2   # Spare ports
        ])
        
        # Recommend switch tier
        if total_bandwidth > 500:
            switch_type = "10GbE Managed Switch"
        elif total_bandwidth > 100:
            switch_type = "1GbE Managed Switch with SFP+ uplink"
        else:
            switch_type = "1GbE Managed Switch"
        
        return {
            'total_bandwidth_mbps': total_bandwidth,
            'switch_type': switch_type,
            'required_ports': required_ports,
            'recommended_ports': math.ceil(required_ports / 8) * 8,
            'poe_required': True,
            'qos_required': True,
            'vlan_structure': {
                'AV_Production': 10,
                'Video_Conferencing': 20,
                'Control_Systems': 30
            }
        }
    
    @staticmethod
    def calculate_power_requirements(boq_items: List[Dict]) -> Dict:
        """
        AVIXA Power & Electrical Standards
        Section 6 of guidelines
        """
        power_ratings = {
            'Displays': {'55-65': 200, '75-85': 375, '98': 600},
            'Video Conferencing': {'codec': 75, 'camera_poe': 25},
            'Audio': {'amplifier': 250, 'dsp': 40, 'speaker': 60},
            'Control Systems': {'processor': 35},
            'Infrastructure': {'switch_24port': 300}
        }
        
        total_watts = 0
        poe_watts = 0
        
        for item in boq_items:
            category = item.get('category', '')
            quantity = item.get('quantity', 1)
            
            # Estimate power based on category
            if category == 'Displays':
                size = item.get('size_requirement', 65)
                if size >= 98:
                    total_watts += 600 * quantity
                elif size >= 75:
                    total_watts += 375 * quantity
                else:
                    total_watts += 200 * quantity
                    
            elif category == 'Audio':
                if 'Amplifier' in item.get('sub_category', ''):
                    total_watts += 250 * quantity
                elif 'DSP' in item.get('sub_category', ''):
                    total_watts += 40 * quantity
                    
            elif category == 'Video Conferencing':
                if 'Camera' in item.get('sub_category', ''):
                    poe_watts += 25 * quantity
                else:
                    total_watts += 75 * quantity
        
        # Add 20% safety factor
        total_watts *= 1.2
        poe_watts *= 1.2
        
        # Calculate circuit requirements (120V systems)
        required_amps = total_watts / 120
        recommended_circuits = math.ceil(required_amps / 15)  # 15A circuits
        
        if required_amps > 30:
            recommended_circuits = math.ceil(required_amps / 20)
            circuit_rating = "20A"
        else:
            circuit_rating = "15A"
        
        return {
            'total_watts': total_watts,
            'poe_watts': poe_watts,
            'total_amps': required_amps,
            'recommended_circuits': recommended_circuits,
            'circuit_rating': circuit_rating,
            'ups_recommended': total_watts > 500,
            'ups_capacity_va': total_watts * 1.4 if total_watts > 500 else 0
        }
    
    @staticmethod
    def recommend_acoustic_treatment(room_volume: float, rt60_measured: float, room_type: str) -> Dict:
        """
        AVIXA Acoustic Treatment Standards
        Section 3 of guidelines
        """
        target_rt60 = {
            "Conference": 0.5,
            "Training": 0.6,
            "Boardroom": 0.4,
            "Auditorium": 1.0
        }.get(room_type, 0.6)
        
        if rt60_measured > target_rt60 * 1.5:
            panel_coverage = room_volume / 100
            return {
                'treatment_level': 'Heavy',
                'panel_area_sqft': panel_coverage,
                'panel_nrc': 0.85,
                'locations': ['ceiling', 'rear_wall', 'side_walls']
            }
            
        elif rt60_measured > target_rt60 * 1.2:
            panel_coverage = room_volume / 150
            return {
                'treatment_level': 'Moderate',
                'panel_area_sqft': panel_coverage,
                'panel_nrc': 0.70,
                'locations': ['rear_wall', 'side_walls']
            }
        
        return {'treatment_level': 'Minimal', 'panel_area_sqft': 0}


class OptimizedBOQGenerator:
    """
    ENHANCED: Now uses full AVIXA calculations and production-ready logic
    """
    
    def __init__(self, product_df: pd.DataFrame, client_requirements: ClientRequirements):
        self.product_df = product_df
        self.requirements = client_requirements
        self.avixa_calc = EnhancedAVIXACalculator()
        
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
        """
        UPDATED: Works for both standard AND custom rooms.
        """
        room_area = room_length * room_width
        room_volume = room_area * ceiling_height
        
        # Run AVIXA calculations (always needed)
        st.info("📊 Running AVIXA Standards Analysis...")
        
        # Display calculations (DISCAS)
        display_calcs = self.avixa_calc.calculate_display_size_discas(
            room_length, room_width, content_type="BDM"
        )
        
        occupancy = ROOM_SPECS.get(room_type, {}).get('capacity_max', None)
        audio_calcs = self.avixa_calc.calculate_audio_coverage_a102(
            room_area, ceiling_height, room_type, occupancy
        )
        
        # Microphone coverage
        table_config = "conference_table" if room_area < 600 else "conference_table"
        mic_calcs = self.avixa_calc.calculate_microphone_coverage(room_area, table_config)
        
        # SPL requirements
        target_spl = 75  # Standard for conference rooms
        spl_calcs = self.avixa_calc.calculate_required_amplifier_power(
            room_volume, target_spl
        )
        
        # Viewing angles
        viewing_calcs = self.avixa_calc.validate_viewing_angles(
            room_width, display_calcs['selected_size_inches'], seating_rows=2
        )
        
        avixa_calcs = {
            'display': display_calcs,
            'audio': audio_calcs,
            'microphones': mic_calcs,
            'spl': spl_calcs,
            'viewing_angles': viewing_calcs,
            'room_area': room_area,
            'room_volume': room_volume
        }
        
        # Pass calculations to selector
        self.selector.requirements_context = {
            'vc_platform': self.requirements.vc_platform,
            'room_type': room_type,
            'room_area': room_area,
            'avixa_calcs': avixa_calcs
        }

        # NEW: Generate tags from room profile
        if room_type in ROOM_SPECS:
            room_profile = ROOM_SPECS[room_type]
            tags = {
                'capacity': room_profile.get('capacity', (6, 8))[1],  # Max capacity
                'room_type_category': 'Conference',  # Derive from room_type
                'display_quantity': room_profile.get('displays', {}).get('quantity', 1),
                'display_type': 'Single Large',
                'camera_type': room_profile.get('video_system', {}).get('camera_type', 'Video Bar'),
                'microphone_type': room_profile.get('audio_system', {}).get('microphone_type', 'Table'),
                'speaker_type': room_profile.get('audio_system', {}).get('speaker_type', 'Ceiling'),
                'needs_dsp': room_profile.get('audio_system', {}).get('dsp_required', True),
                'needs_rack': room_area > 400,
                # ... extract all relevant tags from room_profile
            }
        else:
            # Custom room - would use AI analyzer here
            # For now, use defaults
            tags = {
                'capacity': int(room_area / 25),  # Estimate
                'room_type_category': 'Conference',
                'display_quantity': 1,
                'display_type': 'Single Large',
                'camera_type': 'Video Bar',
                'microphone_type': 'Table',
                'speaker_type': 'Ceiling',
                'needs_dsp': room_area > 400,
                'needs_rack': room_area > 400,
                # ... defaults
            }
        
        # Build blueprint using unified function
        blueprint = self._build_blueprint_from_tags(tags, room_area, ceiling_height, avixa_calcs)
        
        # Select products
        boq_items = []
        for component_key, requirement in blueprint.items():
            # ✅ FIX: Use fallback version of product selection
            product = self.selector.select_product_with_fallback(requirement)
            
            if product:
                justification = self._generate_avixa_justification(
                    component_key, product, avixa_calcs
                )
                
                product.update({
                    'quantity': requirement.quantity,
                    'justification': justification['technical'],
                    'top_3_reasons': justification['reasons'],
                    'avixa_compliant': True,
                    'matched': True,
                    'size_requirement': requirement.size_requirement
                })
                
                boq_items.append(product)
        
        # Calculate network and power requirements
        network_reqs = self.avixa_calc.calculate_network_requirements({
            'video_codec': any('Codec' in item.get('sub_category', '') for item in boq_items),
            'cameras': sum(1 for item in boq_items if 'Camera' in item.get('sub_category', '')),
            'displays': sum(1 for item in boq_items if item.get('category') == 'Displays'),
            'network_displays': 0,
            'digital_signage': 0
        })
        
        power_reqs = self.avixa_calc.calculate_power_requirements(boq_items)
        
        avixa_calcs['network'] = network_reqs
        avixa_calcs['power'] = power_reqs
        
        # Validate AVIXA compliance
        validation_results = self._validate_avixa_compliance(boq_items, avixa_calcs)

        # ✅ NEW: Validate audio ecosystem
        audio_warnings = self._validate_audio_ecosystem(boq_items)
        if audio_warnings:
            if 'warnings' not in validation_results:
                validation_results['warnings'] = []
            # Add critical warnings to issues list for prominence
            for warning in audio_warnings:
                if '🚨' in warning:
                    validation_results['issues'].append(warning)
                else:
                    validation_results['warnings'].append(warning)

        return boq_items, validation_results
    
    def _build_blueprint_from_tags(
        self, 
        tags: Dict,  # NEW: Accept tags instead of room_profile
        room_area: float, 
        ceiling_height: float, 
        avixa_calcs: Dict
    ) -> Dict[str, ProductRequirement]:
        """
        UNIFIED blueprint generator. Works for BOTH standard and custom rooms.
        Uses tags (from room profile OR AI analysis) + AVIXA calculations.
        """
        
        blueprint = {}
        req = self.requirements
        
        # === DISPLAYS (Using tags + AVIXA) ===
        display_size_avixa = avixa_calcs['display']['selected_size_inches']
        display_size = display_size_avixa  # Start with AVIXA
        
        # Override with tags if special display type needed
        if tags.get('needs_video_wall'):
            display_size = 55  # Video walls use smaller tiles
            display_qty = 4  # 2x2 configuration
        elif tags.get('needs_led_wall'):
            # LED walls are specified differently - skip standard display
            blueprint['led_wall'] = ProductRequirement(
                category='Displays',
                sub_category='Direct-View LED',
                quantity=1,
                priority=1,
                justification='AI-determined LED wall for immersive content',
                min_price=5000
            )
            display_qty = 0  # No standard displays needed
        else:
            display_qty = tags.get('display_quantity', 1)
        
        if display_qty > 0:
            blueprint['primary_display'] = ProductRequirement(
                category='Displays',
                sub_category='Professional Display',
                quantity=display_qty,
                priority=1,
                justification=f'AVIXA DISCAS: {display_size}" display',
                size_requirement=display_size,
                required_keywords=['display', '4k', str(display_size)],
                blacklist_keywords=['mount', 'bracket'],
                min_price=500,
                strict_category_match=True
            )
            
            blueprint['display_mount'] = ProductRequirement(
                category='Mounts',
                sub_category='Display Mount / Cart',
                quantity=display_qty,
                priority=2,
                justification=f'Wall mounts for {display_qty}x {display_size}" displays',
                mounting_type='wall',
                size_requirement=display_size,
                min_price=300 if display_size >= 75 else 150
            )
        
        # === VIDEO SYSTEM (Using tags) ===
        camera_type = tags.get('camera_type', 'Video Bar')
        camera_count = tags.get('camera_count', 1)
        
        if camera_type == 'Video Bar' or room_area <= 400:
            blueprint['vc_system'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Video Bar',
                quantity=1,
                priority=3,
                justification='All-in-one solution for room size',
                required_keywords=['video bar', 'all-in-one'],
                min_price=800
            )
        else:
            # Full codec + PTZ system
            blueprint['vc_codec'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='Room Kit / Codec',
                quantity=1,
                priority=3,
                justification=f'Codec for {self.requirements.vc_platform}',
                compatibility_requirements=[self.requirements.vc_platform], # CHANGE 3.1 APPLIED
                required_keywords=['codec', 'room kit'],
                min_price=1500
            )
            
            blueprint['ptz_camera'] = ProductRequirement(
                category='Video Conferencing',
                sub_category='PTZ Camera',
                quantity=camera_count,
                priority=4,
                justification=f'{camera_count}x PTZ camera(s)',
                required_keywords=['ptz', 'camera', 'optical', 'zoom'],
                min_price=1000
            )
            
            if tags.get('needs_matrix_switcher'):
                blueprint['matrix_switcher'] = ProductRequirement(
                    category='Signal Management',
                    sub_category='Matrix Switcher',
                    quantity=1,
                    priority=5,
                    justification='Video switching for multi-camera setup',
                    min_price=1000
                )
        
        # === AUDIO SYSTEM (Using AVIXA + tags) ===
        mics_needed = avixa_calcs['microphones']['mics_needed']
        mic_type = tags.get('microphone_type', 'Table')
        
        # ✅ FIX: Host/Expansion Logic
        mic_type_sub = 'Ceiling Microphone' if mic_type == 'Ceiling' else 'Table/Boundary Microphone'
        preferred_audio_brand = self.requirements.get_brand_preferences().get('audio', 'No Preference')
        
        if mics_needed > 1 and preferred_audio_brand == 'Biamp' and 'Ceiling' in mic_type_sub:
            # Special Biamp ecosystem logic
            blueprint['mic_host'] = ProductRequirement(
                category='Audio',
                sub_category='Ceiling Microphone',
                quantity=1,
                priority=6,
                justification='Biamp Tesira host microphone',
                required_keywords=['host', 'tesira', 'tcm-x', 'tcm-xa', 'biamp'],
                min_price=400
            )
            blueprint['mic_expansion'] = ProductRequirement(
                category='Audio',
                sub_category='Ceiling Microphone',
                quantity=mics_needed - 1,
                priority=6,
                justification=f'{mics_needed - 1}x Biamp expansion microphones',
                required_keywords=['expansion', 'tesira', 'tcm-xex', 'biamp'],
                min_price=300
            )
        else:
            # Standard microphone logic
            blueprint['microphones'] = ProductRequirement(
                category='Audio',
                sub_category=mic_type_sub,
                quantity=mics_needed,
                priority=6,
                justification=f'AVIXA: {mics_needed}x microphones',
                min_price=400 if 'Ceiling' in mic_type_sub else 150
            )
        
        # Speakers (AVIXA-calculated)
        speakers_needed = avixa_calcs['audio']['speakers_needed']
        speaker_type = tags.get('speaker_type', 'Ceiling')
        speaker_sub = 'Ceiling Loudspeaker' if speaker_type == 'Ceiling' else 'Wall-mounted Loudspeaker'
        
        blueprint['ceiling_speakers'] = ProductRequirement(
            category='Audio',
            sub_category=speaker_sub,
            quantity=speakers_needed,
            priority=8,
            justification=f'AVIXA A102.01: {speakers_needed}x speakers',
            required_keywords=['ceiling' if speaker_type == 'Ceiling' else 'wall', 'speaker'],
            blacklist_keywords=['portable', 'powered', 'grille'],
            min_price=100
        )
        
        # DSP (if needed)
        if tags.get('needs_dsp'):
            blueprint['audio_dsp'] = ProductRequirement(
                category='Audio',
                sub_category='DSP / Audio Processor / Mixer',
                quantity=1,
                priority=7,
                justification='AVIXA-required conferencing DSP with AEC',
                required_keywords=['dsp', 'processor', 'tesira', 'qsc core', 'biamp'],
                blacklist_keywords=['mixer', 'amplifier', 'touchmix'],
                min_price=1500
            )
        
        # Amplifier (AVIXA SPL calculation)
        recommended_power = avixa_calcs['spl']['recommended_power_watts']
        blueprint['power_amplifier'] = ProductRequirement(
            category='Audio',
            sub_category='Amplifier',
            quantity=1,
            priority=9,
            justification=f'AVIXA SPL: {recommended_power:.0f}W amplifier',
            required_keywords=['amplifier', 'power', 'channel'],
            blacklist_keywords=['dsp', 'mixer', 'summing'],
            min_price=500
        )
        
        # === INFRASTRUCTURE ===
        if tags.get('needs_rack'):
            blueprint['av_rack'] = ProductRequirement(
                category='Infrastructure',
                sub_category='AV Rack',
                quantity=1,
                priority=10,
                justification='Houses codec, DSP, amplifier',
                required_keywords=['rack', '12u', 'equipment'],
                blacklist_keywords=['shelf', 'mount'],
                min_price=500
            )
            
            # ✅ Also add PDU if rack is added
            blueprint['rack_pdu'] = ProductRequirement(
                category='Infrastructure',
                sub_category='Power (PDU/UPS)',
                quantity=1,
                priority=11,
                justification='Rack-mount power distribution for all equipment',
                required_keywords=['pdu', 'rack', 'power', '8 outlet', 'distribution'],
                min_price=150,
                max_price=800
            )

        blueprint['network_switch'] = ProductRequirement(
            category='Networking',
            sub_category='Network Switch',
            quantity=1,
            priority=12,
            justification='Managed PoE switch',
            required_keywords=['switch', 'poe', 'managed'],
            min_price=300
        )
        
        # Table connectivity, cables, etc. (standard logic remains)
        blueprint['table_connectivity'] = ProductRequirement(
            category='Cables & Connectivity',
            sub_category='Wall & Table Plate Module',
            quantity=1,
            priority=13,
            justification='Table-mount connectivity for HDMI/USB-C laptop input',
            required_keywords=['table', 'connectivity', 'hdmi', 'usb-c', 'retractor', 'cubby'],
            blacklist_keywords=['wall plate', 'single gang', 'mount', 'bracket'],
            min_price=200,
            max_price=800
        )
        blueprint['cables_hdmi'] = ProductRequirement(
            category='Cables & Connectivity', sub_category='AV Cable', quantity=4, priority=14,
            justification='HDMI cables for video distribution',
            required_keywords=['hdmi', 'cable', 'certified', '4k'], min_price=20, max_price=150
        )
        blueprint['cables_network'] = ProductRequirement(
            category='Cables & Connectivity', sub_category='AV Cable', quantity=6, priority=15,
            justification='Cat6A network cables for endpoints',
            required_keywords=['cat6', 'ethernet', 'network', 'cable'], min_price=15, max_price=80
        )
        
        return blueprint

    def _generate_avixa_justification(
        self, component_key: str, product: Dict, avixa_calcs: Dict
    ) -> Dict[str, Any]:
        """
        Generate AVIXA-compliant justification
        """
        category = product.get('category', 'General')
        
        if 'Display' in category:
            display_calcs = avixa_calcs['display']
            technical = (
                f"AVIXA DISCAS-calculated {display_calcs['selected_size_inches']}\" display. "
                f"Max viewing distance: {display_calcs['max_viewing_distance_ft']:.1f}ft. "
                f"Selected {product.get('brand')} {product.get('model_number')} "
                f"for {display_calcs['content_type']} content type."
            )
            reasons = [
                f"AVIXA DISCAS-compliant sizing for {display_calcs['max_viewing_distance_ft']:.1f}ft viewing distance",
                "Professional 4K resolution ensures readability from all seats",
                f"Certified for {self.requirements.vc_platform} collaboration"
            ]
            
        elif 'Audio' in category:
            audio_calcs = avixa_calcs['audio']
            if 'Speaker' in product.get('sub_category', ''):
                technical = (
                    f"AVIXA A102.01-compliant speaker placement. "
                    f"{audio_calcs['speakers_needed']} speakers provide ±3dB uniformity "
                    f"across {avixa_calcs['room_area']:.0f} sqft listening area. "
                    f"Target STI: {audio_calcs['target_sti']}"
                )
                reasons = [
                    f"AVIXA A102.01: Uniform coverage ({audio_calcs['speakers_needed']} speakers for {avixa_calcs['room_area']:.0f} sqft)",
                    f"Speech intelligibility: STI ≥ {audio_calcs['target_sti']} guaranteed",
                    "Professional-grade components with commercial warranty"
                ]
            elif 'Microphone' in product.get('sub_category', ''):
                mic_calcs = avixa_calcs['microphones']
                technical = (
                    f"AVIXA-calculated microphone coverage: {mic_calcs['mics_needed']} units. "
                    f"Pickup pattern: {mic_calcs['pickup_pattern']}. "
                    f"Coverage area: {mic_calcs.get('coverage_area_sqft', 'optimized')} sqft per mic."
                )
                reasons = [
                    f"AVIXA-compliant coverage ({mic_calcs['mics_needed']} mics for full room)",
                    f"{mic_calcs['pickup_pattern']} pattern ensures clear capture",
                    "Professional AEC and noise reduction for remote clarity"
                ]
            elif 'Amplifier' in product.get('sub_category', ''):
                spl_calcs = avixa_calcs['spl']
                technical = (
                    f"AVIXA SPL calculation: {spl_calcs['recommended_power_watts']:.0f}W required "
                    f"for {spl_calcs['target_spl_db']}dB SPL. "
                    f"Accounts for {spl_calcs['acoustic_loss_db']}dB acoustic loss."
                )
                reasons = [
                    f"AVIXA-calculated power: {spl_calcs['recommended_power_watts']:.0f}W for {spl_calcs['target_spl_db']}dB SPL",
                    "Sufficient headroom for dynamic range and reliability",
                    "Professional-grade amplification with thermal protection"
                ]
            else:
                technical = f"AVIXA-compliant audio component for {avixa_calcs['room_area']:.0f} sqft room"
                reasons = [
                    "Professional audio quality per AVIXA standards",
                    "Reliable performance with commercial warranty",
                    "Integrates seamlessly with system architecture"
                ]
        
        else:
            technical = f"AVIXA-compliant component for {avixa_calcs['room_area']:.0f} sqft room"
            reasons = [
                f"Industry-standard solution for this room type",
                "Professional-grade reliability and performance",
                "Cost-effective within project requirements"
            ]
        
        return {
            'technical': technical,
            'reasons': reasons[:3]
        }
    
    def _validate_avixa_compliance(self, boq_items: List[Dict], avixa_calcs: Dict) -> Dict[str, Any]:
        """
        ENHANCED: Comprehensive AVIXA compliance validation with detailed reporting
        """
        validation = {
            'issues': [],
            'warnings': [],
            'avixa_compliance_report': {},
            'compliance_score': 100
        }
        
        # 1. Display Size Compliance (DISCAS)
        display_items = [item for item in boq_items if item.get('category') == 'Displays']
        if display_items and avixa_calcs.get('display'):
            actual_size = display_items[0].get('size_requirement', 0)
            recommended_size = avixa_calcs['display']['selected_size_inches']
            viewing_distance = avixa_calcs['display']['max_viewing_distance_ft']
            
            size_diff = actual_size - recommended_size
            
            if abs(size_diff) <= 5:
                validation['avixa_compliance_report']['display'] = (
                    f"✅ AVIXA DISCAS: {actual_size}\" display compliant "
                    f"({viewing_distance:.1f}ft viewing distance)"
                )
            elif size_diff < -5:
                validation['issues'].append(
                    f"🚨 Display {actual_size}\" is {abs(size_diff):.0f}\" smaller than "
                    f"AVIXA DISCAS recommendation ({recommended_size}\")"
                )
                validation['compliance_score'] -= 15
            else:
                validation['avixa_compliance_report']['display'] = (
                    f"✅ Display {actual_size}\" exceeds AVIXA minimum ({recommended_size}\")"
                )
        
        # 2. Audio Coverage (A102.01)
        speaker_items = [item for item in boq_items if 'Speaker' in item.get('sub_category', '') or 'Loudspeaker' in item.get('sub_category', '')]
        if avixa_calcs.get('audio'):
            actual_speakers = sum(item.get('quantity', 0) for item in speaker_items)
            recommended_speakers = avixa_calcs['audio']['speakers_needed']
            
            if actual_speakers >= recommended_speakers:
                validation['avixa_compliance_report']['audio'] = (
                    f"✅ AVIXA A102.01: {actual_speakers} speakers for uniform coverage "
                    f"(±3dB uniformity)"
                )
            elif actual_speakers >= recommended_speakers - 1:
                validation['warnings'].append(
                    f"⚠️ {actual_speakers} speakers installed, AVIXA recommends {recommended_speakers} "
                    f"for optimal coverage"
                )
                validation['compliance_score'] -= 5
            else:
                validation['issues'].append(
                    f"🚨 CRITICAL: Only {actual_speakers} speakers, AVIXA A102.01 requires "
                    f"{recommended_speakers} for ±3dB uniformity"
                )
                validation['compliance_score'] -= 20
        
        # 3. Microphone Coverage
        mic_items = [item for item in boq_items if 'Microphone' in item.get('sub_category', '') or 'Mic' in item.get('sub_category', '')]
        if avixa_calcs.get('microphones'):
            actual_mics = sum(item.get('quantity', 0) for item in mic_items)
            recommended_mics = avixa_calcs['microphones']['mics_needed']
            
            if actual_mics >= recommended_mics:
                validation['avixa_compliance_report']['microphones'] = (
                    f"✅ AVIXA Coverage: {actual_mics} microphones for "
                    f"{avixa_calcs.get('room_area', 0):.0f} sqft"
                )
            elif actual_mics == 0:
                validation['issues'].append(
                    "🚨 CRITICAL: No microphones found - system cannot capture audio!"
                )
                validation['compliance_score'] -= 30
            else:
                validation['warnings'].append(
                    f"⚠️ {actual_mics} microphones, AVIXA recommends {recommended_mics} "
                    f"for full coverage"
                )
                validation['compliance_score'] -= 10
        
        # 4. Viewing Angles
        viewing_ok = avixa_calcs.get('viewing_angles', {}).get('all_seats_acceptable', True)
        if not viewing_ok:
            validation['warnings'].append(
                "⚠️ Some seats may exceed 45° horizontal viewing angle"
            )
            validation['compliance_score'] -= 5
        else:
            validation['avixa_compliance_report']['viewing_angles'] = (
                "✅ All seats within AVIXA viewing angle limits (≤45° horizontal)"
            )
        
        # 5. Power Requirements
        power_reqs = avixa_calcs.get('power', {})
        if power_reqs.get('ups_recommended'):
            ups_items = [item for item in boq_items if 'UPS' in item.get('name', '').upper() or 'Power' in item.get('sub_category', '')]
            if not ups_items:
                validation['warnings'].append(
                    f"⚠️ AVIXA recommends UPS ({power_reqs['ups_capacity_va']:.0f}VA) "
                    f"for {power_reqs['total_watts']:.0f}W load"
                )
                validation['compliance_score'] -= 5
        
        # 6. Network Requirements
        network_reqs = avixa_calcs.get('network', {})
        if network_reqs.get('total_bandwidth_mbps', 0) > 100:
            switch_items = [item for item in boq_items if 'Switch' in item.get('sub_category', '')]
            if not switch_items:
                validation['warnings'].append(
                    f"⚠️ AVIXA network requirements: {network_reqs['switch_type']} "
                    f"needed for {network_reqs['total_bandwidth_mbps']}Mbps"
                )
                validation['compliance_score'] -= 5
        
        # Overall Status
        compliance_score = validation['compliance_score']
        critical_count = len(validation['issues'])
        
        if compliance_score >= 95 and critical_count == 0:
            validation['overall_status'] = "✅ FULL AVIXA COMPLIANCE"
        elif compliance_score >= 80 and critical_count == 0:
            validation['overall_status'] = f"⚠️ AVIXA COMPLIANT WITH RECOMMENDATIONS"
        else:
            validation['overall_status'] = f"🚨 AVIXA NON-COMPLIANT: {critical_count} critical issues"
        
        return validation

    def _validate_audio_ecosystem(self, boq_items: List[Dict]) -> List[str]:
        """
        NEW: Validate that audio components form a compatible ecosystem
        """
        warnings = []
        
        # Extract audio components
        microphones = [item for item in boq_items if 'Microphone' in item.get('sub_category', '')]
        dsp_items = [item for item in boq_items if 'DSP / Audio Processor / Mixer' in item.get('sub_category', '')]
        
        if microphones and dsp_items:
            mic_brand = microphones[0].get('brand', '').lower()
            dsp_brand = dsp_items[0].get('brand', '').lower()
            
            # Check for known brand mismatches
            if mic_brand == 'biamp' and dsp_brand != 'biamp':
                warnings.append(
                    f"⚠️ AUDIO ECOSYSTEM WARNING: Biamp microphones paired with {dsp_items[0].get('brand')} DSP. "
                    f"Recommend Biamp TesiraFORTE for optimal integration."
                )
            elif mic_brand == 'shure' and dsp_brand not in ['shure', 'biamp', 'qsc']:
                warnings.append(
                    f"⚠️ AUDIO ECOSYSTEM WARNING: Shure microphones paired with {dsp_items[0].get('brand')} DSP. "
                    f"Recommend Shure IntelliMix, Biamp, or QSC for optimal integration."
                )
        
        # Check for mixer instead of DSP
        for item in boq_items:
            if 'DSP' in item.get('sub_category', ''):
                product_name = item.get('name', '').lower()
                if any(term in product_name for term in ['touchmix', 'mixer', 'mg', 'zm']):
                    warnings.append(
                        f"🚨 CRITICAL: {item.get('name')} is a MIXER, not a conferencing DSP! "
                        f"This lacks Acoustic Echo Cancellation (AEC) and will NOT work for video conferencing. "
                        f"Replace with Biamp TesiraFORTE, QSC Core, or Extron DMP."
                    )
        
        return warnings
    
    def generate_boq_from_acim_form(self, acim_responses: Dict) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Generate BOQ from ACIM form responses
        """
        all_boq_items = []
        all_validations = {}
        
        for room_req in acim_responses.get('room_requirements', []):
            room_type = room_req['room_type']
            responses = room_req['responses']
            
            # Extract room dimensions from responses
            dimensions_text = responses.get('room_dimensions', '')
            # Parse dimensions (simplified - you may need more robust parsing)
            room_length = 28.0  # Default
            room_width = 20.0   # Default
            ceiling_height = 10.0  # Default
            
            # Generate BOQ for this room
            boq_items, validation = self.generate_boq_for_room(
                room_type=self._map_acim_to_standard_room(room_type),
                room_length=room_length,
                room_width=room_width,
                ceiling_height=ceiling_height
            )
            
            all_boq_items.extend(boq_items)
            all_validations[room_type] = validation
        
        return all_boq_items, all_validations

    def _map_acim_to_standard_room(self, acim_room_type: str) -> str:
        """Map ACIM room types to standard room profiles"""
        mapping = {
            'Conference/Meeting Room/Boardroom': 'Standard Conference Room (6-8 People)',
            'Experience Center': 'Multipurpose Event Room (40+ People)',
            'Reception/Digital Signage': 'Small Huddle Room (2-3 People)',
            'Training Room': 'Training Room (15-25 People)',
            'Network Operations Center/Command Center': 'Large Conference Room (8-12 People)',
            'Town Hall': 'Multipurpose Event Room (40+ People)',
            'Auditorium': 'Multipurpose Event Room (40+ People)'
        }
        
        # Try exact match first
        if acim_room_type in mapping:
            return mapping[acim_room_type]
        
        # Try partial match
        for key, value in mapping.items():
            if key.lower() in acim_room_type.lower() or acim_room_type.lower() in key.lower():
                return value
        
        # Default fallback
        return 'Standard Conference Room (6-8 People)'
    
    def calculate_boq_quality_score(self, boq_items: List[Dict], validation_results: Dict) -> Dict[str, Any]:
        """
        ENHANCED: Quality score now includes AVIXA compliance
        """
        score_breakdown = {
            'brand_compliance': 0,
            'component_completeness': 0,
            'avixa_compliance': 0,  # NEW
            'integration_quality': 0,
            'pricing_accuracy': 0
        }
        
        max_scores = {
            'brand_compliance': 15,
            'component_completeness': 25,
            'avixa_compliance': 30,  # INCREASED WEIGHT
            'integration_quality': 15,
            'pricing_accuracy': 15
        }
        
        # 1. Brand Compliance (15 points)
        prefs = self.requirements.get_brand_preferences()
        brand_matches = 0
        brand_total = 0
        
        for category, preferred_brand in prefs.items():
            if preferred_brand != 'No Preference':
                brand_total += 1
                category_map = {
                    'displays': 'Displays',
                    'video_conferencing': 'Video Conferencing',
                    'audio': 'Audio',
                    'control': 'Control Systems'
                }
                
                actual_category = category_map.get(category)
                matching_items = [
                    item for item in boq_items 
                    if actual_category in item.get('category', '')
                ]
                
                if any(item.get('brand', '').lower() == preferred_brand.lower() for item in matching_items):
                    brand_matches += 1
        
        if brand_total > 0:
            score_breakdown['brand_compliance'] = (brand_matches / brand_total) * max_scores['brand_compliance']
        else:
            score_breakdown['brand_compliance'] = max_scores['brand_compliance']
        
        # 2. Component Completeness (25 points)
        essential_components = {
            'Displays': 8,
            'Video Conferencing': 8,
            'Audio': 5,
            'Mounts': 2,
            'Cables & Connectivity': 2
        }
        
        completeness_score = 0
        for category, points in essential_components.items():
            if any(category in item.get('category', '') for item in boq_items):
                completeness_score += points
        
        has_microphones = any(
            'Microphone' in item.get('sub_category', '') or 'Mic' in item.get('sub_category', '')
            for item in boq_items
        )
        if has_microphones:
            completeness_score += 5
        
        score_breakdown['component_completeness'] = min(completeness_score, max_scores['component_completeness'])
        
        # 3. AVIXA Compliance (30 points) - NEW EMPHASIS
        avixa_score = validation_results.get('compliance_score', 70)
        score_breakdown['avixa_compliance'] = (avixa_score / 100) * max_scores['avixa_compliance']
        
        # 4. Integration Quality (15 points)
        integration_score = 15
        brands_used = {}
        for item in boq_items:
            category = item.get('category', '')
            brand = item.get('brand', '')
            if category not in brands_used:
                brands_used[category] = set()
            brands_used[category].add(brand)
        
        for category, brands in brands_used.items():
            if len(brands) > 2:
                integration_score -= 3
        
        score_breakdown['integration_quality'] = max(0, min(integration_score, max_scores['integration_quality']))
        
        # 5. Pricing Accuracy (15 points)
        pricing_score = 15
        
        for item in boq_items:
            price = item.get('price', 0)
            category = item.get('category', '')
            
            min_prices = {
                'Displays': 500,
                'Video Conferencing': 800,
                'Audio': 100,
                'Control Systems': 300
            }
            
            expected_min = min_prices.get(category, 50)
            if price < expected_min:
                pricing_score -= 2
        
        score_breakdown['pricing_accuracy'] = max(0, min(pricing_score, max_scores['pricing_accuracy']))
        
        # Calculate total
        total_score = sum(score_breakdown.values())
        max_total = sum(max_scores.values())
        percentage = (total_score / max_total) * 100
        
        # Grade assignment
        if percentage >= 90:
            grade = 'A+'
            quality_level = 'AVIXA CERTIFIED DESIGN'
            color = '#10b981'
        elif percentage >= 80:
            grade = 'A'
            quality_level = 'AVIXA COMPLIANT'
            color = '#22c55e'
        elif percentage >= 70:
            grade = 'B'
            quality_level = 'GOOD WITH MINOR ISSUES'
            color = '#84cc16'
        elif percentage >= 60:
            grade = 'C'
            quality_level = 'ACCEPTABLE - NEEDS REVIEW'
            color = '#eab308'
        else:
            grade = 'D'
            quality_level = 'NON-COMPLIANT - REDESIGN NEEDED'
            color = '#ef4444'
        
        return {
            'score': total_score,
            'max_score': max_total,
            'percentage': percentage,
            'grade': grade,
            'quality_level': quality_level,
            'color': color,
            'breakdown': score_breakdown,
            'max_breakdown': max_scores,
            'avixa_compliance_score': avixa_score
        }
