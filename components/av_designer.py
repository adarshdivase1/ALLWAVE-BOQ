# components/av_designer.py

import streamlit as st
from components.room_profiles import ROOM_SPECS

# --- CONFIGURABLE CONSTANTS ---
# Standard commercial display sizes (in inches) to snap calculations to.
STANDARD_DISPLAY_SIZES = [43, 55, 65, 75, 85, 98, 110]

def calculate_avixa_recommendations(length: float, width: float, ceiling_height: float, room_type: str) -> dict:
    """
    Calculates the optimal display size based on AVIXA's Display Image Size for 2D Content in Audiovisual Systems (DISCAS) standard.
    """
    if length == 0 or width == 0:
        return {}

    # Farthest viewer is estimated as 90% of the room's length.
    farthest_viewer_ft = length * 0.9
    
    # Determine the required display height based on the viewing task.
    # For detailed content (e.g., spreadsheets, presentations), the farthest viewer should be no more than
    # 4 times the image height (AVIXA 4:1 rule). For passive viewing (e.g., video), it's 6:1.
    if any(s in room_type for s in ["Huddle", "Conference", "Boardroom", "Telepresence", "Training"]):
        # Detailed viewing requires a larger relative image.
        display_height_ft = farthest_viewer_ft / 4
    else: 
        # Passive viewing allows for a smaller relative image.
        display_height_ft = farthest_viewer_ft / 6

    # Convert display height (in feet) to a diagonal measurement (in inches) for a 16:9 aspect ratio.
    # The diagonal of a 16:9 screen is approximately 2.22 times its height.
    recommended_size_inches = display_height_ft * 12 * 2.22

    def snap_to_standard_size(size_inches: float) -> int:
        """Finds the closest standard display size to the calculated ideal size."""
        return min(STANDARD_DISPLAY_SIZES, key=lambda x: abs(x - size_inches))

    final_size = snap_to_standard_size(recommended_size_inches)
    
    # Estimate the number of ceiling speakers needed for adequate coverage (approx. 1 per 200 sq ft).
    speakers_needed = max(2, int((length * width) / 200))
    
    return {
        "recommended_display_size_inches": final_size,
        "speakers_needed_for_coverage": speakers_needed
    }

def determine_equipment_requirements(avixa_calcs: dict, room_type: str, technical_reqs: dict) -> dict:
    """
    Combines AVIXA calculations with the base room profile to create a full equipment specification.
    """
    # Get the base template for the selected room type.
    profile = ROOM_SPECS.get(room_type, ROOM_SPECS["Standard Conference Room (6-8 People)"])
    # Create a deep copy to avoid modifying the original spec.
    equipment = {k: (v.copy() if isinstance(v, dict) else v) for k, v in profile.items()}

    # Override the profile's default display size with the AVIXA-calculated size.
    if 'displays' in equipment:
        equipment['displays']['size_inches'] = avixa_calcs.get('recommended_display_size_inches', 65)
    
    # Override the profile's default speaker count with the calculated value.
    if 'audio_system' in equipment:
        equipment['audio_system']['speaker_count'] = avixa_calcs.get('speakers_needed_for_coverage', 2)

    # Check for user-specified overrides, such as a request for dual displays.
    if 'dual display' in technical_reqs.get('features', '').lower() and 'displays' in equipment:
        equipment['displays']['quantity'] = 2
        
    return equipment
