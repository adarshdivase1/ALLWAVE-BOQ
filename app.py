import streamlit as st
import pandas as pd
import google.generativeai as genai
import time # To simulate a typing effect

# --- Page Configuration ---
# Set the page title, icon, and layout for a more professional look.
st.set_page_config(
    page_title="AV BOQ Generator",
    page_icon="🤖",
    layout="wide"
)

# --- Load Data and Guidelines ---
# Use st.cache_data to load the data only once, improving performance.
@st.cache_data
def load_data():
    """Loads the product catalog and AVIXA guidelines from files."""
    try:
        df = pd.read_csv("master_product_catalog.csv")
        with open("avixa_guidelines.md", "r") as f:
            guidelines = f.read()
        return df, guidelines
    except FileNotFoundError:
        st.error("Error: Make sure `master_product_catalog.csv` and `avixa_guidelines.md` are in the same folder as the app.")
        return None, None

product_catalog_df, avixa_guidelines = load_data()

# --- Gemini API Configuration ---
# Configure the generative AI model with the API key from Streamlit's secrets.
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}. Please check your API key in the secrets file.")
    model = None

# --- Application UI ---
st.title("💡 AI-Powered AV BOQ Generator")
st.markdown("This tool helps you create a Bill of Quantities (BOQ) for AV projects based on your requirements and AVIXA standards.")

# Use columns for a cleaner layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("Project Requirements")
    room_type = st.selectbox(
        "Select the type of room:",
        ("Huddle Room (2-4 People)", "Medium Conference Room (5-10 People)", "Executive Boardroom", "Training Room")
    )
    budget_tier = st.select_slider(
        "Select the budget tier:",
        options=["Economy", "Standard", "Premium"],
        value="Standard"
    )

with col2:
    st.subheader("Additional Features")
    features = st.text_area(
        "Enter any specific features or requirements (e.g., 'wireless presentation', 'dual 80-inch displays', 'needs to be Zoom certified'):",
        height=150
    )

# --- BOQ Generation Logic ---
if st.button("Generate BOQ", type="primary"):
    if product_catalog_df is not None and model is not None:
        with st.spinner("🧠 The AI is thinking... Please wait."):
            # Convert the product catalog DataFrame to a string format that's easy for the AI to understand.
            product_catalog_string = product_catalog_df.to_string()

            # --- This is the core of the application: The Prompt ---
            # We create a detailed prompt that gives the AI context, rules, and the specific task.
            # This is a basic form of Retrieval-Augmented Generation (RAG).
            prompt = f"""
            You are an expert AV System Designer. Your task is to create a detailed Bill of Quantities (BOQ) for an AV installation based on the user's requirements, your internal product catalog, and industry best practices.

            **Step 1: Understand the User's Requirements**
            - Room Type: {room_type}
            - Budget Tier: {budget_tier}
            - Specific Features: {features}

            **Step 2: Adhere to the Following Rules (AVIXA Guidelines)**
            These are mandatory design principles. You must follow them.
            ---
            {avixa_guidelines}
            ---

            **Step 3: Use Only Products from the Provided Catalog**
            This is your entire inventory. Do not invent products or use products not listed here.
            ---
            {product_catalog_string}
            ---

            **Step 4: Generate the BOQ**
            Create a logical and complete BOQ. Include quantities, product names, and a brief justification for each choice. The output must be in Markdown format.
            - Start with a title for the BOQ.
            - Group items by category (e.g., Displays, Audio, Video Conferencing).
            - For each item, list: `Quantity - Brand Name - Product Name - Justification`.
            - Conclude with a "Design Rationale" section explaining why the system is a good fit for the user's needs.
            """

            try:
                # Call the Gemini API to generate the content
                response = model.generate_content(prompt)
                
                st.subheader("✅ Generated Bill of Quantities")
                
                # --- Simulate a "typing" effect for a better user experience ---
                response_text = response.text
                message_placeholder = st.empty()
                full_response = ""
                for chunk in response_text.split():
                    full_response += chunk + " "
                    time.sleep(0.05) # Adjust sleep time for faster/slower typing
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)

            except Exception as e:
                st.error(f"An error occurred while generating the BOQ: {e}")
    else:
        st.error("Could not generate BOQ. Please check if data files are loaded and the API key is correct.")
