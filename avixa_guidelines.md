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
Viewing Angle Considerations
Horizontal Viewing Angles:

Optimal: Within 30° of display center

Acceptable: Up to 45° from center

Maximum: 60° (image distortion becomes significant)

Vertical Viewing Angles:

Display center should be at seated eye height (42-48" from floor)

Maximum upward angle: 30° from eye level

Maximum downward angle: 15° from eye level

BOQ Implementation:
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
2. AVIXA A102.01:2017 - Audio Coverage Uniformity
Audio Coverage Standards
Speech Intelligibility Requirements:

Target STI (Speech Transmission Index): ≥ 0.60 for general spaces

Target STI: ≥ 0.70 for critical communication (command centers, courtrooms)

Variation across listening area: ± 3 dB SPL (500Hz - 4kHz)

Speaker Coverage Calculations:
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
Microphone Coverage
Microphone Pickup Patterns:

Cardioid: 120° coverage, 8-10 ft pickup radius

Supercardioid: 115° coverage, 10-12 ft pickup radius

Omnidirectional: 360° coverage, 6-8 ft pickup radius (ceiling mics)

Microphone Spacing Calculations:
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
Microphone Coverage
Microphone Pickup Patterns:

Cardioid: 120° coverage, 8-10 ft pickup radius

Supercardioid: 115° coverage, 10-12 ft pickup radius

Omnidirectional: 360° coverage, 6-8 ft pickup radius (ceiling mics)

Microphone Spacing Calculations:
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
Sound Pressure Level (SPL) Requirements
Target SPL Levels:

Background Music: 65-70 dB SPL

Speech Reinforcement: 70-75 dB SPL

Presentation Audio: 75-80 dB SPL

Large Event Spaces: 85-95 dB SPL

SPL Calculation:
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
3. Room Acoustics & Enviro
nmental Considerations
Reverberation Time (RT60)
Target RT60 by Room Type:

Conference Rooms: 0.4 - 0.6 seconds

Training Rooms: 0.5 - 0.7 seconds

Auditoriums: 0.8 - 1.2 seconds

Lecture Halls: 0.6 - 0.9 seconds

Multipurpose Spaces: 0.6 - 0.8 seconds

Acoustic Treatment Recommendations:

        

    return max(2, mics_needed)  # Minimum 2 for redundancy
