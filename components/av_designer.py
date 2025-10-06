# components/av_designer.py

import streamlit as st
from components.utils import estimate_power_draw
from components.room_profiles import ROOM_SPECS

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    """
    Calculate AVIXA-based recommendations for display size and audio coverage
    """
    if length == 0 or width == 0:
        return {}
    
    area = length * width
    farthest_viewer = length * 0.9
    
    # Define size constraints for different room types
    SIZE_CONSTRAINTS = {
        "Small Huddle": (43, 55),
        "Medium Huddle": (55, 65),
        "Standard Conference": (65, 75),
        "Large Conference": (75, 85),
        "Boardroom": (85, 98)
    }
    
    # Use different ratios for different viewing needs
    if any(s in room_type for s in ["Huddle", "Conference", "Boardroom", "Telepresence"]):
        display_height_ft = farthest_viewer / 4  # Detailed viewing
    else: 
        display_height_ft = farthest_viewer / 6  # Basic viewing

    # Assuming 16:9, diagonal is approx 2.22x height
    recommended_size = display_height_ft * 12 * 2.22

    # Apply constraints based on room type
    for key, (min_size, max_size) in SIZE_CONSTRAINTS.items():
        if key in room_type:
            recommended_size = max(min_size, min(recommended_size, max_size))
            break

    def snap_to_standard_size(size_inches):
        sizes = [43, 55, 65, 75, 85, 98]
        return min(sizes, key=lambda x: abs(x - size_inches))

    final_size = snap_to_standard_size(recommended_size)
    
    # Calculate speaker coverage (1 speaker per 200 sq ft)
    speakers_needed = max(2, int(area / 200) + 1)
    
    # Calculate microphone coverage (1 mic per 150 sq ft)
    mic_count = max(2, int(area / 150))
    
    return {
        "recommended_display_size_inches": final_size,
        "speakers_needed_for_coverage": speakers_needed,
        "microphones_needed": mic_count
    }


def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """
    Determine complete equipment requirements based on room profile and calculations
    """
    # Get base profile
    profile = ROOM_SPECS.get(room_type, ROOM_SPECS["Standard Conference Room (6-8 People)"])
    
    # Deep copy the profile to avoid modifying the original
    equipment = {k: (v.copy() if isinstance(v, dict) else v) for k, v in profile.items()}

    # Update display size based on AVIXA calculations
    if 'displays' in equipment:
        equipment['displays']['size_inches'] = avixa_calcs.get('recommended_display_size_inches', 65)
    
    # Update audio system counts
    if 'audio_system' in equipment:
        equipment['audio_system']['speaker_count'] = avixa_calcs.get('speakers_needed_for_coverage', 2)
        equipment['audio_system']['microphone_count'] = avixa_calcs.get('microphones_needed', 2)

    # Process user-specified features
    user_features = technical_reqs.get('features', '').lower()
    
    # Handle dual display request
    if 'dual display' in user_features and 'displays' in equipment:
        equipment['displays']['quantity'] = 2
    
    # Handle wireless presentation requirement
    if any(term in user_features for term in ['wireless presentation', 'content sharing', 'byod']):
        if 'content_sharing' not in equipment:
            equipment['content_sharing'] = {'type': 'Wireless Presentation System'}
    
    # Handle voice reinforcement for training rooms
    if 'voice reinforcement' in user_features or 'voice lift' in user_features:
        if 'audio_system' in equipment:
            equipment['audio_system']['type'] = 'Voice Reinforcement System'
            equipment['audio_system']['dsp_required'] = True
    
    # Handle recording requirements
    if 'recording' in user_features or 'lecture capture' in user_features:
        equipment['recording_system'] = {'type': 'Lecture Capture / Recording System'}
    
    # Handle accessibility features
    if 'hearing loop' in user_features or 'assistive listening' in user_features:
        equipment['accessibility'] = {'type': 'Assistive Listening System'}
    
    return equipment
