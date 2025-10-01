# Enhanced AV Design Guidelines for BOQ Generation
## Based on AVIXA Standards & Industry Best Practices (Machine-Readable v2.0)

This document provides a structured, machine-readable framework for the automated generation and validation of an audio-visual (AV) Bill of Quantities (BOQ). It is based on AVIXA standards including DISCAS, ISCR, and principles from the CTS 2 Student Guide, designed to be parsed by an application.

---
## Core Design Philosophy & Global Rules

The system operates on a room-first approach. The YAML blocks below define specifications, system requirements, and validation rules for different room types. The application should parse these rules to both generate the initial BOQ and validate the final output for standards compliance.

```yaml
# Global settings and rules applicable to all room types.
# This section can be parsed by the application to enforce universal standards.
global_rules:
  [cite_start]power_capacity_margin: 0.80  # Best practice is to only plan for 80% of a circuit's total power[cite: 2983].
  compliance_standards:
    - [cite_start]"ANSI/AVIXA A102.01:2017 (Audio Coverage Uniformity)" [cite: 2781]
    - [cite_start]"ANSI/AVIXA 2M-2010 (Audiovisual Systems Design and Coordination Processes)" [cite: 2781]
    - [cite_start]"ANSI/AVIXA 3M-2011 (Projected Image System Contrast Ratio - ISCR)" [cite: 2781]
    - [cite_start]"ANSI/AVIXA 4:2012 (Audiovisual Systems Energy Management)" [cite: 2781]
    - [cite_start]"J-STD-710 (Audio, Video and Control Architectural Drawing Symbols)" [cite: 2781]

# AVIXA ISCR (Image System Contrast Ratio) Viewing Categories
# Defines minimum contrast ratios for different viewing tasks.
iscr_viewing_categories:
  passive_viewing:
    [cite_start]description: "For viewing non-critical content where the general intent can be understood." [cite: 3445]
    min_contrast_ratio: 7:1
  basic_decision_making:
    [cite_start]description: "For comprehending content and making simple decisions (e.g., presentations, classrooms)." [cite: 3447, 3448]
    min_contrast_ratio: 15:1
  analytical_decision_making:
    [cite_start]description: "For analyzing critical details (e.g., engineering drawings, forensic evidence)." [cite: 3451]
    min_contrast_ratio: 50:1
  full_motion_video:
    [cite_start]description: "For discerning key elements in video content as intended by the creator." [cite: 3452]
    min_contrast_ratio: 80:1
```

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

## Room Archetypes & Rule Sets (YAML Format)

### Small Huddle Room

```yaml
room_archetype:
  name: "Small Huddle Room"
  specifications:
    area_sqft: [40, 120]
    capacity: [2, 4]
    ceiling_height_range_ft: [8, 10]
  system_requirements:
    display:
      quantity: 1
      recommended_sizing_rule: "DISCAS_BDM"
      type: "Commercial 4K Display"
      min_resolution: "4K"
    audio:
      [cite_start]system_type: "Integrated Video Bar" # Audio is handled by the video bar [cite: 2686]
      dsp_required: false
    video:
      system_type: "All-in-one Video Bar"
      camera_type: "ePTZ 4K"
    control:
      interface_type: "Native Room System Control (e.g., Teams/Zoom Panel)"
    infrastructure:
      rack_required: false
      power_management_type: "Surge Protector"
  validation_rules:
    - CHECK: "BOQ must contain one item from 'Video Conferencing' category with 'bar' in its name."
    - CHECK: "BOQ must contain one item from 'Displays' category between 42 and 60 inches."
    - WARN: "If 'ada_compliance' is True, display mounting height should be noted as 42-48 inches from floor to center."
```

### Medium Conference Room

```yaml
room_archetype:
  name: "Medium Conference Room"
  specifications:
    area_sqft: [121, 300]
    capacity: [5, 12]
    ceiling_height_range_ft: [9, 12]
  system_requirements:
    display:
      quantity: 1 # Default, can be overridden to 2 for dual-display needs
      recommended_sizing_rule: "DISCAS_BDM"
      type: "Commercial 4K Display"
    audio:
      system_type: "Modular DSP"
      dsp_required: true
      microphone_type: "Tabletop or Ceiling Array"
      [cite_start]speaker_type: "Ceiling Speakers" [cite: 3090]
      speaker_count_formula: "max(4, floor(area_sqft / 150))"
    video:
      system_type: "Modular Codec + PTZ Camera"
      camera_type: "PTZ camera with auto-framing"
    control:
      interface_type: "10-inch Tabletop Touch Panel"
    infrastructure:
      rack_required: true
      rack_type: "Wall-mounted or Furniture-integrated"
      power_management_type: "Rackmount PDU"
      [cite_start]dedicated_circuit_recommended: "20A" [cite: 2754]
  validation_rules:
    - RULE: "BOQ must contain one item from 'Audio' category with 'DSP' or 'Processor' in its name."
    - RULE: "BOQ must contain one 'Audio' item with 'Amplifier' in its name."
    - RULE: "IF audio.microphone_type is 'Ceiling Array' AND (ceiling_height_range_ft[0] < 9 OR has_hard_surfaces == True), THEN FLAG 'Acoustic treatment recommended due to ceiling height and/or hard surfaces.'"
    - [cite_start]CHECK: "Total power draw of all equipment should be less than 1920 Watts (80% of a 20A/120V circuit)." [cite: 2983]
    - [cite_start]CHECK: "Loudness capability: System must be able to achieve 25 dB above measured ambient noise." [cite: 3123]
```

### Large Boardroom / Training Room

```yaml
room_archetype:
  name: "Large Boardroom/Training Room"
  specifications:
    area_sqft: [301, 1000]
    capacity: [12, 50]
    ceiling_height_range_ft: [10, 16]
  system_requirements:
    display:
      quantity: 2 # Default for boardrooms
      recommended_sizing_rule: "DISCAS_ADM" # Higher detail requirement
      type: "Large Format 4K Display (86\"+), Laser Projector, or LED Wall"
    audio:
      system_type: "Networked Audio (Dante/AVB)"
      dsp_required: true
      microphone_type: "Ceiling-mounted steerable array (e.g., Shure MXA920)"
      speaker_type: "Zoned Ceiling Speakers"
      speaker_count_formula: "max(8, floor(area_sqft / 100))"
    video:
      system_type: "Multi-camera system with auto-switching"
      camera_type: "Speaker tracking PTZ"
    control:
      interface_type: "Advanced Programmable Control Processor with multiple touch panels"
    infrastructure:
      rack_required: true
      rack_type: "Full-size floor-standing rack (24-42U)"
      power_management_type: "Monitored Rackmount PDU"
      [cite_start]dedicated_circuit_recommended: "Multiple 20A circuits" [cite: 2754]
  validation_rules:
    - REQUIREMENT: "IF area_sqft > 500, BOQ MUST include components for a 'Voice Lift System'."
    - [cite_start]REQUIREMENT: "IF ada_compliance == True, BOQ MUST contain an item from 'Assistive Listening' category." [cite: 2781]
    - CHECK: "BOQ must contain a networked DSP (Dante/AVB capable)."
    - CHECK: "BOQ must contain at least two items from 'Video Conferencing' category with 'camera' in the name."
    - [cite_start]CHECK: "Total equipment heat load (BTU/hr) must be calculated and flagged for HVAC coordination. (1 Watt = 3.41 BTU/hr)" [cite: 4218, 4219]
    - WARN: "Audio system cost should be between 20-30% of total hardware cost. Flag if outside this range."
```

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
