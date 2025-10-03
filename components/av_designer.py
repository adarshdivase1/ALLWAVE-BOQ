# components/av_designer.py

import streamlit as st
from components.utils import estimate_power_draw
from components.room_profiles import ROOM_SPECS # Import from the new central file

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    if length == 0 or width == 0: return {}
    area = length * width
    farthest_viewer = length * 0.9
    
    # Use different ratios for different viewing needs
    if any(s in room_type for s in ["Huddle", "Conference", "Boardroom", "Telepresence"]):
        # Detailed viewing (4:1 ratio)
        display_height_ft = farthest_viewer / 4
    else: 
        # Basic viewing (6:1 ratio) for training/presentation
        display_height_ft = farthest_viewer / 6

    # Assuming 16:9, diagonal is approx 2.22x height
    recommended_size = display_height_ft * 12 * 2.22

    def snap_to_standard_size(size_inches):
        sizes = [55, 65, 75, 85, 98]
        return min(sizes, key=lambda x: abs(x - size_inches))

    final_size = snap_to_standard_size(recommended_size)
    speakers_needed = max(2, int(area / 200) + 1)
    
    return {
        "recommended_display_size_inches": final_size,
        "speakers_needed_for_coverage": speakers_needed
    }

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    # Use a fallback to a standard conference room if the type is unknown
    profile = ROOM_SPECS.get(room_type, ROOM_SPECS["Standard Conference Room (6-8 People)"])
    
    # Create a deep copy to avoid modifying the original dictionary
    equipment = {k: (v.copy() if isinstance(v, dict) else v) for k, v in profile.items()}

    # Dynamically adjust parameters from the profile
    if 'displays' in equipment:
        equipment['displays']['size_inches'] = avixa_calcs.get('recommended_display_size_inches', 65)
    
    if 'audio_system' in equipment:
        equipment['audio_system']['speaker_count'] = avixa_calcs.get('speakers_needed_for_coverage', 2)

    # Override based on user text requests
    user_features = technical_reqs.get('features', '').lower()
    if 'dual display' in user_features and 'displays' in equipment:
        equipment['displays']['quantity'] = 2
            
    return equipment
