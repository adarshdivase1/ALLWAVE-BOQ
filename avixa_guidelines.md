# Enhanced AV Design Guidelines for BOQ Generation
*Based on AVIXA Standards & Industry Best Practices*

This document provides a comprehensive framework for audio-visual systems design. All calculations and recommendations are based on AVIXA DISCAS, AVIXA 10:2013, AVIXA 2M-2010, AVIXA D401.01:2023, InfoComm AV Best Practices, and real-world implementation experience.

## Core Design Philosophy
The design process operates on a room-first approach: analyze the space dimensions, occupancy, and function to determine the appropriate technology tier. Each tier has specific equipment requirements, installation complexity, and cost structures.

## AVIXA Standards Integration
This framework incorporates multiple AVIXA standards:
* **AVIXA DISCAS** (Display Image Size for 2D Content in Audiovisual Systems) - Display sizing calculations
* **AVIXA 10:2013** - Audiovisual Systems Performance Verification
* **AVIXA 2M-2010** - Standard Guide for Audiovisual Systems Design and Coordination Processes
* **AVIXA D401.01:2023** - Audiovisual Project Documentation Standard
* **AVIXA F502.01:2018** - Rack Building for Audiovisual Systems
* **AVIXA A102.01:2017** - Audio Coverage Uniformity in Enclosed Listener Areas

---

## 1. AVIXA DISCAS - Display Sizing

### Display Image Size Considerations

* **For Analytical Decision Making (ADM) - Critical Detail Viewing:**
    * Used for: Engineering drawings, forensic evidence, detailed image inspection.
    * Formula: $ \text{Image Height} = (\text{Farthest Viewer Distance} \div 3438) \times \text{Vertical Resolution} $
    * Example: 12ft viewing distance, 1080p display = 3.75" minimum image height.

* **For Basic Decision Making (BDM) - Standard Presentations:**
    * Element Height is typically 3-5% of screen height for readable text.
    * Formula: $ \text{Image Height} = (\text{Farthest Viewer Distance} \div 200) \div \text{Element Height \%} $
    * Example: 20ft viewing distance, 4% element height = 100" diagonal display recommended.

* **For Passive Viewing - General Content:**
    * Used for: Digital signage, lobby displays, non-critical viewing.
    * Formula: $ \text{Image Height} = \text{Viewing Distance} \div 8 $
    * Example: 16ft viewing distance = 24" minimum screen height.

### Viewing Angle Considerations

* **Horizontal Viewing Angles:**
    * **Optimal:** Within 30° of display center.
    * **Acceptable:** Up to 45° from center.
    * **Maximum:** 60° (image distortion becomes significant).

* **Vertical Viewing Angles:**
    * Display center should be at seated eye height (42-48" from floor).
    * **Maximum upward angle:** 30° from eye level.
    * **Maximum downward angle:** 15° from eye level.

---

## 2. AVIXA A102.01:2017 - Audio Coverage Uniformity

### Audio Coverage Standards

* **Speech Intelligibility Requirements:**
    * **Target STI (Speech Transmission Index):** ≥ 0.60 for general spaces.
    * **Target STI:** ≥ 0.70 for critical communication (command centers, courtrooms).
    * **Variation across listening area:** ± 3 dB SPL (500Hz - 4kHz).

* **Speaker Coverage Guidelines:**
    * For ceilings up to 9 ft: ~150 sq ft per speaker.
    * For ceilings 9-12 ft: ~200 sq ft per speaker.
    * For ceilings >12 ft: ~250 sq ft per speaker.
    * **Note:** Reduce coverage area by 10-20% for rooms requiring higher speech clarity (e.g., conference rooms, training rooms). A minimum of 2 speakers is recommended.

### Microphone Coverage

* **Microphone Pickup Patterns:**
    * **Cardioid:** 120° coverage, 8-10 ft pickup radius.
    * **Supercardioid:** 115° coverage, 10-12 ft pickup radius.
    * **Omnidirectional:** 360° coverage, 6-8 ft pickup radius (ceiling mics).

* **Microphone Spacing:**
    * **Conference Table:** Gooseneck or array mics should be spaced approximately 6 feet apart.
    * **Open Floor Plan:** Ceiling array mics can cover approximately 150 sq ft per unit.
    * A minimum of 2 microphones is recommended for redundancy.

### Sound Pressure Level (SPL) Requirements

* **Target SPL Levels:**
    * **Background Music:** 65-70 dB SPL
    * **Speech Reinforcement:** 70-75 dB SPL
    * **Presentation Audio:** 75-80 dB SPL
    * **Large Event Spaces:** 85-95 dB SPL

---

## 3. Room Acoustics & Environmental Considerations

### Reverberation Time (RT60)

* **Target RT60 by Room Type:**
    * **Conference Rooms:** 0.4 - 0.6 seconds
    * **Training Rooms:** 0.5 - 0.7 seconds
    * **Auditoriums:** 0.8 - 1.2 seconds
    * **Lecture Halls:** 0.6 - 0.9 seconds
    * **Multipurpose Spaces:** 0.6 - 0.8 seconds

### Ambient Noise Requirements

* **Maximum Background Noise Levels (NC/RC Ratings):**
    * **Executive Conference Rooms:** NC 25
    * **Standard Conference Rooms:** NC 30
    * **Training Rooms:** NC 35
    * **Multipurpose Spaces:** NC 35-40
    * **Large Auditoriums:** NC 30

* **HVAC Coordination Requirements:**
    * Ductwork must not run directly above presentation or primary listening areas.
    * VAV boxes should be located away from microphone positions.
    * Specify sound attenuators for supply/return ducts in critical spaces.
    * Target air velocity in diffusers: < 500 FPM (feet per minute).

---

## 4. Video System Design Standards

### Camera Coverage & Positioning

* **Small Rooms (≤ 4 people):** A single fixed, wide-angle camera (120° FOV) mounted above or below the display is sufficient.
* **Medium Rooms (≤ 12 people):** A single PTZ (Pan-Tilt-Zoom) camera with AI auto-framing and speaker tracking provides the best experience. Mount on the ceiling or above the display.
* **Large Rooms (> 12 people):** A multi-camera system is recommended, typically including a primary PTZ camera for active speakers and a secondary wide-angle camera for a room overview.

### Lighting Requirements for Video

* **Illuminance Levels:**
    * **Video Conferencing (HD):** 300-500 lux vertical illuminance on faces.
    * **Video Conferencing (4K):** 400-600 lux vertical illuminance.
    * **Broadcast/Recording:** 500-800 lux.
* **Color Temperature:** 3200K - 5600K (must be consistent across all light sources).
* **Color Rendering Index (CRI):** ≥ 80 (≥ 90 recommended for broadcast quality).

---

## 5. Network Infrastructure Requirements

### Network Bandwidth Calculations

* **Video Conferencing Bandwidth:**
    * **720p HD Video:** 1.5 - 2.5 Mbps per stream.
    * **1080p Full HD:** 2.5 - 4 Mbps per stream.
    * **4K Video:** 15 - 25 Mbps per stream.
* **AV over IP Bandwidth:**
    * **1080p60 (JPEG2000):** 1 Gbps.
    * **4K60 (H.264):** 25 - 50 Mbps.
    * **4K60 (Uncompressed):** 12 - 18 Gbps.

### QoS (Quality of Service) Configuration

* **DSCP Marking Standards:**
    * **Video:** DSCP 34 (AF41) - Assured Forwarding.
    * **Audio:** DSCP 46 (EF) - Expedited Forwarding.
    * **Control:** DSCP 26 (AF31).
    * **Signaling:** DSCP 24 (CS3).

* **VLAN Recommendations:**
    * **AV Production VLAN:** For cameras, displays, and AV over IP traffic. High priority.
    * **Video Conferencing VLAN:** For codecs and video bars. Critical priority.
    * **Control Systems VLAN:** For touch panels and processors. Medium priority.
    * **Management VLAN:** For device management and updates. Low priority.

---

## 6. Power & Electrical Requirements

### Power Consumption (Typical Estimates)

* **55-65" Display:** 150-250W
* **75-85" Display:** 300-450W
* **98" Display:** 500-700W
* **Video Codec:** 50-100W
* **PTZ Camera (PoE):** 20-30W
* **Amplifier (100W/channel):** 200-300W
* **DSP Processor:** 30-50W
* **24-port PoE Switch:** 200-400W

### UPS (Uninterruptible Power Supply) Sizing

* **Runtime Requirements by Room Type:**
    * **Small Huddle:** 10-15 minutes (for graceful shutdown).
    * **Medium Conference:** 15-30 minutes.
    * **Large Boardroom:** 30-60 minutes.
    * **Mission Critical:** 60+ minutes with generator backup.

---

## 7. Cabling & Infrastructure Standards

### Cable Categories & Applications

* **Copper Cabling:**
    * **Cat 6:** Recommended minimum for all new installations (10 Gbps up to 55m).
    * **Cat 6A:** Best for AV over IP and future-proofing (10 Gbps up to 100m).
* **Fiber Optic:**
    * **OM3/OM4 Multimode:** For 10+ Gbps runs up to 550m.
    * **OS2 Single-Mode:** For distances greater than 1 km.
* **HDMI Over Distance:**
    * **HDMI Direct:** Up to 15 ft for reliable 4K60.
    * **HDBaseT (over Cat6A):** Up to 330 ft (100m) for 4K60.
    * **HDMI Optical/Fiber:** For runs longer than 330 ft.

### Conduit Fill Ratios (NEC)

* **1 Cable:** 53% max fill.
* **2 Cables:** 31% max fill.
* **3+ Cables:** 40% max fill.

### Cable Labeling Standards (AVIXA CLAS)

* **Format:** `[System]-[Endpoint]-[Signal Type]-[Number]`
* **Examples:**
    * `CONF-DSP-AUDIO-01`
    * `CONF-DISP1-HDMI-01`
    * `CONF-CAM-PTZ-01`

---

## 8. Control System Integration

### Control System Architecture

* **Small Rooms (< 150 sq ft):** Native device control (e.g., Teams/Zoom app on a touch-enabled codec) is sufficient.
* **Medium Rooms (150-400 sq ft):** A dedicated touch panel (e.g., 10-inch) and a single-core control processor are recommended.
* **Large Rooms (400+ sq ft):** An advanced, enterprise-grade control processor with multiple interfaces (touch panels, mobile apps) is required to manage system complexity.

### User Interface Design Principles

* **Page Structure:**
    * **Home:** System power, primary source selection.
    * **Source Control:** Detailed controls for each input.
    * **Video Conference:** Call controls, camera controls.
    * **Audio Control:** Volume, muting, presets.
    * **Environmental:** Lighting, shades.
    * **Help:** Support contacts, basic troubleshooting.
* **Button Layout:**
    * **Minimum size:** 0.5" x 0.5" touch target.
    * **Spacing:** 0.1" minimum between buttons.
    * **Common functions:** Place in a persistent toolbar (e.g., volume, mute, help).

---

## 9. Room Type Specifications & Equipment Matrices

### Small Huddle Room (2-4 People, 40-150 sq ft)

* **Dimensions:** 8-12 ft length × 6-10 ft width × 8-10 ft ceiling
* **Display:** Single 43-55 inch commercial 4K display.
* **Video Conferencing:** All-in-one video bar with integrated 4K camera (120° FOV), microphones, and speakers.
* **Connectivity:** Single USB-C cable solution for video, audio, and power is ideal. Include HDMI as a backup.
* **Control:** Native control via the video conferencing platform's interface.
* **Budget Range:** $8,000 - $15,000 USD.

### Medium Conference Room (5-12 People, 150-400 sq ft)

* **Dimensions:** 12-20 ft length × 10-16 ft width × 9-12 ft ceiling
* **Display:** Single 65-75 inch display or dual 55-65 inch displays.
* **Video System:**
    * **Codec:** Dedicated Teams Rooms or Zoom Rooms certified codec.
    * **Camera:** 4K PTZ camera with AI auto-framing and speaker tracking.
* **Audio System:**
    * **DSP:** Required for Acoustic Echo Cancellation (AEC), noise reduction, and audio mixing.
    * **Microphones:** 2-3 ceiling array microphones or 2-4 table boundary microphones.
    * **Speakers:** 4-6 distributed ceiling speakers for uniform coverage.
* **Connectivity:** Table connectivity box with HDMI, USB-C, and network ports. Enterprise wireless presentation system.
* **Control System:** 10-inch wall-mount touch panel with a dedicated processor.
* **Infrastructure:** 12U wall-mount rack, dedicated 20A power circuit, 1500VA UPS.
* **Budget Range:** $25,000 - $50,000 USD.

### Large Boardroom / Executive Conference (12-20 People, 400-800 sq ft)

* **Dimensions:** 20-35 ft length × 16-24 ft width × 10-14 ft ceiling
* **Display System:**
    * **Main:** Dual 75-98 inch 4K commercial displays.
    * **Confidence:** Single 43-55 inch confidence monitor for the presenter.
* **Video System:**
    * **Codec:** High-performance, multi-stream capable codec.
    * **Cameras:** Primary 4K PTZ camera with AI tracking and a secondary wide-angle camera for room overview.
* **Audio System:**
    * **DSP:** Networked audio processor (Dante/AVB) with 16+ inputs.
    * **Microphones:** 2-4 ceiling-mount steerable array microphones.
    * **Speakers:** 8-12 premium ceiling speakers in multiple zones.
* **Signal Management:** 4K video matrix switcher (8x4 minimum).
* **Control System:** Advanced processor with multiple touch panels (wall and table) and integration with lighting, shades, and HVAC.
* **Infrastructure:** 24-42U full-size equipment rack with dedicated cooling, multiple 20A circuits, 3000VA+ UPS.
* **Budget Range:** $75,000 - $200,000 USD.

### Training Room / Classroom (20-40 People, 600-1200 sq ft)

* **Display System:**
    * **Primary:** Laser projector (5000+ lumens) with a 120-150 inch ALR screen.
    * **Secondary:** 2-4 smaller collaboration displays for student breakout groups.
* **Audio System:**
    * **Instructor:** Wireless lavalier/headset microphone.
    * **Student:** 2-4 handheld wireless microphones for Q&A.
    * **Reinforcement:** 12-16 distributed ceiling speakers.
* **Lecture Capture:** Automated system with an instructor-tracking PTZ camera, an audience camera, and content capture.
* **Instructor Station:** Multimedia lectern with integrated PC, document camera, and touch panel control.
* **Infrastructure:** Equipment rack in an adjacent room, high-density Wi-Fi.
* **Budget Range:** $60,000 - $150,000 USD.

---

## 10. AVIXA 10:2013 - Performance Verification Standards

A project-specific verification checklist should be generated, including these key tests:
* **Display Tests:**
    * **Image Size:** Verify display size meets DISCAS calculations.
    * **Resolution & Scaling:** Verify 1:1 pixel mapping with no artifacts.
    * **Brightness & Uniformity:** Measure luminance across a 9-point grid.
    * **Viewing Angle:** Confirm readability from all specified seating positions.
* **Audio Tests:**
    * **SPL Uniformity:** Measure SPL across the listening area to confirm ±3 dB variation (per AVIXA A102.01).
    * **Speech Intelligibility (STI):** Measure to ensure STI is ≥ 0.60.
    * **Microphone Pickup:** Verify clear audio capture from every seating position.
    * **Acoustic Echo Cancellation (AEC):** Conduct a full-duplex test call to ensure no echo.
* **Video Conferencing Tests:**
    * **Camera Coverage:** Verify all participants are visible and framed correctly.
    * **Call Quality:** Conduct a 15-minute test call to check for dropouts, latency, and resolution.
* **Control System Tests:**
    * **UI Functionality:** Test every button and function on the touch panel.
    * **Source Routing:** Confirm all sources can be routed to all displays correctly.

---

## 11. Cost Estimation Framework

### Typical Cost Distribution (% of Total Project)

* **Displays & Projectors:** 30%
* **Audio Systems:** 25%
* **Video Conferencing:** 15%
* **Control & Signal Management:** 10%
* **Cabling & Infrastructure:** 5%
* **Installation Labor:** 10%
* **Programming & Commissioning:** 5%

### Installation Time Multipliers

Installation time should be adjusted based on project complexity. Key factors include:
* **Retrofit vs. New Construction:** Retrofit projects can take up to twice as long.
* **System Integration:** Integration with building systems (lighting, HVAC) adds complexity.
* **Custom Furniture:** Integrating technology into custom furniture requires significant coordination and time.
* **Site Conditions:** High ceilings or restricted site access will increase installation time.

### Service & Support Cost Structure

* **Basic Tier:** 3-year warranty, next-business-day response.
* **Standard Tier:** 5-year warranty, 4-hour response.
* **Premium Tier:** 7-year warranty, 2-hour response, 24x7 coverage, remote monitoring.
* Annual maintenance contracts typically cost 12-20% of the equipment total per year.

### Project Management & Overhead

Overhead costs are calculated as a percentage of the equipment subtotal and vary by project complexity:
* **Simple:** ~23% total overhead (8% PM, 5% Engineering, 5% Contingency, etc.).
* **Standard:** ~36% total overhead (10% PM, 8% Engineering, 8% Contingency, etc.).
* **Complex:** ~56% total overhead (15% PM, 12% Engineering, 10% Contingency, etc.).

---

## 12. Compliance & Accessibility Standards

### ADA (Americans with Disabilities Act) Requirements

* **Hearing Accessibility:** For rooms with capacity ≥ 50, an Assistive Listening System (ALS) is required (e.g., Hearing Loop, IR, or FM system).
* **Visual Accessibility:** System must support display of real-time captions. Visual alarms (strobes) must be integrated with the fire alarm system.
* **Physical Accessibility:** Touch panels and other controls must be mounted between 15-48 inches from the floor and be operable with a closed fist.

### Safety & Building Code Compliance

* **Electrical Safety (NEC):** Use dedicated circuits for AV equipment. All work must comply with local electrical codes.
* **Fire Safety:** All cables in plenum spaces must be plenum-rated (CMP). All penetrations through fire-rated walls must be properly fire-stopped.
* **Structural Requirements:** Display and projector mounts must have a minimum 5x safety factor and be attached to structural members, not just drywall. Professional engineering review may be required.

---

## 17. Documentation Standards (AVIXA D401.01:2023)

As-built documentation is critical for system maintenance and support. The package must include:
* **Architectural Drawings:** As-built floor plans, RCPs, and elevations showing final equipment locations.
* **Equipment Documentation:** Final bill of materials, rack elevations, and manufacturer cut sheets.
* **System Diagrams:** Block diagrams, wiring schematics, and network topology diagrams.
* **Cable Documentation:** A complete cable schedule with labels and test results.
* **Configuration Documentation:** Device settings, IP address schedules, and program files for control and DSP systems.
* **Operational Documentation:** End-user guides, quick reference cards, and training materials.
* **Commissioning Records:** AVIXA 10:2013 verification reports and client sign-off documents.

---

## 18. Training & End-User Documentation

A structured training program should be developed for different user roles:
* **Basic User Training (1 hour):** For all users. Covers system power-on/off, connecting a laptop, starting a video call, and basic audio control.
* **Advanced User Training (2 hours):** For frequent presenters and assistants. Covers advanced source routing, manual camera control, audio presets, and environmental controls.
* **Technical Staff Training (4-6 hours):** For IT/AV staff. Covers system architecture, rack equipment, network configuration, DSP/control system basics, and advanced troubleshooting.

---

## 20. Summary & Best Practices

### Common Pitfalls to Avoid

* **Display:** Selecting consumer TVs instead of commercial displays; undersizing the display for the viewing distance.
* **Audio:** Relying on TV speakers in a conference room; insufficient microphone coverage; not including a DSP for echo cancellation.
* **Video:** Using a camera with a field of view that is too narrow for the room; poor lighting on participants.
* **Infrastructure:** Inadequate power or network ports; no UPS for critical equipment; poor cable management.
* **Costing:** Forgetting to include costs for labor, programming, project management, and contingency.
