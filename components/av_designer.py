# components/av_designer.py

import streamlit as st
from components.utils import estimate_power_draw
from components.room_profiles import ROOM_SPECS # Import from the new central file

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    if length == 0 or width == 0: return {}
    area = length * width
    farthest_viewer = length * 0.9
    
    # Define size constraints for different room types to ensure practical results
    SIZE_CONSTRAINTS = {
        "Small Huddle": (43, 55), # Min 43", Max 55"
        "Medium Huddle": (55, 65), # Min 55", Max 65"
        "Standard Conference": (65, 75),
        "Large Conference": (75, 85),
        "Boardroom": (85, 98)
    }
    
    # Use different ratios for different viewing needs
    if any(s in room_type for s in ["Huddle", "Conference", "Boardroom", "Telepresence"]):
        display_height_ft = farthest_viewer / 4 # Detailed viewing
    else: 
        display_height_ft = farthest_viewer / 6 # Basic viewing

    # Assuming 16:9, diagonal is approx 2.22x height
    recommended_size = display_height_ft * 12 * 2.22

    # --- NEW LOGIC: Apply constraints based on room type ---
    for key, (min_size, max_size) in SIZE_CONSTRAINTS.items():
        if key in room_type:
            recommended_size = max(min_size, min(recommended_size, max_size))
            break

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
    profile = ROOM_SPECS.get(room_type, ROOM_SPECS["Standard Conference Room (6-8 People)"])
    equipment = {k: (v.copy() if isinstance(v, dict) else v) for k, v in profile.items()}
    
    # --- BUG FIX STARTS HERE ---
    # Add the room_type and avixa_calcs to the dictionary so they can be used later
    equipment['room_type'] = room_type
    equipment['avixa_calcs'] = avixa_calcs
    # --- BUG FIX ENDS HERE ---

    # This part remains the same
    user_features = technical_reqs.get('features', '').lower()
    if 'dual display' in user_features and 'components' in equipment and 'display' in equipment['components']:
        equipment['components']['display']['quantity'] = 2
        
    return equipment
