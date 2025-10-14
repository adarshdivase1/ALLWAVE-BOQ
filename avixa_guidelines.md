# Enhanced AV Design Guidelines for BOQ Generation (Continued)

```python
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

---

### Medium Conference Room (5-12 People, 150-400 sq ft)

**Dimensions:** 12-20 ft length Ã— 10-16 ft width Ã— 9-12 ft ceiling

**Required Equipment:**
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

**Microphone Selection Logic:**
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

---

### Large Boardroom / Executive Conference (12-20 People, 400-800 sq ft)

**Dimensions:** 20-35 ft length Ã— 16-24 ft width Ã— 10-14 ft ceiling

**Required Equipment:**
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

---

### Training Room / Classroom (20-40 People, 600-1200 sq ft)

**Dimensions:** 30-45 ft length Ã— 20-30 ft width Ã— 10-14 ft ceiling

**Required Equipment:**
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

---

### Auditorium / Large Event Space (100-500 People, 2000-10000 sq ft)

**Dimensions:** Variable, typically 50-100 ft length Ã— 40-80 ft width Ã— 16-30 ft ceiling

**Required Equipment (Summary - Highly Complex):**
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

---

## 10. AVIXA 10:2013 - Performance Verification Standards

### Verification Test Categories

**The AVIXA 10:2013 standard defines 160+ verification criteria across these categories:**

1. **Display Performance Tests**
2. **Audio Performance Tests**
3. **Video Performance Tests**
4. **Control System Tests**
5. **Network & Connectivity Tests**
6. **Integration Tests**
7. **Safety & Compliance Tests**

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

---

## 11. Cost Estimation Framework

### Equipment Cost Structure

**Typical Cost Distribution (% of total project):**
```python
cost_distribution = {
    "Displays & Projectors": 0.30,        # 30%
    "Audio Systems": 0.25,                # 25%
    "Video Conferencing": 0.15,           # 15%
    "Control & Signal Management": 0.10,  # 10%
    "Cabling & Infrastructure": 0.05,     # 5%
    "Installation Labor": 0.10,           # 10%
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
        multiplier Ã—= 1.5
    
    if project_factors["building_system_integration"]:
        multiplier Ã—= 1.3
    
    if project_factors["custom_furniture_integration"]:
        multiplier Ã—= 1.4
    
    if project_factors["project_type"] == "retrofit":
        multiplier Ã—= 2.0  # Renovation projects take longer
    elif project_factors["project_type"] == "new_construction":
        multiplier Ã—= 0.9  # New construction slightly faster
    
    if project_factors["ceiling_height"] > 14:
        multiplier Ã—= 1.3  # Lifts and safety equipment needed
    
    if project_factors["site_access"] == "restricted":
        multiplier Ã—= 1.2  # Limited working hours
    
    adjusted_hours = base_hours Ã— multiplier
    
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
    adjusted_price_usd = base_price_usd Ã— multiplier
    
    if currency != "USD":
        final_price = adjusted_price_usd Ã— exchange_rates[currency]
    else:
        final_price = adjusted_price_usd
    
    return {
        "base_price_usd": base_price_usd,
        "regional_multiplier": multiplier,
        "adjusted_price_usd": adjusted_price_usd,
        # Enhanced AV Design Guidelines for BOQ Generation (Continued)

```python
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
            "warranty_cost_percent": 0.05,      # 5% of equipment
            "annual_maintenance_percent": 0.12,  # 12% per year
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
            "project_management": 0.08,      # 8%
            "design_engineering": 0.05,      # 5%
            "site_supervision": 0.03,        # 3%
            "documentation": 0.02,           # 2%
            "contingency": 0.05              # 5%
        },
        "Standard": {
            "project_management": 0.10,      # 10%
            "design_engineering": 0.08,      # 8%
            "site_supervision": 0.05,        # 5%
            "documentation": 0.03,           # 3%
            "commissioning": 0.02,           # 2%
            "contingency": 0.08              # 8%
        },
        "Complex": {
            "project_management": 0.15,      # 15%
            "design_engineering": 0.12,      # 12%
            "site_supervision": 0.08,        # 8%
            "documentation": 0.05,           # 5%
            "commissioning": 0.04,           # 4%
            "training": 0.02,                # 2%
            "contingency": 0.10              # 10%
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

---

## 12. Compliance & Accessibility Standards

### ADA (Americans with Disabilities Act) Requirements

**For US Installations - Critical Compliance Points:**

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

---

## 13. Product Selection Logic & AI Justification Framework

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

---

## 14. Excel Export Specifications

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
            # Serial Number
            ws[f'A{row}'] = serial_no
            
            # Category
            ws[f'B{row}'] = item['category']
            
            # Product Name
            ws[f'C{row}'] = item['name']
            ws[f'C{row}'].alignment = Alignment(wrap_text=True)
            
            # Brand
            ws[f'D{row}'] = item.get('brand', 'N/A')
            
            # Model Number
            ws[f'E{row}'] = item.get('model_number', 'N/A')
            
            # Product Image (Generated PNG)
            if item.get('product_image'):
                img = Image(item['product_image'])
                img.width = 100
                img.height = 100
                ws.add_image(img, f'F{row}')
                ws.row_dimensions[row].height = 75
            
            # Specifications
            ws[f'G{row}'] = item.get('specifications', 'Standard specifications')
            ws[f'G{row}'].alignment = Alignment(wrap_text=True)
            
            # Quantity
            ws[f'H{row}'] = item['quantity']
            ws[f'H{row}'].number_format = '0'
            
            # Unit
            ws[f'I{row}'] = item.get('unit', 'Each')
            
            # Unit Price
            ws[f'J{row}'] = item['price']
            ws[f'J{row}'].number_format = '"$"#,##0.00' if room_data['currency'] == 'USD' else '"₹"#,##0.00'
            
            # Total Price
            total_price = item['quantity'] * item['price']
            ws[f'K{row}'] = total_price
            ws[f'K{row}'].number_format = '"$"#,##0.00' if room_data['currency'] == 'USD' else '"₹"#,##0.00'
            
            # Warranty
            ws[f'L{row}'] = item.get('warranty', '1 Year')
            
            # Lead Time
            ws[f'M{row}'] = item.get('lead_time_days', 30)
            ws[f'M{row}'].number_format = '0" days"'
            
            # GST %
            gst_rate = item.get('gst_rate', 18)
            ws[f'N{row}'] = gst_rate / 100
            ws[f'N{row}'].number_format = '0%'
            
            # GST Amount
            gst_amount = total_price * (gst_rate / 100)
            ws[f'O{row}'] = gst_amount
            ws[f'O{row}'].number_format = '"$"#,##0.00' if room_data['currency'] == 'USD' else '"₹"#,##0.00'
            
            # Total with GST
            ws[f'P{row}'] = total_price + gst_amount
            ws[f'P{row}'].number_format = '"$"#,##0.00' if room_data['currency'] == 'USD' else '"₹"#,##0.00'
            
            # Top 3 Reasons (AI Generated)
            if item.get('top_3_reasons'):
                reasons_text = "\n".join([f"{i+1}. {reason}" 
                                        for i, reason in enumerate(item['top_3_reasons'])])
                ws[f'Q{row}'] = reasons_text
                ws[f'Q{row}'].alignment = Alignment(wrap_text=True, vertical='top')
                ws.row_dimensions[row].height = max(75, len(reasons_text) / 2)
            
            # Apply borders
            for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q']:
                ws[f'{col}{row}'].border = Border(
                    left=Side(style='thin'),
                    right=Side(style='thin'),
                    top=Side(style='thin'),
                    bottom=Side(style='thin')
                )
            
            row += 1
            serial_no += 1
        
        # Financial Summary Section
        self.add_financial_summary(ws, row, room_data)
        
        return ws
    
    def add_financial_summary(self, ws, start_row, room_data):
        """
        Add financial summary with installation, services, and GST
        """
        
        row = start_row + 2
        
        # Calculate totals
        hardware_subtotal = sum(item['quantity'] * item['price'] for item in room_data['boq_items'])
        installation = hardware_subtotal * 0.15
        warranty_extended = hardware_subtotal * 0.05
        project_mgmt = hardware_subtotal * 0.10
        
        subtotal_before_gst = hardware_subtotal + installation + warranty_extended + project_mgmt
        
        sgst = subtotal_before_gst * 0.09
        cgst = subtotal_before_gst * 0.09
        
        grand_total = subtotal_before_gst + sgst + cgst
        
        # Summary rows
        summary_items = [
            ("Hardware Subtotal", hardware_subtotal),
            ("Installation (15%)", installation),
            ("Extended Warranty (5%)", warranty_extended),
            ("Project Management (10%)", project_mgmt),
            ("", ""),  # Blank row
            ("Subtotal (Before GST)", subtotal_before_gst),
            ("SGST (9%)", sgst),
            ("CGST (9%)", cgst),
            ("", ""),  # Blank row
            ("GRAND TOTAL", grand_total)
        ]
        
        for label, amount in summary_items:
            ws.merge_cells(f'N{row}:O{row}')
            ws[f'N{row}'] = label
            ws[f'N{row}'].font = Font(bold=True if label in ["Hardware Subtotal", "GRAND TOTAL"] else False)
            ws[f'N{row}'].alignment = Alignment(horizontal='right')
            
            if amount:
                ws[f'P{row}'] = amount
                ws[f'P{row}'].number_format = '"$"#,##0.00' if room_data['currency'] == 'USD' else '"₹"#,##0.00'
                ws[f'P{row}'].font = Font(bold=True if label == "GRAND TOTAL" else False)
                
                if label == "GRAND TOTAL":
                    ws[f'P{row}'].fill = PatternFill(start_color='FFD700', end_color='FFD700', fill_type='solid')
            
            row += 1
```

---

## 15. Integration with BOQ Generator Application

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
    
    # Stage 8: Generate verification checklist
    verification_plan = generate_verification_checklist(
        project_params['room_type'],
        validated_boq
      # Enhanced AV Design Guidelines for BOQ Generation (Continued)

```python
    )
    
    # Stage 8 (Continued): Final assembly
    final_boq = {
        "project_metadata": project_params,
        "avixa_calculations": avixa_calcs,
        "equipment_requirements": equipment_reqs,
        "boq_items": validated_boq,
        "quality_score": quality_report,
        "verification_plan": verification_plan,
        "total_cost": calculate_total_cost(validated_boq),
        "installation_estimate": estimate_installation(validated_boq, project_params),
        "warnings": quality_report.get('warnings', []),
        "recommendations": quality_report.get('recommendations', [])
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
    
    # === CONNECTIVITY REQUIREMENTS ===
    connectivity_req = determine_connectivity_requirements(room_type, capacity)
    requirements.extend(connectivity_req)
    
    # === INFRASTRUCTURE REQUIREMENTS ===
    infrastructure_req = determine_infrastructure_requirements(requirements, room_area)
    requirements.extend(infrastructure_req)
    
    # === MOUNTING & INSTALLATION REQUIREMENTS ===
    mounting_req = determine_mounting_requirements(requirements)
    requirements.extend(mounting_req)
    
    return requirements


def determine_display_requirements(room_type, room_area, capacity, budget_tier):
    """
    Determine display requirements using AVIXA DISCAS standards
    """
    
    requirements = []
    
    if room_area < 150:
        # Small Huddle Room
        requirements.append(ProductRequirement(
            category='Displays',
            sub_category='Commercial Display',
            quantity=1,
            priority=1,
            justification='Primary display for content sharing and video conferencing',
            size_requirement=55,  # inches
            required_keywords=['4K', 'commercial', 'display'],
            blacklist_keywords=['consumer', 'tv', 'smart tv'],
            min_price=400,
            max_price=2000,
            strict_category_match=True
        ))
    
    elif room_area < 400:
        # Medium Conference Room
        if budget_tier == "Premium":
            # Dual display configuration
            requirements.append(ProductRequirement(
                category='Displays',
                sub_category='Commercial Display',
                quantity=2,
                priority=1,
                justification='Dual displays for content + video feed separation',
                size_requirement=65,
                required_keywords=['4K', 'commercial'],
                blacklist_keywords=['consumer', 'tv'],
                min_price=800,
                max_price=3000,
                strict_category_match=True
            ))
        else:
            # Single large display
            requirements.append(ProductRequirement(
                category='Displays',
                sub_category='Commercial Display',
                quantity=1,
                priority=1,
                justification='Primary large-format display for presentations',
                size_requirement=75,
                required_keywords=['4K', 'commercial'],
                min_price=1200,
                max_price=4000,
                strict_category_match=True
            ))
    
    else:
        # Large Boardroom
        requirements.append(ProductRequirement(
            category='Displays',
            sub_category='Commercial Display',
            quantity=2,
            priority=1,
            justification='Dual large-format displays for executive presentation',
            size_requirement=86,
            required_keywords=['4K', 'commercial', 'professional'],
            min_price=2500,
            max_price=8000,
            strict_category_match=True
        ))
        
        # Confidence monitor
        requirements.append(ProductRequirement(
            category='Displays',
            sub_category='Commercial Display',
            quantity=1,
            priority=2,
            justification='Confidence monitor for presenter feedback',
            size_requirement=43,
            required_keywords=['commercial'],
            min_price=400,
            max_price=1000,
            strict_category_match=True
        ))
    
    return requirements


def determine_audio_requirements(room_type, room_area, capacity, client_preferences):
    """
    Determine audio system requirements based on AVIXA A102.01 standards
    """
    
    requirements = []
    
    if room_area < 150:
        # Small room - integrated audio in video bar (handled in VC section)
        pass
    
    elif room_area < 400:
        # Medium room - dedicated audio system
        
        # DSP Processor
        requirements.append(ProductRequirement(
            category='Audio',
            sub_category='DSP / Audio Processor',
            quantity=1,
            priority=1,
            justification='Digital signal processing for echo cancellation and audio mixing',
            required_keywords=['dsp', 'processor', 'dante'],
            blacklist_keywords=['consumer', 'home'],
            min_price=500,
            max_price=3000,
            strict_category_match=True
        ))
        
        # Microphones (ceiling or table-mount)
        mic_count = max(2, math.ceil(room_area / 150))
        
        if client_preferences.get('microphone_preference') == 'ceiling':
            requirements.append(ProductRequirement(
                category='Audio',
                sub_category='Microphone Array',
                quantity=mic_count,
                priority=1,
                justification='Ceiling microphone arrays for clean aesthetic',
                required_keywords=['ceiling', 'array', 'beamforming'],
                min_price=600,
                max_price=2500,
                strict_category_match=True
            ))
        else:
            requirements.append(ProductRequirement(
                category='Audio',
                sub_category='Boundary Microphone',
                quantity=mic_count,
                priority=1,
                justification='Table boundary microphones for optimal pickup',
                required_keywords=['boundary', 'table', 'conference'],
                min_price=200,
                max_price=800,
                strict_category_match=True
            ))
        
        # Ceiling Speakers
        speaker_count = max(4, math.ceil(room_area / 100))
        requirements.append(ProductRequirement(
            category='Audio',
            sub_category='Ceiling Speaker',
            quantity=speaker_count,
            priority=1,
            justification='Ceiling speakers for uniform audio coverage',
            required_keywords=['ceiling', 'speaker', '70v'],
            blacklist_keywords=['home', 'consumer'],
            min_price=100,
            max_price=400,
            strict_category_match=True
        ))
        
        # Amplifier
        requirements.append(ProductRequirement(
            category='Audio',
            sub_category='Amplifier',
            quantity=1,
            priority=1,
            justification='Multi-channel amplifier for speaker distribution',
            power_requirement=100,  # watts per channel
            required_keywords=['amplifier', 'multi-channel'],
            min_price=400,
            max_price=2000,
            strict_category_match=True
        ))
    
    else:
        # Large room - professional audio system
        
        # Networked DSP
        requirements.append(ProductRequirement(
            category='Audio',
            sub_category='DSP / Audio Processor',
            quantity=1,
            priority=1,
            justification='Enterprise-grade networked audio processor with Dante',
            required_keywords=['dante', 'dsp', 'networked', 'enterprise'],
            min_price=2000,
            max_price=8000,
            strict_category_match=True
        ))
        
        # Ceiling Microphone Arrays (Steerable)
        mic_count = max(2, math.ceil(room_area / 200))
        requirements.append(ProductRequirement(
            category='Audio',
            sub_category='Microphone Array',
            quantity=mic_count,
            priority=1,
            justification='Ceiling-mount steerable microphone arrays with auto-tracking',
            required_keywords=['ceiling', 'array', 'steerable', 'beamforming'],
            min_price=1500,
            max_price=4000,
            strict_category_match=True
        ))
        
        # Professional Ceiling Speakers
        speaker_count = max(8, math.ceil(room_area / 80))
        requirements.append(ProductRequirement(
            category='Audio',
            sub_category='Ceiling Speaker',
            quantity=speaker_count,
            priority=1,
            justification='Premium ceiling speakers for high-fidelity audio',
            required_keywords=['ceiling', 'speaker', 'commercial'],
            min_price=150,
            max_price=600,
            strict_category_match=True
        ))
        
        # Networked Amplifier
        requirements.append(ProductRequirement(
            category='Audio',
            sub_category='Amplifier',
            quantity=1,
            priority=1,
            justification='Networked multi-channel amplifier with monitoring',
            power_requirement=200,
            required_keywords=['amplifier', 'dante', 'networked'],
            min_price=1500,
            max_price=5000,
            strict_category_match=True
        ))
    
    return requirements


def determine_video_conferencing_requirements(room_area, capacity, budget_tier):
    """
    Determine video conferencing equipment requirements
    """
    
    requirements = []
    
    if room_area < 150:
        # All-in-one video bar
        requirements.append(ProductRequirement(
            category='Video Conferencing',
            sub_category='Video Bar / All-in-One',
            quantity=1,
            priority=1,
            justification='All-in-one video bar with integrated camera, speakers, microphones',
            required_keywords=['video bar', 'all-in-one', 'usb'],
            blacklist_keywords=['consumer', 'webcam'],
            min_price=600,
            max_price=2500,
            strict_category_match=True
        ))
    
    elif room_area < 400:
        # Dedicated codec
        requirements.append(ProductRequirement(
            category='Video Conferencing',
            sub_category='Video Codec / Conferencing System',
            quantity=1,
            priority=1,
            justification='Dedicated video conferencing codec for Teams/Zoom Rooms',
            required_keywords=['codec', 'teams', 'zoom'],
            blacklist_keywords=['consumer', 'personal'],
            min_price=800,
            max_price=3500,
            strict_category_match=True
        ))
        
        # PTZ Camera
        requirements.append(ProductRequirement(
            category='Video Conferencing',
            sub_category='PTZ Camera',
            quantity=1,
            priority=1,
            justification='PTZ camera with auto-framing and speaker tracking',
            required_keywords=['ptz', '4k', 'auto-framing'],
            min_price=1000,
            max_price=4000,
            strict_category_match=True
        ))
    
    else:
        # Large room - professional codec
        requirements.append(ProductRequirement(
            category='Video Conferencing',
            sub_category='Video Codec / Conferencing System',
            quantity=1,
            priority=1,
            justification='Enterprise video conferencing codec with dual-platform support',
            required_keywords=['codec', 'enterprise', '4k'],
            min_price=2500,
            max_price=10000,
            strict_category_match=True
        ))
        
        # Primary PTZ Camera
        requirements.append(ProductRequirement(
            category='Video Conferencing',
            sub_category='PTZ Camera',
            quantity=1,
            priority=1,
            justification='Primary 4K PTZ camera with AI tracking',
            required_keywords=['ptz', '4k', 'ai', 'tracking'],
            min_price=2000,
            max_price=6000,
            strict_category_match=True
        ))
        
        # Secondary Camera (optional)
        if budget_tier == "Premium":
            requirements.append(ProductRequirement(
                category='Video Conferencing',
                sub_category='Fixed Camera',
                quantity=1,
                priority=2,
                justification='Secondary fixed camera for room overview',
                required_keywords=['camera', '4k', 'wide'],
                min_price=500,
                max_price=2000,
                strict_category_match=True
            ))
    
    return requirements


def determine_control_requirements(room_area, complexity):
    """
    Determine control system requirements
    """
    
    requirements = []
    
    if room_area < 150:
        # Native control (no dedicated control system)
        pass
    
    elif room_area < 400:
        # Standard control system
        requirements.append(ProductRequirement(
            category='Control Systems',
            sub_category='Control Processor',
            quantity=1,
            priority=1,
            justification='Dedicated control processor for system automation',
            required_keywords=['control', 'processor', 'automation'],
            min_price=800,
            max_price=2500,
            strict_category_match=True
        ))
        
        requirements.append(ProductRequirement(
            category='Control Systems',
            sub_category='Touch Panel',
            quantity=1,
            priority=1,
            justification='Wall-mount touch panel for user interface',
            required_keywords=['touch', 'panel', '10-inch'],
            min_price=600,
            max_price=1500,
            strict_category_match=True
        ))
    
    else:
        # Advanced control system
        requirements.append(ProductRequirement(
            category='Control Systems',
            sub_category='Control Processor',
            quantity=1,
            priority=1,
            justification='Enterprise control processor with advanced integration',
            required_keywords=['control', 'processor', 'enterprise'],
            min_price=2000,
            max_price=6000,
            strict_category_match=True
        ))
        
        requirements.append(ProductRequirement(
            category='Control Systems',
            sub_category='Touch Panel',
            quantity=2,
            priority=1,
            justification='Multiple touch panels for control redundancy',
            required_keywords=['touch', 'panel'],
            min_price=800,
            max_price=2000,
            strict_category_match=True
        ))
    
    return requirements


def determine_connectivity_requirements(room_type, capacity):
    """
    Determine connectivity and cable management requirements
    """
    
    requirements = []
    
    # Table Connectivity Box
    box_count = 1 if capacity <= 6 else 2
    requirements.append(ProductRequirement(
        category='Cables & Connectivity',
        sub_category='Connectivity Box / Cable Cubby',
        quantity=box_count,
        priority=1,
        justification='Table connectivity for HDMI, USB-C, and network',
        required_keywords=['connectivity', 'table', 'hdmi', 'usb-c'],
        min_price=200,
        max_price=800,
        strict_category_match=True
    ))
    
    # Wireless Presentation System
    requirements.append(ProductRequirement(
        category='Signal Management',
        sub_category='Wireless Presentation',
        quantity=1,
        priority=2,
        justification='Wireless presentation for BYOD convenience',
        required_keywords=['wireless', 'presentation', 'airplay'],
        min_price=500,
        max_price=2000,
        strict_category_match=True
    ))
    
    return requirements


def determine_infrastructure_requirements(equipment_list, room_area):
    """
    Determine infrastructure requirements (racks, power, network)
    """
    
    requirements = []
    
    # Determine if rack is needed
    equipment_count = len([e for e in equipment_list if e.priority == 1])
    
    if equipment_count > 5:
        # Equipment rack required
        if room_area < 400:
            requirements.append(ProductRequirement(
                category='Infrastructure',
                sub_category='Equipment Rack',
                quantity=1,
                priority=1,
                justification='Wall-mount equipment rack for AV components',
                required_keywords=['rack', '12u', 'wall'],
                min_price=200,
                max_price=800,
                strict_category_match=True
            ))
        else:
            requirements.append(ProductRequirement(
                category='Infrastructure',
                sub_category='Equipment Rack',
                quantity=1,
                priority=1,
                justification='Full-size equipment rack with cooling',
                required_keywords=['rack', '24u', 'floor'],
                min_price=500,
                max_price=2000,
                strict_category_match=True
            ))
        
        # Power Distribution Unit (PDU)
        requirements.append(ProductRequirement(
            category='Infrastructure',
            sub_category='PDU / Power Distribution',
            quantity=1,
            priority=1,
            justification='Rack-mount PDU for clean power distribution',
            required_keywords=['pdu', 'power', 'rack'],
            min_price=100,
            max_price=500,
            strict_category_match=True
        ))
        
        # UPS (Uninterruptible Power Supply)
        requirements.append(ProductRequirement(
            category='Infrastructure',
            sub_category='UPS / Battery Backup',
            quantity=1,
            priority=2,
            justification='UPS for system protection and graceful shutdown',
            required_keywords=['ups', 'battery', 'backup'],
            min_price=300,
            max_price=1500,
            strict_category_match=True
        ))
    
    # Network Switch
    if room_area >= 150:
        requirements.append(ProductRequirement(
            category='Networking',
            sub_category='Network Switch',
            quantity=1,
            priority=1,
            justification='Managed PoE switch for AV network infrastructure',
            required_keywords=['switch', 'poe', 'managed', 'gigabit'],
            min_price=300,
            max_price=1500,
            strict_category_match=True
        ))
    
    return requirements


def determine_mounting_requirements(equipment_list):
    """
    Determine mounting hardware requirements based on equipment
    """
    
    requirements = []
    
    # Count displays
    display_count = sum(1 for e in equipment_list if e.category == 'Displays')
    
    if display_count > 0:
        requirements.append(ProductRequirement(
            category='Mounts',
            sub_category='Display Mount / Wall Mount',
            quantity=display_count,
            priority=1,
            justification='Fixed or articulating wall mounts for displays',
            required_keywords=['mount', 'wall', 'display'],
            blacklist_keywords=['camera', 'speaker'],
            min_price=100,
            max_price=800,
            strict_category_match=True
        ))
    
    # Count cameras
    camera_count = sum(1 for e in equipment_list 
                      if 'Camera' in e.sub_category or 'PTZ' in e.sub_category)
    
    if camera_count > 0:
        requirements.append(ProductRequirement(
            category='Mounts',
            sub_category='Camera Mount',
            quantity=camera_count,
            priority=1,
            justification='Ceiling or wall mount for camera positioning',
            required_keywords=['mount', 'camera', 'ptz'],
            blacklist_keywords=['display', 'tv'],
            min_price=50,
            max_price=400,
            strict_category_match=True
        ))
    
    # Speakers (if ceiling speakers present)
    speaker_count = sum(1 for e in equipment_list if 'Ceiling Speaker' in e.sub_category)
    
    if speaker_count > 0:
        requirements.append(ProductRequirement(
            category='Mounts',
            sub_category='Speaker Mount / Tile Bridge',
            quantity=speaker_count,
            priority=1,
            justification='Ceiling tile bridges for speaker installation',
            required_keywords=['tile', 'bridge', 'ceiling'],
            min_price=10,
            max_price=50,
            strict_category_match=True
        ))
    
    return requirements
```

---

## 16. Validation & Quality Scoring

### BOQ Quality Assessment

```python
def score_boq_quality(boq_items, avixa_calcs, equipment_reqs):
    """
    Comprehensive quality scoring system for generated BOQ
    100-point scale across multiple criteria
    """
    
    scores = {
        "avixa_compliance": 0,      # 30 points
        "completeness": 0,           # 25 points
        "price_reasonableness": 0,   # 15 points
        "brand_consistency": 0,      # 10 points
        "specification_match": 0,    # 10 points
        "integration_quality": 0     # 10 points
    }
    
    warnings = []
    recommendations = []
    
    # 1. AVIXA Compliance (30 points)
    avixa_score = 0
    
    # Display size compliance
    display_items = [item for item in boq_items if 'Display' in item['category']]
    if display_items:
        actual_display_size = max(item.get('size_inches', 0) for item in display_items)
        recommended_size = avixa_calcs.get('recommended_display_size_inches', 0)
        
        if abs(actual_display_size - recommended_size) <= 10:
            avixa_score += 10
        elif abs(actual_display_size - recommended_size) <= 20:
            avixa_score += 5
            warnings.append(f"Display size ({actual_display_size}\") deviates from AVIXA recommendation ({recommended_size}\")")
        else:
            warnings.append(f"⚠️ CRITICAL: Display size significantly undersized. Recommended: {recommended_size}\", Selected: {actual_display_size}\"")
    
    # Audio coverage compliance
    speaker_items = [item for item in boq_items if 'Speaker' in item.get('sub_category', '')]
    if speaker_items:
        total_speakers = sum(item['quantity'] for item in speaker_items)
        recommended_speakers = avixa_calcs.get('recommended_speaker_count', 0)
        
        if total_speakers >= recommended_speakers:
            avixa_score += 10
        else:
            avixa_score += 5
            warnings.append(f"Speaker count ({total_speakers}) below AVIXA recommendation ({recommended_speakers})")
    
    # Microphone coverage compliance
    mic_items = [item for item in boq_items if 'Microphone' in item.get('sub_category', '')]
    if mic_items:
        total_mics = sum(item['quantity'] for item in mic_items)
        recommended_mics = avixa_calcs.get('recommended_mic_count', 0)
        
        if total_mics >= recommended_mics:
            avixa_score += 10
        else:
            avixa_score += 5
            warnings.append(f"Microphone count ({total_mics}) below AVIXA recommendation ({recommended_mics})")
    
    scores["avixa_compliance"] = avixa_score
    
    # 2. Completeness (25 points)
    completeness_score = 0
    
    required_categories = ['Displays', 'Video Conferencing', 'Audio', 'Control Systems', 'Connectivity', 'Mounts']
    present_categories = set(item['category'] for item in boq_items)
    
    category_coverage = len(present_categories.intersection(required_categories)) / len(required_categories)
    completeness_score += category_coverage * 15
    
    # Check for critical missing items
    if 'Displays' not in present_categories:
        warnings.append("⚠️ CRITICAL: No displays in BOQ")
    
    if avixa_calcs.get('room_area_sqft', 0) >= 150:
        if 'Audio' not in present_categories:
            warnings.append("⚠️ WARNING: No dedicated audio system for medium/large room")
    
    # Check for mounts
    display_count = sum(item['quantity'] for item in boq_items if 'Display' in item['category'])
    mount_count = sum(item['quantity'] for item in boq_items if 'Mount' in item['category'])
    
    if display_count > 0 and mount_count < display_count:
        warnings.append(f"⚠️ WARNING: Insufficient mounts. Displays: {display_count}, Mounts: {mount_count}")
        completeness_score -= 5
    else:
        completeness_score += 10
    
    scores["completeness"] = max(0, completeness_score)
    
    # 3. Price Reasonableness (15 points)
    price_score = 15
    
    for item in boq_items:
        if item['price'] == 0:
            price_score -= 3
            warnings.append(f"⚠️ WARNING: Zero price for {item['name']}")
        
        if item['price'] > 50000:
            warnings.append(f"ℹ️ High-value item: {item['name']} (${item['price']:,.2f})")
    
    scores["price_reasonableness"] = max(0, price_score)
    
    # 4. Brand Consistency (10 points)
    brands = [item.get('brand', 'Unknown') for item in boq_items]
    unique_brands = len(set(brands))
    
    if unique_brands <= 5:
        scores["brand_consistency"] = 10
        recommendations.append("✓ Good brand consolidation for simplified support")
    elif unique_brands <= 10:
        scores["brand_consistency"] = 7
    else:
        scores["brand_consistency"] = 4
        recommendations.append("Consider consolidating brands for easier support and compatibility")
    
    # 5. Specification Match (10 points)
    spec_score = 10
    
    # Check for specification mismatches
    for item in boq_items:
        if item.get('confidence_score', 1.0) < 0.7:
            spec_score -= 2
            warnings.append(f"Low confidence match: {item['name']}")
    
    scores["specification_match"] = max(0, spec_score)
    
    # 6. Integration Quality (10 points)
    integration_score = 10
    
    # Check for ecosystem compatibility
    control_brands = [item.get('brand') for item in boq_items if 'Control' in item['category']]
    vc_brands = [item.get('brand') for item in boq_items if 'Video Conferencing' in item['category']]
    
    if control_brands and vc_brands:
        # Check for known compatibility issues
        integration_score = 8  # Base score for having both systems
        recommendations.append("Verify control system integration with video conferencing platform")
    
    scores["integration_quality"] = integration_score
    
    # Calculate total score
    total_score = sum(scores.values())
    
    # Grade assignment
    if total_score >= 90:
        grade = "A - Excellent"
    elif total_score >= 80:
        grade = "B - Good"
    elif total_score >= 70:
        grade = "C - Acceptable"
    elif total_score >= 60:
        grade = "D - Needs Improvement"
    else:
        grade = "F - Major Issues"
    
    return {
        "total_score": total_score,
        "grade": grade,
        "category_scores": scores,
        "warnings": warnings,
        "recommendations": recommendations
    }
```

---

## 17. Documentation Standards (AVIXA D401.01:2023)

### As-Built Documentation Requirements

```python
def generate_asbuilt_documentation(project_data, boq_items, installation_notes):
    """
    Generate comprehensive as-built documentation per AVIXA D401.01:2023
    """
    
    documentation = {
        "project_identification": {
            "project_name": project_data['name'],
            "project_number": project_data.get('number', 'TBD'),
            "client_name": project_data['client'],
            "location": project_data['location'],
            "completion_date": project_data.get('completion_date'),
            "as_built_date": datetime.now().strftime("%Y-%m-%d")
        },
        
        "document_sections": {
            "architectural_drawings": {
                "floor_plans": "As-built floor plans showing final equipment locations",
                "reflected_ceiling_plans": "RCP showing ceiling-mounted equipment and cable pathways",
                "elevation_drawings": "Elevations showing display heights and rack configurations",
                "section_drawings": "Wall sections showing cable pathways and in-wall equipment"
            },
            
            "equipment_documentation": {
                "bill_of_materials": generate_final_bom(boq_items),
                "equipment_location_drawings": "Detailed equipment placement with coordinates",
                "equipment_rack_elevations": generate_rack_elevations(boq_items),
                "cutsheets": "Manufacturer cut sheets for all installed equipment"
            },
            
            "system_diagrams": {
                "block_diagrams": "System block diagrams showing signal flow",
                "wiring_diagrams": "Detailed wiring schematics for all connections",
                "network_diagrams": "Network topology showing VLANs and IP addressing",
                "control_logic": "Control system logic diagrams and flowcharts"
            },
            
            "cable_documentation": {
                "cable_schedule": generate_cable_schedule(boq_items),
                "home_run_drawings": "Cable pathways from equipment to terminations",
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
                "quick_reference_cards": "Laminated quick-start guides",
                "training_materials": "Training slides and video recordings",
                "troubleshooting_guides": "Common issues and resolutions"
            },
            
            "commissioning_records": {
                "verification_reports": "AVIXA 10:2013 verification test results",
                "punch_list": "Final punch list items and resolutions",
                "sign_off_documents": "Client acceptance and sign-off forms",
                "warranty_information": "Warranty terms and registration"
            }
        },
        
        "maintenance_requirements": {
            "preventive_maintenance": generate_maintenance_schedule(boq_items),
            "spare_parts_list": generate_spares_list(boq_items),
            "support_contacts": {
                "installer": project_data.get('installer_contact'),
                "manufacturer_support": "Equipment manufacturer support contacts",
                # Enhanced AV Design Guidelines for BOQ Generation (Continued)

```python
                "emergency_contacts": "24/7 emergency support contact information"
            }
        }
    }
    
    return documentation


def generate_cable_schedule(boq_items):
    """
    Generate comprehensive cable schedule per AVIXA CLAS standard
    """
    
    cable_schedule = []
    cable_id = 1
    
    # Audio cables
    audio_items = [item for item in boq_items if item['category'] == 'Audio']
    for item in audio_items:
        if 'Microphone' in item.get('sub_category', ''):
            for i in range(item['quantity']):
                cable_schedule.append({
                    "cable_id": f"AUD-MIC-{cable_id:03d}",
                    "cable_type": "XLR Balanced Audio",
                    "from_location": f"{item['name']} #{i+1}",
                    "to_location": "Audio DSP Input",
                    "length_ft": "TBD - measure during installation",
                    "pathway": "Ceiling plenum to equipment rack",
                    "cable_rating": "CMP (Plenum)",
                    "tested": "Yes",
                    "test_result": "Pass"
                })
                cable_id += 1
    
    # Video cables
    display_items = [item for item in boq_items if item['category'] == 'Displays']
    for i, display in enumerate(display_items, 1):
        cable_schedule.append({
            "cable_id": f"VID-DISP-{i:03d}",
            "cable_type": "HDMI 2.1 or HDBaseT Cat6A",
            "from_location": "Video Matrix / Source Switcher",
            "to_location": f"Display {i}",
            "length_ft": "TBD - measure during installation",
            "pathway": "In-wall conduit or cable tray",
            "cable_rating": "CL3 (In-wall)",
            "tested": "Yes",
            "test_result": "Pass"
        })
    
    # Network cables
    network_devices = [item for item in boq_items 
                      if any(cat in item['category'] for cat in ['Video Conferencing', 'Control Systems', 'Audio'])]
    for item in network_devices:
        cable_schedule.append({
            "cable_id": f"NET-{item['category'][:3].upper()}-{cable_id:03d}",
            "cable_type": "Cat6A Shielded",
            "from_location": f"{item['name']}",
            "to_location": "AV Network Switch",
            "length_ft": "TBD",
            "pathway": "Conduit or cable tray",
            "cable_rating": "CMP (Plenum)",
            "tested": "Yes",
            "test_result": "Pass - Certified to Cat6A specs"
        })
        cable_id += 1
    
    return cable_schedule


def generate_maintenance_schedule(boq_items):
    """
    Create preventive maintenance schedule for all equipment
    """
    
    maintenance_tasks = {
        "Monthly": [
            "Visual inspection of all equipment for physical damage",
            "Check all cable connections for secure attachment",
            "Verify display brightness and image quality",
            "Test video conferencing system with test call",
            "Clean display screens and camera lenses",
            "Check UPS battery status and runtime"
        ],
        "Quarterly": [
            "Clean equipment rack ventilation and fans",
            "Test all microphones and speakers",
            "Verify control system presets and macros",
            "Update firmware on network-connected devices",
            "Test fire alarm integration (coordinate with facilities)",
            "Review and update user documentation if needed"
        ],
        "Semi-Annual": [
            "Professional audio system calibration",
            "Video display calibration and uniformity check",
            "Deep clean of all equipment",
            "Verify all backup systems (UPS runtime test)",
            "Review system logs for errors or warnings",
            "Conduct full AVIXA 10:2013 verification tests"
        ],
        "Annual": [
            "Comprehensive system health check by certified technician",
            "Replace UPS batteries (per manufacturer schedule)",
            "Update all system firmware and software",
            "Review and renew service contracts",
            "Conduct user training refresher",
            "Update as-built documentation with any changes",
            "Review system performance vs. original specifications"
        ]
    }
    
    # Add equipment-specific tasks
    for item in boq_items:
        if 'Projector' in item.get('sub_category', ''):
            if "Lamp" not in maintenance_tasks["Annual"]:
                maintenance_tasks["Annual"].append(
                    f"Replace projector lamps (typically 2000-4000 hours)"
                )
        
        if 'Laser' in item.get('name', ''):
            if "Laser" not in str(maintenance_tasks["Annual"]):
                maintenance_tasks["Annual"].append(
                    "Inspect laser projector cooling system and filters"
                )
    
    return maintenance_tasks
```

---

## 18. Training & End-User Documentation

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
            "attendees": user_roles,
            "trainer_requirements": "AVIXA CTS certified technician preferred"
        },
        
        "training_modules": {}
    }
    
    # Module 1: Basic User Training (All Users)
    training_program["training_modules"]["basic_users"] = {
        "target_audience": "All room users, presenters, meeting participants",
        "duration": "1 hour",
        "topics": [
            {
                "topic": "System Power-On/Off",
                "duration": "10 min",
                "content": [
                    "Locating touch panel or control interface",
                    "Powering on the system",
                    "Selecting 'All Off' for shutdown",
                    "What to do if system doesn't respond"
                ]
            },
            {
                "topic": "Connecting Your Laptop",
                "duration": "15 min",
                "content": [
                    "USB-C connection (single cable for video + audio + charging)",
                    "HDMI connection for older laptops",
                    "Wireless presentation system usage",
                    "Troubleshooting: 'No Signal' issues"
                ]
            },
            {
                "topic": "Starting a Video Conference",
                "duration": "20 min",
                "content": [
                    "Using Teams/Zoom Rooms interface",
                    "Joining scheduled meetings (one-touch join)",
                    "Starting ad-hoc meetings",
                    "Sharing content during calls",
                    "Adjusting camera view and layout"
                ]
            },
            {
                "topic": "Audio Control",
                "duration": "10 min",
                "content": [
                    "Adjusting volume (speakers and microphones)",
                    "Muting microphones",
                    "Understanding microphone pickup zones",
                    "When to use wireless microphones (if available)"
                ]
            },
            {
                "topic": "Getting Help",
                "duration": "5 min",
                "content": [
                    "Using the 'Help' button on touch panel",
                    "Contacting IT/AV support",
                    "Quick troubleshooting guide location",
                    "Emergency contact information"
                ]
            }
        ],
        "hands_on_exercises": [
            "Each attendee connects their laptop and shares content",
            "Practice starting and ending a test video call",
            "Simulate common issues and resolutions"
        ],
        "materials_provided": [
            "Laminated quick-start guide",
            "QR code for digital user manual",
            "Support contact card"
        ]
    }
    
    # Module 2: Advanced User Training (Frequent Users)
    training_program["training_modules"]["advanced_users"] = {
        "target_audience": "Executive assistants, meeting coordinators, frequent presenters",
        "duration": "2 hours",
        "topics": [
            {
                "topic": "Advanced Source Management",
                "duration": "20 min",
                "content": [
                    "Switching between multiple sources",
                    "Picture-in-picture configurations",
                    "Using dual displays effectively",
                    "Managing content + video feed layouts"
                ]
            },
            {
                "topic": "Camera Control",
                "duration": "20 min",
                "content": [
                    "Manual camera positioning (PTZ control)",
                    "Saving and recalling camera presets",
                    "Adjusting zoom and focus",
                    "Understanding auto-framing vs. manual mode"
                ]
            },
            {
                "topic": "Audio Presets & Scenes",
                "duration": "15 min",
                "content": [
                    "Understanding audio presets (presentation, video call, training)",
                    "When to use each preset",
                    "Adjusting individual microphone levels",
                    "Background music control (if applicable)"
                ]
            },
            {
                "topic": "Environmental Controls",
                "duration": "15 min",
                "content": [
                    "Lighting scene control",
                    "Motorized shade operation",
                    "Creating custom environment presets",
                    "Integration with room scheduling"
                ]
            },
            {
                "topic": "Recording & Streaming",
                "duration": "20 min",
                "content": [
                    "Starting recording sessions",
                    "Streaming to corporate platforms",
                    "Managing recorded content",
                    "Privacy and compliance considerations"
                ]
            },
            {
                "topic": "Troubleshooting",
                "duration": "30 min",
                "content": [
                    "Identifying common issues",
                    "Using system diagnostics",
                    "Performing system restart",
                    "When to escalate to support"
                ]
            }
        ],
        "hands_on_exercises": [
            "Set up complex presentation scenarios",
            "Practice advanced camera control",
            "Simulate and resolve common problems"
        ]
    }
    
    # Module 3: Technical Staff Training
    training_program["training_modules"]["technical_staff"] = {
        "target_audience": "IT staff, AV technicians, facilities management",
        "duration": "4-6 hours",
        "topics": [
            {
                "topic": "System Architecture Overview",
                "duration": "45 min",
                "content": [
                    "Complete system block diagram walkthrough",
                    "Signal flow from sources to displays",
                    "Network topology and VLAN configuration",
                    "Control system architecture",
                    "Integration points with building systems"
                ]
            },
            {
                "topic": "Equipment Rack Tour",
                "duration": "30 min",
                "content": [
                    "Location and function of each device",
                    "Cable management and labeling system",
                    "Power distribution and UPS",
                    "Accessing equipment web interfaces",
                    "Understanding status LEDs and indicators"
                ]
            },
            {
                "topic": "Network Configuration",
                "duration": "45 min",
                "content": [
                    "IP addressing scheme",
                    "VLAN configuration and purpose",
                    "QoS settings for AV traffic",
                    "Firewall rules for video conferencing",
                    "Network monitoring and troubleshooting tools"
                ]
            },
            {
                "topic": "Audio System Configuration",
                "duration": "60 min",
                "content": [
                    "DSP configuration and routing",
                    "Microphone gain structure",
                    "Acoustic echo cancellation settings",
                    "Audio presets and scenes",
                    "Using audio measurement tools (SPL meter, RTA)"
                ]
            },
            {
                "topic": "Video System Configuration",
                "duration": "45 min",
                "content": [
                    "Display calibration and settings",
                    "Video matrix routing",
                    "EDID management",
                    "HDCP troubleshooting",
                    "Camera configuration and presets"
                ]
            },
            {
                "topic": "Control System Programming",
                "duration": "60 min",
                "content": [
                    "Accessing control processor",
                    "Understanding program logic",
                    "Modifying button functions (if authorized)",
                    "Adding devices to control system",
                    "Backup and restore procedures"
                ]
            },
            {
                "topic": "Preventive Maintenance",
                "duration": "30 min",
                "content": [
                    "Monthly maintenance checklist",
                    "Firmware update procedures",
                    "Log file review and monitoring",
                    "Performance trending",
                    "When to schedule professional service"
                ]
            },
            {
                "topic": "Advanced Troubleshooting",
                "duration": "60 min",
                "content": [
                    "Systematic troubleshooting methodology",
                    "Using built-in diagnostics",
                    "Signal path testing",
                    "Reading system logs",
                    "Remote access procedures",
                    "Escalation procedures and support contacts"
                ]
            }
        ],
        "hands_on_exercises": [
            "Navigate equipment web interfaces",
            "Make minor DSP adjustments",
            "Perform system restart sequence",
            "Troubleshoot simulated failures",
            "Access and interpret system logs"
        ],
        "certification": "Completion certificate for technical training"
    }
    
    # Training Materials
    training_program["deliverables"] = {
        "documentation": [
            "Complete system operation manual (PDF + printed)",
            "Quick-start guides (laminated, posted in room)",
            "Technical system documentation (for IT staff)",
            "Video tutorials for common tasks",
            "Online knowledge base access"
        ],
        "reference_materials": [
            "Equipment cut sheets and manuals",
            "As-built drawings and schematics",
            "Cable schedule and labeling guide",
            "IP address and device inventory",
            "Support contact list"
        ],
        "tools_provided": [
            "QR codes for instant access to digital manuals",
            "Mobile app for system control (if applicable)",
            "Access to online support portal"
        ]
    }
    
    # Post-Training Support
    training_program["ongoing_support"] = {
        "refresher_training": "Recommended annually or when staff turnover occurs",
        "office_hours": "Monthly office hours for Q&A",
        "on_demand_support": "Phone/email support during business hours",
        "emergency_support": "24/7 emergency support hotline",
        "knowledge_base": "Continuously updated online documentation"
    }
    
    return training_program
```

---

## 19. Final BOQ Assembly & Export

### Complete BOQ Package Generation

```python
def assemble_final_boq_package(project_data, rooms_data, avixa_calcs, quality_scores):
    """
    Assemble complete BOQ package ready for client presentation
    """
    
    boq_package = {
        # Executive Summary
        "executive_summary": {
            "project_name": project_data['project_name'],
            "client_name": project_data['client_name'],
            "prepared_by": project_data['design_engineer'],
            "date": datetime.now().strftime("%B %d, %Y"),
            "project_scope": generate_project_scope_summary(rooms_data),
            "total_investment": calculate_total_investment(rooms_data),
            "implementation_timeline": estimate_project_timeline(rooms_data),
            "key_benefits": [
                "AVIXA standards-compliant design for optimal performance",
                "Professional-grade equipment with commercial warranties",
                "Scalable architecture for future expansion",
                "Comprehensive training and documentation included",
                "24/7 technical support available"
            ]
        },
        
        # Room-by-Room Summary
        "room_summaries": [
            {
                "room_name": room['name'],
                "room_type": room['type'],
                "room_area": f"{room['area_sqft']} sq ft",
                "capacity": f"{room['capacity']} people",
                "equipment_count": len(room['boq_items']),
                "room_cost": calculate_room_cost(room['boq_items']),
                "key_features": extract_key_features(room['boq_items']),
                "avixa_compliance": avixa_calcs[room['name']],
                "quality_score": quality_scores[room['name']]
            }
            for room in rooms_data
        ],
        
        # Detailed BOQ (Multi-Room)
        "detailed_boq": rooms_data,
        
        # Financial Summary
        "financial_summary": {
            "hardware_total": sum(calculate_hardware_cost(room) for room in rooms_data),
            "installation_total": sum(calculate_installation_cost(room) for room in rooms_data),
            "programming_total": sum(calculate_programming_cost(room) for room in rooms_data),
            "project_management": sum(calculate_pm_cost(room) for room in rooms_data),
            "warranty_extended": sum(calculate_warranty_cost(room) for room in rooms_data),
            "subtotal_before_tax": 0,  # Calculated below
            "tax_sgst": 0,
            "tax_cgst": 0,
            "grand_total": 0
        },
        
        # Implementation Plan
        "implementation_plan": {
            "phase_1_design": {
                "duration": "2-3 weeks",
                "activities": [
                    "Final design review and approval",
                    "Detailed engineering drawings",
                    "Equipment procurement",
                    "Project kickoff meeting"
                ]
            },
            "phase_2_installation": {
                "duration": "4-6 weeks",
                "activities": [
                    "Cable infrastructure installation",
                    "Equipment mounting and installation",
                    "System integration and testing",
                    "Quality assurance checks"
                ]
            },
            "phase_3_commissioning": {
                "duration": "1-2 weeks",
                "activities": [
                    "AVIXA 10:2013 performance verification",
                    "System calibration and optimization",
                    "User acceptance testing",
                    "Documentation delivery"
                ]
            },
            "phase_4_training": {
                "duration": "1 week",
                "activities": [
                    "End-user training sessions",
                    "Technical staff training",
                    "Documentation handover",
                    "Go-live support"
                ]
            }
        },
        
        # Terms & Conditions
        "terms_conditions": {
            "payment_terms": "30% advance, 40% on installation completion, 30% on final acceptance",
            "warranty": "3 years comprehensive parts and labor warranty",
            "support": "1 year complimentary support included, extended plans available",
            "validity": "Proposal valid for 60 days from date of submission",
            "exclusions": [
                "Civil works, painting, and building modifications",
                "Electrical power circuits and conduit installation (coordination provided)",
                "Network backbone infrastructure (endpoint connections included)",
                "Furniture and architectural finishes",
                "Permits and regulatory approvals (support provided)"
            ],
            "assumptions": [
                "Client provides access to installation areas during working hours",
                "Electrical power and network infrastructure available per specifications",
                "Equipment rack location approved and accessible",
                "No asbestos or hazardous materials in work areas",
                "Building access for deliveries and equipment"
            ]
        },
        
        # Appendices
        "appendices": {
            "avixa_calculations": avixa_calcs,
            "verification_plan": generate_verification_checklist(project_data['room_type'], rooms_data[0]['boq_items']),
            "cable_schedule": generate_cable_schedule(rooms_data[0]['boq_items']),
            "equipment_cutsheets": "Available upon request",
            "references": [
                "AVIXA DISCAS - Display Image Size for 2D Content in Audiovisual Systems",
                "AVIXA A102.01:2017 - Audio Coverage Uniformity in Enclosed Listener Areas",
                "AVIXA 10:2013 - Audiovisual Systems Performance Verification",
                "AVIXA D401.01:2023 - Audiovisual Project Documentation Standard"
            ]
        }
    }
    
    # Calculate financial totals
    subtotal = (boq_package['financial_summary']['hardware_total'] +
                boq_package['financial_summary']['installation_total'] +
                boq_package['financial_summary']['programming_total'] +
                boq_package['financial_summary']['project_management'] +
                boq_package['financial_summary']['warranty_extended'])
    
    boq_package['financial_summary']['subtotal_before_tax'] = subtotal
    boq_package['financial_summary']['tax_sgst'] = subtotal * 0.09
    boq_package['financial_summary']['tax_cgst'] = subtotal * 0.09
    boq_package['financial_summary']['grand_total'] = subtotal * 1.18
    
    return boq_package
```

---

## 20. Summary & Best Practices

### BOQ Generator Design Checklist

```markdown
## Pre-Generation Checklist

- [ ] Room dimensions verified (length, width, ceiling height)
- [ ] Room type and primary function identified
- [ ] Occupancy/capacity determined
- [ ] Budget tier established
- [ ] Client preferences documented (brands, features, special requirements)
- [ ] Site survey completed (if applicable)
- [ ] Existing infrastructure assessed
- [ ] Power and network availability confirmed

## AVIXA Standards Compliance Checklist

- [ ] Display sizing calculated per DISCAS (viewing distance ÷ 6 or ÷ 4)
- [ ] Audio coverage verified per A102.01 (±3dB uniformity)
- [ ] Microphone coverage calculated (1 per 150 sq ft minimum)
- [ ] Speaker coverage calculated (1 per 200 sq ft minimum)
- [ ] Network bandwidth requirements calculated
- [ ] Power load calculated with 20% safety factor
- [ ] Verification plan created per AVIXA 10:2013

## Product Selection Validation

- [ ] All service contracts filtered out
- [ ] Video bar integration checked (no redundant audio)
- [ ] Display sizes within acceptable range
- [ ] Mount quantities match display quantities
- [ ] Price ranges validated per category
- [ ] Brand ecosystem compatibility verified
- [ ] AI justifications generated for all items
- [ ] Top 3 client-facing reasons provided

## Quality Assurance

- [ ] AVIXA compliance score ≥ 25/30
- [ ] Completeness score ≥ 20/25
- [ ] Price reasonableness verified
- [ ] No zero-price items
- [ ] All warnings reviewed and addressed
- [ ] Integration compatibility confirmed

## Documentation Completeness

- [ ] BOQ items with full specifications
- [ ] Product images generated
- [ ] Cable schedule created
- [ ] Verification checklist included
- [ ] Installation estimate provided
- [ ] Training program outlined
- [ ] Warranty information documented

## Excel Export Quality

- [ ] All sheets properly formatted
- [ ] Product images embedded correctly
- [ ] Top 3 reasons displayed in column Q
- [ ] Financial calculations accurate
- [ ] GST calculations correct (18% total: 9% SGST + 9% CGST)
- [ ] Company branding applied
- [ ] Professional appearance verified

## Pre-Delivery Review

- [ ] Client name and project details verified
- [ ] All room BOQs included
- [ ] Multi-room summary accurate
- [ ] Terms and conditions included
- [ ] Proposal validity date set
- [ ] Contact information current
- [ ] File naming convention followed
- [ ] PDF and Excel versions generated
```

### Common Pitfalls to Avoid

```python
COMMON_PITFALLS = {
    "Display Selection": [
        "❌ Selecting consumer TVs instead of commercial displays",
        "❌ Undersizing displays based on viewing distance",
        "❌ Missing mounts for displays",
        "❌ Not considering screen height from floor (ADA compliance)"
    ],
    
    "Audio System": [
        "❌ Using TV speakers for conference room audio (inadequate)",
        "❌ Insufficient microphone coverage",
        "❌ No DSP for echo cancellation in medium/large rooms",
        "❌ Incorrect speaker placement (coverage gaps)"
    ],
    
    "Video Conferencing": [
        "❌ Camera FOV too narrow for room size",
        "❌ Camera positioned incorrectly (too low/high)",
        "❌ No redundancy for critical systems",
        "❌ Inadequate network bandwidth"
    ],
    
    "Control Systems": [
        "❌ Overly complex interfaces for simple rooms",
        "❌ No control system for medium/large rooms",
        "❌ Touch panel mounted at wrong height",
        "❌ Missing integration with building systems"
    ],
    
    "Infrastructure": [
        "❌ Inadequate power circuits",
        "❌ No UPS for critical equipment",
        "❌ Poor cable management",
        "❌ Insufficient network switch ports"
    ],
    
    "Cost Estimation": [
        "❌ Forgetting installation labor",
        "❌ Not including programming time",
        "❌ Missing project management overhead",
        "❌ Unrealistic warranty/maintenance costs"
    ],
    
    "Documentation": [
        "❌ Missing AI justifications",
        "❌ Incomplete cable schedules",
        "❌ No verification plan",
        "❌ Missing as-built documentation requirements"
    ]
}
```

---


        "
