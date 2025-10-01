# Enhanced AV Design Guidelines for BOQ Generation
## Based on AVIXA Standards & Industry Best Practices (Machine-Readable v2.1)

This document provides a structured, machine-readable framework for the automated generation and validation of an audio-visual (AV) Bill of Quantities (BOQ). It is based on AVIXA standards including DISCAS, ISCR, and principles from the CTS 2 Student Guide, designed to be parsed by an application.

---
## Core Design Philosophy & Global Rules

The system operates on a room-first approach. The YAML blocks below define specifications, system requirements, and validation rules for different room types. The application should parse these rules to both generate the initial BOQ and validate the final output for standards compliance.

```yaml
# Global settings and rules applicable to all room types.
global_rules:
  power_capacity_margin: 0.80
  compliance_standards:
    - "ANSI/AVIXA A102.01:2017 (Audio Coverage Uniformity)"
    - "ANSI/AVIXA 2M-2010 (Audiovisual Systems Design and Coordination Processes)"
    - "ANSI/AVIXA 3M-2011 (Projected Image System Contrast Ratio - ISCR)"
    - "ANSI/AVIXA 4:2012 (Audiovisual Systems Energy Management)"
    - "J-STD-710 (Audio, Video and Control Architectural Drawing Symbols)"

# AVIXA ISCR (Image System Contrast Ratio) Viewing Categories
iscr_viewing_categories:
  passive_viewing:
    description: "For viewing non-critical content where the general intent can be understood."
    min_contrast_ratio: "7:1"
  basic_decision_making:
    description: "For comprehending content and making simple decisions (e.g., presentations, classrooms)."
    min_contrast_ratio: "15:1"
  analytical_decision_making:
    description: "For analyzing critical details (e.g., engineering drawings, forensic evidence)."
    min_contrast_ratio: "50:1"
  full_motion_video:
    description: "For discerning key elements in video content as intended by the creator."
    min_contrast_ratio: "80:1"

# Cost & Labor Estimation Framework
estimation_framework:
  cost_percentages:
    displays_cameras: [0.30, 0.40]
    audio_systems: [0.20, 0.30]
    control_connectivity: [0.15, 0.25]
    infrastructure: [0.05, 0.10]
  labor_estimates:
    small_huddle_room: 6
    medium_conference_room: 16
    large_boardroom: 40
    multipliers:
      complex_programming: 1.5
      building_system_integration: 2.0
      retrofit_renovation: 1.8
  service_contracts:
    standard_warranty_years: 3
    maintenance_annual_cost_percent: 0.15

---
## AVIXA DISCAS Video Sizing Principles

The DISCAS standard provides formulas to determine the appropriate image size based on viewing distance and task.

### Analytical Decision Making (ADM)
[cite_start]Used when viewers must analyze critical details at the pixel level[cite: 3451]. [cite_start]An acuity factor of **3438** is used[cite: 3533].

- [cite_start]**ADM Image Height Formula:** `IH = (IR * FV) / 3438` [cite: 3533]
- [cite_start]**ADM Farthest Viewer Formula:** `FV = (IH * 3438) / IR` [cite: 3534]

### Basic Decision Making (BDM)
[cite_start]The most common category, used for presentations and general meetings[cite: 3535]. [cite_start]An acuity factor of **200** is used (the "200 Rule") applied to the height of lowercase characters[cite: 3516, 3523].

- [cite_start]**BDM Image Height Formula:** `IH = (FV * %EH) / 200` [cite: 3546]
- [cite_start]**BDM Farthest Viewer Formula:** `FV = (IH * 200) / %EH` [cite: 3547]

---

# All room types are now in a single list called "room_archetypes"
room_archetypes:
  - name: "Small Huddle Room"
    specifications:
      area_sqft: [40, 120]
      capacity: [2, 4]
      ceiling_height_range_ft: [8, 10]
    system_requirements:
      display: { quantity: 1, recommended_sizing_rule: "DISCAS_BDM", type: "Commercial 4K Display", min_resolution: "4K" }
      audio: { system_type: "Integrated Video Bar", dsp_required: false }
      video: { system_type: "All-in-one Video Bar", camera_type: "ePTZ 4K" }
      control: { interface_type: "Native Room System Control (e.g., Teams/Zoom Panel)" }
      infrastructure: { rack_required: false, power_management_type: "Surge Protector" }
    validation_rules:
      - "CHECK: BOQ must contain one item from 'Video Conferencing' category with 'bar' in its name."
      - "CHECK: BOQ must contain one item from 'Displays' category between 42 and 60 inches."
      - "WARN: If 'ada_compliance' is True, display mounting height should be noted as 42-48 inches from floor to center."

  - name: "Medium Conference Room"
    specifications:
      area_sqft: [121, 300]
      capacity: [5, 12]
      ceiling_height_range_ft: [9, 12]
    system_requirements:
      display: { quantity: 1, recommended_sizing_rule: "DISCAS_BDM", type: "Commercial 4K Display" }
      audio: { system_type: "Modular DSP", dsp_required: true, microphone_type: "Tabletop or Ceiling Array", speaker_type: "Ceiling Speakers", speaker_count_formula: "max(4, floor(area_sqft / 150))" }
      video: { system_type: "Modular Codec + PTZ Camera", camera_type: "PTZ camera with auto-framing" }
      control: { interface_type: "10-inch Tabletop Touch Panel" }
      infrastructure: { rack_required: true, rack_type: "Wall-mounted or Furniture-integrated", power_management_type: "Rackmount PDU", dedicated_circuit_recommended: "20A" }
    validation_rules:
      - "RULE: BOQ must contain one item from 'Audio' category with 'DSP' or 'Processor' in its name."
      - "RULE: BOQ must contain one 'Audio' item with 'Amplifier' in its name."
      - "WARN: IF audio.microphone_type is 'Ceiling Array' AND (ceiling_height_range_ft[0] < 9 OR has_hard_surfaces == True), THEN FLAG 'Acoustic treatment recommended due to ceiling height and/or hard surfaces.'"
      - "CHECK: Total power draw of all equipment should be less than 1920 Watts (80% of a 20A/120V circuit)."
      - "CHECK: Loudness capability: System must be able to achieve 25 dB above measured ambient noise."

  - name: "Large Boardroom/Training Room"
    specifications:
      area_sqft: [301, 1000]
      capacity: [12, 50]
      ceiling_height_range_ft: [10, 16]
    system_requirements:
      display: { quantity: 2, recommended_sizing_rule: "DISCAS_ADM", type: "Large Format 4K Display (86\"+), Laser Projector, or LED Wall" }
      audio: { system_type: "Networked Audio (Dante/AVB)", dsp_required: true, microphone_type: "Ceiling-mounted steerable array (e.g., Shure MXA920)", speaker_type: "Zoned Ceiling Speakers", speaker_count_formula: "max(8, floor(area_sqft / 100))" }
      video: { system_type: "Multi-camera system with auto-switching", camera_type: "Speaker tracking PTZ" }
      control: { interface_type: "Advanced Programmable Control Processor with multiple touch panels" }
      infrastructure: { rack_required: true, rack_type: "Full-size floor-standing rack (24-42U)", power_management_type: "Monitored Rackmount PDU", dedicated_circuit_recommended: "Multiple 20A circuits" }
    validation_rules:
      - "REQUIREMENT: IF area_sqft > 500, BOQ MUST include components for a 'Voice Lift System'."
      - "REQUIREMENT: IF ada_compliance == True, BOQ MUST contain an item from 'Assistive Listening' category."
      - "CHECK: BOQ must contain a networked DSP (Dante/AVB capable)."
      - "CHECK: BOQ must contain at least two items from 'Video Conferencing' category with 'camera' in the name."
      - "CHECK: Total equipment heat load (BTU/hr) must be calculated and flagged for HVAC coordination. (1 Watt = 3.41 BTU/hr)"
      - "WARN: Audio system cost should be between 20-30% of total hardware cost. Flag if outside this range."

### Cost & Labor Estimation Framework
```yaml
estimation_framework:
  cost_percentages:
    displays_cameras: [0.30, 0.40]
    audio_systems: [0.20, 0.30]
    control_connectivity: [0.15, 0.25]
    infrastructure: [0.05, 0.10]
  labor_estimates:
    # Base hours per room type
    small_huddle_room: 6
    medium_conference_room: 16
    large_boardroom: 40
    # Multipliers for complexity
    multipliers:
      complex_programming: 1.5
      building_system_integration: 2.0 # (e.g., HVAC, lighting control)
      retrofit_renovation: 1.8 # Working around existing construction
  service_contracts:
    standard_warranty_years: 3
    maintenance_annual_cost_percent: 0.15 # 15% of equipment cost annually
```
