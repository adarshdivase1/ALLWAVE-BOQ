# components/av_designer.py

import streamlit as st

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    """Calculates AVIXA-based room recommendations."""
    if length == 0 or width == 0:
        return {}
    area = length * width
    
    farthest_viewer = length * 0.9
    basic_display_height = farthest_viewer / 6
    # Heuristic conversion to inches, ensuring a minimum practical size
    detailed_viewing_display_size = max(55, basic_display_height * 1.15 * 1.25 * 10)
    
    speakers_needed = max(2, int(area / 200) + 1)
    
    return {
        "farthest_viewer_distance": farthest_viewer,
        "basic_viewing_display_size": int(max(43, basic_display_height * 1.25 * 10)),
        "detailed_viewing_display_size": int(detailed_viewing_display_size),
        "estimated_occupancy": int(area / 20),
        "speakers_needed_for_coverage": speakers_needed
    }

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """
    Determines the specific types of equipment needed AND the core brand ecosystem.
    """
    # Start with a baseline for a very simple room
    equipment = {
        'ecosystem': 'Poly', # Default ecosystem
        'displays': {'quantity': 1, 'size_inches': 65, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Integrated', 'dsp_required': False},
        'video_system': {'type': 'All-in-one Video Bar', 'camera_count': 1},
        'control_system': {'type': 'Touch Panel'},
        'housing': {'type': 'Wall Mount Solution'},
        'power_management': {'type': 'Basic Surge Protection'},
    }

    occupancy = avixa_calcs.get('estimated_occupancy', 5)
    display_size = avixa_calcs.get('detailed_viewing_display_size', 65)

    # --- CHANGE START: Logic now defines an ecosystem and is more streamlined ---
    if "Huddle" in room_type or occupancy <= 6:
        equipment['displays']['size_inches'] = display_size
        equipment['ecosystem'] = 'Yealink' # Yealink is often a good fit for smaller rooms

    elif "Standard Conference" in room_type or 6 < occupancy <= 12:
        equipment['displays']['size_inches'] = display_size
        equipment['ecosystem'] = 'Poly' # Poly is a strong choice for mid-size rooms
        equipment['audio_system'] = {'type': 'Integrated Audio with External Mics', 'microphone_count': 2, 'dsp_required': True}
        equipment['power_management'] = {'type': 'Power Conditioner Strip'}

    elif "Large Conference" in room_type or 12 < occupancy <= 20:
        equipment['ecosystem'] = 'Poly'
        equipment['displays']['quantity'] = 2 if "Dual Display" in technical_reqs.get('features', '') else 1
        equipment['displays']['size_inches'] = display_size
        equipment['audio_system'] = {'type': 'Integrated Ceiling Audio', 'microphone_count': 2, 'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 4), 'dsp_required': True}
        equipment['video_system'] = {'type': 'Modular Codec + PTZ Camera', 'camera_count': 1}
        equipment['housing'] = {'type': 'AV Rack'}
        equipment['power_management'] = {'type': 'Rackmount PDU'}

    elif "Boardroom" in room_type or "Training" in room_type or occupancy > 20:
        equipment['ecosystem'] = 'Crestron' # Crestron/QSC for high-end, custom control
        equipment['displays']['quantity'] = 2
        equipment['displays']['size_inches'] = display_size
        equipment['audio_system'] = {'type': 'Fully Integrated Pro Audio', 'microphone_count': 2, 'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 6), 'dsp_required': True}
        equipment['video_system'] = {'type': 'Modular Codec + PTZ Camera', 'camera_count': 2 if "Training" in room_type else 1}
        equipment['housing'] = {'type': 'AV Rack'}
        equipment['power_management'] = {'type': 'Rackmount PDU'}
    # --- CHANGE END ---
        
    # Override for specific UC platform requests
    features_lower = technical_reqs.get('features', '').lower()
    if 'teams certified' in features_lower or 'microsoft teams' in features_lower:
        # Poly and Yealink have strong Teams offerings
        if equipment['ecosystem'] not in ['Poly', 'Yealink']:
            equipment['ecosystem'] = 'Poly'
            
    if 'zoom certified' in features_lower:
         if equipment['ecosystem'] not in ['Poly', 'Yealink']:
            equipment['ecosystem'] = 'Poly'

    return equipment
