import streamlit as st
import pandas as pd
import google.generativeai as genai
import re # ## NEW ## Import the regular expressions library to parse the output

# --- Page Configuration ---
st.set_page_config(
    page_title="AV BOQ Generator Pro",
    page_icon="🤖",
    layout="wide"
)

# --- Load Data and Guidelines ---
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
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}. Please check your API key in the secrets file.")
    model = None

# --- Application UI ---
st.title("💡 AI-Powered AV BOQ Generator (Pro Version)")
st.markdown("This tool helps you create a professional, production-ready Bill of Quantities for AV projects.")

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
if st.button("Generate Production-Ready BOQ", type="primary"):
    if product_catalog_df is not None and model is not None:
        with st.spinner("⚙️ Engineering a production-ready BOQ... This may take a moment."):
            
            product_catalog_string = product_catalog_df.to_csv(index=False)

            # ## NEW ## This is the upgraded, highly-detailed prompt.
            # It's much longer and more specific to force the model into a professional format.
            prompt = f"""
            You are a senior AV System Design Engineer. Your task is to create a professional, production-ready Bill of Quantities (BOQ). Your response must be perfect and strictly follow all instructions.

            **1. USER REQUIREMENTS:**
            - **Room Type:** {room_type}
            - **Budget Tier:** {budget_tier}
            - **Specific Features:** {features if features else "None"}

            **2. MANDATORY RULES & GUIDELINES:**
            - You MUST adhere to the AVIXA guidelines provided below.
            - You MUST only select products from the official Product Catalog provided. Do not invent products.
            - You MUST ensure selected products are compatible. Check the 'compatibility_tags' and 'use_case_tags'.
            - You MUST select products that match the requested 'Budget Tier'.

            **AVIXA GUIDELINES:**
            ---
            {avixa_guidelines}
            ---

            **OFFICIAL PRODUCT CATALOG (CSV FORMAT):**
            ---
            {product_catalog_string}
            ---

            **3. YOUR TASK: STEP-BY-STEP INTERNAL MONOLOGUE (CRITICAL THINKING PROCESS):**
            Before creating the BOQ, first think step-by-step to formulate the best possible solution. Consider the primary function of the room, required components, compatibility, and budget. For example: "The user wants a Medium Conference Room. I need a display, a camera, microphones, speakers, control, and cabling. For the display, AVIXA says 65-75 inches. I will check the catalog for a suitable display in the Standard tier...". Do this for every category.

            **4. FINAL OUTPUT FORMAT (STRICTLY ENFORCED):**
            Your final output must be in two parts: a "System Design Summary" and the "Bill of Quantities" table. The table MUST be a valid Markdown table and include a final total cost line.

            **EXAMPLE OF PERFECT OUTPUT:**
            ---
            ### System Design Summary
            This system is designed for a Medium Conference Room, focusing on reliability and ease of use, aligning with the 'Standard' budget. The 65-inch display meets AVIXA standards for room size. The Poly Studio X52 provides an all-in-one conferencing solution certified for both Teams and Zoom, simplifying user interaction. Audio is enhanced with an expansion microphone for full room coverage. All components are selected for their proven compatibility and performance in a corporate environment.

            ### Bill of Quantities
            | Category | Brand | Product Name | Qty | Unit Price ($) | Total Price ($) |
            | :--- | :--- | :--- | :---: | ---: | ---: |
            | Displays & Projectors | Samsung | QM65C 65" UHD Professional Display | 1 | 1450.00 | 1450.00 |
            | Mounts & Racks | Chief | LTM1U Universal Tilt Wall Mount | 1 | 299.99 | 299.99 |
            | Video Conferencing | Poly | Studio X52 All-In-One Video Bar with TC10 Controller | 1 | 2499.00 | 2499.00 |
            | Cables & Connectivity | AWAV | Premium Cable & Connector Kit | 1 | 250.00 | 250.00 |
            | Installation & Services | AWAV | Installation, Testing & Commissioning | 1 | 999.00 | 999.00 |
            | **TOTAL ESTIMATED COST** | | | | | **$5,497.99** |
            ---
            
            **NOW, GENERATE THE BOQ FOR THE USER'S REQUEST.**
            """

            try:
                response = model.generate_content(prompt)
                
                st.subheader("✅ Generated Bill of Quantities")

                # ## NEW ## We now parse the response to find the table and display it beautifully.
                # This gives the app a much more professional feel than just printing raw text.
                response_text = response.text
                
                # Use a regular expression to find the Markdown table in the response
                table_match = re.search(r'(\|.*\|[\s\r\n]*)+(?:\|.*\|)', response_text, re.MULTILINE)
                
                if table_match:
                    table_str = table_match.group(0)
                    
                    # Read the markdown table into a pandas DataFrame
                    from io import StringIO
                    df_boq = pd.read_csv(StringIO(table_str), sep='|', index_col=1).dropna(axis=1, how='all').iloc[1:]
                    df_boq.columns = [col.strip() for col in df_boq.columns] # Clean up column headers
                    
                    # Display the rest of the text (like the Design Summary)
                    st.markdown(response_text.replace(table_str, ""))
                    
                    # Display the BOQ table using Streamlit's dataframe component
                    st.dataframe(df_boq, use_container_width=True)
                else:
                    # If we can't find a table, just show the raw text
                    st.markdown(response_text)

            except Exception as e:
                st.error(f"An error occurred while generating the BOQ: {e}")
                st.text("Raw Response from AI (for debugging):")
                st.code(response.text)
    else:
        st.error("Could not generate BOQ. Please check if data files are loaded and the API key is correct.")
