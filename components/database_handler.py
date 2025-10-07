# components/database_handler.py

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Use st.cache_resource to initialize the connection only once per session.
@st.cache_resource
def initialize_firebase():
    """Initializes the Firebase connection using credentials from Streamlit secrets."""
    try:
        # Check if the app is already initialized to prevent errors on rerun
        if not firebase_admin._apps:
            # Get credentials from st.secrets
            creds_dict = st.secrets["firebase_credentials"]
            cred = credentials.Certificate(creds_dict)
            firebase_admin.initialize_app(cred)
        
        # Return the firestore client
        return firestore.client()
    except Exception as e:
        st.error(f"Failed to initialize Firebase. Please check your secrets.toml: {e}")
        return None

def save_project(db, user_email, project_data):
    """Saves or updates a project for a specific user in Firestore."""
    if not db or not user_email or not project_data.get('name'):
        st.warning("Could not save project. A project name is required.")
        return False
    
    try:
        # Use the project name as the document ID for simplicity
        project_id = project_data['name']
        project_data['last_saved'] = datetime.now().isoformat()
        
        # Define the path in Firestore: users/{user_email}/projects/{project_id}
        doc_ref = db.collection('users').document(user_email).collection('projects').document(project_id)
        doc_ref.set(project_data, merge=True) # merge=True updates fields without overwriting the whole doc
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
        # Sort by last saved date, newest first
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
