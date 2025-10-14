Of course. Here is the complete AVIXA guidelines document, including the Python code examples, formatted in a single Markdown block for your repository.

````markdown
# Enhanced AV Design Guidelines for BOQ Generation
*Based on AVIXA Standards & Industry Best Practices*

This document provides a comprehensive framework for automated Bill of Quantities (BOQ) generation for audio-visual systems. All calculations and recommendations are based on AVIXA DISCAS, AVIXA 10:2013, AVIXA 2M-2010, AVIXA D401.01:2023, InfoComm AV Best Practices, and real-world implementation experience.

## Core Design Philosophy
The BOQ generator operates on a room-first approach: analyze the space dimensions, occupancy, and function to determine the appropriate technology tier. Each tier has specific equipment requirements, installation complexity, and cost structures.

## AVIXA Standards Integration
The BOQ generator incorporates multiple AVIXA standards:
* **AVIXA DISCAS** (Display Image Size for 2D Content in Audiovisual Systems) - Display sizing calculations
* **AVIXA 10:2013** - Audiovisual Systems Performance Verification
* **AVIXA 2M-2010** - Standard Guide for Audiovisual Systems Design and Coordination Processes
* **AVIXA D401.01:2023** - Audiovisual Project Documentation Standard
* **AVIXA F502.01:2018** - Rack Building for Audiovisual Systems
* **AVIXA A102.01:2017** - Audio Coverage Uniformity in Enclosed Listener Areas

---

## 1. AVIXA DISCAS - Display Sizing (Critical for Automation)

### Display Image Size Considerations

* **For Analytical Decision Making (ADM) - Critical Detail Viewing:**
    * Used for: Engineering drawings, forensic evidence, detailed image inspection
    * Formula: $\text{Image Height} = (\text{Farthest Viewer Distance} \div 3438) \times \text{Vertical Resolution}$
    * Example: 12ft viewing distance, 1080p display = 3.75" minimum image height

* **For Basic Decision Making (BDM) - Standard Presentations:**
    * Element Height typically 3-5% of screen height for readable text
    * Formula: $\text{Image Height} = (\text{Farthest Viewer Distance} \div 200) \div \text{Element Height \%}$
    * Example: 20ft viewing distance, 4% element = 100" display recommended

* **For Passive Viewing - General Content:**
    * Used for: Digital signage, lobby displays, non-critical viewing
    * Formula: $\text{Image Height} = \text{Viewing Distance} \div 8$
    * Example: 16ft viewing distance = 24" minimum screen height

### BOQ Logic Implementation:
```python
# Determine maximum viewing distance
if room_length > room_width:
    max_viewing_distance = room_length * 0.85  # Account for furniture/walls
else:
    max_viewing_distance = room_width * 0.85

# Calculate based on content type
if content_type == "ADM":
    min_image_height = (max_viewing_distance / 3438) * vertical_resolution
elif content_type == "BDM":
    element_height_percent = 0.04  # 4% for standard presentations
    min_image_height = (max_viewing_distance / 200) / element_height_percent
else:  # Passive viewing
    min_image_height = max_viewing_distance / 8

# Convert to diagonal (16:9 aspect ratio)
recommended_diagonal = min_image_height * 2.22

# Snap to available display sizes
available_sizes = [43, 55, 65, 75, 85, 98]
selected_size = min(size for size in available_sizes if size >= recommended_diagonal)
````

### Viewing Angle Considerations

  * **Horizontal Viewing Angles:**

      * Optimal: Within 30° of display center
      * Acceptable: Up to 45° from center
      * Maximum: 60° (image distortion becomes significant)

  * **Vertical Viewing Angles:**

      * Display center should be at seated eye height (42-48" from floor)
      * Maximum upward angle: 30° from eye level
      * Maximum downward angle: 15° from eye level

### BOQ Implementation:

```python
# Calculate seating positions
def validate_viewing_angles(room_width, display_width, seating_rows):
    optimal_viewing_zone = room_width * 0.6  # 60% of room width
    max_offset = display_width / 2 + (math.tan(math.radians(45)) * viewing_distance)

    # Ensure all seats within acceptable viewing angle
    for seat in seating_rows:
        horizontal_angle = math.degrees(math.atan(seat.offset / viewing_distance))
        if horizontal_angle > 45:
            return False, "Seating outside acceptable viewing angle"

    return True, "All seats within optimal viewing zone"
```

-----

## 2\. AVIXA A102.01:2017 - Audio Coverage Uniformity

### Audio Coverage Standards

  * **Speech Intelligibility Requirements:**
      * Target STI (Speech Transmission Index): ≥ 0.60 for general spaces
      * Target STI: ≥ 0.70 for critical communication (command centers, courtrooms)
      * Variation across listening area: ± 3 dB SPL (500Hz - 4kHz)

### Speaker Coverage Calculations:

```python
def calculate_speaker_coverage(room_area, ceiling_height, room_type):
    """
    Calculate required speaker quantity based on AVIXA A102.01
    """
    # Base coverage area per speaker
    if ceiling_height <= 9:
        coverage_per_speaker = 150  # sq ft
    elif ceiling_height <= 12:
        coverage_per_speaker = 200  # sq ft
    else:
        coverage_per_speaker = 250  # sq ft

    # Adjust for room type
    if room_type in ["Conference", "Meeting"]:
        coverage_per_speaker *= 0.8  # Tighter coverage for speech clarity
    elif room_type in ["Training", "Classroom"]:
        coverage_per_speaker *= 0.9

    # Calculate required speakers
    speakers_needed = math.ceil(room_area / coverage_per_speaker)

    # Minimum 2 speakers for stereo/redundancy
    return max(2, speakers_needed)
```

### Microphone Coverage

  * **Microphone Pickup Patterns:**
      * Cardioid: 120° coverage, 8-10 ft pickup radius
      * Supercardioid: 115° coverage, 10-12 ft pickup radius
      * Omnidirectional: 360° coverage, 6-8 ft pickup radius (ceiling mics)

### Microphone Spacing Calculations:

```python
def calculate_microphone_coverage(room_area, table_config):
    """
    Determine microphone quantity based on pickup patterns
    """
    if table_config == "round_table":
        # Boundary/table mics
        mic_coverage_area = 80  # sq ft per microphone
        mics_needed = math.ceil(room_area / mic_coverage_area)

    elif table_config == "conference_table":
        # Gooseneck/array mics
        mic_spacing_ft = 6  # feet between mics
        table_length = calculate_table_length(room_area)
        mics_needed = math.ceil(table_length / mic_spacing_ft)

    else:  # Open floor plan
        # Ceiling array mics
        mic_coverage_area = 150  # sq ft per ceiling mic
        mics_needed = math.ceil(room_area / mic_coverage_area)

    return max(2, mics_needed)  # Minimum 2 for redundancy
```

### Sound Pressure Level (SPL) Requirements

  * **Target SPL Levels:**
      * Background Music: 65-70 dB SPL
      * Speech Reinforcement: 70-75 dB SPL
      * Presentation Audio: 75-80 dB SPL
      * Large Event Spaces: 85-95 dB SPL

### SPL Calculation:

```python
def calculate_required_amplifier_power(room_volume, target_spl, speaker_sensitivity):
    """
    Calculate amplifier power needed to achieve target SPL
    Formula: Required Power = 10^((Target SPL - Speaker Sensitivity + 20log(Distance)) / 10)
    """
    # Distance to farthest listener
    distance_meters = calculate_farthest_listener_distance()

    # Account for room acoustics (RT60)
    if room_volume < 5000:  # cubic feet
        acoustic_loss = 3  # dB
    elif room_volume < 15000:
        acoustic_loss = 6
    else:
        acoustic_loss = 10

    adjusted_target_spl = target_spl + acoustic_loss

    # Power calculation
    power_watts = 10 ** ((adjusted_target_spl - speaker_sensitivity + 20 * math.log10(distance_meters)) / 10)

    # Add headroom (safety factor)
    recommended_power = power_watts * 2

    return recommended_power
```

-----

## 3\. Room Acoustics & Environmental Considerations

### Reverberation Time (RT60)

  * **Target RT60 by Room Type:**
      * Conference Rooms: 0.4 - 0.6 seconds
      * Training Rooms: 0.5 - 0.7 seconds
      * Auditoriums: 0.8 - 1.2 seconds
      * Lecture Halls: 0.6 - 0.9 seconds
      * Multipurpose Spaces: 0.6 - 0.8 seconds

### Acoustic Treatment Recommendations:

```python
def recommend_acoustic_treatment(room_volume, rt60_measured, room_type):
    """
    Recommend acoustic panels based on measured vs target RT60
    """
    target_rt60 = {
        "Conference": 0.5,
        "Training": 0.6,
        "Boardroom": 0.4,
        "Auditorium": 1.0
    }.get(room_type, 0.6)

    if rt60_measured > target_rt60 * 1.5:
        # Significant treatment needed
        panel_coverage = room_volume / 100  # sq ft of panels
        return {
            "treatment_level": "Heavy",
            "panel_area_sqft": panel_coverage,
            "panel_nrc": 0.85,  # High absorption
            "locations": ["ceiling", "rear_wall", "side_walls"]
        }

    elif rt60_measured > target_rt60 * 1.2:
        # Moderate treatment
        panel_coverage = room_volume / 150
        return {
            "treatment_level": "Moderate",
            "panel_area_sqft": panel_coverage,
            "panel_nrc": 0.70,
            "locations": ["rear_wall", "side_walls"]
        }

    else:
        return {"treatment_level": "Minimal", "panel_area_sqft": 0}
```

### Ambient Noise Requirements

  * **Maximum Background Noise Levels (NC/RC Ratings):**

      * Executive Conference Rooms: NC 25
      * Standard Conference Rooms: NC 30
      * Training Rooms: NC 35
      * Multipurpose Spaces: NC 35-40
      * Large Auditoriums: NC 30

  * **HVAC Coordination Requirements:**

      * Ductwork must not run directly above presentation areas
      * VAV boxes should be located away from microphone positions
      * Specify sound attenuators for supply/return ducts
      * Target air velocity in diffusers: \< 500 FPM (feet per minute)

-----

## 4\. Video System Design Standards

### Camera Coverage & Positioning

  * **Camera Field of View (FOV) Requirements:**

<!-- end list -->

```python
def calculate_camera_positioning(room_dimensions, participant_count):
    """
    Determine camera type, quantity, and positioning
    """
    room_length, room_width = room_dimensions
    room_area = room_length * room_width

    if participant_count <= 4:
        # Single fixed camera
        return {
            "camera_type": "Fixed Wide-Angle",
            "quantity": 1,
            "fov": "120°",
            "mounting": "Above display, centered",
            "height": "display_top + 6 inches"
        }

    elif participant_count <= 12:
        # PTZ camera with auto-framing
        return {
            "camera_type": "PTZ with AI Auto-Framing",
            "quantity": 1,
            "fov": "90° horizontal, 12x optical zoom",
            "mounting": "Ceiling or above display",
            "height": "8-10 ft from floor",
            "features": ["speaker_tracking", "auto_framing", "preset_positions"]
        }

    else:
        # Multi-camera system
        main_camera_distance = room_length * 0.6
        return {
            "camera_type": "Multi-Camera System",
            "quantity": 2,
            "primary": {
                "type": "PTZ",
                "position": "front_centered",
                "distance_from_table": main_camera_distance
            },
            "secondary": {
                "type": "Fixed Wide",
                "position": "rear_overview",
                "fov": "120°"
            }
        }
```

### Lighting Requirements for Video

  * **Illuminance Levels:**

      * Video Conferencing (HD): 300-500 lux vertical illuminance on faces
      * Video Conferencing (4K): 400-600 lux vertical illuminance
      * Broadcast/Recording: 500-800 lux

  * **Color Temperature:** 3200K - 5600K (consistent across room)

  * **Color Rendering Index (CRI):** ≥ 80 (≥ 90 for broadcast)

  * **Lighting Design Considerations:**

<!-- end list -->

```python
def specify_video_lighting(room_type, video_quality):
    """
    Specify lighting requirements for video applications
    """
    if video_quality == "4K_broadcast":
        return {
            "target_lux": 600,
            "color_temp_k": 5000,
            "cri_minimum": 90,
            "uniformity_ratio": "2:1",  # Foreground:background
            "control": "Dimming zones with presets",
            "features": ["key_light", "fill_light", "back_light"]
        }

    elif video_quality == "HD_conferencing":
        return {
            "target_lux": 450,
            "color_temp_k": 4000,
            "cri_minimum": 80,
            "uniformity_ratio": "2:1",
            "control": "Scene presets (meeting/presentation/video)",
            "features": ["overhead_soft_lighting", "no_direct_glare"]
        }

    else:  # Standard definition
        return {
            "target_lux": 300,
            "color_temp_k": 4000,
            "cri_minimum": 75,
            "control": "On/off or basic dimming"
        }
```

-----

## 5\. Network Infrastructure Requirements

### Network Bandwidth Calculations

  * **Video Conferencing Bandwidth:**

      * 720p HD Video: 1.5 - 2.5 Mbps per stream
      * 1080p Full HD: 2.5 - 4 Mbps per stream
      * 4K Video: 15 - 25 Mbps per stream
      * Multi-stream (Dual camera + content): 2x primary bandwidth

  * **AV over IP Bandwidth:**

      * 1080p60 (JPEG2000): 1 Gbps
      * 4K60 (H.264): 25 - 50 Mbps
      * 4K60 (Uncompressed): 12 - 18 Gbps

<!-- end list -->

```python
def calculate_network_requirements(room_equipment):
    """
    Calculate total network bandwidth and switch requirements
    """
    total_bandwidth = 0

    # Video conferencing codec
    if "video_codec" in room_equipment:
        codec_streams = room_equipment["cameras"] + 1  # +1 for content
        total_bandwidth += codec_streams * 4  # Mbps per 1080p stream

    # Networked displays (AV over IP)
    if "network_displays" in room_equipment:
        display_count = room_equipment["network_displays"]
        total_bandwidth += display_count * 50  # Mbps per 4K display

    # Control system
    total_bandwidth += 5  # Mbps for control traffic

    # Digital signage
    if "digital_signage" in room_equipment:
        total_bandwidth += 10  # Mbps per signage player

    # Calculate switch requirements
    required_ports = sum([
        room_equipment.get("cameras", 0),
        room_equipment.get("displays", 0),
        room_equipment.get("network_displays", 0),
        1,  # Codec/processor
        1,  # Control system
        2   # Spare ports
    ])

    # Recommend switch tier
    if total_bandwidth > 500:
        switch_type = "10GbE Managed Switch"
    elif total_bandwidth > 100:
        switch_type = "1GbE Managed Switch with SFP+ uplink"
    else:
        switch_type = "1GbE Managed Switch"

    return {
        "total_bandwidth_mbps": total_bandwidth,
        "switch_type": switch_type,
        "required_ports": required_ports,
        "recommended_ports": math.ceil(required_ports / 8) * 8,  # Round to 8/16/24/48
        "poe_required": True,
        "qos_required": True
    }
```

### QoS (Quality of Service) Configuration

  * **DSCP Marking Standards:**

      * Video: DSCP 34 (AF41) - Assured Forwarding
      * Audio: DSCP 46 (EF) - Expedited Forwarding
      * Control: DSCP 26 (AF31)
      * Signaling: DSCP 24 (CS3)

  * **VLAN Recommendations:**

<!-- end list -->

```python
def recommend_vlan_structure():
    return {
        "AV_Production": {
            "vlan_id": 10,
            "description": "Cameras, displays, AV over IP",
            "qos_priority": "High",
            "bandwidth_reserved": "50%"
        },
        "Video_Conferencing": {
            "vlan_id": 20,
            "description": "Codecs, video bars",
            "qos_priority": "Critical",
            "bandwidth_reserved": "30%"
        },
        "Control_Systems": {
            "vlan_id": 30,
            "description": "Touch panels, processors",
            "qos_priority": "Medium",
            "bandwidth_reserved": "10%"
        },
        "Management": {
            "vlan_id": 99,
            "description": "Device management, firmware updates",
            "qos_priority": "Low",
            "bandwidth_reserved": "10%"
        }
    }
```

-----

## 6\. Power & Electrical Requirements

### Power Consumption Calculations

  * **Equipment Power Draw (Typical):**
      * 55-65" Display: 150-250W
      * 75-85" Display: 300-450W
      * 98" Display: 500-700W
      * Video Conferencing Codec: 50-100W
      * PTZ Camera: 20-30W (PoE)
      * Amplifier (per channel, 100W): 200-300W actual draw
      * DSP Processor: 30-50W
      * Control Processor: 25-40W
      * Network Switch (24-port PoE): 200-400W

<!-- end list -->

```python
def calculate_power_requirements(boq_items):
    """
    Calculate total power load and circuit requirements
    """
    total_watts = 0
    poe_watts = 0

    power_ratings = {
        "55-65_inch_display": 200,
        "75-85_inch_display": 375,
        "98_inch_display": 600,
        "video_codec": 75,
        "ptz_camera_poe": 25,
        "amplifier_100w": 250,
        "dsp_processor": 40,
        "control_processor": 35,
        "network_switch_24port": 300
    }

    for item in boq_items:
        category = item["category"].lower()
        quantity = item["quantity"]

        # Match to power rating
        for key, watts in power_ratings.items():
            if key in category:
                if "poe" in key:
                    poe_watts += watts * quantity
                else:
                    total_watts += watts * quantity

    # Add 20% safety factor
    total_watts *= 1.2
    poe_watts *= 1.2

    # Calculate circuit requirements (120V systems)
    required_amps = total_watts / 120
    recommended_circuits = math.ceil(required_amps / 15)  # 15A circuits

    # If high power, use 20A circuits
    if required_amps > 30:
        recommended_circuits = math.ceil(required_amps / 20)
        circuit_rating = "20A"
    else:
        circuit_rating = "15A"

    return {
        "total_watts": total_watts,
        "poe_watts": poe_watts,
        "total_amps": required_amps,
        "recommended_circuits": recommended_circuits,
        "circuit_rating": circuit_rating,
        "ups_recommended": total_watts > 500,
        "ups_capacity_va": total_watts * 1.4 if total_watts > 500 else 0
    }
```

### UPS (Uninterruptible Power Supply) Sizing

  * **Runtime Requirements by Room Type:**
      * Small Huddle: 10-15 minutes (graceful shutdown)
      * Medium Conference: 15-30 minutes
      * Large Boardroom: 30-60 minutes
      * Mission Critical: 60+ minutes with generator backup

<!-- end list -->

```python
def specify_ups_system(total_watts, room_criticality):
    """
    Recommend UPS capacity based on load and runtime needs
    """
    runtime_minutes = {
        "low": 10,
        "medium": 20,
        "high": 45,
        "critical": 120
    }.get(room_criticality, 15)

    # UPS sizing formula: VA = Watts / Power Factor * Runtime Factor
    power_factor = 0.7  # Typical for AV equipment

    if runtime_minutes <= 15:
        runtime_factor = 1.4
    elif runtime_minutes <= 30:
        runtime_factor = 1.8
    elif runtime_minutes <= 60:
        runtime_factor = 2.5
    else:
        runtime_factor = 4.0

    required_va = (total_watts / power_factor) * runtime_factor

    # Round up to standard UPS sizes
    standard_sizes = [1000, 1500, 2200, 3000, 5000, 10000]
    ups_capacity_va = min(size for size in standard_sizes if size >= required_va)

    return {
        "ups_capacity_va": ups_capacity_va,
        "estimated_runtime_minutes": runtime_minutes,
        "form_factor": "Rack Mount" if ups_capacity_va > 2200 else "Tower/Rack",
        "features_required": [
            "Automatic Voltage Regulation (AVR)",
            "LCD Display",
            "Network Management Card",
            "Graceful Shutdown Software"
        ]
    }
```

-----

## 7\. Cabling & Infrastructure Standards

### Cable Categories & Applications

  * **Copper Cabling:**

      * Cat 5e: Up to 1 Gbps, 100 meters, suitable for basic AV control
      * Cat 6: Up to 10 Gbps (55m), 100 meters @ 1Gbps, recommended minimum
      * Cat 6A: Up to 10 Gbps (100m), shielded, best for AV over IP
      * Cat 8: Up to 40 Gbps (30m), data center applications

  * **Fiber Optic:**

      * OM3 Multimode: 10 Gbps up to 300m
      * OM4 Multimode: 10 Gbps up to 550m, 40 Gbps up to 150m
      * OS2 Single-Mode: 10+ Gbps, distances \> 1 km

  * **HDMI Over Distance:**

      * HDMI Direct: 4K60 up to 15 ft (high-quality cables)
      * HDMI Optical: 4K60 up to 300 ft
      * HDBaseT (Cat6A): 4K60 up to 330 ft (100m)
      * HDMI Over Fiber: 4K60 up to 10 km

### Cable Pathways & Conduit Fill

  * **Conduit Fill Ratios (NEC Article 344):**
      * 1 Cable: 53% fill
      * 2 Cables: 31% fill
      * 3+ Cables: 40% fill

<!-- end list -->

```python
def calculate_conduit_size(cable_list):
    """
    Determine required conduit size based on cable count and diameter
    """
    # Cable cross-sectional areas (sq inches)
    cable_areas = {
        "cat6": 0.0325,
        "cat6a": 0.0425,
        "hdmi": 0.0450,
        "fiber_duplex": 0.0200,
        "power_14awg": 0.0190
    }

    total_cable_area = sum(cable_areas[cable["type"]] * cable["count"]
                           for cable in cable_list)

    # Determine fill ratio
    cable_count = sum(cable["count"] for cable in cable_list)
    if cable_count == 1:
        fill_ratio = 0.53
    elif cable_count == 2:
        fill_ratio = 0.31
    else:
        fill_ratio = 0.40

    # Calculate required conduit area
    required_conduit_area = total_cable_area / fill_ratio

    # Match to standard EMT conduit sizes (inner diameter area)
    conduit_sizes = {
        "1/2 inch": 0.304,
        "3/4 inch": 0.533,
        "1 inch": 0.864,
        "1-1/4 inch": 1.496,
        "1-1/2 inch": 2.036,
        "2 inch": 3.356
    }

    for size, area in conduit_sizes.items():
        if area >= required_conduit_area:
            return {
                "conduit_size": size,
                "fill_percentage": (total_cable_area / area) * 100,
                "cable_count": cable_count
            }

    return {"conduit_size": "2+ inch", "note": "Requires larger conduit or multiple runs"}
```

### Cable Labeling Standards (AVIXA CLAS)

  * **Label Format:**
    `[System]-[Endpoint]-[Signal Type]-[Number]`

  * **Examples:**

      * `CONF-DSP-AUDIO-01`
      * `CONF-DISP1-HDMI-01`
      * `CONF-CAM-PTZ-01`

  * **Implementation in BOQ:**

<!-- end list -->

```python
def generate_cable_schedule(room_name, boq_items):
    """
    Create comprehensive cable labeling schedule
    """
    cable_schedule = []

    system_prefix = room_name[:4].upper()  # "CONF", "TRAIN", etc.

    # Audio cables
    audio_devices = [item for item in boq_items if item["category"] == "Audio"]
    for i, device in enumerate(audio_devices, 1):
        cable_schedule.append({
            "cable_id": f"{system_prefix}-DSP-AUDIO-{i:02d}",
            "from": device["name"],
            "to": "DSP Matrix Input",
            "cable_type": "XLR Balanced Audio",
            "length_ft": "Est. based on rack location"
        })

    # Video cables
    displays = [item for item in boq_items if "Display" in item["category"]]
    for i, display in enumerate(displays, 1):
        cable_schedule.append({
            "cable_id": f"{system_prefix}-DISP{i}-HDMI-01",
            "from": "Video Matrix Output",
            "to": f"Display {i}",
            "cable_type": "HDMI 2.0 or HDBaseT",
            "length_ft": "Est. based on display location"
        })

    return cable_schedule
```

-----

## 8\. Control System Integration

### Control System Architecture

  * **System Types:**
      * Small Rooms (\< 150 sq ft): Native device control (Teams/Zoom app)
      * Medium Rooms (150-400 sq ft): Dedicated touch panel + processor
      * Large Rooms (400+ sq ft): Advanced control processor + multiple interfaces

<!-- end list -->

```python
def specify_control_system(room_area, equipment_complexity):
    """
    Determine appropriate control system based on room size and equipment
    """
    device_count = len(equipment_complexity["controllable_devices"])

    if room_area < 150 and device_count <= 5:
        # Simple native control
        return {
            "control_type": "Native Device Control",
            "interface": "Built-in touch panel on codec/video bar",
            "processor": "Not required",
            "complexity": "Low"
        }

    elif room_area < 400 and device_count <= 15:
        # Standard touch panel control
        return {
            "control_type": "Dedicated Control System",
            "processor": "Single-core control processor",
            "interface": "10-inch wall-mount touch panel",
            "features": [
                "Source selection",
                "Volume control",
                "Display power",
                "Lighting presets",
                "Video conferencing start/stop"
            ],
            "programming_hours": 16
        }

    else:
        # Advanced programmable control
        return {
            "control_type": "Enterprise Control System",
            "processor": "Multi-core control processor",
            "interface": "Multiple touch panels + mobile app",
            "features": [
                "Advanced source routing",
                "Camera presets",
                "Multi-zone audio",
                "Lighting/shade integration",
                "Room scheduling integration",
                "Remote monitoring",
                "Help desk integration"
            ],
            "programming_hours": 40,
            "additional_hardware": [
                "Relay modules for lighting control",
                "IR/RS-232 control interfaces",
                "Network switch for control network"
            ]
        }
```

### User Interface Design Principles

  * **Touch Panel Page Structure:**

      * Home Page - System power on/off, source selection
      * Source Control - Laptop input, wireless sharing, Blu-ray, etc.
      * Video Conference - Start/end meeting, camera control, layout selection
      * Audio Control - Volume, microphone muting, preset audio scenes
      * Environmental - Lighting presets, shade control, temperature
      * Help - Support contact, system diagram, troubleshooting

  * **Button Layout Standards:**

      * Minimum button size: 0.5" x 0.5" (touch target)
      * Spacing between buttons: 0.1" minimum
      * Common functions: Bottom toolbar (volume, mute, help)
      * Emergency controls: Large, red, always visible

-----

## 9\. Room Type Specifications & Equipment Matrices

### Small Huddle Room (2-4 People, 40-150 sq ft)

  * **Dimensions:** 8-12 ft length × 6-10 ft width × 8-10 ft ceiling
  * **Required Equipment:**

<!-- end list -->

```python
{
    "Display": {
        "size": "43-55 inches",
        "type": "Commercial 4K Display with USB-C",
        "quantity": 1,
        "mounting": "Articulating wall mount",
        "height_from_floor": "42-48 inches to center"
    },
    "Video_Conferencing": {
        "type": "All-in-One Video Bar",
        "features": [
            "Integrated camera (120° FOV)",
            "Built-in speakers and microphones",
            "USB connectivity to laptop",
            "4K video capability",
            "AI auto-framing"
        ],
        "quantity": 1,
        "mounting": "Below or above display"
    },
    "Connectivity": {
        "primary": "USB-C single-cable (video + USB + 60-100W power)",
        "secondary": "HDMI + USB-A for legacy devices",
        "wireless": "Built-in wireless presentation",
        "network": "1 Gbps Ethernet, PoE+ capable"
    },
    "Control": {
        "type": "Native (Teams/Zoom Rooms interface on touch display)",
        "additional": "Optional table-mount touch controller"
    },
    "Power": {
        "total_load": "300-500W",
        "circuit": "Single 15A circuit adequate",
        "ups": "Optional 650VA for 15-min backup"
    },
    "Cabling": {
        "data": "2x Cat6A (display, video bar)",
        "video": "1x HDMI 2.0 (backup connection)",
        "power": "Dedicated outlets behind display and table"
    },
    "Installation_Hours": 6,
    "Programming_Hours": 2,
    "Budget_Range_USD": "8000-15000"
}
```

### Medium Conference Room (5-12 People, 150-400 sq ft)

  * **Dimensions:** 12-20 ft length × 10-16 ft width × 9-12 ft ceiling
  * **Required Equipment:**

<!-- end list -->

```python
{
    "Display": {
        "configuration": "Single large or dual displays",
        "primary": {
            "size": "65-75 inches (single) or 55-65 inches (dual)",
            "type": "Commercial 4K Display",
            "quantity": "1-2",
            "purpose": "Content + camera feed"
        },
        "alternative": "Single 86-98 inch for budget optimization",
        "mounting": "Fixed wall mount or floor stand",
        "height": "Center at 48-54 inches from floor"
    },
    "Video_System": {
        "codec": {
            "type": "Dedicated video conferencing codec",
            "platform": "Microsoft Teams Rooms / Zoom Rooms certified",
            "video_quality": "4K capable",
            "quantity": 1
        },
        "camera": {
            "type": "PTZ camera with auto-framing",
            "fov": "120° horizontal",
            "mounting": "Center above display(s), 8-10 ft from table",
            "features": ["Speaker tracking", "Preset positions", "4K capture"],
            "quantity": 1
        }
    },
    "Audio_System": {
        "dsp": {
            "type": "Digital Signal Processor",
            "channels": "Minimum 4 input, 4 output",
            "features": ["AEC", "AGC", "Noise reduction", "Dante capable"],
            "quantity": 1
        },
        "microphones": {
            "option_1": {
                "type": "Ceiling microphone array",
                "coverage": "One per 150 sq ft",
                "quantity": "2-3",
                "note": "Aesthetic preference, requires ceiling height > 9 ft"
            },
            "option_2": {
                "type": "Table boundary microphones",
                "coverage": "One per 80 sq ft",
                "quantity": "2-4",
                "note": "Better performance, more flexible positioning"
            }
        },
        "speakers": {
            "type": "Ceiling speakers (not TV speakers)",
            "quantity": "4-6 in zones",
            "coverage": "±3dB variation 500Hz-4kHz",
            "mounting": "Distributed ceiling coverage"
        },
        "amplification": {
            "type": "4-channel amplifier",
            "power_per_channel": "50-100W",
            "quantity": 1
        }
    },
    "Connectivity": {
        "table_connectivity_box": {
            "inputs": ["HDMI", "USB-C", "USB-A", "Network"],
            "quantity": "1-2 (based on table size)"
        },
        "wireless_presentation": {
            "type": "Enterprise wireless presentation system",
            "quantity": 1,
            "features": ["Multi-user", "AirPlay/Miracast", "Moderation"]
        }
    },
    "Control_System": {
        "processor": "Dedicated control processor",
        "interface": "10-inch wall-mount touch panel",
        "features": [
            "Source selection",
            "Camera control",
            "Audio presets",
            "Display power",
            "Lighting integration ready"
        ],
        "programming_hours": 16
    },
    "Infrastructure": {
        "rack": "Wall-mount 12U rack or furniture-integrated",
        "power": {
            "total_load": "800-1500W",
            "circuit": "Dedicated 20A circuit recommended",
            "ups": "1500VA UPS for 30-min backup"
        },
        "network": {
            "bandwidth": "25 Mbps minimum per endpoint",
            "vlan": "Dedicated AV VLAN with QoS",
            "switch_ports": "8-port managed PoE+ switch"
        }
    },
    "Cabling": {
        "data": "6-12x Cat6A (cameras, mics, displays, control)",
        "audio": "4-8x Balanced XLR (microphones to DSP)",
        "video": "2-4x HDMI 2.1 or HDBaseT",
        "conduit": "2-3 conduit runs (1.5-2 inch)"
    },
    "Installation_Hours": 20,
    "Programming_Hours": 16,
    "Commissioning_Hours": 4,
    "Budget_Range_USD": "25000-50000"
}
```

### Microphone Selection Logic:

```python
def select_microphone_type(ceiling_height, aesthetic_priority, budget):
    """
    Decision tree for microphone selection in medium conference rooms
    """
    if ceiling_height < 9:
        return {
            "type": "Table boundary microphones",
            "reason": "Ceiling height insufficient for ceiling mics"
        }

    if aesthetic_priority == "high" and budget == "premium":
        return {
            "type": "Ceiling array microphones",
            "reason": "Clean aesthetic, no table clutter",
            "note": "Requires acoustic treatment if RT60 > 0.6s"
        }

    return {
        "type": "Table boundary microphones",
        "reason": "Best performance-to-cost ratio, flexible positioning"
    }
```

### Large Boardroom / Executive Conference (12-20 People, 400-800 sq ft)

  * **Dimensions:** 20-35 ft length × 16-24 ft width × 10-14 ft ceiling
  * **Required Equipment:**

<!-- end list -->

```python
{
    "Display_System": {
        "configuration": "Dual large displays + confidence monitor",
        "main_displays": {
            "size": "75-98 inches each",
            "type": "Commercial 4K LCD or Fine-Pitch LED",
            "quantity": 2,
            "mounting": "Fixed wall mount, side-by-side",
            "purpose": "Content + video conferencing"
        },
        "confidence_monitor": {
            "size": "43-55 inches",
            "location": "Presenter area or credenza",
            "purpose": "Presenter preview"
        }
    },
    "Video_System": {
        "codec": {
            "type": "High-performance video codec",
            "platform": "Dual-platform capable (Teams + Zoom)",
            "video_quality": "4K, multi-stream capable",
            "quantity": 1
        },
        "cameras": {
            "primary": {
                "type": "PTZ camera with AI tracking",
                "resolution": "4K",
                "fov": "Wide-angle with 12x optical zoom",
                "mounting": "Ceiling center or above display",
                "quantity": 1
            },
            "secondary": {
                "type": "Fixed wide-angle camera",
                "resolution": "4K",
                "purpose": "Room overview, backup",
                "quantity": 1
            },
            "optional": {
                "type": "Document camera",
                "resolution": "4K",
                "purpose": "Physical document sharing"
            }
        }
    },
    "Audio_System": {
        "dsp": {
            "type": "Networked audio processor (Dante/AVB)",
            "channels": "16+ input, 8+ output",
            "features": [
                "Multi-channel AEC with reference signals",
                "Automatic mixing with priority",
                "Zone-based processing",
                "Recording capability"
            ],
            "quantity": 1
        },
        "microphones": {
            "type": "Ceiling-mount steerable array (e.g., Shure MXA920)",
            "quantity": "2-4 based on room dimensions",
            "features": [
                "Multiple virtual pickup lobes",
                "Automatic speaker tracking",
                "Zone-based coverage",
                "Dante networked audio"
            ],
            "alternative": "Tabletop gooseneck array with logic mixing"
        },
        "speakers": {
            "type": "Premium ceiling speakers in zones",
            "quantity": "8-12 speakers in 4 zones",
            "coverage": "Voice lift + video conferencing",
            "mounting": "Distributed for ±2dB uniformity"
        },
        "amplification": {
            "type": "Networked multi-channel amplifier",
            "channels": "8+ channels",
            "power_per_channel": "100-200W",
            "features": ["Dante audio", "Individual channel monitoring"]
        }
    },
    "Signal_Management": {
        "matrix_switcher": {
            "type": "4K Video Matrix Switcher",
            "inputs": "8-12 (HDMI, HDBaseT)",
            "outputs": "4-6",
            "features": ["Seamless switching", "HDCP 2.2", "Scaling"],
            "quantity": 1
        },
        "presentation_system": {
            "type": "Enterprise wireless presentation gateway",
            "capacity": "32+ concurrent users",
            "outputs": "Multiple simultaneous streams"
        }
    },
    "Control_System": {
        "processor": "Advanced programmable control processor",
        "interfaces": {
            "primary": "15-inch wall-mount touch panel",
            "secondary": "10-inch tabletop touch panel",
            "mobile": "iOS/Android control app"
        },
        "integrations": [
            "Lighting control (DMX/DALI)",
            "Motorized shades",
            "HVAC integration",
            "Room scheduling display",
            "Help desk integration"
        ],
        "programming_hours": 40
    },
    "Infrastructure": {
        "rack": {
            "type": "Full-size equipment rack",
            "size": "24-42U",
            "features": [
                "Environmental monitoring",
                "Cooling fans or AC unit",
                "Cable management",
                "Glass or vented door"
            ],
            "location": "In-room credenza or adjacent equipment room"
        },
        "power": {
            "total_load": "2000-4000W",
            "circuits": "Multiple dedicated 20A circuits",
            "ups": {
                "capacity": "3000VA minimum",
                "runtime": "60 minutes",
                "features": ["Automatic failover", "Network monitoring"]
            }
        },
        "network": {
            "bandwidth": "100 Mbps minimum per codec",
            "switch": "24-port managed PoE++ switch with 10G uplink",
            "redundancy": "Dual network paths for critical systems"
        },
        "cooling": {
            "requirement": "Dedicated HVAC or in-rack cooling",
            "target_temp": "68-75°F (20-24°C)",
            "humidity": "30-50% RH"
        }
    },
    "Cabling": {
        "data": "20+ Cat6A runs (Dante audio, control, cameras)",
        "video": "6-10 HDBaseT or fiber runs for 4K distribution",
        "audio": "16+ XLR balanced audio (if not using Dante)",
        "power": "Multiple conditioned power runs",
        "fiber": "Optional for long-distance 4K (>100m)",
        "conduit": "Multiple 2-inch conduit runs + cable trays"
    },
    "Specialized_Features": {
        "recording": {
            "type": "Integrated recording system",
            "capability": "Multi-camera switching, content capture",
            "storage": "Network-attached or cloud-based"
        },
        "streaming": {
            "capability": "Live streaming to corporate network",
            "platforms": "Teams Live, Zoom Webinar, YouTube"
        },
        "assistive_listening": {
            "type": "IR or FM assistive listening system",
            "requirement": "ADA compliance for >50 person capacity",
            "coverage": "4% of seating, minimum 2 units"
        }
    },
    "Installation_Hours": 60,
    "Programming_Hours": 40,
    "Commissioning_Hours": 8,
    "Training_Hours": 4,
    "Budget_Range_USD": "75000-200000"
}
```

### Training Room / Classroom (20-40 People, 600-1200 sq ft)

  * **Dimensions:** 30-45 ft length × 20-30 ft width × 10-14 ft ceiling
  * **Required Equipment:**

<!-- end list -->

```python
{
    "Display_System": {
        "primary": {
            "type": "Laser projector (5000+ lumens) with ALR screen",
            "size": "120-150 inch diagonal (16:10 aspect)",
            "resolution": "WUXGA (1920x1200) minimum",
            "mounting": "Ceiling-recessed projector, motorized screen",
            "alternative": "Dual 86-98 inch displays for smaller rooms"
        },
        "secondary": {
            "type": "Student collaboration displays",
            "size": "55-65 inches",
            "quantity": "2-4 around perimeter",
            "purpose": "Small group breakout work"
        }
    },
    "Audio_System": {
        "instructor_reinforcement": {
            "microphone": {
                "type": "Wireless lavalier or headset",
                "quantity": 2,
                "features": ["Diversity receiver", "Rechargeable"]
            },
            "speakers": {
                "type": "Ceiling speakers + optional front soundbar",
                "quantity": "12-16 ceiling + 1 soundbar",
                "coverage": "Uniform 75-80 dB SPL at student positions"
            }
        },
        "student_response": {
            "type": "Handheld wireless microphones",
            "quantity": "2-4",
            "features": ["Quick-mute", "LED status indicator"]
        },
        "dsp": {
            "type": "Dante-enabled DSP",
            "features": [
                "Automatic mic mixing (8+ channels)",
                "Acoustic echo cancellation",
                "Recording output",
                "Zone-based speaker control"
            ]
        }
    },
    "Lecture_Capture": {
        "cameras": {
            "instructor": {
                "type": "PTZ camera with auto-tracking",
                "resolution": "4K",
                "quantity": 1
            },
            "audience": {
                "type": "Fixed wide-angle camera",
                "resolution": "1080p",
                "quantity": 1
            }
        },
        "recording_system": {
            "type": "Automated lecture capture system",
            "inputs": ["2x camera feeds", "Presentation content", "Audio"],
            "output": "Streaming + local recording",
            "integration": "LMS integration (Moodle, Canvas, Blackboard)"
        }
    },
    "Instructor_Station": {
        "lectern": {
            "type": "Multimedia lectern with integrated control",
            "features": [
                "Built-in PC (OPS module)",
                "Document camera",
                "Touch panel control",
                "Wireless mic charging",
                "Gooseneck mic",
                "HDMI/USB-C input",
                "Storage drawer"
            ]
        },
        "additional": {
            "type": "Wireless keyboard/mouse",
            "quantity": 1
        }
    },
    "Student_Response_System": {
        "type": "Interactive polling/feedback system",
        "method": "Web-based (BYOD) or dedicated clickers",
        "integration": "Presentation software integration"
    },
    "Control_System": {
        "processor": "Education-focused control system",
        "interface": "Lectern-mount touch panel + wall panel",
        "presets": [
            "Lecture mode",
            "Presentation mode",
            "Video conferencing",
            "Breakout groups",
            "All-off"
        ],
        "features": [
            "Display/projector control",
            "Lighting scenes",
            "Motorized screen control",
            "Audio source routing",
            "Camera preset recall"
        ]
    },
    "Infrastructure": {
        "power": {
            "total_load": "3000-5000W",
            "circuits": "Multiple 20A circuits",
            "ups": "2200VA for critical equipment (30-min runtime)"
        },
        "network": {
            "bandwidth": "50 Mbps for recording/streaming",
            "wifi": "High-density Wi-Fi for student devices (40+ concurrent)",
            "wired": "Gigabit connections for AV equipment"
        },
        "rack": "Equipment room adjacent to classroom (24U rack)"
    },
    "Installation_Hours": 50,
    "Programming_Hours": 24,
    "Training_Hours": 6,
    "Budget_Range_USD": "60000-150000"
}
```

### Auditorium / Large Event Space (100-500 People, 2000-10000 sq ft)

  * **Dimensions:** Variable, typically 50-100 ft length × 40-80 ft width × 16-30 ft ceiling
  * **Required Equipment (Summary - Highly Complex):**

<!-- end list -->

```python
{
    "Display": "LED video wall (3mm-5mm pixel pitch) or large-venue projectors (10000+ lumens)",
    "Audio": "Line array speakers, distributed delay speakers, professional mixing console",
    "Video": "Multi-camera production system with video switcher",
    "Lighting": "Theatrical lighting with DMX control",
    "Control": "Central control room with multi-operator capability",
    "Installation_Hours": 200,
    "Programming_Hours": 80,
    "Budget_Range_USD": "250000-1000000+"
}
```

*(Note: Auditorium systems require specialized consultants and are beyond typical automated BOQ generation)*

-----

## 10\. AVIXA 10:2013 - Performance Verification Standards

### Verification Test Categories

The AVIXA 10:2013 standard defines 160+ verification criteria across these categories:

  * Display Performance Tests
  * Audio Performance Tests
  * Video Performance Tests
  * Control System Tests
  * Network & Connectivity Tests
  * Integration Tests
  * Safety & Compliance Tests

### Key Verification Tests for BOQ Generator

```python
def generate_verification_checklist(room_type, boq_items):
    """
    Generate project-specific verification checklist based on AVIXA 10:2013
    """

    verification_plan = {
        "project_info": {
            "room_type": room_type,
            "verification_standard": "AVIXA 10:2013",
            "test_date": "To be scheduled post-installation"
        },
        "tests": []
    }

    # Display verification tests
    if any("Display" in item["category"] for item in boq_items):
        verification_plan["tests"].extend([
            {
                "test_id": "DISP-001",
                "category": "Display Performance",
                "test": "Display Image Size Verification",
                "method": "Measure actual display diagonal, verify against DISCAS calculations",
                "acceptance_criteria": "Within ±2 inches of specified size",
                "priority": "Critical"
            },
            {
                "test_id": "DISP-002",
                "category": "Display Performance",
                "test": "Display Resolution & Scaling",
                "method": "Display native resolution test pattern, verify 1:1 pixel mapping",
                "acceptance_criteria": "No scaling artifacts, text readable from farthest seat",
                "priority": "Critical"
            },
            {
                "test_id": "DISP-003",
                "category": "Display Performance",
                "test": "Display Brightness & Uniformity",
                "method": "Measure center and 9-point grid luminance with meter",
                "acceptance_criteria": "Center brightness ≥ spec, uniformity within 20%",
                "priority": "High"
            },
            {
                "test_id": "DISP-004",
                "category": "Display Performance",
                "test": "Viewing Angle Test",
                "method": "Verify image quality from extreme seating positions",
                "acceptance_criteria": "Readable from all seats within specified viewing angles",
                "priority": "High"
            }
        ])

    # Audio verification tests
    if any("Audio" in item["category"] for item in boq_items):
        verification_plan["tests"].extend([
            {
                "test_id": "AUDIO-001",
                "category": "Audio Performance",
                "test": "SPL Uniformity (AVIXA A102.01)",
                "method": "Measure SPL at 6+ positions across room with pink noise",
                "acceptance_criteria": "±3 dB variation 500Hz-4kHz across listening area",
                "priority": "Critical"
            },
            {
                "test_id": "AUDIO-002",
                "category": "Audio Performance",
                "test": "Speech Intelligibility (STI)",
                "method": "Measure STI at farthest listening position",
                "acceptance_criteria": "STI ≥ 0.60 (≥0.70 for critical spaces)",
                "priority": "Critical"
            },
            {
                "test_id": "AUDIO-003",
                "category": "Audio Performance",
                "test": "Microphone Pickup Verification",
                "method": "Speak from each seating position, verify clear pickup",
                "acceptance_criteria": "All positions captured without clipping or dropouts",
                "priority": "Critical"
            },
            {
                "test_id": "AUDIO-004",
                "category": "Audio Performance",
                "test": "Acoustic Echo Cancellation",
                "method": "Full-duplex conversation test with far-end audio",
                "acceptance_criteria": "No audible echo or feedback during conversation",
                "priority": "Critical"
            },
            {
                "test_id": "AUDIO-005",
                "category": "Audio Performance",
                "test": "Background Noise Level",
                "method": "Measure ambient noise with HVAC operating",
                "acceptance_criteria": f"NC {get_target_nc(room_type)} or lower",
                "priority": "High"
            }
        ])

    # Video conferencing tests
    if any("Video Conferencing" in item.get("sub_category", "") for item in boq_items):
        verification_plan["tests"].extend([
            {
                "test_id": "VC-001",
                "category": "Video Conferencing",
                "test": "Camera Coverage & Framing",
                "method": "Verify all seating positions visible in camera frame",
                "acceptance_criteria": "All participants visible, proper headroom/framing",
                "priority": "Critical"
            },
            {
                "test_id": "VC-002",
                "category": "Video Conferencing",
                "test": "Video Call Quality",
                "method": "Conduct 15-minute test call with far-end participant",
                "acceptance_criteria": "1080p video, no dropouts, < 200ms latency",
                "priority": "Critical"
            },
            {
                "test_id": "VC-003",
                "category": "Video Conferencing",
                "test": "Auto-Framing & Tracking",
                "method": "Test camera auto-framing with participants moving",
                "acceptance_criteria": "Smooth tracking, appropriate framing adjustments",
                "priority": "High"
            }
        ])

    # Control system tests
    if any("Control" in item["category"] for item in boq_items):
        verification_plan["tests"].extend([
            {
                "test_id": "CTRL-001",
                "category": "Control System",
                "test": "User Interface Functionality",
                "method": "Test all buttons, sliders, and page navigation",
                "acceptance_criteria": "All controls respond within 2 seconds",
                "priority": "Critical"
            },
            {
                "test_id": "CTRL-002",
                "category": "Control System",
                "test": "Source Selection & Routing",
                "method": "Test all source inputs to all display outputs",
                "acceptance_criteria": "Correct source displayed on selected output",
                "priority": "Critical"
            },
            {
                "test_id": "CTRL-003",
                "category": "Control System",
                "test": "System Power-On Sequence",
                "method": "Activate system from powered-off state",
                "acceptance_criteria": "All devices power on in correct sequence",
                "priority": "High"
            }
        ])

    # Integration tests
    verification_plan["tests"].extend([
        {
            "test_id": "INT-001",
            "category": "System Integration",
            "test": "Fire Alarm Integration",
            "method": "Simulate fire alarm activation",
            "acceptance_criteria": "AV system mutes audio, displays emergency message",
            "priority": "Critical"
        },
        {
            "test_id": "INT-002",
            "category": "System Integration",
            "test": "Lighting Preset Recall",
            "method": "Test all lighting scenes from AV control system",
            "acceptance_criteria": "Lights adjust to correct levels within 3 seconds",
            "priority": "Medium"
        }
    ])

    return verification_plan
```

### Verification Report Format

```python
def generate_verification_report(test_results):
    """
    Create AVIXA 10:2013 compliant verification report
    """

    report = {
        "report_header": {
            "project_name": "...",
            "room_name": "...",
            "verification_date": "...",
            "performed_by": "...",
            "standard_reference": "AVIXA 10:2013"
        },
        "executive_summary": {
            "total_tests": len(test_results),
            "passed": sum(1 for t in test_results if t["status"] == "Pass"),
            "failed": sum(1 for t in test_results if t["status"] == "Fail"),
            "deferred": sum(1 for t in test_results if t["status"] == "Deferred"),
            "overall_status": "Pass" if all(t["status"] != "Fail" for t in test_results) else "Fail with exceptions"
        },
        "test_results": test_results,
        "failed_tests_action_plan": [
            {
                "test_id": t["test_id"],
                "issue": t["notes"],
                "corrective_action": t["corrective_action"],
                "retest_date": t["retest_date"]
            }
            for t in test_results if t["status"] == "Fail"
        ],
        "recommendations": [],
        "sign_off": {
            "installer": {"name": "", "signature": "", "date": ""},
            "client": {"name": "", "signature": "", "date": ""}
        }
    }

    return report
```

-----

## 11\. Cost Estimation Framework

### Equipment Cost Structure

  * **Typical Cost Distribution (% of total project):**

<!-- end list -->

```python
cost_distribution = {
    "Displays & Projectors": 0.30,      # 30%
    "Audio Systems": 0.25,              # 25%
    "Video Conferencing": 0.15,         # 15%
    "Control & Signal Management": 0.10, # 10%
    "Cabling & Infrastructure": 0.05,   # 5%
    "Installation Labor": 0.10,         # 10%
    "Programming & Commissioning": 0.05   # 5%
}
```

### Installation Time Multipliers

```python
def calculate_installation_time(base_hours, project_factors):
    """
    Adjust installation time based on project complexity
    """

    multiplier = 1.0

    # Complexity factors
    if project_factors["programming_required"] == "advanced":
        multiplier *= 1.5

    if project_factors["building_system_integration"]:
        multiplier *= 1.3

    if project_factors["custom_furniture_integration"]:
        multiplier *= 1.4

    if project_factors["project_type"] == "retrofit":
        multiplier *= 2.0  # Renovation projects take longer
    elif project_factors["project_type"] == "new_construction":
        multiplier *= 0.9  # New construction slightly faster

    if project_factors["ceiling_height"] > 14:
        multiplier *= 1.3  # Lifts and safety equipment needed

    if project_factors["site_access"] == "restricted":
        multiplier *= 1.2  # Limited working hours

    adjusted_hours = base_hours * multiplier

    return {
        "base_hours": base_hours,
        "multiplier": multiplier,
        "adjusted_hours": adjusted_hours,
        "factors_applied": project_factors
    }
```

### Regional Pricing Adjustments

```python
def apply_regional_pricing(base_price_usd, region, currency):
    """
    Adjust pricing based on geographic region and currency
    """

    regional_multipliers = {
        "India_Metro": 0.85,      # Mumbai, Delhi, Bangalore
        "India_Tier2": 0.75,      # Pune, Ahmedabad, Hyderabad
        "India_Tier3": 0.70,      # Smaller cities
        "Middle_East": 1.15,      # UAE, Saudi Arabia
        "Southeast_Asia": 0.90,   # Singapore, Malaysia
        "US_Major": 1.00,         # Baseline
        "Europe": 1.10
    }

    exchange_rates = {
        "INR": 83.5,
        "USD": 1.0,
        "AED": 3.67,
        "EUR": 0.92,
        "GBP": 0.79
    }

    multiplier = regional_multipliers.get(region, 1.0)
    adjusted_price_usd = base_price_usd * multiplier

    if currency != "USD":
        final_price = adjusted_price_usd * exchange_rates[currency]
    else:
        final_price = adjusted_price_usd

    return {
        "base_price_usd": base_price_usd,
        "regional_multiplier": multiplier,
        "adjusted_price_usd": adjusted_price_usd,
        "final_price": final_price,
        "currency": currency,
        "exchange_rate": exchange_rates[currency]
    }
```

### Service & Support Cost Structure

```python
def calculate_service_costs(equipment_total, service_tier):
    """
    Calculate warranty, maintenance, and support costs
    """

    service_tiers = {
        "Basic": {
            "warranty_years": 3,
            "warranty_cost_percent": 0.05,     # 5% of equipment
            "annual_maintenance_percent": 0.12, # 12% per year
            "response_time": "Next business day",
            "coverage_hours": "9x5"
        },
        "Standard": {
            "warranty_years": 5,
            "warranty_cost_percent": 0.08,
            "annual_maintenance_percent": 0.15,
            "response_time": "4 hours",
            "coverage_hours": "9x5"
        },
        "Premium": {
            "warranty_years": 7,
            "warranty_cost_percent": 0.12,
            "annual_maintenance_percent": 0.20,
            "response_time": "2 hours",
            "coverage_hours": "24x7",
            "includes": ["Remote monitoring", "Preventive maintenance quarterly"]
        }
    }

    tier = service_tiers[service_tier]

    warranty_cost = equipment_total * tier["warranty_cost_percent"]
    annual_maintenance = equipment_total * tier["annual_maintenance_percent"]

    return {
        "warranty": {
            "years": tier["warranty_years"],
            "cost": warranty_cost,
            "coverage": "Parts and labor"
        },
        "maintenance_contract": {
            "annual_cost": annual_maintenance,
            "response_time": tier["response_time"],
            "coverage_hours": tier["coverage_hours"],
            "includes": tier.get("includes", ["Standard support"])
        },
        "total_year_1": warranty_cost + annual_maintenance,
        "total_5_years": warranty_cost + (annual_maintenance * 5)
    }
```

### Project Management & Installation Overhead

```python
def calculate_project_overhead(equipment_subtotal, project_complexity):
    """
    Calculate project management, design, and overhead costs
    """

    overhead_structure = {
        "Simple": {
            "project_management": 0.08,     # 8%
            "design_engineering": 0.05,     # 5%
            "site_supervision": 0.03,       # 3%
            "documentation": 0.02,          # 2%
            "contingency": 0.05             # 5%
        },
        "Standard": {
            "project_management": 0.10,     # 10%
            "design_engineering": 0.08,     # 8%
            "site_supervision": 0.05,       # 5%
            "documentation": 0.03,          # 3%
            "commissioning": 0.02,          # 2%
            "contingency": 0.08             # 8%
        },
        "Complex": {
            "project_management": 0.15,     # 15%
            "design_engineering": 0.12,     # 12%
            "site_supervision": 0.08,       # 8%
            "documentation": 0.05,          # 5%
            "commissioning": 0.04,          # 4%
            "training": 0.02,               # 2%
            "contingency": 0.10             # 10%
        }
    }

    rates = overhead_structure[project_complexity]

    costs = {
        item: equipment_subtotal * rate
        for item, rate in rates.items()
    }

    total_overhead = sum(costs.values())

    return {
        "breakdown": costs,
        "total_overhead": total_overhead,
        "overhead_percentage": (total_overhead / equipment_subtotal) * 100
    }
```

-----

## 12\. Compliance & Accessibility Standards

### ADA (Americans with Disabilities Act) Requirements

  * **For US Installations - Critical Compliance Points:**

<!-- end list -->

```python
def check_ada_compliance(room_specs):
    """
    Verify ADA compliance requirements for AV installations
    """

    compliance_checklist = {
        "hearing_accessibility": {
            "required": room_specs["capacity"] >= 50,
            "solutions": [
                {
                    "type": "Hearing Loop System",
                    "coverage": "All seating areas",
                    "standard": "IEC 60118-4",
                    "note": "Preferred solution for ADA compliance"
                },
                {
                    "type": "FM/IR Assistive Listening System",
                    "receivers_required": max(2, math.ceil(room_specs["capacity"] * 0.04)),
                    "note": "Minimum 4% of seating capacity, minimum 2 units"
                }
            ]
        },
        "visual_accessibility": {
            "caption_display": {
                "required": True,
                "method": "Real-time captioning display on screen",
                "alternative": "Individual caption monitors"
            },
            "visual_alarms": {
                "required": True,
                "type": "Strobe lights for emergency notifications",
                "placement": "Visible from all areas"
            }
        },
        "physical_accessibility": {
            "control_height": {
                "touch_panels": "15-48 inches from floor (preferred 36-42 inches)",
                "operable_with": "Closed fist (no fine motor skills required)",
                "reach_depth": "Maximum 10 inches from edge"
            },
            "wheelchair_positions": {
                "required_count": math.ceil(room_specs["capacity"] * 0.01),
                "distribution": "Dispersed throughout seating area",
                "companion_seating": "Adjacent seating for companion"
            }
        },
        "signage": {
            "tactile_room_signs": {
                "required": True,
                "height": "48-60 inches to centerline",
                "braille": "Grade 2 Braille required"
            }
        }
    }

    return compliance_checklist
```

### Safety & Building Code Compliance

```python
def generate_safety_compliance_requirements(project_specs):
    """
    Generate safety and building code compliance checklist
    """

    requirements = {
        "electrical_safety": {
            "nec_compliance": {
                "standard": "NFPA 70 (National Electrical Code)",
                "requirements": [
                    "Dedicated circuits for AV equipment",
                    "GFCI protection where required",
                    "Proper equipment grounding",
                    "Arc-fault circuit interrupters (AFCI) in applicable locations",
                    "Isolated technical ground if specified"
                ]
            },
            "voltage_drop": {
                "maximum": "3% for branch circuits",
                "calculation_required": True
            }
        },
        "fire_safety": {
            "cable_ratings": {
                "plenum_spaces": "CMP (Plenum-rated) cables required",
                "riser": "CMR (Riser-rated) minimum",
                "general": "CM (Communications) rated minimum"
            },
            "penetrations": {
                "requirement": "Fire-stop all cable penetrations through fire-rated walls",
                "material": "UL-listed fire-stop material",
                "inspection": "Required by AHJ"
            },
            "egress": {
                "restriction": "Equipment shall not block exit paths",
                "signage": "Exit signs must remain visible",
                "doors": "Maintain required door swing clearances"
            }
        },
        "structural_requirements": {
            "display_mounting": {
                "load_calculation": "5x safety factor minimum",
                "structural_attachment": "Attachment to structural members, not drywall",
                "engineer_stamp": "Required for mounts >100 lbs in many jurisdictions"
            },
            "ceiling_loading": {
                "projector_mounts": "Verify ceiling load capacity",
                "speaker_mounts": "Attachment to structure above ceiling",
                "grid_support": "Additional bracing required for ceiling grid mounts"
            },
            "seismic_requirements": {
                "zone_dependent": True,
                "bracing": "Seismic bracing required in zones 3-4",
                "flexible_connections": "Flexible connections for equipment that may shift"
            }
        },
        "environmental": {
            "hvac_coordination": {
                "heat_load": "Provide heat load calculations to MEP engineer",
                "clearances": "Maintain equipment ventilation clearances",
                "duct_routing": "Coordinate ductwork to avoid equipment conflicts"
            },
            "acoustical_treatment": {
                "fire_rating": "Acoustic panels must meet flame spread requirements",
                "class_a": "Class A fire rating (flame spread <25) preferred"
            }
        },
        "inspection_requirements": {
            "rough_in": "Inspection of cable pathways before drywall",
            "electrical": "Electrical rough-in and final inspections",
            "final": "Final AV system inspection and commissioning",
            "documentation": "As-built drawings required for permit close-out"
        }
    }

    return requirements
```

-----

## 13\. Product Selection Logic & AI Justification Framework

### Product Selection Decision Tree

```python
class IntelligentProductSelector:
    """
    Advanced product selection with multi-stage filtering and AI justification
    """

    def select_product_with_justification(self, requirement, room_context, avixa_calcs):
        """
        Main product selection method with integrated AI justification
        """

        # Stage 1: Category filtering
        candidates = self.filter_by_category(requirement.category, requirement.sub_category)

        # Stage 2: Service contract filtering (CRITICAL)
        candidates = self.remove_service_contracts(candidates)

        # Stage 3: Specification matching
        candidates = self.apply_specification_filters(candidates, requirement)

        # Stage 4: Keyword filtering
        candidates = self.apply_keyword_filters(candidates, requirement)

        # Stage 5: Video bar integration check
        if self.is_video_bar_integration(candidates, room_context):
            candidates = self.remove_redundant_audio_components(candidates)

        # Stage 6: Brand ecosystem matching
        candidates = self.apply_brand_preferences(candidates, room_context)

        # Stage 7: Price range validation
        candidates = self.validate_price_ranges(candidates, requirement)

        # Stage 8: Display size validation (for multi-display warnings)
        if requirement.category == "Displays":
            self.check_unusual_display_config(candidates, room_context)

        # Stage 9: Final scoring and selection
        scored_candidates = self.score_products(candidates, requirement, room_context)

        if not scored_candidates:
            return None

        # Select top product
        best_product = scored_candidates[0]

        # Stage 10: Generate AI justification
        justification = self.generate_ai_justification(
            best_product,
            requirement,
            room_context,
            avixa_calcs
        )

        return {
            "product": best_product,
            "technical_justification": justification["technical"],
            "top_3_reasons": justification["top_3_client_reasons"],
            "confidence_score": justification["confidence"]
        }

    def remove_service_contracts(self, products):
        """
        CRITICAL: Filter out warranty, support contracts, and service items
        """
        service_keywords = [
            'warranty', 'extended warranty', 'support', 'maintenance',
            'service contract', 'care pack', 'protection plan',
            'assurance', 'year warranty', 'yr warranty', 'support plan'
        ]

        filtered = []
        for product in products:
            description_lower = product['description'].lower()
            name_lower = product['name'].lower()

            is_service = any(keyword in description_lower or keyword in name_lower
                             for keyword in service_keywords)

            # Additional check: unreasonably low price for category
            if product['category'] in ['Displays', 'Video Conferencing']:
                if product['price_usd'] < 50:  # Likely a service item
                    is_service = True

            if not is_service:
                filtered.append(product)

        return filtered

    def is_video_bar_integration(self, candidates, room_context):
        """
        Detect if room uses all-in-one video bar (integrated audio)
        """
        for product in candidates:
            if 'video bar' in product['name'].lower():
                if any(keyword in product['description'].lower()
                       for keyword in ['integrated audio', 'built-in speakers', 'integrated microphone']):
                    return True
        return False

    def remove_redundant_audio_components(self, candidates):
        """
        Remove standalone microphones/speakers if video bar provides audio
        """
        filtered = []
        for product in candidates:
            category = product['primary_category']
            if category not in ['Audio', 'Microphones', 'Speakers']:
                filtered.append(product)

        return filtered

    def validate_price_ranges(self, candidates, requirement):
        """
        Enforce minimum/maximum price thresholds by category
        """
        price_thresholds = {
            'Displays': {'min': 200, 'max': 30000},
            'Mounts': {'min': 50, 'max': 3000},
            'Video Conferencing': {'min': 300, 'max': 50000},
            'Audio': {'min': 100, 'max': 20000},
            'Cameras': {'min': 200, 'max': 15000}
        }

        thresholds = price_thresholds.get(requirement.category, {'min': 0, 'max': 1000000})

        # Override with requirement-specific thresholds if provided
        if requirement.min_price:
            thresholds['min'] = requirement.min_price
        if requirement.max_price:
            thresholds['max'] = requirement.max_price

        filtered = [
            p for p in candidates
            if thresholds['min'] <= p['price_usd'] <= thresholds['max']
        ]

        return filtered

    def check_unusual_display_config(self, candidates, room_context):
        """
        Warn about unusual display configurations (e.g., too many displays)
        """
        display_count = sum(1 for item in room_context['boq_items']
                            if 'Display' in item.get('category', ''))

        if display_count > 3:
            warning = f"⚠️ WARNING: {display_count} displays specified for room. Verify this is intentional."
            room_context['warnings'].append(warning)

        # Check for mismatched display sizes
        display_sizes = [item.get('size_inches', 0) for item in room_context['boq_items']
                         if 'Display' in item.get('category', '')]
        if display_sizes and max(display_sizes) - min(display_sizes) > 20:
            warning = f"⚠️ WARNING: Large variation in display sizes ({min(display_sizes)}-{max(display_sizes)} inches)"
            room_context['warnings'].append(warning)
```

### AI Justification Generation

```python
def generate_ai_product_justification(model, product_info, room_context, avixa_calcs):
    """
    Generate comprehensive AI-powered product justification
    Uses Google Gemini with structured JSON output
    """

    prompt = f"""
    You are an expert AV system designer. Provide a technical justification for selecting this product:

    PRODUCT INFORMATION:
    - Name: {product_info['name']}
    - Brand: {product_info['brand']}
    - Category: {product_info['category']} - {product_info['sub_category']}
    - Price: ${product_info['price_usd']:,.2f}
    - Specifications: {product_info.get('full_specifications', 'Standard specifications')}

    ROOM CONTEXT:
    - Room Type: {room_context['room_type']}
    - Room Area: {room_context['area_sqft']} sq ft
    - Capacity: {room_context['capacity']} people
    - Use Case: {room_context['primary_use']}

    AVIXA CALCULATIONS:
    - Recommended Display Size: {avixa_calcs.get('display_size_inches', 'N/A')} inches
    - Audio Coverage: {avixa_calcs.get('speaker_count', 'N/A')} speakers required
    - Viewing Distance: {avixa_calcs.get('max_viewing_distance_ft', 'N/A')} ft

    Generate a JSON response with:
    1. "technical_justification": Detailed technical explanation (100-150 words) for internal documentation
    2. "top_3_reasons": Array of exactly 3 client-facing reasons (10-15 words each) focusing on benefits
    3. "confidence_score": Your confidence in this selection (0.0 to 1.0)

    Focus on:
    - AVIXA standards compliance
    - Room-specific suitability
    - Performance specifications
    - Value proposition
    - Future-proofing

    Return ONLY valid JSON, no other text.
    """

    try:
        response = model.generate_content(prompt)
        justification_data = json.loads(response.text)

        # Validate structure
        required_keys = ['technical_justification', 'top_3_reasons', 'confidence_score']
        if not all(key in justification_data for key in required_keys):
            raise ValueError("Missing required keys in AI response")

        if len(justification_data['top_3_reasons']) != 3:
            raise ValueError("Expected exactly 3 client-facing reasons")

        return justification_data

    except Exception as e:
        # Fallback justification if AI fails
        return {
            "technical_justification": f"Selected {product_info['name']} based on category match, "
                                       f"specification alignment with room requirements, and competitive pricing. "
                                       f"Product meets AVIXA standards for {room_context['room_type']} applications.",
            "top_3_reasons": [
                f"Optimal specifications for {room_context['area_sqft']} sq ft space",
                f"Professional-grade {product_info['category']} with commercial warranty",
                "Competitive pricing with proven reliability"
            ],
            "confidence_score": 0.7
        }
```

-----

## 14\. Excel Export Specifications

### Professional BOQ Excel Format

```python
class ExcelBOQGenerator:
    """
    Generate professional, client-ready Excel proposals
    """

    def __init__(self):
        self.company_colors = {
            'primary': '002250',      # Dark Blue
            'accent': 'F07D00',       # Orange
            'text': 'F4F2F1',         # Grey
            'background': 'FFFFFF'
        }

    def create_proposal_workbook(self, project_data, rooms_data):
        """
        Create multi-sheet Excel workbook with complete proposal
        """

        wb = Workbook()

        # Sheet 1: Version Control & Metadata
        self.create_version_control_sheet(wb, project_data)

        # Sheet 2: Scope of Work
        self.create_scope_sheet(wb, project_data)

        # Sheet 3: Proposal Summary (Multi-Room Rollup)
        self.create_summary_sheet(wb, rooms_data)

        # Sheet 4: Terms & Conditions
        self.create_terms_sheet(wb)

        # Sheets 5+: Individual Room BOQs
        for room in rooms_data:
            self.create_room_boq_sheet(wb, room)

        return wb

    def create_room_boq_sheet(self, wb, room_data):
        """
        Create detailed BOQ sheet for a single room
        """

        ws = wb.create_sheet(title=f"BOQ - {room_data['name']}")

        # Header Section with Company Branding
        self.add_proposal_header(ws, room_data)

        # Room Information Section
        row = 6
        ws.merge_cells(f'A{row}:Q{row}')
        ws[f'A{row}'] = f"Room: {room_data['name']} | Type: {room_data['type']} | Area: {room_data['area_sqft']} sq ft"
        ws[f'A{row}'].font = Font(size=12, bold=True, color=self.company_colors['primary'])

        # Column Headers
        row = 8
        headers = [
            ("A", "S.No", 6),
            ("B", "Category", 20),
            ("C", "Product Name", 35),
            ("D", "Brand", 15),
            ("E", "Model Number", 20),
            ("F", "Product Image", 15),
            ("G", "Specifications", 30),
            ("H", "Quantity", 10),
            ("I", "Unit", 8),
            ("J", "Unit Price", 12),
            ("K", "Total Price", 12),
            ("L", "Warranty", 12),
            ("M", "Lead Time", 10),
            ("N", "GST %", 8),
            ("O", "GST Amount", 12),
            ("P", "Total with GST", 15),
            ("Q", "Top 3 Reasons", 40)
        ]

        for col, header, width in headers:
            ws.column_dimensions[col].width = width
            cell = ws[f'{col}{row}']
            cell.value = header
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color=self.company_colors['primary'],
                                    end_color=self.company_colors['primary'],
                                    fill_type='solid')
            cell.alignment = Alignment(horizontal='center', vertical='center')
            cell.border = Border(bottom=Side(style='thick'))

        # BOQ Items
        row = 9
        serial_no = 1

        for item in room_data['boq_items']:
            # ... [Code for populating each cell] ...
            row += 1
            serial_no += 1

        # Financial Summary Section
        self.add_financial_summary(ws, row, room_data)

        return ws

    def add_financial_summary(self, ws, start_row, room_data):
        """
        Add financial summary with installation, services, and GST
        """
        # ... [Code for calculating and formatting financial summary] ...
        pass
```

-----

## 15\. Integration with BOQ Generator Application

### Main BOQ Generation Pipeline

```python
def generate_comprehensive_boq(model, product_df, guidelines, project_params):
    """
    Main BOQ generation pipeline integrating all AVIXA standards

    8-Stage Process:
    1. NLP Requirements Parsing
    2. AVIXA Calculations
    3. Equipment Requirements Determination
    4. Component Blueprint Building
    5. Intelligent Product Selection with AI Justifications
    6. Compatibility & Redundancy Checking
    7. Validation & Quality Scoring
    8. Final Assembly & Export Preparation
    """

    # Stage 1: Parse natural language requirements
    parsed_requirements = parse_client_requirements(
        project_params['features_text'],
        project_params['technical_requirements']
    )

    # Stage 2: AVIXA Calculations
    avixa_calcs = calculate_avixa_recommendations(
        room_length=project_params['room_length'],
        room_width=project_params['room_width'],
        ceiling_height=project_params['ceiling_height'],
        room_type=project_params['room_type']
    )

    # Stage 3: Determine equipment requirements
    equipment_reqs = determine_equipment_requirements(
        room_type=project_params['room_type'],
        room_area=avixa_calcs['room_area_sqft'],
        capacity=project_params['capacity'],
        budget_tier=project_params['budget_tier'],
        client_preferences=parsed_requirements
    )

    # Stage 4: Build component blueprint
    component_blueprint = build_component_requirements(
        equipment_reqs,
        avixa_calcs,
        parsed_requirements
    )

    # Stage 5: Intelligent product selection with AI justification
    boq_items = []
    for requirement in component_blueprint:
        selected_product = intelligent_product_selector.select_product_with_justification(
            requirement=requirement,
            room_context=project_params,
            avixa_calcs=avixa_calcs
        )
        if selected_product:
            boq_items.append(selected_product)

    # Stage 6: Compatibility checking
    validated_boq = check_system_compatibility(boq_items, project_params)

    # Stage 7: Quality scoring
    quality_report = score_boq_quality(validated_boq, avixa_calcs, equipment_reqs)

    # Stage 8: Generate verification checklist and assemble
    verification_plan = generate_verification_checklist(
        project_params['room_type'],
        validated_boq
    )
    final_boq = {
        "project_metadata": project_params,
        "avixa_calculations": avixa_calcs,
        "boq_items": validated_boq,
        "quality_score": quality_report,
        "verification_plan": verification_plan,
        # ... other final assembly items
    }

    return final_boq
```

### Equipment Requirements Determination Logic

```python
def determine_equipment_requirements(room_type, room_area, capacity, budget_tier, client_preferences):
    """
    Determine comprehensive equipment requirements based on AVIXA standards and room specifications
    """
    requirements = []

    # === DISPLAY REQUIREMENTS ===
    display_req = determine_display_requirements(room_type, room_area, capacity, budget_tier)
    requirements.extend(display_req)

    # === AUDIO REQUIREMENTS ===
    audio_req = determine_audio_requirements(room_type, room_area, capacity, client_preferences)
    requirements.extend(audio_req)

    # === VIDEO CONFERENCING REQUIREMENTS ===
    if client_preferences.get('video_conferencing', True):
        vc_req = determine_video_conferencing_requirements(room_area, capacity, budget_tier)
        requirements.extend(vc_req)

    # === CONTROL SYSTEM REQUIREMENTS ===
    control_req = determine_control_requirements(room_area, complexity_score(requirements))
    requirements.extend(control_req)
    
    # ... and so on for Connectivity, Infrastructure, Mounting ...

    return requirements

# ... [Detailed functions like determine_display_requirements, determine_audio_requirements, etc.]
```

-----

## 16\. Validation & Quality Scoring

### BOQ Quality Assessment

```python
def score_boq_quality(boq_items, avixa_calcs, equipment_reqs):
    """
    Comprehensive quality scoring system for generated BOQ
    100-point scale across multiple criteria
    """
    scores = {
        "avixa_compliance": 0,      # 30 points
        "completeness": 0,          # 25 points
        "price_reasonableness": 0,  # 15 points
        "brand_consistency": 0,     # 10 points
        "specification_match": 0,   # 10 points
        "integration_quality": 0    # 10 points
    }
    warnings = []
    recommendations = []

    # 1. AVIXA Compliance (30 points)
    # ... [Logic to check display size, speaker count, etc., against avixa_calcs]

    # 2. Completeness (25 points)
    # ... [Logic to check for missing critical components like mounts, displays, etc.]

    # 3. Price Reasonableness (15 points)
    # ... [Logic to flag zero-price items or unusually high-priced items]

    # 4. Brand Consistency (10 points)
    # ... [Logic to count unique brands and score based on consolidation]

    # 5. Specification Match (10 points)
    # ... [Logic to check AI confidence scores for each product selection]

    # 6. Integration Quality (10 points)
    # ... [Logic to check for brand ecosystem compatibility, e.g., control and VC]

    total_score = sum(scores.values())
    
    # ... [Logic to assign a final grade (A, B, C...)]

    return {
        "total_score": total_score,
        "grade": "...",
        "category_scores": scores,
        "warnings": warnings,
        "recommendations": recommendations
    }
```

-----

## 17\. Documentation Standards (AVIXA D401.01:2023)

### As-Built Documentation Requirements

```python
def generate_asbuilt_documentation(project_data, boq_items, installation_notes):
    """
    Generate comprehensive as-built documentation per AVIXA D401.01:2023
    """

    documentation = {
        "project_identification": {
            # ... project details
        },
        "document_sections": {
            "architectural_drawings": {
                "floor_plans": "As-built floor plans showing final equipment locations",
                "reflected_ceiling_plans": "RCP showing ceiling-mounted equipment",
                "elevation_drawings": "Elevations showing display heights and rack configurations"
            },
            "equipment_documentation": {
                "bill_of_materials": "...",
                "equipment_rack_elevations": "...",
                "cutsheets": "Manufacturer cut sheets for all installed equipment"
            },
            "system_diagrams": {
                "block_diagrams": "System block diagrams showing signal flow",
                "wiring_diagrams": "Detailed wiring schematics for all connections",
                "network_diagrams": "Network topology showing VLANs and IP addressing"
            },
            "cable_documentation": {
                "cable_schedule": "...",
                "cable_labels": "Cable labeling per AVIXA CLAS standard",
                "test_results": "Cable certification test results"
            },
            "configuration_documentation": {
                "device_settings": "Configuration settings for all programmable devices",
                "ip_addressing": "Complete IP address schedule with device names",
                "control_programming": "Control system program files and logic",
                "dsp_settings": "Audio DSP configuration files and presets"
            },
            "operational_documentation": {
                "user_guides": "End-user operation guides for each room mode",
                "quick_reference_cards": "Laminated quick-start guides"
            },
            "commissioning_records": {
                "verification_reports": "AVIXA 10:2013 verification test results",
                "sign_off_documents": "Client acceptance and sign-off forms"
            }
        }
    }

    return documentation
```

-----

## 18\. Training & End-User Documentation

### User Training Program Structure

```python
def generate_training_program(room_data, boq_items, user_roles):
    """
    Create comprehensive training program for different user roles
    """

    training_program = {
        "training_overview": {
            "total_duration": "4-8 hours (depending on system complexity)",
            "format": "Hands-on in-room training with documentation",
            "attendees": user_roles
        },
        "training_modules": {
            "basic_users": {
                "target_audience": "All room users",
                "duration": "1 hour",
                "topics": [
                    {"topic": "System Power-On/Off"},
                    {"topic": "Connecting Your Laptop"},
                    {"topic": "Starting a Video Conference"},
                    {"topic": "Audio Control"},
                    {"topic": "Getting Help"}
                ]
            },
            "advanced_users": {
                "target_audience": "Executive assistants, meeting coordinators",
                "duration": "2 hours",
                "topics": [
                    {"topic": "Advanced Source Management"},
                    {"topic": "Camera Control"},
                    {"topic": "Audio Presets & Scenes"},
                    {"topic": "Environmental Controls"}
                ]
            },
            "technical_staff": {
                "target_audience": "IT staff, AV technicians",
                "duration": "4-6 hours",
                "topics": [
                    {"topic": "System Architecture Overview"},
                    {"topic": "Equipment Rack Tour"},
                    {"topic": "Network Configuration"},
                    {"topic": "Audio/Video/Control System Configuration"},
                    {"topic": "Preventive Maintenance & Troubleshooting"}
                ]
            }
        },
        "deliverables": {
            "documentation": [
                "Complete system operation manual (PDF + printed)",
                "Quick-start guides (laminated, posted in room)"
            ]
        }
    }
    return training_program
```

-----

## 19\. Final BOQ Assembly & Export

### Complete BOQ Package Generation

```python
def assemble_final_boq_package(project_data, rooms_data, avixa_calcs, quality_scores):
    """
    Assemble complete BOQ package ready for client presentation
    """

    boq_package = {
        "executive_summary": {
            # ... project scope, total investment, timeline, key benefits
        },
        "room_summaries": [
            # ... list of summaries for each room
        ],
        "detailed_boq": rooms_data,
        "financial_summary": {
            # ... hardware, installation, tax, and grand totals
        },
        "implementation_plan": {
            # ... phased plan for design, installation, commissioning, training
        },
        "terms_conditions": {
            # ... payment terms, warranty, validity, exclusions, assumptions
        },
        "appendices": {
            "avixa_calculations": avixa_calcs,
            "verification_plan": "...",
            "cable_schedule": "...",
            "references": [
                "AVIXA DISCAS",
                "AVIXA A102.01:2017",
                "AVIXA 10:2013",
                "AVIXA D401.01:2023"
            ]
        }
    }
    # ... [Final financial calculations]
    return boq_package
```

-----

## 20\. Summary & Best Practices

### BOQ Generator Design Checklist

#### Pre-Generation Checklist

  - [ ] Room dimensions verified (length, width, ceiling height)
  - [ ] Room type and primary function identified
  - [ ] Occupancy/capacity determined
  - [ ] Budget tier established
  - [ ] Client preferences documented

#### AVIXA Standards Compliance Checklist

  - [ ] Display sizing calculated per DISCAS
  - [ ] Audio coverage verified per A102.01 (±3dB uniformity)
  - [ ] Network bandwidth requirements calculated
  - [ ] Power load calculated with 20% safety factor
  - [ ] Verification plan created per AVIXA 10:2013

### Common Pitfalls to Avoid

```python
COMMON_PITFALLS = {
    "Display Selection": [
        "❌ Selecting consumer TVs instead of commercial displays",
        "❌ Undersizing displays based on viewing distance",
        "❌ Missing mounts for displays"
    ],
    "Audio System": [
        "❌ Using TV speakers for conference room audio (inadequate)",
        "❌ Insufficient microphone coverage",
        "❌ No DSP for echo cancellation in medium/large rooms"
    ],
    "Infrastructure": [
        "❌ Inadequate power circuits",
        "❌ No UPS for critical equipment",
        "❌ Insufficient network switch ports"
    ],
    "Cost Estimation": [
        "❌ Forgetting installation labor",
        "❌ Not including programming time",
        "❌ Missing project management overhead"
    ]
}
```

```
```
