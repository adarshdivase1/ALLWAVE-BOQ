# components/av_designer.py

def calculate_avixa_recommendations(room_length, room_width, room_height, room_type):
    """Calculate comprehensive AVIXA recommendations with proper formulas."""
    room_area = room_length * room_width
    room_volume = room_area * room_height

    # AVIXA DISCAS Display Sizing
    max_viewing_distance = min(room_length * 0.85, room_width * 0.9)
    detailed_screen_height_ft = max_viewing_distance / 6
    detailed_screen_size = detailed_screen_height_ft * 12 / 0.49
    basic_screen_height_ft = max_viewing_distance / 4
    basic_screen_size = basic_screen_height_ft * 12 / 0.49

    # Audio Power
    base_power_per_cubic_ft = 0.5
    if 'training' in room_type.lower() or 'presentation' in room_type.lower(): base_power_per_cubic_ft = 0.75
    elif 'executive' in room_type.lower() or 'boardroom' in room_type.lower(): base_power_per_cubic_ft = 1.0
    audio_power_needed = int(room_volume * base_power_per_cubic_ft)

    # Lighting
    if 'conference' in room_type.lower(): ambient_lighting, presentation_lighting = 200, 150
    elif 'training' in room_type.lower(): ambient_lighting, presentation_lighting = 300, 200
    else: ambient_lighting, presentation_lighting = 250, 175

    # Network & Power
    estimated_people = min(room_area // 20, 50) if room_area > 0 else 1
    recommended_bandwidth = int((2.5 * estimated_people) + 5.0 + 10)
    display_power = 250 if detailed_screen_size < 75 else 400
    audio_system_power = 150 + (audio_power_needed * 0.3)
    total_av_power = display_power + audio_system_power + 25 + 100 + 75
    if total_av_power < 1200: circuit_requirement = "15A Standard Circuit"
    elif total_av_power < 1800: circuit_requirement = "20A Dedicated Circuit"
    else: circuit_requirement = "Multiple 20A Circuits"
    
    # UPS
    if 'executive' in room_type.lower() or 'boardroom' in room_type.lower(): ups_runtime_minutes = 30
    elif 'training' in room_type.lower() or 'conference' in room_type.lower(): ups_runtime_minutes = 15
    else: ups_runtime_minutes = 10
    ups_va_required = int(total_av_power * 1.4)

    return {
        'detailed_viewing_display_size': int(detailed_screen_size), 'basic_viewing_display_size': int(basic_screen_size),
        'max_viewing_distance': max_viewing_distance, 'recommended_display_count': 2 if room_area > 300 else 1,
        'audio_power_needed': audio_power_needed, 'microphone_coverage_zones': max(2, estimated_people // 4),
        'speaker_zones_required': max(2, int(room_area // 150)) if room_area > 0 else 1,
        'ambient_lighting_lux': ambient_lighting, 'presentation_lighting_lux': presentation_lighting,
        'lighting_zones_required': max(2, int(room_area // 200)) if room_area > 0 else 1,
        'estimated_occupancy': estimated_people, 'recommended_bandwidth_mbps': recommended_bandwidth,
        'total_power_load_watts': total_av_power, 'circuit_requirement': circuit_requirement,
        'ups_va_required': ups_va_required, 'ups_runtime_minutes': ups_runtime_minutes,
        'cable_runs': {'cat6a_network': 3 + max(1, estimated_people // 6), 'hdmi_video': 2, 'xlr_audio': max(1, estimated_people // 3), 'power_circuits': 2 + max(1, total_av_power // 1000)},
        'requires_ada_compliance': estimated_people > 15, 'requires_hearing_loop': estimated_people > 50, 'requires_assistive_listening': estimated_people > 25
    }

def determine_equipment_requirements(avixa_calcs, room_type, technical_reqs):
    """Determine specific equipment based on AVIXA calculations and room requirements."""
    requirements = {'displays': [], 'audio_system': {}, 'video_system': {}, 'control_system': {}, 'infrastructure': {}, 'compliance': []}
    display_size, display_count = avixa_calcs['detailed_viewing_display_size'], avixa_calcs['recommended_display_count']
    
    if display_size <= 55: display_type = "Commercial LED Display"
    elif display_size <= 75: display_type = "Large Format Display"
    elif display_size <= 86: display_type = "Professional Large Format Display"
    else: display_type = "Video Wall or Laser Projector"
    requirements['displays'] = {'type': display_type, 'size_inches': display_size, 'quantity': display_count, 'resolution': '4K' if display_size > 43 else '1080p', 'mounting': 'Wall Mount' if display_size < 75 else 'Heavy Duty Wall Mount'}
    
    room_volume = (avixa_calcs['audio_power_needed'] / 0.5) if avixa_calcs['audio_power_needed'] > 0 else 1
    if room_volume < 2000:
        requirements['audio_system'] = {'type': 'All-in-One Video Bar', 'microphones': 'Integrated Beamforming Array', 'speakers': 'Integrated Speakers', 'dsp_required': False}
    elif room_volume < 5000:
        mic_solution = 'Tabletop Microphones' if technical_reqs.get('ceiling_height', 10) < 9 else 'Ceiling Microphone Array'
        requirements['audio_system'] = {'type': 'Distributed Audio System', 'microphones': mic_solution, 'microphone_count': avixa_calcs['microphone_coverage_zones'], 'speakers': 'Ceiling Speakers', 'speaker_count': avixa_calcs['speaker_zones_required'], 'amplifier': 'Multi-Channel Amplifier', 'dsp_required': True, 'dsp_type': 'Basic DSP with AEC'}
    else:
        requirements['audio_system'] = {'type': 'Professional Audio System', 'microphones': 'Steerable Ceiling Array', 'microphone_count': avixa_calcs['microphone_coverage_zones'], 'speakers': 'Distributed Ceiling System', 'speaker_count': avixa_calcs['speaker_zones_required'], 'amplifier': 'Networked Amplifier System', 'dsp_required': True, 'dsp_type': 'Advanced DSP with Dante/AVB', 'voice_lift': room_volume > 8000}
    
    if avixa_calcs['estimated_occupancy'] <= 6: camera_type = 'Fixed Wide-Angle Camera'
    elif avixa_calcs['estimated_occupancy'] <= 12: camera_type = 'PTZ Camera with Auto-Framing'
    else: camera_type = 'Multi-Camera System with Tracking'
    requirements['video_system'] = {'camera_type': camera_type, 'camera_count': 1 if avixa_calcs['estimated_occupancy'] <= 12 else 2, '4k_required': avixa_calcs['estimated_occupancy'] > 8}
    
    if room_volume < 2000: control_type = 'Native Room System Control'
    elif room_volume < 5000: control_type = 'Touch Panel Control'
    else: control_type = 'Advanced Programmable Control System'
    requirements['control_system'] = {'type': control_type, 'touch_panel_size': '7-inch' if room_volume < 3000 else '10-inch', 'integration_required': room_volume > 5000}
    
    requirements['infrastructure'] = {'equipment_rack': 'Wall-Mount' if room_volume < 3000 else 'Floor-Standing', 'rack_size': '6U' if room_volume < 3000 else '12U' if room_volume < 8000 else '24U', 'cooling_required': avixa_calcs['total_power_load_watts'] > 1500, 'ups_required': True, 'cable_management': 'Standard' if room_volume < 5000 else 'Professional'}

    if avixa_calcs['requires_ada_compliance']: requirements['compliance'].extend(['ADA Compliant Touch Panels (15-48" height)', 'Visual Notification System'])
    if avixa_calcs['requires_hearing_loop']: requirements['compliance'].append('Hearing Loop System')
    if avixa_calcs['requires_assistive_listening']: requirements['compliance'].append('FM/IR Assistive Listening (4% of capacity)')
        
    return requirements
