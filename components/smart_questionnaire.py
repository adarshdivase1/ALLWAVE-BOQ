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
        """Enhanced question tree with component-level selection"""
        return [
            # ===== SECTION 1: PROJECT BASICS =====
            Question(
                id="project_type",
                text="What type of space are you designing?",
                type="single_choice",
                options=[
                    "Corporate Meeting Room (4-8 people)",
                    "Executive Boardroom (8-16 people)",
                    "Training/Classroom (15-30 people)",
                    "Large Auditorium (30+ people)",
                    "Small Huddle Space (2-4 people)",
                    "Video Production Studio",
                    "Telepresence Suite",
                    "Multi-Purpose Event Space"
                ],
                icon="🏢"
            ),
            
            Question(
                id="exact_dimensions",
                text="Enter your room dimensions",
                type="numeric",
                help_text="Length × Width × Ceiling Height (in feet)",
                icon="📏"
            ),
            
            Question(
                id="primary_activity",
                text="What is the PRIMARY activity in this space? (Select ONE)",
                type="single_choice",
                options=[
                    "Video Conferencing (Daily Teams/Zoom meetings)",
                    "Presentations & Training (Screen sharing, teaching)",
                    "Collaborative Work (Whiteboarding, brainstorming)",
                    "Hybrid Events (Mix of in-person + remote)",
                    "Content Creation (Recording, broadcasting)",
                    "Executive Discussions (High-stakes meetings)"
                ],
                icon="🎯"
            ),
            
            Question(
                id="secondary_activities",
                text="What SECONDARY activities will happen here? (Select all)",
                type="multi_choice",
                options=[
                    "Quick huddles/stand-ups",
                    "Client presentations",
                    "Video calls with remote teams",
                    "Training sessions",
                    "Document review meetings",
                    "Recording/streaming content",
                    "None - single purpose room"
                ],
                required=False,
                icon="📋"
            ),
            
            # ===== SECTION 2: DISPLAY SYSTEM =====
            Question(
                id="need_displays",
                text="Does this room need display screens?",
                type="single_choice",
                options=["Yes - Essential", "Yes - If budget allows", "No - Audio only room"],
                icon="🖥️"
            ),
            
            Question(
                id="display_quantity",
                text="How many displays do you need?",
                type="single_choice",
                options=[
                    "One display (standard setup)",
                    "Two displays (content + people)",
                    "Three or more (video wall/multi-screen)",
                    "Not sure - recommend for me"
                ],
                depends_on={"need_displays": ["Yes - Essential", "Yes - If budget allows"]},
                icon="🖥️"
            ),
            
            Question(
                id="display_type",
                text="What TYPE of display do you prefer?",
                type="single_choice",
                options=[
                    "Standard LED/LCD Display (65-98 inch)",
                    "Interactive Touch Display (for collaboration)",
                    "Projector + Screen (for large rooms)",
                    "Direct-View LED Wall (premium/video wall)",
                    "Let AI recommend based on room size"
                ],
                depends_on={"need_displays": ["Yes - Essential", "Yes - If budget allows"]},
                icon="📺"
            ),
            
            Question(
                id="display_brand",
                text="Preferred DISPLAY brand? (Select ONE or 'No Preference')",
                type="single_choice",
                options=["Samsung", "LG", "Sony", "NEC", "Sharp", "Barco", "No Preference"],
                depends_on={"need_displays": ["Yes - Essential", "Yes - If budget allows"]},
                required=False,
                icon="🏷️"
            ),
            
            Question(
                id="display_features",
                text="What DISPLAY features are important?",
                type="multi_choice",
                options=[
                    "4K/UHD resolution",
                    "Touch capability",
                    "Anti-glare coating",
                    "Built-in wireless sharing",
                    "Thin bezels (for video walls)",
                    "Long warranty (5+ years)",
                    "Energy efficiency",
                    "Just basic quality"
                ],
                depends_on={"need_displays": ["Yes - Essential", "Yes - If budget allows"]},
                icon="✨"
            ),
            
            # ===== SECTION 3: VIDEO CONFERENCING =====
            Question(
                id="video_conf_usage",
                text="How often will you use VIDEO CONFERENCING?",
                type="single_choice",
                options=[
                    "Daily - Primary use case",
                    "Several times per week",
                    "Occasionally (monthly)",
                    "Rarely/Never"
                ],
                icon="📹"
            ),
            
            Question(
                id="vc_platform",
                text="Which video conferencing platform do you use MOST?",
                type="single_choice",
                options=[
                    "Microsoft Teams",
                    "Zoom",
                    "Google Meet",
                    "Cisco Webex",
                    "Multiple platforms (need flexibility)",
                    "Other/Custom platform"
                ],
                depends_on={"video_conf_usage": ["Daily - Primary use case", "Several times per week"]},
                icon="💻"
            ),
            
            Question(
                id="camera_system",
                text="What CAMERA system do you need?",
                type="single_choice",
                options=[
                    "All-in-One Video Bar (camera + speakers + mics)",
                    "PTZ Camera (pan-tilt-zoom for large rooms)",
                    "Dual Camera System (room + speaker tracking)",
                    "Basic Webcam (budget option)",
                    "Studio-Grade Cameras (production quality)",
                    "Recommend based on room size"
                ],
                depends_on={"video_conf_usage": ["Daily - Primary use case", "Several times per week", "Occasionally (monthly)"]},
                icon="📷"
            ),
            
            Question(
                id="camera_features",
                text="What CAMERA features do you need?",
                type="multi_choice",
                options=[
                    "Auto-framing (AI tracks people)",
                    "Speaker tracking",
                    "4K resolution",
                    "Low-light performance",
                    "Wide field of view (120°+)",
                    "Privacy shutter",
                    "Preset camera positions",
                    "Basic quality is fine"
                ],
                depends_on={"video_conf_usage": ["Daily - Primary use case", "Several times per week", "Occasionally (monthly)"]},
                icon="🎥"
            ),
            
            Question(
                id="vc_brand",
                text="Preferred VIDEO CONFERENCING equipment brand?",
                type="single_choice",
                options=["Poly", "Cisco", "Logitech", "Yealink", "Crestron", "Neat", "Zoom", "No Preference"],
                depends_on={"video_conf_usage": ["Daily - Primary use case", "Several times per week"]},
                required=False,
                icon="🏷️"
            ),
            
            # ===== SECTION 4: AUDIO SYSTEM (CRITICAL) =====
            Question(
                id="audio_importance",
                text="How CRITICAL is audio quality for this room?",
                type="single_choice",
                options=[
                    "Mission-Critical (Executive/client-facing)",
                    "Very Important (Daily professional use)",
                    "Important (Standard conferencing)",
                    "Basic (Simple meetings only)"
                ],
                icon="🔊"
            ),
            
            Question(
                id="microphone_type",
                text="What MICROPHONE system do you prefer?",
                type="single_choice",
                options=[
                    "Ceiling Microphones (clean aesthetic, best for large rooms)",
                    "Table Microphones (best performance, visible)",
                    "Wireless Handheld/Lapel Mics (for presenters)",
                    "All-in-One Video Bar Mics (integrated solution)",
                    "Gooseneck Podium Mics (for lectern/stage)",
                    "Recommend based on room type"
                ],
                icon="🎤"
            ),
            
            Question(
                id="speaker_type",
                text="What SPEAKER system do you need?",
                type="single_choice",
                options=[
                    "Ceiling Speakers (distributed audio, clean look)",
                    "Soundbar (integrated with video bar)",
                    "Wall-Mounted Speakers (directional audio)",
                    "Floor Speakers (highest quality)",
                    "Built-in Display Speakers (budget option)",
                    "Recommend based on room acoustics"
                ],
                icon="🔈"
            ),
            
            Question(
                id="audio_processing",
                text="Do you need advanced AUDIO PROCESSING?",
                type="multi_choice",
                options=[
                    "Echo Cancellation (AEC) - Essential for conferencing",
                    "Noise Suppression (block background noise)",
                    "Auto-Gain Control (consistent volume)",
                    "Voice Reinforcement (amplify local voices)",
                    "Recording capability",
                    "Multi-zone audio (different volumes per area)",
                    "Basic audio is fine"
                ],
                icon="🎚️"
            ),
            
            Question(
                id="dsp_requirement",
                text="Does this room need a dedicated AUDIO PROCESSOR/DSP?",
                type="single_choice",
                options=[
                    "Yes - Large room with complex audio",
                    "Yes - For multi-mic/multi-speaker setup",
                    "Maybe - If AI recommends it",
                    "No - Integrated audio is fine"
                ],
                help_text="DSP provides professional echo cancellation and audio routing",
                icon="🎛️"
            ),
            
            Question(
                id="audio_brand",
                text="Preferred AUDIO equipment brand?",
                type="single_choice",
                options=["Shure", "Biamp", "QSC", "Sennheiser", "Bose", "Yamaha", "ClearOne", "No Preference"],
                required=False,
                icon="🏷️"
            ),
            
            # ===== SECTION 5: CONTROL SYSTEM =====
            Question(
                id="control_requirement",
                text="Who will be OPERATING this AV system?",
                type="single_choice",
                options=[
                    "Non-technical users (must be one-touch simple)",
                    "Mixed technical abilities (intuitive interface)",
                    "Technical staff (can handle complexity)",
                    "Fully automated (no user control needed)"
                ],
                icon="🎮"
            ),
            
            Question(
                id="control_type",
                text="What CONTROL INTERFACE do you prefer?",
                type="single_choice",
                options=[
                    "Touch Panel on wall/table (professional)",
                    "Tablet/iPad control (mobile)",
                    "Native room system control (Teams/Zoom interface)",
                    "Smartphone app control",
                    "Physical button panel (simple)",
                    "Automated - no manual control"
                ],
                icon="🎛️"
            ),
            
            Question(
                id="control_features",
                text="What CONTROL features do you need?",
                type="multi_choice",
                options=[
                    "One-touch meeting start",
                    "Preset scenes (presentation/video call mode)",
                    "Scheduling integration (Outlook/Google Calendar)",
                    "Lighting control integration",
                    "Volume control",
                    "Source selection (laptop/wireless/camera)",
                    "System power on/off",
                    "Keep it simple - basic control only"
                ],
                icon="⚙️"
            ),
            
            Question(
                id="control_brand",
                text="Preferred CONTROL SYSTEM brand?",
                type="single_choice",
                options=["Crestron", "Extron", "AMX", "QSC", "Native (Teams/Zoom)", "No Preference"],
                required=False,
                icon="🏷️"
            ),
            
            # ===== SECTION 6: CONNECTIVITY & COLLABORATION =====
            Question(
                id="byod_requirement",
                text="Will users need to connect their OWN LAPTOPS/DEVICES?",
                type="single_choice",
                options=[
                    "Yes - Critical (BYOD is primary use)",
                    "Yes - Important (BYOD + room system)",
                    "Sometimes - Nice to have",
                    "No - Dedicated room system only"
                ],
                icon="💼"
            ),
            
            Question(
                id="connectivity_type",
                text="What CONNECTION methods do you need?",
                type="multi_choice",
                options=[
                    "USB-C (single cable for video+audio+power)",
                    "HDMI (standard connection)",
                    "Wireless Screen Sharing (AirPlay/Miracast)",
                    "Dedicated Wireless Presentation System",
                    "Table connectivity box/plate",
                    "Network connection only",
                    "Multiple connection options"
                ],
                depends_on={"byod_requirement": ["Yes - Critical (BYOD is primary use)", "Yes - Important (BYOD + room system)", "Sometimes - Nice to have"]},
                icon="🔌"
            ),
            
            Question(
                id="wireless_presentation",
                text="Do you need a WIRELESS PRESENTATION SYSTEM?",
                type="single_choice",
                options=[
                    "Yes - Essential (ClickShare/AirMedia/Solstice)",
                    "Yes - If budget allows",
                    "No - Wired is fine",
                    "Not sure - recommend"
                ],
                depends_on={"byod_requirement": ["Yes - Critical (BYOD is primary use)", "Yes - Important (BYOD + room system)"]},
                icon="📡"
            ),
            
            # ===== SECTION 7: INFRASTRUCTURE & MOUNTING =====
            Question(
                id="display_mounting",
                text="How should DISPLAYS be mounted?",
                type="single_choice",
                options=[
                    "Wall Mount (fixed or tilting)",
                    "Floor Stand/Cart (mobile)",
                    "Ceiling Mount (for projector)",
                    "Integrated Furniture Mount",
                    "Video Wall Frame (for multiple displays)",
                    "Recommend based on room layout"
                ],
                depends_on={"need_displays": ["Yes - Essential", "Yes - If budget allows"]},
                icon="🔧"
            ),
            
            Question(
                id="equipment_housing",
                text="Where should AV EQUIPMENT be stored?",
                type="single_choice",
                options=[
                    "Wall-Mounted Rack (compact)",
                    "Floor Rack/Cabinet (for complex systems)",
                    "Under-Table/In-Furniture",
                    "Ceiling-Mounted (for projector/mics)",
                    "No rack needed (all-in-one system)",
                    "Recommend based on equipment count"
                ],
                icon="🗄️"
            ),
            
            Question(
                id="cable_management",
                text="What CABLE MANAGEMENT do you prefer?",
                type="single_choice",
                options=[
                    "All cables hidden (in-wall/in-ceiling)",
                    "Conduit/raceway (surface-mounted but neat)",
                    "Under carpet/floor",
                    "Some exposed cables acceptable",
                    "Don't care - functionality over aesthetics"
                ],
                icon="📏"
            ),
            
            Question(
                id="power_requirements",
                text="Are DEDICATED ELECTRICAL CIRCUITS available?",
                type="single_choice",
                options=[
                    "Yes - Dedicated 20A circuits",
                    "Yes - Standard 15A circuits",
                    "No - Using existing outlets",
                    "Not sure - will verify"
                ],
                help_text="Large systems may need dedicated power",
                icon="⚡"
            ),
            
            # ===== SECTION 8: SPECIAL FEATURES & COMPLIANCE =====
            Question(
                id="recording_streaming",
                text="Do you need RECORDING or STREAMING capability?",
                type="single_choice",
                options=[
                    "Yes - Recording only (save meetings)",
                    "Yes - Streaming only (broadcast events)",
                    "Yes - Both recording and streaming",
                    "No - Live meetings only"
                ],
                icon="🎬"
            ),
            
            Question(
                id="room_scheduling",
                text="Do you need ROOM SCHEDULING integration?",
                type="single_choice",
                options=[
                    "Yes - With calendar display panel",
                    "Yes - Software integration only",
                    "No - Not needed"
                ],
                icon="📅"
            ),
            
            Question(
                id="compliance_requirements",
                text="What COMPLIANCE requirements apply?",
                type="multi_choice",
                options=[
                    "ADA Compliance (assistive listening)",
                    "Fire Code Compliance (plenum cables)",
                    "Security Clearance (classified environments)",
                    "Green Building (LEED certification)",
                    "None - Standard commercial"
                ],
                icon="📋"
            ),
            
            Question(
                id="lighting_integration",
                text="Do you need LIGHTING CONTROL integration?",
                type="single_choice",
                options=[
                    "Yes - Automated lighting scenes",
                    "Yes - Manual dimming control",
                    "No - Separate lighting control"
                ],
                required=False,
                icon="💡"
            ),
            
            # ===== SECTION 9: BUDGET & PRIORITIES =====
            Question(
                id="budget_tier",
                text="What is your BUDGET approach?",
                type="single_choice",
                options=[
                    "Economy - Most cost-effective solutions",
                    "Standard - Balanced quality and price",
                    "Premium - High-end equipment",
                    "Executive - Best available (no compromise)",
                    "Not sure - Recommend based on needs"
                ],
                icon="💰"
            ),
            
            Question(
                id="priority_1",
                text="What is your TOP PRIORITY? (Choose ONE)",
                type="single_choice",
                options=[
                    "Ease of Use (non-technical users)",
                    "Audio/Video Quality (best performance)",
                    "Reliability (minimal downtime)",
                    "Budget (cost-effective)",
                    "Brand Reputation (known brands)",
                    "Future Expansion (scalability)"
                ],
                icon="🎯"
            ),
            
            Question(
                id="priority_2",
                text="What is your SECOND PRIORITY?",
                type="single_choice",
                options=[
                    "Ease of Use",
                    "Audio/Video Quality",
                    "Reliability",
                    "Budget",
                    "Brand Reputation",
                    "Future Expansion"
                ],
                icon="🎯"
            ),
            
            Question(
                id="future_proofing",
                text="How long do you plan to USE this system?",
                type="single_choice",
                options=[
                    "3-5 years (standard lifecycle)",
                    "5-7 years (prefer longevity)",
                    "10+ years (maximum investment)",
                    "Temporary (1-2 years)"
                ],
                help_text="Affects equipment tier and warranty recommendations",
                icon="🔮"
            ),
            
            # ===== SECTION 10: INSTALLATION & SUPPORT =====
            Question(
                id="installation_type",
                text="What INSTALLATION approach do you prefer?",
                type="single_choice",
                options=[
                    "Turnkey - Professional installation + training",
                    "Standard - Professional installation only",
                    "Assisted - We install, you do cables",
                    "DIY - Equipment only, we self-install"
                ],
                icon="🔧"
            ),
            
            Question(
                id="support_level",
                text="What ONGOING SUPPORT do you need?",
                type="single_choice",
                options=[
                    "24/7 Premium Support + Monitoring",
                    "Business Hours Support + SLA",
                    "Standard Warranty Support",
                    "Self-Supported (minimal support)"
                ],
                icon="🛠️"
            ),
            
            Question(
                id="training_requirement",
                text="Do you need USER TRAINING?",
                type="single_choice",
                options=[
                    "Yes - Comprehensive training (admin + users)",
                    "Yes - Basic user training only",
                    "No - Self-serve documentation is fine"
                ],
                icon="👨‍🏫"
            ),
            
            Question(
                id="timeline",
                text="What is your PROJECT TIMELINE?",
                type="single_choice",
                options=[
                    "Urgent (< 2 weeks)",
                    "Fast-track (2-4 weeks)",
                    "Standard (4-8 weeks)",
                    "Flexible (8+ weeks)"
                ],
                icon="📅"
            ),
            
            # ===== SECTION 11: FINAL DETAILS =====
            Question(
                id="existing_equipment",
                text="Do you have EXISTING EQUIPMENT to integrate?",
                type="single_choice",
                options=[
                    "Yes - Must integrate existing displays",
                    "Yes - Must integrate existing audio",
                    "Yes - Must integrate existing control system",
                    "No - Complete new system"
                ],
                required=False,
                icon="🔄"
            ),
            
            Question(
                id="additional_requirements",
                text="Any OTHER REQUIREMENTS or preferences?",
                type="text",
                required=False,
                help_text="Specific brands you must avoid, aesthetic preferences, technical constraints, etc.",
                icon="📝"
            ),
            
            Question(
                id="design_confidence",
                text="How confident are you in your requirements?",
                type="single_choice",
                options=[
                    "Very confident - I know exactly what I need",
                    "Moderately confident - Some flexibility",
                    "Not confident - Need expert recommendations",
                    "Completely new to AV - Guide me through everything"
                ],
                icon="💭"
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
            "🖥️ Display System": [],
            "📹 Video Conferencing": [],
            "🔊 Audio System (Critical)": [],
            "🎮 Control System": [],
            "🔌 Connectivity & Collaboration": [],
            "🔧 Infrastructure & Mounting": [],
            "⚙️ Special Features & Compliance": [],
            "💰 Budget & Priorities": [],
            "🛠️ Installation & Support": [],
            "📝 Final Details": []
        }
        
        section_mapping = {
            ("project_type", "exact_dimensions", "primary_activity", "secondary_activities"): "📋 Project Basics",
            ("need_displays", "display_quantity", "display_type", "display_brand", "display_features"): "🖥️ Display System",
            ("video_conf_usage", "vc_platform", "camera_system", "camera_features", "vc_brand"): "📹 Video Conferencing",
            ("audio_importance", "microphone_type", "speaker_type", "audio_processing", "dsp_requirement", "audio_brand"): "🔊 Audio System (Critical)",
            ("control_requirement", "control_type", "control_features", "control_brand"): "🎮 Control System",
            ("byod_requirement", "connectivity_type", "wireless_presentation"): "🔌 Connectivity & Collaboration",
            ("display_mounting", "equipment_housing", "cable_management", "power_requirements"): "🔧 Infrastructure & Mounting",
            ("recording_streaming", "room_scheduling", "compliance_requirements", "lighting_integration"): "⚙️ Special Features & Compliance",
            ("budget_tier", "priority_1", "priority_2", "future_proofing"): "💰 Budget & Priorities",
            ("installation_type", "support_level", "training_requirement", "timeline"): "🛠️ Installation & Support",
            ("existing_equipment", "additional_requirements", "design_confidence"): "📝 Final Details"
        }
        
        for question in self.questions:
            found = False
            for question_ids, section_name in section_mapping.items():
                if question.id in question_ids:
                    sections[section_name].append(question)
                    found = True
                    break
            if not found:
                # Handle any questions not in the mapping if necessary
                pass

        return sections
    
    def _calculate_confidence_score(self) -> float:
        """
        ENHANCED: Calculate confidence score based on response quality
        """
        score = 0.0
        weights = {
            'required_complete': 0.30,  # 30% for answering all required
            'technical_detail': 0.25,  # 25% for technical specifications
            'brand_preferences': 0.15,  # 15% for brand clarity
            'use_case_clarity': 0.15,  # 15% for clear use case
            'budget_defined': 0.15     # 15% for budget clarity
        }
        
        # 1. Required questions (30%)
        required_questions = [q for q in self.questions if q.required]
        if required_questions:
            required_answered = sum(1 for q in required_questions if q.id in self.responses and self.responses[q.id])
            score += (required_answered / len(required_questions)) * weights['required_complete']
        
        # 2. Technical detail (25%)
        technical_questions = [
            'exact_dimensions', 'display_type', 'camera_system', 
            'microphone_type', 'speaker_type', 'control_type'
        ]
        technical_answered = sum(1 for qid in technical_questions if self.responses.get(qid))
        score += (technical_answered / len(technical_questions)) * weights['technical_detail']
        
        # 3. Brand preferences (15%)
        brand_questions = ['display_brand', 'vc_brand', 'audio_brand', 'control_brand']
        brands_specified = sum(1 for qid in brand_questions 
                               if self.responses.get(qid) and self.responses[qid] != 'No Preference')
        score += (brands_specified / len(brand_questions)) * weights['brand_preferences']
        
        # 4. Use case clarity (15%)
        use_case_detail = 0
        if self.responses.get('primary_activity'):
            use_case_detail += 0.5
        if self.responses.get('secondary_activities'):
            use_case_detail += 0.3
        if self.responses.get('video_conf_usage'):
            use_case_detail += 0.2
        score += use_case_detail * weights['use_case_clarity']
        
        # 5. Budget defined (15%)
        budget_clarity = 0
        if self.responses.get('budget_tier') and self.responses['budget_tier'] != 'Not sure - Recommend based on needs':
            budget_clarity += 0.6
        if self.responses.get('priority_1'):
            budget_clarity += 0.2
        if self.responses.get('priority_2'):
            budget_clarity += 0.2
        score += budget_clarity * weights['budget_defined']
        
        return min(score, 1.0)  # Cap at 100%


    def _process_responses(self) -> Dict:
        """
        ENHANCED: Convert responses to comprehensive BOQ parameters
        """
        confidence = self._calculate_confidence_score()
        
        processed = {
            'room_type': self._map_room_type(),
            'room_dimensions': self.responses.get('exact_dimensions', {}),
            
            # Client preferences with brand ecosystem
            'client_preferences': {
                'displays': self.responses.get('display_brand'),
                'video_conferencing': self.responses.get('vc_brand'),
                'audio': self.responses.get('audio_brand'),
                'control': self.responses.get('control_brand')
            },
            
            # Equipment overrides from questionnaire
            'equipment_overrides': {
                'displays': self._extract_display_requirements(),
                'video_system': self._extract_video_requirements(),
                'audio_system': self._extract_audio_requirements(),
                'control_system': self._extract_control_requirements(),
                'connectivity': self._extract_connectivity_requirements(),
                'infrastructure': self._extract_infrastructure_requirements()
            },
            
            'technical_reqs': {
                'ceiling_height': self.responses.get('exact_dimensions', {}).get('height', 10),
                'room_length': self.responses.get('exact_dimensions', {}).get('length', 24),
                'room_width': self.responses.get('exact_dimensions', {}).get('width', 16),
                'features': self._generate_features_text(),
                'dedicated_circuit': 'Yes' in str(self.responses.get('power_requirements', '')),
                'network_capability': 'Standard 1Gb',
                'cable_management': self._map_cable_management(),
                'ada_compliance': 'ADA' in str(self.responses.get('compliance_requirements', [])),
                'fire_code_compliance': 'Fire Code' in str(self.responses.get('compliance_requirements', [])),
                'security_clearance': 'Security' in str(self.responses.get('compliance_requirements', [])) and 'Classified' or 'Standard'
            },
            
            'budget_tier': self._map_budget_tier(),
            'features': self._generate_features_text(),
            'questionnaire_confidence': confidence,
            
            # NEW: Priority weighting for intelligent selection
            'priorities': {
                'ease_of_use': self._calculate_priority_weight('Ease of Use'),
                'quality': self._calculate_priority_weight('Audio/Video Quality'),
                'reliability': self._calculate_priority_weight('Reliability'),
                'budget': self._calculate_priority_weight('Budget'),
                'brand': self._calculate_priority_weight('Brand Reputation'),
                'expansion': self._calculate_priority_weight('Future Expansion')
            },
            
            # NEW: Installation context
            'installation_context': {
                'type': self.responses.get('installation_type', 'Standard'),
                'support_level': self.responses.get('support_level', 'Standard Warranty'),
                'training': self.responses.get('training_requirement', 'No'),
                'timeline': self.responses.get('timeline', 'Standard (4-8 weeks)')
            }
        }
        
        return processed


    def _extract_display_requirements(self) -> Dict:
        """Extract display-specific requirements"""
        if self.responses.get('need_displays') in ['Yes - Essential', 'Yes - If budget allows']:
            qty_map = {
                "One display (standard setup)": 1,
                "Two displays (content + people)": 2,
                "Three or more (video wall/multi-screen)": 3
            }
            
            type_map = {
                "Standard LED/LCD Display (65-98 inch)": "Commercial 4K Display",
                "Interactive Touch Display (for collaboration)": "Interactive Touch Display",
                "Projector + Screen (for large rooms)": "Projector and Screen",
                "Direct-View LED Wall (premium/video wall)": "Direct-View LED Wall"
            }
            
            return {
                'quantity': qty_map.get(self.responses.get('display_quantity'), 1),
                'type': type_map.get(self.responses.get('display_type'), 'Commercial 4K Display'),
                'features': self.responses.get('display_features', []),
                'preferred_brand': self.responses.get('display_brand')
            }
        return {}


    def _extract_video_requirements(self) -> Dict:
        """Extract video conferencing requirements"""
        if self.responses.get('video_conf_usage') in ['Daily - Primary use case', 'Several times per week']:
            camera_type_map = {
                "All-in-One Video Bar (camera + speakers + mics)": "All-in-one Video Bar",
                "PTZ Camera (pan-tilt-zoom for large rooms)": "PTZ Camera",
                "Dual Camera System (room + speaker tracking)": "Dual PTZ Cameras",
                "Studio-Grade Cameras (production quality)": "Studio Cameras"
            }
            
            return {
                'type': camera_type_map.get(self.responses.get('camera_system'), 'All-in-one Video Bar'),
                'camera_type': self.responses.get('camera_system', 'PTZ Camera'),
                'camera_count': 2 if 'Dual' in str(self.responses.get('camera_system')) else 1,
                'features': self.responses.get('camera_features', []),
                'platform': self.responses.get('vc_platform'),
                'preferred_brand': self.responses.get('vc_brand')
            }
        return {}


    def _extract_audio_requirements(self) -> Dict:
        """Extract audio system requirements"""
        mic_type_map = {
            "Ceiling Microphones (clean aesthetic, best for large rooms)": "Ceiling Microphone",
            "Table Microphones (best performance, visible)": "Table Microphone",
            "Wireless Handheld/Lapel Mics (for presenters)": "Wireless Microphone System",
            "Gooseneck Podium Mics (for lectern/stage)": "Gooseneck Microphone"
        }
        
        speaker_type_map = {
            "Ceiling Speakers (distributed audio, clean look)": "Ceiling Loudspeaker",
            "Soundbar (integrated with video bar)": "Integrated in Video Bar",
            "Wall-Mounted Speakers (directional audio)": "Wall-mounted Loudspeaker",
            "Floor Speakers (highest quality)": "Loudspeaker / Speaker"
        }
        
        # Determine if DSP is needed
        needs_dsp = (
            'Yes' in str(self.responses.get('dsp_requirement')) or
            self.responses.get('audio_importance') in ['Mission-Critical', 'Very Important'] or
            len(self.responses.get('audio_processing', [])) > 2
        )
        
        return {
            'type': 'Professional Audio System' if needs_dsp else 'Integrated Audio',
            'microphone_type': mic_type_map.get(self.responses.get('microphone_type'), 'Table Microphone'),
            'microphone_count': self._calculate_mic_count(),
            'speaker_type': speaker_type_map.get(self.responses.get('speaker_type'), 'Ceiling Loudspeaker'),
            'speaker_count': self._calculate_speaker_count(),
            'dsp_required': needs_dsp,
            'features': self.responses.get('audio_processing', []),
            'importance': self.responses.get('audio_importance'),
            'preferred_brand': self.responses.get('audio_brand')
        }


    def _extract_control_requirements(self) -> Dict:
        """Extract control system requirements"""
        control_type_map = {
            "Touch Panel on wall/table (professional)": "Touch Panel",
            "Tablet/iPad control (mobile)": "Tablet Controller",
            "Native room system control (Teams/Zoom interface)": "Native System Control",
            "Smartphone app control": "App-Based Control",
            "Physical button panel (simple)": "Keypad",
            "Automated - no manual control": "Automated System"
        }
        
        complexity_map = {
            "Non-technical users (must be one-touch simple)": "Simple",
            "Mixed technical abilities (intuitive interface)": "Standard",
            "Technical staff (can handle complexity)": "Advanced",
            "Fully automated (no user control needed)": "Automated"
        }
        
        return {
            'type': control_type_map.get(self.responses.get('control_type'), 'Touch Panel'),
            'complexity': complexity_map.get(self.responses.get('control_requirement'), 'Standard'),
            'features': self.responses.get('control_features', []),
            'user_profile': self.responses.get('control_requirement'),
            'preferred_brand': self.responses.get('control_brand')
        }


    def _extract_connectivity_requirements(self) -> Dict:
        """Extract connectivity requirements"""
        if self.responses.get('byod_requirement') in ['Yes - Critical (BYOD is primary use)', 'Yes - Important (BYOD + room system)']:
            return {
                'byod_required': True,
                'connection_types': self.responses.get('connectivity_type', []),
                'wireless_presentation': 'Yes - Essential' in str(self.responses.get('wireless_presentation')),
                'table_connectivity': 'Table connectivity box/plate' in str(self.responses.get('connectivity_type', []))
            }
        return {}


    def _extract_infrastructure_requirements(self) -> Dict:
        """Extract infrastructure and mounting requirements"""
        return {
            'display_mounting': self.responses.get('display_mounting'),
            'equipment_housing': self.responses.get('equipment_housing'),
            'cable_management': self.responses.get('cable_management'),
            'power_type': self.responses.get('power_requirements'),
            'recording': self.responses.get('recording_streaming'),
            'room_scheduling': self.responses.get('room_scheduling'),
            'lighting_control': self.responses.get('lighting_integration')
        }


    def _calculate_mic_count(self) -> int:
        """Calculate number of microphones based on room and requirements"""
        dims = self.responses.get('exact_dimensions', {})
        length = dims.get('length', 24)
        width = dims.get('width', 16)
        
        if length and width:
            area = length * width
            # Base calculation: 1 mic per 150 sq ft
            base_count = max(2, int(area / 150))
        else:
            base_count = 2

        # Adjust based on importance
        if self.responses.get('audio_importance') == 'Mission-Critical (Executive/client-facing)':
            return base_count + 1
        elif self.responses.get('audio_importance') == 'Basic (Simple meetings only)':
            return max(1, base_count - 1)
        
        return base_count


    def _calculate_speaker_count(self) -> int:
        """Calculate number of speakers based on room"""
        dims = self.responses.get('exact_dimensions', {})
        length = dims.get('length', 24)
        width = dims.get('width', 16)

        if length and width:
            area = length * width
            # Base calculation: 1 speaker per 200 sq ft
            base_count = max(2, int(area / 200))
        else:
            base_count = 2
        
        # Adjust based on speaker type
        if 'Soundbar' in str(self.responses.get('speaker_type')):
            return 1  # Soundbar is a single unit
        elif 'Floor Speakers' in str(self.responses.get('speaker_type')):
            return 2  # Stereo pair
        
        return base_count


    def _calculate_priority_weight(self, priority_name: str) -> float:
        """Calculate priority weight for intelligent product selection"""
        priority_1 = self.responses.get('priority_1', '')
        priority_2 = self.responses.get('priority_2', '')
        
        if priority_name in priority_1:
            return 1.0  # Highest priority
        elif priority_name in priority_2:
            return 0.7  # Second priority
        else:
            return 0.3  # Lower priority


    def _map_room_type(self) -> str:
        """Map questionnaire response to room profile"""
        project_type = self.responses.get('project_type', '')
        
        mapping = {
            "Small Huddle Space (2-4 people)": "Small Huddle Room (2-3 People)",
            "Corporate Meeting Room (4-8 people)": "Standard Conference Room (6-8 People)",
            "Executive Boardroom (8-16 people)": "Executive Boardroom (10-16 People)",
            "Training/Classroom (15-30 people)": "Training Room (15-25 People)",
            "Large Auditorium (30+ people)": "Multipurpose Event Room (40+ People)",
            "Video Production Studio": "Video Production Studio",
            "Telepresence Suite": "Telepresence Suite",
            "Multi-Purpose Event Space": "Multipurpose Event Room (40+ People)"
        }
        
        return mapping.get(project_type, "Standard Conference Room (6-8 People)")


    def _map_budget_tier(self) -> str:
        """Map budget response to tier"""
        budget = self.responses.get('budget_tier', '')
        
        mapping = {
            "Economy - Most cost-effective solutions": "Economy",
            "Standard - Balanced quality and price": "Standard",
            "Premium - High-end equipment": "Premium",
            "Executive - Best available (no compromise)": "Executive"
        }
        
        return mapping.get(budget, "Standard")


    def _map_cable_management(self) -> str:
        """Map cable management preference"""
        cable = self.responses.get('cable_management', '')
        
        mapping = {
            "All cables hidden (in-wall/in-ceiling)": "Concealed",
            "Conduit/raceway (surface-mounted but neat)": "Conduit",
            "Under carpet/floor": "Under Floor",
            "Some exposed cables acceptable": "Exposed",
            "Don't care - functionality over aesthetics": "Exposed"
        }
        
        return mapping.get(cable, "Exposed")


    def _generate_features_text(self) -> str:
        """Generate comprehensive features text from all responses"""
        features = []
        
        # Primary use case
        if self.responses.get('primary_activity'):
            features.append(f"Primary use: {self.responses['primary_activity']}")
        
        # Secondary activities
        if self.responses.get('secondary_activities'):
            secondary = ', '.join(self.responses['secondary_activities'])
            features.append(f"Also used for: {secondary}")
        
        # Video conferencing platform
        if self.responses.get('vc_platform'):
            features.append(f"Video platform: {self.responses['vc_platform']} certified required")
        
        # Camera features
        camera_features = self.responses.get('camera_features', [])
        if camera_features:
            features.append(f"Camera needs: {', '.join(camera_features)}")
        
        # Audio requirements
        audio_features = self.responses.get('audio_processing', [])
        if audio_features:
            features.append(f"Audio requirements: {', '.join(audio_features)}")
        
        # Display features
        display_features = self.responses.get('display_features', [])
        if display_features:
            features.append(f"Display features: {', '.join(display_features)}")
        
        # Control features
        control_features = self.responses.get('control_features', [])
        if control_features:
            features.append(f"Control needs: {', '.join(control_features)}")
        
        # Connectivity
        connectivity = self.responses.get('connectivity_type', [])
        if connectivity:
            features.append(f"Connectivity: {', '.join(connectivity)}")
        
        # Recording/streaming
        if self.responses.get('recording_streaming') and 'No' not in str(self.responses['recording_streaming']):
            features.append(f"Recording/streaming: {self.responses['recording_streaming']}")
        
        # Room scheduling
        if self.responses.get('room_scheduling') and 'No' not in str(self.responses['room_scheduling']):
            features.append(f"Room scheduling: {self.responses['room_scheduling']}")
        
        # Compliance
        compliance = self.responses.get('compliance_requirements', [])
        if compliance and 'None' not in str(compliance):
            features.append(f"Compliance: {', '.join(compliance)}")
        
        # Lighting integration
        if self.responses.get('lighting_integration') and 'No' not in str(self.responses['lighting_integration']):
            features.append(f"Lighting control: {self.responses['lighting_integration']}")
        
        # User confidence level
        if self.responses.get('design_confidence'):
            features.append(f"User confidence: {self.responses['design_confidence']}")
        
        # Additional requirements
        if self.responses.get('additional_requirements'):
            features.append(f"Additional notes: {self.responses['additional_requirements']}")
        
        return ". ".join(features)
    

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
