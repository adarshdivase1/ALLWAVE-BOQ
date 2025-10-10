# Enhanced AV Design Guidelines for BOQ Generation
## Based on AVIXA Standards & Industry Best Practices

This document provides a comprehensive framework for automated Bill of Quantities (BOQ) generation for audio-visual systems. All calculations and recommendations are based on AVIXA DISCAS, InfoComm AV Best Practices, and real-world implementation experience.

---

## Core Design Philosophy

The BOQ generator operates on a **room-first approach**: analyze the space dimensions, occupancy, and function to determine the appropriate technology tier. Each tier has specific equipment requirements, installation complexity, and cost structures.

### AVIXA DISCAS Display Sizing (Critical for Automation)

**For Detailed Viewing (text/fine detail):**
- Screen Height = Viewing Distance ÷ 6
- Example: 12ft viewing distance = 24" screen height = 55" diagonal (16:9)

**For Basic Viewing (presentations/video):**
- Screen Height = Viewing Distance ÷ 4  
- Example: 12ft viewing distance = 36" screen height = 80" diagonal (16:9)

**BOQ Logic Implementation:**
```
IF room_length > room_width:
    max_viewing_distance = room_length × 0.85
ELSE:
    max_viewing_distance = room_width × 0.85

recommended_screen_height = max_viewing_distance ÷ 6
recommended_diagonal = screen_height ÷ 0.49 (for 16:9 aspect ratio)
```

---

## Room Categories & Technical Specifications

### Small Huddle Room (2-4 People, 40-120 sq ft)

**Space Requirements:**
- Room Length: 8-12 ft
- Room Width: 6-10 ft  
- Ceiling Height: 8-10 ft minimum
- Max Viewing Distance: 6-8 ft

**Visual System Requirements:**
- **Display Size:** 32-55" (based on DISCAS calculations)
- **Display Type:** Commercial-grade flat panel with 10-point touch (optional)
- **Resolution:** 4K minimum for future-proofing
- **Mounting:** Articulating wall mount for table visibility
- **Height:** Display center 42-48" from floor (ADA compliant)

**Audio System Requirements:**
- **Solution:** All-in-one video bar with integrated speakers/microphones
- **Microphone Pickup:** 360° coverage, minimum 8ft radius
- **Audio Processing:** Built-in AEC (Acoustic Echo Cancellation)
- **Sound Pressure Level:** 70-75 dB SPL at seating positions

**Connectivity & Control:**
- **Primary:** USB-C single-cable solution (video + USB + power up to 100W)
- **Secondary:** HDMI + USB-A for legacy devices
- **Wireless:** Built-in wireless presentation capability
- **Network:** 1 Gbps minimum, PoE+ for powered devices
- **Control:** Native room system control (Zoom Rooms, Teams Rooms)

**Power & Infrastructure:**
- **Power Required:** 300-500W total system load
- **Circuit:** Standard 15A circuit adequate
- **UPS:** Optional 15-minute backup for graceful shutdown
- **Cables:** 2 x Cat6A, 1 x HDMI 2.1, 1 x Power

**Installation Complexity:** Low (4-6 hours)
**Typical Budget Range:** $8,000 - $15,000

---

### Medium Conference Room (5-12 People, 120-300 sq ft)

**Space Requirements:**
- Room Length: 12-20 ft
- Room Width: 10-16 ft
- Ceiling Height: 9-12 ft minimum
- Max Viewing Distance: 10-16 ft

**Visual System Requirements:**
- **Display Configuration:** Dual 65-75" displays (content + people)
- **Alternative:** Single 86-98" display for budget constraints
- **Camera:** PTZ camera with auto-framing and speaker tracking
- **Camera Position:** Center-mounted above displays, 8-10ft from table
- **Field of View:** 120° horizontal minimum

**Audio System Requirements (Critical Separation from Visual):**
- **DSP Required:** Digital Signal Processor with AEC, AGC, noise reduction
- **Microphones:** 4-8 ceiling microphones OR 2-4 tabletop microphones
  - **Ceiling Choice:** Clean aesthetic, requires proper acoustic design
  - **Tabletop Choice:** Better performance, more flexible positioning
- **Speakers:** 4-6 ceiling speakers in zones (not display speakers)
- **Coverage:** ±3dB variation across seating area (500Hz-4kHz)
- **Amplification:** Minimum 4-channel amplifier, 50W per channel

**Microphone Placement Logic:**
```
IF ceiling_height < 9ft OR hard_ceiling_surfaces:
    recommend_tabletop_microphones()
ELIF aesthetic_priority AND budget_allows:
    recommend_ceiling_array()
ELSE:
    recommend_tabletop_microphones()
```

**Connectivity & Control:**
- **Room System:** Dedicated codec (Teams Rooms/Zoom Rooms certified)
- **BYOD Integration:** Table connectivity box with HDMI/USB-C
- **Wireless Sharing:** Enterprise wireless presentation system
- **Control Interface:** 10" touch panel with custom programming
- **Network:** Dedicated VLAN, QoS configured, 100 Mbps minimum per endpoint

**Power & Infrastructure:**
- **Power Required:** 800-1,500W total system load
- **Circuit Requirement:** Dedicated 20A circuit recommended
- **UPS:** 30-minute backup for all critical components
- **Equipment Housing:** Wall-mounted or furniture-integrated rack
- **Cable Requirements:** 
  - 6-12 x Cat6A (network, control, audio)
  - 4-8 x Audio cables (balanced XLR)
  - 2-4 x Video cables (HDMI 2.1 or HDBaseT)

**Installation Complexity:** Medium (12-20 hours)
**Typical Budget Range:** $25,000 - $50,000

---

### Large Boardroom/Training Room (12+ People, 300+ sq ft)

**Space Requirements:**
- Room Length: 20+ ft
- Room Width: 16+ ft
- Ceiling Height: 10+ ft minimum
- Max Viewing Distance: 20+ ft

**Visual System Requirements:**
- **Executive Boardroom:** 2 x 86-98" displays + confidence monitor
- **Training Room:** Laser projector (5,000+ lumens) + ALR screen OR fine-pitch LED wall
- **Camera System:** Multi-camera with auto-switching
  - Primary: Room overview camera
  - Secondary: Speaker tracking PTZ camera
  - Optional: Document camera integration

**Audio System Requirements (Mission-Critical Performance):**
- **DSP:** Networked audio processor (Dante/AVB capable)
- **Microphone System:** Ceiling-mounted steerable array (e.g., Shure MXA920)
  - Multiple virtual pickup lobes
  - Automatic speaker tracking
  - Zone-based coverage
- **Speaker System:** 8-16 ceiling speakers in 4 zones minimum
- **Voice Lift System:** For rooms >500 sq ft - microphone audio reinforcement
- **Amplification:** Networked amplifiers with individual channel monitoring

**Advanced Features:**
- **Acoustic Echo Cancellation:** Multi-channel AEC with reference signals
- **Automatic Mixing:** Priority-based microphone mixing
- **Audio Recording:** Integrated recording capability for training rooms
- **Assistive Listening:** IR or FM system for ADA compliance

**Connectivity & Control:**
- **Control System:** Advanced programmable control processor
- **User Interface:** Multiple touch panels + mobile app control
- **Integration:** Lighting, HVAC, window shades, security systems
- **Recording/Streaming:** Built-in capability for training/corporate communications
- **Redundancy:** Backup systems for mission-critical installations

**Power & Infrastructure:**
- **Power Required:** 2,000-5,000W total system load
- **Circuit Requirements:** Multiple dedicated 20A circuits
- **UPS:** 60-minute backup minimum, automatic failover
- **Equipment Housing:** Full-size rack (24-42U) with environmental monitoring
- **Cooling:** Dedicated HVAC or rack cooling system
- **Cable Infrastructure:**
  - 20+ x Cat6A (network, control, audio over IP)
  - Fiber optic for high-bandwidth video
  - Dedicated emergency power connections

**Installation Complexity:** High (40-80 hours)
**Typical Budget Range:** $75,000 - $200,000+

---

## Specialized Room Types

### Executive Telepresence Suite

**Unique Requirements:**
- **Lighting:** Professionally designed LED lighting with scene control
- **Acoustics:** Enhanced acoustic treatment, RT60 <0.6 seconds
- **Camera:** 4K cameras with professional color accuracy
- **Audio:** Separate zones for local and remote audio optimization
- **Furniture:** Purpose-built telepresence table with integrated technology

### Training/Classroom

**Instructor-Centric Design:**
- **Lectern:** Integrated control and connectivity
- **Student Response System:** Interactive polling/feedback
- **Content Sharing:** Multiple wireless sharing zones
- **Recording:** Lecture capture with automatic camera switching
- **Breakout Capability:** Audio zones for small group work

### Multipurpose/Divisible Spaces

**Flexible Configuration Requirements:**
- **Airwall Integration:** Automated partition control
- **Audio Combining:** Automatic system combining when walls open
- **Video Distribution:** Content sharing across divided spaces
- **Independent Control:** Separate system operation when divided

---

## Technical Selection Criteria

### Codec Selection Matrix

**Microsoft Teams Environments:**
- **Small:** Teams Rooms on Windows (computer-based)
- **Medium:** Teams Rooms on Android (appliance-based)  
- **Large:** Teams Rooms with custom AV integration

**Zoom Environments:**
- **Small/Medium:** Zoom Rooms appliance
- **Large:** Zoom Rooms with AV integration

**Platform Agnostic:**
- Use BYOD-friendly systems with USB/HDMI connectivity

### Network Requirements by Room Size

**Small Huddle:** 10 Mbps up/down minimum
**Medium Conference:** 25 Mbps up/down minimum  
**Large Boardroom:** 50+ Mbps up/down minimum
**Training Room:** 100+ Mbps (for recording/streaming)

**QoS Requirements:**
- Video: DSCP 34 (AF41)
- Audio: DSCP 46 (EF)
- Control: DSCP 26 (AF31)

---

## Cost Estimation Framework

### Equipment Cost Percentages (of total project)
- **Displays & Cameras:** 30-40%
- **Audio Systems:** 20-30%
- **Control & Connectivity:** 15-25%
- **Installation & Programming:** 20-30%
- **Project Management:** 5-10%

### Installation Time Multipliers
- **Basic Installation:** 1.0x
- **Complex Programming Required:** 1.5x
- **Integration with Building Systems:** 2.0x
- **Custom Furniture Integration:** 1.8x
- **Retrofit/Renovation:** 2.5x

### Service & Support Structure
- **Standard Warranty:** 3 years parts/labor
- **Extended Warranty:** Available 5-7 years
- **Maintenance Contract:** 15-25% of equipment cost annually
- **Emergency Response:** 4-hour/next day options

---

## Compliance & Accessibility

### ADA Requirements (US Installations)
- **Hearing Loop Systems:** Required for assembly areas >50 people
- **Visual Notification:** Strobe lights for emergency announcements
- **Control Accessibility:** Touch panels 15-48" height, operable with closed fist
- **Assistive Listening:** FM/IR systems for 4% of seating (minimum 2 units)

### Safety & Building Codes
- **Electrical:** NEC compliance, dedicated circuits for high-power systems
- **Fire Safety:** Plenum-rated cables, fire stopping of penetrations
- **Seismic:** Equipment mounting rated for local seismic zones
- **Emergency Systems:** Integration with fire alarm for automatic shutdown

---

## BOQ Generation Logic

### Automated Equipment Selection Process

1. **Room Analysis**
   - Calculate display size using DISCAS formulas
   - Determine audio coverage requirements
   - Assess power and infrastructure needs

2. **Equipment Database Matching**
   - Filter by room size category
   - Match performance specifications
   - Consider brand preferences and budget constraints

3. **Integration Requirements**
   - Calculate cable runs and quantities
   - Determine control system complexity
   - Assess installation time requirements

4. **Cost Calculation**
   - Apply regional pricing factors
   - Include installation complexity multipliers
   - Add service and support options

5. **Validation & Optimization**
   - Verify AVIXA compliance
   - Check power and infrastructure capacity
   - Optimize for performance/cost ratio

This framework ensures consistent, professional AV system designs that meet performance requirements while staying within budget parameters.
