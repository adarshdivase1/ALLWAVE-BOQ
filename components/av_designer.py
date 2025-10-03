# components/av_designer.py

import streamlit as st
from components.utils import estimate_power_draw

# --- NEW: Room Profile Database ---
# This dictionary contains the "recipe" for each room type. It defines the baseline
# technology and complexity for every space.
ROOM_PROFILES = {
    "Small Huddle Room (2-3 People)": {
        'displays': {'quantity': 1, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Integrated in Video Bar', 'dsp_required': False},
        'video_system': {'type': 'All-in-one Video Bar', 'camera_type': 'ePTZ 4K'},
        'housing': {'type': 'Wall Mount Solution'}
    },
    "Medium Huddle Room (4-6 People)": {
        'displays': {'quantity': 1, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Integrated with optional Mic Pod', 'dsp_required': True, 'microphone_type': 'Table Microphone'},
        'video_system': {'type': 'All-in-one Video Bar', 'camera_type': 'ePTZ 4K with Autoframing'},
        'housing': {'type': 'Wall Mount Solution'}
    },
    "Standard Conference Room (6-8 People)": {
        'displays': {'quantity': 1, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Dedicated Mics & DSP', 'dsp_required': True, 'microphone_type': 'Table Microphone', 'speaker_type': 'Integrated in Video Bar'},
        'video_system': {'type': 'All-in-one Video Bar', 'camera_type': 'Optical Zoom PTZ'},
        'housing': {'type': 'Wall Mount or Credenza'}
    },
    "Large Conference Room (8-12 People)": {
        'displays': {'quantity': 1, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Integrated Ceiling Audio', 'dsp_required': True, 'microphone_type': 'Ceiling Microphone', 'speaker_type': 'Ceiling Loudspeaker'},
        'video_system': {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'High-Performance Optical Zoom PTZ', 'camera_count': 1},
        'housing': {'type': 'AV Rack'},
        'power_management': {'type': 'Rackmount PDU'}
    },
    "Executive Boardroom (10-16 People)": {
        'displays': {'quantity': 2, 'type': 'Premium Commercial 4K Display'},
        'audio_system': {'type': 'Fully Integrated Pro Audio', 'dsp_required': True, 'microphone_type': 'Ceiling Microphone', 'speaker_type': 'Ceiling Loudspeaker'},
        'video_system': {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'High-Performance Optical Zoom PTZ', 'camera_count': 1},
        'content_sharing': {'type': 'Wireless & Wired HDMI'},
        'housing': {'type': 'AV Rack'},
        'power_management': {'type': 'Rackmount PDU'}
    },
    "Training Room (15-25 People)": {
        'displays': {'quantity': 2, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Voice Reinforcement System', 'dsp_required': True, 'microphone_type': 'Ceiling Microphone', 'speaker_type': 'Ceiling Loudspeaker'},
        'video_system': {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'Dual PTZ Cameras (Presenter/Audience)', 'camera_count': 2},
        'content_sharing': {'type': 'Wireless Presentation System'},
        'housing': {'type': 'AV Rack'},
        'power_management': {'type': 'Rackmount PDU'}
    },
    "Large Training/Presentation Room (25-40 People)": {
        'displays': {'quantity': 1, 'type': 'Projector and Screen'},
        'audio_system': {'type': 'Voice Reinforcement System', 'dsp_required': True, 'microphone_type': 'Ceiling Microphone', 'speaker_type': 'Ceiling Loudspeaker'},
        'video_system': {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'Dual PTZ Cameras (Presenter/Audience)', 'camera_count': 2},
        'content_sharing': {'type': 'Wireless Presentation System'},
        'housing': {'type': 'AV Rack'},
        'power_management': {'type': 'Rackmount PDU'}
    },
    "Multipurpose Event Room (40+ People)": {
        'displays': {'quantity': 1, 'type': 'Large Projector or Direct-View LED'},
        'audio_system': {'type': 'Full PA System with Mixer', 'dsp_required': True, 'microphone_type': 'Wireless Handheld/Lapel', 'speaker_type': 'Wall-mounted Loudspeaker'},
        'video_system': {'type': 'Presentation Switcher with VC Add-on', 'camera_type': 'Multiple PTZ Cameras for Event Coverage', 'camera_count': 2},
        'housing': {'type': 'AV Rack'},
        'power_management': {'type': 'Rackmount PDU'}
    },
    "Video Production Studio": {
        'displays': {'quantity': 3, 'type': 'Reference Monitors & Multiviewer'},
        'audio_system': {'type': 'Studio Mixing Console', 'dsp_required': True, 'microphone_type': 'Studio Condenser Mics'},
        'video_system': {'type': 'Production Switcher', 'camera_type': 'Studio Cameras', 'camera_count': 3},
        'specialized': ['Studio Lighting Grid', 'Recording Decks', 'Acoustic Treatment'],
        'housing': {'type': 'AV Rack'},
        'power_management': {'type': 'Rackmount PDU'}
    },
    "Telepresence Suite": {
        'displays': {'quantity': 3, 'type': 'Vendor-Specific Immersive Displays'},
        'audio_system': {'type': 'Tuned Immersive Audio', 'dsp_required': True, 'microphone_type': 'Integrated Array'},
        'video_system': {'type': 'Dedicated Immersive Telepresence Codec', 'camera_type': 'Multi-camera Array'},
        'specialized': ['Custom Furniture', 'Controlled Lighting'],
        'housing': {'type': 'Integrated into Room Architecture'}
    }
}

def calculate_avixa_recommendations(length, width, ceiling_height, room_type):
    """Calculates AVIXA-based room recommendations."""
    if length == 0 or width == 0:
        return {}
    area = length * width
    
    # DISCAS Calculations
    farthest_viewer = length * 0.9
    
    # Determine appropriate diagonal size in inches based on viewing needs
    # Basic viewing (like presentations) uses a 6:1 distance-to-height ratio
    basic_display_height_ft = farthest_viewer / 6
    # Assuming 16:9 aspect ratio, diagonal is approx. 2.22x height
    basic_display_diagonal_inches = basic_display_height_ft * 12 * 2.22

    # Detailed viewing (like spreadsheets) uses a 4:1 ratio
    detailed_display_height_ft = farthest_viewer / 4
    detailed_display_diagonal_inches = detailed_display_height_ft * 12 * 2.22

    # Choose the appropriate size based on room type
    if any(s in room_type for s in ["Huddle", "Conference", "Boardroom", "Telepresence"]):
        recommended_size = detailed_display_diagonal_inches
    else: # Training, Presentation, Multipurpose rooms
        recommended_size = basic_display_diagonal_inches

    # Snap to nearest standard display size
    def snap_to_standard_size(size_inches):
        sizes = [55, 65, 75, 85, 98]
        return min(sizes, key=lambda x: abs(x - size_inches))

    final_size = snap_to_standard_size(recommended_size)

    # Audio Calculations
    speakers_needed = max(2, int(area / 200) + 1)
    
    return {
        "farthest_viewer_distance": farthest_viewer,
        "recommended_display_size_inches": final_size,
        "estimated_occupancy": int(area / 20),
        "speakers_needed_for_coverage": speakers_needed
    }


# --- REFACTORED: New determine_equipment_requirements function ---
def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """
    Determines the specific types of equipment needed by using the Room Profile
    database as a template and then customizing it.
    """
    # 1. Get the base template from the ROOM_PROFILES database
    # Use a fallback to a standard conference room if the type is unknown
    equipment = ROOM_PROFILES.get(room_type, ROOM_PROFILES["Standard Conference Room (6-8 People)"]).copy()
    equipment['room_type'] = room_type # Add room type for context

    # 2. Dynamically adjust parameters based on AVIXA calculations
    if 'displays' in equipment:
        equipment['displays']['size_inches'] = avixa_calcs.get('recommended_display_size_inches', 65)
    
    if 'audio_system' in equipment:
        equipment['audio_system']['speaker_count'] = avixa_calcs.get('speakers_needed_for_coverage', 2)

    # 3. Override template based on specific user text requests
    user_features = technical_reqs.get('features', '').lower()
    if 'dual display' in user_features:
        if 'displays' in equipment:
            equipment['displays']['quantity'] = 2
            
    if 'voice lift' in user_features:
        if 'audio_system' in equipment:
            equipment['audio_system']['type'] = 'Voice Reinforcement System'

    return equipment
