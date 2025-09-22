import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import hashlib
import json
import time
from io import BytesIO
import base64
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Page Configuration ---
st.set_page_config(
    page_title="Enterprise AV BOQ Generator Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Enhanced AVIXA Compliance Framework ---
class AVIXAComplianceEngine:
    """Comprehensive AVIXA standards compliance engine"""
    
    def __init__(self):
        self.compliance_rules = {
            'displays': {
                'viewing_distance_multiplier': 2.0,  # Screen height × 2 minimum
                'max_viewing_angle': 30,  # degrees from center
                'brightness_requirements': {
                    'huddle_room': 300,  # cd/m²
                    'conference_room': 400,
                    'training_room': 500,
                    'auditorium': 600
                },
                'contrast_ratio_min': 1000,
                'resolution_standards': {
                    'small_room': '1920x1080',
                    'medium_room': '3840x2160',
                    'large_room': '3840x2160'
                }
            },
            'audio': {
                'spl_requirements': {
                    'conference': 70,  # dB SPL
                    'presentation': 75,
                    'auditorium': 80
                },
                'coverage_overlap': 0.1,  # 10% overlap between speakers
                'microphone_pickup_radius': 3,  # feet
                'echo_cancellation': True,
                'noise_reduction': True,
                'frequency_response': '20Hz-20kHz ±3dB'
            },
            'infrastructure': {
                'power_safety_factor': 1.25,  # 25% safety margin
                'cooling_requirements': 3414,  # BTU per kW
                'cable_category_min': 'Cat6A',
                'fiber_requirements': {
                    'distance_threshold': 328,  # feet
                    'bandwidth_min': '10Gb'
                },
                'ups_backup_minutes': 15
            },
            'accessibility': {
                'ada_compliance': True,
                'hearing_loop_required': False,
                'control_height_max': 48,  # inches AFF
                'visual_indicators': True,
                'tactile_feedback': True
            },
            'environmental': {
                'operating_temperature': (32, 104),  # Fahrenheit
                'operating_humidity': (10, 80),  # Percent RH
                'noise_rating_max': 35,  # dB-A
                'heat_dissipation_factor': 0.85
            }
        }
    
    def validate_system_design(self, boq_items, room_specs):
        """Comprehensive AVIXA compliance validation"""
        compliance_report = {
            'compliant': True,
            'warnings': [],
            'errors': [],
            'recommendations': [],
            'compliance_score': 0
        }
        
        # Validate each subsystem
        displays = [item for item in boq_items if 'display' in item.get('category', '').lower()]
        if displays:
            display_validation = self._validate_displays(displays, room_specs)
            compliance_report['warnings'].extend(display_validation.get('warnings', []))
            compliance_report['errors'].extend(display_validation.get('errors', []))
            compliance_report['recommendations'].extend(display_validation.get('recommendations', []))
        
        audio_items = [item for item in boq_items if 'audio' in item.get('category', '').lower()]
        if audio_items:
            audio_validation = self._validate_audio_system(audio_items, room_specs)
            compliance_report['warnings'].extend(audio_validation.get('warnings', []))
            compliance_report['errors'].extend(audio_validation.get('errors', []))
            compliance_report['recommendations'].extend(audio_validation.get('recommendations', []))
        
        infrastructure_validation = self._validate_infrastructure(boq_items, room_specs)
        compliance_report['warnings'].extend(infrastructure_validation.get('warnings', []))
        compliance_report['errors'].extend(infrastructure_validation.get('errors', []))
        compliance_report['recommendations'].extend(infrastructure_validation.get('recommendations', []))
        
        accessibility_validation = self._validate_accessibility(boq_items, room_specs)
        compliance_report['warnings'].extend(accessibility_validation.get('warnings', []))
        compliance_report['errors'].extend(accessibility_validation.get('errors', []))
        compliance_report['recommendations'].extend(accessibility_validation.get('recommendations', []))
        
        # Calculate overall compliance score
        compliance_report['compliance_score'] = self._calculate_compliance_score(compliance_report)
        
        if compliance_report['errors']:
            compliance_report['compliant'] = False
        
        return compliance_report
    
    def _validate_displays(self, displays, room_specs):
        """Validate display sizing and positioning per AVIXA standards"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        
        room_length = room_specs.get('length', 16)
        room_width = room_specs.get('width', 12)
        room_type = room_specs.get('type', 'conference_room')
        
        for display in displays:
            size_match = re.search(r'(\d+)"', display.get('name', ''))
            if size_match:
                diagonal_size = int(size_match.group(1))
                screen_height = diagonal_size * 0.49  # For 16:9 aspect ratio
                
                # AVIXA 2H rule validation
                min_distance = screen_height * 2
                max_distance = screen_height * 8
                
                if room_length < min_distance:
                    report['errors'].append(
                        f"AVIXA Violation: Room too small for {diagonal_size}\" display. "
                        f"Minimum viewing distance (2H rule): {min_distance:.1f} ft, Room length: {room_length} ft"
                    )
                elif room_length > max_distance:
                    report['warnings'].append(
                        f"Display may be undersized. {diagonal_size}\" display at {room_length} ft "
                        f"exceeds 8H maximum viewing distance ({max_distance:.1f} ft)"
                    )
                
                # Brightness requirements
                required_brightness = self.compliance_rules['displays']['brightness_requirements'].get(
                    room_type.lower(), 400
                )
                
                # Check if brightness info is available in product specs
                brightness_match = re.search(r'(\d+)\s*(?:cd/m²|nits)', display.get('specifications', ''), re.I)
                if brightness_match:
                    actual_brightness = int(brightness_match.group(1))
                    if actual_brightness < required_brightness:
                        report['warnings'].append(
                            f"Display brightness {actual_brightness} cd/m² below recommended "
                            f"{required_brightness} cd/m² for {room_type}"
                        )
                else:
                    report['recommendations'].append(
                        f"Verify display brightness meets {required_brightness} cd/m² requirement for {room_type}"
                    )
        
        return report
    
    def _validate_audio_system(self, audio_items, room_specs):
        """Validate audio system per AVIXA standards"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        
        room_area = room_specs.get('area', 200)
        room_type = room_specs.get('type', 'conference_room')
        ceiling_height = room_specs.get('ceiling_height', 9)
        
        # Calculate room volume for acoustic considerations
        room_volume = room_area * ceiling_height
        
        # Check SPL requirements
        required_spl = self.compliance_rules['audio']['spl_requirements'].get(
            room_type.lower().replace('_room', ''), 75
        )
        
        # Validate microphone coverage
        microphones = [item for item in audio_items if 'mic' in item.get('name', '').lower()]
        speakers = [item for item in audio_items if any(word in item.get('name', '').lower() 
                                                      for word in ['speaker', 'loudspeaker', 'ceiling'])]
        
        if microphones:
            total_coverage = sum(item.get('quantity', 1) for item in microphones) * 28  # π × 3² coverage per mic
            if total_coverage < room_area:
                report['warnings'].append(
                    f"Insufficient microphone coverage. Current: {total_coverage:.0f} sq ft, "
                    f"Required: {room_area:.0f} sq ft"
                )
        
        if speakers:
            # Basic speaker coverage validation
            speaker_count = sum(item.get('quantity', 1) for item in speakers)
            recommended_speakers = max(2, int(room_area / 150))  # Rough guideline
            
            if speaker_count < recommended_speakers:
                report['recommendations'].append(
                    f"Consider additional speakers. Current: {speaker_count}, "
                    f"Recommended for {room_area:.0f} sq ft: {recommended_speakers}"
                )
        
        # Check for essential audio components
        has_dsp = any('dsp' in item.get('name', '').lower() or 'processor' in item.get('name', '').lower() 
                     for item in audio_items)
        if not has_dsp:
            report['errors'].append(
                "Missing DSP/Audio Processor - Required for professional AV systems per AVIXA standards"
            )
        
        return report
    
    def _validate_infrastructure(self, boq_items, room_specs):
        """Validate infrastructure requirements"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        
        # Calculate total power consumption
        total_power = 0
        for item in boq_items:
            # Estimate power based on category and quantity
            power_estimates = {
                'display': 200,  # Watts per display
                'audio': 100,   # Watts per audio component
                'control': 50,  # Watts per control component
                'video': 150    # Watts per video component
            }
            
            category = item.get('category', '').lower()
            quantity = item.get('quantity', 1)
            
            for cat_key, power in power_estimates.items():
                if cat_key in category:
                    total_power += power * quantity
                    break
        
        # Apply safety factor
        total_power_with_safety = total_power * self.compliance_rules['infrastructure']['power_safety_factor']
        
        # Check circuit capacity
        standard_circuit_capacity = 1800  # 15A at 120V
        dedicated_circuit_capacity = 2400  # 20A at 120V
        
        if total_power_with_safety > standard_circuit_capacity:
            if total_power_with_safety <= dedicated_circuit_capacity:
                report['warnings'].append(
                    f"System requires dedicated 20A circuit. Total power: {total_power_with_safety:.0f}W "
                    f"(with 25% safety factor)"
                )
            else:
                report['errors'].append(
                    f"Power requirements exceed single circuit capacity. "
                    f"Total: {total_power_with_safety:.0f}W requires multiple circuits or 30A service"
                )
        
        # Cooling requirements
        cooling_btus = (total_power / 1000) * self.compliance_rules['infrastructure']['cooling_requirements']
        if cooling_btus > 5000:  # Threshold for HVAC consideration
            report['recommendations'].append(
                f"HVAC consideration required. System heat load: {cooling_btus:.0f} BTU/hr"
            )
        
        # Network infrastructure
        network_devices = len([item for item in boq_items if any(term in item.get('name', '').lower() 
                                                               for term in ['switch', 'codec', 'control', 'display'])])
        if network_devices > 4:
            report['recommendations'].append(
                f"Consider managed network switch for {network_devices} networked devices"
            )
        
        return report
    
    def _validate_accessibility(self, boq_items, room_specs):
        """Validate ADA and accessibility compliance"""
        report = {'warnings': [], 'errors': [], 'recommendations': []}
        
        ada_required = room_specs.get('ada_compliance', False)
        
        if ada_required:
            # Check control interface accessibility
            control_items = [item for item in boq_items if 'control' in item.get('category', '').lower()]
            touch_panels = [item for item in control_items if 'touch' in item.get('name', '').lower()]
            
            if touch_panels and not any('accessible' in item.get('name', '').lower() for item in touch_panels):
                report['warnings'].append(
                    "ADA compliance: Consider accessible control interface options"
                )
            
            # Audio accessibility
            assistive_listening = any('loop' in item.get('name', '').lower() or 
                                    'assistive' in item.get('name', '').lower() 
                                    for item in boq_items)
            
            if not assistive_listening:
                report['recommendations'].append(
                    "ADA compliance: Consider assistive listening system for hearing accessibility"
                )
        
        return report
    
    def _calculate_compliance_score(self, compliance_report):
        """Calculate overall compliance score (0-100)"""
        error_count = len(compliance_report.get('errors', []))
        warning_count = len(compliance_report.get('warnings', []))
        
        # Start with 100 and deduct points
        score = 100
        score -= error_count * 20  # Major deductions for errors
        score -= warning_count * 5  # Minor deductions for warnings
        
        return max(0, score)

# --- Professional Product Matching System ---
class ProfessionalProductMatcher:
    """Advanced product matching with industry standards validation"""
    
    def __init__(self, product_database):
        self.products = product_database
        self.compatibility_matrix = self._build_compatibility_matrix()
        self.performance_tiers = self._define_performance_tiers()
        self.cost_benchmarks = self._load_cost_benchmarks()
    
    def _build_compatibility_matrix(self):
        """Build comprehensive product compatibility matrix"""
        return {
            'control_systems': {
                'crestron': {
                    'compatible_displays': ['samsung', 'lg', 'panasonic', 'sony'],
                    'protocols': ['CEC', 'RS-232', 'IP', 'IR'],
                    'max_outputs': 16
                },
                'extron': {
                    'compatible_displays': ['extron', 'samsung', 'sony', 'lg'],
                    'protocols': ['CEC', 'RS-232', 'IP'],
                    'max_outputs': 12
                },
                'amx': {
                    'compatible_displays': ['samsung', 'panasonic', 'sharp'],
                    'protocols': ['RS-232', 'IP', 'IR'],
                    'max_outputs': 8
                }
            },
            'mount_compatibility': {
                'weight_limits': {
                    'light_duty': 50,    # lbs
                    'medium_duty': 100,
                    'heavy_duty': 200,
                    'extra_heavy': 300
                },
                'vesa_patterns': {
                    'small': ['100x100', '200x200'],
                    'medium': ['400x400', '600x400'],
                    'large': ['800x400', '800x600']
                }
            },
            'signal_compatibility': {
                'hdmi_versions': {
                    'hdmi_1.4': {'max_resolution': '4K@30Hz', 'bandwidth': '10.2Gbps'},
                    'hdmi_2.0': {'max_resolution': '4K@60Hz', 'bandwidth': '18Gbps'},
                    'hdmi_2.1': {'max_resolution': '8K@60Hz', 'bandwidth': '48Gbps'}
                }
            }
        }
    
    def _define_performance_tiers(self):
        """Define product performance tiers"""
        return {
            'economy': {
                'display_brightness_min': 250,
                'audio_snr_min': 90,
                'warranty_years': 1,
                'mtbf_hours': 30000
            },
            'standard': {
                'display_brightness_min': 350,
                'audio_snr_min': 100,
                'warranty_years': 3,
                'mtbf_hours': 50000
            },
            'premium': {
                'display_brightness_min': 450,
                'audio_snr_min': 110,
                'warranty_years': 5,
                'mtbf_hours': 70000
            },
            'enterprise': {
                'display_brightness_min': 500,
                'audio_snr_min': 120,
                'warranty_years': 7,
                'mtbf_hours': 100000
            }
        }
    
    def _load_cost_benchmarks(self):
        """Load cost benchmarks for validation"""
        return {
            'display_per_inch': {
                'economy': 15,      # $ per inch diagonal
                'standard': 25,
                'premium': 40,
                'enterprise': 60
            },
            'audio_per_sqft': {
                'economy': 2,       # $ per sq ft coverage
                'standard': 4,
                'premium': 7,
                'enterprise': 12
            },
            'control_base_cost': {
                'economy': 500,
                'standard': 1500,
                'premium': 3000,
                'enterprise': 5000
            }
        }
    
    def find_optimal_products(self, requirements, budget_tier='standard'):
        """Find optimal product combinations with compatibility validation"""
        
        recommendations = {
            'displays': [],
            'audio': [],
            'control': [],
            'mounting': [],
            'cabling': [],
            'accessories': [],
            'services': []
        }
        
        # Display selection with AVIXA compliance
        display_requirements = self._extract_display_requirements(requirements, budget_tier)
        recommendations['displays'] = self._select_displays(display_requirements)
        
        # Audio system design
        audio_requirements = self._extract_audio_requirements(requirements, budget_tier)
        recommendations['audio'] = self._design_audio_system(audio_requirements)
        
        # Control system selection
        control_requirements = self._extract_control_requirements(requirements, budget_tier)
        recommendations['control'] = self._select_control_system(control_requirements)
        
        # Mounting and infrastructure
        recommendations['mounting'] = self._select_mounting_solutions(
            recommendations['displays'], requirements
        )
        
        # Cabling requirements
        recommendations['cabling'] = self._calculate_cabling_requirements(
            requirements, recommendations
        )
        
        # Professional services
        recommendations['services'] = self._define_professional_services(
            requirements, recommendations
        )
        
        return recommendations
    
    def _select_displays(self, requirements):
        """Select optimal displays based on requirements"""
        if not hasattr(self.products, 'iterrows'):
            return []
        
        display_products = self.products[
            self.products['category'].str.contains('display', case=False, na=False)
        ]
        
        selected_displays = []
        for _, product in display_products.iterrows():
            # Extract size from product name
            size_match = re.search(r'(\d+)"', product.get('name', ''))
            if size_match:
                size = int(size_match.group(1))
                if (requirements['min_size'] <= size <= requirements['max_size'] and
                    requirements['min_price'] <= product.get('price', 0) <= requirements['max_price']):
                    
                    selected_displays.append({
                        'category': 'Primary Display',
                        'name': product.get('name', ''),
                        'brand': product.get('brand', ''),
                        'model': product.get('model', ''),
                        'part_number': product.get('part_number', ''),
                        'specifications': self._generate_display_specs(product, size),
                        'quantity': requirements.get('quantity', 1),
                        'price': product.get('price', 0),
                        'installation_hours': 4,
                        'warranty_years': 3,
                        'lead_time_weeks': 2,
                        'notes': f'{size}" Professional Display - AVIXA Compliant'
                    })
                    break  # Take first matching product for simplicity
        
        return selected_displays
    
    def _generate_display_specs(self, product, size):
        """Generate comprehensive display specifications"""
        return f"{size}\" Diagonal, 3840x2160 4K Resolution, 400 cd/m² Brightness, 1000:1 Contrast, HDMI/DisplayPort Inputs"

# --- Quality Assurance Engine ---
class QualityAssuranceEngine:
    """Professional quality assurance for BOQ generation"""
    
    def __init__(self):
        self.validation_rules = self._load_validation_rules()
        self.cost_benchmarks = self._load_cost_benchmarks()
    
    def _load_validation_rules(self):
        """Load comprehensive validation rules"""
        return {
            'essential_categories': [
                'Primary Display', 'Audio System', 'Control System',
                'Video Conferencing', 'Mounting Hardware', 'Cabling',
                'Installation Services', 'Commissioning'
            ],
            'cost_validation': {
                'max_single_item_percentage': 40,  # No single item > 40% of total
                'min_services_percentage': 20,     # Services should be 20%+ of total
                'typical_markup_range': (1.15, 1.4)  # 15-40% markup range
            },
            'technical_validation': {
                'redundancy_requirements': ['control_processor', 'network_switch'],
                'backup_power_categories': ['control', 'network'],
                'certification_requirements': ['UL', 'FCC', 'CE']
            }
        }
    
    def _load_cost_benchmarks(self):
        """Load industry cost benchmarks"""
        return {
            'cost_per_sqft': {
                'huddle_room': (150, 300),
                'conference_room': (200, 500),
                'training_room': (300, 700),
                'auditorium': (500, 1200)
            },
            'category_percentages': {
                'displays': (25, 35),
                'audio': (15, 25),
                'control': (10, 20),
                'video_conf': (10, 20),
                'services': (20, 30)
            }
        }
    
    def validate_boq_completeness(self, boq_items, room_specs):
        """Comprehensive BOQ validation"""
        validation_report = {
            'missing_categories': [],
            'cost_anomalies': [],
            'technical_issues': [],
            'recommendations': [],
            'overall_score': 0
        }
        
        # Check completeness
        found_categories = [item.get('category', '') for item in boq_items]
        for essential_category in self.validation_rules['essential_categories']:
            if not any(essential_category.lower() in cat.lower() for cat in found_categories):
                validation_report['missing_categories'].append(essential_category)
        
        # Cost validation
        total_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in boq_items)
        room_area = room_specs.get('area', 200)
        room_type = room_specs.get('type', 'conference_room')
        
        # Cost per square foot validation
        cost_per_sqft = total_cost / room_area
        benchmark_range = self.cost_benchmarks['cost_per_sqft'].get(room_type, (200, 500))
        
        if cost_per_sqft < benchmark_range[0]:
            validation_report['cost_anomalies'].append(
                f"System cost unusually low: ${cost_per_sqft:.0f}/sq ft "
                f"(typical: ${benchmark_range[0]}-${benchmark_range[1]}/sq ft)"
            )
        elif cost_per_sqft > benchmark_range[1]:
            validation_report['cost_anomalies'].append(
                f"System cost above typical range: ${cost_per_sqft:.0f}/sq ft "
                f"(typical: ${benchmark_range[0]}-${benchmark_range[1]}/sq ft)"
            )
        
        # Technical validation
        self._validate_technical_requirements(boq_items, validation_report)
        
        # Calculate overall score
        validation_report['overall_score'] = self._calculate_validation_score(validation_report)
        
        return validation_report
    
    def _validate_technical_requirements(self, boq_items, report):
        """Validate technical requirements and standards compliance"""
        
        # Check for redundancy in critical systems
        control_items = [item for item in boq_items if 'control' in item.get('category', '').lower()]
        if len(control_items) == 1 and control_items[0].get('quantity', 1) == 1:
            report['recommendations'].append(
                "Consider redundant control processor for mission-critical applications"
            )
        
        # Validate power backup
        has_ups = any('ups' in item.get('name', '').lower() or 'backup' in item.get('name', '').lower() 
                     for item in boq_items)
        if not has_ups:
            report['technical_issues'].append(
                "Missing UPS/backup power for system reliability"
            )
        
        # Network infrastructure validation
        network_devices = len([item for item in boq_items 
                              if any(term in item.get('name', '').lower() 
                                   for term in ['switch', 'codec', 'processor', 'display'])])
        managed_switches = len([item for item in boq_items 
                               if 'managed' in item.get('name', '').lower() and 'switch' in item.get('name', '').lower()])
        
        if network_devices > 5 and managed_switches == 0:
            report['technical_issues'].append(
                "Consider managed network switch for complex installations"
            )
    
    def _calculate_validation_score(self, report):
        """Calculate overall validation score"""
        score = 100
        score -= len(report['missing_categories']) * 15
        score -= len(report['cost_anomalies']) * 10
        score -= len(report['technical_issues']) * 8
        
        return max(0, score)

# --- Professional Documentation Generator ---
class ProfessionalDocumentGenerator:
    """Generate industry-standard documentation packages"""
    
    def generate_complete_boq_package(self, boq_data, project_info, compliance_report):
        """Generate comprehensive professional BOQ package"""
        
        package = {}
        
        # Executive Summary
        package['executive_summary'] = self._create_executive_summary(boq_data, project_info)
        
        # Technical Specifications
        package['technical_specifications'] = self._create_detailed_tech_specs(boq_data)
        
        # Installation Timeline
        package['installation_timeline'] = self._create_installation_schedule(boq_data)
        
        # Compliance Report
        package['compliance_report'] = self._format_compliance_report(compliance_report)
        
        # Training Program
        package['training_program'] = self._create_training_curriculum(boq_data)
        
        # Warranty Matrix
        package['warranty_matrix'] = self._create_warranty_schedule(boq_data)
        
        # Maintenance Plan
        package['maintenance_plan'] = self._create_maintenance_program(boq_data)
        
        return package
    
    def _create_executive_summary(self, boq_data, project_info):
        """Create professional executive summary"""
        total_cost = sum(
            item.get('price', 0) * item.get('quantity', 1) 
            for category_items in boq_data.values() 
            for item in (category_items if isinstance(category_items, list) else [])
        )
        
        return f"""
# EXECUTIVE SUMMARY

**Project:** {project_info.get('name', 'Professional AV System Integration')}
**Client:** {project_info.get('client', 'Enterprise Client')}
**Date:** {datetime.now().strftime('%B %d, %Y')}
**Project Manager:** Professional AV Solutions Team

## SYSTEM OVERVIEW
This comprehensive audiovisual solution has been engineered to meet your organization's 
collaboration and communication requirements while maintaining strict compliance with 
AVIXA industry standards and best practices.

## KEY SYSTEM FEATURES
- **Enterprise-Grade Components**: All specified equipment meets commercial reliability standards
- **AVIXA Compliant Design**: System design follows current AVIXA guidelines for performance
- **Scalable Architecture**: Infrastructure designed to support future expansion requirements  
- **Professional Integration**: Complete installation, programming, and commissioning services
- **Comprehensive Support**: Multi-year warranty with preventive maintenance program

## INVESTMENT SUMMARY
- **Equipment & Materials**: ${total_cost * 0.70:,.2f}
- **Professional Services**: ${total_cost * 0.20:,.2f}
- **Engineering & Design**: ${total_cost * 0.05:,.2f}
- **Project Management**: ${total_cost * 0.05:,.2f}

### **TOTAL PROJECT INVESTMENT: ${total_cost:,.2f}**

## PROJECT TIMELINE
- **Design & Engineering**: 2-3 weeks
- **Equipment Procurement**: 4-6 weeks
- **Installation Phase**: 3-5 business days
- **System Commissioning**: 2-3 days  
- **User Training**: 1-2 days
- **Final Acceptance**: 1 day

### **Total Project Duration: 8-12 weeks from approval**

## QUALITY ASSURANCE
- All equipment backed by manufacturer warranties (3-5 years)
- Professional installation per AVIXA standards
- Complete system commissioning and performance verification
- Comprehensive user training program
- 90-day post-installation support period
"""
    
    def _create_detailed_tech_specs(self, boq_data):
        """Create detailed technical specifications"""
        specs = """
# TECHNICAL SPECIFICATIONS

## SYSTEM ARCHITECTURE
The proposed audiovisual system utilizes a distributed architecture with centralized 
control processing to ensure reliable operation and simplified management.

### SIGNAL FLOW DESIGN
- All video signals distributed via HDMI over Cat6A infrastructure
- Audio signals processed through dedicated DSP with automatic mixing
- Control signals distributed via IP network with RS-232 backup
- Power management through dedicated circuits with UPS backup

## PERFORMANCE SPECIFICATIONS

### VIDEO SUBSYSTEM
- **Resolution**: Native 4K (3840x2160) throughout signal chain
- **Color Space**: Full Rec. 709 color gamut support
- **Frame Rate**: 60Hz progressive scan
- **Latency**: <40ms end-to-end video latency
- **HDCP**: HDCP 2.2 compliance for content protection

### AUDIO SUBSYSTEM
- **Frequency Response**: 20Hz - 20kHz ±3dB
- **Signal-to-Noise Ratio**: >100dB
- **Total Harmonic Distortion**: <0.1% @ 1kHz
- **Maximum SPL**: 85dB @ 1 meter
- **Echo Cancellation**: Full-duplex with 128ms tail length
- **Noise Reduction**: Automatic ambient noise suppression

### CONTROL SUBSYSTEM
- **Response Time**: <200ms for all commands
- **Network Protocol**: TCP/IP with SSL encryption
- **Backup Control**: IR and RS-232 failover capability
- **User Interface**: Responsive touch panel with haptic feedback
"""
        
        return specs
    
    def _create_installation_schedule(self, boq_data):
        """Create detailed installation timeline"""
        return """
# INSTALLATION SCHEDULE

## PRE-INSTALLATION (Week -2 to -1)
- **Site Survey Confirmation**: Validate all measurements and infrastructure
- **Equipment Staging**: Receive and inventory all system components
- **Coordination Meeting**: Final walkthrough with client facilities team
- **Permit Acquisition**: Obtain all required electrical/low-voltage permits

## INSTALLATION PHASE

### Day 1: Infrastructure & Mounting
- **Morning (8:00-12:00)**
  - Install display mounting hardware
  - Run all cabling (power, data, video)
  - Install equipment rack and grounding
- **Afternoon (1:00-5:00)**
  - Mount displays and verify positioning
  - Install ceiling speakers and microphones
  - Complete all low-voltage connections

### Day 2: Equipment Installation
- **Morning (8:00-12:00)**
  - Install and rack all electronic components
  - Complete all signal path connections
  - Initial power-on and basic connectivity tests
- **Afternoon (1:00-5:00)**
  - Install control interfaces
  - Complete network configuration
  - Basic system functionality verification

### Day 3: Programming & Commissioning
- **Morning (8:00-12:00)**
  - Control system programming and configuration
  - Audio DSP tuning and optimization
  - Video system calibration and setup
- **Afternoon (1:00-5:00)**
  - System integration testing
  - Performance verification and documentation
  - Initial user interface training

## POST-INSTALLATION
- **System Documentation**: Complete as-built drawings and documentation
- **User Training**: Comprehensive training for all system operators
- **Warranty Registration**: Register all equipment warranties
- **Final Acceptance**: Client sign-off and project completion
"""
    
    def _format_compliance_report(self, compliance_report):
        """Format the compliance report for documentation"""
        if not compliance_report:
            return "# COMPLIANCE REPORT\n\nCompliance validation pending system finalization."
        
        report = f"""
# AVIXA COMPLIANCE REPORT

## OVERALL COMPLIANCE STATUS
**Compliance Score**: {compliance_report.get('compliance_score', 0)}/100
**Status**: {'✓ COMPLIANT' if compliance_report.get('compliant', False) else '⚠ ISSUES IDENTIFIED'}

## COMPLIANCE ANALYSIS

### Standards Adherence
- **AVIXA Display Guidelines**: Viewing distance and sizing per 2H/8H rule
- **Audio Performance Standards**: SPL and coverage requirements met
- **Infrastructure Requirements**: Power and cooling calculations validated
- **Accessibility Compliance**: ADA requirements addressed where applicable

"""
        
        if compliance_report.get('errors'):
            report += "### Critical Issues (Must Address)\n"
            for error in compliance_report['errors']:
                report += f"- ❌ {error}\n"
            report += "\n"
        
        if compliance_report.get('warnings'):
            report += "### Warnings (Recommended Action)\n"
            for warning in compliance_report['warnings']:
                report += f"- ⚠️ {warning}\n"
            report += "\n"
        
        if compliance_report.get('recommendations'):
            report += "### Optimization Recommendations\n"
            for rec in compliance_report['recommendations']:
                report += f"- 💡 {rec}\n"
            report += "\n"
        
        return report
    
    def _create_training_curriculum(self, boq_data):
        """Create comprehensive training program"""
        return """
# USER TRAINING CURRICULUM

## TRAINING OVERVIEW
Comprehensive hands-on training program designed to ensure confident system operation
by all designated users and administrators.

## SESSION 1: BASIC OPERATIONS (2 hours)
### System Startup & Shutdown
- Proper system power-on sequence
- Display activation and source selection
- Audio system initialization
- Safe shutdown procedures

### Primary Functions
- Content sharing from laptops and mobile devices
- Video conferencing setup and operation
- Basic audio level adjustments
- Simple troubleshooting procedures

## SESSION 2: ADVANCED FEATURES (2 hours)
### Video Conferencing Management
- Contact directory management
- Advanced calling features
- Content sharing during calls
- Recording and streaming options

### System Customization
- Preset creation and management
- User preference settings
- Custom control layouts
- Integration with calendar systems

## SESSION 3: ADMINISTRATION (1 hour)
### System Maintenance
- Daily operational checks
- Cleaning and care procedures
- Basic diagnostics
- When to contact support

### Documentation Review
- User manual walkthrough
- Quick reference guide
- Emergency contact procedures
- Warranty and support information

## TRAINING MATERIALS PROVIDED
- Laminated quick reference cards
- Video tutorials (USB drive)
- Complete user manual
- Emergency contact information
- System warranty documentation
"""
    
    def _create_warranty_schedule(self, boq_data):
        """Create comprehensive warranty matrix"""
        return """
# WARRANTY & SUPPORT MATRIX

## MANUFACTURER WARRANTIES

### Display Systems
- **Warranty Period**: 3 Years Parts & Labor
- **Coverage**: Full replacement for manufacturing defects
- **Response Time**: Next business day for critical failures
- **Support**: 24/7 technical support hotline

### Audio Equipment
- **Warranty Period**: 5 Years Parts & Labor  
- **Coverage**: Component-level repair or replacement
- **Response Time**: 4-hour response for system-down issues
- **Support**: Direct manufacturer technical support

### Control Systems
- **Warranty Period**: 2 Years Hardware, 1 Year Software
- **Coverage**: Full system including programming
- **Response Time**: Same-day remote support
- **Support**: Dedicated control systems engineer

### Installation Services
- **Warranty Period**: 1 Year Workmanship Warranty
- **Coverage**: All installation work and system integration
- **Response Time**: 24-hour response guarantee
- **Support**: On-site service technician

## EXTENDED SUPPORT OPTIONS

### Premium Support Package
- Extended 5-year comprehensive coverage
- Quarterly preventive maintenance visits
- Priority technical support (2-hour response)
- Annual system performance optimization
- User refresher training sessions

### Standard Support Package  
- Extended 3-year parts and labor coverage
- Semi-annual maintenance visits
- Business hours technical support
- Annual system health check
"""
    
    def _create_maintenance_program(self, boq_data):
        """Create comprehensive maintenance program"""
        return """
# PREVENTIVE MAINTENANCE PROGRAM

## MAINTENANCE PHILOSOPHY
Proactive maintenance approach designed to maximize system reliability,
extend equipment lifespan, and ensure optimal performance.

## QUARTERLY MAINTENANCE (Every 3 Months)

### System Health Assessment
- Complete system diagnostic scan
- Performance benchmark testing
- Error log analysis and cleanup
- Security update verification

### Physical Inspection
- Visual inspection of all connections
- Display screen cleaning and calibration check
- Audio component inspection and testing
- Control interface cleaning and testing

### Preventive Actions
- Firmware update installation
- System backup and configuration archival
- User feedback collection and analysis
- Performance optimization adjustments

## ANNUAL COMPREHENSIVE SERVICE

### Complete System Overhaul
- Full electrical safety inspection
- Comprehensive performance testing
- Cable management and organization review
- Thermal analysis and cooling verification

### Technology Refresh Assessment
- Equipment lifecycle analysis
- Emerging technology evaluation
- Upgrade path recommendations
- Budget planning for future enhancements

### Documentation Updates
- As-built drawing verification
- User manual updates
- Training material refresh
- Warranty status review

## EMERGENCY RESPONSE PROTOCOL

### Critical System Failure
- **Response Time**: 4 hours maximum
- **Escalation**: Direct technician dispatch
- **Communication**: Hourly status updates
- **Resolution**: Temporary workaround within 8 hours

### Non-Critical Issues
- **Response Time**: Next business day
- **Support Method**: Remote diagnosis preferred
- **Communication**: 24-hour status update
- **Resolution**: Permanent fix within 48 hours

## MAINTENANCE RECORD KEEPING
- Digital maintenance logs
- Performance trend analysis
- Cost tracking and reporting
- Predictive failure analysis
"""

# --- Streamlit Application Interface ---

def main():
    """Main Streamlit application"""
    
    # Custom CSS for professional styling
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72, #2a5298);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
    }
    .compliance-pass { color: #28a745; font-weight: bold; }
    .compliance-warning { color: #ffc107; font-weight: bold; }
    .compliance-error { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
    
    # Application header
    st.markdown("""
    <div class="main-header">
        <h1>⚡ Enterprise AV BOQ Generator Pro</h1>
        <p>Professional Audiovisual System Design & Documentation Platform</p>
        <p><i>AVIXA Standards Compliant | Enterprise Grade Solutions</i></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'boq_generated' not in st.session_state:
        st.session_state.boq_generated = False
    if 'current_boq' not in st.session_state:
        st.session_state.current_boq = {}
    if 'project_info' not in st.session_state:
        st.session_state.project_info = {}
    
    # Sidebar configuration
    with st.sidebar:
        st.header("🎯 Project Configuration")
        
        # Gemini API configuration
        st.subheader("AI Configuration")
        api_key = st.text_input("Gemini API Key", type="password")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                st.success("✓ AI Engine Connected")
            except Exception as e:
                st.error(f"❌ API Configuration Error: {str(e)}")
        
        # Project information
        st.subheader("Project Details")
        project_name = st.text_input("Project Name", value="Enterprise AV Integration")
        client_name = st.text_input("Client Organization", value="Professional Client")
        project_manager = st.text_input("Project Manager", value="AV Solutions Team")
        
        st.session_state.project_info = {
            'name': project_name,
            'client': client_name,
            'manager': project_manager,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        # File upload for product database
        st.subheader("Product Database")
        uploaded_file = st.file_uploader(
            "Upload Product Catalog (CSV)", 
            type=['csv'],
            help="Upload your product database with columns: name, category, brand, price, specifications"
        )
        
        # Budget and quality settings
        st.subheader("System Parameters")
        budget_tier = st.selectbox(
            "Quality Tier",
            ['economy', 'standard', 'premium', 'enterprise'],
            index=1,
            help="Select quality/performance tier for equipment selection"
        )
        
        max_budget = st.number_input(
            "Maximum Budget ($)",
            min_value=1000,
            max_value=500000,
            value=25000,
            step=1000,
            help="Set maximum project budget for recommendations"
        )
    
    # Main application tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏗️ System Design", 
        "📊 BOQ Generation", 
        "✅ Compliance Check", 
        "📋 Documentation", 
        "📈 Analytics"
    ])
    
    with tab1:
        st.header("Professional System Design")
        
        # Room specification input
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Room Specifications")
            room_type = st.selectbox(
                "Room Type",
                [
                    'huddle_room', 'conference_room', 'training_room', 
                    'auditorium', 'boardroom', 'multipurpose'
                ],
                index=1
            )
            
            room_length = st.number_input("Room Length (ft)", min_value=8, max_value=100, value=16)
            room_width = st.number_input("Room Width (ft)", min_value=6, max_value=80, value=12)
            ceiling_height = st.number_input("Ceiling Height (ft)", min_value=8, max_value=20, value=9)
            
            room_area = room_length * room_width
            st.metric("Room Area", f"{room_area:,} sq ft")
        
        with col2:
            st.subheader("Usage Requirements")
            max_occupancy = st.number_input("Maximum Occupancy", min_value=2, max_value=200, value=12)
            
            usage_patterns = st.multiselect(
                "Primary Uses",
                [
                    'Video Conferencing', 'Presentations', 'Training', 
                    'Collaboration', 'Streaming', 'Recording'
                ],
                default=['Video Conferencing', 'Presentations']
            )
            
            ada_compliance = st.checkbox("ADA Compliance Required", value=False)
            redundancy_required = st.checkbox("Mission Critical (Redundancy)", value=False)
            
            # Environmental considerations
            ambient_light = st.select_slider(
                "Ambient Light Level",
                options=['Low', 'Medium', 'High', 'Very High'],
                value='Medium'
            )
        
        # System requirements
        st.subheader("System Requirements")
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            st.write("**Display Requirements**")
            display_count = st.number_input("Number of Displays", min_value=1, max_value=10, value=1)
            display_size_pref = st.select_slider(
                "Preferred Display Size",
                options=['55"', '65"', '75"', '86"', '98"'],
                value='75"'
            )
            
        with col4:
            st.write("**Audio Requirements**")
            audio_zones = st.number_input("Audio Zones", min_value=1, max_value=5, value=1)
            wireless_mics = st.checkbox("Wireless Microphones", value=True)
            ceiling_speakers = st.checkbox("Ceiling Speakers", value=True)
            
        with col5:
            st.write("**Control & Integration**")
            touch_panel = st.checkbox("Touch Panel Control", value=True)
            room_scheduling = st.checkbox("Room Scheduling Integration", value=False)
            lighting_control = st.checkbox("Lighting Control", value=False)
        
        # Store room specifications
        room_specs = {
            'type': room_type,
            'length': room_length,
            'width': room_width,
            'ceiling_height': ceiling_height,
            'area': room_area,
            'occupancy': max_occupancy,
            'usage_patterns': usage_patterns,
            'ada_compliance': ada_compliance,
            'redundancy_required': redundancy_required,
            'ambient_light': ambient_light,
            'display_count': display_count,
            'display_size': display_size_pref,
            'audio_zones': audio_zones
        }
        
        if st.button("🎯 Generate System Design", type="primary"):
            if api_key:
                with st.spinner("Generating professional system design..."):
                    # Initialize engines
                    compliance_engine = AVIXAComplianceEngine()
                    
                    # Load product database
                    product_db = None
                    if uploaded_file:
                        try:
                            product_db = pd.read_csv(uploaded_file)
                            st.success(f"✓ Loaded {len(product_db)} products from database")
                        except Exception as e:
                            st.warning(f"Could not load product database: {e}")
                    
                    # Generate AI-powered requirements
                    system_prompt = f"""
                    You are a professional AV system designer with expertise in AVIXA standards.
                    Generate a comprehensive BOQ for the following room:
                    
                    Room Type: {room_type}
                    Dimensions: {room_length}' x {room_width}' x {ceiling_height}'
                    Area: {room_area} sq ft
                    Occupancy: {max_occupancy} people
                    Usage: {', '.join(usage_patterns)}
                    Budget Tier: {budget_tier}
                    Max Budget: ${max_budget:,}
                    
                    Generate a detailed equipment list with:
                    1. Primary displays sized per AVIXA 2H/8H rule
                    2. Professional audio system with proper coverage
                    3. Video conferencing solution
                    4. Control system with touch panel
                    5. Infrastructure (mounting, cabling, power)
                    6. Installation and commissioning services
                    
                    Format as structured data with categories, quantities, and estimated pricing.
                    """
                    
                    try:
                        # Generate with Gemini
                        model = genai.GenerativeModel('gemini-pro')
                        response = model.generate_content(system_prompt)
                        
                        # For demonstration, create a structured BOQ
                        demo_boq = generate_demo_boq(room_specs, budget_tier, max_budget)
                        st.session_state.current_boq = demo_boq
                        st.session_state.boq_generated = True
                        
                        st.success("✓ Professional system design generated successfully!")
                        
                        # Display design summary
                        st.subheader("System Design Summary")
                        
                        total_cost = sum(
                            item.get('price', 0) * item.get('quantity', 1)
                            for category_items in demo_boq.values()
                            for item in (category_items if isinstance(category_items, list) else [])
                        )
                        
                        col6, col7, col8, col9 = st.columns(4)
                        with col6:
                            st.metric("Total Investment", f"${total_cost:,.0f}")
                        with col7:
                            st.metric("Cost per Sq Ft", f"${total_cost/room_area:.0f}")
                        with col8:
                            st.metric("Equipment Items", f"{sum(len(items) for items in demo_boq.values() if isinstance(items, list))}")
                        with col9:
                            st.metric("Installation Days", "3-5")
                        
                    except Exception as e:
                        st.error(f"Error generating design: {str(e)}")
            else:
                st.warning("Please enter your Gemini API key to generate system design.")

def generate_demo_boq(room_specs, budget_tier, max_budget):
    """Generate a comprehensive demo BOQ"""
    
    room_area = room_specs['area']
    display_size = int(room_specs['display_size'].replace('"', ''))
    
    # Tier-based pricing multipliers
    tier_multipliers = {
        'economy': 0.7,
        'standard': 1.0,
        'premium': 1.4,
        'enterprise': 1.8
    }
    
    multiplier = tier_multipliers.get(budget_tier, 1.0)
    
    boq = {
        'displays': [
            {
                'category': 'Primary Display',
                'name': f'Professional {display_size}" 4K Display',
                'brand': 'Samsung Business',
                'model': f'QM{display_size}H',
                'part_number': f'LH{display_size}QMHPLGC/GO',
                'specifications': f'{display_size}" 4K UHD, 400 cd/m², 24/7 Operation, HDMI/DP inputs',
                'quantity': room_specs['display_count'],
                'price': int(2500 * multiplier * (display_size / 75)),
                'installation_hours': 4,
                'warranty_years': 3,
                'lead_time_weeks': 2,
                'notes': f'AVIXA compliant sizing for {room_specs["length"]}ft viewing distance'
            }
        ],
        'audio': [
            {
                'category': 'Audio DSP',
                'name': 'Professional Audio Processor',
                'brand': 'Biamp',
                'model': 'Tesira FORTE AVB VT4',
                'part_number': '910.3200.900',
                'specifications': '4x4 AVB Audio Server with VoIP, AEC, Dante',
                'quantity': 1,
                'price': int(1800 * multiplier),
                'installation_hours': 6,
                'warranty_years': 5,
                'lead_time_weeks': 3,
                'notes': 'Handles all audio processing and conferencing'
            },
            {
                'category': 'Ceiling Speakers',
                'name': 'Ceiling Mount Speakers',
                'brand': 'Biamp',
                'model': 'Desono C-IC6',
                'part_number': '906.101.900',
                'specifications': '6" Ceiling Speaker, 70/100V, Frequency: 65Hz-22kHz',
                'quantity': max(2, int(room_area / 100)),
                'price': int(320 * multiplier),
                'installation_hours': 2,
                'warranty_years': 5,
                'lead_time_weeks': 2,
                'notes': 'Even coverage throughout space'
            },
            {
                'category': 'Microphone System',
                'name': 'Wireless Microphone System',
                'brand': 'Shure',
                'model': 'ULXD124/85',
                'part_number': 'ULXD124/85-G50',
                'specifications': 'Digital wireless handheld system, 80MHz tuning bandwidth',
                'quantity': 2 if room_specs['occupancy'] > 20 else 1,
                'price': int(1200 * multiplier),
                'installation_hours': 3,
                'warranty_years': 2,
                'lead_time_weeks': 2,
                'notes': 'Presentation and Q&A microphones'
            }
        ],
        'video_conferencing': [
            {
                'category': 'Video Codec',
                'name': 'Professional Video Conferencing System',
                'brand': 'Poly',
                'model': 'Studio X70',
                'part_number': '2200-87030-001',
                'specifications': '4K Ultra HD, Dual camera system, NoiseBlockAI, DirectorAI',
                'quantity': 1,
                'price': int(4500 * multiplier),
                'installation_hours': 4,
                'warranty_years': 1,
                'lead_time_weeks': 3,
                'notes': 'Complete video conferencing solution'
            },
            {
                'category': 'PTZ Camera',
                'name': 'PTZ Conference Camera',
                'brand': 'Poly',
                'model': 'EagleEye IV 12x',
                'part_number': '8200-64370-001',
                'specifications': '12x optical zoom, 1080p60, HDMI/3G-SDI output',
                'quantity': 1,
                'price': int(2800 * multiplier),
                'installation_hours': 3,
                'warranty_years': 2,
                'lead_time_weeks': 2,
                'notes': 'Wide angle and presenter tracking'
            }
        ],
        'control': [
            {
                'category': 'Control Processor',
                'name': 'AV Control System',
                'brand': 'Extron',
                'model': 'DMP 128 Plus AT',
                'part_number': '60-1509-01',
                'specifications': 'DSP with AEC, VoIP, Dante, 12x8 matrix mixer',
                'quantity': 1,
                'price': int(3200 * multiplier),
                'installation_hours': 8,
                'warranty_years': 3,
                'lead_time_weeks': 4,
                'notes': 'Central system control and audio processing'
            },
            {
                'category': 'Touch Panel',
                'name': 'Wall Mount Touch Panel',
                'brand': 'Extron',
                'model': 'TLP Pro 725T',
                'part_number': '60-1496-01',
                'specifications': '7" capacitive touchscreen, PoE+, built-in camera',
                'quantity': 1,
                'price': int(1800 * multiplier),
                'installation_hours': 3,
                'warranty_years': 2,
                'lead_time_weeks': 3,
                'notes': 'Primary user control interface'
            }
        ],
        'infrastructure': [
            {
                'category': 'Display Mount',
                'name': 'Fixed Wall Mount',
                'brand': 'Chief',
                'model': 'PFMUB',
                'part_number': 'PFMUB',
                'specifications': f'Universal mount for {display_size-10}"-{display_size+10}" displays, 200 lb capacity',
                'quantity': room_specs['display_count'],
                'price': int(280 * multiplier),
                'installation_hours': 2,
                'warranty_years': 10,
                'lead_time_weeks': 1,
                'notes': 'Professional grade mounting hardware'
            },
            {
                'category': 'Network Switch',
                'name': 'Managed Network Switch',
                'brand': 'Netgear',
                'model': 'GS728TP',
                'part_number': 'GS728TP-100NAS',
                'specifications': '24-Port PoE+ Gigabit switch, 4x SFP ports, 380W PoE budget',
                'quantity': 1,
                'price': int(650 * multiplier),
                'installation_hours': 2,
                'warranty_years': 5,
                'lead_time_weeks': 1,
                'notes': 'Network infrastructure for all IP devices'
            },
            {
                'category': 'Rack Cabinet',
                'name': 'Equipment Rack',
                'brand': 'Middle Atlantic',
                'model': 'ERK-1220',
                'part_number': 'ERK-1220-44',
                'specifications': '12RU wall mount rack, 20" deep, locking door',
                'quantity': 1,
                'price': int(580 * multiplier),
                'installation_hours': 3,
                'warranty_years': 10,
                'lead_time_weeks': 2,
                'notes': 'Houses all rack-mount equipment'
            },
            {
                'category': 'UPS Battery Backup',
                'name': 'Uninterruptible Power Supply',
                'brand': 'APC',
                'model': 'SMT1500RM2U',
                'part_number': 'SMT1500RM2U',
                'specifications': '1500VA/1000W, 2U rackmount, LCD display, network management',
                'quantity': 1,
                'price': int(750 * multiplier),
                'installation_hours': 1,
                'warranty_years': 3,
                'lead_time_weeks': 1,
                'notes': 'Backup power for critical systems'
            }
        ],
        'cabling': [
            {
                'category': 'Structured Cabling',
                'name': 'Cat6A Cable Installation',
                'brand': 'Belden',
                'model': '10GX13',
                'part_number': '2413F',
                'specifications': 'Cat6A 23AWG, 10Gb rated, plenum rated',
                'quantity': int(room_area / 20),  # Estimated cable runs
                'price': int(180 * multiplier),
                'installation_hours': 4,
                'warranty_years': 25,
                'lead_time_weeks': 1,
                'notes': 'Complete structured cabling system'
            },
            {
                'category': 'HDMI Distribution',
                'name': 'HDMI over IP Transmitters/Receivers',
                'brand': 'Extron',
                'model': 'NAV Pro Xi Series',
                'part_number': 'NAV 101 Xi T/R',
                'specifications': '4K60 4:4:4, uncompressed, <1 frame latency',
                'quantity': 4,  # TX/RX pairs
                'price': int(890 * multiplier),
                'installation_hours': 2,
                'warranty_years': 3,
                'lead_time_weeks': 3,
                'notes': '4K video distribution over IP'
            }
        ],
        'services': [
            {
                'category': 'System Design',
                'name': 'Professional System Design',
                'brand': 'AV Integration Services',
                'model': 'DESIGN-PRO',
                'part_number': 'SVC-DESIGN-001',
                'specifications': 'Complete system design, CAD drawings, specifications',
                'quantity': 1,
                'price': int(2500 * multiplier),
                'installation_hours': 40,
                'warranty_years': 1,
                'lead_time_weeks': 2,
                'notes': 'Professional engineering and design services'
            },
            {
                'category': 'Installation Services',
                'name': 'Complete System Installation',
                'brand': 'AV Integration Services',
                'model': 'INSTALL-PRO',
                'part_number': 'SVC-INSTALL-001',
                'specifications': 'Complete installation, termination, and basic testing',
                'quantity': 1,
                'price': int(4800 * multiplier),
                'installation_hours': 32,
                'warranty_years': 1,
                'lead_time_weeks': 1,
                'notes': 'Professional installation and integration'
            },
            {
                'category': 'System Programming',
                'name': 'Control System Programming',
                'brand': 'AV Integration Services',
                'model': 'PROGRAM-PRO',
                'part_number': 'SVC-PROGRAM-001',
                'specifications': 'Complete control system programming and user interface design',
                'quantity': 1,
                'price': int(3500 * multiplier),
                'installation_hours': 24,
                'warranty_years': 1,
                'lead_time_weeks': 1,
                'notes': 'Custom programming and user interface'
            },
            {
                'category': 'System Commissioning',
                'name': 'System Testing & Commissioning',
                'brand': 'AV Integration Services',
                'model': 'COMMISSION-PRO',
                'part_number': 'SVC-COMMISSION-001',
                'specifications': 'Complete system testing, optimization, and documentation',
                'quantity': 1,
                'price': int(1800 * multiplier),
                'installation_hours': 16,
                'warranty_years': 1,
                'lead_time_weeks': 1,
                'notes': 'Performance verification and optimization'
            },
            {
                'category': 'User Training',
                'name': 'End User Training Program',
                'brand': 'AV Integration Services',
                'model': 'TRAINING-PRO',
                'part_number': 'SVC-TRAINING-001',
                'specifications': 'Comprehensive user training and documentation',
                'quantity': 1,
                'price': int(1200 * multiplier),
                'installation_hours': 8,
                'warranty_years': 0,
                'lead_time_weeks': 0,
                'notes': 'On-site user training and documentation'
            },
            {
                'category': 'Project Management',
                'name': 'Professional Project Management',
                'brand': 'AV Integration Services',
                'model': 'PM-PRO',
                'part_number': 'SVC-PM-001',
                'specifications': 'Complete project coordination and management',
                'quantity': 1,
                'price': int(2200 * multiplier),
                'installation_hours': 0,
                'warranty_years': 0,
                'lead_time_weeks': 0,
                'notes': 'End-to-end project management services'
            }
        ]
    }
    
    return boq

    with tab2:
        st.header("Professional BOQ Generation")
        
        if st.session_state.boq_generated and st.session_state.current_boq:
            boq_data = st.session_state.current_boq
            
            # Calculate totals
            total_equipment_cost = 0
            total_services_cost = 0
            total_items = 0
            
            for category, items in boq_data.items():
                if isinstance(items, list):
                    for item in items:
                        item_cost = item.get('price', 0) * item.get('quantity', 1)
                        if 'services' in category.lower() or 'service' in item.get('category', '').lower():
                            total_services_cost += item_cost
                        else:
                            total_equipment_cost += item_cost
                        total_items += 1
            
            total_project_cost = total_equipment_cost + total_services_cost
            
            # Display summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Project Cost", f"${total_project_cost:,.0f}")
            with col2:
                st.metric("Equipment Cost", f"${total_equipment_cost:,.0f}")
            with col3:
                st.metric("Services Cost", f"${total_services_cost:,.0f}")
            with col4:
                st.metric("Total Line Items", f"{total_items}")
            
            # Detailed BOQ tables
            for category_name, items in boq_data.items():
                if isinstance(items, list) and items:
                    st.subheader(f"{category_name.replace('_', ' ').title()}")
                    
                    # Convert to DataFrame for display
                    df_items = []
                    for item in items:
                        df_items.append({
                            'Item': item.get('name', ''),
                            'Brand': item.get('brand', ''),
                            'Model': item.get('model', ''),
                            'Part Number': item.get('part_number', ''),
                            'Qty': item.get('quantity', 1),
                            'Unit Price': f"${item.get('price', 0):,.0f}",
                            'Total': f"${item.get('price', 0) * item.get('quantity', 1):,.0f}",
                            'Lead Time': f"{item.get('lead_time_weeks', 0)} weeks",
                            'Warranty': f"{item.get('warranty_years', 0)} years"
                        })
                    
                    if df_items:
                        df = pd.DataFrame(df_items)
                        st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Export options
            st.subheader("Export Options")
            col5, col6, col7 = st.columns(3)
            
            with col5:
                if st.button("📊 Export to Excel"):
                    excel_data = create_excel_export(boq_data, st.session_state.project_info)
                    st.download_button(
                        label="📥 Download Excel BOQ",
                        data=excel_data,
                        file_name=f"BOQ_{st.session_state.project_info.get('name', 'Project').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            
            with col6:
                if st.button("📋 Export to CSV"):
                    csv_data = create_csv_export(boq_data)
                    st.download_button(
                        label="📥 Download CSV BOQ",
                        data=csv_data,
                        file_name=f"BOQ_{st.session_state.project_info.get('name', 'Project').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            with col7:
                if st.button("📄 Generate PDF Report"):
                    st.info("PDF generation feature coming soon!")
        
        else:
            st.info("👈 Please generate a system design first in the System Design tab.")
    
    with tab3:
        st.header("AVIXA Compliance Validation")
        
        if st.session_state.boq_generated and st.session_state.current_boq:
            # Run compliance check
            compliance_engine = AVIXAComplianceEngine()
            
            # Flatten BOQ items for compliance checking
            all_items = []
            for category, items in st.session_state.current_boq.items():
                if isinstance(items, list):
                    all_items.extend(items)
            
            # Get room specs from session or use defaults
            room_specs = getattr(st.session_state, 'room_specs', {
                'type': 'conference_room',
                'length': 16,
                'width': 12,
                'area': 192,
                'occupancy': 12
            })
            
            compliance_report = compliance_engine.validate_system_design(all_items, room_specs)
            
            # Display compliance score
            score = compliance_report.get('compliance_score', 0)
            if score >= 90:
                score_color = "compliance-pass"
                status_icon = "✅"
            elif score >= 70:
                score_color = "compliance-warning" 
                status_icon = "⚠️"
            else:
                score_color = "compliance-error"
                status_icon = "❌"
            
            st.markdown(f"""
            <div class="metric-card">
                <h2>{status_icon} Compliance Score: <span class="{score_color}">{score}/100</span></h2>
                <p>Overall Status: <span class="{score_color}">
                {'COMPLIANT' if compliance_report.get('compliant', False) else 'ISSUES IDENTIFIED'}
                </span></p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display issues and recommendations
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("❌ Critical Issues")
                if compliance_report.get('errors'):
                    for error in compliance_report['errors']:
                        st.error(error)
                else:
                    st.success("No critical compliance issues found!")
            
            with col2:
                st.subheader("⚠️ Warnings")
                if compliance_report.get('warnings'):
                    for warning in compliance_report['warnings']:
                        st.warning(warning)
                else:
                    st.info("No warnings identified.")
            
            with col3:
                st.subheader("💡 Recommendations")
                if compliance_report.get('recommendations'):
                    for rec in compliance_report['recommendations']:
                        st.info(rec)
                else:
                    st.success("System meets all best practices!")
            
            # Detailed compliance breakdown
            st.subheader("Detailed Compliance Analysis")
            
            compliance_categories = {
                'Display Standards': ['AVIXA 2H/8H viewing distance rule', 'Brightness requirements', 'Resolution standards'],
                'Audio Standards': ['SPL requirements', 'Microphone coverage', 'Echo cancellation'],
                'Infrastructure': ['Power safety margins', 'Cooling requirements', 'Network capacity'],
                'Accessibility': ['ADA compliance', 'Control accessibility', 'Visual indicators']
            }
            
            for category, standards in compliance_categories.items():
                with st.expander(f"📋 {category} Compliance"):
                    for standard in standards:
                        # Simulate compliance status (in real implementation, this would check actual compliance)
                        status = "✅ Compliant" if score > 70 else "⚠️ Review Required"
                        st.write(f"**{standard}**: {status}")
        
        else:
            st.info("👈 Please generate a system design first to run compliance validation.")
    
    with tab4:
        st.header("Professional Documentation Package")
        
        if st.session_state.boq_generated and st.session_state.current_boq:
            doc_generator = ProfessionalDocumentGenerator()
            
            # Generate documentation package
            compliance_report = AVIXAComplianceEngine().validate_system_design([], {})
            doc_package = doc_generator.generate_complete_boq_package(
                st.session_state.current_boq,
                st.session_state.project_info,
                compliance_report
            )
            
            # Document selection
            st.subheader("📋 Available Documents")
            
            doc_options = {
                'Executive Summary': 'executive_summary',
                'Technical Specifications': 'technical_specifications', 
                'Installation Timeline': 'installation_timeline',
                'Compliance Report': 'compliance_report',
                'Training Program': 'training_program',
                'Warranty Matrix': 'warranty_matrix',
                'Maintenance Plan': 'maintenance_plan'
            }
            
            selected_docs = st.multiselect(
                "Select documents to generate:",
                list(doc_options.keys()),
                default=list(doc_options.keys())[:3]
            )
            
            # Generate and display selected documents
            for doc_name in selected_docs:
                doc_key = doc_options[doc_name]
                if doc_key in doc_package:
                    with st.expander(f"📄 {doc_name}", expanded=True):
                        st.markdown(doc_package[doc_key])
            
            # Download options
            st.subheader("📥 Download Documentation")
            
            if st.button("Generate Complete Documentation Package"):
                # Create combined document
                combined_doc = f"""
# {st.session_state.project_info.get('name', 'AV System Integration')}
## Professional Documentation Package

Generated on: {datetime.now().strftime('%B %d, %Y')}
Project Manager: {st.session_state.project_info.get('manager', 'AV Solutions Team')}

---

"""
                
                for doc_name in selected_docs:
                    doc_key = doc_options[doc_name]
                    if doc_key in doc_package:
                        combined_doc += doc_package[doc_key] + "\n\n---\n\n"
                
                st.download_button(
                    label="📥 Download Complete Documentation (Markdown)",
                    data=combined_doc,
                    file_name=f"AV_Documentation_{st.session_state.project_info.get('name', 'Project').replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown"
                )
        
        else:
            st.info("👈 Please generate a system design first to create documentation.")
    
    with tab5:
        st.header("Project Analytics & Insights")
        
        if st.session_state.boq_generated and st.session_state.current_boq:
            boq_data = st.session_state.current_boq
            
            # Prepare data for analysis
            categories = []
            costs = []
            quantities = []
            
            for category, items in boq_data.items():
                if isinstance(items, list):
                    category_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
                    category_qty = sum(item.get('quantity', 1) for item in items)
                    
                    categories.append(category.replace('_', ' ').title())
                    costs.append(category_cost)
                    quantities.append(category_qty)
            
            # Cost breakdown chart
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("💰 Cost Breakdown by Category")
                if categories and costs:
                    fig_pie = px.pie(
                        values=costs,
                        names=categories,
                        title="Project Cost Distribution"
                    )
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.subheader("📊 Item Quantity by Category")
                if categories and quantities:
                    fig_bar = px.bar(
                        x=categories,
                        y=quantities,
                        title="Equipment Quantities by Category"
                    )
                    fig_bar.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_bar, use_container_width=True)
            
            # Cost analysis metrics
            st.subheader("📈 Cost Analysis")
            
            total_cost = sum(costs)
            room_area = 192  # Default, would come from room specs in real implementation
            
            col3, col4, col5, col6 = st.columns(4)
            
            with col3:
                st.metric("Cost per Sq Ft", f"${total_cost/room_area:.0f}")
            
            with col4:
                equipment_cost = sum(cost for i, cost in enumerate(costs) if 'service' not in categories[i].lower())
                st.metric("Equipment %", f"{(equipment_cost/total_cost)*100:.0f}%")
            
            with col5:
                services_cost = total_cost - equipment_cost
                st.metric("Services %", f"{(services_cost/total_cost)*100:.0f}%")
            
            with col6:
                st.metric("Total Items", f"{sum(quantities)}")
            
            # Timeline analysis
            st.subheader("⏱️ Project Timeline Analysis")
            
            # Extract installation hours and lead times
            installation_data = []
            for category, items in boq_data.items():
                if isinstance(items, list):
                    for item in items:
                        installation_data.append({
                            'Category': category.replace('_', ' ').title(),
                            'Item': item.get('name', 'Unknown'),
                            'Installation Hours': item.get('installation_hours', 0),
                            'Lead Time (weeks)': item.get('lead_time_weeks', 0),
                            'Quantity': item.get('quantity', 1)
                        })
            
            if installation_data:
                timeline_df = pd.DataFrame(installation_data)
                
                col7, col8 = st.columns(2)
                
                with col7:
                    category_hours = timeline_df.groupby('Category')['Installation Hours'].sum().reset_index()
                    fig_hours = px.bar(
                        category_hours,
                        x='Category',
                        y='Installation Hours',
                        title='Installation Time by Category'
                    )
                    fig_hours.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_hours, use_container_width=True)
                
                with col8:
                    max_lead_time = timeline_df.groupby('Category')['Lead Time (weeks)'].max().reset_index()
                    fig_lead = px.bar(
                        max_lead_time,
                        x='Category',
                        y='Lead Time (weeks)',
                        title='Maximum Lead Time by Category'
                    )
                    fig_lead.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_lead, use_container_width=True)
                
                # Project timeline summary
                total_install_hours = timeline_df['Installation Hours'].sum()
                max_lead_time_weeks = timeline_df['Lead Time (weeks)'].max()
                
                st.info(f"""
                **Project Timeline Summary:**
                - Maximum Lead Time: {max_lead_time_weeks} weeks
                - Total Installation Hours: {total_install_hours} hours
                - Estimated Installation Days: {int(total_install_hours / 8) + 1} days
                - Recommended Project Duration: {max_lead_time_weeks + 2} weeks
                """)
        
        else:
            st.info("👈 Please generate a system design first to view analytics.")

def create_excel_export(boq_data, project_info):
    """Create Excel export of BOQ data"""
    output = BytesIO()
    
    # Create workbook
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = []
        total_cost = 0
        
        for category, items in boq_data.items():
            if isinstance(items, list):
                category_cost = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
                summary_data.append({
                    'Category': category.replace('_', ' ').title(),
                    'Items': len(items),
                    'Total Cost': category_cost
                })
                total_cost += category_cost
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Detailed sheets for each category
        for category, items in boq_data.items():
            if isinstance(items, list) and items:
                detailed_data = []
                for item in items:
                    detailed_data.append({
                        'Category': item.get('category', category),
                        'Name': item.get('name', ''),
                        'Brand': item.get('brand', ''),
                        'Model': item.get('model', ''),
                        'Part Number': item.get('part_number', ''),
                        'Specifications': item.get('specifications', ''),
                        'Quantity': item.get('quantity', 1),
                        'Unit Price': item.get('price', 0),
                        'Total Price': item.get('price', 0) * item.get('quantity', 1),
                        'Installation Hours': item.get('installation_hours', 0),
                        'Warranty (Years)': item.get('warranty_years', 0),
                        'Lead Time (Weeks)': item.get('lead_time_weeks', 0),
                        'Notes': item.get('notes', '')
                    })
                
                if detailed_data:
                    detail_df = pd.DataFrame(detailed_data)
                    sheet_name = category.replace('_', ' ').title()[:31]  # Excel sheet name limit
                    detail_df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    return output.getvalue()

def create_csv_export(boq_data):
    """Create CSV export of BOQ data"""
    csv_data = []
    
    for category, items in boq_data.items():
        if isinstance(items, list):
            for item in items:
                csv_data.append({
                    'Category': item.get('category', category),
                    'Name': item.get('name', ''),
                    'Brand': item.get('brand', ''),
                    'Model': item.get('model', ''),
                    'Part Number': item.get('part_number', ''),
                    'Specifications': item.get('specifications', ''),
                    'Quantity': item.get('quantity', 1),
                    'Unit Price': item.get('price', 0),
                    'Total Price': item.get('price', 0) * item.get('quantity', 1),
                    'Installation Hours': item.get('installation_hours', 0),
                    'Warranty Years': item.get('warranty_years', 0),
                    'Lead Time Weeks': item.get('lead_time_weeks', 0),
                    'Notes': item.get('notes', '')
                })
    
    if csv_data:
        df = pd.DataFrame(csv_data)
        return df.to_csv(index=False)
    
    return ""

if __name__ == "__main__":
    main()
