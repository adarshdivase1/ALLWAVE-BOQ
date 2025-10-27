# components/acim_form_questionnaire.py
"""
ACIM Form Style Questionnaire System
Matches the exact structure and appearance of the web form at allwaveav.com/acim
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
class RoomRequirements:
    """Requirements for each room type"""
    room_type: str
    responses: Dict[str, Any]

class ACIMFormQuestionnaire:
    """
    ACIM Form Style Questionnaire matching allwaveav.com/acim
    """
    
    def __init__(self):
        self.room_types = self._get_room_types()
        self.questions_by_room_type = self._build_questions_by_room_type()
        
    def _get_room_types(self) -> List[str]:
        """Available room types"""
        return [
            "Conference/Meeting Room/Boardroom",
            "Experience Center",
            "Reception/Digital Signage",
            "Training Room",
            "Network Operations Center/Command Center",
            "Town Hall",
            "Auditorium"
        ]
    
    def _build_questions_by_room_type(self) -> Dict[str, List[Dict]]:
        """Build questions for each room type"""
        return {
            "Conference/Meeting Room/Boardroom": [
                {
                    'id': 'seating_layout',
                    'question': '1. What is the seating capacity, layout (e.g., square table, U-shaped table, theater style), and detailed dimensions of the room, including its length, breadth, and height?',
                    'type': 'text_area',
                    'placeholder': 'Enter room details...'
                },
                {
                    'id': 'solution_type',
                    'question': '2. Would you require a AV(Audio Visual) Solution for only Presentations or Video Collaboration (Teams/Zoom) as well for this meeting room?',
                    'type': 'text_area',
                    'placeholder': 'Enter your preference...'
                },
                {
                    'id': 'uc_platform',
                    'question': '3. Which UC platform does your organization currently use? (e.g., Zoom Rooms, Microsoft Teams Rooms, Google Meet, Cisco Webex, GoToMeeting, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter UC platform...'
                },
                {
                    'id': 'native_solution',
                    'question': '4. Would you require a Native Solution for simplified one-touch dialing via a touch panel mounted on the desk, or would you prefer to connect your laptop and use the meeting room\'s camera to facilitate the meeting with remote participants (e.g., via Teams, Zoom)?',
                    'type': 'text_area',
                    'placeholder': 'Enter your preference...'
                },
                {
                    'id': 'connectivity',
                    'question': '5. Do you require wired (e.g., HDMI) or wireless connectivity, and would you also need USB-C as an option?',
                    'type': 'text_area',
                    'placeholder': 'Enter connectivity requirements...'
                },
                {
                    'id': 'digital_whiteboard',
                    'question': '6. Would you like a digital whiteboard with streaming capabilities, such as Kaptivo or Logitech Scribe, for collaboration?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and details...'
                },
                {
                    'id': 'automation',
                    'question': '7. Do you want room automation for controlling AV systems, lighting, air conditioning, and blinds?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'room_scheduler',
                    'question': '8. Would you require a room scheduler outside the room that integrates with platforms like Microsoft 365 or Gmail?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No...'
                },
                {
                    'id': 'virtual_demo',
                    'question': '9. Would you be interested in scheduling a virtual demo to experience our AV solutions?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No...'
                },
                {
                    'id': 'acoustic_solutions',
                    'question': '10. Would you like more information about acoustic solutions to enhance the AV and video collaboration experience?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No...'
                },
                {
                    'id': 'budget',
                    'question': '11. What is your budget range for this project?',
                    'type': 'text_area',
                    'placeholder': 'Enter budget range...'
                },
                {
                    'id': 'documents',
                    'question': '12. Do you have any supporting documents, such as floor plans, reflected ceiling plans, or elevation drawings, to help us design the room effectively? If Yes, then please upload them for reference.',
                    'type': 'file_upload',
                    'help': 'file size limit: 2MB | file types supported: jpg | jpeg | gif | tiff | zip | gz | pdf | mp4 | xlsx | docx | pptx | xls | doc | ppt | csv | txt'
                }
            ],
            
            "Experience Center": [
                {
                    'id': 'business_outcome',
                    'question': '1. What is the intended business outcome of the Experience Center? Please provide detailed insights into the overall management goals and explain how the Experience Center will add value to your organization.',
                    'type': 'text_area',
                    'placeholder': 'Enter detailed business outcome...'
                },
                {
                    'id': 'room_dimensions',
                    'question': '2. Can you provide detailed room dimensions (length, breadth, height) and layout preferences (e.g., open space, structured zones)?',
                    'type': 'text_area',
                    'placeholder': 'Enter room dimensions and layout...'
                },
                {
                    'id': 'showcase_items',
                    'question': '3. What products, services, or solutions will be showcased in the Experience Center?',
                    'type': 'text_area',
                    'placeholder': 'Enter showcase items...'
                },
                {
                    'id': 'flexibility',
                    'question': '4. Will this space be flexible, allowing for changing product showcases? Will the showcase include both physical products and non-physical elements such as services or software solutions?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and details...'
                },
                {
                    'id': 'stakeholders',
                    'question': '5. Who are the key stakeholders or target audiences for the Experience Center (e.g., customers, partners, internal teams)?',
                    'type': 'text_area',
                    'placeholder': 'Enter stakeholders...'
                },
                {
                    'id': 'visitor_experience',
                    'question': '6. What type of experience do you want visitors to have (e.g., interactive, guided, self-serve)? How long will a typical walkthrough take?',
                    'type': 'text_area',
                    'placeholder': 'Enter experience type...'
                },
                {
                    'id': 'zones_flow',
                    'question': '7. Should the journey be structured into specific zones or flows (e.g., welcome area, product demonstration, innovation showcase)?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and zone details...'
                },
                {
                    'id': 'group_presentations',
                    'question': '8. Do you want the space to accommodate group presentations or one-on-one interactions?',
                    'type': 'text_area',
                    'placeholder': 'Enter preference...'
                },
                {
                    'id': 'av_equipment',
                    'question': '9. What types of AV equipment do you envision using (e.g., videowalls, touch screens, projection systems)?',
                    'type': 'text_area',
                    'placeholder': 'Enter AV equipment requirements...'
                },
                {
                    'id': 'video_conferencing',
                    'question': '10. Will the Experience Center be used for video conferencing or virtual demonstrations? Do you prefer wired or wireless connectivity for devices?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and connectivity preference...'
                },
                {
                    'id': 'budget',
                    'question': '11. What is the allocated budget for this project?',
                    'type': 'text_area',
                    'placeholder': 'Enter budget range...'
                },
                {
                    'id': 'timeline',
                    'question': '12. Do you have a preferred timeline for the design and implementation?',
                    'type': 'text_area',
                    'placeholder': 'Enter timeline...'
                },
                {
                    'id': 'documents',
                    'question': '13. Do you have any supporting materials (e.g., floor plans, reflected ceiling plans, or elevation drawings) that could assist in designing the Experience Center? Please upload them for reference.',
                    'type': 'file_upload',
                    'help': 'file size limit: 2MB | file types supported: jpg | jpeg | gif | tiff | zip | gz | pdf | mp4 | xlsx | docx | pptx | xls'
                }
            ],
            
            "Reception/Digital Signage": [
                {
                    'id': 'display_type',
                    'question': '1. What type of display would you prefer: a commercial display, video wall, or active LED?',
                    'type': 'text_area',
                    'placeholder': 'Enter display type preference...'
                },
                {
                    'id': 'room_dimensions',
                    'question': '2. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Enter room dimensions and features...'
                },
                {
                    'id': 'content_type',
                    'question': '3. What type of content will be showcased on the digital signage (e.g., welcome messages, event promotions, product launches, commercial broadcasts)',
                    'type': 'text_area',
                    'placeholder': 'Enter content types...'
                },
                {
                    'id': 'centralized_platform',
                    'question': '4. Do you require a centralized, web-based platform for remotely managing and pushing updates to the digital signage?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'locations_count',
                    'question': '5. How many locations or screens would need to be controlled?',
                    'type': 'text_area',
                    'placeholder': 'Enter number of locations/screens...'
                },
                {
                    'id': 'audio_solution',
                    'question': '6. Do you require an audio solution to complement the digital signage, such as background music or sound for videos?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and details...'
                },
                {
                    'id': 'audio_integration',
                    'question': '7. If yes, would you like the audio to integrate with the existing AV system in the space?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No...'
                },
                {
                    'id': 'budget',
                    'question': '8. What is your budget range for this project?',
                    'type': 'text_area',
                    'placeholder': 'Enter budget range...'
                },
                {
                    'id': 'pain_points',
                    'question': '9. Are there any specific challenges or pain points with your other current AV setup that we should address?',
                    'type': 'text_area',
                    'placeholder': 'Enter challenges/pain points...'
                },
                {
                    'id': 'documents',
                    'question': '10. Do you have any floor plans, reflected ceiling plans, elevations, or other documents that would help us design the solution more effectively? Please upload them here.',
                    'type': 'file_upload',
                    'help': 'file size limit: 2MB | file types supported: jpg | jpeg | gif | tiff | zip | gz | pdf | mp4 | xlsx | docx | pptx | xls | doc | ppt | csv | txt'
                }
            ],
            
            "Training Room": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Enter room dimensions and features...'
                },
                {
                    'id': 'seating_info',
                    'question': '2. How many seats are there in the room, and what is the seating orientation towards the trainer? (e.g., classroom, theater, U-shaped)',
                    'type': 'text_area',
                    'placeholder': 'Enter seating details...'
                },
                {
                    'id': 'connectivity',
                    'question': '3. Are you looking for wired and wireless connectivity from both the podium and the overall seating area?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'remote_training',
                    'question': '4. Will this training room be used for remote training via platforms like Microsoft Teams, Zoom, WebEx, GoToMeeting, etc.?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and platform details...'
                },
                {
                    'id': 'camera_requirements',
                    'question': '5. Based on the size of the room, would you require a single camera to capture the trainer, or would you need multiple cameras to capture the trainer and the audience?',
                    'type': 'text_area',
                    'placeholder': 'Enter camera requirements...'
                },
                {
                    'id': 'camera_features',
                    'question': '6. If multiple cameras are required, would you like features such as speech tracking and auto-focus based on predefined presets?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and feature requirements...'
                },
                {
                    'id': 'digital_whiteboard',
                    'question': '7. Would you require a digital whiteboard collaboration tool with streaming options, such as Kaptivo or Logitech Scribe?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No...'
                },
                {
                    'id': 'automation',
                    'question': '8. Would you need automation in the room for controlling Audio Visual equipment, lights, air conditioning, blinds, etc.?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'budget',
                    'question': '9. What is your budget range for this project?',
                    'type': 'text_area',
                    'placeholder': 'Enter budget range...'
                },
                {
                    'id': 'live_streaming',
                    'question': '10. Would you need live streaming or corporate broadcasting for distance learning on platforms like corporate networks, YouTube Live, or Facebook Live?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and platform preferences...'
                },
                {
                    'id': 'documents',
                    'question': '11. Are there any additional documents (floor plans, reflected ceiling plans, elevations, etc.) that would help us design your room more effectively? Please upload them here.',
                    'type': 'file_upload',
                    'help': 'file size limit: 2MB | file types supported: jpg | jpeg | gif | tiff | zip | gz | pdf | mp4 | xlsx | docx | pptx | xls | doc | ppt | csv | txt'
                }
            ],
            
            "Network Operations Center/Command Center": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Enter room dimensions and features...'
                },
                {
                    'id': 'users_count',
                    'question': '2. How many users will be viewing the screen? This information will help us calculate the number of screens and windows required.',
                    'type': 'text_area',
                    'placeholder': 'Enter number of users...'
                },
                {
                    'id': 'connectivity',
                    'question': '3. Are you looking for wired and wireless connectivity from both the podium and the overall seating area?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'display_preference',
                    'question': '4. Do you have a preference for video walls, LED video walls, active LEDs, or projection for this room?',
                    'type': 'text_area',
                    'placeholder': 'Enter display preference...'
                },
                {
                    'id': 'source_inputs',
                    'question': '5. How many source inputs will be needed in this room? Should each user have their own input, or would it be from a central repository?',
                    'type': 'text_area',
                    'placeholder': 'Enter source input requirements...'
                },
                {
                    'id': 'digital_whiteboard',
                    'question': '6. Would you require a digital whiteboard collaboration tool with streaming options, such as Kaptivo or Logitech Scribe?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No...'
                },
                {
                    'id': 'program_audio',
                    'question': '7. Would you require program audio for this room? (Will this room also be used for regular presentations/training?)',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and usage details...'
                },
                {
                    'id': 'encoder_decoder',
                    'question': '8. Do you have a preference for hardware-based encoder/decoder solutions, or would you prefer a software-based solution that can be loaded on your IT infrastructure with redundancy?',
                    'type': 'text_area',
                    'placeholder': 'Enter preference...'
                },
                {
                    'id': 'automation',
                    'question': '9. Would you need automation in the room for controlling Audio Visual equipment, lights, air conditioning, blinds, etc.?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'live_streaming',
                    'question': '10. Would you need live streaming or corporate broadcasting for distance learning on platforms like corporate networks, YouTube Live, or Facebook Live?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and platform preferences...'
                },
                {
                    'id': 'budget',
                    'question': '11. What is your budget range for this project?',
                    'type': 'text_area',
                    'placeholder': 'Enter budget range...'
                },
                {
                    'id': 'documents',
                    'question': '12. Are there any additional documents (floor plans, reflected ceiling plans, elevations, etc.) that would help us design your room more effectively? Please upload them here.',
                    'type': 'file_upload',
                    'help': 'file size limit: 2MB | file types supported: jpg | jpeg | gif | tiff | zip | gz | pdf | mp4 | xlsx | docx | pptx | xls | doc | ppt | csv | txt'
                }
            ],
            
            "Town Hall": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Enter room dimensions and features...'
                },
                {
                    'id': 'seating_info',
                    'question': '2. How many seats are there in the room, and what is the seating orientation towards the trainer? (e.g., classroom, theater, U-shaped)',
                    'type': 'text_area',
                    'placeholder': 'Enter seating details...'
                },
                {
                    'id': 'connectivity',
                    'question': '3. Are you looking for wired and wireless connectivity from both the podium and the overall seating area?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'usage_frequency',
                    'question': '4. How often will the Town Hall be used? (e.g., Once a week, Once a month, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter usage frequency...'
                },
                {
                    'id': 'primary_users',
                    'question': '5. Who will be the primary users of the Town Hall space? (e.g., employees, management, external guests, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter primary users...'
                },
                {
                    'id': 'uc_platform',
                    'question': '6. Which UC (Unified Collaboration) platform do you currently use? (e.g., Zoom Rooms, Microsoft Rooms, Google Meet, GoToMeeting, Cisco WebEx, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter UC platform...'
                },
                {
                    'id': 'digital_whiteboard',
                    'question': '7. Would you require a digital whiteboard collaboration tool with streaming options, such as Kaptivo or Logitech Scribe?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No...'
                },
                {
                    'id': 'camera_requirements',
                    'question': '8. Based on the size of the room, would you require a single camera to capture the presenter, or would you need multiple cameras to capture both presenters and the audience?',
                    'type': 'text_area',
                    'placeholder': 'Enter camera requirements...'
                },
                {
                    'id': 'camera_features',
                    'question': '9. If you require multiple cameras, would you like features such as speech tracking and auto-focus based on presets?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and feature requirements...'
                },
                {
                    'id': 'program_audio',
                    'question': '10. Would you require program audio for this room? (Will this room also be used for regular presentations/training?)',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and usage details...'
                },
                {
                    'id': 'automation',
                    'question': '11. Would you need automation in the room for controlling Audio Visual equipment, lights, air conditioning, blinds, etc.?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'audio_performance',
                    'question': '12. Town halls are often conducted in reverberant spaces (acoustically challenging). If high-performance audio is crucial, we recommend using high-performance or digitally scalable columns. Please share your thoughts on this approach.',
                    'type': 'text_area',
                    'placeholder': 'Enter your thoughts on audio requirements...'
                },
                {
                    'id': 'budget',
                    'question': '13. What is your budget range for this project?',
                    'type': 'text_area',
                    'placeholder': 'Enter budget range...'
                },
                {
                    'id': 'documents',
                    'question': '14. Are there any additional documents (floor plans, reflected ceiling plans, elevations, etc.) that would help us design your room more effectively? Please upload them here.',
                    'type': 'file_upload',
                    'help': 'file size limit: 2MB | file types supported: jpg | jpeg | gif | tiff | zip | gz | pdf | mp4 | xlsx | docx | pptx | xls | doc | ppt | csv | txt'
                }
            ],
            
            "Auditorium": [
                {
                    'id': 'room_dimensions',
                    'question': '1. Could you provide detailed room dimensions (length, breadth, and height) and any existing architectural features we need to consider?',
                    'type': 'text_area',
                    'placeholder': 'Enter room dimensions and features...'
                },
                {
                    'id': 'seating_info',
                    'question': '2. How many seats are there in the room, and what is the seating orientation towards the trainer? (e.g., classroom, theater, U-shaped)',
                    'type': 'text_area',
                    'placeholder': 'Enter seating details...'
                },
                {
                    'id': 'connectivity',
                    'question': '3. Are you looking for wired and wireless connectivity from both the podium and the overall seating area?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'usage_frequency',
                    'question': '4. How often will the Auditorium be used? (e.g., Once a week, Once a month, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter usage frequency...'
                },
                {
                    'id': 'primary_applications',
                    'question': '5. What are the primary applications for this auditorium? (e.g., presentations, distance learning, entertainment, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter primary applications...'
                },
                {
                    'id': 'vc_solution',
                    'question': '6. Would you require a Video Conferencing solution for Native Solution for simplified one-touch dialing via a touch panel mounted on a desk? Or would you prefer to connect your laptop and use the camera of the meeting room to drive the meeting (e.g. Teams, Zoom)',
                    'type': 'text_area',
                    'placeholder': 'Enter preference...'
                },
                {
                    'id': 'uc_platform',
                    'question': '7. Which UC (Unified Collaboration) platform do you currently use? (e.g., Zoom Rooms, Microsoft Rooms, Google Meet, GoToMeeting, Cisco WebEx, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter UC platform...'
                },
                {
                    'id': 'microphone_preferences',
                    'question': '8. What type of microphones are preferred for onstage and offstage use? (e.g., lapel, wireless handheld, boundary, etc.)',
                    'type': 'text_area',
                    'placeholder': 'Enter microphone preferences...'
                },
                {
                    'id': 'camera_requirements',
                    'question': '9. Based on the size of the room, would you require a single camera to capture the presenter, or would you need multiple cameras to capture both presenters and the audience?',
                    'type': 'text_area',
                    'placeholder': 'Enter camera requirements...'
                },
                {
                    'id': 'camera_features',
                    'question': '10. If you require multiple cameras, would you like features such as speech tracking and auto-focus based on presets?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and feature requirements...'
                },
                {
                    'id': 'live_streaming',
                    'question': '11. Would you require live streaming, corporate broadcast, or distance learning on a corporate network, YouTube Live, or Facebook Live?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and platform preferences...'
                },
                {
                    'id': 'automation',
                    'question': '12. Would you need automation in the room for controlling Audio Visual equipment, lights, air conditioning, blinds, etc.?',
                    'type': 'text_area',
                    'placeholder': 'Yes/No and requirements...'
                },
                {
                    'id': 'audio_performance',
                    'question': '13. Town halls are often conducted in reverberant spaces (acoustically challenging). If high-performance audio is crucial, we recommend using high-performance or digitally scalable columns. Please share your thoughts on this approach.',
                    'type': 'text_area',
                    'placeholder': 'Enter your thoughts on audio requirements...'
                },
                {
                    'id': 'budget',
                    'question': '14. What is your budget range for this project?',
                    'type': 'text_area',
                    'placeholder': 'Enter budget range...'
                },
                {
                    'id': 'documents',
                    'question': '15. Are there any additional documents (floor plans, reflected ceiling plans, elevations, etc.) that would help us design your room more effectively? Please upload them here.',
                    'type': 'file_upload',
                    'help': 'file size limit: 2MB | file types supported: jpg | jpeg | gif | tiff | zip | gz | pdf | mp4 | xlsx | docx | pptx | xls | doc | ppt | csv | txt'
                }
            ]
        }
    
    def render_client_details_section(self) -> ClientDetails:
        """Render the 'Your Details' section matching web form"""
        st.markdown("## Your Details")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Name:", key="client_name")
            company_location = st.text_input("Company Location", key="client_location")
            email = st.text_input("Email", key="client_email")
        
        with col2:
            company_name = st.text_input("Company Name:", key="client_company")
            designation = st.text_input("Designation", key="client_designation")
            mobile = st.text_input("Mobile", key="client_mobile")
        
        return ClientDetails(
            name=name,
            company_name=company_name,
            company_location=company_location,
            designation=designation,
            email=email,
            mobile=mobile
        )
    
    def render_room_type_selection(self) -> List[str]:
        """Render room type selection matching web form"""
        st.markdown("---")
        st.markdown("## What kind of room are you planning to design?")
        st.markdown("")
        
        selected_rooms = st.multiselect(
            "Select one or more room types:",
            options=self.room_types,
            key="selected_room_types",
            help="You can select multiple room types if you have different spaces to design"
        )
        
        return selected_rooms
    
    def render_room_questions(self, room_type: str) -> Dict[str, Any]:
        """Render questions for a specific room type"""
        st.markdown("---")
        st.markdown(f"## ACIM Form for {room_type}")
        st.markdown("To help us design the most effective AV solution for your space, kindly provide the following details:")
        st.markdown("")
        
        questions = self.questions_by_room_type.get(room_type, [])
        responses = {}
        
        for question in questions:
            q_id = question['id']
            q_text = question['question']
            q_type = question['type']
            q_placeholder = question.get('placeholder', '')
            q_help = question.get('help', '')
            
            if q_type == 'text_area':
                response = st.text_area(
                    q_text,
                    placeholder=q_placeholder,
                    key=f"{room_type}_{q_id}",
                    height=100
                )
                responses[q_id] = response
                
            elif q_type == 'file_upload':
                st.markdown(q_text)
                uploaded_file = st.file_uploader(
                    "Choose file",
                    type=['jpg', 'jpeg', 'gif', 'tiff', 'zip', 'gz', 'pdf', 'mp4', 
                          'xlsx', 'docx', 'pptx', 'xls', 'doc', 'ppt', 'csv', 'txt'],
                    key=f"{room_type}_{q_id}",
                    help=q_help
                )
                responses[q_id] = uploaded_file
                
                if q_help:
                    st.caption(q_help)
        
        return responses
    
    def render_complete_form(self) -> Dict[str, Any]:
        """Render the complete ACIM form"""
        # Custom CSS to match web form styling
        st.markdown("""
        <style>
        .main {
            background-color: #f8f9fa;
        }
        h2 {
            color: #2c3e50;
            font-weight: 600;
            margin-bottom: 1.5rem;
        }
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            background-color: #e9ecef;
            border: none;
            border-radius: 4px;
            padding: 12px;
        }
        .stTextArea > div > div > textarea {
            min-height: 100px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Render client details
        client_details = self.render_client_details_section()
        
        # Render room type selection
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
            st.markdown("## Room Requirements")
            
            for idx, room_type in enumerate(selected_rooms):
                with st.expander(f"📋 {room_type}", expanded=(idx == 0)):
                    room_responses = self.render_room_questions(room_type)
                    all_responses['room_requirements'].append({
                        'room_type': room_type,
                        'responses': room_responses
                    })
        
        return all_responses
    
    def generate_summary_report(self, all_responses: Dict[str, Any]) -> str:
        """Generate summary report from form responses"""
        report = ["=" * 80]
        report.append("ACIM FORM SUBMISSION SUMMARY")
        report.append("=" * 80)
        report.append("")
        
        # Client Details
        client = all_responses['client_details']
        report.append("CLIENT DETAILS")
        report.append("-" * 80)
        report.append(f"Name:              {client.name}")
        report.append(f"Company:           {client.company_name}")
        report.append(f"Location:          {client.company_location}")
        report.append(f"Designation:       {client.designation}")
        report.append(f"Email:             {client.email}")
        report.append(f"Mobile:            {client.mobile}")
        report.append("")
        
        # Selected Room Types
        report.append("SELECTED ROOM TYPES")
        report.append("-" * 80)
        for room_type in all_responses['selected_rooms']:
            report.append(f"  • {room_type}")
        report.append("")
        
        # Room Requirements
        for room_req in all_responses['room_requirements']:
            report.append("=" * 80)
            report.append(f"ROOM TYPE: {room_req['room_type']}")
            report.append("=" * 80)
            report.append("")
            
            for q_id, response in room_req['responses'].items():
                if response and not str(response).startswith("<"):  # Skip file uploads in text
                    question_text = self._get_question_text(room_req['room_type'], q_id)
                    report.append(question_text)
                    if isinstance(response, str) and '\n' in response:
                        report.append("  " + response.replace('\n', '\n  '))
                    else:
                        report.append(f"  {response}")
                    report.append("")
        
        return "\n".join(report)
    
    def _get_question_text(self, room_type: str, q_id: str) -> str:
        """Get question text for a given question ID"""
        questions = self.questions_by_room_type.get(room_type, [])
        for q in questions:
            if q['id'] == q_id:
                return q['question']
        return q_id
    
    def export_to_json(self, all_responses: Dict[str, Any]) -> str:
        """Export responses to JSON format"""
        # Convert dataclass to dict
        export_data = {
            'client_details': asdict(all_responses['client_details']),
            'selected_rooms': all_responses['selected_rooms'],
            'room_requirements': all_responses['room_requirements']
        }
        return json.dumps(export_data, indent=2)


# Main function to integrate with Streamlit app
def show_acim_form_questionnaire():
    """Main function to display ACIM form in Streamlit"""
    
    # Initialize form
    acim_form = ACIMFormQuestionnaire()
    
    # Add header with branding
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0; text-align: center;'>
            ACIM Form - AV Solution Questionnaire
        </h1>
        <p style='color: white; text-align: center; margin-top: 0.5rem; opacity: 0.9;'>
            Complete this form to receive a detailed programmed report with Bill of Materials
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background-color: #fff3cd; border-left: 4px solid #ffc107; 
                padding: 1rem; margin-bottom: 2rem; border-radius: 4px;'>
        <p style='margin: 0; color: #856404;'>
            <b>ℹ️ Instructions:</b> As a follow-up, the Allwave AV design team will send a 
            detailed programmed report with a Bill of Materials for each room type and 
            schedule a Teams or a Zoom call thereafter.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- START: CHANGE 4 ---
    # ✅ NEW: NLP Parser Integration
    with st.expander("💡 Smart Requirements Parser", expanded=False):
        st.markdown("Paste your client's requirements and we'll auto-fill the form.")
        
        nlp_input = st.text_area(
            "Paste requirements here:",
            placeholder="e.g., We need a 12-person boardroom with dual 85\" Samsung displays...",
            height=150,
            key="nlp_input_acim"
        )
        
        if st.button("🔍 Parse Requirements", key="parse_nlp_btn"):
            try:
                from components.nlp_requirements_parser import NLPRequirementsParser
                
                parser = NLPRequirementsParser()
                parsed = parser.parse(nlp_input)
                
                if parsed.get('confidence_score', 0) > 0.3:
                    st.success(f"✅ Parsed with {parsed['confidence_score']*100:.0f}% confidence. Form will be pre-filled.")
                    
                    # Store parsed data
                    st.session_state.nlp_parsed_data = parsed
                    
                    # Show summary
                    summary = parser.generate_summary_report(parsed)
                    st.code(summary)
                    st.rerun() # Rerun to apply pre-fill
                else:
                    st.warning("Could not parse requirements reliably")
            except ImportError:
                st.error("Error: `nlp_requirements_parser` component not found.")
            except Exception as e:
                st.error(f"An error occurred during parsing: {e}")

    # ✅ NEW: Pre-fill form from parsed data
    if 'nlp_parsed_data' in st.session_state:
        parsed = st.session_state.nlp_parsed_data
        
        # Pre-fill client details
        if parsed.get('client_preferences'):
            prefs = parsed['client_preferences']
            # Set session state keys that match the st.text_input keys in render_client_details_section
            if 'name' in prefs:
                st.session_state.client_name = prefs.get('name', '')
            if 'company' in prefs:
                st.session_state.client_company = prefs.get('company', '')
        
        # Auto-detect quantities
        if 'quantities' in parsed:
            if 'displays' in parsed['quantities']:
                st.info(f"💡 Detected: {parsed['quantities']['displays']} displays")
        
        # Auto-select room type
        if 'room_type' in parsed:
            nlp_room = parsed['room_type'].lower()
            form_rooms = acim_form.room_types # acim_form is already instantiated
            matched_room = None
            for room in form_rooms:
                if nlp_room in room.lower():
                    matched_room = room
                    break
            if matched_room:
                # Key from render_room_type_selection
                st.session_state.selected_room_types = [matched_room]
                st.info(f"💡 Auto-selected room type: {matched_room}")
        
        # Delete the parsed data so it doesn't pre-fill again after manual changes
        del st.session_state.nlp_parsed_data
    # --- END: CHANGE 4 ---
    
    # Render the complete form
    all_responses = acim_form.render_complete_form()
    
    # Store in session state
    st.session_state.acim_form_responses = all_responses
    
    # Action buttons
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        if st.button("🚀 Submit Form & Generate BOQ", type="primary", use_container_width=True):
            # Validate required fields
            if not all_responses['client_details'].name:
                st.error("❌ Please enter your name")
            elif not all_responses['client_details'].email:
                st.error("❌ Please enter your email")
            elif not all_responses['selected_rooms']:
                st.error("❌ Please select at least one room type")
            else:
                st.success("✅ Form submitted successfully!")
                st.balloons()
                st.session_state.trigger_boq_generation = True
                
                # Show success message
                st.info("""
                **📧 What happens next?**
                - Our design team will review your requirements
                - You'll receive a detailed programmed report with Bill of Materials
                - We'll schedule a Teams/Zoom call to discuss the solution
                """)
    
    with col2:
        if st.button("📄 Generate Summary Report", use_container_width=True):
            if all_responses['selected_rooms']:
                summary = acim_form.generate_summary_report(all_responses)
                
                with st.expander("📋 Form Summary", expanded=True):
                    st.text(summary)
                    
                    # Download buttons
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.download_button(
                            "💾 Download as TXT",
                            data=summary,
                            file_name="acim_form_summary.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                    with col_b:
                        json_data = acim_form.export_to_json(all_responses)
                        st.download_button(
                            "💾 Download as JSON",
                            data=json_data,
                            file_name="acim_form_data.json",
                            mime="application/json",
                            use_container_width=True
                        )
            else:
                st.warning("⚠️ Please select at least one room type first")
    
    with col3:
        if st.button("🔄 Clear Form", use_container_width=True):
            # Clear session state
            for key in list(st.session_state.keys()):
                if key.startswith('client_') or key.startswith('selected_') or 'acim' in key or 'nlp' in key:
                    del st.session_state[key]
            st.rerun()
    
    # Show room count summary
    if all_responses['selected_rooms']:
        st.markdown("---")
        st.markdown("### 📊 Project Summary")
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Room Types Selected", len(all_responses['selected_rooms']))
        with col_b:
            total_questions = sum(
                len([r for r in req['responses'].values() if r]) 
                for req in all_responses['room_requirements']
            )
            st.metric("Questions Answered", total_questions)
        with col_c:
            completion = (total_questions / (len(all_responses['selected_rooms']) * 12) * 100) if all_responses['selected_rooms'] else 0
            st.metric("Completion", f"{completion:.0f}%")


# If running standalone for testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="ACIM Form - AV Solution Questionnaire",
        page_icon="🎬",
        layout="wide"
    )
    show_acim_form_questionnaire()
