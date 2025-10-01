import streamlit as st
from components.utils import estimate_power_draw
import math

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    """
    Calculates AVIXA-based room recommendations with corrected and enhanced logic.
    """
    if length <= 0 or width <= 0:
        return {}

    area = length * width

    # --- 1. IMPROVED: Determine Farthest Viewer Distance ---
    # Use the longest dimension of the room for a more robust calculation.
    # The 0.85 multiplier is from your avixa_guidelines.md
    farthest_viewer = max(length, width) * 0.85

    # --- 2. CORRECTED: AVIXA DISCAS Formulas ---
    # Formulas are now correctly applied as per the guidelines.
    detailed_viewing_height_ft = farthest_viewer / 6
    basic_viewing_height_ft = farthest_viewer / 4

    # --- 3. IMPROVED: Clear Height-to-Diagonal Conversion ---
    # Convert height in feet to diagonal in inches for a 16:9 display.
    # Formula: diagonal_inches = (height_ft * 12) / 0.49
    def get_diagonal_inches(height_in_feet):
        if height_in_feet == 0:
            return 0
        # The screen height of a 16:9 display is approx. 49% of its diagonal.
        return (height_in_feet * 12) / 0.49

    detailed_diagonal_size = get_diagonal_inches(detailed_viewing_height_ft)
    basic_diagonal_size = get_diagonal_inches(basic_viewing_height_ft)

    # --- 4. ENHANCED: Audio Calculation ---
    # Incorporate ceiling height for a slightly more advanced estimate.
    # Higher ceilings may require more speakers for even coverage.
    if ceiling_height > 12:
        # For high ceilings, reduce the effective area coverage per speaker.
        area_divisor = 150
    else:
        area_divisor = 200
    speakers_needed = max(2, math.ceil(area / area_divisor))

    # --- 5. NEW: Select Primary Display Size based on Room Type ---
    # Default to detailed viewing for critical spaces.
    if any(keyword in room_type for keyword in ["Boardroom", "Training", "Conference"]):
        primary_display_size = detailed_diagonal_size
    else:
        primary_display_size = basic_diagonal_size

    return {
        "farthest_viewer_distance": farthest_viewer,
        "recommended_display_size_inches": int(primary_display_size),
        "basic_viewing_display_size_inches": int(basic_diagonal_size),
        "detailed_viewing_display_size_inches": int(detailed_diagonal_size),
        "estimated_occupancy": int(area / 20), # 20 sq ft per person
        "speakers_needed_for_coverage": speakers_needed
    }


def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """
    Determines the specific types of equipment needed based on AVIXA calcs and room type.
    UPDATED to use the new output from calculate_avixa_recommendations.
    """
    # Default values
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

    # Refine based on room type and complexity
    if "Huddle" in room_type:
        # UPDATED KEY:
        equipment['displays']['size_inches'] = avixa_calcs.get('recommended_display_size_inches', 65)

    elif any(keyword in room_type for keyword in ["Boardroom", "Large", "Training"]):
        equipment['displays']['quantity'] = 2 if "Dual Display" in technical_reqs.get('features', '') else 1
        # UPDATED KEY:
        equipment['displays']['size_inches'] = avixa_calcs.get('recommended_display_size_inches', 85)
        equipment['audio_system'] = {
            'type': 'Integrated Ceiling Audio',
            'microphone_type': 'Ceiling Mic Array',
            'speaker_type': 'Ceiling Speakers',
            'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 4),
            'dsp_required': True
        }
        equipment['video_system'] = {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'Optical Zoom PTZ', 'camera_count': 1}
        # NEW: Specify rack and PDU for complex rooms
        equipment['housing'] = {'type': 'AV Rack'}
        equipment['power_management'] = {'type': 'Rackmount PDU'}

    # Further refinement based on tech reqs
    if technical_reqs.get('audio_requirements') == 'Voice Lift':
        equipment['audio_system']['type'] = 'Voice Reinforcement System'
        equipment['audio_system']['dsp_required'] = True

    return equipment
