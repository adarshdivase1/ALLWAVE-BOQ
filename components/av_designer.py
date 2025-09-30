import streamlit as st
from components.utils import estimate_power_draw

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    """Calculates AVIXA-based room recommendations."""
    if length == 0 or width == 0:
        return {}
    area = length * width
    
    # DISCAS Calculations (simplified model for screen height)
    farthest_viewer = length * 0.9
    # For detailed viewing (e.g., spreadsheets), screen height should be at least 1/6th of the distance.
    basic_display_height_ft = farthest_viewer / 6 
    
    # Convert display height to a 16:9 diagonal in inches
    # Diagonal = Height * sqrt( (16/9)^2 + 1^2 ) -- simplified heuristic is ~2x height
    basic_display_diagonal_in = basic_display_height_ft * 12 * 2.2 

    # For inspection viewing (e.g., medical imaging), ratio is 1/4
    detailed_display_height_ft = farthest_viewer / 4
    detailed_display_diagonal_in = detailed_display_height_ft * 12 * 2.2

    # Audio Calculations
    # A simple rule of thumb: one speaker per 200 sq ft after the first one.
    speakers_needed = max(2, int(area / 200) + 1)
    
    return {
        "farthest_viewer_distance": round(farthest_viewer, 1),
        "basic_viewing_display_size": int(basic_display_diagonal_in),
        "detailed_viewing_display_size": int(detailed_display_diagonal_in),
        "estimated_occupancy": int(area / 20), # Standard estimate for occupancy
        "speakers_needed_for_coverage": speakers_needed
    }

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """Determines the specific types of equipment needed based on AVIXA calcs and room type."""
    # Default values for a standard medium conference room
    equipment = {
        'displays': {'quantity': 1, 'size_inches': 75, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Integrated', 'microphone_type': 'Beamforming', 'speaker_type': 'Integrated', 'dsp_required': False},
        'video_system': {'type': 'All-in-one Video Bar', 'camera_type': 'ePTZ 4K', 'camera_count': 1},
        'control_system': {'type': 'Touch Panel'},
        # NEW: Adding holistic system requirements
        'user_interface': {'type': 'Touch Panel Controller'},
        'housing': {'type': 'Wall Mount Solution'},
        'power_management': {'type': 'Basic Surge Protection'},
        'content_sharing': {'type': 'Wireless & Wired HDMI'}
    }

    # Refine based on room type and complexity using AVIXA calculations
    if "Huddle" in room_type or "Small" in room_type:
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 65)
    
    elif any(keyword in room_type for keyword in ["Boardroom", "Large", "Training", "Auditorium"]):
        equipment['displays']['quantity'] = 2 if "Dual Display" in technical_reqs.get('features', '') else 1
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 85)
        equipment['audio_system'] = {
            'type': 'Integrated Ceiling Audio', 
            'microphone_type': 'Ceiling Mic Array', 
            'speaker_type': 'Ceiling Speakers', 
            'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 4),
            'dsp_required': True
        }
        equipment['video_system'] = {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'Optical Zoom PTZ', 'camera_count': 1}
        # Specify rack and PDU for these more complex rooms
        equipment['housing'] = {'type': 'AV Rack'}
        equipment['power_management'] = {'type': 'Rackmount PDU'}

    # Further refinement based on specific technical requirements
    if technical_reqs.get('audio_requirements') == 'Voice Lift':
        equipment['audio_system']['type'] = 'Voice Reinforcement System'
        equipment['audio_system']['dsp_required'] = True
        # A voice lift system would typically need more speakers
        equipment['audio_system']['speaker_count'] = avixa_calcs.get('speakers_needed_for_coverage', 4) * 2

    return equipment
