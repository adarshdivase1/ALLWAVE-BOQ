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
    
    # Audio Calculations
    speakers_needed = max(2, int(area / 200) + 1)
    
    return {
        "farthest_viewer_distance": farthest_viewer,
        "basic_viewing_display_size": int(basic_display_height * 1.25 * 10),
        "detailed_viewing_display_size": int(detailed_viewing_display_size),
        "estimated_occupancy": int(area / 20),
        "speakers_needed_for_coverage": speakers_needed
    }

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """
    Determines the specific types of equipment needed based on AVIXA calcs and room type.
    -- REVISED FOR GRANULARITY --
    """
    # Start with a baseline for a very simple room
    equipment = {
        'displays': {'quantity': 1, 'size_inches': 65, 'type': 'Commercial 4K Display'},
        'audio_system': {'type': 'Integrated', 'microphone_type': 'Integrated', 'speaker_type': 'Integrated', 'dsp_required': False},
        'video_system': {'type': 'All-in-one Video Bar', 'camera_type': 'ePTZ 4K', 'camera_count': 1},
        'control_system': {'type': 'Touch Panel'},
        'user_interface': {'type': 'Touch Panel Controller'},
        'housing': {'type': 'Wall Mount Solution'},
        'power_management': {'type': 'Basic Surge Protection'},
        'content_sharing': {'type': 'Wireless & Wired HDMI'}
    }

    # -- NEW: GRANULAR LOGIC PER ROOM TYPE --

    # 1. Huddle Room (Simple, All-in-One)
    if "Huddle" in room_type:
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 65)
        # The default is already perfect for a Huddle Room.

    # 2. Standard Conference Room (More robust than Huddle)
    elif "Standard Conference" in room_type:
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 75)
        equipment['audio_system'] = {
            'type': 'Integrated Audio with External Mics',
            'microphone_type': 'Tabletop Mic Pods',
            'microphone_count': 2, # Specify mic count
            'speaker_type': 'Integrated in Video Bar',
            'dsp_required': True # DSP is often needed for external mics
        }
        equipment['video_system']['type'] = 'All-in-one Video Bar' # Still a bar, but a more premium one
        equipment['housing'] = {'type': 'Wall Mount Solution'}
        equipment['power_management'] = {'type': 'Power Conditioner Strip'}

    # 3. Large Conference Room (Modular, high performance)
    elif "Large Conference" in room_type:
        equipment['displays']['quantity'] = 2 if "Dual Display" in technical_reqs.get('features', '') else 1
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 85)
        equipment['audio_system'] = {
            'type': 'Integrated Ceiling Audio',
            'microphone_type': 'Ceiling Mic Array',
            'microphone_count': 2, # Two arrays for better coverage
            'speaker_type': 'Ceiling Speakers',
            'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 4),
            'dsp_required': True
        }
        equipment['video_system'] = {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'Optical Zoom PTZ', 'camera_count': 1}
        equipment['housing'] = {'type': 'AV Rack'}
        equipment['power_management'] = {'type': 'Rackmount PDU'}

    # 4. Boardroom (Premium modular system)
    elif "Boardroom" in room_type:
        equipment['displays']['quantity'] = 2 # Dual displays are standard for boardrooms
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 98)
        equipment['audio_system'] = {
            'type': 'Fully Integrated Pro Audio',
            'microphone_type': 'Ceiling Mic Array',
            'microphone_count': 2,
            'speaker_type': 'Ceiling Speakers',
            'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 6), # More speakers for premium audio
            'dsp_required': True
        }
        equipment['video_system'] = {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'High-Performance Optical Zoom PTZ', 'camera_count': 1}
        equipment['housing'] = {'type': 'AV Rack'}
        equipment['power_management'] = {'type': 'Rackmount PDU'}

    # 5. Training Room (Focus on presentation and voice lift)
    elif "Training" in room_type:
        equipment['displays']['quantity'] = 2 # One for presentation, one for remote participants
        equipment['displays']['size_inches'] = avixa_calcs.get('detailed_viewing_display_size', 85)
        equipment['audio_system'] = {
            'type': 'Voice Reinforcement System', # Key difference for training rooms
            'microphone_type': 'Presenter Wireless + Ceiling Mics',
            'microphone_count': 3, # 1 wireless + 2 ceiling
            'speaker_type': 'Ceiling Speakers',
            'speaker_count': avixa_calcs.get('speakers_needed_for_coverage', 6),
            'dsp_required': True
        }
        equipment['video_system'] = {'type': 'Modular Codec + PTZ Camera', 'camera_type': 'Dual PTZ Cameras (Presenter/Audience)', 'camera_count': 2}
        equipment['housing'] = {'type': 'AV Rack'}
        equipment['power_management'] = {'type': 'Rackmount PDU'}

    # Further refinement based on specific technical requirements can still be added here
    if technical_reqs.get('audio_requirements') == 'Voice Lift':
        equipment['audio_system']['type'] = 'Voice Reinforcement System'
        equipment['audio_system']['dsp_required'] = True

    return equipment
