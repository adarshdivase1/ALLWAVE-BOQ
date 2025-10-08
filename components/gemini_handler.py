# components/gemini_handler.py
import streamlit as st
import google.generativeai as genai
import time
import json

def setup_gemini():
    """Configure the Gemini API and return the model."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            # Using a more recent and widely available model
            model = genai.GenerativeModel('gemini-2.0-flash-lite-001')
            return model
        else:
            st.error("GEMINI_API_KEY not found in Streamlit secrets.")
            return None
    except Exception as e:
        st.error(f"Gemini API configuration failed: {e}")
        return None


def generate_with_retry(model, prompt, max_retries=3, return_text_only=True):
    """Generate content with retry logic and error handling."""
    for attempt in range(max_retries):
        try:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            
            response = model.generate_content(prompt, safety_settings=safety_settings)
            
            # ENHANCED: More robust text extraction
            if return_text_only:
                # Method 1: Direct text attribute
                if hasattr(response, 'text') and response.text:
                    return str(response.text).strip()
                
                # Method 2: Candidates path
                if hasattr(response, 'candidates') and len(response.candidates) > 0:
                    try:
                        text = response.candidates[0].content.parts[0].text
                        if text:
                            return str(text).strip()
                    except (AttributeError, IndexError):
                        pass
                
                # Method 3: String conversion fallback
                try:
                    return str(response).strip()
                except:
                    pass
                
                # If all methods fail
                st.warning(f"⚠️ Could not extract text from Gemini response")
                return None
            else:
                return response
                
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"AI generation failed after {max_retries} attempts: {e}")
                return None
            time.sleep(2 ** attempt)
    
    return None


def validate_against_avixa(model, guidelines, boq_items):
    """Use AI to validate the BOQ against AVIXA standards."""
    if not guidelines or not boq_items or not model:
        return []
    
    prompt = f"""
    You are an AVIXA Certified Technology Specialist (CTS). Review the following BOQ against the provided AVIXA standards.
    List any potential non-compliance issues, missing items (like accessibility components), or areas for improvement.
    If no issues are found, respond with 'No specific compliance issues found.'
    
    **AVIXA Standards Summary:**
    {guidelines}
    
    **Bill of Quantities to Review:**
    {json.dumps(boq_items, indent=2)}
    
    **Your Compliance Review:**
    """
    
    try:
        # Use return_text_only=True to get plain text
        response_text = generate_with_retry(model, prompt, return_text_only=True)
        
        if response_text:
            if "no specific compliance issues" in response_text.lower():
                return []
            return [line.strip() for line in response_text.split('\n') if line.strip()]
        return []
        
    except Exception as e:
        return [f"AVIXA compliance check failed: {str(e)}"]


def extract_text_from_response(response):
    """
    Helper function to extract text from Gemini response object.
    Handles multiple response formats gracefully.
    
    Args:
        response: Gemini GenerateContentResponse object or string
    
    Returns:
        Plain text string or None
    """
    if response is None:
        return None
    
    if isinstance(response, str):
        return response
    
    if hasattr(response, 'text'):
        return response.text
    
    if hasattr(response, 'candidates') and len(response.candidates) > 0:
        try:
            return response.candidates[0].content.parts[0].text
        except (AttributeError, IndexError):
            return None
    
    return None

