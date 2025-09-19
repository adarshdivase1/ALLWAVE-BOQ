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

# ===== ENTERPRISE PRODUCT DATABASE =====
class EnterpriseProductCatalog:
    def __init__(self):
        self.products = self._initialize_comprehensive_catalog()
        self.pricing_api = PricingAPIClient()
        self.compliance_db = ComplianceDatabase()

    def _initialize_comprehensive_catalog(self) -> Dict[str, List[AVProduct]]:
        """Initialize comprehensive AV product catalog with real-world products"""
        return {
            "displays": [
                AVProduct(
                    id="SAMSUNG_QM75R",
                    name="Samsung QM75R 75\" 4K Commercial Display",
                    brand="Samsung",
                    category="Display",
                    subcategory="LED Display",
                    price_usd=2899.00,
                    specifications={
                        "size_inches": 75,
                        "resolution": "3840x2160",
                        "brightness_nits": 500,
                        "contrast_ratio": "4000:1",
                        "viewing_angle": "178°/178°",
                        "connectivity": ["HDMI 2.0", "DisplayPort", "USB-C", "LAN"],
                        "power_consumption": 165,
                        "mounting": "VESA 600x400",
                        "operating_hours": 16,
                        "touch_capable": False
                    },
                    compliance={"avixa": True, "energy_star": True, "rohs": True, "fcc": True},
                    warranty_years=3,
                    lead_time_days=5,
                    distributor="D&H"
                ),
                AVProduct(
                    id="LG_86UN8570",
                    name="LG 86UN8570PUC 86\" 4K NanoCell Display",
                    brand="LG",
                    category="Display",
                    subcategory="NanoCell Display",
                    price_usd=3499.00,
                    specifications={
                        "size_inches": 86,
                        "resolution": "3840x2160",
                        "brightness_nits": 400,
                        "contrast_ratio": "1200:1",
                        "viewing_angle": "178°/178°",
                        "connectivity": ["HDMI 2.1", "USB-C", "LAN", "WiFi 6"],
                        "power_consumption": 195,
                        "mounting": "VESA 600x400",
                        "operating_hours": 24,
                        "hdr_support": ["HDR10", "Dolby Vision"]
                    },
                    compliance={"avixa": True, "energy_star": True, "rohs": True},
                    warranty_years=2,
                    lead_time_days=3,
                    distributor="Ingram Micro"
                ),
                AVProduct(
                    id="SHARP_PN_C703B",
                    name="Sharp PN-C703B 70\" 4K Interactive Display",
                    brand="Sharp",
                    category="Display",
                    subcategory="Interactive Display",
                    price_usd=4299.00,
                    specifications={
                        "size_inches": 70,
                        "resolution": "3840x2160",
                        "brightness_nits": 400,
                        "touch_points": 20,
                        "connectivity": ["HDMI", "USB-C", "LAN", "WiFi"],
                        "power_consumption": 180,
                        "mounting": "VESA 400x400",
                        "pen_support": True,
                        "palm_rejection": True
                    },
                    compliance={"avixa": True, "fcc": True, "ul": True},
                    warranty_years=3,
                    lead_time_days=10,
                    distributor="CDW"
                )
            ],
            "audio": [
                AVProduct(
                    id="SHURE_MXA910",
                    name="Shure MXA910 Ceiling Array Microphone",
                    brand="Shure",
                    category="Audio",
                    subcategory="Ceiling Microphone",
                    price_usd=1899.00,
                    specifications={
                        "coverage_diameter_ft": 28,
                        "frequency_response": "100Hz - 20kHz",
                        "pickup_pattern": "Programmable",
                        "connectivity": ["Dante", "AES67", "PoE+"],
                        "power_consumption": 30,
                        "mounting": "Ceiling",
                        "noise_floor": "-40 dBFS",
                        "max_spl": "120 dB SPL"
                    },
                    compliance={"avixa": True, "rohs": True, "ce": True},
                    warranty_years=2,
                    lead_time_days=7,
                    distributor="Shure Direct"
                ),
                AVProduct(
                    id="QSC_K8_2",
                    name="QSC K8.2 Powered Speaker",
                    brand="QSC",
                    category="Audio",
                    subcategory="Powered Speaker",
                    price_usd=649.00,
                    specifications={
                        "power_watts": 2000,
                        "frequency_response": "45Hz - 20kHz",
                        "max_spl": "131 dB",
                        "coverage_pattern": "105° x 60°",
                        "connectivity": ["XLR", "TRS", "RCA"],
                        "dsp": "Built-in",
                        "weight_lbs": 39.7
                    },
                    compliance={"avixa": True, "ul": True, "ce": True},
                    warranty_years=6,
                    lead_time_days=3,
                    distributor="QSC Direct"
                ),
                AVProduct(
                    id="BOSE_ES1",
                    name="Bose EdgeMax ES1 In-Ceiling Speaker",
                    brand="Bose",
                    category="Audio",
                    subcategory="Ceiling Speaker",
                    price_usd=899.00,
                    specifications={
                        "frequency_response": "70Hz - 14kHz",
                        "coverage_angle": "160°",
                        "sensitivity": "89 dB SPL",
                        "power_handling": "100W",
                        "mounting": "Ceiling Tile",
                        "driver_config": "2-way"
                    },
                    compliance={"avixa": True, "ul": True},
                    warranty_years=5,
                    lead_time_days=5,
                    distributor="Bose Pro"
                )
            ],
            "video_conferencing": [
                AVProduct(
                    id="LOGITECH_RALLY_BAR",
                    name="Logitech Rally Bar All-in-One ConferenceCam",
                    brand="Logitech",
                    category="Video Conferencing",
                    subcategory="All-in-One System",
                    price_usd=2699.00,
                    specifications={
                        "camera_resolution": "4K Ultra HD",
                        "field_of_view": "90°",
                        "zoom": "5x digital",
                        "microphones": "Beamforming array",
                        "speakers": "Premium stereo",
                        "connectivity": ["USB-C", "HDMI", "DisplayPort"],
                        "certifications": ["Zoom", "Teams", "Meet", "WebEx"],
                        "ai_features": ["RightSight", "RightSound", "RightLight"]
                    },
                    compliance={"avixa": True, "fcc": True, "ce": True},
                    warranty_years=2,
                    lead_time_days=5,
                    distributor="Logitech"
                ),
                AVProduct(
                    id="POLY_G7500",
                    name="Poly Studio G7500 4K Video Bar",
                    brand="Poly",
                    category="Video Conferencing",
                    subcategory="Video Bar",
                    price_usd=3299.00,
                    specifications={
                        "camera_resolution": "4K",
                        "field_of_view": "120°",
                        "zoom": "5x optical",
                        "microphone_range": "20ft",
                        "speakers": "Full-range stereo",
                        "ai_features": ["NoiseBlockAI", "Acoustic Fence"],
                        "connectivity": ["USB 3.0", "HDMI", "Ethernet"]
                    },
                    compliance={"avixa": True, "fcc": True},
                    warranty_years=3,
                    lead_time_days=7,
                    distributor="Poly"
                ),
                AVProduct(
                    id="CISCO_DESK_PRO",
                    name="Cisco Webex Desk Pro",
                    brand="Cisco",
                    category="Video Conferencing",
                    subcategory="Desktop System",
                    price_usd=1899.00,
                    specifications={
                        "display_size": "27 inch",
                        "camera_resolution": "4K",
                        "microphones": "6-microphone array",
                        "speakers": "High-fidelity stereo",
                        "connectivity": ["USB-C", "HDMI", "Ethernet"],
                        "ai_features": ["Background noise removal", "People focus"]
                    },
                    compliance={"avixa": True, "fcc": True, "ce": True},
                    warranty_years=1,
                    lead_time_days=10,
                    distributor="Cisco"
                )
            ],
            "control_systems": [
                AVProduct(
                    id="CRESTRON_DM_RMC_4K",
                    name="Crestron DM-RMC-4K-100-C Room Controller",
                    brand="Crestron",
                    category="Control Systems",
                    subcategory="Room Controller",
                    price_usd=1299.00,
                    specifications={
                        "inputs": ["4K HDMI", "USB-C", "LAN"],
                        "outputs": ["DM 8G+", "HDMI", "Audio"],
                        "control_ports": ["RS-232", "IR", "I/O"],
                        "power_consumption": 25,
                        "rack_units": 1,
                        "programming": "SIMPL Windows"
                    },
                    compliance={"avixa": True, "ul": True, "ce": True},
                    warranty_years=3,
                    lead_time_days=14,
                    distributor="Crestron"
                ),
                AVProduct(
                    id="EXTRON_IN1608",
                    name="Extron IN1608 Xi Presentation Switcher",
                    brand="Extron",
                    category="Control Systems",
                    subcategory="Presentation Switcher",
                    price_usd=2899.00,
                    specifications={
                        "inputs": 16,
                        "outputs": 8,
                        "resolution": "4K/60 4:4:4",
                        "scaling": "Vector 4K",
                        "control": "IP Link Pro",
                        "rack_units": 3,
                        "power_consumption": 85
                    },
                    compliance={"avixa": True, "ul": True},
                    warranty_years=3,
                    lead_time_days=10,
                    distributor="Extron"
                ),
                AVProduct(
                    id="AMX_NX_1200",
                    name="AMX NX-1200 NetLinx Controller",
                    brand="AMX",
                    category="Control Systems",
                    subcategory="Central Controller",
                    price_usd=1599.00,
                    specifications={
                        "processors": "Dual-core ARM",
                        "memory": "1GB RAM, 8GB Flash",
                        "ports": ["4 Serial", "8 Relay", "8 I/O"],
                        "ethernet": "Dual Gigabit",
                        "rack_units": 1,
                        "programming": "NetLinx Studio"
                    },
                    compliance={"avixa": True, "ul": True, "rohs": True},
                    warranty_years=2,
                    lead_time_days=12,
                    distributor="AMX"
                )
            ],
            "mounts_hardware": [
                AVProduct(
                    id="PEERLESS_DS_VW765",
                    name="Peerless DS-VW765-LAND Wall Mount",
                    brand="Peerless",
                    category="Mounts & Hardware",
                    subcategory="Wall Mount",
                    price_usd=299.00,
                    specifications={
                        "screen_size_range": "46-75 inches",
                        "weight_capacity": "132 lbs",
                        "vesa_compatibility": ["400x400", "600x400"],
                        "adjustment": "Tilt -12° to +3°",
                        "wall_clearance": "2.36 inches"
                    },
                    compliance={"ul": True, "safety": True},
                    warranty_years=10,
                    lead_time_days=2,
                    distributor="Peerless"
                ),
                AVProduct(
                    id="MIDDLE_ATLANTIC_ERK",
                    name="Middle Atlantic ERK-4425 Equipment Rack",
                    brand="Middle Atlantic",
                    category="Mounts & Hardware",
                    subcategory="Equipment Rack",
                    price_usd=1299.00,
                    specifications={
                        "rack_units": 44,
                        "depth": "25 inches",
                        "width": "24 inches",
                        "height": "77 inches",
                        "weight_capacity": "3000 lbs",
                        "ventilation": "Convection cooling"
                    },
                    compliance={"eia": True, "ul": True},
                    warranty_years=10,
                    lead_time_days=7,
                    distributor="Middle Atlantic"
                )
            ],
            "cables_connectivity": [
                AVProduct(
                    id="KRAMER_C_HM_50",
                    name="Kramer C-HM/HM-50 HDMI Cable",
                    brand="Kramer",
                    category="Cables & Connectivity",
                    subcategory="HDMI Cable",
                    price_usd=89.00,
                    specifications={
                        "length_ft": 50,
                        "version": "HDMI 2.1",
                        "bandwidth": "48Gbps",
                        "resolution_support": "8K@60Hz, 4K@120Hz",
                        "connector_type": "HDMI Type A"
                    },
                    compliance={"hdmi_certified": True, "rohs": True},
                    warranty_years=7,
                    lead_time_days=1,
                    distributor="Kramer"
                ),
                AVProduct(
                    id="BELDEN_1694A",
                    name="Belden 1694A HD-SDI Cable (per foot)",
                    brand="Belden",
                    category="Cables & Connectivity",
                    subcategory="Video Cable",
                    price_usd=3.50,
                    specifications={
                        "impedance": "75 ohm",
                        "bandwidth": "4.5 GHz",
                        "return_loss": "> 15dB to 3GHz",
                        "jacket": "PVC",
                        "bend_radius": "10x diameter"
                    },
                    compliance={"ul": True, "rohs": True, "reach": True},
                    warranty_years=25,
                    lead_time_days=1,
                    distributor="Belden"
                )
            ]
        }

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

        display_budget = budget * 0.35  # 35% for displays
        audio_budget = budget * 0.25   # 25% for audio
        control_budget = budget * 0.20  # 20% for control
        misc_budget = budget * 0.20     # 20% for misc/installation

        # Select display based on tier
        displays = self.catalog.products["displays"]
        suitable_displays = [d for d in displays if d.specifications["size_inches"] >= optimal_display_size - 10]

        if suitable_displays:
            if tier == "economy":
                selected_display = min(suitable_displays, key=lambda x: x.price_usd)
            elif tier == "premium":
                selected_display = max(suitable_displays, key=lambda x: x.specifications["brightness_nits"])
            else:  # standard
                # Balance price and performance
                selected_display = sorted(suitable_displays,
                                          key=lambda x: x.price_usd + (1000 - x.specifications["brightness_nits"]))[0]
            
            config["products"].append(selected_display)
            config["total_cost"] += selected_display.price_usd

        # Audio system selection
        audio_products = self.catalog.products["audio"]
        if room_specs.primary_use in ["Video Conferencing", "Hybrid Meeting"]:
            # Add microphone system
            microphones = [p for p in audio_products if "microphone" in p.name.lower()]
            selected_mic = microphones[0] if microphones else None
            if selected_mic:
                config["products"].append(selected_mic)
                config["total_cost"] += selected_mic.price_usd

        # Add speakers based on room size
        speakers = [p for p in audio_products if "speaker" in p.name.lower()]
        room_area = room_specs.length_ft * room_specs.width_ft
        speaker_count = max(2, int(room_area / 200))  # 1 speaker per 200 sq ft minimum

        if speakers:
            if tier == "economy":
                selected_speaker = min(speakers, key=lambda x: x.price_usd)
            else:
                selected_speaker = max(speakers, key=lambda x: x.specifications.get("max_spl", "0 dB").split(" ")[0])

            for _ in range(speaker_count):
                config["products"].append(selected_speaker)
                config["total_cost"] += selected_speaker.price_usd

        # Control system for premium tier
        if tier == "premium" or len(config["products"]) > 3:
            control_systems = self.catalog.products["control_systems"]
            if control_systems:
                config["products"].append(control_systems[0])
                config["total_cost"] += control_systems[0].price_usd

        # Add mounting hardware
        mounts = self.catalog.products["mounts_hardware"]
        wall_mount = [m for m in mounts if "wall" in m.name.lower()]
        if wall_mount:
            config["products"].append(wall_mount[0])
            config["total_cost"] += wall_mount[0].price_usd

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
                # Higher brightness and resolution increase score
                brightness = product.specifications.get("brightness_nits", 300)
                product_score += min((brightness - 300) / 10, 50)  # Max 50 bonus points
                weight = 3  # Displays are most important

            elif product.category == "Audio":
                # Higher SPL and frequency response increase score
                max_spl = product.specifications.get("max_spl", "100 dB SPL")
                spl_value = int(re.search(r'\d+', str(max_spl)).group()) if re.search(r'\d+', str(max_spl)) else 100
                product_score += min((spl_value - 100) / 2, 50)
                weight = 2

            elif product.category == "Control Systems":
                # Control systems add significant value
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
        # Placeholder for performance optimization logic
        return {}

    def _analyze_future_proofing(self, room_specs, requirements):
        # Placeholder for future-proofing analysis
        return {}

    def _assess_project_risks(self, room_specs, requirements):
        # Placeholder for risk assessment
        return {}

    def _generate_alternatives(self, room_specs, requirements):
        # Placeholder for generating alternative recommendations
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

        # Create HTML template for PDF generation
        html_content = self._create_boq_html_template(
            project_info, room_specs, products,
            compliance_results, optimization_results
        )

        # Convert to PDF (using weasyprint or similar)
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

        # Add product rows
        total_cost = 0
        product_counts = {}

        for product in products:
            # Count identical products
            if product.id in product_counts:
                product_counts[product.id]['quantity'] += 1
            else:
                product_counts[product.id] = {
                    'product': product,
                    'quantity': 1
                }

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

            <div class="section">
                <h3>AVIXA Compliance Analysis</h3>
        """

        # Add compliance results
        for result in compliance_results:
            status_class = "compliance-pass" if result.status == "PASS" else "compliance-fail"
            html_template += f"""
                <h4>{result.standard}</h4>
                <p class="{status_class}">Status: {result.status} (Score: {result.score:.1f}/100)</p>
            """

            if result.issues:
                html_template += "<strong>Issues:</strong><ul>"
                for issue in result.issues:
                    html_template += f"<li>{issue}</li>"
                html_template += "</ul>"

            if result.recommendations:
                html_template += "<div class='recommendations'><strong>Recommendations:</strong><ul>"
                for rec in result.recommendations:
                    html_template += f"<li>{rec}</li>"
                html_template += "</ul></div>"

        html_template += """
            </div>

            <div class="section">
                <h3>System Optimization Analysis</h3>
                <p>Cost optimization and performance analysis results:</p>
        """

        # Add optimization results
        if 'cost_optimization' in optimization_results:
            cost_opt = optimization_results['cost_optimization']
            html_template += """
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

            html_template += """
                    </tbody>
                </table>
            """

        html_template += """
            </div>

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
        # In production, use weasyprint, reportlab, or similar library
        # For now, return HTML as bytes
        return html_content.encode('utf-8')

# ===== ENHANCED STREAMLIT INTERFACE =====
def create_enhanced_streamlit_interface():
    """Enhanced Streamlit interface with professional features"""

    # Initialize session state
    if 'project_info' not in st.session_state:
        st.session_state.project_info = None
    if 'room_specs' not in st.session_state:
        st.session_state.room_specs = None
    if 'selected_products' not in st.session_state:
        st.session_state.selected_products = []
    if 'optimization_results' not in st.session_state:
        st.session_state.optimization_results = {}


    # Header with professional styling
    st.markdown("""
        <div style='background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
                    padding: 2rem; margin: -1rem -1rem 2rem; border-radius: 10px;'>
            <h1 style='color: white; margin: 0;'>🏢 Enterprise AV BOQ Generator</h1>
            <p style='color: #e2e8f0; margin: 0.5rem 0 0;'>Professional Audio-Visual System Design & Specification Tool</p>
        </div>
    """, unsafe_allow_html=True)

    # Sidebar for project setup
    with st.sidebar:
        st.header("Project Configuration")

        # Project Information
        with st.expander("Project Details", expanded=True):
            project_name = st.text_input("Project Name", "Conference Room Alpha")
            client_name = st.text_input("Client", "Enterprise Corp")
            location = st.text_input("Location", "New York, NY")
            designer_name = st.text_input("AV Designer", "John Smith, CTS")

            budget_min = st.number_input("Minimum Budget ($)", 10000, 1000000, 25000)
            budget_max = st.number_input("Maximum Budget ($)", budget_min, 1000000, 50000)

            timeline_weeks = st.slider("Project Timeline (weeks)", 2, 20, 8)
            security_level = st.selectbox("Security Level",
                                          ["Standard", "Enhanced", "High Security", "Top Secret"])

        # Room Specifications
        with st.expander("Room Specifications", expanded=True):
            room_type = st.selectbox("Room Type", [
                "Conference Room", "Training Room", "Board Room", "Auditorium",
                "Classroom", "Huddle Space", "Multi-Purpose Room", "Control Room"
            ])

            col1, col2, col3 = st.columns(3)
            with col1:
                length_ft = st.number_input("Length (ft)", 8.0, 100.0, 20.0, 0.5)
            with col2:
                width_ft = st.number_input("Width (ft)", 8.0, 100.0, 16.0, 0.5)
            with col3:
                height_ft = st.number_input("Height (ft)", 8.0, 20.0, 10.0, 0.5)

            occupancy = st.number_input("Max Occupancy", 2, 500, 12)
            primary_use = st.selectbox("Primary Use", [
                "Presentations", "Video Conferencing", "Hybrid Meeting",
                "Training", "Collaboration", "Entertainment"
            ])

            viewing_distance = st.number_input("Max Viewing Distance (ft)", 5.0, 50.0, 15.0, 0.5)

            ambient_light = st.selectbox("Ambient Light Level",
                                         ["Low", "Medium", "High", "Variable"])
            acoustics = st.selectbox("Acoustic Environment",
                                     ["Good", "Average", "Poor", "Requires Treatment"])
            power_available = st.selectbox("Power Infrastructure",
                                           ["Standard 15A", "20A Available", "30A Available", "Custom"])
            network_infra = st.selectbox("Network Infrastructure",
                                         ["Basic Ethernet", "Managed Switch", "Enterprise Network", "Fiber Backbone"])

    # Create project objects
    if st.sidebar.button("Initialize Project", type="primary"):
        st.session_state.project_info = ProjectInfo(
            id=f"PRJ_{int(time.time())}",
            name=project_name,
            client=client_name,
            location=location,
            designer=designer_name,
            created_date=datetime.now(),
            budget_range=(budget_min, budget_max),
            timeline_weeks=timeline_weeks,
            security_level=security_level
        )

        st.session_state.room_specs = RoomSpecification(
            type=room_type,
            length_ft=length_ft,
            width_ft=width_ft,
            height_ft=height_ft,
            occupancy=occupancy,
            primary_use=primary_use,
            viewing_distance_max=viewing_distance,
            ambient_light=ambient_light,
            acoustics=acoustics,
            power_available=power_available,
            network_infrastructure=network_infra
        )

        st.success("✅ Project initialized successfully!")
        st.rerun()

    # Main interface tabs
    if st.session_state.project_info and st.session_state.room_specs:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 System Design", "📊 AVIXA Compliance", "🤖 AI Optimization",
            "📄 Professional BOQ", "📈 Analytics"
        ])

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

    # Product category selection
    categories = list(catalog.products.keys())
    selected_category = st.selectbox("Select Product Category",
                                     [cat.replace('_', ' ').title() for cat in categories])

    category_key = selected_category.lower().replace(' ', '_')
    if category_key in catalog.products:
        products_in_category = catalog.products[category_key]

        # Display products in a nice format
        for product in products_in_category:
            with st.expander(f"{product.brand} {product.name} - ${product.price_usd:,.2f}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Category:** {product.category}")
                    st.write(f"**Subcategory:** {product.subcategory}")
                    st.write(f"**Warranty:** {product.warranty_years} years")
                    st.write(f"**Lead Time:** {product.lead_time_days} days")
                    st.write(f"**Distributor:** {product.distributor}")

                with col2:
                    st.write("**Key Specifications:**")
                    for spec_key, spec_value in list(product.specifications.items())[:5]:
                        st.write(f"• {spec_key.replace('_', ' ').title()}: {spec_value}")

                # Add to cart button
                if st.button(f"Add {product.name}", key=f"add_{product.id}"):
                    st.session_state.selected_products.append(product)
                    st.success(f"✅ Added {product.name} to BOQ")
                    st.rerun()


    # Display selected products
    if st.session_state.selected_products:
        st.subheader("Selected Products")
        total_cost = 0

        for i, product in enumerate(st.session_state.selected_products):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.write(f"**{product.name}**")
                st.write(f"{product.brand} - {product.category}")

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
    results = compliance_engine.validate_system_design(
        st.session_state.room_specs,
        st.session_state.selected_products
    )

    # Overall compliance score
    overall_score = sum(r.score for r in results) / len(results) if results else 0

    # Display overall status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Overall Compliance Score", f"{overall_score:.1f}/100")
    with col2:
        passing_standards = len([r for r in results if r.status == "PASS"])
        st.metric("Passing Standards", f"{passing_standards}/{len(results)}")
    with col3:
        critical_issues = sum(len(r.critical_failures) for r in results)
        st.metric("Critical Issues", critical_issues)

    # Detailed results
    for result in results:
        status_color = "green" if result.status == "PASS" else "red" if result.status == "CRITICAL" else "orange"

        st.markdown(f"""
        <div style='border-left: 4px solid {status_color}; padding: 1rem; margin: 1rem 0; background: #f8f9fa;'>
            <h4>{result.standard}</h4>
            <p><strong>Status:</strong> <span style='color: {status_color};'>{result.status}</span>
               <strong>Score:</strong> {result.score:.1f}/100</p>
        </div>
        """, unsafe_allow_html=True)

        if result.critical_failures:
            st.error("**Critical Failures:**")
            for failure in result.critical_failures:
                st.error(f"• {failure}")

        if result.issues:
            st.warning("**Issues:**")
            for issue in result.issues:
                st.warning(f"• {issue}")

        if result.recommendations:
            st.info("**Recommendations:**")
            for rec in result.recommendations:
                st.info(f"• {rec}")

def create_optimization_interface():
    """AI optimization interface"""
    if not st.session_state.selected_products:
        st.warning("Please select products in the System Design tab first.")
        return

    catalog = EnterpriseProductCatalog()
    ai_engine = AIOptimizationEngine(catalog)

    st.subheader("Optimization Parameters")

    col1, col2 = st.columns(2)
    with col1:
        optimization_type = st.selectbox("Optimization Focus", [
            "Cost Optimization", "Performance Maximization", "Balanced Approach"
        ])

    with col2:
        budget_constraint = st.number_input("Budget Constraint ($)",
                                            value=st.session_state.project_info.budget_range[1])

    if st.button("Run AI Optimization", type="primary"):
        with st.spinner("Running AI optimization analysis..."):
            requirements = {"optimization_type": optimization_type}

            optimization_results = ai_engine.optimize_system_design(
                st.session_state.room_specs,
                requirements,
                budget_constraint
            )

            st.session_state.optimization_results = optimization_results
            st.success("✅ Optimization analysis complete!")

    # Display optimization results
    if st.session_state.get('optimization_results'):
        results = st.session_state.optimization_results

        if 'cost_optimization' in results:
            st.subheader("Alternative Configurations")

            config_data = []
            for config in results['cost_optimization']['configurations']:
                config_data.append({
                    'Configuration': config['tier'].title(),
                    'Total Cost': f"${config['total_cost']:,.2f}",
                    'Performance Score': f"{config['performance_score']:.1f}/100",
                    'Compliance Score': f"{config['compliance_score']:.1f}/100",
                })
            df_configs = pd.DataFrame(config_data)
            st.dataframe(df_configs, use_container_width=True)

            # Cost savings opportunities
            st.subheader("Cost Savings Opportunities")
            for saving in results['cost_optimization']['cost_savings_opportunities']:
                st.info(f"💡 {saving}")

            # Value engineering suggestions
            st.subheader("Value Engineering Suggestions")
            for suggestion in results['cost_optimization']['value_engineering_suggestions']:
                st.info(f"🔧 {suggestion}")

def create_boq_generation_interface():
    """Professional BOQ generation interface"""
    if not st.session_state.selected_products:
        st.warning("Please select products in the System Design tab first.")
        return

    st.subheader("Professional BOQ Generation")

    # BOQ generation options
    col1, col2 = st.columns(2)
    with col1:
        include_compliance = st.checkbox("Include AVIXA Compliance Analysis", True)
        include_optimization = st.checkbox("Include AI Optimization Results", True)

    with col2:
        document_format = st.selectbox("Document Format", ["PDF", "Excel", "HTML"])
        include_specifications = st.checkbox("Include Detailed Specifications", True)

    if st.button("Generate Professional BOQ", type="primary"):
        with st.spinner("Generating professional BOQ document..."):
            # Run compliance analysis if needed
            compliance_results = []
            if include_compliance:
                compliance_engine = AVIXAComplianceEngine()
                compliance_results = compliance_engine.validate_system_design(
                    st.session_state.room_specs,
                    st.session_state.selected_products
                )

            # Run optimization if needed
            optimization_results = {}
            if include_optimization and hasattr(st.session_state, 'optimization_results'):
                optimization_results = st.session_state.optimization_results

            # Generate document
            doc_generator = ProfessionalDocumentGenerator()
            document_content = doc_generator.generate_comprehensive_boq(
                st.session_state.project_info,
                st.session_state.room_specs,
                st.session_state.selected_products,
                compliance_results,
                optimization_results
            )

            # Create download button
            st.success("✅ BOQ document generated successfully!")

            # Display summary
            total_cost = sum(p.price_usd for p in st.session_state.selected_products)
            st.metric("Total System Cost", f"${total_cost:,.2f}")

            # Download button
            st.download_button(
                label=f"📄 Download {document_format} BOQ",
                data=document_content,
                file_name=f"BOQ_{st.session_state.project_info.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html"
            )

    # Live BOQ preview
    st.subheader("BOQ Preview")
    if st.session_state.selected_products:
        # Create summary table
        boq_data = []
        total_cost = 0

        product_counts = {}
        for product in st.session_state.selected_products:
            if product.id in product_counts:
                product_counts[product.id]['quantity'] += 1
            else:
                product_counts[product.id] = {
                    'product': product,
                    'quantity': 1
                }

        for item_id, item_data in product_counts.items():
            product = item_data['product']
            quantity = item_data['quantity']
            line_total = product.price_usd * quantity
            total_cost += line_total

            boq_data.append({
                'Item': product.name,
                'Brand': product.brand,
                'Category': product.category,
                'Qty': quantity,
                'Unit Price': f"${product.price_usd:,.2f}",
                'Total': f"${line_total:,.2f}",
                'Lead Time': f"{product.lead_time_days} days"
            })

        df_boq = pd.DataFrame(boq_data)
        st.dataframe(df_boq, use_container_width=True)

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", len(product_counts))
        with col2:
            st.metric("Total Cost", f"${total_cost:,.2f}")
        with col3:
            avg_lead_time = np.mean([p.lead_time_days for p in st.session_state.selected_products])
            st.metric("Avg Lead Time", f"{avg_lead_time:.1f} days")
        with col4:
            budget_utilization = (total_cost / st.session_state.project_info.budget_range[1]) * 100
            st.metric("Budget Utilization", f"{budget_utilization:.1f}%")

def create_analytics_interface():
    """Project analytics and insights interface"""
    if not st.session_state.selected_products:
        st.warning("Please select products in the System Design tab first.")
        return

    st.subheader("Project Analytics Dashboard")

    # Cost breakdown by category
    st.subheader("Cost Breakdown by Category")

    category_costs = {}
    for product in st.session_state.selected_products:
        if product.category not in category_costs:
            category_costs[product.category] = 0
        category_costs[product.category] += product.price_usd

    # Create pie chart
    if category_costs:
        fig_pie = px.pie(
            values=list(category_costs.values()),
            names=list(category_costs.keys()),
            title="System Cost Distribution"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    # Brand analysis
    st.subheader("Brand Distribution")

    brand_counts = {}
    brand_costs = {}

    for product in st.session_state.selected_products:
        if product.brand not in brand_counts:
            brand_counts[product.brand] = 0
            brand_costs[product.brand] = 0
        brand_counts[product.brand] += 1
        brand_costs[product.brand] += product.price_usd

    col1, col2 = st.columns(2)

    with col1:
        if brand_counts:
            fig_brand_count = px.bar(
                x=list(brand_counts.keys()),
                y=list(brand_counts.values()),
                title="Products by Brand",
                labels={'x': 'Brand', 'y': 'Number of Products'}
            )
            st.plotly_chart(fig_brand_count, use_container_width=True)

    with col2:
        if brand_costs:
            fig_brand_cost = px.bar(
                x=list(brand_costs.keys()),
                y=list(brand_costs.values()),
                title="Cost by Brand",
                labels={'x': 'Brand', 'y': 'Total Cost ($)'}
            )
            st.plotly_chart(fig_brand_cost, use_container_width=True)

    # Timeline analysis
    st.subheader("Project Timeline Analysis")

    lead_times = [p.lead_time_days for p in st.session_state.selected_products]
    max_lead_time = max(lead_times) if lead_times else 0
    avg_lead_time = np.mean(lead_times) if lead_times else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Longest Lead Time", f"{max_lead_time} days")
    with col2:
        st.metric("Average Lead Time", f"{avg_lead_time:.1f} days")
    with col3:
        total_project_time = max_lead_time + 14  # Add installation time
        st.metric("Estimated Project Duration", f"{total_project_time} days")

    # Room utilization metrics
    st.subheader("Room Utilization Analysis")

    room_area = st.session_state.room_specs.length_ft * st.session_state.room_specs.width_ft
    room_volume = room_area * st.session_state.room_specs.height_ft

    displays = [p for p in st.session_state.selected_products if p.category == "Display"]
    total_display_area = sum(
        (p.specifications.get("size_inches", 50) * 0.49) * (p.specifications.get("size_inches", 50) * 0.87) / 144
        for p in displays
    )  # Convert to square feet

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Room Area", f"{room_area:.1f} sq ft")
    with col2:
        st.metric("Display Area", f"{total_display_area:.1f} sq ft")
    with col3:
        display_ratio = (total_display_area / room_area) * 100 if room_area > 0 else 0
        st.metric("Display/Room Ratio", f"{display_ratio:.2f}%")

    # Power consumption analysis
    st.subheader("Power Consumption Analysis")

    total_power = sum(p.specifications.get("power_consumption", 100) for p in st.session_state.selected_products)

    # Create power consumption chart
    power_by_category = {}
    for product in st.session_state.selected_products:
        category = product.category
        power = product.specifications.get("power_consumption", 100)
        if category not in power_by_category:
            power_by_category[category] = 0
        power_by_category[category] += power

    if power_by_category:
        fig_power = px.bar(
            x=list(power_by_category.keys()),
            y=list(power_by_category.values()),
            title="Power Consumption by Category (Watts)",
            labels={'x': 'Category', 'y': 'Power Consumption (W)'}
        )
        st.plotly_chart(fig_power, use_container_width=True)

    # Power metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Power", f"{total_power} W")
    with col2:
        circuit_utilization = (total_power / 1800) * 100  # 15A circuit = 1800W
        st.metric("15A Circuit Usage", f"{circuit_utilization:.1f}%")
    with col3:
        annual_energy_cost = (total_power * 8 * 365 * 0.12) / 1000  # Assuming $0.12/kWh, 8hrs/day
        st.metric("Est. Annual Energy Cost", f"${annual_energy_cost:.2f}")

    # Compliance summary
    if hasattr(st.session_state, 'optimization_results'):
        st.subheader("System Performance Summary")

        # Mock performance indicators for demonstration
        performance_metrics = {
            "Display Quality Score": 85,
            "Audio Performance": 92,
            "Control System Rating": 78,
            "Future-Proofing Score": 88,
            "Installation Complexity": 65
        }

        # Create radar chart
        categories = list(performance_metrics.keys())
        values = list(performance_metrics.values())

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='System Performance'
        ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title="System Performance Radar"
        )

        st.plotly_chart(fig_radar, use_container_width=True)

# ===== MAIN APPLICATION =====
def main():
    """Main application entry point"""
    try:
        create_enhanced_streamlit_interface()

    except Exception as e:
        st.error(f"Application Error: {str(e)}")
        st.write("Please refresh the page and try again.")

        # Debug information (only in development)
        if st.checkbox("Show Debug Information"):
            st.exception(e)

if __name__ == "__main__":
    # Configure Streamlit settings
    st.set_option('deprecation.showPyplotGlobalUse', False)

    # Custom CSS for better styling
    st.markdown("""
    <style>
        .stMetric > label {
            font-size: 14px !important;
            font-weight: 600 !important;
        }
        .stMetric > div {
            font-size: 24px !important;
            font-weight: 700 !important;
        }
        .stExpander > div > div > div > div {
            background-color: #f8f9fa;
        }
        .stSelectbox > label {
            font-weight: 600 !important;
        }
        .stButton > button {
            width: 100%;
        }
        div[data-testid="metric-container"] {
            background-color: white;
            border: 1px solid #e2e8f0;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
    """, unsafe_allow_html=True)

    main()
