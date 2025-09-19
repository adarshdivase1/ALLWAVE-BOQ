import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import json
import time
import math
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
from pathlib import Path

# ===== CONFIGURATION & SETUP =====
st.set_page_config(
    page_title="Enterprise AV BOQ Generator",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== NEW DATA MODELS (MATCHING YOUR CSV) =====
@dataclass
class AVProduct:
    id: str
    category: str
    brand: str
    name: str
    price_usd: float
    features: str
    tier: str
    use_case_tags: List[str]
    compatibility_tags: List[str]
    last_updated: datetime = datetime.now()

@dataclass
class RoomSpecification:
    type: str
    length_ft: float
    width_ft: float
    height_ft: float
    occupancy: int
    primary_use: str
    viewing_distance_max: float
    ambient_light: str
    acoustics: str
    power_available: str
    network_infrastructure: str

@dataclass
class ComplianceResult:
    standard: str
    status: str
    score: float
    issues: List[str]
    recommendations: List[str]
    critical_failures: List[str]

@dataclass
class ProjectInfo:
    id: str
    name: str
    client: str
    location: str
    designer: str
    created_date: datetime
    budget_range: Tuple[float, float]
    timeline_weeks: int
    security_level: str

# ===== NEW DATA LOADING FUNCTION (FOR YOUR CSV) =====
@st.cache_data(ttl=3600)  # Caches the data and refetches from GitHub every hour
def load_products_from_github():
    """
    Fetches the master product catalog from your GitHub repository CSV.
    """
    url = "https://raw.githubusercontent.com/adarshdivase1/ALLWAVE-BOQ/main/master_product_catalog.csv"
    try:
        df = pd.read_csv(url)
        # Rename 'price' to 'price_usd' to match dataclass
        df = df.rename(columns={'price': 'price_usd'})
        # Fill missing values with sensible defaults
        df['price_usd'] = pd.to_numeric(df['price_usd'], errors='coerce').fillna(0.0)
        df.fillna('', inplace=True)
    except Exception as e:
        st.error(f"Failed to load product catalog from GitHub: {e}")
        return {}

    products_by_category = {}

    for index, row in df.iterrows():
        try:
            # Generate a unique ID since one isn't provided in the CSV
            product_id = f"{row['brand']}_{row['name']}_{index}"
            
            product = AVProduct(
                id=product_id,
                category=str(row['category']),
                brand=str(row['brand']),
                name=str(row['name']),
                price_usd=float(row['price_usd']),
                features=str(row['features']),
                tier=str(row['tier']),
                use_case_tags=str(row['use_case_tags']).split(',') if row['use_case_tags'] else [],
                compatibility_tags=str(row['compatibility_tags']).split(',') if row['compatibility_tags'] else []
            )

            if product.category not in products_by_category:
                products_by_category[product.category] = []
            products_by_category[product.category].append(product)
        except Exception as e:
            # Skip rows with errors
            continue
            
    return products_by_category

# ===== ENTERPRISE PRODUCT DATABASE =====
class EnterpriseProductCatalog:
    def __init__(self):
        self.products = load_products_from_github()
        self.compliance_db = ComplianceDatabase()

class ComplianceDatabase:
    """Stores general AVIXA principles."""
    def get_avixa_standards(self) -> Dict[str, Any]:
        return {
            "display_sizing": {"min_size_recommendation": "Display should be large enough for farthest viewer."},
            "audio_requirements": {"min_coverage": "Audio system should provide clear coverage for all participants."},
            "control_standards": {"min_control": "Complex systems should have a unified control interface."},
            "infrastructure": {"min_power": "System power should not exceed circuit limits."}
        }

# ===== REFACTORED AVIXA COMPLIANCE ENGINE =====
class AVIXAComplianceEngine:
    def __init__(self):
        self.standards = ComplianceDatabase().get_avixa_standards()

    def validate_system_design(self, room_specs: RoomSpecification, selected_products: List[AVProduct]) -> List[ComplianceResult]:
        """Simplified AVIXA compliance validation based on new data."""
        results = []
        # Basic check: Ensure a display exists if the use case is visual
        if room_specs.primary_use in ["Presentations", "Video Conferencing", "Hybrid Meeting"]:
            if not any(p.category == "Displays & Projectors" for p in selected_products):
                results.append(ComplianceResult("Display", "CRITICAL", 20, [], [], ["No display selected for a visual-focused room."]))
            else:
                 results.append(ComplianceResult("Display", "PASS", 100, [], ["Display is present."], []))

        # Basic check: Ensure audio exists for conferencing
        if room_specs.primary_use in ["Video Conferencing", "Hybrid Meeting"]:
            if not any("Audio" in p.category or "Conferencing" in p.category for p in selected_products):
                 results.append(ComplianceResult("Audio", "CRITICAL", 20, [], [], ["No audio or conferencing equipment selected for a meeting room."]))
            else:
                 results.append(ComplianceResult("Audio", "PASS", 100, [], ["Audio/VC equipment is present."], []))
        
        return results

# ===== REFACTORED AI-POWERED OPTIMIZATION ENGINE =====
class AIOptimizationEngine:
    def __init__(self, product_catalog: EnterpriseProductCatalog):
        self.catalog = product_catalog

    def generate_alternative_by_tier(self, tier: str, room_specs: RoomSpecification) -> Dict[str, Any]:
        """Generates a simple system configuration based on the tier."""
        config = {"tier": tier, "products": [], "total_cost": 0.0}
        
        all_products = [p for cat_prods in self.catalog.products.values() for p in cat_prods]
        
        # Select one product from key categories based on tier
        key_categories = ["Displays & Projectors", "Video Conferencing", "Audio: Microphones & Conferencing"]
        
        for cat in key_categories:
            products_in_cat = [p for p in all_products if p.category == cat and p.tier.lower() == tier.lower()]
            if not products_in_cat: # If no exact match, try to find any product in category
                products_in_cat = [p for p in all_products if p.category == cat]

            if products_in_cat:
                # Select the median-priced product for that tier and category
                sorted_products = sorted(products_in_cat, key=lambda x: x.price_usd)
                selected_product = sorted_products[len(sorted_products) // 2]
                config["products"].append(selected_product)
                config["total_cost"] += selected_product.price_usd

        # Add generic installation
        install_product = next((p for p in all_products if p.category == "Installation & Services"), None)
        if install_product:
            config["products"].append(install_product)
            config["total_cost"] += install_product.price_usd
            
        return config

# ===== PROFESSIONAL DOCUMENT GENERATOR =====
class ProfessionalDocumentGenerator:
    def generate_comprehensive_boq(self, project_info: ProjectInfo, room_specs: RoomSpecification, products: List[AVProduct]) -> bytes:
        html_content = self._create_boq_html_template(project_info, room_specs, products)
        return html_content.encode('utf-8')

    def _create_boq_html_template(self, project_info: ProjectInfo, room_specs: RoomSpecification, products: List[AVProduct]) -> str:
        # (This function remains largely the same, but simplified for brevity in this view)
        product_rows_html = ""
        total_cost = 0
        product_counts = {}
        for product in products:
            if product.id in product_counts:
                product_counts[product.id]['quantity'] += 1
            else:
                product_counts[product.id] = {'product': product, 'quantity': 1}

        for item_id, item_data in product_counts.items():
            product = item_data['product']
            quantity = item_data['quantity']
            line_total = product.price_usd * quantity
            total_cost += line_total
            product_rows_html += f"""
                <tr>
                    <td>{product.name}</td>
                    <td>{product.brand}</td>
                    <td>{product.category}</td>
                    <td>{quantity}</td>
                    <td>${product.price_usd:,.2f}</td>
                    <td>${line_total:,.2f}</td>
                </tr>
            """

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>AV Bill of Quantities - {project_info.name}</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; }}
                .header {{ background: #1e3a8a; color: white; padding: 20px; margin-bottom: 20px; }}
                .section {{ border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; background: #f8fafc; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #e2e8f0; padding: 10px; text-align: left; }}
                th {{ background: #f1f5f9; }}
                .total-row {{ font-weight: bold; background: #e2e8f0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>AV System Bill of Quantities</h1>
                <h2>{project_info.name} for {project_info.client}</h2>
            </div>
            <div class="section">
                <h3>Equipment List</h3>
                <table>
                    <thead><tr><th>Item</th><th>Brand</th><th>Category</th><th>Qty</th><th>Unit Price</th><th>Total Price</th></tr></thead>
                    <tbody>{product_rows_html}</tbody>
                    <tfoot><tr class="total-row"><td colspan="5">Total System Cost</td><td>${total_cost:,.2f}</td></tr></tfoot>
                </table>
            </div>
        </body>
        </html>
        """
        return html_template

# ===== STREAMLIT INTERFACE =====
def create_enhanced_streamlit_interface():
    if 'project_info' not in st.session_state: st.session_state.project_info = None
    if 'room_specs' not in st.session_state: st.session_state.room_specs = None
    if 'selected_products' not in st.session_state: st.session_state.selected_products = []

    st.markdown(
        "<div style='background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 2rem; border-radius: 10px;'>"
        "<h1 style='color: white;'>🏢 Enterprise AV BOQ Generator</h1>"
        "</div>", unsafe_allow_html=True
    )

    with st.sidebar:
        st.header("Project Configuration")
        with st.expander("Project Details", expanded=True):
            project_name = st.text_input("Project Name", "Conference Room Alpha")
            client_name = st.text_input("Client", "Enterprise Corp")
            location = st.text_input("Location", "New York, NY")
            designer_name = st.text_input("AV Designer", "John Smith, CTS")
            budget_min, budget_max = st.slider("Budget Range ($)", 1000, 100000, (25000, 50000))
            timeline_weeks = st.slider("Project Timeline (weeks)", 2, 20, 8)

        with st.expander("Room Specifications", expanded=True):
            room_type = st.selectbox("Room Type", ["Conference Room", "Training Room", "Board Room"])
            col1, col2, col3 = st.columns(3)
            with col1: length_ft = st.number_input("Length (ft)", 8.0, 100.0, 20.0, 0.5)
            with col2: width_ft = st.number_input("Width (ft)", 8.0, 100.0, 16.0, 0.5)
            with col3: height_ft = st.number_input("Height (ft)", 8.0, 20.0, 10.0, 0.5)
            occupancy = st.number_input("Max Occupancy", 2, 500, 12)
            primary_use = st.selectbox("Primary Use", ["Presentations", "Video Conferencing", "Hybrid Meeting"])
            viewing_distance = st.number_input("Max Viewing Distance (ft)", 5.0, 50.0, 15.0, 0.5)
    
    if st.sidebar.button("Initialize Project", type="primary"):
        st.session_state.project_info = ProjectInfo(
            id=f"PRJ_{int(time.time())}", name=project_name, client=client_name, location=location,
            designer=designer_name, created_date=datetime.now(), budget_range=(budget_min, budget_max),
            timeline_weeks=timeline_weeks, security_level="Standard"
        )
        st.session_state.room_specs = RoomSpecification(
            type=room_type, length_ft=length_ft, width_ft=width_ft, height_ft=height_ft, occupancy=occupancy, 
            primary_use=primary_use, viewing_distance_max=viewing_distance, ambient_light="Medium", 
            acoustics="Average", power_available="Standard 15A", network_infrastructure="Managed Switch"
        )
        st.success("✅ Project initialized successfully!")
        st.rerun()

    if st.session_state.project_info and st.session_state.room_specs:
        tabs = ["🎯 System Design", "📊 Compliance", "🤖 AI Optimization", "📄 Professional BOQ", "📈 Analytics"]
        tab1, tab2, tab3, tab4, tab5 = st.tabs(tabs)
        
        with tab1: create_system_design_interface()
        with tab2: create_compliance_interface()
        with tab3: create_optimization_interface()
        with tab4: create_boq_generation_interface()
        with tab5: create_analytics_interface()

def create_system_design_interface():
    st.header("System Design & Product Selection")
    catalog = EnterpriseProductCatalog()

    if not catalog.products:
        st.error("The product catalog could not be loaded. Please check the data source.")
        return

    categories = sorted(list(catalog.products.keys()))
    selected_category = st.selectbox("Select Product Category", categories)
    
    products_in_category = catalog.products.get(selected_category, [])
    for product in products_in_category:
        with st.expander(f"{product.brand} {product.name} - ${product.price_usd:,.2f}"):
            st.write(f"**Tier:** {product.tier}")
            st.write(f"**Features:** {product.features}")
            if product.use_case_tags: st.write(f"**Use Cases:** {', '.join(product.use_case_tags)}")
            if st.button(f"Add to BOQ", key=f"add_{product.id}"):
                st.session_state.selected_products.append(product)
                st.success(f"Added {product.name}")
                st.rerun()

    if st.session_state.selected_products:
        st.subheader("Current Bill of Quantities")
        total_cost = 0
        for i, p in enumerate(st.session_state.selected_products):
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1: st.write(f"**{p.name}** ({p.brand})")
            with col2: st.write(f"${p.price_usd:,.2f}"); total_cost += p.price_usd
            with col3: 
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.selected_products.pop(i)
                    st.rerun()
        st.markdown(f"### **Total Cost: ${total_cost:,.2f}**")

def create_compliance_interface():
    st.header("AVIXA Compliance Analysis")
    if not st.session_state.selected_products:
        st.warning("Please add products to the BOQ first.")
        return

    engine = AVIXAComplianceEngine()
    results = engine.validate_system_design(st.session_state.room_specs, st.session_state.selected_products)
    
    if not results:
        st.info("No specific compliance checks apply to the current selection.")

    for result in results:
        if result.status == "CRITICAL":
            st.error(f"**{result.standard}:** {result.critical_failures[0]}")
        elif result.status == "PASS":
            st.success(f"**{result.standard}:** {result.recommendations[0]}")

def create_optimization_interface():
    st.header("AI-Powered Optimization")
    st.info("This feature generates alternative system configurations based on price tiers.")
    
    if st.button("Generate Alternative Configurations", type="primary"):
        engine = AIOptimizationEngine(EnterpriseProductCatalog())
        tiers = ["Economy", "Standard", "Premium"]
        configs = [engine.generate_alternative_by_tier(t, st.session_state.room_specs) for t in tiers]
        
        for config in configs:
            with st.expander(f"**{config['tier']} Tier Suggestion - ${config['total_cost']:,.2f}**"):
                for p in config['products']:
                    st.write(f"- **{p.name}** ({p.brand})")
                if st.button(f"Use This {config['tier']} Configuration", key=f"use_{config['tier']}"):
                    st.session_state.selected_products = config['products']
                    st.success(f"{config['tier']} configuration loaded!")
                    st.rerun()

def create_boq_generation_interface():
    st.header("Professional BOQ Generation")
    if not st.session_state.selected_products:
        st.warning("Please add products to the BOQ first.")
        return

    if st.button("Generate Professional BOQ", type="primary"):
        generator = ProfessionalDocumentGenerator()
        doc = generator.generate_comprehensive_boq(st.session_state.project_info, st.session_state.room_specs, st.session_state.selected_products)
        st.download_button("Download BOQ (HTML)", doc, f"BOQ_{st.session_state.project_info.name}.html", "text/html")

def create_analytics_interface():
    st.header("Project Analytics & Insights")
    if not st.session_state.selected_products:
        st.warning("Please add products to the BOQ first.")
        return
    
    df = pd.DataFrame([asdict(p) for p in st.session_state.selected_products])
    
    st.subheader("Cost Breakdown by Category")
    category_costs = df.groupby('category')['price_usd'].sum().reset_index()
    if not category_costs.empty:
        fig_pie = px.pie(category_costs, values='price_usd', names='category', title="System Cost Distribution")
        st.plotly_chart(fig_pie, width='stretch')
        
    st.subheader("Brand Distribution")
    col1, col2 = st.columns(2)
    with col1:
        brand_counts = df['brand'].value_counts().reset_index()
        fig_brand_count = px.bar(brand_counts, x='brand', y='count', title="Products by Brand")
        st.plotly_chart(fig_brand_count, width='stretch')
    with col2:
        brand_costs = df.groupby('brand')['price_usd'].sum().reset_index()
        fig_brand_cost = px.bar(brand_costs, x='brand', y='price_usd', title="Cost by Brand")
        st.plotly_chart(fig_brand_cost, width='stretch')

# ===== MAIN APPLICATION =====
def main():
    try:
        create_enhanced_streamlit_interface()
    except Exception as e:
        st.error(f"An application error occurred: {e}")
        if st.checkbox("Show Debug Information"):
            st.exception(e)

if __name__ == "__main__":
    st.markdown("""
    <style>
        .stMetric > label { font-size: 14px !important; font-weight: 600 !important; }
        .stMetric > div { font-size: 24px !important; font-weight: 700 !important; }
        .stButton > button { width: 100%; }
        div[data-testid="metric-container"] {
            background-color: white; border: 1px solid #e2e8f0; padding: 1rem;
            border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    main()
