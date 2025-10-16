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
