# components/av_designer.py

import streamlit as st
from components.utils import estimate_power_draw

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    """Calculates AVIXA-based room recommendations."""
    if length == 0 or width == 0:
        return {}
    area = length * width
    
    # DISCAS Calculations
    farthest_viewer = length * 0.9
    basic_display_height = farthest_viewer / 6
    detailed_viewing_display_size = basic_display_height * 1.15 * 1.25 * 10 # Heuristic conversion to inches
    
    # Audio Calculations - More nuanced speaker count
    if area <= 250:
        speakers_needed = 2
    elif area <= 500:
        speakers_needed = 4
    else:
        speakers_needed = 6

    return {
        "farthest_viewer_distance": farthest_viewer,
        "basic_viewing_display_size": int(basic_display_height * 1.25 * 10),
        "detailed_viewing_display_size": int(detailed_viewing_display_size),
        "estimated_occupancy": int(area / 20),
        "speakers_needed_for_coverage": speakers_needed
    }

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """
    -- UPGRADED FOR SMARTER BOQ --
    Determines the specific types and sub-types of equipment needed.
    """
    equipment = {
        'displays': {'quantity': 1, 'size_inches': avixa_calcs.get('detailed_viewing_display_size', 55), 'sub_category': 'Professional Display'},
        'audio_system': {
            'primary_category': 'Audio', 'sub_category': 'Loudspeaker', 'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 2),
            'microphone_type': 'Table Microphone', 'microphone_count': 1, 'dsp_required': False
        },
        'video_system': {'primary_category': 'Video Conferencing', 'sub_category': 'Video Bar', 'camera_count': 1},
        'control_system': {'primary_category': 'Control Systems', 'sub_category': 'Touch Panel'},
        'connectivity': {'primary_category': 'Cables & Connectivity', 'sub_category': 'Wireless Presentation'},
        'housing': {'primary_category': 'Infrastructure', 'sub_category': 'AV Rack'},
        'power': {'primary_category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)'}
    }

    # Room Type Specific Logic
    if room_type == 'Huddle Room':
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 55)
        equipment['video_system']['sub_category'] = 'Video Bar' # All-in-one is perfect
        equipment['housing'] = None # Typically no rack in a huddle
    
    elif room_type == 'Standard Conference Room':
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 75)
        equipment['audio_system']['microphone_type'] = 'Ceiling Microphone'
        equipment['audio_system']['microphone_count'] = 1
        equipment['audio_system']['dsp_required'] = True
        equipment['video_system']['sub_category'] = 'PTZ Camera'

    elif room_type == 'Large Conference Room' or room_type == 'Boardroom':
        equipment['displays']['quantity'] = 2 if "Dual Display" in technical_reqs.get('features', '') else 1
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 86)
        equipment['audio_system']['microphone_type'] = 'Ceiling Microphone'
        equipment['audio_system']['microphone_count'] = 2
        equipment['audio_system']['dsp_required'] = True
        equipment['video_system']['sub_category'] = 'PTZ Camera'
        equipment['video_system']['camera_count'] = 2 # One for presenter, one for audience

    elif room_type == 'Training Room' or room_type == 'Classroom':
        equipment['displays']['sub_category'] = 'Interactive Display' # Key for training
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 86)
        equipment['audio_system']['microphone_type'] = 'Wireless Microphone System'
        equipment['video_system']['sub_category'] = 'PTZ Camera'

    # Override based on specific user requests
    if technical_reqs.get('audio_requirements') == 'Voice Lift':
        equipment['audio_system']['sub_category'] = 'Loudspeaker'
        equipment['audio_system']['dsp_required'] = True
    
    if "Interactive" in technical_reqs.get('features', ''):
        equipment['displays']['sub_category'] = 'Interactive Display'

    return equipment
