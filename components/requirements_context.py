# components/requirements_context.py
"""
Unified Requirements Context - The Single Source of Truth
This object is passed to ALL systems to ensure coordination
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json

@dataclass
class RoomContext:
    """Physical room characteristics"""
    length_ft: float
    width_ft: float
    ceiling_height_ft: float
    area_sqft: float
    volume_cuft: float
    room_type: str
    room_name: str = "Main Room"
    
    # ACIM-specific details
    seating_capacity: Optional[int] = None
    seating_layout: str = "conference"  # conference, theater, classroom, u-shape
    table_dimensions: Optional[Dict[str, float]] = None
    architectural_features: str = ""

@dataclass
class TechnicalRequirements:
    """Technical specifications from questionnaire"""
    # Display requirements
    display_quantity: int = 1
    display_size_preference: Optional[int] = None  # Manual override
    display_size_avixa: Optional[int] = None  # AVIXA calculated
    display_size_final: Optional[int] = None  # Final decision
    dual_display_needed: bool = False
    interactive_display_needed: bool = False
    
    # Video conferencing
    vc_platform: str = "Microsoft Teams"
    vc_solution_type: str = "BYOD"  # Native, BYOD, Both
    camera_type: str = "Video Bar"  # Video Bar, PTZ, Multi-camera
    auto_tracking_needed: bool = False
    
    # Audio requirements
    microphone_type: str = "Table"  # Table, Ceiling, Gooseneck, Wireless
    microphone_count_avixa: Optional[int] = None
    speaker_type: str = "Ceiling"
    speaker_count_avixa: Optional[int] = None
    dsp_required: bool = False
    voice_reinforcement_needed: bool = False
    
    # Connectivity
    connectivity_types: List[str] = field(default_factory=lambda: ["HDMI", "USB-C"])
    wireless_presentation_needed: bool = True
    
    # Control & Automation
    control_type: str = "Native Platform"  # Native, Programmable, Hybrid
    automation_scope: str = "None"
    room_scheduling_needed: bool = False
    
    # Infrastructure
    network_capability: str = "1Gb"
    power_adequate: bool = True
    cable_management: str = "In-Wall"
    
    # Compliance
    ada_compliance: bool = False
    recording_needed: bool = False
    streaming_needed: bool = False

@dataclass
class BrandPreferences:
    """Client brand preferences with ecosystem awareness"""
    displays: str = "No Preference"
    video_conferencing: str = "No Preference"
    audio: str = "No Preference"
    control: str = "No Preference"
    
    # NEW: Ecosystem enforcement
    vc_ecosystem_brand: Optional[str] = None  # Enforced brand for VC components
    audio_ecosystem_brand: Optional[str] = None  # Enforced brand for audio

@dataclass
class ProjectContext:
    """Overall project metadata"""
    project_name: str
    client_name: str
    budget_tier: str = "Standard"
    is_psni_referral: bool = False
    is_existing_customer: bool = False
    currency: str = "USD"
    timeline_weeks: int = 12

@dataclass
class UnifiedRequirementsContext:
    """
    THE SINGLE SOURCE OF TRUTH
    All systems read from this object to ensure coordination
    """
    room: RoomContext
    technical: TechnicalRequirements
    brands: BrandPreferences
    project: ProjectContext
    
    # ACIM detailed responses (from questionnaire)
    acim_responses: Dict[str, Any] = field(default_factory=dict)
    
    # AVIXA calculations (populated by AV Designer)
    avixa_calculations: Dict[str, Any] = field(default_factory=dict)
    
    # Decision log (tracks why decisions were made)
    decision_log: List[str] = field(default_factory=list)
    
    def log_decision(self, decision: str):
        """Track decision-making process"""
        self.decision_log.append(decision)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'room': self.room.__dict__,
            'technical': self.technical.__dict__,
            'brands': self.brands.__dict__,
            'project': self.project.__dict__,
            'acim_responses': self.acim_responses,
            'avixa_calculations': self.avixa_calculations,
            'decision_log': self.decision_log
        }
    
    @classmethod
    def from_questionnaire(cls, questionnaire_responses: Dict, 
                           client_requirements: 'ClientRequirements') -> 'UnifiedRequirementsContext':
        """
        FACTORY METHOD: Creates UnifiedRequirementsContext from questionnaire
        This is the bridge between old and new systems
        """
        
        # Extract room dimensions
        room_length = questionnaire_responses.get('room_length', 28.0)
        room_width = questionnaire_responses.get('room_width', 20.0)
        ceiling_height = questionnaire_responses.get('ceiling_height', 10.0)
        room_area = room_length * room_width
        room_volume = room_area * ceiling_height
        
        room_ctx = RoomContext(
            length_ft=room_length,
            width_ft=room_width,
            ceiling_height_ft=ceiling_height,
            area_sqft=room_area,
            volume_cuft=room_volume,
            room_type=questionnaire_responses.get('room_type', 'Standard Conference Room'),
            seating_layout=client_requirements.acim_seating_layout or "conference"
        )
        
        # Map questionnaire to technical requirements
        tech_req = TechnicalRequirements(
            display_quantity=2 if client_requirements.dual_display_needed else 1,
            dual_display_needed=client_requirements.dual_display_needed,
            interactive_display_needed=client_requirements.interactive_display_needed,
            
            vc_platform=client_requirements.vc_platform,
            vc_solution_type=client_requirements.acim_native_solution or "BYOD",
            camera_type=client_requirements.camera_type_preference,
            auto_tracking_needed=client_requirements.auto_tracking_needed,
            
            microphone_type=client_requirements.microphone_type,
            speaker_type=client_requirements.ceiling_vs_table_audio,
            voice_reinforcement_needed=client_requirements.voice_reinforcement_needed,
            
            wireless_presentation_needed=client_requirements.wireless_presentation_needed,
            room_scheduling_needed=client_requirements.room_scheduling_needed,
            
            automation_scope=client_requirements.acim_automation or "None",
            ada_compliance=client_requirements.ada_compliance_required,
            recording_needed=client_requirements.recording_capability_needed,
            streaming_needed=client_requirements.streaming_capability_needed
        )
        
        # Extract brand preferences
        brand_prefs = client_requirements.get_brand_preferences()
        brands = BrandPreferences(
            displays=brand_prefs.get('displays', 'No Preference'),
            video_conferencing=brand_prefs.get('video_conferencing', 'No Preference'),
            audio=brand_prefs.get('audio', 'No Preference'),
            control=brand_prefs.get('control', 'No Preference')
        )
        
        # Determine VC ecosystem brand
        if client_requirements.vc_platform.lower() == 'microsoft teams':
            brands.vc_ecosystem_brand = brands.video_conferencing if brands.video_conferencing != 'No Preference' else 'Poly'
        elif 'zoom' in client_requirements.vc_platform.lower():
            brands.vc_ecosystem_brand = brands.video_conferencing if brands.video_conferencing != 'No Preference' else 'Poly'
        elif 'cisco' in client_requirements.vc_platform.lower():
            brands.vc_ecosystem_brand = 'Cisco'
        
        project_ctx = ProjectContext(
            project_name=questionnaire_responses.get('project_name', 'Untitled Project'),
            client_name=questionnaire_responses.get('client_name', 'Client'),
            budget_tier=client_requirements.budget_level
        )
        
        # Build ACIM responses dict
        acim_responses = {
            'room_type_acim': client_requirements.room_type_acim,
            'seating_layout': client_requirements.acim_seating_layout,
            'solution_type': client_requirements.acim_solution_type,
            'uc_platform': client_requirements.acim_uc_platform,
            'connectivity': client_requirements.acim_connectivity,
            'digital_whiteboard': client_requirements.acim_digital_whiteboard,
            'automation': client_requirements.acim_automation,
            'budget': client_requirements.acim_budget
        }
        
        return cls(
            room=room_ctx,
            technical=tech_req,
            brands=brands,
            project=project_ctx,
            acim_responses=acim_responses
        )
