import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import google.generativeai as genai
import re
import json
import time
import math
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import base64
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import asyncio
import aiohttp

# ===== CONFIGURATION & SETUP =====
st.set_page_config(
    page_title="Enterprise AV BOQ Generator",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== ENTERPRISE DATA MODELS =====
@dataclass
class AVProduct:
    id: str
    name: str
    brand: str
    category: str
    subcategory: str
    price_usd: float
    specifications: Dict[str, Any]
    compliance: Dict[str, bool]
    warranty_years: int
    lead_time_days: int
    distributor: str
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

# ===== NEW DATA LOADING FUNCTION =====
@st.cache_data(ttl=3600) # Caches the data and refetches from GitHub every hour
def load_products_from_github():
    """
    Fetches the master product catalog from the GitHub repository CSV.
    """
    # The direct "raw" URL to your CSV file
    url = "https://raw.githubusercontent.com/adarshdivase1/ALLWAVE-BOQ/main/master_product_catalog.csv"
    
    # Read the CSV file using pandas
    df = pd.read_csv(url)
    
    # Replace any potential missing values (NaN) with sensible defaults
    df['specifications'] = df['specifications'].fillna('{}')
    df['compliance'] = df['compliance'].fillna('{}')
    df = df.fillna(0) # Fill remaining numeric NaNs with 0

    products_by_category = {}
    
    # Iterate over each row in the DataFrame to create AVProduct objects
    for _, row in df.iterrows():
        try:
            # The 'specifications' and 'compliance' columns are strings, so we parse them as JSON
            # Using .replace("'", "\"") to handle potential single quotes in the data
            specifications_dict = json.loads(row['specifications'].replace("'", "\""))
            compliance_dict = json.loads(row['compliance'].replace("'", "\""))

            product = AVProduct(
                id=str(row['id']),
                name=str(row['name']),
                brand=str(row['brand']),
                category=str(row['category']),
                subcategory=str(row['subcategory']),
                price_usd=float(row['price_usd']),
                specifications=specifications_dict,
                compliance=compliance_dict,
                warranty_years=int(row['warranty_years']),
                lead_time_days=int(row['lead_time_days']),
                distributor=str(row['distributor'])
            )

            # Group the products by category, just like the original code did
            if product.category not in products_by_category:
                products_by_category[product.category] = []
            products_by_category[product.category].append(product)

        except (json.JSONDecodeError, TypeError) as e:
            st.warning(f"Skipping product with ID {row.get('id', 'N/A')} due to a data formatting error: {e}")
            continue # Skip this row if data is malformed

    return products_by_category

# ===== ENTERPRISE PRODUCT DATABASE =====
class EnterpriseProductCatalog:
    def __init__(self):
        # This now calls your new GitHub loading function
        self.products = load_products_from_github()
        self.pricing_api = PricingAPIClient()
        self.compliance_db = ComplianceDatabase()

class PricingAPIClient:
    """Mock pricing API client for demonstration"""

    async def get_real_time_pricing(self, product_id: str) -> float:
        """Get real-time pricing from distributor APIs"""
        # Simulate API call delay
        await asyncio.sleep(0.1)
        # Mock price fluctuation ±5%
        base_price = self._get_base_price(product_id)
        fluctuation = np.random.uniform(0.95, 1.05)
        return base_price * fluctuation

    def _get_base_price(self, product_id: str) -> float:
        """Get base price for simulation"""
        price_map = {
            "SAMSUNG_QM75R": 2899.00,
            "LG_86UN8570": 3499.00,
            "SHARP_PN_C703B": 4299.00,
            "SHURE_MXA910": 1899.00,
            "QSC_K8_2": 649.00
        }
        return price_map.get(product_id, 1000.00)

class ComplianceDatabase:
    """Compliance standards database"""

    def get_avixa_standards(self) -> Dict[str, Any]:
        return {
            "display_sizing": {
                "max_viewing_distance_formula": "8 * display_height",
                "optimal_viewing_distance": "3 * display_height",
                "minimum_brightness": 300,  # cd/m²
                "contrast_ratio_min": "1000:1",
                "viewing_angle_min": 160  # degrees
            },
            "audio_requirements": {
                "speech_intelligibility_min": 0.60,  # STI
                "background_noise_max": 35,  # dB(A) NC-35
                "sound_pressure_level": (70, 75),  # dB SPL range
                "frequency_response": (100, 8000)  # Hz range for speech
            },
            "control_standards": {
                "response_time_max": 2.0,  # seconds
                "reliability_uptime": 99.9,  # percent
                "user_interface_complexity": "max_3_touches"
            }
        }

# ===== AVIXA COMPLIANCE ENGINE =====
class AVIXAComplianceEngine:
    def __init__(self):
        self.standards = ComplianceDatabase().get_avixa_standards()

    def validate_system_design(self, room_specs: RoomSpecification,
                               selected_products: List[AVProduct]) -> List[ComplianceResult]:
        """Comprehensive AVIXA compliance validation"""
        results = []

        # Display Compliance Validation
        display_result = self._validate_displays(room_specs, selected_products)
        results.append(display_result)

        # Audio System Compliance
        audio_result = self._validate_audio_system(room_specs, selected_products)
        results.append(audio_result)

        # Control System Compliance
        control_result = self._validate_control_system(room_specs, selected_products)
        results.append(control_result)

        # Power and Infrastructure
        infrastructure_result = self._validate_infrastructure(room_specs, selected_products)
        results.append(infrastructure_result)

        return results

    def _validate_displays(self, room_specs: RoomSpecification,
                           products: List[AVProduct]) -> ComplianceResult:
        """Validate display sizing and specifications against AVIXA standards"""
        issues = []
        recommendations = []
        critical_failures = []
        score = 100

        displays = [p for p in products if p.category == "Display"]

        if not displays:
            critical_failures.append("No display selected for system")
            return ComplianceResult("AVIXA Display", "CRITICAL", 0, issues, recommendations, critical_failures)

        for display in displays:
            size_inches = display.specifications.get("size_inches", 0)
            brightness = display.specifications.get("brightness_nits", 0)

            # Calculate display height (16:9 aspect ratio)
            display_height_inches = size_inches * 0.49
            display_height_feet = display_height_inches / 12

            # AVIXA DISCAS Calculation
            max_viewing_distance = room_specs.viewing_distance_max
            optimal_distance = display_height_feet * 3
            max_acceptable_distance = display_height_feet * 8

            # Validation checks
            if max_viewing_distance > max_acceptable_distance:
                issues.append(f"Display too small: Max viewing distance {max_viewing_distance:.1f}ft exceeds limit {max_acceptable_distance:.1f}ft")
                score -= 25

            if max_viewing_distance > optimal_distance * 2:
                recommendations.append(f"Consider larger display: Optimal distance is {optimal_distance:.1f}ft")
                score -= 10

            if brightness < self.standards["display_sizing"]["minimum_brightness"]:
                issues.append(f"Display brightness {brightness} cd/m² below AVIXA minimum {self.standards['display_sizing']['minimum_brightness']} cd/m²")
                score -= 15

            # Viewing angle validation
            viewing_angle = display.specifications.get("viewing_angle", "0°/0°")
            if "178°" not in viewing_angle:
                recommendations.append("Consider display with wider viewing angles for conference room use")
                score -= 5

        status = "PASS" if score >= 80 else "FAIL" if score >= 60 else "CRITICAL"

        return ComplianceResult(
            standard="AVIXA Display Standards",
            status=status,
            score=score,
            issues=issues,
            recommendations=recommendations,
            critical_failures=critical_failures
        )

    def _validate_audio_system(self, room_specs: RoomSpecification,
                               products: List[AVProduct]) -> ComplianceResult:
        """Validate audio system design"""
        issues = []
        recommendations = []
        critical_failures = []
        score = 100

        audio_products = [p for p in products if p.category == "Audio"]

        if not audio_products:
            critical_failures.append("No audio system components selected")
            return ComplianceResult("AVIXA Audio", "CRITICAL", 0, issues, recommendations, critical_failures)

        room_area = room_specs.length_ft * room_specs.width_ft

        # Check microphone coverage
        microphones = [p for p in audio_products if "microphone" in p.name.lower() or "mic" in p.subcategory.lower()]
        speakers = [p for p in audio_products if "speaker" in p.name.lower()]

        if not microphones and room_specs.primary_use in ["Video Conferencing", "Hybrid Meeting"]:
            critical_failures.append("No microphone system for conferencing room")
            score = 0

        if not speakers:
            critical_failures.append("No speaker system selected")
            score = 0

        # Coverage analysis
        total_mic_coverage = sum(p.specifications.get("coverage_diameter_ft", 10)**2 * math.pi/4 for p in microphones)
        if total_mic_coverage < room_area * 0.8:  # 80% coverage minimum
            issues.append("Insufficient microphone coverage for room size")
            score -= 20

        # Frequency response validation
        for audio_item in audio_products:
            freq_response = audio_item.specifications.get("frequency_response", "")
            if "100Hz" not in freq_response or "20kHz" not in freq_response:
                recommendations.append(f"Check frequency response range for {audio_item.name}")
                score -= 5

        status = "PASS" if score >= 80 else "FAIL" if score >= 60 else "CRITICAL"

        return ComplianceResult(
            standard="AVIXA Audio Standards",
            status=status,
            score=score,
            issues=issues,
            recommendations=recommendations,
            critical_failures=critical_failures
        )

    def _validate_control_system(self, room_specs: RoomSpecification,
                                 products: List[AVProduct]) -> ComplianceResult:
        """Validate control system design"""
        issues = []
        recommendations = []
        critical_failures = []
        score = 100

        control_products = [p for p in products if p.category == "Control Systems"]

        if not control_products and len(products) > 3:  # Complex system needs control
            issues.append("Complex system should include dedicated control system")
            score -= 30

        # Check for unified control approach
        video_conf_products = [p for p in products if p.category == "Video Conferencing"]
        if len(video_conf_products) > 1 and not control_products:
            recommendations.append("Multiple video conferencing systems may need unified control")
            score -= 15

        status = "PASS" if score >= 80 else "FAIL" if score >= 60 else "CRITICAL"

        return ComplianceResult(
            standard="AVIXA Control Standards",
            status=status,
            score=score,
            issues=issues,
            recommendations=recommendations,
            critical_failures=critical_failures
        )

    def _validate_infrastructure(self, room_specs: RoomSpecification,
                                 products: List[AVProduct]) -> ComplianceResult:
        """Validate power and infrastructure requirements"""
        issues = []
        recommendations = []
        critical_failures = []
        score = 100

        # Power consumption analysis
        total_power = sum(p.specifications.get("power_consumption", 100) for p in products)

        # Standard 15A circuit = 1800W maximum
        if total_power > 1800:
            issues.append(f"Power consumption {total_power}W exceeds standard 15A circuit capacity")
            recommendations.append("Specify dedicated 20A circuit or power distribution")
            score -= 20

        if total_power > 2400:  # 20A circuit limit
            critical_failures.append("Power requirements exceed 20A circuit capacity")
            score -= 40

        # Check for proper mounting hardware
        displays = [p for p in products if p.category == "Display"]
        mounts = [p for p in products if "mount" in p.category.lower()]

        if displays and not mounts:
            issues.append("Display mounting hardware not included in BOQ")
            score -= 15

        # Cable and connectivity check
        cables = [p for p in products if "cable" in p.category.lower()]
        if len(products) > 2 and not cables:
            recommendations.append("Consider including necessary cables and connectivity")
            score -= 10

        status = "PASS" if score >= 80 else "FAIL" if score >= 60 else "CRITICAL"

        return ComplianceResult(
            standard="Infrastructure Requirements",
            status=status,
            score=score,
            issues=issues,
            recommendations=recommendations,
            critical_failures=critical_failures
        )

# ===== AI-POWERED OPTIMIZATION ENGINE =====
class AIOptimizationEngine:
    def __init__(self, product_catalog: EnterpriseProductCatalog):
        self.catalog = product_catalog

    def optimize_system_design(self, room_specs: RoomSpecification,
                               requirements: Dict, budget_constraint: float) -> Dict[str, Any]:
        """AI-powered system optimization"""

        optimization_results = {
            "cost_optimization": self._optimize_for_cost(room_specs, requirements, budget_constraint),
            "performance_optimization": self._optimize_for_performance(room_specs, requirements),
            "future_proofing": self._analyze_future_proofing(room_specs, requirements),
            "risk_assessment": self._assess_project_risks(room_specs, requirements),
            "alternative_recommendations": self._generate_alternatives(room_specs, requirements)
        }

        return optimization_results

    def _optimize_for_cost(self, room_specs: RoomSpecification,
                           requirements: Dict, budget: float) -> Dict[str, Any]:
        """Cost optimization analysis"""

        # Generate multiple system configurations at different price points
        configurations = []

        # Economy configuration (70% of budget)
        economy_budget = budget * 0.7
        economy_config = self._generate_configuration(room_specs, requirements, economy_budget, "economy")
        configurations.append(economy_config)

        # Standard configuration (budget target)
        standard_config = self._generate_configuration(room_specs, requirements, budget, "standard")
        configurations.append(standard_config)

        # Premium configuration (130% of budget)
        premium_budget = budget * 1.3
        premium_config = self._generate_configuration(room_specs, requirements, premium_budget, "premium")
        configurations.append(premium_config)

        return {
            "configurations": configurations,
            "cost_savings_opportunities": self._identify_cost_savings(room_specs, requirements),
            "value_engineering_suggestions": self._suggest_value_engineering(room_specs, requirements)
        }

    def _generate_configuration(self, room_specs: RoomSpecification,
                                requirements: Dict, budget: float, tier: str) -> Dict[str, Any]:
        """Generate system configuration for specific budget and tier"""

        config = {
            "tier": tier,
            "budget_target": budget,
            "products": [],
            "total_cost": 0,
            "performance_score": 0,
            "compliance_score": 0
        }

        # Display selection based on room size and budget
        room_diagonal = math.sqrt(room_specs.length_ft**2 + room_specs.width_ft**2)
        optimal_display_size = min(max(int(room_diagonal * 2.5), 55), 86)
        
        # Select display based on tier
        all_displays = self.catalog.products.get("Display", [])
        if all_displays:
            suitable_displays = [d for d in all_displays if d.specifications.get("size_inches", 0) >= optimal_display_size - 10]
            if suitable_displays:
                if tier == "economy":
                    selected_display = min(suitable_displays, key=lambda x: x.price_usd)
                elif tier == "premium":
                    selected_display = max(suitable_displays, key=lambda x: x.specifications.get("brightness_nits", 0))
                else:  # standard
                    selected_display = sorted(suitable_displays,
                                            key=lambda x: x.price_usd + (1000 - x.specifications.get("brightness_nits", 0)))[0]
                
                config["products"].append(selected_display)
                config["total_cost"] += selected_display.price_usd

        # Audio system selection
        all_audio_products = self.catalog.products.get("Audio", [])
        if all_audio_products:
            if room_specs.primary_use in ["Video Conferencing", "Hybrid Meeting"]:
                microphones = [p for p in all_audio_products if "microphone" in p.name.lower()]
                if microphones:
                    selected_mic = min(microphones, key=lambda p: p.price_usd) # Simple selection
                    config["products"].append(selected_mic)
                    config["total_cost"] += selected_mic.price_usd

            speakers = [p for p in all_audio_products if "speaker" in p.name.lower()]
            if speakers:
                room_area = room_specs.length_ft * room_specs.width_ft
                speaker_count = max(2, int(room_area / 200))
                
                if tier == "economy":
                    selected_speaker = min(speakers, key=lambda x: x.price_usd)
                else:
                    selected_speaker = max(speakers, key=lambda x: int(re.search(r'\d+', str(x.specifications.get("max_spl", "0"))).group()))

                for _ in range(speaker_count):
                    config["products"].append(selected_speaker)
                    config["total_cost"] += selected_speaker.price_usd

        # Control system for premium tier
        all_control_systems = self.catalog.products.get("Control Systems", [])
        if (tier == "premium" or len(config["products"]) > 3) and all_control_systems:
            selected_control = min(all_control_systems, key=lambda p: p.price_usd)
            config["products"].append(selected_control)
            config["total_cost"] += selected_control.price_usd

        # Add mounting hardware
        all_mounts = self.catalog.products.get("Mounts & Hardware", [])
        if any(p.category == "Display" for p in config['products']) and all_mounts:
             wall_mounts = [m for m in all_mounts if "wall" in m.name.lower()]
             if wall_mounts:
                config["products"].append(wall_mounts[0])
                config["total_cost"] += wall_mounts[0].price_usd

        # Calculate performance and compliance scores
        config["performance_score"] = self._calculate_performance_score(config["products"], room_specs)
        config["compliance_score"] = self._calculate_compliance_score(config["products"], room_specs)

        return config

    def _calculate_performance_score(self, products: List[AVProduct], room_specs: RoomSpecification) -> float:
        """Calculate overall system performance score"""
        score = 0
        total_weight = 0

        for product in products:
            product_score = 50  # Base score
            weight = 1

            if product.category == "Display":
                brightness = product.specifications.get("brightness_nits", 300)
                product_score += min((brightness - 300) / 10, 50)
                weight = 3

            elif product.category == "Audio":
                max_spl = product.specifications.get("max_spl", "100 dB SPL")
                spl_value = int(re.search(r'\d+', str(max_spl)).group()) if re.search(r'\d+', str(max_spl)) else 100
                product_score += min((spl_value - 100) / 2, 50)
                weight = 2

            elif product.category == "Control Systems":
                product_score += 30
                weight = 2

            score += product_score * weight
            total_weight += weight

        return min(score / total_weight if total_weight > 0 else 0, 100)

    def _calculate_compliance_score(self, products: List[AVProduct], room_specs: RoomSpecification) -> float:
        """Calculate AVIXA compliance score"""
        compliance_engine = AVIXAComplianceEngine()
        results = compliance_engine.validate_system_design(room_specs, products)

        total_score = sum(result.score for result in results)
        return total_score / len(results) if results else 0

    def _identify_cost_savings(self, room_specs: RoomSpecification, requirements: Dict) -> List[str]:
        """Identify potential cost savings opportunities"""
        savings = [
            "Consider standardizing on single brand for volume discounts",
            "Evaluate refurbished or previous-generation products",
            "Bundle installation and support services",
            "Negotiate extended payment terms with distributors",
            "Consider leasing options for high-value equipment"
        ]
        if room_specs.primary_use != "Video Conferencing":
            savings.append("Remove advanced conferencing features if not required")
        return savings

    def _suggest_value_engineering(self, room_specs: RoomSpecification, requirements: Dict) -> List[str]:
        """Suggest value engineering opportunities"""
        suggestions = [
            "Use standard HDMI instead of fiber optic for shorter runs",
            "Implement software-based control instead of dedicated hardware",
            "Consider all-in-one solutions to reduce component count",
            "Use ceiling-mounted speakers instead of in-wall installation",
            "Standardize on PoE+ power delivery where possible"
        ]
        return suggestions

    def _optimize_for_performance(self, room_specs, requirements):
        return {}

    def _analyze_future_proofing(self, room_specs, requirements):
        return {}

    def _assess_project_risks(self, room_specs, requirements):
        return {}

    def _generate_alternatives(self, room_specs, requirements):
        return {}

# ===== PROFESSIONAL DOCUMENT GENERATOR =====
class ProfessionalDocumentGenerator:
    def __init__(self):
        self.template_path = Path("templates")
        self.template_path.mkdir(exist_ok=True)

    def generate_comprehensive_boq(self, project_info: ProjectInfo,
                                   room_specs: RoomSpecification,
                                   products: List[AVProduct],
                                   compliance_results: List[ComplianceResult],
                                   optimization_results: Dict) -> bytes:
        """Generate professional BOQ document"""
        html_content = self._create_boq_html_template(
            project_info, room_specs, products,
            compliance_results, optimization_results
        )
        return self._html_to_pdf(html_content)

    def _create_boq_html_template(self, project_info: ProjectInfo,
                                  room_specs: RoomSpecification,
                                  products: List[AVProduct],
                                  compliance_results: List[ComplianceResult],
                                  optimization_results: Dict) -> str:
        """Create professional HTML template for BOQ"""
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Professional AV Bill of Quantities - {project_info.name}</title>
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                          color: white; padding: 30px; margin: -20px -20px 30px; }}
                .project-info {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }}
                .section {{ background: #f8fafc; border-left: 4px solid #3b82f6; padding: 20px; margin: 20px 0; }}
                .compliance-pass {{ color: #10b981; font-weight: bold; }}
                .compliance-fail {{ color: #ef4444; font-weight: bold; }}
                .product-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .product-table th, .product-table td {{ border: 1px solid #e2e8f0; padding: 12px; text-align: left; }}
                .product-table th {{ background: #f1f5f9; font-weight: 600; }}
                .total-row {{ background: #fee2e2; font-weight: bold; }}
                .recommendations {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Professional AV System Bill of Quantities</h1>
                <h2>{project_info.name}</h2>
                <p>Client: {project_info.client} | Location: {project_info.location}</p>
                <p>Designer: {project_info.designer} | Date: {project_info.created_date.strftime('%B %d, %Y')}</p>
            </div>

            <div class="section">
                <h3>Executive Summary</h3>
                <div class="project-info">
                    <div>
                        <strong>Project Overview:</strong><br>
                        Comprehensive AV system design for {room_specs.type} application.<br><br>
                        <strong>Room Specifications:</strong><br>
                        • Dimensions: {room_specs.length_ft}' × {room_specs.width_ft}' × {room_specs.height_ft}'<br>
                        • Occupancy: {room_specs.occupancy} persons<br>
                        • Primary Use: {room_specs.primary_use}
                    </div>
                    <div>
                        <strong>Budget Information:</strong><br>
                        Target Range: ${project_info.budget_range[0]:,.2f} - ${project_info.budget_range[1]:,.2f}<br><br>
                        <strong>Timeline:</strong><br>
                        Estimated Duration: {project_info.timeline_weeks} weeks<br>
                        Security Level: {project_info.security_level}
                    </div>
                </div>
            </div>

            <div class="section">
                <h3>Equipment Bill of Quantities</h3>
                <table class="product-table">
                    <thead>
                        <tr>
                            <th>Item</th>
                            <th>Brand</th>
                            <th>Model</th>
                            <th>Category</th>
                            <th>Qty</th>
                            <th>Unit Price</th>
                            <th>Total Price</th>
                            <th>Lead Time</th>
                        </tr>
                    </thead>
                    <tbody>
        """

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
            html_template += f"""
                        <tr>
                            <td>{product.name}</td>
                            <td>{product.brand}</td>
                            <td>{product.id}</td>
                            <td>{product.category}</td>
                            <td>{quantity}</td>
                            <td>${product.price_usd:,.2f}</td>
                            <td>${line_total:,.2f}</td>
                            <td>{product.lead_time_days} days</td>
                        </tr>
            """

        html_template += f"""
                        <tr class="total-row">
                            <td colspan="6"><strong>Total System Cost</strong></td>
                            <td><strong>${total_cost:,.2f}</strong></td>
                            <td></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        """

        if compliance_results:
            html_template += """
            <div class="section">
                <h3>AVIXA Compliance Analysis</h3>
            """
            for result in compliance_results:
                status_class = "compliance-pass" if result.status == "PASS" else "compliance-fail"
                html_template += f"""
                    <h4>{result.standard}</h4>
                    <p class="{status_class}">Status: {result.status} (Score: {result.score:.1f}/100)</p>
                """
                if result.issues:
                    html_template += "<strong>Issues:</strong><ul>" + "".join(f"<li>{issue}</li>" for issue in result.issues) + "</ul>"
                if result.recommendations:
                    html_template += "<div class='recommendations'><strong>Recommendations:</strong><ul>" + "".join(f"<li>{rec}</li>" for rec in result.recommendations) + "</ul></div>"
            html_template += "</div>"

        if optimization_results and 'cost_optimization' in optimization_results:
            cost_opt = optimization_results['cost_optimization']
            html_template += """
            <div class="section">
                <h3>System Optimization Analysis</h3>
                <p>Cost optimization and performance analysis results:</p>
                <h4>Alternative Configurations</h4>
                <table class="product-table">
                    <thead>
                        <tr>
                            <th>Configuration</th>
                            <th>Total Cost</th>
                            <th>Performance Score</th>
                            <th>Compliance Score</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for config in cost_opt.get('configurations', []):
                html_template += f"""
                        <tr>
                            <td>{config['tier'].title()}</td>
                            <td>${config['total_cost']:,.2f}</td>
                            <td>{config['performance_score']:.1f}/100</td>
                            <td>{config['compliance_score']:.1f}/100</td>
                        </tr>
                """
            html_template += "</tbody></table></div>"

        html_template += """
            <div class="section">
                <h3>Installation and Support Notes</h3>
                <p><strong>Installation Requirements:</strong></p>
                <ul>
                    <li>Professional installation required for all components</li>
                    <li>Electrical work must be performed by licensed electrician</li>
                    <li>Network configuration requires IT coordination</li>
                    <li>System commissioning and training included</li>
                </ul>
                <p><strong>Warranty Coverage:</strong></p>
                <ul>
                    <li>Equipment warranties as specified per manufacturer</li>
                    <li>Installation warranty: 1 year parts and labor</li>
                    <li>Extended support options available</li>
                </ul>
            </div>
            <div class="section">
                <h3>Terms and Conditions</h3>
                <ul>
                    <li>Prices valid for 30 days from quote date</li>
                    <li>Final pricing subject to current distributor rates</li>
                    <li>Installation scheduling based on equipment availability</li>
                    <li>Change orders may affect timeline and pricing</li>
                    <li>Client approval required before procurement</li>
                </ul>
            </div>
        </body>
        </html>
        """
        return html_template

    def _html_to_pdf(self, html_content: str) -> bytes:
        """Convert HTML to PDF (placeholder - implement with weasyprint or similar)"""
        return html_content.encode('utf-8')

# ===== ENHANCED STREAMLIT INTERFACE =====
def create_enhanced_streamlit_interface():
    """Enhanced Streamlit interface with professional features"""
    if 'project_info' not in st.session_state:
        st.session_state.project_info = None
    if 'room_specs' not in st.session_state:
        st.session_state.room_specs = None
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = []
    if 'optimization_results' not in st.session_state:
        st.session_state.optimization_results = {}

    st.markdown("""
        <div style='background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                    padding: 2rem; margin: -1rem -1rem 2rem; border-radius: 10px;'>
            <h1 style='color: white; margin: 0;'>🏢 Enterprise AV BOQ Generator</h1>
            <p style='color: #e2e8f0; margin: 0.5rem 0 0;'>Professional Audio-Visual System Design & Specification Tool</p>
        </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.header("Project Configuration")
        with st.expander("Project Details", expanded=True):
            project_name = st.text_input("Project Name", "Conference Room Alpha")
            client_name = st.text_input("Client", "Enterprise Corp")
            location = st.text_input("Location", "New York, NY")
            designer_name = st.text_input("AV Designer", "John Smith, CTS")
            budget_min = st.number_input("Minimum Budget ($)", 10000, 1000000, 25000)
            budget_max = st.number_input("Maximum Budget ($)", budget_min, 1000000, 50000)
            timeline_weeks = st.slider("Project Timeline (weeks)", 2, 20, 8)
            security_level = st.selectbox("Security Level", ["Standard", "Enhanced", "High Security", "Top Secret"])

        with st.expander("Room Specifications", expanded=True):
            room_type = st.selectbox("Room Type", ["Conference Room", "Training Room", "Board Room", "Auditorium", "Classroom", "Huddle Space", "Multi-Purpose Room", "Control Room"])
            col1, col2, col3 = st.columns(3)
            with col1: length_ft = st.number_input("Length (ft)", 8.0, 100.0, 20.0, 0.5)
            with col2: width_ft = st.number_input("Width (ft)", 8.0, 100.0, 16.0, 0.5)
            with col3: height_ft = st.number_input("Height (ft)", 8.0, 20.0, 10.0, 0.5)
            occupancy = st.number_input("Max Occupancy", 2, 500, 12)
            primary_use = st.selectbox("Primary Use", ["Presentations", "Video Conferencing", "Hybrid Meeting", "Training", "Collaboration", "Entertainment"])
            viewing_distance = st.number_input("Max Viewing Distance (ft)", 5.0, 50.0, 15.0, 0.5)
            ambient_light = st.selectbox("Ambient Light Level", ["Low", "Medium", "High", "Variable"])
            acoustics = st.selectbox("Acoustic Environment", ["Good", "Average", "Poor", "Requires Treatment"])
            power_available = st.selectbox("Power Infrastructure", ["Standard 15A", "20A Available", "30A Available", "Custom"])
            network_infra = st.selectbox("Network Infrastructure", ["Basic Ethernet", "Managed Switch", "Enterprise Network", "Fiber Backbone"])

    if st.sidebar.button("Initialize Project", type="primary"):
        st.session_state.project_info = ProjectInfo(
            id=f"PRJ_{int(time.time())}", name=project_name, client=client_name, location=location,
            designer=designer_name, created_date=datetime.now(), budget_range=(budget_min, budget_max),
            timeline_weeks=timeline_weeks, security_level=security_level
        )
        st.session_state.room_specs = RoomSpecification(
            type=room_type, length_ft=length_ft, width_ft=width_ft, height_ft=height_ft,
            occupancy=occupancy, primary_use=primary_use, viewing_distance_max=viewing_distance,
            ambient_light=ambient_light, acoustics=acoustics, power_available=power_available,
            network_infrastructure=network_infra
        )
        st.success("✅ Project initialized successfully!")
        st.rerun()

    if st.session_state.project_info and st.session_state.room_specs:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 System Design", "📊 AVIXA Compliance", "🤖 AI Optimization", "📄 Professional BOQ", "📈 Analytics"])
        with tab1:
            st.header("System Design & Product Selection")
            create_system_design_interface()
        with tab2:
            st.header("AVIXA Compliance Analysis")
            create_compliance_interface()
        with tab3:
            st.header("AI-Powered Optimization")
            create_optimization_interface()
        with tab4:
            st.header("Professional BOQ Generation")
            create_boq_generation_interface()
        with tab5:
            st.header("Project Analytics & Insights")
            create_analytics_interface()

def create_system_design_interface():
    """System design and product selection interface"""
    catalog = EnterpriseProductCatalog()
    st.subheader("Product Selection")

    # Gracefully handle the case where the catalog might be empty
    if not catalog.products:
        st.error("The product catalog could not be loaded. Please check the data source.")
        return

    categories = list(catalog.products.keys())
    selected_category = st.selectbox("Select Product Category", [cat.replace('_', ' ').title() for cat in categories])

    category_key = selected_category.lower().replace(' ', '_')
    if category_key in catalog.products:
        products_in_category = catalog.products[category_key]
        for product in products_in_category:
            with st.expander(f"{product.brand} {product.name} - ${product.price_usd:,.2f}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Category:** {product.category}")
                    st.write(f"**Subcategory:** {product.subcategory}")
                    st.write(f"**Warranty:** {product.warranty_years} years")
                    st.write(f"**Lead Time:** {product.lead_time_days} days")
                with col2:
                    st.write("**Key Specifications:**")
                    for spec_key, spec_value in list(product.specifications.items())[:5]:
                        st.write(f"• {spec_key.replace('_', ' ').title()}: {spec_value}")
                if st.button(f"Add {product.name}", key=f"add_{product.id}"):
                    st.session_state.selected_products.append(product)
                    st.success(f"✅ Added {product.name} to BOQ")
                    st.rerun()

    if st.session_state.selected_products:
        st.subheader("Selected Products")
        total_cost = 0
        for i, product in enumerate(st.session_state.selected_products):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{product.name}** ({product.brand})")
            with col2:
                st.write(f"${product.price_usd:,.2f}")
                total_cost += product.price_usd
            with col3:
                if st.button("Remove", key=f"remove_{i}"):
                    st.session_state.selected_products.pop(i)
                    st.rerun()
        st.markdown(f"### **Total Cost: ${total_cost:,.2f}**")

def create_compliance_interface():
    """AVIXA compliance analysis interface"""
    if not st.session_state.selected_products:
        st.warning("Please select products in the System Design tab first.")
        return

    compliance_engine = AVIXAComplianceEngine()
    results = compliance_engine.validate_system_design(st.session_state.room_specs, st.session_state.selected_products)
    
    overall_score = sum(r.score for r in results) / len(results) if results else 0
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Overall Compliance Score", f"{overall_score:.1f}/100")
    with col2: st.metric("Passing Standards", f"{len([r for r in results if r.status == 'PASS'])}/{len(results)}")
    with col3: st.metric("Critical Issues", sum(len(r.critical_failures) for r in results))

    for result in results:
        status_color = "green" if result.status == "PASS" else "red" if result.status == "CRITICAL" else "orange"
        st.markdown(f"<div style='border-left: 4px solid {status_color}; padding: 1rem; margin: 1rem 0; background: #f8f9fa;'><h4>{result.standard}</h4><p><strong>Status:</strong> <span style='color: {status_color};'>{result.status}</span> <strong>Score:</strong> {result.score:.1f}/100</p></div>", unsafe_allow_html=True)
        if result.critical_failures:
            st.error("**Critical Failures:**")
            for failure in result.critical_failures: st.error(f"• {failure}")
        if result.issues:
            st.warning("**Issues:**")
            for issue in result.issues: st.warning(f"• {issue}")
        if result.recommendations:
            st.info("**Recommendations:**")
            for rec in result.recommendations: st.info(f"• {rec}")

def create_optimization_interface():
    """AI optimization interface"""
    if not st.session_state.selected_products:
        st.warning("Please select products in the System Design tab first.")
        return

    catalog = EnterpriseProductCatalog()
    ai_engine = AIOptimizationEngine(catalog)

    st.subheader("Optimization Parameters")
    col1, col2 = st.columns(2)
    with col1: optimization_type = st.selectbox("Optimization Focus", ["Cost Optimization", "Performance Maximization", "Balanced Approach"])
    with col2: budget_constraint = st.number_input("Budget Constraint ($)", value=st.session_state.project_info.budget_range[1])

    if st.button("Run AI Optimization", type="primary"):
        with st.spinner("Running AI optimization analysis..."):
            requirements = {"optimization_type": optimization_type}
            optimization_results = ai_engine.optimize_system_design(st.session_state.room_specs, requirements, budget_constraint)
            st.session_state.optimization_results = optimization_results
            st.success("✅ Optimization analysis complete!")

    if st.session_state.get('optimization_results'):
        results = st.session_state.optimization_results
        if 'cost_optimization' in results:
            st.subheader("Alternative Configurations")
            config_data = [{'Configuration': config['tier'].title(), 'Total Cost': f"${config['total_cost']:,.2f}", 'Performance Score': f"{config['performance_score']:.1f}/100", 'Compliance Score': f"{config['compliance_score']:.1f}/100"} for config in results['cost_optimization']['configurations']]
            st.dataframe(pd.DataFrame(config_data), use_container_width=True)
            
            st.subheader("Cost Savings Opportunities")
            for saving in results['cost_optimization']['cost_savings_opportunities']: st.info(f"💡 {saving}")
            
            st.subheader("Value Engineering Suggestions")
            for suggestion in results['cost_optimization']['value_engineering_suggestions']: st.info(f"🔧 {suggestion}")

def create_boq_generation_interface():
    """Professional BOQ generation interface"""
    if not st.session_state.selected_products:
        st.warning("Please select products in the System Design tab first.")
        return

    st.subheader("Professional BOQ Generation")
    col1, col2 = st.columns(2)
    with col1:
        include_compliance = st.checkbox("Include AVIXA Compliance Analysis", True)
        include_optimization = st.checkbox("Include AI Optimization Results", True)
    with col2:
        document_format = st.selectbox("Document Format", ["HTML", "PDF (Preview)", "Excel (Preview)"])
        
    if st.button("Generate Professional BOQ", type="primary"):
        with st.spinner("Generating professional BOQ document..."):
            compliance_results = AVIXAComplianceEngine().validate_system_design(st.session_state.room_specs, st.session_state.selected_products) if include_compliance else []
            optimization_results = st.session_state.optimization_results if include_optimization else {}
            
            doc_generator = ProfessionalDocumentGenerator()
            document_content = doc_generator.generate_comprehensive_boq(st.session_state.project_info, st.session_state.room_specs, st.session_state.selected_products, compliance_results, optimization_results)
            
            st.success("✅ BOQ document generated successfully!")
            st.download_button(
                label=f"📄 Download {document_format} BOQ",
                data=document_content,
                file_name=f"BOQ_{st.session_state.project_info.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html"
            )

    st.subheader("BOQ Preview")
    if st.session_state.selected_products:
        boq_data = []
        product_counts = {}
        for p in st.session_state.selected_products:
            product_counts[p.id] = product_counts.get(p.id, {'product': p, 'quantity': 0})
            product_counts[p.id]['quantity'] += 1

        for item_id, item_data in product_counts.items():
            p = item_data['product']
            qty = item_data['quantity']
            boq_data.append({'Item': p.name, 'Brand': p.brand, 'Category': p.category, 'Qty': qty, 'Unit Price': f"${p.price_usd:,.2f}", 'Total': f"${p.price_usd * qty:,.2f}"})
        
        df_boq = pd.DataFrame(boq_data)
        st.dataframe(df_boq, use_container_width=True)
        
        total_cost = sum(p.price_usd for p in st.session_state.selected_products)
        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Total Unique Items", len(product_counts))
        with col2: st.metric("Total Cost", f"${total_cost:,.2f}")
        with col3: st.metric("Avg Lead Time", f"{np.mean([p.lead_time_days for p in st.session_state.selected_products]):.1f} days")
        with col4: st.metric("Budget Utilization", f"{(total_cost / st.session_state.project_info.budget_range[1]) * 100:.1f}%")

def create_analytics_interface():
    """Project analytics and insights interface"""
    if not st.session_state.selected_products:
        st.warning("Please select products in the System Design tab first.")
        return

    st.subheader("Project Analytics Dashboard")
    
    df_products = pd.DataFrame([asdict(p) for p in st.session_state.selected_products])

    st.subheader("Cost Breakdown by Category")
    category_costs = df_products.groupby('category')['price_usd'].sum().reset_index()
    if not category_costs.empty:
        fig_pie = px.pie(category_costs, values='price_usd', names='category', title="System Cost Distribution")
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Brand Distribution")
    col1, col2 = st.columns(2)
    with col1:
        brand_counts = df_products['brand'].value_counts().reset_index()
        brand_counts.columns = ['brand', 'count']
        fig_brand_count = px.bar(brand_counts, x='brand', y='count', title="Products by Brand")
        st.plotly_chart(fig_brand_count, use_container_width=True)
    with col2:
        brand_costs = df_products.groupby('brand')['price_usd'].sum().reset_index()
        fig_brand_cost = px.bar(brand_costs, x='brand', y='price_usd', title="Cost by Brand")
        st.plotly_chart(fig_brand_cost, use_container_width=True)

    st.subheader("Project Timeline Analysis")
    max_lead_time = df_products['lead_time_days'].max()
    avg_lead_time = df_products['lead_time_days'].mean()
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Longest Lead Time", f"{max_lead_time} days")
    with col2: st.metric("Average Lead Time", f"{avg_lead_time:.1f} days")
    with col3: st.metric("Estimated Project Duration", f"{max_lead_time + 14} days") # Add installation time

    st.subheader("Power Consumption Analysis")
    df_products['power_consumption'] = df_products['specifications'].apply(lambda x: x.get('power_consumption', 100))
    total_power = df_products['power_consumption'].sum()
    
    power_by_category = df_products.groupby('category')['power_consumption'].sum().reset_index()
    fig_power = px.bar(power_by_category, x='category', y='power_consumption', title="Power Consumption by Category (Watts)")
    st.plotly_chart(fig_power, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Total Power", f"{total_power} W")
    with col2: st.metric("15A Circuit Usage", f"{(total_power / 1800) * 100:.1f}%")
    with col3: st.metric("Est. Annual Energy Cost", f"${(total_power * 8 * 365 * 0.12) / 1000:.2f}")

# ===== MAIN APPLICATION =====
def main():
    """Main application entry point"""
    try:
        create_enhanced_streamlit_interface()
    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        if st.checkbox("Show Debug Information"):
            st.exception(e)

if __name__ == "__main__":
    st.markdown("""
    <style>
        .stMetric > label { font-size: 14px !important; font-weight: 600 !important; }
        .stMetric > div { font-size: 24px !important; font-weight: 700 !important; }
        .stExpander > div > div > div > div { background-color: #f8f9fa; }
        .stButton > button { width: 100%; }
        div[data-testid="metric-container"] {
            background-color: white; border: 1px solid #e2e8f0; padding: 1rem;
            border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)
    main()
