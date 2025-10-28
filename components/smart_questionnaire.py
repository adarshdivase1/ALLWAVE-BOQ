# components/smart_questionnaire_v2.py
"""
Enhanced Smart BOQ Questionnaire System - ACIM Integration Phase 1
Combines existing questionnaire with ACIM form's detailed room-specific questions
"""

import streamlit as st
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import json

@dataclass
class ClientRequirements:
    """Enhanced structured client requirements"""
    # EXISTING FIELDS (preserved for backward compatibility)
    project_type: str
    room_count: int
    primary_use_case: str
    budget_level: str
    
    # Display Preferences
    display_brand_preference: str
    display_size_preference: str
    dual_display_needed: bool
    interactive_display_needed: bool
    
    # Video Conferencing
    vc_platform: str
    vc_brand_preference: str
    camera_type_preference: str
    auto_tracking_needed: bool
    
    # Audio System
    audio_brand_preference: str
    microphone_type: str
    ceiling_vs_table_audio: str
    voice_reinforcement_needed: bool
    
    # Control & Integration
    control_brand_preference: str
    wireless_presentation_needed: bool
    room_scheduling_needed: bool
    lighting_control_integration: bool
    
    # Infrastructure
    existing_network_capable: bool
    power_infrastructure_adequate: bool
    cable_management_type: str
    
    # Compliance & Special Requirements
    ada_compliance_required: bool
    recording_capability_needed: bool
    streaming_capability_needed: bool
    
    # Advanced Requirements
    additional_requirements: str
    
    # AVIXA-specific requirements
    avixa_display_sizing: str = "AVIXA DISCAS Recommended (Optimal viewing)"
    performance_verification_required: bool = False
    target_sti_level: str = "Standard (STI ≥ 0.60)"
    
    # NEW FIELDS - ACIM Integration Phase 1
    room_type_acim: str = ""  # Specific ACIM room type
    detailed_room_dimensions: str = ""  # Detailed dimensions with layout
    solution_type: str = ""  # AV only or AV + Video Collaboration
    connectivity_requirements: str = ""  # Detailed connectivity needs
    digital_whiteboard_needed: bool = False
    automation_scope: str = ""  # What should be automated
    supporting_documents: List = None  # Floor plans, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def get_brand_preferences(self) -> Dict[str, str]:
        """Extract brand preferences for product selection"""
        return {
            'displays': self.display_brand_preference,
            'video_conferencing': self.vc_brand_preference,
            'audio': self.audio_brand_preference,
            'control': self.control_brand_preference
        }


class EnhancedSmartQuestionnaire:
    """
    Enhanced questionnaire with ACIM form integration
    Phase 1: Add room type selection and detailed questions
    """
    
    def __init__(self):
        self.questions = self._build_enhanced_question_tree()
        self.responses = {}
        
        # ACIM room types mapping
        self.acim_room_types = {
            "Conference/Meeting Room/Boardroom": "conference_boardroom",
            "Experience Center": "experience_center",
            "Reception/Digital Signage": "reception_signage",
            "Training Room": "training_room",
            "Network Operations Center/Command Center": "noc_command",
            "Town Hall": "town_hall",
            "Auditorium": "auditorium"
        }
    
    def _get_acim_detailed_questions(self, room_type: str) -> List[Dict]:
        """
        Get detailed ACIM questions for specific room type
        Phase 2: Room-specific detailed questions
        """
        
        # Conference/Meeting Room/Boardroom Questions
        if room_type == "Conference/Meeting Room/Boardroom":
            return [
                {
                    'id': 'acim_seating_layout',
                    'question': '1. What is the seating capacity, layout (e.g., square table, U-shaped table, theater style), and detailed dimensions of the room, including its length, breadth, and height?',
                    'type': 'text_area',
                    'placeholder': 'Example: 12 people, rectangular table, 28ft x 20ft x 10ft height',
                    'help': 'Be as specific as possible about room layout and dimensions'
                },
                {
                    'id': 'acim_solution_type',
                    'question': '2. Would you require an AV (Audio Visual) Solution for only Presentations or Video Collaboration (Teams/Zoom) as well?',
                    'type': 'select',
                    'options': [
                        'Presentations Only',
                        'Video Collaboration Only',
                        'Both Presentations and Video Collaboration'
                    ],
                    'help': 'This determines if we need video conferencing equipment'
                },
                {
                    'id': 'acim_uc_platform',
                    'question': '3. Which UC platform does your organization currently use?',
                    'type': 'select',
                    'options': [
                        'Microsoft Teams',
                        'Zoom',
                        'Google Meet',
                        'Cisco Webex',
                        'GoToMeeting',
                        'Other'
                    ],
                    'help': 'We will ensure compatibility with your UC platform'
                },
                {
                    'id': 'acim_native_solution',
                    'question': '4. Would you require a Native Solution for simplified one-touch dialing via a touch panel mounted on the desk, or would you prefer to connect your laptop and use the meeting room\'s camera?',
                    'type': 'select',
                    'options': [
                        'Native Solution (One-touch dialing with touch panel)',
                        'BYOD (Bring Your Own Device - connect laptop)',
                        'Both options needed'
                    ],
                    'help': 'Native solution provides easier user experience'
                },
                {
                    'id': 'acim_connectivity',
                    'question': '5. Do you require wired (e.g., HDMI) or wireless connectivity, and would you also need USB-C as an option?',
                    'type': 'multiselect',
                    'options': [
                        'HDMI wired',
                        'USB-C',
                        'Wireless presentation',
                        'All of the above'
                    ],
                    'help': 'Multiple connectivity options provide flexibility'
                },
                {
                    'id': 'acim_digital_whiteboard',
                    'question': '6. Would you like a digital whiteboard with streaming capabilities, such as Kaptivo or Logitech Scribe, for collaboration?',
                    'type': 'boolean',
                    'default': False,
                    'help': 'Digital whiteboards enable remote participants to see whiteboard content'
                },
                {
                    'id': 'acim_automation',
                    'question': '7. Do you want room automation for controlling AV systems, lighting, air conditioning, and blinds?',
                    'type': 'text_area',
                    'placeholder': 'Specify which systems should be automated and how',
                    'help': 'Automation enhances user experience but adds complexity'
                },
                {
                    'id': 'acim_room_scheduler',
                    'question': '8. Would you require a room scheduler outside the room that integrates with platforms like Microsoft 365 or Gmail?',
                    'type': 'boolean',
                    'default': False,
                    'help': 'Room schedulers show availability and meeting details'
                },
                {
                    'id': 'acim_virtual_demo',
                    'question': '9. Would you be interested in scheduling a virtual demo to experience our AV solutions?',
                    'type': 'boolean',
                    'default': False,
                    'help': 'We can arrange a virtual demonstration of recommended solutions'
                },
                {
                    'id': 'acim_acoustic_solutions',
                    'question': '10. Would you like more information about acoustic solutions to enhance the AV and video collaboration experience?',
                    'type': 'boolean',
                    'default': False,
                    'help': 'Acoustic treatment can significantly improve audio quality'
                },
                {
                    'id': 'acim_budget',
                    'question': '11. What is your budget range for this project?',
                    'type': 'select',
                    'options': [
                        'Under $10,000',
                        '$10,000 - $25,000',
                        '$25,000 - $50,000',
                        '$50,000 - $100,000',
                        'Over $100,000',
                        'To be discussed'
                    ],
                    'help': 'Budget helps us recommend appropriate solutions'
                }
            ]
        
        # Training Room Questions
        elif room_type == "Training Room":
            return [
                {
                    'id': 'acim_room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Example: 40ft x 25ft x 12ft height, columns at center, drop ceiling',
                    'help': 'Architectural features affect equipment placement'
                },
                {
                    'id': 'acim_seating_info',
                    'question': '2. How many seats are there in the room, and what is the seating orientation towards the trainer? (e.g., classroom, theater, U-shaped)',
                    'type': 'text_area',
                    'placeholder': 'Example: 25 seats, classroom style, 5 rows of 5 seats',
                    'help': 'Seating arrangement affects camera and audio placement'
                },
                {
                    'id': 'acim_connectivity',
                    'question': '3. Are you looking for wired and wireless connectivity from both the podium and the overall seating area?',
                    'type': 'select',
                    'options': [
                        'Podium only',
                        'Seating area only',
                        'Both podium and seating area',
                        'Wireless throughout'
                    ],
                    'help': 'Multiple connection points increase flexibility'
                },
                {
                    'id': 'acim_remote_training',
                    'question': '4. Will this training room be used for remote training via platforms like Microsoft Teams, Zoom, WebEx, GoToMeeting, etc.?',
                    'type': 'boolean',
                    'default': True,
                    'help': 'Remote training requires video conferencing equipment'
                },
                {
                    'id': 'acim_camera_requirements',
                    'question': '5. Based on the size of the room, would you require a single camera to capture the trainer, or would you need multiple cameras to capture the trainer and the audience?',
                    'type': 'select',
                    'options': [
                        'Single camera (trainer only)',
                        'Dual cameras (trainer + audience)',
                        'Multi-camera (full coverage)'
                    ],
                    'help': 'Multiple cameras provide better remote experience'
                },
                {
                    'id': 'acim_camera_features',
                    'question': '6. If multiple cameras are required, would you like features such as speech tracking and auto-focus based on predefined presets?',
                    'type': 'boolean',
                    'default': False,
                    'help': 'Smart tracking keeps remote participants engaged'
                },
                {
                    'id': 'acim_digital_whiteboard',
                    'question': '7. Would you require a digital whiteboard collaboration tool with streaming options, such as Kaptivo or Logitech Scribe?',
                    'type': 'boolean',
                    'default': False
                },
                {
                    'id': 'acim_automation',
                    'question': '8. Would you need automation in the room for controlling Audio Visual equipment, lights, air conditioning, blinds, etc.?',
                    'type': 'text_area',
                    'placeholder': 'Specify automation requirements'
                },
                {
                    'id': 'acim_budget',
                    'question': '9. What is your budget range for this project?',
                    'type': 'select',
                    'options': [
                        'Under $25,000',
                        '$25,000 - $50,000',
                        '$50,000 - $75,000',
                        '$75,000 - $100,000',
                        'Over $100,000',
                        'To be discussed'
                    ]
                },
                {
                    'id': 'acim_live_streaming',
                    'question': '10. Would you need live streaming or corporate broadcasting for distance learning on platforms like corporate networks, YouTube Live, or Facebook Live?',
                    'type': 'boolean',
                    'default': False,
                    'help': 'Live streaming requires additional encoding equipment'
                }
            ]
        
        # Experience Center Questions
        elif room_type == "Experience Center":
            return [
                {
                    'id': 'acim_business_outcome',
                    'question': '1. What is the intended business outcome of the Experience Center? Please provide detailed insights into the overall management goals and explain how the Experience Center will add value to your organization.',
                    'type': 'text_area',
                    'placeholder': 'Describe business goals, target audience, and expected outcomes',
                    'height': 200
                },
                {
                    'id': 'acim_room_dimensions',
                    'question': '2. Can you provide detailed room dimensions (length, breadth, height) and layout preferences (e.g., open space, structured zones)?',
                    'type': 'text_area',
                    'placeholder': 'Example: 60ft x 40ft x 15ft, open floor plan with 3 zones'
                },
                {
                    'id': 'acim_showcase_items',
                    'question': '3. What products, services, or solutions will be showcased in the Experience Center?',
                    'type': 'text_area',
                    'placeholder': 'List products/services to be demonstrated'
                },
                {
                    'id': 'acim_flexibility',
                    'question': '4. Will this space be flexible, allowing for changing product showcases? Will the showcase include both physical products and non-physical elements such as services or software solutions?',
                    'type': 'text_area',
                    'placeholder': 'Describe flexibility requirements'
                },
                {
                    'id': 'acim_stakeholders',
                    'question': '5. Who are the key stakeholders or target audiences for the Experience Center (e.g., customers, partners, internal teams)?',
                    'type': 'text_area',
                    'placeholder': 'List target audiences and their needs'
                },
                {
                    'id': 'acim_visitor_experience',
                    'question': '6. What type of experience do you want visitors to have (e.g., interactive, guided, self-serve)? How long will a typical walkthrough take?',
                    'type': 'text_area',
                    'placeholder': 'Example: Self-guided, interactive displays, 30-minute walkthrough'
                },
                {
                    'id': 'acim_av_equipment',
                    'question': '9. What types of AV equipment do you envision using (e.g., videowalls, touch screens, projection systems)?',
                    'type': 'multiselect',
                    'options': [
                        'Video Walls',
                        'Interactive Touch Screens',
                        'Projection Systems',
                        'LED Walls',
                        'Audio Systems',
                        'Lighting Effects',
                        'Digital Signage'
                    ]
                },
                {
                    'id': 'acim_budget',
                    'question': '11. What is the allocated budget for this project?',
                    'type': 'select',
                    'options': [
                        '$50,000 - $100,000',
                        '$100,000 - $250,000',
                        '$250,000 - $500,000',
                        'Over $500,000',
                        'To be discussed'
                    ]
                }
            ]
        
        # Reception/Digital Signage Questions
        elif room_type == "Reception/Digital Signage":
            return [
                {
                    'id': 'acim_display_type',
                    'question': '1. What type of display would you prefer: a commercial display, video wall, or active LED?',
                    'type': 'select',
                    'options': [
                        'Single Commercial Display',
                        'Video Wall (multiple displays)',
                        'Active LED Wall',
                        'Multiple individual displays'
                    ]
                },
                {
                    'id': 'acim_room_dimensions',
                    'question': '2. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Include ceiling height, wall space available, viewing distances'
                },
                {
                    'id': 'acim_content_type',
                    'question': '3. What type of content will be showcased on the digital signage (e.g., welcome messages, event promotions, product launches, commercial broadcasts)?',
                    'type': 'text_area',
                    'placeholder': 'Describe content types and update frequency'
                },
                {
                    'id': 'acim_centralized_platform',
                    'question': '4. Do you require a centralized, web-based platform for remotely managing and pushing updates to the digital signage?',
                    'type': 'boolean',
                    'default': True,
                    'help': 'Centralized management simplifies content updates'
                },
                {
                    'id': 'acim_locations_count',
                    'question': '5. How many locations or screens would need to be controlled?',
                    'type': 'number',
                    'min': 1,
                    'max': 100,
                    'default': 1
                },
                {
                    'id': 'acim_audio_solution',
                    'question': '6. Do you require an audio solution to complement the digital signage, such as background music or sound for videos?',
                    'type': 'boolean',
                    'default': False
                },
                {
                    'id': 'acim_budget',
                    'question': '8. What is your budget range for this project?',
                    'type': 'select',
                    'options': [
                        'Under $10,000',
                        '$10,000 - $25,000',
                        '$25,000 - $50,000',
                        '$50,000 - $100,000',
                        'Over $100,000'
                    ]
                }
            ]
        
        # Default: Return empty list if room type not matched
        else:
            return []
    
    def _build_enhanced_question_tree(self) -> Dict[str, Any]:
        """Build comprehensive question structure with ACIM integration"""
        return {
            'basic_info': {
                'title': '📋 Project Basics',
                'questions': [
                    {
                        'id': 'project_type',
                        'question': 'What type of project is this?',
                        'type': 'select',
                        'options': [
                            'New Installation',
                            'System Upgrade',
                            'Room Renovation',
                            'Technology Refresh'
                        ],
                        'help': 'This helps us understand infrastructure constraints'
                    },
                    {
                        'id': 'room_count',
                        'question': 'How many rooms need AV systems?',
                        'type': 'number',
                        'min': 1,
                        'max': 50,
                        'default': 1,
                        'help': 'Total number of spaces requiring AV equipment'
                    },
                    {
                        'id': 'primary_use_case',
                        'question': 'What is the primary use case?',
                        'type': 'select',
                        'options': [
                            'Video Conferencing',
                            'Presentations & Training',
                            'Hybrid Meetings',
                            'Executive Boardroom',
                            'Event & Broadcast',
                            'Multipurpose'
                        ],
                        'help': 'Primary activity that will drive system design'
                    },
                    {
                        'id': 'budget_level',
                        'question': 'What is your budget level?',
                        'type': 'select',
                        'options': [
                            'Economy (Cost-focused)',
                            'Standard (Balanced)',
                            'Premium (Quality-focused)',
                            'Executive (Best-in-class)'
                        ],
                        'default': 'Standard (Balanced)',
                        'help': 'This determines product tier selection'
                    }
                ]
            },
            
            # NEW SECTION - ACIM Room Type Selection
            'acim_room_selection': {
                'title': '🏢 Detailed Room Classification (ACIM)',
                'help_text': 'Select the specific room type for detailed technical requirements',
                'questions': [
                    {
                        'id': 'room_type_acim',
                        'question': 'Select the ACIM room type that best matches your space:',
                        'type': 'select',
                        'options': [
                            'Conference/Meeting Room/Boardroom',
                            'Experience Center',
                            'Reception/Digital Signage',
                            'Training Room',
                            'Network Operations Center/Command Center',
                            'Town Hall',
                            'Auditorium'
                        ],
                        'default': 'Conference/Meeting Room/Boardroom',
                        'help': 'This determines which detailed questions you will see next'
                    }
                ]
            },
            
            # EXISTING SECTIONS (preserved)
            'display_system': {
                'title': '🖥️ Display System Preferences',
                'questions': [
                    {
                        'id': 'display_brand_preference',
                        'question': 'Do you have a preferred display brand?',
                        'type': 'select',
                        'options': [
                            'No Preference',
                            'Samsung',
                            'LG',
                            'Sony',
                            'NEC',
                            'Sharp'
                        ],
                        'default': 'No Preference',
                        'help': 'We can prioritize specific brands if you have standardization requirements'
                    },
                    {
                        'id': 'display_size_preference',
                        'question': 'Display size preference (will be validated against AVIXA standards)',
                        'type': 'select',
                        'options': [
                            'AVIXA Recommended (Automatic)',
                            'Specific Size (I will specify)',
                            'Largest Possible',
                            'Budget Constrained (Smaller)'
                        ],
                        'default': 'AVIXA Recommended (Automatic)',
                        'help': 'AVIXA recommendation ensures optimal viewing experience'
                    },
                    {
                        'id': 'dual_display_needed',
                        'question': 'Do you need dual displays (content + people)?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'primary_use_case': ['Video Conferencing', 'Hybrid Meetings', 'Executive Boardroom']
                        },
                        'help': 'Dual displays improve hybrid meeting experience'
                    },
                    {
                        'id': 'interactive_display_needed',
                        'question': 'Do you need touch/interactive displays?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'primary_use_case': ['Presentations & Training', 'Multipurpose']
                        },
                        'help': 'Interactive displays enable collaboration and annotation'
                    }
                ]
            },
            
            'video_conferencing': {
                'title': '🎥 Video Conferencing Requirements',
                'questions': [
                    {
                        'id': 'vc_platform',
                        'question': 'Which video conferencing platform do you use?',
                        'type': 'select',
                        'options': [
                            'Microsoft Teams',
                            'Zoom',
                            'Cisco Webex',
                            'Google Meet',
                            'Platform Agnostic (BYOD)'
                        ],
                        'help': 'This ensures compatibility and certification'
                    },
                    {
                        'id': 'vc_brand_preference',
                        'question': 'Video conferencing equipment brand preference?',
                        'type': 'select',
                        'options': [
                            'No Preference',
                            'Poly',
                            'Logitech',
                            'Cisco',
                            'Yealink',
                            'Crestron',
                            'Neat'
                        ],
                        'default': 'No Preference',
                        'help': 'Ecosystem consistency can simplify management'
                    },
                    {
                        'id': 'camera_type_preference',
                        'question': 'Camera system preference',
                        'type': 'select',
                        'options': [
                            'All-in-One Video Bar (Recommended for small/medium rooms)',
                            'PTZ Camera with Codec (Better for large rooms)',
                            'Auto-Framing Camera System',
                            'Multi-Camera Setup'
                        ],
                        'help': 'Room size will influence final recommendation'
                    },
                    {
                        'id': 'auto_tracking_needed',
                        'question': 'Do you need automatic speaker tracking?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'primary_use_case': ['Video Conferencing', 'Hybrid Meetings', 'Presentations & Training']
                        },
                        'help': 'Keeps remote participants engaged by focusing on active speaker'
                    }
                ]
            },
            
            'audio_system': {
                'title': '🔊 Audio System Requirements',
                'questions': [
                    {
                        'id': 'audio_brand_preference',
                        'question': 'Audio equipment brand preference?',
                        'type': 'select',
                        'options': [
                            'No Preference',
                            'Shure',
                            'Biamp',
                            'QSC',
                            'Sennheiser',
                            'Bose',
                            'Crestron'
                        ],
                        'default': 'No Preference',
                        'help': 'Professional audio brands ensure reliability'
                    },
                    {
                        'id': 'microphone_type',
                        'question': 'Preferred microphone solution',
                        'type': 'select',
                        'options': [
                            'Integrated in Video Bar (for small rooms)',
                            'Table/Boundary Microphones',
                            'Ceiling Microphone Array',
                            'Wireless Handheld/Lapel',
                            'Hybrid (Multiple Types)'
                        ],
                        'help': 'Ceiling mics provide clean aesthetics but may affect acoustics'
                    },
                    {
                        'id': 'ceiling_vs_table_audio',
                        'question': 'For speakers, do you prefer ceiling or table placement?',
                        'type': 'select',
                        'options': [
                            'Ceiling Mounted (Clean aesthetic)',
                            'Table/Soundbar (Better performance)',
                            'Integrated in Video Bar',
                            'Wall Mounted'
                        ],
                        'show_if': {
                            'room_count': [1, 2, 3, 4, 5]
                        }
                    },
                    {
                        'id': 'voice_reinforcement_needed',
                        'question': 'Do you need voice reinforcement for presenters?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'primary_use_case': ['Presentations & Training', 'Event & Broadcast', 'Multipurpose']
                        },
                        'help': 'Essential for rooms >500 sqft with audience seating'
                    }
                ]
            },
            
            'control_integration': {
                'title': '🎛️ Control & Integration',
                'questions': [
                    {
                        'id': 'control_brand_preference',
                        'question': 'Control system brand preference?',
                        'type': 'select',
                        'options': [
                            'No Preference',
                            'Crestron',
                            'Extron',
                            'AMX',
                            'Native Platform Control (Teams Rooms/Zoom Rooms)'
                        ],
                        'default': 'Native Platform Control (Teams Rooms/Zoom Rooms)',
                        'help': 'Native control is simpler; programmable systems offer more flexibility'
                    },
                    {
                        'id': 'wireless_presentation_needed',
                        'question': 'Do you need wireless presentation (BYOD)?',
                        'type': 'boolean',
                        'default': True,
                        'help': 'Allows guests to share content wirelessly'
                    },
                    {
                        'id': 'room_scheduling_needed',
                        'question': 'Do you need room scheduling displays?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'budget_level': ['Premium (Quality-focused)', 'Executive (Best-in-class)']
                        },
                        'help': 'Shows room availability and calendar integration'
                    },
                    {
                        'id': 'lighting_control_integration',
                        'question': 'Do you want to integrate lighting control?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'budget_level': ['Premium (Quality-focused)', 'Executive (Best-in-class)']
                        },
                        'help': 'Automated lighting enhances user experience'
                    }
                ]
            },
            
            'infrastructure': {
                'title': '🔌 Infrastructure & Installation',
                'questions': [
                    {
                        'id': 'existing_network_capable',
                        'question': 'Is your network infrastructure AV-ready? (1Gb+ with QoS)',
                        'type': 'boolean',
                        'default': True,
                        'help': 'We may need to include network switches if infrastructure is inadequate'
                    },
                    {
                        'id': 'power_infrastructure_adequate',
                        'question': 'Are dedicated 20A circuits available for AV equipment?',
                        'type': 'boolean',
                        'default': False,
                        'help': 'Large systems may require electrical upgrades'
                    },
                    {
                        'id': 'cable_management_type',
                        'question': 'Cable management approach',
                        'type': 'select',
                        'options': [
                            'In-Wall/Conduit (Professional)',
                            'Surface Mount Raceways',
                            'Under Table/Furniture',
                            'Exposed (Budget)'
                        ],
                        'help': 'Affects installation cost and aesthetics'
                    }
                ]
            },
            
            'compliance_special': {
                'title': '✅ Compliance & Special Features',
                'questions': [
                    {
                        'id': 'ada_compliance_required',
                        'question': 'Is ADA compliance required?',
                        'type': 'boolean',
                        'default': False,
                        'help': 'May require assistive listening systems and accessible controls'
                    },
                    {
                        'id': 'recording_capability_needed',
                        'question': 'Do you need recording capability?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'primary_use_case': ['Presentations & Training', 'Event & Broadcast']
                        },
                        'help': 'For lecture capture or content creation'
                    },
                    {
                        'id': 'streaming_capability_needed',
                        'question': 'Do you need live streaming capability?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'primary_use_case': ['Event & Broadcast', 'Multipurpose']
                        },
                        'help': 'For broadcasting to remote audiences'
                    }
                ]
            },
            
            'avixa_compliance': {
                'title': '📐 AVIXA Standards & Performance',
                'questions': [
                    {
                        'id': 'avixa_display_sizing',
                        'question': 'Display sizing preference',
                        'type': 'select',
                        'options': [
                            'AVIXA DISCAS Recommended (Optimal viewing)',
                            'Budget-Constrained (Smaller acceptable)',
                            'Premium Viewing (Larger than minimum)',
                            'I will specify exact size'
                        ],
                        'default': 'AVIXA DISCAS Recommended (Optimal viewing)',
                        'help': 'AVIXA DISCAS ensures optimal viewing experience based on room dimensions'
                    },
                    {
                        'id': 'performance_verification_required',
                        'question': 'Do you require AVIXA 10:2013 performance verification testing?',
                        'type': 'boolean',
                        'default': False,
                        'show_if': {
                            'budget_level': ['Premium (Quality-focused)', 'Executive (Best-in-class)']
                        },
                        'help': 'Professional commissioning with documented test results per AVIXA standards'
                    },
                    {
                        'id': 'target_sti_level',
                        'question': 'Audio intelligibility requirements',
                        'type': 'select',
                        'options': [
                            'Standard (STI ≥ 0.60)',
                            'High (STI ≥ 0.70)',
                            'Critical (STI ≥ 0.75)'
                        ],
                        'default': 'Standard (STI ≥ 0.60)',
                        'show_if': {
                            'primary_use_case': ['Video Conferencing', 'Executive Boardroom', 'Event & Broadcast']
                        },
                        'help': 'Speech Transmission Index - higher values ensure clearer audio'
                    }
                ]
            },
            
            'advanced_requirements': {
                'title': '📝 Additional Requirements',
                'questions': [
                    {
                        'id': 'additional_requirements',
                        'question': 'Any additional requirements or specific features?',
                        'type': 'text_area',
                        'placeholder': 'Examples:\n- Must integrate with existing Crestron system\n- Need digital signage capability\n- Require video wall in lobby\n- Special acoustical considerations\n- Existing equipment to be reused',
                        'help': 'Include any requirements not covered by the questions above'
                    }
                ]
            }
        }
    
    def should_show_question(self, question: Dict, responses: Dict) -> bool:
        """Determine if question should be shown based on previous answers"""
        if 'show_if' not in question:
            return True
        
        show_if = question['show_if']
        for condition_key, condition_values in show_if.items():
            if condition_key not in responses:
                return False
            if responses[condition_key] not in condition_values:
                return False
        
        return True
    
    def render_questionnaire(self) -> Dict[str, Any]:
        """Render the complete questionnaire in Streamlit"""
        st.markdown("## 🎯 Enhanced Smart BOQ Questionnaire")
        st.markdown("Answer these questions to generate an optimized, AVIXA-compliant Bill of Quantities.")
        st.markdown("---")
        
        responses = {}
        
        # Progress tracking
        total_questions = sum(
            len(section['questions']) 
            for section in self.questions.values()
        )
        questions_answered = 0
        
        for section_key, section in self.questions.items():
            # Special handling for ACIM room selection
            is_acim_section = (section_key == 'acim_room_selection')
            
            with st.expander(
                f"**{section['title']}**", 
                expanded=(section_key == 'basic_info' or is_acim_section)
            ):
                # Add help text for ACIM section
                if 'help_text' in section:
                    st.info(section['help_text'])
                
                for question in section['questions']:
                    # Check if question should be shown
                    if not self.should_show_question(question, responses):
                        continue
                    
                    q_id = question['id']
                    q_text = question['question']
                    q_type = question['type']
                    q_help = question.get('help', '')
                    
                    # Render based on question type
                    if q_type == 'select':
                        response = st.selectbox(
                            q_text,
                            options=question['options'],
                            index=question['options'].index(question.get('default', question['options'][0])) if 'default' in question else 0,
                            key=f"q_{q_id}",
                            help=q_help
                        )
                        responses[q_id] = response
                        questions_answered += 1
                        
                    elif q_type == 'boolean':
                        response = st.checkbox(
                            q_text,
                            value=question.get('default', False),
                            key=f"q_{q_id}",
                            help=q_help
                        )
                        responses[q_id] = response
                        questions_answered += 1
                        
                    elif q_type == 'number':
                        response = st.number_input(
                            q_text,
                            min_value=question.get('min', 1),
                            max_value=question.get('max', 100),
                            value=question.get('default', 1),
                            key=f"q_{q_id}",
                            help=q_help
                        )
                        responses[q_id] = response
                        questions_answered += 1
                        
                    elif q_type == 'text_area':
                        response = st.text_area(
                            q_text,
                            value=question.get('default', ''),
                            placeholder=question.get('placeholder', ''),
                            key=f"q_{q_id}",
                            help=q_help,
                            height=150
                        )
                        responses[q_id] = response
                        questions_answered += 1
        
        # Progress indicator
        progress = questions_answered / total_questions
        st.progress(progress)
        st.caption(f"Progress: {questions_answered}/{total_questions} questions answered")
        
        return responses
    
    def convert_to_client_requirements(self, responses: Dict[str, Any]) -> ClientRequirements:
        """Convert questionnaire responses to ClientRequirements object"""
        return ClientRequirements(
            # Existing fields
            project_type=responses.get('project_type', 'New Installation'),
            room_count=responses.get('room_count', 1),
            primary_use_case=responses.get('primary_use_case', 'Video Conferencing'),
            budget_level=responses.get('budget_level', 'Standard (Balanced)').split(' ')[0],
            
            display_brand_preference=responses.get('display_brand_preference', 'No Preference'),
            display_size_preference=responses.get('display_size_preference', 'AVIXA Recommended (Automatic)'),
            dual_display_needed=responses.get('dual_display_needed', False),
            interactive_display_needed=responses.get('interactive_display_needed', False),
            
            vc_platform=responses.get('vc_platform', 'Microsoft Teams'),
            vc_brand_preference=responses.get('vc_brand_preference', 'No Preference'),
            camera_type_preference=responses.get('camera_type_preference', 'All-in-One Video Bar'),
            auto_tracking_needed=responses.get('auto_tracking_needed', False),
            
            audio_brand_preference=responses.get('audio_brand_preference', 'No Preference'),
            microphone_type=responses.get('microphone_type', 'Table/Boundary Microphones'),
            ceiling_vs_table_audio=responses.get('ceiling_vs_table_audio', 'Integrated in Video Bar'),
            voice_reinforcement_needed=responses.get('voice_reinforcement_needed', False),
            
            control_brand_preference=responses.get('control_brand_preference', 'Native Platform Control'),
            wireless_presentation_needed=responses.get('wireless_presentation_needed', True),
            room_scheduling_needed=responses.get('room_scheduling_needed', False),
            lighting_control_integration=responses.get('lighting_control_integration', False),
            
            existing_network_capable=responses.get('existing_network_capable', True),
            power_infrastructure_adequate=responses.get('power_infrastructure_adequate', False),
            cable_management_type=responses.get('cable_management_type', 'In-Wall/Conduit (Professional)'),
            
            ada_compliance_required=responses.get('ada_compliance_required', False),
            recording_capability_needed=responses.get('recording_capability_needed', False),
            streaming_capability_needed=responses.get('streaming_capability_needed', False),
            
            additional_requirements=responses.get('additional_requirements', ''),
            
            avixa_display_sizing=responses.get('avixa_display_sizing', 'AVIXA DISCAS Recommended'),
            performance_verification_required=responses.get('performance_verification_required', False),
            target_sti_level=responses.get('target_sti_level', 'Standard (STI ≥ 0.60)'),
            
            # NEW ACIM fields
            room_type_acim=responses.get('room_type_acim', ''),
            supporting_documents=[]
        )
