# components/acim_parser_enhanced.py
"""
REVISED & ENHANCED: ACIM form parser specifically tuned for Auditorium requirements
Generates a complete and logical blueprint based on detailed client input.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import math

# Define constants for clarity
DEFAULT_AUDITORIUM_LENGTH = 80.0
DEFAULT_AUDITORIUM_WIDTH = 60.0
DEFAULT_AUDITORIUM_HEIGHT = 20.0
DEFAULT_AUDITORIUM_CAPACITY = 250
SQFT_PER_PERSON_AUDITORIUM = 20 # More space per person in auditoriums
DEFAULT_BUDGET_PER_SEAT = 800 # Baseline cost estimate

@dataclass
class AuditoriumClientRequirements:
    """Specialized requirements parsed from ACIM form for auditorium spaces"""
    # Parsed directly from form
    seating_capacity: int
    seating_orientation: str
    room_dimensions_text: str
    connectivity_podium: List[str] # ['wired', 'wireless']
    connectivity_seating: List[str]
    usage_frequency: str
    primary_applications: List[str]
    vc_solution_preference: str # 'Native' or 'BYOM'
    uc_platform: str # 'Microsoft Teams', 'Zoom Rooms', etc.
    mic_types_onstage: Dict[str, int] # {'Wireless Handheld': 2, 'Wireless Lapel': 2, 'Gooseneck': 1, 'Boundary': 4}
    mic_types_offstage: Dict[str, int] # {'Wireless Handheld': 2}
    camera_count_preference: str # 'single', 'multiple'
    camera_features: List[str] # ['speech tracking', 'presets']
    streaming_required: bool
    streaming_platforms: List[str] # ['internal', 'youtube']
    automation_requirements: List[str] # ['AV', 'lights', 'blinds']
    audio_performance_preference: str # 'High-performance columns recommended' or similar
    budget_text: str

    # Derived values
    estimated_budget_midpoint: float
    length_ft: float
    width_ft: float
    height_ft: float
    area_sqft: float
    stage_present: bool = False
    tiered_seating: bool = False
    control_booth: bool = False

def _extract_dimensions(text: str) -> Tuple[float, float, float]:
    """Helper to extract dimensions, using auditorium defaults"""
    import re
    if not text:
        return DEFAULT_AUDITORIUM_LENGTH, DEFAULT_AUDITORIUM_WIDTH, DEFAULT_AUDITORIUM_HEIGHT

    # Try various patterns (LxWxH)
    patterns = [
        r'(\d+\.?\d*)\s*(?:ft|feet|\')\s*[xX×]\s*(\d+\.?\d*)\s*(?:ft|feet|\')\s*[xX×]?\s*(\d+\.?\d*)\s*(?:ft|feet|\')?', # 80ft x 60ft x 25ft
        r'(\d+\.?\d*)\s*[xX×]\s*(\d+\.?\d*)\s*[xX×]?\s*(\d+\.?\d*)', # 80 x 60 x 25
        r'length[:\s]*(\d+\.?\d*).*breadth[:\s]*(\d+\.?\d*).*height[:\s]*(\d+\.?\d*)', # length: 80...
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                l = float(match.group(1)) if match.group(1) else DEFAULT_AUDITORIUM_LENGTH
                w = float(match.group(2)) if match.group(2) else DEFAULT_AUDITORIUM_WIDTH
                h = float(match.group(3)) if match.group(3) else DEFAULT_AUDITORIUM_HEIGHT
                # Basic sanity check
                if l > 10 and w > 10 and h > 5:
                     return l, w, h
            except (ValueError, IndexError):
                continue
    # Fallback if only LxW found
    simple_match = re.search(r'(\d+\.?\d*)\s*(?:ft|feet|\')?\s*[xX×]\s*(\d+\.?\d*)\s*(?:ft|feet|\')?', text, re.IGNORECASE)
    if simple_match:
         try:
            l = float(simple_match.group(1)) if simple_match.group(1) else DEFAULT_AUDITORIUM_LENGTH
            w = float(simple_match.group(2)) if simple_match.group(2) else DEFAULT_AUDITORIUM_WIDTH
            if l > 10 and w > 10:
                return l, w, DEFAULT_AUDITORIUM_HEIGHT
         except (ValueError, IndexError):
             pass

    return DEFAULT_AUDITORIUM_LENGTH, DEFAULT_AUDITORIUM_WIDTH, DEFAULT_AUDITORIUM_HEIGHT

def _parse_budget(budget_text: str, capacity: int) -> float:
    """Robust budget parsing and estimation"""
    import re
    if not budget_text:
        return float(capacity * DEFAULT_BUDGET_PER_SEAT)

    # Remove currency symbols, commas, and labels
    cleaned_text = re.sub(r'[$,₹€]|(?:USD|INR)|range|budget|approx', '', budget_text, flags=re.IGNORECASE)
    cleaned_text = cleaned_text.replace(',', '').strip()

    # Pattern to find numbers, potentially separated by 'to' or '-'
    pattern = r'(\d+\.?\d*k?)\s*(?:to|-)?\s*(\d+\.?\d*k?)?'
    match = re.search(pattern, cleaned_text)

    def parse_value(val_str):
        if not val_str: return None
        val_str = val_str.lower()
        multiplier = 1000 if 'k' in val_str else 1
        try:
            return float(re.sub(r'k', '', val_str)) * multiplier
        except ValueError:
            return None

    if match:
        low_str = match.group(1)
        high_str = match.group(2)

        low_val = parse_value(low_str)
        high_val = parse_value(high_str)

        if low_val is not None and high_val is not None:
            # Range provided (e.g., 150k - 220k)
            return (low_val + high_val) / 2
        elif low_val is not None:
            # Single value provided (e.g., 200k) - estimate range
            return low_val * 1.1 # Estimate midpoint slightly above single value
        elif high_val is not None:
             # Only high value found (less common, e.g., "up to 200k")
             return high_val * 0.8 # Estimate midpoint below max

    # If no numbers found, estimate based on capacity
    return float(capacity * DEFAULT_BUDGET_PER_SEAT)

def parse_auditorium_requirements(responses: Dict) -> AuditoriumClientRequirements:
    """
    Extract detailed auditorium specifications from ACIM responses.
    Matches the sample client requirements provided.
    """

    # --- Basic Info ---
    seating_text = responses.get('seating_info', '')
    capacity_match = re.search(r'(\d+)\s*seats?', seating_text, re.IGNORECASE)
    seating_capacity = int(capacity_match.group(1)) if capacity_match else DEFAULT_AUDITORIUM_CAPACITY
    seating_orientation = "Theater" # Default assumption for auditorium

    dimensions_text = responses.get('room_dimensions', '')
    length, width, height = _extract_dimensions(dimensions_text)
    area = length * width

    stage_present = any(term in dimensions_text.lower() for term in ['stage', 'platform'])
    tiered_seating = any(term in dimensions_text.lower() for term in ['tiered', 'sloped'])
    control_booth = 'control booth' in dimensions_text.lower()

    # --- Connectivity ---
    conn_text = responses.get('connectivity', '')
    conn_podium = []
    if 'wired' in conn_text.lower() or 'hdmi' in conn_text.lower() or 'usb-c' in conn_text.lower():
        conn_podium.append('wired')
    if 'wireless' in conn_text.lower():
        conn_podium.append('wireless')
    conn_seating = ['wireless'] if 'wireless' in conn_text.lower() and 'seating' in conn_text.lower() else []

    # --- Usage ---
    usage_frequency = responses.get('usage_frequency', 'Weekly')
    primary_apps_text = responses.get('primary_applications', 'presentations, training, town halls')
    primary_applications = [app.strip() for app in re.split(r',|and', primary_apps_text)]

    # --- VC ---
    vc_pref_text = responses.get('vc_solution', 'Native')
    vc_solution_preference = 'Native' if 'native' in vc_pref_text.lower() else 'BYOM'

    uc_platform_text = responses.get('uc_platform', 'Microsoft Teams')
    uc_platform = "Microsoft Teams" # Default, refine based on text later if needed
    if 'zoom' in uc_platform_text.lower():
        uc_platform = "Zoom Rooms"
    elif 'webex' in uc_platform_text.lower():
        uc_platform = "Cisco Webex"

    # --- Microphones ---
    mic_text = responses.get('microphone_preferences', '')
    mics_onstage = {}
    mics_offstage = {}

    mics_onstage['Wireless Handheld'] = int(re.search(r'(\d+)(?:x)?\s*Wireless Handheld', mic_text, re.IGNORECASE).group(1)) if re.search(r'(\d+)(?:x)?\s*Wireless Handheld', mic_text, re.IGNORECASE) else 2
    mics_onstage['Wireless Lapel'] = int(re.search(r'(\d+)(?:x)?\s*Wireless Lapel', mic_text, re.IGNORECASE).group(1)) if re.search(r'(\d+)(?:x)?\s*Wireless Lapel', mic_text, re.IGNORECASE) else 2
    mics_onstage['Gooseneck'] = 1 # Always include one for lectern
    mics_onstage['Boundary'] = int(re.search(r'(\d+)(?:x)?\s*(?:wired\s*)?Boundary', mic_text, re.IGNORECASE).group(1)) if re.search(r'(\d+)(?:x)?\s*(?:wired\s*)?Boundary', mic_text, re.IGNORECASE) else 4

    mics_offstage['Wireless Handheld'] = int(re.search(r'(\d+)(?:x)?\s*Wireless Handheld.*audience', mic_text, re.IGNORECASE).group(1)) if re.search(r'(\d+)(?:x)?\s*Wireless Handheld.*audience', mic_text, re.IGNORECASE) else 2

    # --- Cameras ---
    cam_req_text = responses.get('camera_requirements', 'multiple')
    camera_count_preference = 'multiple' if 'multiple' in cam_req_text.lower() else 'single'

    cam_feat_text = responses.get('camera_features', 'speech tracking, presets')
    camera_features = []
    if 'tracking' in cam_feat_text.lower():
        camera_features.append('speech tracking')
    if 'presets' in cam_feat_text.lower():
        camera_features.append('presets')

    # --- Streaming ---
    stream_text = responses.get('live_streaming', 'yes, internal')
    streaming_required = 'yes' in stream_text.lower() or 'live streaming' in stream_text.lower()
    streaming_platforms = []
    if 'internal' in stream_text.lower() or 'corporate' in stream_text.lower():
        streaming_platforms.append('internal')
    if 'youtube' in stream_text.lower():
        streaming_platforms.append('youtube')
    if 'facebook' in stream_text.lower():
        streaming_platforms.append('facebook')

    # --- Automation ---
    auto_text = responses.get('automation', 'yes, AV, lights')
    automation_requirements = []
    if 'yes' in auto_text.lower():
        if 'av' in auto_text.lower() or 'audio visual' in auto_text.lower():
            automation_requirements.append('AV')
        if 'lights' in auto_text.lower():
            automation_requirements.append('lights')
        if 'blinds' in auto_text.lower():
            automation_requirements.append('blinds')
        if 'ac' in auto_text.lower() or 'air conditioning' in auto_text.lower():
            automation_requirements.append('AC')

    # --- Audio Preference & Budget ---
    audio_performance_preference = responses.get('audio_performance', 'High-performance columns recommended')
    budget_text = responses.get('budget', '150,000 - 220,000 USD')
    estimated_budget_midpoint = _parse_budget(budget_text, seating_capacity)

    return AuditoriumClientRequirements(
        seating_capacity=seating_capacity,
        seating_orientation=seating_orientation,
        room_dimensions_text=dimensions_text,
        connectivity_podium=conn_podium,
        connectivity_seating=conn_seating,
        usage_frequency=usage_frequency,
        primary_applications=primary_applications,
        vc_solution_preference=vc_solution_preference,
        uc_platform=uc_platform,
        mic_types_onstage=mics_onstage,
        mic_types_offstage=mics_offstage,
        camera_count_preference=camera_count_preference,
        camera_features=camera_features,
        streaming_required=streaming_required,
        streaming_platforms=streaming_platforms,
        automation_requirements=automation_requirements,
        audio_performance_preference=audio_performance_preference,
        budget_text=budget_text,
        estimated_budget_midpoint=estimated_budget_midpoint,
        length_ft=length,
        width_ft=width,
        height_ft=height,
        area_sqft=area,
        stage_present=stage_present,
        tiered_seating=tiered_seating,
        control_booth=control_booth
    )

def generate_auditorium_blueprint(
    requirements: AuditoriumClientRequirements,
    avixa_calcs: Dict # Pass AVIXA calculations for reference
) -> Dict[str, 'ProductRequirement']:
    """
    Generate enterprise-grade auditorium system blueprint based on parsed requirements.
    Includes ALL necessary components.
    """
    from components.intelligent_product_selector import ProductRequirement # Import here to avoid circular dependency

    blueprint = {}
    priority_counter = 1

    # ========== VIDEO SYSTEM ==========

    # --- Main Display ---
    # Use Projector for large capacity, high ceiling
    if requirements.seating_capacity >= 100 or requirements.height_ft > 18:
        # Estimate lumens: Area * Target Lux / Projector Efficiency (Lux based on AVIXA guidelines)
        target_lux = 50 # Standard for presentation venues
        efficiency = 0.5 # Typical
        required_lumens = (requirements.area_sqft * target_lux) / efficiency
        required_lumens = max(10000, required_lumens) # Ensure minimum for large venue

        blueprint['main_projector'] = ProductRequirement(
            category='Displays', sub_category='Projector', quantity=1, priority=priority_counter,
            justification=f'{required_lumens:.0f}+ Lumen large venue laser projector for {requirements.seating_capacity} seats',
            required_keywords=['projector', 'laser', 'large venue', '10000 lumens', '12000 lumens', '15000 lumens'], # Include lumen ranges
            min_price=8000 # Realistic minimum for large venue laser
        )
        priority_counter += 1

        blueprint['projector_mount'] = ProductRequirement(
             category='Mounts', sub_category='Projector Mount', quantity=1, priority=priority_counter,
             justification='Ceiling mount for large venue projector',
             required_keywords=['projector mount', 'ceiling', 'heavy duty'], min_price=300
        )
        priority_counter += 1

        # Estimate screen size based on AVIXA (e.g., Image Height = Farthest Dist / 6)
        farthest_viewer = requirements.length_ft * 0.9
        image_height_ft = farthest_viewer / 6
        image_width_ft = image_height_ft * (16/9)
        screen_diagonal_inches = math.sqrt(image_width_ft**2 + image_height_ft**2) * 12
        screen_diagonal_inches = max(150, min(300, round(screen_diagonal_inches / 10) * 10)) # Round to nearest 10, reasonable bounds

        blueprint['projection_screen'] = ProductRequirement(
            category='Displays', sub_category='Projection Screen', quantity=1, priority=priority_counter,
            justification=f'Motorized ~{screen_diagonal_inches}" projection screen (AVIXA calc)',
            required_keywords=['screen', 'motorized', 'projection', f'{screen_diagonal_inches}"'],
            size_requirement=float(screen_diagonal_inches),
            min_price=2000
        )
        priority_counter += 1

    else: # Use LED Wall for smaller/modern auditoriums
        # Estimate size (e.g., fill a significant portion of stage width)
        led_width_ft = requirements.width_ft * 0.4
        led_height_ft = led_width_ft * (9/16)
        led_diagonal_inches = math.sqrt(led_width_ft**2 + led_height_ft**2) * 12
        led_diagonal_inches = max(120, min(250, round(led_diagonal_inches / 10) * 10))

        blueprint['led_display'] = ProductRequirement(
            category='Displays', sub_category='Direct-View LED', quantity=1, priority=priority_counter,
            justification=f'~{led_diagonal_inches}" Direct-View LED wall for main display',
            required_keywords=['led', 'direct view', 'video wall'],
            size_requirement=float(led_diagonal_inches),
            min_price=25000 # LED walls are expensive
        )
        priority_counter += 1

    # --- Confidence Monitors ---
    blueprint['confidence_monitors'] = ProductRequirement(
        category='Displays', sub_category='Professional Display', quantity=2, priority=priority_counter,
        justification='Dual 55" stage confidence monitors for presenter view',
        required_keywords=['display', 'monitor', '55"'], size_requirement=55.0,
        min_price=600, max_price=1500
    )
    priority_counter += 1
    blueprint['confidence_mounts'] = ProductRequirement(
        category='Mounts', sub_category='Display Mount / Cart', quantity=2, priority=priority_counter,
        justification='Floor stands or low-profile mounts for confidence monitors',
        required_keywords=['floor stand', 'mount', 'low profile'], min_price=150
    )
    priority_counter += 1

    # --- Video Switching ---
    # Inputs: Lectern (HDMI, USB-C), Wireless Pres, VC Codec Out, Camera 1, Camera 2, (Spare)
    # Outputs: Projector/LED, Confidence 1, Confidence 2, Streamer, VC Codec In (Content)
    input_count = 6
    output_count = 5
    blueprint['matrix_switcher'] = ProductRequirement(
        category='Signal Management', sub_category='Matrix Switcher', quantity=1, priority=priority_counter,
        justification=f'{input_count}x{output_count} 4K seamless presentation switcher/scaler',
        required_keywords=['matrix', 'switcher', 'seamless', 'scaler', '4k', f'{input_count}x{output_count}'],
        min_price=5000
    )
    priority_counter += 1

    # ========== CAMERA SYSTEM ==========
    num_cameras = 2 if requirements.camera_count_preference == 'multiple' else 1
    camera_keywords = ['ptz', 'camera', '4k', 'optical zoom', '20x']
    if 'speech tracking' in requirements.camera_features:
        camera_keywords.extend(['tracking', 'auto-track', 'presenter track'])

    blueprint['ptz_cameras'] = ProductRequirement(
        category='Video Conferencing', sub_category='PTZ Camera', quantity=num_cameras, priority=priority_counter,
        justification=f'{num_cameras}x PTZ camera(s) with required features (tracking/presets)',
        required_keywords=camera_keywords, min_price=2500 # Higher min price for tracking cameras
    )
    priority_counter += 1
    blueprint['camera_mounts'] = ProductRequirement(
         category='Mounts', sub_category='Camera Mount', quantity=num_cameras, priority=priority_counter,
         justification=f'{num_cameras}x Wall or ceiling mounts for PTZ cameras',
         required_keywords=['camera mount', 'wall mount', 'ceiling mount', 'ptz'], min_price=100
    )
    priority_counter += 1

    # ========== VIDEO CONFERENCING ==========
    if requirements.vc_solution_preference == 'Native':
        platform_keywords = {
            'Microsoft Teams': ['teams', 'microsoft', 'mtr'],
            'Zoom Rooms': ['zoom'],
            'Cisco Webex': ['cisco', 'webex', 'room kit']
        }
        codec_keywords = ['codec', 'room kit'] + platform_keywords.get(requirements.uc_platform, ['teams'])
        blueprint['vc_codec'] = ProductRequirement(
            category='Video Conferencing', sub_category='Room Kit / Codec', quantity=1, priority=priority_counter,
            justification=f'Native {requirements.uc_platform} codec for one-touch join',
            required_keywords=codec_keywords,
            compatibility_requirements=[requirements.uc_platform], min_price=3000
        )
        priority_counter += 1

        # MUST have a touch controller for Native VC
        controller_keywords = ['touch', 'controller', 'panel'] + platform_keywords.get(requirements.uc_platform, ['teams'])
        blueprint['vc_touch_controller'] = ProductRequirement(
            category='Video Conferencing', sub_category='Touch Controller / Panel', quantity=1, priority=priority_counter,
            justification=f'Touch controller for {requirements.uc_platform} system',
            required_keywords=controller_keywords,
            compatibility_requirements=[requirements.uc_platform], min_price=500, max_price=1500
        )
        priority_counter += 1

    # --- BYOM Solution ---
    # Needed if client wants BYOM or if VC preference isn't Native
    if requirements.vc_solution_preference != 'Native' or 'BYOM' in requirements.vc_solution_preference:
         blueprint['byom_solution'] = ProductRequirement(
             category='Signal Management', sub_category='Extender (TX/RX)', # Often uses USB extenders/switchers
             quantity=1, priority=priority_counter,
             justification='BYOM solution (e.g., USB switcher/extender) for laptop-driven meetings',
             required_keywords=['byom', 'usb switch', 'usb extender', 'laptop connect'], min_price=500
         )
         priority_counter += 1

    # ========== AUDIO SYSTEM ==========

    # --- Microphones ---
    total_wireless_channels = 0
    # Onstage
    if requirements.mic_types_onstage.get('Wireless Handheld', 0) > 0:
        qty = requirements.mic_types_onstage['Wireless Handheld']
        blueprint['mic_wireless_handheld_onstage'] = ProductRequirement(
            category='Audio', sub_category='Wireless Microphone System', quantity=qty, priority=priority_counter,
            justification=f'{qty}x Wireless handheld microphones for presenters',
            required_keywords=['wireless', 'handheld', 'system', 'receiver'], min_price=500
        )
        total_wireless_channels += qty
        priority_counter += 1
    if requirements.mic_types_onstage.get('Wireless Lapel', 0) > 0:
        qty = requirements.mic_types_onstage['Wireless Lapel']
        blueprint['mic_wireless_lapel_onstage'] = ProductRequirement(
            category='Audio', sub_category='Wireless Microphone System', quantity=qty, priority=priority_counter,
            justification=f'{qty}x Wireless lapel/lavalier microphones for presenters',
            required_keywords=['wireless', 'lapel', 'lavalier', 'bodypack', 'system', 'receiver'], min_price=600
        )
        total_wireless_channels += qty
        priority_counter += 1
    if requirements.mic_types_onstage.get('Gooseneck', 0) > 0:
        blueprint['mic_gooseneck_lectern'] = ProductRequirement(
            category='Audio', sub_category='Gooseneck Microphone', quantity=1, priority=priority_counter,
            justification='Wired gooseneck microphone for lectern',
            required_keywords=['gooseneck', 'microphone', 'wired', 'xlr'], min_price=200
        )
        priority_counter += 1
    if requirements.mic_types_onstage.get('Boundary', 0) > 0:
        qty = requirements.mic_types_onstage['Boundary']
        blueprint['mic_boundary_panel'] = ProductRequirement(
            category='Audio', sub_category='Table/Boundary Microphone', quantity=qty, priority=priority_counter,
            justification=f'{qty}x Wired boundary/table microphones for panel discussions',
            required_keywords=['boundary', 'table', 'microphone', 'wired', 'xlr'], min_price=150
        )
        priority_counter += 1
    # Offstage
    if requirements.mic_types_offstage.get('Wireless Handheld', 0) > 0:
        qty = requirements.mic_types_offstage['Wireless Handheld']
        blueprint['mic_wireless_handheld_audience'] = ProductRequirement(
            category='Audio', sub_category='Wireless Microphone System', quantity=qty, priority=priority_counter,
            justification=f'{qty}x Wireless handheld microphones for audience Q&A',
            required_keywords=['wireless', 'handheld', 'system', 'receiver'], min_price=500
        )
        total_wireless_channels += qty
        priority_counter += 1

    # Antenna Distribution (if many wireless channels)
    if total_wireless_channels >= 4:
         blueprint['mic_antenna_distro'] = ProductRequirement(
             category='Audio', sub_category='RF & Antenna', quantity=1, priority=priority_counter,
             justification='Antenna distribution system for multiple wireless mic channels',
             required_keywords=['antenna', 'distribution', 'combiner', 'splitter'], min_price=500
         )
         priority_counter += 1

    # --- Audio Processing ---
    # Calculate required DSP inputs/outputs
    dsp_inputs = sum(requirements.mic_types_onstage.values()) + sum(requirements.mic_types_offstage.values()) + 4 # Mics + Program Audio + VC Audio + Spares
    dsp_outputs = avixa_calcs['audio']['speakers_needed'] + 4 # Speakers + Record Out + Stream Out + VC Send + Spares
    blueprint['audio_dsp'] = ProductRequirement(
        category='Audio', sub_category='DSP / Audio Processor / Mixer', quantity=1, priority=priority_counter,
        justification=f'Networked DSP (~{dsp_inputs}x{dsp_outputs}) with AEC for all inputs',
        required_keywords=['dsp', 'processor', 'networked', 'dante', 'aec'],
        blacklist_keywords=['mixer', 'analog', 'touchmix'], min_price=4000
    )
    priority_counter += 1

    # --- Speakers ---
    speakers_needed = avixa_calcs['audio']['speakers_needed']
    speaker_keywords = ['speaker', 'loudspeaker']
    if 'column' in requirements.audio_performance_preference.lower():
         speaker_keywords.extend(['column', 'line array', 'steerable'])
         speaker_sub_category = 'Wall-mounted Loudspeaker' # Columns are typically wall-mounted
         min_speaker_price = 800
    else:
         speaker_keywords.extend(['ceiling', 'pendant'])
         speaker_sub_category = 'Ceiling Loudspeaker'
         min_speaker_price = 200

    blueprint['speakers'] = ProductRequirement(
        category='Audio', sub_category=speaker_sub_category, quantity=speakers_needed, priority=priority_counter,
        justification=f'AVIXA A102.01: {speakers_needed}x {speaker_sub_category} ({", ".join(speaker_keywords)})',
        required_keywords=speaker_keywords, min_price=min_speaker_price
    )
    priority_counter += 1

    # --- Amplification ---
    amp_power_watts = avixa_calcs['spl']['recommended_power_watts']
    # Estimate channels needed (e.g., 1 amp channel per 2 speakers, or per column speaker)
    channels_needed = math.ceil(speakers_needed / 2) if 'ceiling' in speaker_sub_category.lower() else speakers_needed
    # Assume 4 or 8 channel amps
    num_amps = math.ceil(channels_needed / 8) if channels_needed > 4 else math.ceil(channels_needed / 4)
    amp_channels_per_amp = 8 if num_amps == math.ceil(channels_needed / 8) else 4

    blueprint['amplifiers'] = ProductRequirement(
        category='Audio', sub_category='Amplifier', quantity=num_amps, priority=priority_counter,
        justification=f'{num_amps}x {amp_channels_per_amp}-Ch Networked Amplifier(s) for ~{amp_power_watts:.0f}W total',
        required_keywords=['amplifier', 'power', 'multi-channel', 'networked', f'{amp_channels_per_amp}-channel'],
        blacklist_keywords=['dsp', 'mixer'], min_price=1500
    )
    priority_counter += 1

    # ========== CONTENT SHARING ==========
    if 'wireless' in requirements.connectivity_podium:
         blueprint['wireless_presentation'] = ProductRequirement(
             category='Signal Management', sub_category='Wireless Presentation System', quantity=1, priority=priority_counter,
             justification='Enterprise wireless presentation system (e.g., ClickShare, Mersive)',
             required_keywords=['wireless', 'presentation', 'byod', 'clickshare', 'mersive'], min_price=1500
         )
         priority_counter += 1

    # ========== CONTROL SYSTEM ==========
    blueprint['control_processor'] = ProductRequirement(
        category='Control Systems', sub_category='Control Processor', quantity=1, priority=priority_counter,
        justification='Enterprise control processor for full room automation',
        required_keywords=['control', 'processor', 'automation', '4-series', 'ipcp pro'], min_price=2500
    )
    priority_counter += 1

    # Control Booth Touch Panel (larger)
    if requirements.control_booth:
        blueprint['control_panel_booth'] = ProductRequirement(
            category='Control Systems', sub_category='Touch Panel', quantity=1, priority=priority_counter,
            justification='Large touch panel (15"+) for control booth operation',
            required_keywords=['touch', 'panel', '15"', '17"', '20"'], min_price=3000
        )
        priority_counter += 1

    # Lectern Touch Panel (smaller)
    blueprint['control_panel_lectern'] = ProductRequirement(
        category='Control Systems', sub_category='Touch Panel', quantity=1, priority=priority_counter,
        justification='Touch panel (10") integrated into lectern for presenter',
        required_keywords=['touch', 'panel', '10"'], min_price=1500, max_price=4000
    )
    priority_counter += 1

    # ========== STREAMING / RECORDING ==========
    if requirements.streaming_required:
         blueprint['streaming_encoder'] = ProductRequirement(
             category='Signal Management', sub_category='AV over IP (Encoder/Decoder)', # Often handled by streaming encoders
             quantity=1, priority=priority_counter,
             justification='Hardware encoder for live streaming and recording',
             required_keywords=['streaming', 'encoder', 'recorder', 'h.264', 'h.265'], min_price=2000
         )
         priority_counter += 1

    # ========== INFRASTRUCTURE ==========
    blueprint['lectern'] = ProductRequirement(
         category='Furniture', sub_category='Podium / Lectern', quantity=1, priority=priority_counter,
         justification='Professional lectern/podium for stage',
         required_keywords=['lectern', 'podium', 'av'], min_price=1500
    )
    priority_counter += 1

    # Racks (adjust quantity based on control booth presence)
    num_racks = 2 if requirements.control_booth else 1
    blueprint['equipment_racks'] = ProductRequirement(
        category='Infrastructure', sub_category='AV Rack', quantity=num_racks, priority=priority_counter,
        justification=f'{num_racks}x Equipment rack(s) (42U) for housing AV gear',
        required_keywords=['rack', '42u', 'enclosure', 'cabinet'], min_price=1200
    )
    priority_counter += 1

    # Network Switch (size based on AVIXA calculation)
    switch_ports = avixa_calcs['network']['recommended_ports']
    switch_size_keyword = '48 port' if switch_ports >= 36 else ('24 port' if switch_ports >= 16 else '16 port')
    blueprint['network_switch'] = ProductRequirement(
        category='Networking', sub_category='Network Switch', quantity=1, priority=priority_counter,
        justification=f'{switch_size_keyword} managed PoE+ switch for AV network',
        required_keywords=['switch', 'managed', 'poe+', switch_size_keyword], min_price=1000
    )
    priority_counter += 1

    # PDUs (at least one per rack)
    blueprint['power_distribution'] = ProductRequirement(
        category='Infrastructure', sub_category='Power (PDU/UPS)', quantity=num_racks, priority=priority_counter,
        justification=f'{num_racks}x Rack-mount PDU(s) for power management',
        required_keywords=['pdu', 'power distribution', 'rack mount', '15a', '20a'], min_price=200
    )
    priority_counter += 1

    # UPS (sized based on AVIXA calculation)
    if avixa_calcs['power']['ups_recommended']:
        ups_va = avixa_calcs['power']['ups_capacity_va']
        ups_va_keyword = f'{round(ups_va / 1000)}kva' if ups_va >= 1000 else f'{ups_va:.0f}va'
        blueprint['ups_system'] = ProductRequirement(
            category='Infrastructure', sub_category='Power (PDU/UPS)', quantity=1, priority=priority_counter,
            justification=f'UPS ({ups_va_keyword}) for critical equipment backup power',
            required_keywords=['ups', 'uninterruptible', 'battery backup', ups_va_keyword], min_price=1000
        )
        priority_counter += 1

    # ========== CABLING ==========
    # Add more specific cable types based on the system design
    cable_runs_cat6a = avixa_calcs['cabling']['cable_requirements']['cat6a']['runs']
    cable_runs_video = avixa_calcs['cabling']['cable_requirements']['hdmi_hdbaset']['runs']
    cable_runs_audio = avixa_calcs['cabling']['cable_requirements']['xlr_audio']['runs']
    cable_runs_speaker = avixa_calcs['cabling']['cable_requirements']['speaker_cable']['runs']

    blueprint['cables_network_bulk'] = ProductRequirement(
        category='Cables & Connectivity', sub_category='Bulk Cable / Wire', quantity=math.ceil(cable_runs_cat6a/5), priority=priority_counter, # Estimate boxes
        justification=f'Bulk Cat6A cable for ~{cable_runs_cat6a} network runs',
        required_keywords=['cat6a', 'bulk', 'cable', '1000ft'], min_price=200
    )
    priority_counter += 1
    blueprint['cables_video_long'] = ProductRequirement(
        category='Cables & Connectivity', sub_category='AV Cable', quantity=cable_runs_video, priority=priority_counter,
        justification=f'{cable_runs_video}x Long-distance video cables (Fiber/HDBT)',
        required_keywords=['fiber optic', 'hdbaset', 'video cable', '50m', '100m'], min_price=100
    )
    priority_counter += 1
    blueprint['cables_audio_bulk'] = ProductRequirement(
        category='Cables & Connectivity', sub_category='Bulk Cable / Wire', quantity=math.ceil(cable_runs_audio/10), priority=priority_counter,
        justification=f'Bulk balanced audio cable for ~{cable_runs_audio} mic/line runs',
        required_keywords=['audio', 'cable', 'bulk', 'balanced', 'xlr'], min_price=150
    )
    priority_counter += 1
    blueprint['cables_speaker_bulk'] = ProductRequirement(
        category='Cables & Connectivity', sub_category='Bulk Cable / Wire', quantity=math.ceil(cable_runs_speaker/5), priority=priority_counter,
        justification=f'Bulk speaker wire for ~{cable_runs_speaker} speaker runs',
        required_keywords=['speaker', 'wire', 'cable', 'bulk', '14awg', '12awg'], min_price=100
    )
    priority_counter += 1
    blueprint['cable_connectors_plates'] = ProductRequirement(
        category='Cables & Connectivity', sub_category='Connectors, Adapters & Dongles', quantity=1, priority=priority_counter, # Placeholder for misc
        justification='Assortment of connectors, plates, and termination hardware',
        required_keywords=['connector', 'termination', 'xlr', 'rj45', 'wall plate'], min_price=500 # Budget placeholder
    )
    priority_counter += 1

    return blueprint


# ========== INTEGRATION FUNCTION ==========

def generate_auditorium_boq(acim_responses: Dict, product_df, avixa_calcs: Dict) -> Tuple[List[Dict], Dict]:
    """
    Main function to generate enterprise-grade auditorium BOQ.
    Uses parsed requirements and AVIXA calculations.
    """
    from components.intelligent_product_selector import IntelligentProductSelector # Import here

    # Extract room requirements from ACIM form data
    room_req_data = acim_responses.get('room_requirements', [])
    if not room_req_data:
        raise ValueError("No room requirements found in ACIM data")
    responses = room_req_data[0]['responses'] # Assume first room is auditorium

    # Parse specialized auditorium requirements
    aud_reqs = parse_auditorium_requirements(responses)

    # Generate blueprint based on parsed requirements and AVIXA data
    blueprint = generate_auditorium_blueprint(aud_reqs, avixa_calcs)

    # Initialize product selector
    # Determine client preferences (can refine this)
    client_prefs = {} # Example: {'audio': 'QSC'} if parsed
    selector = IntelligentProductSelector(
        product_df=product_df,
        client_preferences=client_prefs,
        budget_tier='Premium' # Auditoriums default to Premium
    )
    # Pass necessary context for selection
    selector.requirements = aud_reqs # Pass parsed requirements
    selector.requirements_context = { # Pass AVIXA context
         'vc_platform': aud_reqs.uc_platform,
         'room_type': 'Auditorium',
         'room_area': aud_reqs.area_sqft,
         'avixa_calcs': avixa_calcs
     }

    # --- Select products based on blueprint ---
    boq_items = []
    print("\n--- Starting Auditorium Product Selection ---")
    for component_key, requirement in blueprint.items():
        print(f"Selecting: {component_key} ({requirement.sub_category})")
        # Use select_product_with_fallback for ecosystem handling
        selected_product_dict = selector.select_product_with_fallback(requirement)

        if selected_product_dict:
            # Add quantity back, as selector returns a single dict
            selected_product_dict['quantity'] = requirement.quantity
            # Store the original requirement for reference if needed
            selected_product_dict['requirement_details'] = requirement
            # **REMOVE HARDCODED JUSTIFICATION** - Let main generator handle this
            # selected_product_dict['top_3_reasons'] = [...]
            selected_product_dict['matched'] = True
            boq_items.append(selected_product_dict)
            print(f"  -> Selected: {selected_product_dict.get('brand')} {selected_product_dict.get('model_number')}")
        else:
            print(f"  -> FAILED to select product for {component_key}")
            # Add a placeholder or log failure
            boq_items.append({
                'name': f"MISSING: {requirement.sub_category}",
                'category': requirement.category,
                'sub_category': requirement.sub_category,
                'quantity': requirement.quantity,
                'price': 0,
                'matched': False,
                'justification': f"No suitable product found matching: {requirement.justification}",
                'requirement_details': requirement
            })

    # --- Final Validation & Summary ---
    total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in boq_items if item.get('matched'))
    validation_warnings = selector.get_validation_warnings() # Get warnings from selector

    # Budget validation
    budget_status = "Within Range"
    if total_cost < aud_reqs.estimated_budget_midpoint * 0.7:
        budget_status = "Significantly Under Budget (Review Scope?)"
        validation_warnings.append({
            'component': 'Overall Budget',
            'issue': f"Estimated cost (${total_cost:,.0f}) is well below client budget midpoint (${aud_reqs.estimated_budget_midpoint:,.0f}). Consider upgrades or confirm scope.",
            'severity': 'Medium'
        })
    elif total_cost > aud_reqs.estimated_budget_midpoint * 1.3:
        budget_status = "Potentially Over Budget (Review Options)"
        validation_warnings.append({
            'component': 'Overall Budget',
            'issue': f"Estimated cost (${total_cost:,.0f}) may exceed client budget midpoint (${aud_reqs.estimated_budget_midpoint:,.0f}). Value engineering options may be needed.",
            'severity': 'High'
        })

    validation = {
        'warnings': [w['issue'] for w in validation_warnings if w['severity'] != 'CRITICAL'],
        'issues': [w['issue'] for w in validation_warnings if w['severity'] == 'CRITICAL'],
        'compliance_score': 90 - len([w for w in validation_warnings if w['severity'] == 'CRITICAL'])*10, # Simple score based on critical issues
        'auditorium_validated': True,
        'seating_capacity': aud_reqs.seating_capacity,
        'estimated_cost': total_cost,
        'budget_status': budget_status,
        'selection_log': selector.get_selection_report() # Include detailed log
    }

    print("--- Auditorium BOQ Generation Complete ---")
    return boq_items, validation
