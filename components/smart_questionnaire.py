# components/smart_questionnaire.py
"""
ENHANCED Smart BOQ Questionnaire System - ACIM Form Integration
Combines ACIM-style detailed questions with automated BOQ generation
"""

import streamlit as st
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class ClientDetails:
    """Client contact information"""
    name: str = ""
    company_name: str = ""
    company_location: str = ""
    designation: str = ""
    email: str = ""
    mobile: str = ""

@dataclass
class ClientRequirements:
    """Structured client requirements from questionnaire - ENHANCED for ACIM integration"""

    # Client Details
    client_name: str = ""
    client_company: str = ""
    client_location: str = ""
    client_designation: str = ""
    client_email: str = ""
    client_mobile: str = ""

    # Project Basics
    project_type: str = "New Installation"
    room_count: int = 1
    primary_use_case: str = "Video Conferencing"
    budget_level: str = "Standard"

    # Room-Specific Responses (will hold detailed ACIM answers per room)
    room_responses: Dict[str, Dict[str, Any]] = None

    # Display Preferences (derived from ACIM responses)
    display_brand_preference: str = "No Preference"
    display_size_preference: str = "AVIXA Recommended"
    dual_display_needed: bool = False
    interactive_display_needed: bool = False

    # Video Conferencing (derived from ACIM responses)
    vc_platform: str = "Microsoft Teams"
    vc_brand_preference: str = "No Preference"
    camera_type_preference: str = "Auto-detect from room size"
    auto_tracking_needed: bool = False

    # Audio System (derived from ACIM responses)
    audio_brand_preference: str = "No Preference"
    microphone_type: str = "Table/Boundary Microphones"
    ceiling_vs_table_audio: str = "Integrated in Video Bar"
    voice_reinforcement_needed: bool = False

    # Control & Integration
    control_brand_preference: str = "Native Platform Control"
    wireless_presentation_needed: bool = True
    room_scheduling_needed: bool = False
    lighting_control_integration: bool = False

    # Infrastructure
    existing_network_capable: bool = True
    power_infrastructure_adequate: bool = False
    cable_management_type: str = "In-Wall/Conduit"

    # Compliance & Special Requirements
    ada_compliance_required: bool = False
    recording_capability_needed: bool = False
    streaming_capability_needed: bool = False

    # Advanced Requirements
    additional_requirements: str = ""

    # AVIXA-specific requirements
    avixa_display_sizing: str = "AVIXA DISCAS Recommended"
    performance_verification_required: bool = False
    target_sti_level: str = "Standard (STI ≥ 0.60)"

    def __post_init__(self):
        if self.room_responses is None:
            self.room_responses = {}

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
    ENHANCED: Combines ACIM-style detailed questions with intelligent BOQ generation
    Adapts questions based on room type
    """

    def __init__(self):
        self.room_types = self._get_room_types()
        self.questions_by_room_type = self._build_acim_questions_by_room_type()

    def _get_room_types(self) -> List[str]:
        """Available room types - maps to your existing ROOM_SPECS"""
        return [
            "Conference/Meeting Room/Boardroom",
            "Training Room",
            "Town Hall",
            "Auditorium",
            "Experience Center",
            "Reception/Digital Signage",
            "Network Operations Center/Command Center"
        ]

    def _map_room_type_to_spec(self, acim_room_type: str) -> str:
        """Map ACIM room types to your existing ROOM_SPECS keys"""
        mapping = {
            "Conference/Meeting Room/Boardroom": "Standard Conference Room (6-8 People)",
            "Training Room": "Training Room (15-25 People)",
            "Town Hall": "Large Training/Presentation Room (25-40 People)",
            "Auditorium": "Multipurpose Event Room (40+ People)",
            "Experience Center": "Multipurpose Event Room (40+ People)",
            "Reception/Digital Signage": "Small Huddle Room (2-3 People)",
            "Network Operations Center/Command Center": "Executive Boardroom (10-16 People)"
        }
        return mapping.get(acim_room_type, "Standard Conference Room (6-8 People)")

    def _build_acim_questions_by_room_type(self) -> Dict[str, List[Dict]]:
        """Build ACIM-style questions for each room type"""
        return {
            "Conference/Meeting Room/Boardroom": [
                {
                    'id': 'room_dimensions',
                    'question': '1. What is the seating capacity, layout (e.g., square table, U-shaped table, theater style), and detailed dimensions of the room, including its length, breadth, and height?',
                    'type': 'text_area',
                    'placeholder': 'Example: 8-person capacity, rectangular table, 20ft x 15ft x 9ft ceiling',
                    'required': True,
                    'extract_dimensions': True
                },
                {
                    'id': 'solution_type',
                    'question': '2. Would you require an AV (Audio Visual) Solution for only Presentations or Video Collaboration (Teams/Zoom) as well for this meeting room?',
                    'type': 'select',
                    'options': ['Presentations Only', 'Video Collaboration Only', 'Both Presentations and Video Collaboration'],
                    'required': True
                },
                {
                    'id': 'uc_platform',
                    'question': '3. Which UC platform does your organization currently use?',
                    'type': 'select',
                    'options': ['Microsoft Teams', 'Zoom', 'Cisco Webex', 'Google Meet', 'GoToMeeting', 'Platform Agnostic'],
                    'required': True
                },
                {
                    'id': 'native_solution',
                    'question': '4. Would you require a Native Solution for simplified one-touch dialing via a touch panel mounted on the desk, or would you prefer to connect your laptop and use the meeting room\'s camera to facilitate the meeting with remote participants?',
                    'type': 'select',
                    'options': ['Native Solution (One-touch dialing)', 'BYOD (Bring Your Own Device)', 'Both Options'],
                    'required': True
                },
                {
                    'id': 'connectivity',
                    'question': '5. Do you require wired (e.g., HDMI) or wireless connectivity, and would you also need USB-C as an option?',
                    'type': 'multiselect',
                    'options': ['HDMI', 'Wireless Presentation', 'USB-C', 'DisplayPort'],
                    'required': True
                },
                {
                    'id': 'digital_whiteboard',
                    'question': '6. Would you like a digital whiteboard with streaming capabilities, such as Kaptivo or Logitech Scribe, for collaboration?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'automation',
                    'question': '7. Do you want room automation for controlling AV systems, lighting, air conditioning, and blinds?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'room_scheduler',
                    'question': '8. Would you require a room scheduler outside the room that integrates with platforms like Microsoft 365 or Gmail?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'acoustic_solutions',
                    'question': '9. Would you like more information about acoustic solutions to enhance the AV and video collaboration experience?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'budget',
                    'question': '10. What is your budget range for this project?',
                    'type': 'select',
                    'options': ['Under $10,000', '$10,000 - $25,000', '$25,000 - $50,000', '$50,000 - $100,000', 'Above $100,000', 'Not Sure'],
                    'required': False
                }
            ],

            "Training Room": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Example: 40ft x 30ft x 12ft ceiling, with columns at mid-points',
                    'required': True,
                    'extract_dimensions': True
                },
                {
                    'id': 'seating_info',
                    'question': '2. How many seats are there in the room, and what is the seating orientation towards the trainer? (e.g., classroom, theater, U-shaped)',
                    'type': 'text_area',
                    'placeholder': 'Example: 25 seats, classroom style, all facing front',
                    'required': True
                },
                {
                    'id': 'connectivity',
                    'question': '3. Are you looking for wired and wireless connectivity from both the podium and the overall seating area?',
                    'type': 'multiselect',
                    'options': ['Wired Podium Connectivity', 'Wireless Podium', 'Wired Seat Connectivity', 'Wireless throughout room'],
                    'required': True
                },
                {
                    'id': 'remote_training',
                    'question': '4. Will this training room be used for remote training via platforms like Microsoft Teams, Zoom, WebEx, GoToMeeting, etc.?',
                    'type': 'select',
                    'options': ['Yes - Primary Use', 'Yes - Occasional Use', 'No'],
                    'required': True
                },
                {
                    'id': 'camera_requirements',
                    'question': '5. Based on the size of the room, would you require a single camera to capture the trainer, or would you need multiple cameras to capture the trainer and the audience?',
                    'type': 'select',
                    'options': ['Single Camera (Trainer Only)', 'Multiple Cameras (Trainer + Audience)', 'Auto-Tracking Camera System'],
                    'required': True
                },
                {
                    'id': 'digital_whiteboard',
                    'question': '6. Would you require a digital whiteboard collaboration tool with streaming options, such as Kaptivo or Logitech Scribe?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'automation',
                    'question': '7. Would you need automation in the room for controlling Audio Visual equipment, lights, air conditioning, blinds, etc.?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'live_streaming',
                    'question': '8. Would you need live streaming or corporate broadcasting for distance learning?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'budget',
                    'question': '9. What is your budget range for this project?',
                    'type': 'select',
                    'options': ['Under $25,000', '$25,000 - $50,000', '$50,000 - $100,000', 'Above $100,000', 'Not Sure'],
                    'required': False
                }
            ],

            "Town Hall": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Example: 60ft x 40ft x 15ft ceiling',
                    'required': True,
                    'extract_dimensions': True
                },
                {
                    'id': 'seating_info',
                    'question': '2. How many seats are there in the room, and what is the seating orientation? (e.g., theater, auditorium style)',
                    'type': 'text_area',
                    'placeholder': 'Example: 150 seats, theater style facing stage',
                    'required': True
                },
                {
                    'id': 'usage_frequency',
                    'question': '3. How often will the Town Hall be used?',
                    'type': 'select',
                    'options': ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Occasionally'],
                    'required': True
                },
                {
                    'id': 'uc_platform',
                    'question': '4. Which UC (Unified Collaboration) platform do you currently use?',
                    'type': 'select',
                    'options': ['Microsoft Teams', 'Zoom', 'Cisco Webex', 'Google Meet', 'Multiple Platforms'],
                    'required': True
                },
                {
                    'id': 'camera_requirements',
                    'question': '5. Would you require multiple cameras to capture both presenters and the audience?',
                    'type': 'select',
                    'options': ['Single Presenter Camera', 'Multiple Cameras with Switching', 'Auto-Tracking System', 'Full Production Setup'],
                    'required': True
                },
                {
                    'id': 'audio_performance',
                    'question': '6. Town halls are often conducted in reverberant spaces (acoustically challenging). Would you require high-performance audio with digital processing?',
                    'type': 'select',
                    'options': ['Yes - Critical audio quality needed', 'Standard conference audio acceptable', 'Need acoustic consultation'],
                    'required': True
                },
                {
                    'id': 'automation',
                    'question': '7. Would you need automation in the room for controlling Audio Visual equipment, lights, air conditioning, blinds, etc.?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'budget',
                    'question': '8. What is your budget range for this project?',
                    'type': 'select',
                    'options': ['$50,000 - $100,000', '$100,000 - $200,000', 'Above $200,000', 'Not Sure'],
                    'required': False
                }
            ],

            "Auditorium": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height)?',
                    'type': 'text_area',
                    'placeholder': 'Example: 80ft x 60ft x 20ft ceiling',
                    'required': True,
                    'extract_dimensions': True
                },
                {
                    'id': 'seating_info',
                    'question': '2. How many seats are there in the auditorium?',
                    'type': 'text_area',
                    'placeholder': 'Example: 300 seats, fixed theater seating with balcony',
                    'required': True
                },
                {
                    'id': 'primary_applications',
                    'question': '3. What are the primary applications for this auditorium?',
                    'type': 'multiselect',
                    'options': ['Presentations', 'Distance Learning', 'Live Events', 'Entertainment', 'Corporate Broadcast'],
                    'required': True
                },
                {
                    'id': 'vc_solution',
                    'question': '4. Would you require a Video Conferencing solution for this space?',
                    'type': 'select',
                    'options': ['Yes - Native Solution', 'Yes - BYOD', 'No - Presentation Only'],
                    'required': True
                },
                {
                    'id': 'microphone_preferences',
                    'question': '5. What type of microphones are preferred for onstage and offstage use?',
                    'type': 'multiselect',
                    'options': ['Wireless Handheld', 'Lapel/Lavalier', 'Podium Gooseneck', 'Boundary Mics', 'Audience Mics'],
                    'required': True
                },
                {
                    'id': 'live_streaming',
                    'question': '6. Would you require live streaming, corporate broadcast, or distance learning capabilities?',
                    'type': 'boolean',
                    'required': False
                },
                {
                    'id': 'budget',
                    'question': '7. What is your budget range for this project?',
                    'type': 'select',
                    'options': ['$100,000 - $250,000', '$250,000 - $500,000', 'Above $500,000', 'Not Sure'],
                    'required': False
                }
            ],

            "Experience Center": [
                {
                    'id': 'business_outcome',
                    'question': '1. What is the intended business outcome of the Experience Center? Please provide detailed insights into the overall management goals and explain how the Experience Center will add value to your organization.',
                    'type': 'text_area',
                    'placeholder': 'Describe your vision and objectives...',
                    'required': True
                },
                {
                    'id': 'room_dimensions',
                    'question': '2. Can you provide detailed room dimensions (length, breadth, height) and layout preferences?',
                    'type': 'text_area',
                    'placeholder': 'Example: 50ft x 40ft x 12ft, open space with 3 zones',
                    'required': True,
                    'extract_dimensions': True
                },
                {
                    'id': 'av_equipment',
                    'question': '3. What types of AV equipment do you envision using?',
                    'type': 'multiselect',
                    'options': ['Video Walls', 'Touch Screens', 'Interactive Displays', 'Projection Systems', 'Digital Signage', 'Immersive Audio'],
                    'required': True
                },
                {
                    'id': 'video_conferencing',
                    'question': '4. Will the Experience Center be used for video conferencing or virtual demonstrations?',
                    'type': 'boolean',
                    'required': True
                },
                {
                    'id': 'budget',
                    'question': '5. What is the allocated budget for this project?',
                    'type': 'select',
                    'options': ['$100,000 - $250,000', '$250,000 - $500,000', 'Above $500,000', 'Not Sure'],
                    'required': False
                }
            ],

            "Reception/Digital Signage": [
                {
                    'id': 'display_type',
                    'question': '1. What type of display would you prefer?',
                    'type': 'select',
                    'options': ['Commercial Display', 'Video Wall', 'Active LED', 'Not Sure'],
                    'required': True
                },
                {
                    'id': 'room_dimensions',
                    'question': '2. Could you provide room dimensions and viewing distances?',
                    'type': 'text_area',
                    'placeholder': 'Example: Wall is 15ft wide, viewing distance 10-20ft',
                    'required': True,
                    'extract_dimensions': True
                },
                {
                    'id': 'content_type',
                    'question': '3. What type of content will be showcased on the digital signage?',
                    'type': 'multiselect',
                    'options': ['Welcome Messages', 'Event Promotions', 'Product Launches', 'Commercial Broadcasts', 'Wayfinding'],
                    'required': True
                },
                {
                    'id': 'centralized_platform',
                    'question': '4. Do you require a centralized, web-based platform for remotely managing and pushing updates to the digital signage?',
                    'type': 'boolean',
                    'required': True
                },
                {
                    'id': 'budget',
                    'question': '5. What is your budget range for this project?',
                    'type': 'select',
                    'options': ['Under $10,000', '$10,000 - $25,000', '$25,000 - $50,000', 'Above $50,000'],
                    'required': False
                }
            ],

            "Network Operations Center/Command Center": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height)?',
                    'type': 'text_area',
                    'placeholder': 'Example: 40ft x 30ft x 10ft ceiling',
                    'required': True,
                    'extract_dimensions': True
                },
                {
                    'id': 'users_count',
                    'question': '2. How many users will be viewing the screen? This will help us calculate the number of screens and windows required.',
                    'type': 'number',
                    'min': 1,
                    'max': 100,
                    'required': True
                },
                {
                    'id': 'display_preference',
                    'question': '3. Do you have a preference for video walls, LED video walls, active LEDs, or projection for this room?',
                    'type': 'select',
                    'options': ['LCD Video Wall', 'LED Video Wall', 'Projection System', 'Combination', 'Not Sure'],
                    'required': True
                },
                {
                    'id': 'source_inputs',
                    'question': '4. How many source inputs will be needed? Should each user have their own input, or would it be from a central repository?',
                    'type': 'text_area',
                    'placeholder': 'Example: 12 workstations, each with 2 inputs, plus 4 central feeds',
                    'required': True
                },
                {
                    'id': 'budget',
                    'question': '5. What is your budget range for this project?',
                    'type': 'select',
                    'options': ['$100,000 - $250,000', '$250,000 - $500,000', 'Above $500,000', 'Not Sure'],
                    'required': False
                }
            ]
        }

    def _extract_dimensions_from_text(self, text: str) -> Dict[str, float]:
        """
        Extract room dimensions from natural language text
        Examples:
        - "20ft x 15ft x 9ft"
        - "Length 20', Width 15', Height 9'"
        - "6m x 5m x 3m"
        """
        import re

        # Pattern for ft format: "20ft x 15ft x 9ft" or "20' x 15' x 9'"
        pattern_ft = r"(\d+(?:\.\d+)?)\s*(?:ft|')\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:ft|')\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:ft|')"
        match = re.search(pattern_ft, text)

        if match:
            return {
                'length': float(match.group(1)),
                'width': float(match.group(2)),
                'ceiling_height': float(match.group(3))
            }

        # Pattern for meters: "6m x 5m x 3m"
        pattern_m = r"(\d+(?:\.\d+)?)\s*m\s*[xX×]\s*(\d+(?:\.\d+)?)\s*m\s*[xX×]\s*(\d+(?:\.\d+)?)\s*m"
        match = re.search(pattern_m, text)

        if match:
            # Convert meters to feet
            return {
                'length': float(match.group(1)) * 3.28084,
                'width': float(match.group(2)) * 3.28084,
                'ceiling_height': float(match.group(3)) * 3.28084
            }

        # If no pattern matches, return empty dict
        return {}

    def render_client_details_section(self) -> ClientDetails:
        """Render the 'Your Details' section"""
        st.markdown("## 📋 Your Details")
        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name *", key="client_name", placeholder="John Doe")
            company_location = st.text_input("Company Location *", key="client_location", placeholder="New York, NY")
            email = st.text_input("Email *", key="client_email", placeholder="john.doe@company.com")

        with col2:
            company_name = st.text_input("Company Name *", key="client_company", placeholder="Acme Corporation")
            designation = st.text_input("Designation", key="client_designation", placeholder="IT Manager")
            mobile = st.text_input("Mobile", key="client_mobile", placeholder="+1 (555) 123-4567")

        return ClientDetails(
            name=name,
            company_name=company_name,
            company_location=company_location,
            designation=designation,
            email=email,
            mobile=mobile
        )

    def render_room_type_selection(self) -> List[str]:
        """Render room type selection"""
        st.markdown("---")
        st.markdown("## 🏢 What kind of room(s) are you planning to design?")
        st.markdown("")

        selected_rooms = st.multiselect(
            "Select one or more room types:",
            options=self.room_types,
            key="selected_room_types",
            help="You can select multiple room types if you have different spaces to design"
        )

        return selected_rooms

    def render_room_questions(self, room_type: str, room_index: int) -> Dict[str, Any]:
        """Render questions for a specific room type"""
        questions = self.questions_by_room_type.get(room_type, [])
        responses = {}
        extracted_dimensions = {}

        for question in questions:
            q_id = question['id']
            q_text = question['question']
            q_type = question['type']
            q_placeholder = question.get('placeholder', '')
            q_required = question.get('required', False)

            # Add asterisk for required questions
            if q_required:
                q_text = q_text + " *"

            if q_type == 'text_area':
                response = st.text_area(
                    q_text,
                    placeholder=q_placeholder,
                    key=f"{room_type}_{room_index}_{q_id}",
                    height=100
                )
                responses[q_id] = response

                # Extract dimensions if this question contains room dimensions
                if question.get('extract_dimensions') and response:
                    dims = self._extract_dimensions_from_text(response)
                    if dims:
                        extracted_dimensions = dims
                        st.success(f"✅ Detected: {dims['length']:.1f}ft × {dims['width']:.1f}ft × {dims['ceiling_height']:.1f}ft ceiling")

            elif q_type == 'select':
                response = st.selectbox(
                    q_text,
                    options=question['options'],
                    key=f"{room_type}_{room_index}_{q_id}"
                )
                responses[q_id] = response

            elif q_type == 'multiselect':
                response = st.multiselect(
                    q_text,
                    options=question['options'],
                    key=f"{room_type}_{room_index}_{q_id}"
                )
                responses[q_id] = response

            elif q_type == 'boolean':
                response = st.checkbox(
                    q_text,
                    key=f"{room_type}_{room_index}_{q_id}"
                )
                responses[q_id] = response

            elif q_type == 'number':
                response = st.number_input(
                    q_text,
                    min_value=question.get('min', 1),
                    max_value=question.get('max', 100),
                    value=question.get('default', 1),
                    key=f"{room_type}_{room_index}_{q_id}"
                )
                responses[q_id] = response

        # Store extracted dimensions with responses
        if extracted_dimensions:
            responses['extracted_dimensions'] = extracted_dimensions

        return responses

    def _convert_to_client_requirements(self, client_details: ClientDetails, 
                                       selected_rooms: List[str], 
                                       all_room_responses: List[Dict]) -> ClientRequirements:
        """
        Convert ACIM form responses to ClientRequirements format for BOQ generation
        """

        # Start with default requirements
        requirements = ClientRequirements()

        # Fill client details
        requirements.client_name = client_details.name
        requirements.client_company = client_details.company_name
        requirements.client_location = client_details.company_location
        requirements.client_designation = client_details.designation
        requirements.client_email = client_details.email
        requirements.client_mobile = client_details.mobile

        # Store all room responses
        requirements.room_responses = {}
        for room_data in all_room_responses:
            room_type = room_data['room_type']
            room_key = f"{room_type}_{room_data.get('room_index', 0)}"
            requirements.room_responses[room_key] = room_data['responses']

        # Derive general requirements from first room (or aggregate logic)
        if all_room_responses:
            first_room = all_room_responses[0]
            responses = first_room['responses']

            # Extract UC platform
            if 'uc_platform' in responses:
                requirements.vc_platform = responses['uc_platform']

            # Extract budget level
            if 'budget' in responses:
                budget_text = responses['budget']
                if 'Under' in budget_text or '10,000' in budget_text:
                    requirements.budget_level = 'Economy'
                elif '100,000' in budget_text or 'Above' in budget_text:
                    requirements.budget_level = 'Premium'
                else:
                    requirements.budget_level = 'Standard'

            # Extract connectivity preferences
            if 'connectivity' in responses:
                conn = responses['connectivity']
                if isinstance(conn, list):
                    if 'Wireless Presentation' in conn:
                        requirements.wireless_presentation_needed = True
                    if 'USB-C' in conn:
                        requirements.cable_management_type = 'USB-C Priority'

            # Extract automation
            if responses.get('automation'):
                requirements.lighting_control_integration = True

            # Extract room scheduler
            if responses.get('room_scheduler'):
                requirements.room_scheduling_needed = True

            # Extract digital whiteboard
            if responses.get('digital_whiteboard'):
                requirements.interactive_display_needed = True

            # Extract streaming
            if responses.get('live_streaming'):
                requirements.streaming_capability_needed = True

            # Camera requirements
            if 'camera_requirements' in responses:
                cam = responses['camera_requirements']
                if 'Multiple' in str(cam) or 'Tracking' in str(cam):
                    requirements.auto_tracking_needed = True

            # Audio performance
            if 'audio_performance' in responses:
                audio = responses['audio_performance']
                if 'Critical' in str(audio) or 'high-performance' in str(audio):
                    requirements.voice_reinforcement_needed = True

        # Set room count
        requirements.room_count = len(selected_rooms)

        # Determine primary use case from selected room types
        if 'Training Room' in selected_rooms or 'Auditorium' in selected_rooms:
            requirements.primary_use_case = 'Presentations & Training'
        elif 'Conference/Meeting Room/Boardroom' in selected_rooms:
            requirements.primary_use_case = 'Video Conferencing'
        elif 'Experience Center' in selected_rooms:
            requirements.primary_use_case = 'Multipurpose'
        else:
            requirements.primary_use_case = 'Video Conferencing'

        return requirements

    def render_complete_form(self) -> Dict[str, Any]:
        """Render the complete ACIM-style questionnaire"""

        # Header
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
            <h1 style='color: white; margin: 0;'>🎯 ENHANCED BOQ QUESTIONNAIRE</h1>
            <p style='color: #e0e7ff; margin-top: 0.5rem; font-size: 1.1rem;'>
                Complete this form to receive a detailed AVIXA-compliant Bill of Quantities
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.info("**ℹ️ Instructions:** Fill out your details and room requirements below. The Allwave AV design team will generate a detailed programmed report with a Bill of Materials for each room type.")

        # Client Details
        client_details = self.render_client_details_section()

        # Room Type Selection
        selected_rooms = self.render_room_type_selection()

        # Store all responses
        all_responses = {
            'client_details': client_details,
            'selected_rooms': selected_rooms,
            'room_requirements': []
        }

        # Render questions for each selected room type
        if selected_rooms:
            st.markdown("---")
            st.markdown("## 📝 Room Requirements")
            st.markdown("Please provide details for each room type you selected:")

            for idx, room_type in enumerate(selected_rooms):
                with st.expander(f"**{idx+1}. {room_type}**", expanded=(idx == 0)):
                    st.markdown(f"*To help us design the most effective AV solution for your {room_type}, please provide the following details:*")
                    st.markdown("")

                    room_responses = self.render_room_questions(room_type, idx)

                    all_responses['room_requirements'].append({
                        'room_type': room_type,
                        'room_index': idx,
                        'responses': room_responses,
                        'room_spec_mapping': self._map_room_type_to_spec(room_type)
                    })

        return all_responses

    def validate_responses(self, all_responses: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate that all required fields are filled"""
        errors = []

        # Check client details
        client = all_responses['client_details']
        if not client.name:
            errors.append("Please enter your name")
        if not client.company_name:
            errors.append("Please enter your company name")
        if not client.email:
            errors.append("Please enter your email")
        if not client.company_location:
            errors.append("Please enter your company location")

        # Check room selection
        if not all_responses['selected_rooms']:
            errors.append("Please select at least one room type")

        # Check room responses
        for room_req in all_responses.get('room_requirements', []):
            room_type = room_req['room_type']
            responses = room_req['responses']

            # Check for room dimensions
            if 'extracted_dimensions' not in responses:
                errors.append(f"{room_type}: Please provide room dimensions in the format: Length x Width x Height (e.g., 20ft x 15ft x 9ft)")

        return (len(errors) == 0, errors)


# Main function to integrate with existing app
def show_smart_questionnaire_tab():
    """
    MAIN FUNCTION: Render the enhanced questionnaire tab in your app
    This replaces your old show_smart_questionnaire_tab function
    """

    # Initialize questionnaire
    questionnaire = EnhancedSmartQuestionnaire()

    # Benefits section
    st.markdown("### Why Use This Questionnaire?")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("⚡ **Faster**\nGenerate BOQs with guided questions")

    with col2:
        st.success("🎯 **More Accurate**\nRoom-specific questions ensure precision")

    with col3:
        st.warning("📊 **AVIXA Compliant**\nAll recommendations follow industry standards")

    st.markdown("---")

    # Render the complete form
    all_responses = questionnaire.render_complete_form()

    # Store in session state
    st.session_state.questionnaire_responses = all_responses

    st.markdown("---")

    # Action buttons
    col_generate, col_summary = st.columns([1, 1])

    with col_generate:
        if st.button("🚀 Generate BOQ from Questionnaire", type="primary", use_container_width=True):
            # Validate responses
            is_valid, errors = questionnaire.validate_responses(all_responses)

            if not is_valid:
                st.error("**Please complete all required fields:**")
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Convert to ClientRequirements
                client_requirements = questionnaire._convert_to_client_requirements(
                    all_responses['client_details'],
                    all_responses['selected_rooms'],
                    all_responses['room_requirements']
                )

                # Store in session state
                st.session_state.client_requirements = client_requirements
                st.session_state.questionnaire_room_data = all_responses['room_requirements']

                st.success("✅ Requirements captured! Ready to generate BOQ...")
                st.balloons()

                # Display next steps
                st.info("**Next Steps:**\n1. Go to the **'BOQ Generation'** tab\n2. Your room details and requirements are pre-filled\n3. Click **Generate BOQ** to create your Bill of Quantities")

                # Auto-switch to BOQ tab (optional)
                st.session_state.trigger_boq_generation = True

    with col_summary:
        if st.button("📄 Show Requirements Summary", use_container_width=True):
            if all_responses['room_requirements']:
                with st.expander("📋 Requirements Summary", expanded=True):
                    client = all_responses['client_details']
                    st.markdown(f"**Client:** {client.name} ({client.company_name})")
                    st.markdown(f"**Location:** {client.company_location}")
                    st.markdown(f"**Email:** {client.email}")
                    st.markdown("")

                    st.markdown(f"**Selected Rooms:** {len(all_responses['selected_rooms'])}")
                    for room_req in all_responses['room_requirements']:
                        st.markdown(f"- {room_req['room_type']}")
                        responses = room_req['responses']
                        if 'extracted_dimensions' in responses:
                            dims = responses['extracted_dimensions']
                            st.markdown(f"  - Dimensions: {dims['length']:.1f}ft × {dims['width']:.1f}ft × {dims['ceiling_height']:.1f}ft")
            else:
                st.warning("Please fill out the questionnaire first")
