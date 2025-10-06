# components/room_profiles.py

# This file is the single source of truth for all room specifications.
# MODIFICATION: This has been significantly enhanced to be the blueprint for the new profile-driven logic.
ROOM_SPECS = {
    'Small Huddle Room (2-3 People)': {
        'area_sqft': (100, 150), 'capacity': (2, 3), 'primary_use': 'Ad-hoc collaboration, quick calls',
        'typical_dims_ft': (12, 10),
        'preferred_ecosystem': 'Logitech',
        'components': {
            'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': 1},
            'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': 1},
            'video_bar': {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1},
        }
    },
    'Medium Huddle Room (4-6 People)': {
        'area_sqft': (150, 250), 'capacity': (4, 6), 'primary_use': 'Team meetings, brainstorming',
        'typical_dims_ft': (15, 12),
        'preferred_ecosystem': 'Poly',
        'components': {
            'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': 1},
            'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': 1},
            'video_bar': {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1},
            'controller': {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1},
        }
    },
    'Standard Conference Room (6-8 People)': {
        'area_sqft': (250, 400), 'capacity': (6, 8), 'primary_use': 'Formal meetings, presentations',
        'typical_dims_ft': (20, 15),
        'preferred_ecosystem': 'Poly',
        'components': {
            'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': 1},
            'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': 1},
            'video_bar': {'category': 'Video Conferencing', 'sub_category': 'Video Bar', 'quantity': 1},
            'controller': {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1},
            'mic_pod': {'category': 'Audio', 'sub_category': 'Table Microphone', 'quantity': 1, 'justification': 'Extension mic pod for better table coverage.'},
        }
    },
    'Large Conference Room (8-12 People)': {
        'area_sqft': (400, 600), 'capacity': (8, 12), 'primary_use': 'Client presentations, project reviews',
        'typical_dims_ft': (28, 20),
        'preferred_ecosystem': 'Cisco',
        'components': {
            'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': 1},
            'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': 1},
            'codec': {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1},
            'camera': {'category': 'Video Conferencing', 'sub_category': 'PTZ Camera', 'quantity': 1},
            'controller': {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1},
            'dsp': {'category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1},
            'microphone': {'category': 'Audio', 'sub_category': 'Ceiling Microphone', 'quantity': 2},
            'speakers': {'category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': 4},
            'amplifier': {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1},
            'connectivity': {'category': 'Cables & Connectivity', 'sub_category': 'Wall & Table Plate Module', 'quantity': 1},
            'rack': {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1},
            'pdu': {'category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'quantity': 1}
        }
    },
    'Executive Boardroom (10-16 People)': {
        'area_sqft': (600, 800), 'capacity': (10, 16), 'primary_use': 'High-stakes meetings, executive sessions',
        'typical_dims_ft': (35, 20),
        'preferred_ecosystem': 'Poly',
        'components': {
            'display': {'category': 'Displays', 'sub_category': 'Professional Display', 'quantity': 2, 'justification': 'Dual displays for content and video feeds.'},
            'display_mount': {'category': 'Mounts', 'sub_category': 'Display Mount / Cart', 'quantity': 2},
            'codec': {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1},
            'camera': {'category': 'Video Conferencing', 'sub_category': 'PTZ Camera', 'quantity': 1},
            'controller': {'category': 'Video Conferencing', 'sub_category': 'Touch Controller', 'quantity': 1},
            'dsp': {'category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1},
            'microphone': {'category': 'Audio', 'sub_category': 'Ceiling Microphone', 'quantity': 2},
            'speakers': {'category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': 4},
            'amplifier': {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1},
            'connectivity': {'category': 'Cables & Connectivity', 'sub_category': 'Wall & Table Plate Module', 'quantity': 1},
            'rack': {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1},
            'pdu': {'category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'quantity': 1}
        }
    },
    'Training Room (15-25 People)': {
        'area_sqft': (750, 1250), 'capacity': (15, 25), 'primary_use': 'Instruction, workshops',
        'typical_dims_ft': (40, 25),
        'preferred_ecosystem': 'Extron',
        'components': {
            'display': {'category': 'Displays', 'sub_category': 'Projector', 'quantity': 1, 'justification': 'Large format projection for visibility.'},
            'projector_screen': {'category': 'Displays', 'sub_category': 'Projector Screen', 'quantity': 1},
            'display_mount': {'category': 'Mounts', 'sub_category': 'Projector Mount', 'quantity': 1},
            'codec': {'category': 'Video Conferencing', 'sub_category': 'Room Kit / Codec', 'quantity': 1},
            'camera': {'category': 'Video Conferencing', 'sub_category': 'PTZ Camera', 'quantity': 2, 'justification': 'One camera for presenter, one for audience.'},
            'dsp': {'category': 'Audio', 'sub_category': 'DSP / Processor', 'quantity': 1, 'justification': 'For voice reinforcement and program audio.'},
            'presenter_mic': {'category': 'Audio', 'sub_category': 'Wireless Microphone System', 'quantity': 1},
            'audience_mic': {'category': 'Audio', 'sub_category': 'Ceiling Microphone', 'quantity': 4},
            'speakers': {'category': 'Audio', 'sub_category': 'Loudspeaker', 'quantity': 6},
            'amplifier': {'category': 'Audio', 'sub_category': 'Amplifier', 'quantity': 1},
            'wireless_presentation': {'category': 'Cables & Connectivity', 'sub_category': 'Wireless Presentation System', 'quantity': 1},
            'rack': {'category': 'Infrastructure', 'sub_category': 'AV Rack', 'quantity': 1},
            'pdu': {'category': 'Infrastructure', 'sub_category': 'Power (PDU/UPS)', 'quantity': 1}
        }
    }
}
