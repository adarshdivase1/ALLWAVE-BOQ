# components/smart_questionnaire.py
"""
Smart BOQ Questionnaire System
Replaces scattered inputs with structured questions to gather all necessary information
"""

import streamlit as st
from typing import Dict, List, Any
from dataclasses import dataclass, asdict
import json

@dataclass
class ClientRequirements:
    """Structured client requirements from questionnaire"""
    # Project Basics
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
    
    # NEW: AVIXA-specific requirements
    avixa_display_sizing: str = "AVIXA DISCAS Recommended (Optimal viewing)"
    performance_verification_required: bool = False
    target_sti_level: str = "Standard (STI ≥ 0.60)"
    
    # Advanced Requirements
    additional_requirements: str
    
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


class SmartQuestionnaire:
    """
    Intelligent questionnaire that adapts based on room type and previous answers
    """
    
    def __init__(self):
        self.questions = self._build_question_tree()
        self.responses = {}
        
    def _build_question_tree(self) -> Dict[str, Any]:
        """Build comprehensive question structure"""
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
                'title': '📹 Video Conferencing Requirements',
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
                            'room_count': [1, 2, 3, 4, 5]  # Small projects
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
        st.markdown("## 🎯 Smart BOQ Questionnaire")
        st.markdown("Please answer the following questions to generate an optimized, AVIXA-compliant Bill of Quantities.")
        st.markdown("---")
        
        responses = {}
        
        # Progress tracking
        total_questions = sum(
            len(section['questions']) 
            for section in self.questions.values()
        )
        questions_answered = 0
        
        for section_key, section in self.questions.items():
            with st.expander(f"**{section['title']}**", expanded=(section_key == 'basic_info')):
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
            camera_type_preference=responses.get('camera_type_preference', 'All-in-One Video Bar (Recommended for small/medium rooms)'),
            auto_tracking_needed=responses.get('auto_tracking_needed', False),
            
            audio_brand_preference=responses.get('audio_brand_preference', 'No Preference'),
            microphone_type=responses.get('microphone_type', 'Table/Boundary Microphones'),
            ceiling_vs_table_audio=responses.get('ceiling_vs_table_audio', 'Integrated in Video Bar'),
            voice_reinforcement_needed=responses.get('voice_reinforcement_needed', False),
            
            control_brand_preference=responses.get('control_brand_preference', 'Native Platform Control (Teams Rooms/Zoom Rooms)'),
            wireless_presentation_needed=responses.get('wireless_presentation_needed', True),
            room_scheduling_needed=responses.get('room_scheduling_needed', False),
            lighting_control_integration=responses.get('lighting_control_integration', False),
            
            existing_network_capable=responses.get('existing_network_capable', True),
            power_infrastructure_adequate=responses.get('power_infrastructure_adequate', False),
            cable_management_type=responses.get('cable_management_type', 'In-Wall/Conduit (Professional)'),
            
            ada_compliance_required=responses.get('ada_compliance_required', False),
            recording_capability_needed=responses.get('recording_capability_needed', False),
            streaming_capability_needed=responses.get('streaming_capability_needed', False),
            
            # NEW: AVIXA requirements
            avixa_display_sizing=responses.get('avixa_display_sizing', 'AVIXA DISCAS Recommended (Optimal viewing)'),
            performance_verification_required=responses.get('performance_verification_required', False),
            target_sti_level=responses.get('target_sti_level', 'Standard (STI ≥ 0.60)'),
            
            additional_requirements=responses.get('additional_requirements', '')
        )
    
    def generate_summary_report(self, requirements: ClientRequirements) -> str:
        """Generate human-readable summary of requirements"""
        report = ["=== PROJECT REQUIREMENTS SUMMARY ===\n"]
        
        report.append(f"**Project Type:** {requirements.project_type}")
        report.append(f"**Number of Rooms:** {requirements.room_count}")
        report.append(f"**Primary Use:** {requirements.primary_use_case}")
        report.append(f"**Budget Level:** {requirements.budget_level}\n")
        
        report.append("**Display System:**")
        report.append(f"  • Brand Preference: {requirements.display_brand_preference}")
        report.append(f"  • Size Strategy: {requirements.display_size_preference}")
        if requirements.dual_display_needed:
            report.append(f"  • ✅ Dual displays required")
        if requirements.interactive_display_needed:
            report.append(f"  • ✅ Interactive/touch capability required\n")
        
        report.append("**Video Conferencing:**")
        report.append(f"  • Platform: {requirements.vc_platform}")
        report.append(f"  • Equipment Brand: {requirements.vc_brand_preference}")
        report.append(f"  • Camera System: {requirements.camera_type_preference}")
        if requirements.auto_tracking_needed:
            report.append(f"  • ✅ Auto-tracking enabled\n")
        
        report.append("**Audio System:**")
        report.append(f"  • Brand Preference: {requirements.audio_brand_preference}")
        report.append(f"  • Microphone Type: {requirements.microphone_type}")
        report.append(f"  • Speaker Placement: {requirements.ceiling_vs_table_audio}")
        if requirements.voice_reinforcement_needed:
            report.append(f"  • ✅ Voice reinforcement system included\n")
        
        report.append("**Control & Integration:**")
        report.append(f"  • Control System: {requirements.control_brand_preference}")
        if requirements.wireless_presentation_needed:
            report.append(f"  • ✅ Wireless presentation (BYOD)")
        if requirements.room_scheduling_needed:
            report.append(f"  • ✅ Room scheduling displays")
        if requirements.lighting_control_integration:
            report.append(f"  • ✅ Lighting control integration\n")
        
        report.append("**Special Requirements:**")
        if requirements.ada_compliance_required:
            report.append(f"  • ✅ ADA compliance")
        if requirements.recording_capability_needed:
            report.append(f"  • ✅ Recording capability")
        if requirements.streaming_capability_needed:
            report.append(f"  • ✅ Live streaming capability")
        
        if requirements.additional_requirements:
            report.append(f"\n**Additional Notes:**")
            report.append(f"{requirements.additional_requirements}")
        
        return "\n".join(report)


# Integration function for existing app
def show_smart_questionnaire_tab():
    """Render questionnaire tab in main app"""
    questionnaire = SmartQuestionnaire()
    
    st.markdown("### Why Use the Smart Questionnaire?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("⚡ **Faster**\nGenerate BOQs 10x faster with optimized queries")
    with col2:
        st.success("🎯 **More Accurate**\nGuided questions ensure nothing is missed")
    with col3:
        st.warning("📊 **AVIXA Compliant**\nAll recommendations follow industry standards")
    
    st.markdown("---")
    
    # Render questionnaire
    responses = questionnaire.render_questionnaire()
    
    # Store responses in session state
    st.session_state.questionnaire_responses = responses
    
    st.markdown("---")
    
    # Generate button
    col_generate, col_summary = st.columns([1, 2])
    
    with col_generate:
        if st.button("🚀 Generate BOQ from Questionnaire", type="primary", use_container_width=True):
            # Convert to structured requirements
            requirements = questionnaire.convert_to_client_requirements(responses)
            st.session_state.client_requirements = requirements
            
            st.success("✅ Requirements captured! Generating BOQ...")
            st.balloons()
            
            # This will trigger BOQ generation in the main flow
            st.session_state.trigger_boq_generation = True
    
    with col_summary:
        if st.button("📄 Show Requirements Summary", use_container_width=True):
            requirements = questionnaire.convert_to_client_requirements(responses)
            summary = questionnaire.generate_summary_report(requirements)
            
            with st.expander("📋 Requirements Summary", expanded=True):
                st.code(summary, language=None)
                
                # Export option
                st.download_button(
                    "💾 Export Summary",
                    data=summary,
                    file_name="project_requirements.txt",
                    mime="text/plain"
                )
