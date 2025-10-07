# components/database_handler.py

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

@st.cache_resource
def initialize_firebase():
    """Initializes the Firebase connection using credentials from Streamlit secrets."""
    try:
        if not firebase_admin._apps:
            # --- THIS IS THE MODIFIED PART ---
            # Streamlit secrets will provide the credentials as a dictionary
            creds_dict = st.secrets["firebase_credentials"]
            
            # The private key needs the newlines correctly formatted
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            
            cred = credentials.Certificate(creds_dict)
            # --- END OF MODIFICATION ---
            
            firebase_admin.initialize_app(cred)
        
        return firestore.client()
    except Exception as e:
        st.error(f"Failed to initialize Firebase. Please check your secrets.toml: {e}")
        return None

# --- The rest of the file (save_project, load_projects, etc.) remains unchanged ---
def save_project(db, user_email, project_data):
    """Saves or updates a project for a specific user in Firestore."""
    if not db or not user_email or not project_data.get('name'):
        st.warning("Could not save project. A project name is required.")
        return False
    
    try:
        project_id = project_data['name']
        project_data['last_saved'] = datetime.now().isoformat()
        
        doc_ref = db.collection('users').document(user_email).collection('projects').document(project_id)
        doc_ref.set(project_data, merge=True)
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
