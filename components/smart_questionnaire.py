# NEW FILE: components/smart_questionnaire.py

import streamlit as st
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Question:
    id: str
    text: str
    type: str  # 'single_choice', 'multi_choice', 'numeric', 'text', 'brand_select'
    options: Optional[List[str]] = None
    depends_on: Optional[Dict] = None  # Conditional logic
    help_text: Optional[str] = None
    required: bool = True
    icon: str = "❓"

class AVQuestionnaire:
    """Interactive questionnaire that adapts based on user responses"""
    
    def __init__(self):
        self.questions = self._build_question_tree()
        self.responses = {}
    
    def _build_question_tree(self) -> List[Question]:
        """Define all questions in logical order"""
        return [
            # ===== SECTION 1: PROJECT BASICS =====
            Question(
                id="project_type",
                text="What type of space are you designing?",
                type="single_choice",
                options=[
                    "Corporate Meeting Room",
                    "Executive Boardroom",
                    "Training/Classroom",
                    "Auditorium/Event Space",
                    "Huddle/Collaboration Space",
                    "Video Production Studio",
                    "Telepresence Suite",
                    "Multi-Purpose Room"
                ],
                help_text="This determines the base equipment package",
                icon="🏢"
            ),
            
            Question(
                id="room_size_known",
                text="Do you know the exact room dimensions?",
                type="single_choice",
                options=["Yes, I have exact measurements", "No, but I know approximate size", "I need help determining this"],
                icon="📏"
            ),
            
            # Conditional: Only show if room_size_known == "Yes"
            Question(
                id="room_dimensions",
                text="Enter room dimensions (in feet)",
                type="numeric",
                depends_on={"room_size_known": "Yes, I have exact measurements"},
                help_text="Length × Width × Height",
                icon="📐"
            ),
            
            Question(
                id="participant_count",
                text="How many people will typically use this space?",
                type="single_choice",
                options=["2-4", "5-8", "9-16", "17-30", "30+"],
                icon="👥"
            ),
            
            # ===== SECTION 2: PRIMARY USE CASE =====
            Question(
                id="primary_use",
                text="What will be the PRIMARY use of this room?",
                type="single_choice",
                options=[
                    "Video Conferencing (Teams/Zoom meetings)",
                    "Presentations (Screen sharing, training)",
                    "Collaboration (Whiteboarding, brainstorming)",
                    "Hybrid Events (In-person + remote attendees)",
                    "Recording/Broadcasting",
                    "Multiple uses (equally important)"
                ],
                help_text="We'll optimize the design for this use case",
                icon="🎯"
            ),
            
            Question(
                id="video_conf_frequency",
                text="How often will you use video conferencing?",
                type="single_choice",
                options=["Daily (primary use)", "Weekly", "Occasionally", "Rarely/Never"],
                depends_on={"primary_use": ["Video Conferencing (Teams/Zoom meetings)", "Hybrid Events (In-person + remote attendees)"]},
                icon="📹"
            ),
            
            # ===== SECTION 3: DISPLAY PREFERENCES =====
            Question(
                id="display_preference",
                text="What type of display do you prefer?",
                type="single_choice",
                options=[
                    "Single Large Display (65-98 inches)",
                    "Dual Displays (for content + people)",
                    "Interactive Touch Display",
                    "Projector + Screen",
                    "LED Video Wall",
                    "Not sure - recommend for me"
                ],
                icon="🖥️"
            ),
            
            Question(
                id="display_brand_preference",
                text="Do you have a preferred display brand?",
                type="brand_select",
                options=["Samsung", "LG", "Sony", "NEC", "Sharp", "No preference"],
                required=False,
                icon="🏷️"
            ),
            
            # ===== SECTION 4: VIDEO SYSTEM =====
            Question(
                id="camera_requirements",
                text="What camera features are important to you?",
                type="multi_choice",
                options=[
                    "Auto-framing (camera follows speakers)",
                    "Speaker tracking",
                    "Multiple camera angles",
                    "4K resolution",
                    "Low-light performance",
                    "Privacy shutter",
                    "Basic quality is fine"
                ],
                help_text="Select all that apply",
                icon="📷"
            ),
            
            Question(
                id="vc_platform",
                text="Which video conferencing platform do you primarily use?",
                type="single_choice",
                options=[
                    "Microsoft Teams",
                    "Zoom",
                    "Google Meet",
                    "Cisco Webex",
                    "Multiple platforms (need flexibility)",
                    "Other/Not sure"
                ],
                depends_on={"video_conf_frequency": ["Daily (primary use)", "Weekly"]},
                icon="💻"
            ),
            
            Question(
                id="vc_brand_preference",
                text="Preferred video conferencing equipment brand?",
                type="brand_select",
                options=["Poly", "Cisco", "Logitech", "Yealink", "Crestron", "Neat", "No preference"],
                required=False,
                depends_on={"video_conf_frequency": ["Daily (primary use)", "Weekly"]},
                icon="🏷️"
            ),
            
            # ===== SECTION 5: AUDIO SYSTEM =====
            Question(
                id="audio_priority",
                text="How important is audio quality for this room?",
                type="single_choice",
                options=[
                    "Critical - Executive/client-facing",
                    "Very Important - Daily meetings",
                    "Standard - Basic conferencing needs",
                    "Not a priority"
                ],
                icon="🔊"
            ),
            
            Question(
                id="audio_features",
                text="What audio features do you need?",
                type="multi_choice",
                options=[
                    "Echo cancellation",
                    "Noise suppression",
                    "Voice reinforcement (amplification)",
                    "Wireless microphones",
                    "Ceiling audio (clean aesthetic)",
                    "Table microphones (best performance)",
                    "Recording capability",
                    "Basic conferencing audio"
                ],
                icon="🎤"
            ),
            
            Question(
                id="audio_brand_preference",
                text="Preferred audio equipment brand?",
                type="brand_select",
                options=["Shure", "Biamp", "QSC", "Sennheiser", "Bose", "No preference"],
                required=False,
                icon="🏷️"
            ),
            
            # ===== SECTION 6: CONTROL & CONNECTIVITY =====
            Question(
                id="control_simplicity",
                text="Who will be operating this system?",
                type="single_choice",
                options=[
                    "Non-technical users (must be simple)",
                    "Mixed technical abilities",
                    "Technical staff only",
                    "Automated (minimal user interaction)"
                ],
                help_text="This affects control system complexity",
                icon="🎛️"
            ),
            
            Question(
                id="byod_requirement",
                text="Do users need to connect their own laptops/devices?",
                type="single_choice",
                options=["Yes - critical requirement", "Nice to have", "No - dedicated system only"],
                icon="💼"
            ),
            
            Question(
                id="wireless_presentation",
                text="Would you like wireless screen sharing?",
                type="single_choice",
                options=["Yes - essential", "Yes - if budget allows", "No - wired is fine"],
                depends_on={"byod_requirement": ["Yes - critical requirement", "Nice to have"]},
                icon="📡"
            ),
            
            # ===== SECTION 7: SPECIAL REQUIREMENTS =====
            Question(
                id="special_features",
                text="Do you need any of these specialized features?",
                type="multi_choice",
                options=[
                    "Room scheduling display (calendar integration)",
                    "Recording/streaming capability",
                    "Assistive listening (ADA compliance)",
                    "Lighting control integration",
                    "Acoustic echo cancellation",
                    "Digital signage",
                    "Multi-room audio",
                    "Emergency notification system",
                    "None of the above"
                ],
                required=False,
                icon="⚙️"
            ),
            
            Question(
                id="future_proofing",
                text="How long do you plan to use this system?",
                type="single_choice",
                options=[
                    "3-5 years (standard)",
                    "5-7 years (prefer longevity)",
                    "10+ years (maximum investment)",
                    "Temporary/short-term"
                ],
                help_text="Affects equipment tier recommendations",
                icon="🔮"
            ),
            
            # ===== SECTION 8: BUDGET & PRIORITIES =====
            Question(
                id="budget_tier",
                text="What is your budget approach?",
                type="single_choice",
                options=[
                    "Economy - Cost-effective solutions",
                    "Standard - Balanced quality/price",
                    "Premium - High-end equipment",
                    "Executive - Best available",
                    "Not sure - recommend based on needs"
                ],
                icon="💰"
            ),
            
            Question(
                id="priority_ranking",
                text="Rank your priorities (drag to reorder)",
                type="ranking",
                options=[
                    "Ease of use",
                    "Audio/video quality",
                    "Reliability",
                    "Future expansion",
                    "Budget constraints",
                    "Brand reputation"
                ],
                icon="📊"
            ),
            
            # ===== SECTION 9: INSTALLATION & SUPPORT =====
            Question(
                id="installation_preference",
                text="Installation and cabling preferences?",
                type="single_choice",
                options=[
                    "Professional installation required",
                    "Some DIY acceptable",
                    "Fully DIY (provide guidance)",
                    "Not sure"
                ],
                icon="🔧"
            ),
            
            Question(
                id="cable_management",
                text="Cable management preferences?",
                type="single_choice",
                options=[
                    "All cables hidden (in-wall/ceiling)",
                    "Some exposed cables acceptable",
                    "Surface-mounted conduit",
                    "Don't care about aesthetics"
                ],
                icon="🔌"
            ),
            
            Question(
                id="support_level",
                text="What level of ongoing support do you need?",
                type="single_choice",
                options=[
                    "24/7 Support + Monitoring",
                    "Standard business hours support",
                    "Basic warranty only",
                    "Self-supported"
                ],
                icon="🛠️"
            ),
            
            # ===== SECTION 10: FINAL DETAILS =====
            Question(
                id="timeline",
                text="What is your project timeline?",
                type="single_choice",
                options=[
                    "Urgent (< 2 weeks)",
                    "Normal (2-6 weeks)",
                    "Flexible (6+ weeks)",
                    "Planning phase (no rush)"
                ],
                icon="📅"
            ),
            
            Question(
                id="additional_requirements",
                text="Anything else we should know?",
                type="text",
                required=False,
                help_text="Specific brand requirements, aesthetic preferences, technical constraints, etc.",
                icon="📝"
            )
        ]
    
    def render(self):
        """Render the questionnaire with progress tracking"""
        st.markdown("### 🎯 Smart AV Design Questionnaire")
        st.info("Answer these questions to receive a customized BOQ. Estimated time: 3-5 minutes")
        
        # Progress tracking
        total_questions = len([q for q in self.questions if not q.depends_on])
        answered = len(self.responses)
        progress = answered / total_questions if total_questions > 0 else 0
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(progress, text=f"Progress: {answered}/{total_questions} questions")
        with col2:
            if progress == 1.0:
                st.success("✅ Complete")
        
        # Render questions by section
        sections = self._group_questions_by_section()
        
        for section_name, questions in sections.items():
            with st.expander(f"**{section_name}**", expanded=(answered < 5)):
                for question in questions:
                    if self._should_show_question(question):
                        self._render_question(question)
        
        # Generate BOQ button
        if progress >= 0.8:  # At least 80% complete
            st.markdown("---")
            if st.button("🚀 Generate Custom BOQ", type="primary", use_container_width=True):
                return self._process_responses()
        
        return None
    
    def _should_show_question(self, question: Question) -> bool:
        """Check if question should be displayed based on dependencies"""
        if not question.depends_on:
            return True
        
        for dep_question_id, required_values in question.depends_on.items():
            user_response = self.responses.get(dep_question_id)
            if isinstance(required_values, list):
                if user_response not in required_values:
                    return False
            else:
                if user_response != required_values:
                    return False
        return True
    
    def _render_question(self, question: Question):
        """Render individual question based on type"""
        st.markdown(f"**{question.icon} {question.text}**")
        if question.help_text:
            st.caption(question.help_text)
        
        key = f"q_{question.id}"
        
        if question.type == "single_choice":
            response = st.radio(
                label="",
                options=question.options,
                key=key,
                label_visibility="collapsed"
            )
            self.responses[question.id] = response
        
        elif question.type == "multi_choice":
            response = st.multiselect(
                label="",
                options=question.options,
                key=key,
                label_visibility="collapsed"
            )
            self.responses[question.id] = response
        
        elif question.type == "brand_select":
            response = st.selectbox(
                label="",
                options=question.options,
                key=key,
                label_visibility="collapsed"
            )
            if response != "No preference":
                self.responses[question.id] = response
        
        elif question.type == "numeric":
            col1, col2, col3 = st.columns(3)
            with col1:
                length = st.number_input("Length (ft)", min_value=5.0, value=20.0, key=f"{key}_length")
            with col2:
                width = st.number_input("Width (ft)", min_value=5.0, value=15.0, key=f"{key}_width")
            with col3:
                height = st.number_input("Height (ft)", min_value=7.0, value=10.0, key=f"{key}_height")
            self.responses[question.id] = {"length": length, "width": width, "height": height}
        
        elif question.type == "text":
            response = st.text_area(
                label="",
                key=key,
                height=100,
                label_visibility="collapsed"
            )
            if response:
                self.responses[question.id] = response
        
        st.markdown("---")
    
    def _group_questions_by_section(self) -> Dict[str, List[Question]]:
        """Group questions into logical sections"""
        sections = {
            "📋 Project Basics": [],
            "🎯 Primary Use Case": [],
            "🖥️ Display Requirements": [],
            "📹 Video System": [],
            "🔊 Audio System": [],
            "🎛️ Control & Connectivity": [],
            "⚙️ Special Features": [],
            "💰 Budget & Priorities": [],
            "🔧 Installation & Support": [],
            "📝 Final Details": []
        }
        
        section_mapping = {
            ("project_type", "room_size_known", "room_dimensions", "participant_count"): "📋 Project Basics",
            ("primary_use", "video_conf_frequency"): "🎯 Primary Use Case",
            ("display_preference", "display_brand_preference"): "🖥️ Display Requirements",
            ("camera_requirements", "vc_platform", "vc_brand_preference"): "📹 Video System",
            ("audio_priority", "audio_features", "audio_brand_preference"): "🔊 Audio System",
            ("control_simplicity", "byod_requirement", "wireless_presentation"): "🎛️ Control & Connectivity",
            ("special_features", "future_proofing"): "⚙️ Special Features",
            ("budget_tier", "priority_ranking"): "💰 Budget & Priorities",
            ("installation_preference", "cable_management", "support_level"): "🔧 Installation & Support",
            ("timeline", "additional_requirements"): "📝 Final Details"
        }
        
        for question in self.questions:
            for question_ids, section_name in section_mapping.items():
                if question.id in question_ids:
                    sections[section_name].append(question)
                    break
        
        return sections
    
    def _process_responses(self) -> Dict:
        """Convert questionnaire responses to BOQ generation parameters"""
        # This would map responses to your existing system's inputs
        processed = {
            'room_type': self._map_room_type(),
            'client_preferences': self._extract_brand_preferences(),
            'technical_reqs': self._extract_technical_requirements(),
            'budget_tier': self._map_budget_tier(),
            'features': self._generate_features_text(),
            'room_dimensions': self.responses.get('room_dimensions', {}),
            'questionnaire_confidence': self._calculate_confidence_score()
        }
        
        return processed
    
    def _map_room_type(self) -> str:
        """Map questionnaire response to room profile"""
        project_type = self.responses.get('project_type', '')
        participant_count = self.responses.get('participant_count', '')
        
        mapping = {
            "Huddle/Collaboration Space": "Small Huddle Room (2-3 People)",
            "Corporate Meeting Room": "Standard Conference Room (6-8 People)",
            "Executive Boardroom": "Executive Boardroom (10-16 People)",
            "Training/Classroom": "Training Room (15-25 People)",
            # ... complete mapping
        }
        
        return mapping.get(project_type, "Standard Conference Room (6-8 People)")
    
    def _extract_brand_preferences(self) -> Dict[str, str]:
        """Extract brand preferences from responses"""
        return {
            'displays': self.responses.get('display_brand_preference'),
            'video_conferencing': self.responses.get('vc_brand_preference'),
            'audio': self.responses.get('audio_brand_preference')
        }
    
    def _generate_features_text(self) -> str:
        """Generate natural language features description"""
        features = []
        
        # Add camera requirements
        camera_reqs = self.responses.get('camera_requirements', [])
        if camera_reqs:
            features.append(f"Camera needs: {', '.join(camera_reqs)}")
        
        # Add audio features
        audio_feats = self.responses.get('audio_features', [])
        if audio_feats:
            features.append(f"Audio requirements: {', '.join(audio_feats)}")
        
        # Add special features
        special = self.responses.get('special_features', [])
        if special and 'None of the above' not in special:
            features.append(f"Special features: {', '.join(special)}")
        
        # Add additional notes
        if self.responses.get('additional_requirements'):
            features.append(self.responses['additional_requirements'])
        
        return ". ".join(features)
    
    def _calculate_confidence_score(self) -> float:
        """Calculate how complete/confident we are in the data"""
        required_answered = sum(1 for q in self.questions if q.required and q.id in self.responses)
        total_required = sum(1 for q in self.questions if q.required)
        return required_answered / total_required if total_required > 0 else 0.0


# INTEGRATION INTO app.py
def show_questionnaire_tab():
    """NEW TAB in main app"""
    questionnaire = AVQuestionnaire()
    processed_data = questionnaire.render()
    
    if processed_data:
        # Store in session state for use in BOQ generation
        st.session_state.questionnaire_data = processed_data
        st.session_state.questionnaire_complete = True
        
        # Show summary
        with st.expander("📊 Questionnaire Summary", expanded=True):
            st.json(processed_data)
        
        # Auto-populate other tabs
        st.success("✅ Questionnaire complete! Your answers have been applied to all tabs.")
        st.info("💡 You can now review the configuration in other tabs or proceed directly to BOQ generation.")
