# components/room_profiles.py
# ENHANCED VERSION - Includes table/chair info and AVIXA compliance flags.

ROOM_SPECS = {
    'Small Huddle Room (2-3 People)': {
        'area_sqft': (100, 150),
        'capacity': (2, 3),
        'primary_use': 'Ad-hoc collaboration, quick calls',
        'typical_dims_ft': (12, 10),
        'table_size': [5, 3],
        'chair_count': 3,
        'chair_arrangement': 'conference',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,
            'type': 'Commercial 4K Display'
        },
        'audio_system': {
            'type': 'Integrated in Video Bar',
            'dsp_required': False,
            'microphone_count': 0,
            'speaker_count': 0
        },
        'video_system': {
            'type': 'All-in-one Video Bar',
            'camera_type': 'ePTZ 4K'
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'housing': {
            'type': 'Wall Mount Solution'
        }
    },
    'Medium Huddle Room (4-6 People)': {
        'area_sqft': (150, 250),
        'capacity': (4, 6),
        'primary_use': 'Team meetings, brainstorming',
        'typical_dims_ft': (15, 12),
        'table_size': [8, 4],
        'chair_count': 6,
        'chair_arrangement': 'conference',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,
            'type': 'Commercial 4K Display'
        },
        'audio_system': {
            'type': 'Integrated with optional Mic Pod',
            'dsp_required': True,
            'microphone_type': 'Table Microphone',
            'microphone_count': 1,
            'speaker_count': 0
        },
        'video_system': {
            'type': 'All-in-one Video Bar',
            'camera_type': 'ePTZ 4K with Autoframing'
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'housing': {
            'type': 'Wall Mount Solution'
        }
    },
    'Standard Conference Room (6-8 People)': {
        'area_sqft': (250, 400),
        'capacity': (6, 8),
        'primary_use': 'Formal meetings, presentations',
        'typical_dims_ft': (20, 15),
        'table_size': [14, 4],
        'chair_count': 8,
        'chair_arrangement': 'conference',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,
            'type': 'Commercial 4K Display'
        },
        'audio_system': {
            'type': 'Dedicated Mics & DSP',
            'dsp_required': True,
            'microphone_type': 'Table Microphone',
            'speaker_type': 'Integrated in Video Bar',
            'microphone_count': 2,
            'speaker_count': 0
        },
        'video_system': {
            'type': 'All-in-one Video Bar',
            'camera_type': 'Optical Zoom PTZ'
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'housing': {
            'type': 'Wall Mount or Credenza'
        }
    },
    'Large Conference Room (8-12 People)': {
        'area_sqft': (400, 600),
        'capacity': (8, 12),
        'primary_use': 'Client presentations, project reviews',
        'typical_dims_ft': (28, 20),
        'table_size': [18, 5],
        'chair_count': 12,
        'chair_arrangement': 'conference',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,
            'type': 'Commercial 4K Display'
        },
        'audio_system': {
            'type': 'Integrated Ceiling Audio',
            'dsp_required': True,
            'microphone_type': 'Ceiling Microphone',
            'speaker_type': 'Ceiling Loudspeaker',
            'microphone_count': 3,
            'speaker_count': 4
        },
        'video_system': {
            'type': 'Modular Codec + PTZ Camera',
            'camera_type': 'High-Performance Optical Zoom PTZ',
            'camera_count': 1
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'housing': {
            'type': 'AV Rack'
        },
        'power_management': {
            'type': 'Rackmount PDU'
        }
    },
    'Executive Boardroom (10-16 People)': {
        'area_sqft': (600, 800),
        'capacity': (10, 16),
        'primary_use': 'High-stakes meetings, executive sessions',
        'typical_dims_ft': (35, 20),
        'table_size': [24, 6],
        'chair_count': 16,
        'chair_arrangement': 'conference',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.70,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 2,
            'type': 'Premium Commercial 4K Display'
        },
        'audio_system': {
            'type': 'Fully Integrated Pro Audio',
            'dsp_required': True,
            'microphone_type': 'Ceiling Microphone',
            'speaker_type': 'Ceiling Loudspeaker',
            'microphone_count': 4,
            'speaker_count': 6
        },
        'video_system': {
            'type': 'Modular Codec + PTZ Camera',
            'camera_type': 'High-Performance Optical Zoom PTZ',
            'camera_count': 1
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'content_sharing': {
            'type': 'Wireless & Wired HDMI'
        },
        'housing': {
            'type': 'AV Rack'
        },
        'power_management': {
            'type': 'Rackmount PDU'
        }
    },
    'Training Room (15-25 People)': {
        'area_sqft': (750, 1250),
        'capacity': (15, 25),
        'primary_use': 'Instruction, workshops',
        'typical_dims_ft': (40, 25),
        'table_size': [6, 2], # Representative size for individual tables
        'chair_count': 25,
        'chair_arrangement': 'classroom',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 2,
            'type': 'Commercial 4K Display'
        },
        'audio_system': {
            'type': 'Voice Reinforcement System',
            'dsp_required': True,
            'microphone_type': 'Ceiling Microphone',
            'speaker_type': 'Ceiling Loudspeaker',
            'microphone_count': 5,
            'speaker_count': 8
        },
        'video_system': {
            'type': 'Modular Codec + PTZ Camera',
            'camera_type': 'Dual PTZ Cameras (Presenter/Audience)',
            'camera_count': 2
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'content_sharing': {
            'type': 'Wireless Presentation System'
        },
        'housing': {
            'type': 'AV Rack'
        },
        'power_management': {
            'type': 'Rackmount PDU'
        }
    },
    'Large Training/Presentation Room (25-40 People)': {
        'area_sqft': (1250, 2000),
        'capacity': (25, 40),
        'primary_use': 'Lectures, seminars',
        'typical_dims_ft': (50, 35),
        'table_size': [6, 2], # Representative size for individual tables
        'chair_count': 40,
        'chair_arrangement': 'classroom',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,
            'type': 'Projector and Screen'
        },
        'audio_system': {
            'type': 'Voice Reinforcement System',
            'dsp_required': True,
            'microphone_type': 'Ceiling Microphone',
            'speaker_type': 'Ceiling Loudspeaker',
            'microphone_count': 6,
            'speaker_count': 10
        },
        'video_system': {
            'type': 'Modular Codec + PTZ Camera',
            'camera_type': 'Dual PTZ Cameras (Presenter/Audience)',
            'camera_count': 2
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'content_sharing': {
            'type': 'Wireless Presentation System'
        },
        'housing': {
            'type': 'AV Rack'
        },
        'power_management': {
            'type': 'Rackmount PDU'
        }
    },
    'Multipurpose Event Room (40+ People)': {
        'area_sqft': (2000, 4000),
        'capacity': (40, 100),
        'primary_use': 'Town halls, large events',
        'typical_dims_ft': (60, 40),
        'table_size': None,
        'chair_count': 100,
        'chair_arrangement': 'theater',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,
            'type': 'Large Projector or Direct-View LED'
        },
        'audio_system': {
            'type': 'Full PA System with Mixer',
            'dsp_required': True,
            'microphone_type': 'Wireless Handheld/Lapel',
            'speaker_type': 'Wall-mounted Loudspeaker',
            'microphone_count': 4,
            'speaker_count': 12
        },
        'video_system': {
            'type': 'Presentation Switcher with VC Add-on',
            'camera_type': 'Multiple PTZ Cameras for Event Coverage',
            'camera_count': 2
        },
        'control_system': {
            'type': 'Touch Controller'
        },
        'housing': {
            'type': 'AV Rack'
        },
        'power_management': {
            'type': 'Rackmount PDU'
        }
    },
    'Video Production Studio': {
        'area_sqft': (500, 1500),
        'capacity': (3, 10),
        'primary_use': 'Content creation, recording',
        'typical_dims_ft': (40, 25),
        'table_size': None,
        'chair_count': 5,
        'chair_arrangement': 'studio',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.70,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 3,
            'type': 'Reference Monitors & Multiviewer'
        },
        'audio_system': {
            'type': 'Studio Mixing Console',
            'dsp_required': True,
            'microphone_type': 'Studio Condenser Mics',
            'microphone_count': 6,
            'speaker_count': 4
        },
        'video_system': {
            'type': 'Production Switcher',
            'camera_type': 'Studio Cameras',
            'camera_count': 3
        },
        'control_system': {
            'type': 'Production Control Surface'
        },
        'specialized': [
            'Studio Lighting Grid',
            'Recording Decks',
            'Acoustic Treatment'
        ],
        'housing': {
            'type': 'AV Rack'
        },
        'power_management': {
            'type': 'Rackmount PDU'
        }
    },
    'Telepresence Suite': {
        'area_sqft': (400, 800),
        'capacity': (6, 12),
        'primary_use': 'Immersive video conferencing',
        'typical_dims_ft': (30, 20),
        'table_size': [20, 8], # Based on custom furniture
        'chair_count': 12,
        'chair_arrangement': 'conference',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.70,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 3,
            'type': 'Vendor-Specific Immersive Displays'
        },
        'audio_system': {
            'type': 'Tuned Immersive Audio',
            'dsp_required': True,
            'microphone_type': 'Integrated Array',
            'microphone_count': 8,
            'speaker_count': 8
        },
        'video_system': {
            'type': 'Dedicated Immersive Telepresence Codec',
            'camera_type': 'Multi-camera Array'
        },
        'control_system': {
            'type': 'Integrated Touch Controller'
        },
        'specialized': [
            'Custom Furniture',
            'Controlled Lighting'
        ],
        'housing': {
            'type': 'Integrated into Room Architecture'
        }
    }
}

# Newly added, more specialized room profiles
EXTENDED_ROOM_SPECS = {
    'Amphitheater / Lecture Hall (100-300 People)': {
        'area_sqft': (2500, 8000),
        'capacity': (100, 300),
        'primary_use': 'Large-scale presentations, lectures, keynotes',
        'typical_dims_ft': (80, 60),
        'table_size': None,
        'chair_count': 250,
        'chair_arrangement': 'theater',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.65,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,
            'type': 'Large Projector or LED Wall',
            'size_inches': 150  # Diagonal for projection
        },
        'audio_system': {
            'type': 'Line Array Speaker System',
            'dsp_required': True,
            'microphone_type': 'Wireless Handheld + Lapel',
            'speaker_type': 'Line Array + Delay Speakers',
            'microphone_count': 4,
            'speaker_count': 6  # Main arrays + delays
        },
        'video_system': {
            'type': 'Multi-Camera Broadcast System',
            'camera_type': 'Broadcast PTZ Cameras',
            'camera_count': 3
        },
        'control_system': {
            'type': 'Advanced Control Processor',
            'features': ['Lighting scenes', 'Multi-zone audio', 'Recording control']
        },
        'specialized': [
            'Recording/Streaming System',
            'Confidence Monitors',
            'Assistive Listening (ADA)',
            'Stage Lighting Integration'
        ],
        'housing': {
            'type': 'Technical Booth + Main Equipment Room'
        },
        'power_management': {
            'type': 'Dedicated Power Distribution + UPS'
        }
    },

    'Divisible Training Room (2x20 People)': {
        'area_sqft': (1000, 1800),
        'capacity': (40, 60),
        'capacity_per_section': (20, 30),
        'primary_use': 'Training that can split into two independent spaces',
        'typical_dims_ft': (50, 30),
        'table_size': [6, 2],  # Per individual table
        'chair_count': 40,
        'chair_arrangement': 'classroom',
        'divisible': True,
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.60,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 2,  # One per section
            'type': 'Commercial 4K Display',
            'size_inches': 75
        },
        'audio_system': {
            'type': 'Zoned Audio with Auto-Switching',
            'dsp_required': True,
            'microphone_type': 'Ceiling Microphone',
            'speaker_type': 'Ceiling Loudspeaker in Zones',
            'microphone_count': 6,  # 3 per zone
            'speaker_count': 10,  # 5 per zone
            'partition_sensing': True
        },
        'video_system': {
            'type': 'Dual Independent VC Systems',
            'camera_type': 'PTZ Camera per section',
            'camera_count': 2
        },
        'control_system': {
            'type': 'Advanced Control with Partition Logic',
            'features': ['Auto room combining', 'Zone control', 'Partition sensor']
        },
        'specialized': [
            'Motorized Partition Wall Sensor',
            'Dual-Mode Audio Routing',
            'Independent or Combined Room Modes'
        ],
        'housing': {
            'type': 'Central Equipment Room'
        }
    },

    'Corporate Lobby with Digital Signage': {
        'area_sqft': (800, 3000),
        'capacity': (0, 50),  # Transient traffic
        'primary_use': 'Visitor reception, brand messaging, wayfinding',
        'typical_dims_ft': (60, 40),
        'table_size': None,
        'chair_count': 10,
        'chair_arrangement': 'lounge',
        'avixa_requirements': {
            'display_sizing_method': 'Passive Viewing',
            'audio_standard': 'Background Music',
            'target_sti': 0.50,
            'requires_performance_verification': False
        },
        'displays': {
            'quantity': 3,  # Video wall or distributed displays
            'type': 'Video Wall or Large Format Displays',
            'configuration': 'Video Wall 2x2 or standalone 85"+'
        },
        'audio_system': {
            'type': 'Background Music System',
            'dsp_required': False,
            'speaker_type': 'Ceiling Loudspeaker',
            'speaker_count': 8
        },
        'digital_signage': {
            'type': 'Content Management System',
            'players': 3,
            'scheduling': True
        },
        'control_system': {
            'type': 'Automated Scheduling System',
            'features': ['Dayparting', 'Remote content update']
        },
        'specialized': [
            'Room Scheduling Panels (3x)',
            'Directory/Wayfinding Display',
            'Corporate Branding Integration'
        ],
        'housing': {
            'type': 'IDF Closet or Small Equipment Room'
        }
    },

    'Control Room / Network Operations Center': {
        'area_sqft': (600, 1500),
        'capacity': (6, 20),
        'primary_use': '24/7 monitoring, command & control operations',
        'typical_dims_ft': (40, 30),
        'table_size': [8, 3],  # Large operator consoles
        'chair_count': 12,
        'chair_arrangement': 'control console',
        'avixa_requirements': {
            'display_sizing_method': 'ADM - Analytical Decision Making',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.75,  # Critical communications
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 1,  # Main video wall
            'type': 'Video Wall 3x3 or larger',
            'operator_displays': 24  # 2 per operator
        },
        'audio_system': {
            'type': 'Intercom + PA System',
            'dsp_required': True,
            'microphone_type': 'Gooseneck + Headsets',
            'speaker_type': 'Ceiling Loudspeaker',
            'microphone_count': 12,
            'speaker_count': 6,
            'intercom_system': True
        },
        'video_system': {
            'type': 'Multi-Input Video Wall Processor',
            'inputs': 32,
            'multiviewer': True
        },
        'control_system': {
            'type': 'Enterprise Control Processor',
            'features': ['Preset layouts', 'Emergency override', 'Monitoring']
        },
        'specialized': [
            'Redundant Power (Dual UPS)',
            'KVM Switching System',
            '24/7 Environmental Monitoring',
            'Backup Failover System'
        ],
        'housing': {
            'type': 'Multiple Equipment Racks in Separate Room'
        }
    },

    'Worship Space (200-500 People)': {
        'area_sqft': (4000, 10000),
        'capacity': (200, 500),
        'primary_use': 'Religious services, worship, community gatherings',
        'typical_dims_ft': (100, 60),
        'table_size': None,
        'chair_count': 400,
        'chair_arrangement': 'theater',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.70,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 2,  # Main + Confidence
            'type': 'Large LED Wall or Projector',
            'main_display': 'LED Wall 12ft wide',
            'confidence_displays': 2
        },
        'audio_system': {
            'type': 'Distributed PA System',
            'dsp_required': True,
            'microphone_type': 'Wireless Lavalier + Handheld',
            'speaker_type': 'Line Array + Distributed Fill',
            'microphone_count': 6,
            'speaker_count': 12
        },
        'video_system': {
            'type': 'Multi-Camera Broadcast',
            'camera_type': 'Robotic PTZ + Static Wide',
            'camera_count': 4
        },
        'control_system': {
            'type': 'Advanced Production Control',
            'features': ['Camera presets', 'Lighting scenes', 'Recording']
        },
        'specialized': [
            'Live Streaming System',
            'Recording/Archiving',
            'Assistive Listening (Hearing Loop)',
            'Stage Lighting Control',
            'Confidence Monitors for Worship Leaders'
        ],
        'housing': {
            'type': 'Production Control Room + Equipment Racks'
        }
    },

    'Medical Simulation Lab (12-20 People)': {
        'area_sqft': (600, 1200),
        'capacity': (12, 20),
        'primary_use': 'Medical training, simulation, debrief',
        'typical_dims_ft': (40, 25),
        'table_size': [10, 4],
        'chair_count': 20,
        'chair_arrangement': 'classroom',
        'avixa_requirements': {
            'display_sizing_method': 'ADM - Critical Detail',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.70,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 3,
            'type': '4K Medical-Grade Displays',
            'size_inches': 65
        },
        'audio_system': {
            'type': 'Recording-Grade Audio',
            'dsp_required': True,
            'microphone_type': 'Ceiling Array + Lapel',
            'speaker_type': 'Ceiling Loudspeaker',
            'microphone_count': 4,
            'speaker_count': 6
        },
        'video_system': {
            'type': 'Multi-Camera Recording System',
            'camera_type': 'PTZ + Dome Cameras',
            'camera_count': 4  # Multiple angles
        },
        'control_system': {
            'type': 'Advanced Control with Recording Integration'
        },
        'specialized': [
            'Recording/Debrief System',
            'Multi-Angle Video Recording',
            'Annotation Capability',
            'Medical Equipment Integration',
            'One-Way Glass Observation Window Support'
        ],
        'housing': {
            'type': 'Observation/Control Room Adjacent'
        }
    },

    'Executive Briefing Center (20-30 People)': {
        'area_sqft': (800, 1200),
        'capacity': (20, 30),
        'primary_use': 'High-level presentations, investor briefings, board meetings',
        'typical_dims_ft': (40, 30),
        'table_size': [20, 6],
        'chair_count': 30,
        'chair_arrangement': 'conference',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.75,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 3,
            'type': 'Premium 4K Displays or LED Wall',
            'size_inches': 98,
            'main_display': 'Video Wall or 98" displays'
        },
        'audio_system': {
            'type': 'Premium Audio with Zone Control',
            'dsp_required': True,
            'microphone_type': 'Steerable Array + Lapel',
            'speaker_type': 'Premium Ceiling Loudspeaker',
            'microphone_count': 4,
            'speaker_count': 8
        },
        'video_system': {
            'type': 'Dual-Platform VC + Presentation',
            'camera_type': 'High-End PTZ with Tracking',
            'camera_count': 2
        },
        'control_system': {
            'type': 'Custom Programmable Control',
            'features': ['Lighting integration', 'Shades', 'HVAC preset']
        },
        'specialized': [
            'Recording Capability',
            'Confidence Monitors',
            'Wireless Presentation (Enterprise)',
            'Integrated Lighting Control',
            'Motorized Shades'
        ],
        'housing': {
            'type': 'Premium Built-In Credenza + Equipment Room'
        }
    },

    'Virtual Production Studio (Small-Medium)': {
        'area_sqft': (1000, 2500),
        'capacity': (5, 15),
        'primary_use': 'Video production, streaming, content creation',
        'typical_dims_ft': (50, 40),
        'table_size': None,
        'chair_count': 8,
        'chair_arrangement': 'production',
        'avixa_requirements': {
            'display_sizing_method': 'Broadcast Reference',
            'audio_standard': 'Broadcast Audio',
            'target_sti': 0.80,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 6,
            'type': 'Broadcast Reference Monitors + LED Wall',
            'led_wall': 'Virtual Production LED 12ft x 8ft',
            'reference_monitors': 4
        },
        'audio_system': {
            'type': 'Broadcast Audio System',
            'dsp_required': True,
            'microphone_type': 'Studio Condenser + Lapel',
            'speaker_type': 'Studio Monitors',
            'microphone_count': 6,
            'speaker_count': 4
        },
        'video_system': {
            'type': 'Broadcast Production System',
            'camera_type': 'Broadcast Studio Cameras',
            'camera_count': 3,
            'video_switcher': True
        },
        'control_system': {
            'type': 'Production Control Surface'
        },
        'specialized': [
            'LED Virtual Background Wall',
            'Camera Tracking System',
            'Chroma Key Lighting',
            'Multi-Track Recording',
            'Live Streaming Encoder',
            'Teleprompter System'
        ],
        'housing': {
            'type': 'Production Control Room + Equipment Racks'
        }
    },

    'Call Center Training Room (30-40 People)': {
        'area_sqft': (1200, 1800),
        'capacity': (30, 40),
        'primary_use': 'Call center training, customer service practice',
        'typical_dims_ft': (50, 30),
        'table_size': [4, 2],  # Individual workstations
        'chair_count': 40,
        'chair_arrangement': 'classroom',
        'avixa_requirements': {
            'display_sizing_method': 'DISCAS',
            'audio_standard': 'A102.01:2017',
            'target_sti': 0.65,
            'requires_performance_verification': True
        },
        'displays': {
            'quantity': 2,
            'type': 'Commercial 4K Display',
            'size_inches': 85,
            'individual_monitors': 40  # One per station
        },
        'audio_system': {
            'type': 'Zoned Audio with Headset Support',
            'dsp_required': True,
            'microphone_type': 'Ceiling Microphone',
            'speaker_type': 'Ceiling Loudspeaker in Zones',
            'microphone_count': 6,
            'speaker_count': 12,
            'headset_infrastructure': True
        },
        'video_system': {
            'type': 'VC System + Screen Recording',
            'camera_type': 'PTZ Camera',
            'camera_count': 2
        },
        'control_system': {
            'type': 'Standard Control with Zone Management'
        },
        'specialized': [
            'Individual Workstation Monitors (40x)',
            'Headset Jacks at Each Station',
            'Call Recording System',
            'Screen Sharing for Trainer',
            'Individual Audio Zones'
        ],
        'housing': {
            'type': 'Equipment Room + Wall-Mount Rack'
        }
    }
}

def get_all_room_specs():
    """
    Returns combined dictionary of standard + extended room profiles.
    """
    # This function is now self-contained and does not need a separate import
    # of ROOM_SPECS from the same file.
    combined_specs = ROOM_SPECS.copy()
    combined_specs.update(EXTENDED_ROOM_SPECS)
    
    return combined_specs
