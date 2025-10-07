# components/database_handler.py
# ENHANCED VERSION - Saves and restores COMPLETE project state

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json

@st.cache_resource
def initialize_firebase():
    """Initializes the Firebase connection using credentials from Streamlit secrets."""
    try:
        if not firebase_admin._apps:
            secrets_object = st.secrets["firebase_credentials"]
            creds_dict = dict(secrets_object)
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        
        return firestore.client()
    except Exception as e:
        st.error(f"Failed to initialize Firebase. Please check your secrets.toml: {e}")
        return None


def save_project(db, user_email, project_data):
    """
    Saves COMPLETE project state including all tabs and settings.
    Now captures everything the user has configured.
    """
    if not db or not user_email or not project_data.get('name'):
        st.warning("Could not save project. A project name is required.")
        return False
    
    try:
        project_id = project_data['name']
        
        # Build comprehensive project data structure
        complete_project_data = {
            # Basic Info
            'name': project_id,
            'last_saved': datetime.now().isoformat(),
            
            # Project Header Info (Tab 1)
            'project_name_input': project_data.get('project_name_input', ''),
            'client_name_input': project_data.get('client_name_input', ''),
            'location_input': project_data.get('location_input', ''),
            'design_engineer_input': project_data.get('design_engineer_input', ''),
            'account_manager_input': project_data.get('account_manager_input', ''),
            'client_personnel_input': project_data.get('client_personnel_input', ''),
            'comments_input': project_data.get('comments_input', ''),
            
            # Room Configuration (Tab 2)
            'room_type_select': st.session_state.get('room_type_select', 'Standard Conference Room'),
            'room_length_input': st.session_state.get('room_length_input', 28.0),
            'room_width_input': st.session_state.get('room_width_input', 20.0),
            'ceiling_height_input': st.session_state.get('ceiling_height_input', 10.0),
            'budget_tier_slider': st.session_state.get('budget_tier_slider', 'Standard'),
            
            # Advanced Requirements (Tab 3)
            'features_text_area': st.session_state.get('features_text_area', ''),
            'dedicated_circuit_checkbox': st.session_state.get('dedicated_circuit_checkbox', False),
            'network_capability_select': st.session_state.get('network_capability_select', 'Standard 1Gb'),
            'cable_management_select': st.session_state.get('cable_management_select', 'Exposed'),
            'ada_compliance_checkbox': st.session_state.get('ada_compliance_checkbox', False),
            'fire_code_compliance_checkbox': st.session_state.get('fire_code_compliance_checkbox', False),
            'security_clearance_select': st.session_state.get('security_clearance_select', 'Standard'),
            
            # Financial Settings
            'currency_select': st.session_state.get('currency_select', 'USD'),
            'gst_rates': project_data.get('gst_rates', {'Electronics': 18, 'Services': 18}),
            
            # Multi-Room Data (includes BOQ for each room)
            'rooms': project_data.get('rooms', []),
            'current_room_index': st.session_state.get('current_room_index', 0),
            
            # BOQ State (Tab 4)
            'boq_items': st.session_state.get('boq_items', []),
            'validation_results': st.session_state.get('validation_results', {}),
            
            # 3D Visualization State (Tab 5) - if you have specific viz settings
            'viz_generated': st.session_state.get('viz_generated', False),
            
            # User Context
            'is_psni_certified': st.session_state.get('is_psni_certified', False),
            'is_existing_customer': st.session_state.get('is_existing_customer', False),
            'user_location_type': st.session_state.get('user_location_type', 'Global'),
        }
        
        # Save to Firestore
        doc_ref = db.collection('users').document(user_email).collection('projects').document(project_id)
        doc_ref.set(complete_project_data, merge=True)
        
        return True
        
    except Exception as e:
        st.error(f"Error saving project: {e}")
        return False


def load_projects(db, user_email):
    """Loads all projects for a specific user from Firestore."""
    if not db or not user_email:
        return []
    
    try:
        projects_ref = db.collection('users').document(user_email).collection('projects')
        projects = projects_ref.stream()
        
        project_list = [doc.to_dict() for doc in projects]
        project_list.sort(key=lambda x: x.get('last_saved', ''), reverse=True)
        
        return project_list
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        return []


def restore_project_state(project_data):
    """
    Restores COMPLETE session state from loaded project data.
    This function sets ALL the session state variables that were saved.
    """
    if not project_data:
        return False
    
    try:
        # Project Header (Tab 1)
        st.session_state.project_name_input = project_data.get('project_name_input', '')
        st.session_state.client_name_input = project_data.get('client_name_input', '')
        st.session_state.location_input = project_data.get('location_input', '')
        st.session_state.design_engineer_input = project_data.get('design_engineer_input', '')
        st.session_state.account_manager_input = project_data.get('account_manager_input', '')
        st.session_state.client_personnel_input = project_data.get('client_personnel_input', '')
        st.session_state.comments_input = project_data.get('comments_input', '')
        
        # Room Configuration (Tab 2)
        st.session_state.room_type_select = project_data.get('room_type_select', 'Standard Conference Room')
        st.session_state.room_length_input = project_data.get('room_length_input', 28.0)
        st.session_state.room_width_input = project_data.get('room_width_input', 20.0)
        st.session_state.ceiling_height_input = project_data.get('ceiling_height_input', 10.0)
        st.session_state.budget_tier_slider = project_data.get('budget_tier_slider', 'Standard')
        
        # Advanced Requirements (Tab 3)
        st.session_state.features_text_area = project_data.get('features_text_area', '')
        st.session_state.dedicated_circuit_checkbox = project_data.get('dedicated_circuit_checkbox', False)
        st.session_state.network_capability_select = project_data.get('network_capability_select', 'Standard 1Gb')
        st.session_state.cable_management_select = project_data.get('cable_management_select', 'Exposed')
        st.session_state.ada_compliance_checkbox = project_data.get('ada_compliance_checkbox', False)
        st.session_state.fire_code_compliance_checkbox = project_data.get('fire_code_compliance_checkbox', False)
        st.session_state.security_clearance_select = project_data.get('security_clearance_select', 'Standard')
        
        # Financial Settings
        st.session_state.currency_select = project_data.get('currency_select', 'USD')
        st.session_state.gst_rates = project_data.get('gst_rates', {'Electronics': 18, 'Services': 18})
        
        # Multi-Room Data
        st.session_state.project_rooms = project_data.get('rooms', [])
        st.session_state.current_room_index = project_data.get('current_room_index', 0)
        
        # Load BOQ for current room
        if st.session_state.project_rooms and st.session_state.current_room_index < len(st.session_state.project_rooms):
            current_room = st.session_state.project_rooms[st.session_state.current_room_index]
            st.session_state.boq_items = current_room.get('boq_items', [])
        else:
            st.session_state.boq_items = project_data.get('boq_items', [])
        
        # BOQ State
        st.session_state.validation_results = project_data.get('validation_results', {})
        
        # 3D Visualization State
        st.session_state.viz_generated = project_data.get('viz_generated', False)
        
        # User Context
        st.session_state.is_psni_certified = project_data.get('is_psni_certified', False)
        st.session_state.is_existing_customer = project_data.get('is_existing_customer', False)
        st.session_state.user_location_type = project_data.get('user_location_type', 'Global')
        
        return True
        
    except Exception as e:
        st.error(f"Error restoring project state: {e}")
        return False


def delete_project(db, user_email, project_name):
    """Deletes a project for a specific user."""
    if not db or not user_email or not project_name:
        return False
    try:
        db.collection('users').document(user_email).collection('projects').document(project_name).delete()
        return True
    except Exception as e:
        st.error(f"Error deleting project: {e}")
        return False
