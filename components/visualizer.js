# components/visualizer.py

import streamlit as st
import streamlit.components.v1 as components
import re
import json

# --- Enhanced Room Specifications Database (Also needed by the visualizer) ---
ROOM_SPECS = {
    "Small Huddle Room (2-3 People)": {
        "area_sqft": (40, 80),
        "recommended_display_size": (32, 43),
        "viewing_distance_ft": (4, 6),
        "audio_coverage": "Near-field single speaker",
        "camera_type": "Fixed wide-angle",
        "power_requirements": "Standard 15A circuit",
        "network_ports": 1,
        "typical_budget_range": (3000, 8000),
        "furniture_config": "small_huddle",
        "table_size": [4, 2.5],
        "chair_count": 3,
        "chair_arrangement": "casual"
    },
    "Medium Huddle Room (4-6 People)": {
        "area_sqft": (80, 150),
        "recommended_display_size": (43, 55),
        "viewing_distance_ft": (6, 10),
        "audio_coverage": "Near-field stereo",
        "camera_type": "Fixed wide-angle with auto-framing",
        "power_requirements": "Standard 15A circuit",
        "network_ports": 2,
        "typical_budget_range": (8000, 18000),
        "furniture_config": "medium_huddle",
        "table_size": [6, 3],
        "chair_count": 6,
        "chair_arrangement": "round_table"
    },
    "Standard Conference Room (6-8 People)": {
        "area_sqft": (150, 250),
        "recommended_display_size": (55, 65),
        "viewing_distance_ft": (8, 12),
        "audio_coverage": "Room-wide with ceiling mics",
        "camera_type": "PTZ or wide-angle with tracking",
        "power_requirements": "20A dedicated circuit recommended",
        "network_ports": 2,
        "typical_budget_range": (15000, 30000),
        "furniture_config": "standard_conference",
        "table_size": [10, 4],
        "chair_count": 8,
        "chair_arrangement": "rectangular"
    },
    "Large Conference Room (8-12 People)": {
        "area_sqft": (300, 450),
        "recommended_display_size": (65, 75),
        "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed ceiling mics with expansion",
        "camera_type": "PTZ with presenter tracking",
        "power_requirements": "20A dedicated circuit",
        "network_ports": 3,
        "typical_budget_range": (25000, 50000),
        "furniture_config": "large_conference",
        "table_size": [16, 5],
        "chair_count": 12,
        "chair_arrangement": "rectangular"
    },
    "Executive Boardroom (10-16 People)": {
        "area_sqft": (400, 700),
        "recommended_display_size": (75, 86),
        "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling and table mics",
        "camera_type": "Multiple cameras with auto-switching",
        "power_requirements": "30A dedicated circuit",
        "network_ports": 4,
        "typical_budget_range": (50000, 100000),
        "furniture_config": "executive_boardroom",
        "table_size": [20, 6],
        "chair_count": 16,
        "chair_arrangement": "oval"
    },
    "Training Room (15-25 People)": {
        "area_sqft": (500, 800),
        "recommended_display_size": (65, 86),
        "viewing_distance_ft": (10, 18),
        "audio_coverage": "Distributed with wireless mic support",
        "camera_type": "Fixed or PTZ for presenter tracking",
        "power_requirements": "20A circuit with UPS backup",
        "network_ports": 3,
        "typical_budget_range": (30000, 70000),
        "furniture_config": "training_room",
        "table_size": [10, 4],
        "chair_count": 25,
        "chair_arrangement": "classroom"
    },
    "Large Training/Presentation Room (25-40 People)": {
        "area_sqft": (800, 1200),
        "recommended_display_size": (86, 98),
        "viewing_distance_ft": (15, 25),
        "audio_coverage": "Full distributed system with handheld mics",
        "camera_type": "Multiple PTZ cameras",
        "power_requirements": "30A circuit with UPS backup",
        "network_ports": 4,
        "typical_budget_range": (60000, 120000),
        "furniture_config": "large_training",
        "table_size": [12, 4],
        "chair_count": 40,
        "chair_arrangement": "theater"
    },
    "Multipurpose Event Room (40+ People)": {
        "area_sqft": (1200, 2000),
        "recommended_display_size": (98, 110),
        "viewing_distance_ft": (20, 35),
        "audio_coverage": "Professional distributed PA system",
        "camera_type": "Professional multi-camera setup",
        "power_requirements": "Multiple 30A circuits",
        "network_ports": 6,
        "typical_budget_range": (100000, 250000),
        "furniture_config": "multipurpose_event",
        "table_size": [16, 6],
        "chair_count": 50,
        "chair_arrangement": "flexible"
    },
    "Video Production Studio": {
        "area_sqft": (400, 600),
        "recommended_display_size": (32, 55),
        "viewing_distance_ft": (6, 12),
        "audio_coverage": "Professional studio monitors",
        "camera_type": "Professional broadcast cameras",
        "power_requirements": "Multiple 20A circuits",
        "network_ports": 4,
        "typical_budget_range": (75000, 200000),
        "furniture_config": "production_studio",
        "table_size": [12, 5],
        "chair_count": 6,
        "chair_arrangement": "production"
    },
    "Telepresence Suite": {
        "area_sqft": (350, 500),
        "recommended_display_size": (65, 98),
        "viewing_distance_ft": (8, 14),
        "audio_coverage": "High-fidelity spatial audio",
        "camera_type": "Multiple high-res cameras with AI tracking",
        "power_requirements": "20A dedicated circuit",
        "network_ports": 3,
        "typical_budget_range": (80000, 180000),
        "furniture_config": "telepresence",
        "table_size": [14, 4],
        "chair_count": 8,
        "chair_arrangement": "telepresence"
    }
}


# --- 3D Visualization Helper Functions ---
def map_equipment_type(category, name, brand):
    """Maps a BOQ item to a standardized equipment type for 3D rendering."""
    cat_lower = str(category).lower()
    name_lower = str(name).lower()
    
    if 'display' in cat_lower or 'monitor' in name_lower or 'screen' in name_lower:
        return 'display'
    if 'camera' in cat_lower or 'rally' in name_lower or 'conferencing' in cat_lower:
        return 'camera'
    if 'speaker' in name_lower or 'soundbar' in name_lower:
        return 'audio_speaker'
    if 'microphone' in name_lower or 'mic' in name_lower:
        return 'audio_mic'
    if 'switch' in name_lower or 'router' in name_lower:
        return 'network_switch'
    if 'control' in cat_lower or 'processor' in name_lower:
        return 'control_processor'
    if 'mount' in cat_lower or 'bracket' in name_lower:
        return 'mount'
    if 'rack' in name_lower:
        return 'rack'
    if 'service' in cat_lower or 'installation' in name_lower or 'warranty' in name_lower:
        return 'service' # Special type to be skipped
    return 'generic_box' # Fallback for unknown items

def get_equipment_specs(equipment_type, name):
    """Returns estimated [width, height, depth] in feet for 3D models."""
    name_lower = str(name).lower()
    
    # Check for specific size in name (e.g., 65")
    # Robust regex to handle variations like "65 inch", "65-inch", "65\""
    size_match = re.search(r'(\d{2,3})[ -]*(?:inch|\")', name_lower)
    if size_match and equipment_type == 'display':
        try:
            size_inches = int(size_match.group(1))
            # Aspect ratio 16:9 conversion to feet
            width = size_inches * 0.871 / 12 
            height = size_inches * 0.490 / 12
            return [width, height, 0.3] # W, H, D in feet
        except (ValueError, IndexError):
            # If conversion fails for any reason, fall through to default size
            pass

    # Default sizes in feet
    specs = {
        'display': [4.0, 2.3, 0.3],
        'camera': [0.8, 0.5, 0.6],
        'audio_speaker': [0.8, 1.2, 0.8],
        'audio_mic': [0.5, 0.1, 0.5],
        'network_switch': [1.5, 0.15, 0.8],
        'control_processor': [1.5, 0.3, 1.0],
        'mount': [2.0, 1.5, 0.2],
        'rack': [2.0, 6.0, 2.5],
        'generic_box': [1.0, 1.0, 1.0]
    }
    return specs.get(equipment_type, [1, 1, 1])

def get_placement_constraints(equipment_type):
    """Defines where an object can be placed."""
    constraints = {
        'display': ['wall'],
        'camera': ['wall', 'ceiling', 'table'],
        'audio_speaker': ['wall', 'ceiling', 'floor'],
        'audio_mic': ['table', 'ceiling'],
        'network_switch': ['floor', 'rack'],
        'control_processor': ['floor', 'rack'],
        'mount': ['wall'],
        'rack': ['floor']
    }
    return constraints.get(equipment_type, ['floor', 'table'])

def get_power_requirements(equipment_type):
    """Estimates power draw in Watts."""
    power = {
        'display': 250,
        'camera': 15,
        'audio_speaker': 80,
        'network_switch': 100,
        'control_processor': 50
    }
    return power.get(equipment_type, 20)

def get_weight_estimate(equipment_type, specs):
    """Estimates weight in lbs based on volume."""
    volume = specs[0] * specs[1] * specs[2]
    density = { # lbs per cubic foot
        'display': 20,
        'camera': 15,
        'audio_speaker': 25,
        'network_switch': 30,
        'control_processor': 25,
        'rack': 10
    }
    return volume * density.get(equipment_type, 10)

# --- 3D Visualization Main Function ---
def create_3d_visualization():
    """Create production-ready 3D room planner with drag-drop and space analytics."""
    st.subheader("Interactive 3D Room Planner & Space Analytics")

    equipment_data = st.session_state.get('boq_items', [])

    if not equipment_data:
        st.info("No BOQ items to visualize. Generate a BOQ first or add items manually.")
        return

    js_equipment = []
    for item in equipment_data:
        equipment_type = map_equipment_type(item.get('category', ''), item.get('name', ''), item.get('brand', ''))
        # Skip service items properly
        if equipment_type == 'service':
            continue

        specs = get_equipment_specs(equipment_type, item.get('name', ''))

        try:
            quantity = int(item.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        # Create individual instances for each quantity
        for i in range(quantity):
            js_equipment.append({
                'id': len(js_equipment) + 1,
                'type': equipment_type,
                'name': item.get('name', 'Unknown'),
                'brand': item.get('brand', 'Unknown'),
                'price': float(item.get('price', 0)),
                'instance': i + 1,
                'original_quantity': quantity,
                'specs': specs,
                'placement_constraints': get_placement_constraints(equipment_type),
                'power_requirements': get_power_requirements(equipment_type),
                'weight': get_weight_estimate(equipment_type, specs)
            })

    room_length = st.session_state.get('room_length_input', 24.0)
    room_width = st.session_state.get('room_width_input', 16.0)
    room_height = st.session_state.get('ceiling_height_input', 9.0)
    room_type_str = st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)')

    # The HTML and JavaScript to be rendered in the browser.
    # It reads Python variables via f-strings.
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            body {{
                margin: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #1a1a1a;
            }}
            #container {{
                width: 100%;
                height: 700px;
                position: relative;
                cursor: grab;
            }}
            #container:active {{
                cursor: grabbing;
            }}
            #analytics-panel {{
                position: absolute;
                top: 15px;
                right: 15px;
                color: #ffffff;
                background: linear-gradient(135deg, rgba(0, 30, 60, 0.95), rgba(0, 20, 40, 0.9));
                padding: 20px;
                border-radius: 15px;
                backdrop-filter: blur(15px);
                border: 2px solid rgba(64, 196, 255, 0.3);
                width: 350px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            #equipment-panel {{
                position: absolute;
                top: 15px;
                left: 15px;
                color: #ffffff;
                background: linear-gradient(135deg, rgba(30, 0, 60, 0.95), rgba(20, 0, 40, 0.9));
                padding: 20px;
                border-radius: 15px;
                backdrop-filter: blur(15px);
                border: 2px solid rgba(196, 64, 255, 0.3);
                width: 320px;
                max-height: 670px;
                overflow-y: auto;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }}
            .space-metric {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 8px 0;
                padding: 10px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                border-left: 4px solid #40C4FF;
            }}
            .space-value {{
                font-size: 16px;
                font-weight: bold;
                color: #40C4FF;
            }}
            .space-warning {{
                border-left-color: #FF6B35 !important;
            }}
            .space-warning .space-value {{
                color: #FF6B35;
            }}
            .equipment-item {{
                margin: 6px 0;
                padding: 12px;
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.03));
                border-radius: 8px;
                border-left: 3px solid transparent;
                cursor: grab;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            .equipment-item:hover {{
                background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.08));
                transform: translateY(-2px);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            }}
            .equipment-item:active {{
                cursor: grabbing;
            }}
            .equipment-item.placed {{
                border-left-color: #4CAF50;
                opacity: 0.7;
            }}
            .equipment-item.dragging {{
                transform: scale(1.05);
                z-index: 1000;
            }}
            .equipment-name {{
                color: #FFD54F;
                font-weight: bold;
                font-size: 14px;
            }}
            .equipment-details {{
                color: #ccc;
                font-size: 12px;
                margin-top: 4px;
            }}
            .equipment-specs {{
                color: #aaa;
                font-size: 11px;
                margin-top: 6px;
            }}
            #suggestions-panel {{
                position: absolute;
                bottom: 20px;
                right: 20px;
                background: linear-gradient(135deg, rgba(0, 60, 30, 0.95), rgba(0, 40, 20, 0.9));
                padding: 15px;
                border-radius: 12px;
                backdrop-filter: blur(10px);
                border: 2px solid rgba(76, 255, 76, 0.3);
                max-width: 300px;
                color: white;
                display: none;
            }}
            .suggestion-item {{
                padding: 8px;
                margin: 4px 0;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            .suggestion-item:hover {{
                background: rgba(76, 255, 76, 0.2);
            }}
            #controls {{
                position: absolute;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: linear-gradient(135deg, rgba(0, 0, 0, 0.9), rgba(20, 20, 20, 0.8));
                padding: 15px;
                border-radius: 25px;
                display: flex;
                gap: 12px;
                backdrop-filter: blur(15px);
                border: 2px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            }}
            .control-btn {{
                background: linear-gradient(135deg, rgba(64, 196, 255, 0.8), rgba(32, 164, 223, 0.6));
                border: 2px solid rgba(64, 196, 255, 0.4);
                color: white;
                padding: 10px 18px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 13px;
                font-weight: 500;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
            }}
            .control-btn:hover {{
                background: linear-gradient(135deg, rgba(64, 196, 255, 1), rgba(32, 164, 223, 0.8));
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(64, 196, 255, 0.4);
            }}
            .control-btn.active {{
                background: linear-gradient(135deg, #40C4FF, #0288D1);
                border-color: #0288D1;
                box-shadow: 0 4px 15px rgba(64, 196, 255, 0.6);
            }}
            .mode-indicator {{
                position: absolute;
                top: 20px;
                right: 50%;
                transform: translateX(50%);
                background: rgba(0, 0, 0, 0.8);
                color: #40C4FF;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: bold;
                font-size: 14px;
                border: 2px solid rgba(64, 196, 255, 0.5);
            }}
            .drag-overlay {{
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(64, 196, 255, 0.1);
                border: 3px dashed #40C4FF;
                border-radius: 15px;
                display: none;
                pointer-events: none;
                animation: pulse 2s infinite;
            }}
            @keyframes pulse {{
                0%, 100% {{
                    opacity: 0.3;
                }}
                50% {{
                    opacity: 0.7;
                }}
            }}
        </style>
    </head>
    <body>
        <div id="container">
            <div class="mode-indicator" id="modeIndicator">VIEW MODE</div>
            <div class="drag-overlay" id="dragOverlay"></div>
            
            <div id="analytics-panel">
                <h3 style="margin-top: 0; color: #40C4FF; font-size: 18px;">Space Analytics</h3>
                <div class="space-metric">
                    <span>Total Room Area</span>
                    <span class="space-value" id="totalArea">{room_length * room_width:.0f} sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Usable Floor Space</span>
                    <span class="space-value" id="usableArea">0 sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Equipment Footprint</span>
                    <span class="space-value" id="equipmentFootprint">0 sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Wall Space Used</span>
                    <span class="space-value" id="wallSpaceUsed">0%</span>
                </div>
                <div class="space-metric">
                    <span>Remaining Floor Space</span>
                    <span class="space-value" id="remainingSpace">{room_length * room_width:.0f} sq ft</span>
                </div>
                <div class="space-metric">
                    <span>Power Load</span>
                    <span class="space-value" id="powerLoad">0W</span>
                </div>
                <div class="space-metric">
                    <span>Cable Runs Required</span>
                    <span class="space-value" id="cableRuns">0</span>
                </div>
                
                <div id="spaceRecommendations" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2);">
                    <h4 style="color: #40C4FF; margin: 0 0 10px 0;">Recommendations</h4>
                    <div id="recommendationsList" style="font-size: 12px; line-height: 1.4;"></div>
                </div>
            </div>
            
            <div id="equipment-panel">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: #C440FF; font-size: 18px;">Equipment Library</h3>
                    <button class="control-btn" onclick="togglePlacementMode()" id="placementToggle">
                        PLACE MODE
                    </button>
                </div>
                <div style="font-size: 12px; color: #ccc; margin-bottom: 15px;" id="placementInstructions">
                    Click "PLACE MODE" then drag items into the room
                </div>
                <div id="equipmentList"></div>
            </div>

            <div id="suggestions-panel">
                <h4 style="margin: 0 0 10px 0; color: #4CFF4C;">Suggested Additions</h4>
                <div id="suggestionsList"></div>
            </div>
            
            <div id="controls">
                <button class="control-btn active" onclick="setView('overview', true, this)">🏠 Overview</button>
                <button class="control-btn" onclick="setView('front', true, this)">📺 Front</button>
                <button class="control-btn" onclick="setView('side', true, this)">📐 Side</button>
                <button class="control-btn" onclick="setView('top', true, this)">📊 Top</button>
                <button class="control-btn" onclick="resetLayout()">🔄 Reset</button>
                <button class="control-btn" onclick="saveLayout()">💾 Save</button>
            </div>
        </div>
        
        <script>
            let scene, camera, renderer, raycaster, mouse, dragControls;
            let animationId, selectedObject = null, placementMode = false;
            let draggedEquipment = null, originalPosition = null;
            let roomBounds, spaceAnalytics;
            
            const toUnits = (feet) => feet * 0.3048;
            const toFeet = (units) => units / 0.3048;
            const avEquipment = {json.dumps(js_equipment)};
            const roomType = `{room_type_str}`;
            const allRoomSpecs = {json.dumps(ROOM_SPECS)};
            const roomDims = {{
                length: {room_length},
                width: {room_width},
                height: {room_height}
            }};

            // Enhanced space analytics system
            class SpaceAnalytics {{
                constructor() {{
                    this.placedEquipment = [];
                    this.roomBounds = {{
                        minX: -toUnits(roomDims.length / 2),
                        maxX: toUnits(roomDims.length / 2),
                        minZ: -toUnits(roomDims.width / 2),
                        maxZ: toUnits(roomDims.width / 2),
                        height: toUnits(roomDims.height)
                    }};
                    this.walls = this.calculateWalls();
                }}
                
                calculateWalls() {{
                    return {{
                        front: {{ start: {{ x: this.roomBounds.minX, z: this.roomBounds.maxZ }}, end: {{ x: this.roomBounds.maxX, z: this.roomBounds.maxZ }}, length: roomDims.length }},
                        back: {{ start: {{ x: this.roomBounds.minX, z: this.roomBounds.minZ }}, end: {{ x: this.roomBounds.maxX, z: this.roomBounds.minZ }}, length: roomDims.length }},
                        left: {{ start: {{ x: this.roomBounds.minX, z: this.roomBounds.minZ }}, end: {{ x: this.roomBounds.minX, z: this.roomBounds.maxZ }}, length: roomDims.width }},
                        right: {{ start: {{ x: this.roomBounds.maxX, z: this.roomBounds.minZ }}, end: {{ x: this.roomBounds.maxX, z: this.roomBounds.maxZ }}, length: roomDims.width }}
                    }};
                }}
                
                addPlacedEquipment(obj, equipment) {{
                    const bbox = new THREE.Box3().setFromObject(obj);
                    const size = bbox.getSize(new THREE.Vector3());
                    const position = obj.position.clone();
                    
                    this.placedEquipment.push({{
                        object: obj,
                        equipment: equipment,
                        footprint: toFeet(size.x) * toFeet(size.z),
                        position: position,
                        bounds: bbox,
                        powerDraw: equipment.power_requirements || 0,
                        isWallMounted: this.isWallMounted(obj, equipment)
                    }});
                    
                    this.updateAnalytics();
                }}
                
                removePlacedEquipment(obj) {{
                    this.placedEquipment = this.placedEquipment.filter(item => item.object !== obj);
                    this.updateAnalytics();
                }}
                
                isWallMounted(obj, equipment) {{
                    const tolerance = toUnits(1); // 1 foot tolerance
                    const pos = obj.position;
                    
                    return (
                        Math.abs(pos.z - this.roomBounds.minZ) < tolerance || // Back wall
                        Math.abs(pos.z - this.roomBounds.maxZ) < tolerance || // Front wall
                        Math.abs(pos.x - this.roomBounds.minX) < tolerance || // Left wall
                        Math.abs(pos.x - this.roomBounds.maxX) < tolerance    // Right wall
                    );
                }}
                
                getWallSpaceUsed() {{
                    let totalUsed = 0;
                    const wallMountedItems = this.placedEquipment.filter(item => item.isWallMounted);
                    
                    Object.values(this.walls).forEach(wall => {{
                        let wallUsed = 0;
                        wallMountedItems.forEach(item => {{
                            const bbox = item.bounds;
                            const size = bbox.getSize(new THREE.Vector3());
                            
                            // Simplified wall space calculation
                            if (this.isOnWall(item.position, wall)) {{
                                wallUsed += toFeet(Math.max(size.x, size.z));
                            }}
                        }});
                        totalUsed += Math.min(wallUsed / wall.length, 1);
                    }});
                    
                    return (totalUsed / 4) * 100; // Average across 4 walls
                }}
                
                isOnWall(position, wall) {{
                    const tolerance = toUnits(1);
                    
                    if (wall === this.walls.front || wall === this.walls.back) {{
                        return Math.abs(position.z - wall.start.z) < tolerance;
                    }} else {{
                        return Math.abs(position.x - wall.start.x) < tolerance;
                    }}
                }}
                
                updateAnalytics() {{
                    const totalRoomArea = roomDims.length * roomDims.width;
                    const furnitureArea = this.calculateFurnitureFootprint();
                    const equipmentFootprint = this.placedEquipment.reduce((sum, item) => sum + item.footprint, 0);
                    const usableArea = totalRoomArea - furnitureArea;
                    const remainingSpace = Math.max(0, usableArea - equipmentFootprint);
                    const wallSpaceUsed = this.getWallSpaceUsed();
                    const totalPowerDraw = this.placedEquipment.reduce((sum, item) => sum + item.powerDraw, 0);
                    const cableRuns = this.calculateCableRuns();
                    
                    // Update UI with proper formatting
                    document.getElementById('usableArea').textContent = `${{usableArea.toFixed(0)}} sq ft`;
                    document.getElementById('equipmentFootprint').textContent = `${{equipmentFootprint.toFixed(1)}} sq ft`;
                    document.getElementById('remainingSpace').textContent = `${{remainingSpace.toFixed(1)}} sq ft`;
                    document.getElementById('wallSpaceUsed').textContent = `${{wallSpaceUsed.toFixed(1)}}%`;
                    document.getElementById('powerLoad').textContent = `${{totalPowerDraw}}W`;
                    document.getElementById('cableRuns').textContent = cableRuns;
                    
                    // Visual warnings
                    const remainingMetric = document.getElementById('remainingSpace').parentElement;
                    if (remainingSpace < totalRoomArea * 0.2) {{
                        remainingMetric.classList.add('space-warning');
                    }} else {{
                        remainingMetric.classList.remove('space-warning');
                    }}
                    
                    this.generateRecommendations(remainingSpace, wallSpaceUsed);
                }}
                
                calculateFurnitureFootprint() {{
                    // Estimate furniture footprint based on room type
                    const roomSpec = allRoomSpecs[roomType] || {{ table_size: [10, 4], chair_count: 8 }};
                    const tableArea = roomSpec.table_size[0] * roomSpec.table_size[1];
                    const chairArea = roomSpec.chair_count * 4; // 2ft x 2ft per chair
                    return tableArea + chairArea;
                }}
                
                calculateCableRuns() {{
                    // Estimate cable runs needed
                    const displays = this.placedEquipment.filter(item => item.equipment.type === 'display');
                    const audioDevices = this.placedEquipment.filter(item => item.equipment.type.includes('audio'));
                    const networkDevices = this.placedEquipment.filter(item => item.equipment.type.includes('network'));
                    
                    return displays.length * 3 + audioDevices.length * 2 + networkDevices.length;
                }}
                
                generateRecommendations(remainingSpace, wallSpaceUsed) {{
                    const recommendations = [];
                    
                    if (remainingSpace < 50) {{
                        recommendations.push("⚠️ Very limited floor space remaining");
                    }}
                    if (wallSpaceUsed > 80) {{
                        recommendations.push("⚠️ Wall space nearly fully utilized");
                    }}
                    if (remainingSpace > 200) {{
                        recommendations.push("✅ Ample space for additional equipment");
                    }}
                    
                    const totalPowerDraw = this.placedEquipment.reduce((sum, item) => sum + item.powerDraw, 0);
                    if (totalPowerDraw > 1500) {{
                        recommendations.push("⚡ May require dedicated 20A circuit");
                    }}
                    
                    document.getElementById('recommendationsList').innerHTML =
                        recommendations.length > 0 ? recommendations.join('<br>') : "All metrics within normal ranges";
                }}
                
                generateSuggestions(remainingSpace) {{
                    const suggestions = [];
                    const suggestionsPanel = document.getElementById('suggestions-panel');
                    
                    if (remainingSpace > 100) {{
                        suggestions.push({{ name: "Additional Display", space: 25, reason: "Dual display setup" }});
                        suggestions.push({{ name: "Wireless Presenter", space: 5, reason: "Enhanced mobility" }});
                    }}
                    if (remainingSpace > 50) {{
                        suggestions.push({{ name: "Document Camera", space: 8, reason: "Content sharing" }});
                        suggestions.push({{ name: "Room Control Panel", space: 3, reason: "User interface" }});
                    }}
                    
                    if (suggestions.length > 0) {{
                        const suggestionsList = document.getElementById('suggestionsList');
                        suggestionsList.innerHTML = suggestions.map(s =>
                            `<div class="suggestion-item">
                                <strong>${{s.name}}</strong><br>
                                <small>${{s.reason}} • ${{s.space}} sq ft</small>
                            </div>`
                        ).join('');
                        suggestionsPanel.style.display = 'block';
                    }} else {{
                        suggestionsPanel.style.display = 'none';
                    }}
                }}
            }}

            function init() {{
                scene = new THREE.Scene();
                scene.background = new THREE.Color(0x2a3a4a);
                scene.fog = new THREE.Fog(0x2a3a4a, toUnits(30), toUnits(120));
                
                const container = document.getElementById('container');
                camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
                setView('overview', false);
                
                renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                renderer.shadowMap.enabled = true;
                renderer.shadowMap.type = THREE.PCFSoftShadowMap;
                renderer.outputEncoding = THREE.sRGBEncoding;
                renderer.toneMapping = THREE.ACESFilmicToneMapping;
                renderer.toneMappingExposure = 1.2;
                container.appendChild(renderer.domElement);
                
                raycaster = new THREE.Raycaster();
                mouse = new THREE.Vector2();
                
                spaceAnalytics = new SpaceAnalytics();
                
                createRealisticRoom();
                createEnhancedLighting();
                createRoomFurniture();
                createPlaceableEquipmentObjects();
                setupEnhancedControls();
                setupKeyboardControls();
                updateEquipmentList();
                animate();
            }}

            function createRealisticRoom() {{
                const floorMaterial = new THREE.MeshStandardMaterial({{
                    color: 0x8B7355,
                    roughness: 0.8,
                    metalness: 0.1,
                    normalScale: new THREE.Vector2(0.5, 0.5)
                }});
                
                const wallMaterial = new THREE.MeshStandardMaterial({{
                    color: 0xF5F5F5,
                    roughness: 0.9,
                    metalness: 0.05
                }});
                
                const ceilingMaterial = new THREE.MeshStandardMaterial({{
                    color: 0xFFFFFF,
                    roughness: 0.95
                }});
                
                const wallHeight = toUnits(roomDims.height);

                const floor = new THREE.Mesh(
                    new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)),
                    floorMaterial
                );
                floor.rotation.x = -Math.PI / 2;
                floor.receiveShadow = true;
                floor.name = 'floor';
                scene.add(floor);

                const walls = [
                    {{ pos: [0, wallHeight / 2, -toUnits(roomDims.width / 2)], rot: [0, 0, 0], size: [toUnits(roomDims.length), wallHeight] }}, // Back
                    {{ pos: [-toUnits(roomDims.length / 2), wallHeight / 2, 0], rot: [0, Math.PI / 2, 0], size: [toUnits(roomDims.width), wallHeight] }}, // Left
                    {{ pos: [toUnits(roomDims.length / 2), wallHeight / 2, 0], rot: [0, -Math.PI / 2, 0], size: [toUnits(roomDims.width), wallHeight] }}, // Right
                    {{ pos: [0, wallHeight / 2, toUnits(roomDims.width / 2)], rot: [0, Math.PI, 0], size: [toUnits(roomDims.length), wallHeight] }} // Front
                ];

                walls.forEach((wallConfig, index) => {{
                    const wall = new THREE.Mesh(
                        new THREE.PlaneGeometry(wallConfig.size[0], wallConfig.size[1]),
                        wallMaterial
                    );
                    wall.position.set(...wallConfig.pos);
                    wall.rotation.set(...wallConfig.rot);
                    wall.receiveShadow = true;
                    wall.name = `wall_${{index}}`;
                    scene.add(wall);
                }});

                const ceiling = new THREE.Mesh(
                    new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)),
                    ceilingMaterial
                );
                ceiling.position.y = wallHeight;
                ceiling.rotation.x = Math.PI / 2;
                ceiling.receiveShadow = true;
                ceiling.name = 'ceiling';
                scene.add(ceiling);
            }}

            function createEnhancedLighting() {{
                const ambientLight = new THREE.HemisphereLight(0x87CEEB, 0x8B7355, 0.6);
                scene.add(ambientLight);

                const dirLight = new THREE.DirectionalLight(0xFFF8DC, 0.8);
                dirLight.position.set(toUnits(10), toUnits(15), toUnits(8));
                dirLight.castShadow = true;
                dirLight.shadow.mapSize.width = 2048;
                dirLight.shadow.mapSize.height = 2048;
                dirLight.shadow.camera.near = 0.5;
                dirLight.shadow.camera.far = 50;
                dirLight.shadow.camera.left = dirLight.shadow.camera.bottom = -25;
                dirLight.shadow.camera.right = dirLight.shadow.camera.top = 25;
                scene.add(dirLight);

                const roomLights = [
                    new THREE.Vector3(-toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), -toUnits(roomDims.width / 4)),
                    new THREE.Vector3(toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), -toUnits(roomDims.width / 4)),
                    new THREE.Vector3(-toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), toUnits(roomDims.width / 4)),
                    new THREE.Vector3(toUnits(roomDims.length / 4), toUnits(roomDims.height - 0.5), toUnits(roomDims.width / 4))
                ];

                roomLights.forEach(pos => {{
                    const light = new THREE.PointLight(0xFFFFE0, 0.4, toUnits(20));
                    light.position.copy(pos);
                    light.castShadow = true;
                    light.shadow.mapSize.width = 512;
                    light.shadow.mapSize.height = 512;
                    scene.add(light);
                    
                    const fixture = new THREE.Mesh(
                        new THREE.CylinderGeometry(toUnits(0.5), toUnits(0.5), toUnits(0.2)),
                        new THREE.MeshStandardMaterial({{ color: 0x888888 }})
                    );
                    fixture.position.copy(pos);
                    scene.add(fixture);
                }});
            }}
            
            function createRoomFurniture() {{
                const roomSpec = allRoomSpecs[roomType] || {{ chair_count: 8 }};
                
                let tableConfig = getTableConfig(roomType, roomSpec);
                
                const tableMaterial = new THREE.MeshStandardMaterial({{
                    color: 0x8B4513,
                    roughness: 0.3,
                    metalness: 0.1
                }});
                
                const table = new THREE.Mesh(
                    new THREE.BoxGeometry(
                        toUnits(tableConfig.length),
                        toUnits(tableConfig.height),
                        toUnits(tableConfig.width)
                    ),
                    tableMaterial
                );
                table.position.set(tableConfig.x, toUnits(tableConfig.height / 2), tableConfig.z);
                table.castShadow = true;
                table.receiveShadow = true;
                table.name = 'conference_table';
                scene.add(table);

                addRoomSpecificFurniture(roomType, roomSpec);
                
                const chairPositions = calculateChairPositions(roomSpec, tableConfig);
                createChairs(chairPositions);
            }}

            function getTableConfig(roomType, roomSpec) {{
                const tableSize = roomSpec.table_size || [10, 4];
                const configs = {{
                    'Small Huddle Room (2-3 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Medium Huddle Room (4-6 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Standard Conference Room (6-8 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Large Conference Room (8-12 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Executive Boardroom (10-16 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0
                    }},
                    'Training Room (15-25 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, 
                        x: -toUnits(roomDims.length/2 - tableSize[0]/2 - 3), z: -toUnits(roomDims.width/4)
                    }},
                    'Large Training/Presentation Room (25-40 People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, 
                        x: -toUnits(roomDims.length/2 - tableSize[0]/2 - 4), z: -toUnits(roomDims.width/3)
                    }},
                    'Multipurpose Event Room (40+ People)': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, 
                        x: -toUnits(roomDims.length/2 - tableSize[0]/2 - 5), z: -toUnits(roomDims.width/3)
                    }},
                    'Video Production Studio': {{
                        length: tableSize[0], width: tableSize[1], height: 3, 
                        x: toUnits(roomDims.length/2 - tableSize[0]/2 - 2), z: 0
                    }},
                    'Telepresence Suite': {{
                        length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: toUnits(2)
                    }}
                }};
                
                return configs[roomType] || {{ length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0 }};
            }}
            
            function addRoomSpecificFurniture(roomType, roomSpec) {{
                const furnitureMaterial = new THREE.MeshStandardMaterial({{ color: 0x666666 }});
                const woodMaterial = new THREE.MeshStandardMaterial({{ color: 0x8B4513 }});
                
                if (roomType.includes('Training')) {{
                    // Add student desks for training rooms with better spacing
                    const numRows = roomType.includes('Large') ? 6 : 4;
                    const seatsPerRow = Math.ceil(roomSpec.chair_count / numRows);
                    
                    for (let row = 0; row < numRows; row++) {{
                        for (let seat = 0; seat < seatsPerRow && (row * seatsPerRow + seat) < roomSpec.chair_count - 1; seat++) {{
                            const desk = new THREE.Mesh(
                                new THREE.BoxGeometry(toUnits(4), toUnits(2.5), toUnits(2)),
                                woodMaterial
                            );
                            desk.position.set(
                                toUnits(-roomDims.length/2 + 8 + seat * 6),
                                toUnits(1.25),
                                toUnits(roomDims.width/2 - 6 - row * 5)
                            );
                            desk.castShadow = true;
                            desk.receiveShadow = true;
                            scene.add(desk);
                        }}
                    }}
                }} else if (roomType.includes('Production Studio')) {{
                    // Add control console and equipment racks
                    const console = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(12), toUnits(3), toUnits(3)),
                        furnitureMaterial
                    );
                    console.position.set(toUnits(roomDims.length/2 - 8), toUnits(1.5), 0);
                    console.castShadow = true;
                    console.receiveShadow = true;
                    scene.add(console);
                    
                    // Equipment racks
                    for (let i = 0; i < 3; i++) {{
                        const rack = new THREE.Mesh(
                            new THREE.BoxGeometry(toUnits(2), toUnits(6), toUnits(2)),
                            new THREE.MeshStandardMaterial({{ color: 0x333333 }})
                        );
                        rack.position.set(
                            toUnits(roomDims.length/2 - 6),
                            toUnits(3),
                            toUnits(-4 + i * 4)
                        );
                        rack.castShadow = true;
                        rack.receiveShadow = true;
                        scene.add(rack);
                    }}
                }} else if (roomType.includes('Multipurpose Event')) {{
                    // Add stage area
                    const stage = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(16), toUnits(1), toUnits(8)),
                        woodMaterial
                    );
                    stage.position.set(
                        toUnits(-roomDims.length/2 + 8),
                        toUnits(0.5),
                        0
                    );
                    stage.castShadow = true;
                    stage.receiveShadow = true;
                    scene.add(stage);
                }} else if (roomType.includes('Executive Boardroom')) {{
                    // Add credenza
                    const credenza = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(8), toUnits(3), toUnits(2)),
                        woodMaterial
                    );
                    credenza.position.set(
                        0,
                        toUnits(1.5),
                        toUnits(-roomDims.width/2 + 1)
                    );
                    credenza.castShadow = true;
                    credenza.receiveShadow = true;
                    scene.add(credenza);
                }}
            }}

            function createChairs(chairPositions) {{
                 const chairMaterial = new THREE.MeshStandardMaterial({{
                    color: 0x333333,
                    roughness: 0.7
                }});
                
                chairPositions.forEach((pos, index) => {{
                    const chair = new THREE.Group();
                    
                    const seat = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(1.5), toUnits(0.3), toUnits(1.5)),
                        chairMaterial
                    );
                    seat.position.y = toUnits(1.5);
                    chair.add(seat);
                    
                    const backrest = new THREE.Mesh(
                        new THREE.BoxGeometry(toUnits(1.5), toUnits(2), toUnits(0.2)),
                        chairMaterial
                    );
                    backrest.position.set(0, toUnits(2.5), toUnits(-0.65));
                    chair.add(backrest);
                    
                    chair.position.set(toUnits(pos.x), 0, toUnits(pos.z));
                    chair.rotation.y = pos.rotationY || 0;
                    chair.castShadow = true;
                    chair.receiveShadow = true;
                    chair.name = `chair_${{index}}`;
                    scene.add(chair);
                }});
            }}

            function calculateChairPositions(roomSpec, tableConfig) {{
                const positions = [];
                const tableLength = tableConfig.length;
                const tableWidth = tableConfig.width;
                
                if (roomSpec.chair_arrangement === 'theater' || roomSpec.chair_arrangement === 'classroom') {{
                    // Theater/classroom seating for training rooms
                    const numRows = Math.ceil(roomSpec.chair_count / 8);
                    const chairsPerRow = Math.min(8, roomSpec.chair_count);
                    
                    for (let row = 0; row < numRows; row++) {{
                        for (let seat = 0; seat < chairsPerRow && positions.length < roomSpec.chair_count; seat++) {{
                            positions.push({{
                                x: -chairsPerRow * 2 + seat * 4,
                                z: tableWidth/2 + 4 + row * 4,
                                rotationY: 0
                            }});
                        }}
                    }}
                }} else {{
                    // Traditional conference table seating
                    const chairSpacing = Math.max(3, Math.min(4.5, tableLength / (roomSpec.chair_count / 2 + 1)));
                    const chairsPerLongSide = Math.floor((tableLength - 2) / chairSpacing);
                    
                    // Long sides of table
                    for (let i = 0; i < chairsPerLongSide && positions.length < roomSpec.chair_count; i++) {{
                        const x = -tableLength / 2 + (i + 1) * (tableLength / (chairsPerLongSide + 1));
                        
                        positions.push({{ x: x, z: tableWidth / 2 + 2, rotationY: Math.PI }});
                        if (positions.length < roomSpec.chair_count) {{
                            positions.push({{ x: x, z: -tableWidth / 2 - 2, rotationY: 0 }});
                        }}
                    }}
                    
                    // Short sides of table
                    if (positions.length < roomSpec.chair_count && tableWidth > 6) {{
                        positions.push({{ x: tableLength / 2 + 2, z: 0, rotationY: -Math.PI / 2 }});
                        if (positions.length < roomSpec.chair_count) {{
                            positions.push({{ x: -tableLength / 2 - 2, z: 0, rotationY: Math.PI / 2 }});
                        }}
                    }}
                }}
                
                return positions.slice(0, roomSpec.chair_count);
            }}

            function createPlaceableEquipmentObjects() {{
                avEquipment.forEach(equipment => {{
                    const obj = createEquipmentMesh(equipment);
                    obj.userData = {{ equipment: equipment, placed: false, draggable: true }};
                    obj.visible = false;
                    scene.add(obj);
                }});
            }}
            
            function createEquipmentMesh(equipment) {{
                const group = new THREE.Group();
                const specs = equipment.specs;
                const type = equipment.type;
                let geometry, material, mesh;

                // Create realistic materials
                const materials = {{
                    metal: new THREE.MeshStandardMaterial({{
                        color: 0x606060,
                        roughness: 0.2,
                        metalness: 0.9,
                        envMapIntensity: 1.0
                    }}),
                    plastic: new THREE.MeshStandardMaterial({{
                        color: 0x2a2a2a,
                        roughness: 0.7,
                        metalness: 0.1
                    }}),
                    screen: new THREE.MeshStandardMaterial({{
                        color: 0x000000,
                        emissive: 0x001122,
                        emissiveIntensity: 0.2,
                        roughness: 0.1,
                        metalness: 0.1
                    }}),
                    speaker: new THREE.MeshStandardMaterial({{
                        color: 0x1a1a1a,
                        roughness: 0.8,
                        metalness: 0.2
                    }})
                }};

                switch (type) {{
                    case 'display':
                        const displayWidth = toUnits(specs[0]);
                        const displayHeight = toUnits(specs[1]);
                        const displayDepth = toUnits(specs[2]);

                        geometry = new THREE.BoxGeometry(displayWidth, displayHeight, displayDepth);
                        mesh = new THREE.Mesh(geometry, materials.metal);

                        const screen = new THREE.Mesh(
                            new THREE.PlaneGeometry(displayWidth * 0.92, displayHeight * 0.92),
                            materials.screen
                        );
                        screen.position.z = displayDepth / 2 + 0.005;
                        group.add(screen);

                        const logo = new THREE.Mesh(
                            new THREE.PlaneGeometry(displayWidth * 0.15, displayHeight * 0.05),
                            new THREE.MeshStandardMaterial({{ color: 0x666666 }})
                        );
                        logo.position.set(0, -displayHeight * 0.45, displayDepth / 2 + 0.01);
                        group.add(logo);

                        const powerLED = new THREE.Mesh(
                            new THREE.SphereGeometry(toUnits(0.02)),
                            new THREE.MeshStandardMaterial({{ 
                                color: 0x00ff00, 
                                emissive: 0x003300, 
                                emissiveIntensity: 0.5 
                            }})
                        );
                        powerLED.position.set(displayWidth * 0.4, -displayHeight * 0.45, displayDepth / 2 + 0.01);
                        group.add(powerLED);
                        break;

                    case 'audio_speaker':
                        geometry = new THREE.BoxGeometry(toUnits(specs[0]), toUnits(specs[1]), toUnits(specs[2]));
                        mesh = new THREE.Mesh(geometry, materials.speaker);

                        const driverSizes = [0.4, 0.25, 0.15];
                        const driverPositions = [-0.3, 0, 0.3];
                        
                        driverSizes.forEach((size, i) => {{
                            const driver = new THREE.Mesh(
                                new THREE.CylinderGeometry(toUnits(specs[0] * size), toUnits(specs[0] * size), toUnits(0.02), 16),
                                new THREE.MeshStandardMaterial({{ color: 0x333333, roughness: 0.9 }})
                            );
                            driver.rotation.x = Math.PI / 2;
                            driver.position.set(0, toUnits(specs[1] * driverPositions[i]), toUnits(specs[2] / 2 + 0.01));
                            group.add(driver);

                            const cone = new THREE.Mesh(
                                new THREE.ConeGeometry(toUnits(specs[0] * size * 0.6), toUnits(0.05), 12),
                                new THREE.MeshStandardMaterial({{ color: 0x444444 }})
                            );
                            cone.rotation.x = Math.PI;
                            cone.position.set(0, toUnits(specs[1] * driverPositions[i]), toUnits(specs[2] / 2 + 0.03));
                            group.add(cone);
                        }});

                        const grille = new THREE.Mesh(
                            new THREE.PlaneGeometry(toUnits(specs[0] * 0.9), toUnits(specs[1] * 0.9)),
                            new THREE.MeshStandardMaterial({{ 
                                color: 0x222222, 
                                transparent: true, 
                                opacity: 0.3,
                                wireframe: true 
                            }})
                        );
                        grille.position.z = toUnits(specs[2] / 2 + 0.04);
                        group.add(grille);
                        break;

                    case 'camera':
                        geometry = new THREE.BoxGeometry(toUnits(specs[0]), toUnits(specs[1]), toUnits(specs[2]));
                        mesh = new THREE.Mesh(geometry, materials.plastic);

                        const lensAssembly = new THREE.Group();
                        
                        const outerRing = new THREE.Mesh(
                            new THREE.CylinderGeometry(toUnits(0.3), toUnits(0.35), toUnits(0.15), 20),
                            materials.metal
                        );
                        outerRing.rotation.x = Math.PI / 2;
                        lensAssembly.add(outerRing);

                        const lensGlass = new THREE.Mesh(
                            new THREE.CylinderGeometry(toUnits(0.25), toUnits(0.25), toUnits(0.02), 20),
                            new THREE.MeshStandardMaterial({{ 
                                color: 0x001122, 
                                roughness: 0.05, 
                                metalness: 0.9,
                                transparent: true,
                                opacity: 0.8
                            }})
                        );
                        lensGlass.rotation.x = Math.PI / 2;
                        lensGlass.position.z = toUnits(0.05);
                        lensAssembly.add(lensGlass);

                        lensAssembly.position.z = toUnits(specs[2] / 2 + 0.1);
                        group.add(lensAssembly);

                        const ledColors = [0x00ff00, 0xff0000, 0x0000ff];
                        ledColors.forEach((color, i) => {{
                            const led = new THREE.Mesh(
                                new THREE.SphereGeometry(toUnits(0.02)),
                                new THREE.MeshStandardMaterial({{ 
                                    color: color, 
                                    emissive: color, 
                                    emissiveIntensity: 0.3 
                                }})
                            );
                            led.position.set(
                                toUnits(specs[0] * 0.3 - i * 0.15), 
                                toUnits(specs[1] * 0.4), 
                                toUnits(specs[2] / 2 + 0.01)
                            );
                            group.add(led);
                        }});
                        break;

                    case 'network_switch':
                        geometry = new THREE.BoxGeometry(toUnits(specs[0]), toUnits(specs[1]), toUnits(specs[2]));
                        mesh = new THREE.Mesh(geometry, materials.metal);

                        for (let i = 0; i < 4; i++) {{
                            const vent = new THREE.Mesh(
                                new THREE.PlaneGeometry(toUnits(0.8), toUnits(0.05)),
                                new THREE.MeshStandardMaterial({{ color: 0x222222 }})
                            );
                            vent.position.set(0, toUnits(specs[1] / 2 - 0.02), toUnits(-specs[2] / 2 + i * 0.3));
                            vent.rotation.x = -Math.PI / 2;
                            group.add(vent);
                        }}

                        const portRows = 2;
                        const portsPerRow = 12;
                        for (let row = 0; row < portRows; row++) {{
                            for (let port = 0; port < portsPerRow; port++) {{
                                const portGeometry = new THREE.BoxGeometry(toUnits(0.06), toUnits(0.03), toUnits(0.08));
                                const portMesh = new THREE.Mesh(portGeometry, new THREE.MeshStandardMaterial({{ color: 0x111111 }}));
                                
                                portMesh.position.set(
                                    toUnits(-specs[0] / 2 + 0.1 + port * (specs[0] - 0.2) / portsPerRow),
                                    toUnits(-specs[1] / 2 + 0.04 + row * 0.05),
                                    toUnits(specs[2] / 2 + 0.04)
                                );
                                group.add(portMesh);

                                if (Math.random() > 0.3) {{ // 70% chance of activity
                                    const activityLED = new THREE.Mesh(
                                        new THREE.SphereGeometry(toUnits(0.005)),
                                        new THREE.MeshStandardMaterial({{ 
                                            color: Math.random() > 0.5 ? 0x00ff00 : 0xff8800,
                                            emissive: Math.random() > 0.5 ? 0x002200 : 0x221100,
                                            emissiveIntensity: 0.5
                                        }})
                                    );
                                    activityLED.position.copy(portMesh.position);
                                    activityLED.position.z += toUnits(0.05);
                                    activityLED.position.y += toUnits(0.02);
                                    group.add(activityLED);
                                }}
                            }}
                        }}
                        break;

                    default:
                        geometry = new THREE.BoxGeometry(toUnits(specs[0] || 2), toUnits(specs[1] || 1), toUnits(specs[2] || 1));
                        mesh = new THREE.Mesh(geometry, materials.plastic);

                        const genericDetails = [
                            {{ pos: [0.3, 0.3, 0.5], color: 0x0066ff }},
                            {{ pos: [-0.3, 0.3, 0.5], color: 0xff6600 }},
                            {{ pos: [0, -0.3, 0.5], color: 0x00ff66 }}
                        ];

                        genericDetails.forEach(detail => {{
                            const indicator = new THREE.Mesh(
                                new THREE.SphereGeometry(toUnits(0.03)),
                                new THREE.MeshStandardMaterial({{ 
                                    color: detail.color,
                                    emissive: detail.color,
                                    emissiveIntensity: 0.2
                                }})
                            );
                            indicator.position.set(
                                toUnits((specs[0] || 2) * detail.pos[0]), 
                                toUnits((specs[1] || 1) * detail.pos[1]), 
                                toUnits((specs[2] || 1) * detail.pos[2])
                            );
                            group.add(indicator);
                        }});
                }}

                if (mesh) {{
                    mesh.castShadow = true;
                    mesh.receiveShadow = true;
                    group.add(mesh);
                }}

                const highlightGeometry = new THREE.BoxGeometry(
                    toUnits(specs[0] + 0.3), 
                    toUnits(specs[1] + 0.3), 
                    toUnits(specs[2] + 0.3)
                );
                const highlightMaterial = new THREE.MeshBasicMaterial({{
                    color: 0x40C4FF,
                    transparent: true,
                    opacity: 0,
                    wireframe: true,
                    linewidth: 2
                }});
                const highlight = new THREE.Mesh(highlightGeometry, highlightMaterial);
                highlight.name = 'highlight';
                group.add(highlight);

                group.name = `equipment_${{equipment.id}}`;
                return group;
            }}
            
            function onContextMenu(event) {{
                event.preventDefault();

                const rect = event.target.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);

                const equipmentIntersect = intersects.find(intersect =>
                    intersect.object.parent && intersect.object.parent.name.startsWith('equipment_') &&
                    intersect.object.parent.userData.placed
                );

                if (equipmentIntersect) {{
                    const equipmentObj = equipmentIntersect.object.parent;
                    const equipment = equipmentObj.userData.equipment;

                    // Simple context actions
                    if (confirm(`Remove ${{equipment.name}} from layout?`)) {{
                        equipmentObj.visible = false;
                        equipmentObj.userData.placed = false;
                        spaceAnalytics.removePlacedEquipment(equipmentObj);
                        updateEquipmentList();
                    }}
                }}
            }}

            function setupEnhancedControls() {{
                const container = document.getElementById('container');
                
                let isMouseDown = false;
                let previousMousePosition = {{ x: 0, y: 0 }};
                
                container.addEventListener('mousedown', (event) => {{
                    if (event.button === 0 && !placementMode) {{ // Left click and not in placement mode
                        isMouseDown = true;
                        previousMousePosition = {{ x: event.clientX, y: event.clientY }};
                        container.style.cursor = 'grabbing';
                    }}
                }});
                
                container.addEventListener('mousemove', (event) => {{
                    if (isMouseDown && !placementMode) {{
                        const deltaMove = {{
                            x: event.clientX - previousMousePosition.x,
                            y: event.clientY - previousMousePosition.y
                        }};
                        
                        const spherical = new THREE.Spherical();
                        spherical.setFromVector3(camera.position);
                        
                        spherical.theta -= deltaMove.x * 0.01;
                        spherical.phi += deltaMove.y * 0.01;
                        spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi));
                        
                        camera.position.setFromSpherical(spherical);
                        camera.lookAt(0, toUnits(3), 0);
                        
                        previousMousePosition = {{ x: event.clientX, y: event.clientY }};
                    }} else {{
                        const rect = event.target.getBoundingClientRect();
                        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                        
                        if (placementMode && (draggedEquipment || selectedObject)) {{
                            updateDraggedEquipmentPosition();
                        }}
                    }}
                }});
                
                container.addEventListener('mouseup', (event) => {{
                    if (event.button === 0) {{
                        if (isMouseDown && !placementMode) {{
                            isMouseDown = false;
                            container.style.cursor = 'grab';
                        }}
                    }}
                    if (placementMode) {{
                         if (selectedObject) {{
                             selectedObject.userData.placed = true;
                             draggedEquipment = null;
                             spaceAnalytics.addPlacedEquipment(selectedObject, selectedObject.userData.equipment)
                             highlightEquipment(selectedObject, false);
                             selectedObject = null;
                             document.getElementById('modeIndicator').textContent = 'PLACE MODE';
                             updateEquipmentList();
                         }}
                    }}
                }});
                
                container.addEventListener('mousedown', onMouseDown);
                container.addEventListener('contextmenu', onContextMenu);
                container.addEventListener('dblclick', onDoubleClick);
                container.addEventListener('wheel', onMouseWheel);
                container.addEventListener('dragover', onDragOver);
                container.addEventListener('drop', onDrop);
            }}

            function onMouseDown(event) {{
                if (!placementMode) return;

                const rect = event.target.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);

                const equipmentIntersect = intersects.find(intersect =>
                    intersect.object.parent && intersect.object.parent.name.startsWith('equipment_') &&
                    intersect.object.parent.userData.placed
                );

                if (equipmentIntersect) {{
                    const equipmentObj = equipmentIntersect.object.parent;
                    selectedObject = equipmentObj;
                    equipmentObj.userData.placed = false;
                    spaceAnalytics.removePlacedEquipment(equipmentObj);
                    draggedEquipment = equipmentObj.userData.equipment;
                    highlightEquipment(equipmentObj, true);
                    document.getElementById('modeIndicator').textContent = `MOVING: ${{draggedEquipment.name}}`;
                    return;
                }}

                const validIntersect = intersects.find(intersect => 
                    intersect.object.name === 'floor' ||
                    intersect.object.name.startsWith('wall_') ||
                    intersect.object.name === 'ceiling'
                );
                
                if (validIntersect && draggedEquipment) {{
                    placeDraggedEquipment(validIntersect.point);
                }}
            }}
            
            function onDoubleClick(event) {{
                const rect = event.target.getBoundingClientRect();
                mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                
                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);
                
                const equipmentIntersect = intersects.find(intersect => 
                    intersect.object.parent && intersect.object.parent.name.startsWith('equipment_')
                );
                
                if (equipmentIntersect) {{
                    const equipmentObj = equipmentIntersect.object.parent;
                    focusOnEquipment(equipmentObj);
                }}
            }}

            function focusOnEquipment(equipmentObj) {{
                const bbox = new THREE.Box3().setFromObject(equipmentObj);
                const center = bbox.getCenter(new THREE.Vector3());
                const size = bbox.getSize(new THREE.Vector3());
                
                const maxDim = Math.max(size.x, size.y, size.z);
                const distance = maxDim * 4;
                
                const targetPosition = new THREE.Vector3(
                    center.x + distance * 0.7,
                    center.y + distance * 0.5,
                    center.z + distance * 0.7
                );
                
                const startPosition = camera.position.clone();
                const startTime = Date.now();
                const duration = 1500;
                
                function animateToEquipment() {{
                    const elapsed = Date.now() - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    
                    camera.position.lerpVectors(startPosition, targetPosition, eased);
                    camera.lookAt(center);
                    
                    if (progress < 1) {{
                        requestAnimationFrame(animateToEquipment);
                    }}
                }}
                
                animateToEquipment();
            }}

            function onMouseWheel(event) {{
                event.preventDefault();
                const zoomSpeed = 0.1;
                const zoomFactor = 1 + (event.deltaY > 0 ? zoomSpeed : -zoomSpeed);
                const distanceToTarget = camera.position.length();

                if (distanceToTarget * zoomFactor > toUnits(5) && distanceToTarget * zoomFactor < toUnits(100)) {{
                    camera.position.multiplyScalar(zoomFactor);
                }}
            }}
            
            function onDragOver(event) {{
                event.preventDefault();
                event.dataTransfer.dropEffect = "move";
                
                if (placementMode) {{
                    document.getElementById('dragOverlay').style.display = 'block';
                }}
            }}

            function onDrop(event) {{
                event.preventDefault();
                document.getElementById('dragOverlay').style.display = 'none';
                
                if (!placementMode) {{
                    alert('Please enable PLACE MODE first');
                    return;
                }}
                
                const equipmentId = event.dataTransfer.getData('text/plain');
                const equipment = avEquipment.find(eq => eq.id.toString() === equipmentId);
                
                if (equipment) {{
                    const rect = event.target.getBoundingClientRect();
                    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                    
                    raycaster.setFromCamera(mouse, camera);
                    const intersects = raycaster.intersectObjects(scene.children, true);
                    const floorIntersect = intersects.find(intersect => intersect.object.name === 'floor' || intersect.object.name.startsWith('wall'));
                    
                    if (floorIntersect) {{
                        startDragging(equipment);
                        placeDraggedEquipment(floorIntersect.point);
                    }}
                }}
            }}

            function updateEquipmentList() {{
                const listElement = document.getElementById('equipmentList');
                listElement.innerHTML = avEquipment.map(equipment => {{
                    const placed = scene.getObjectByName(`equipment_${{equipment.id}}`)?.userData.placed || false;
                    return `
                        <div class="equipment-item ${{placed ? 'placed' : ''}}" 
                                draggable="true" 
                                onclick="selectEquipment(${{equipment.id}})"
                                ondragstart="startDragFromPanel(event, ${{equipment.id}})">
                            <div class="equipment-name">${{equipment.name}}</div>
                            <div class="equipment-details">
                                ${{equipment.brand}} • $${{equipment.price.toLocaleString()}}
                                ${{equipment.instance > 1 ? ` (${{equipment.instance}}/${{equipment.original_quantity}})` : ''}}
                            </div>
                            <div class="equipment-specs">
                                ${{equipment.specs[0].toFixed(1)}}W × ${{equipment.specs[1].toFixed(1)}}H × ${{equipment.specs[2].toFixed(1)}}D ft
                                ${{equipment.power_requirements ? ` • ${{equipment.power_requirements}}W` : ''}}
                            </div>
                        </div>
                    `;
                }}).join('');
            }}

            function startDragFromPanel(event, equipmentId) {{
                event.dataTransfer.setData('text/plain', equipmentId.toString());
            }}

            function selectEquipment(equipmentId) {{
                if (!placementMode) return;
                
                const equipment = avEquipment.find(eq => eq.id === equipmentId);
                if (equipment) {{
                    startDragging(equipment);
                }}
            }}

            function startDragging(equipment) {{
                const obj = scene.getObjectByName(`equipment_${{equipment.id}}`);
                if (obj && obj.userData.placed) return;
                
                draggedEquipment = equipment;
                document.getElementById('modeIndicator').textContent = `PLACING: ${{equipment.name}}`;
            }}
            
            function highlightEquipment(equipmentObj, highlightStatus = true) {{
                const highlightMesh = equipmentObj.getObjectByName('highlight');
                if (highlightMesh) {{
                    if (highlightStatus) {{
                        highlightMesh.material.opacity = 0.3;
                    }} else {{
                        highlightMesh.material.opacity = 0;
                    }}
                }}
            }}
            
            function updateDraggedEquipmentPosition() {{
                const equipmentToMove = selectedObject ? selectedObject.userData.equipment : draggedEquipment;
                if (!equipmentToMove) return;

                raycaster.setFromCamera(mouse, camera);
                const intersects = raycaster.intersectObjects(scene.children, true);
                
                const validIntersect = intersects.find(intersect => 
                    intersect.object.name === 'floor' ||
                    intersect.object.name.startsWith('wall_') || 
                    intersect.object.name === 'ceiling'
                );

                if (validIntersect) {{
                    const obj = scene.getObjectByName(`equipment_${{equipmentToMove.id}}`);
                    if (obj) {{
                        const intersectPoint = validIntersect.point.clone();
                        const normal = validIntersect.face.normal.clone();
                        
                        const offset = normal.multiplyScalar(toUnits(Math.max(...equipmentToMove.specs) / 2 + 0.1));
                        obj.position.copy(intersectPoint.add(offset));
                        
                        const bounds = spaceAnalytics.roomBounds;
                        obj.position.x = Math.max(bounds.minX + toUnits(0.5), Math.min(bounds.maxX - toUnits(0.5), obj.position.x));
                        obj.position.z = Math.max(bounds.minZ + toUnits(0.5), Math.min(bounds.maxZ - toUnits(0.5), obj.position.z));
                        obj.position.y = Math.max(toUnits(0.1), Math.min(bounds.height - toUnits(0.1), obj.position.y));
                        
                        if (!selectedObject) highlightEquipment(obj, true);
                        
                        obj.visible = true;
                    }}
                }}
            }}

            function placeDraggedEquipment(position) {{
                if (!draggedEquipment) return;
                
                const obj = scene.getObjectByName(`equipment_${{draggedEquipment.id}}`);
                if (obj) {{
                    obj.visible = true;
                    obj.userData.placed = true;
                    
                    spaceAnalytics.addPlacedEquipment(obj, draggedEquipment);
                    updateEquipmentList();
                }}
                
                draggedEquipment = null;
                document.getElementById('modeIndicator').textContent = 'PLACE MODE';
            }}

            function togglePlacementMode() {{
                placementMode = !placementMode;
                const button = document.getElementById('placementToggle');
                const instructions = document.getElementById('placementInstructions');
                const indicator = document.getElementById('modeIndicator');
                
                if (placementMode) {{
                    button.textContent = 'VIEW MODE';
                    button.classList.add('active');
                    instructions.textContent = 'Drag items from library into the room';
                    indicator.textContent = 'PLACE MODE';
                }} else {{
                    button.textContent = 'PLACE MODE';
                    button.classList.remove('active');
                    instructions.textContent = 'Click "PLACE MODE" then drag items into the room';
                    indicator.textContent = 'VIEW MODE';
                    draggedEquipment = null;
                }}
            }}

            function setView(viewType, animate = true, buttonElement = null) {{
                if (buttonElement) {{
                    document.querySelectorAll('.control-btn').forEach(btn => btn.classList.remove('active'));
                    buttonElement.classList.add('active');
                }}
                
                const roomSize = Math.max(roomDims.length, roomDims.width);
                const baseDist = roomSize > 30 ? roomSize * 0.8 : roomSize * 0.6;
                
                let newPosition;
                
                switch (viewType) {{
                    case 'overview':
                        newPosition = new THREE.Vector3(
                            toUnits(baseDist * 0.7), 
                            toUnits(roomDims.height + baseDist * 0.4), 
                            toUnits(baseDist * 0.7)
                        );
                        break;
                    case 'front':
                        newPosition = new THREE.Vector3(0, toUnits(roomDims.height * 0.6), toUnits(roomDims.width / 2 + baseDist * 0.5));
                        break;
                    case 'side':
                        newPosition = new THREE.Vector3(toUnits(roomDims.length / 2 + baseDist * 0.5), toUnits(roomDims.height * 0.6), 0);
                        break;
                    case 'top':
                        newPosition = new THREE.Vector3(0, toUnits(roomDims.height + baseDist * 0.8), 0.1);
                        break;
                }}
                
                if (animate) {{
                    const startPosition = camera.position.clone();
                    const startTime = Date.now();
                    const duration = 1000;
                    
                    function animateCamera() {{
                        const elapsed = Date.now() - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const eased = 1 - Math.pow(1 - progress, 3);
                        
                        camera.position.lerpVectors(startPosition, newPosition, eased);
                        camera.lookAt(0, toUnits(roomDims.height * 0.3), 0);
                        
                        if (progress < 1) {{
                            requestAnimationFrame(animateCamera);
                        }}
                    }}
                    animateCamera();
                }} else {{
                    camera.position.copy(newPosition);
                    camera.lookAt(0, toUnits(roomDims.height * 0.3), 0);
                }}
            }}

            function resetLayout() {{
                scene.children.forEach(child => {{
                    if (child.name.startsWith('equipment_')) {{
                        child.visible = false;
                        child.userData.placed = false;
                    }}
                }});
                
                spaceAnalytics.placedEquipment = [];
                spaceAnalytics.updateAnalytics();
                updateEquipmentList();
            }}

            function saveLayout() {{
                const placedItems = [];
                scene.children.forEach(child => {{
                    if (child.name.startsWith('equipment_') && child.userData.placed) {{
                        placedItems.push({{
                            id: child.userData.equipment.id,
                            position: {{
                                x: child.position.x,
                                y: child.position.y,
                                z: child.position.z
                            }},
                            rotation: {{
                                x: child.rotation.x,
                                y: child.rotation.y,
                                z: child.rotation.z
                            }}
                        }});
                    }}
                }});
                
                const layoutData = {{
                    room: roomDims,
                    equipment: placedItems,
                    analytics: {{
                        footprint: spaceAnalytics.placedEquipment.reduce((sum, item) => sum + item.footprint, 0),
                        powerLoad: spaceAnalytics.placedEquipment.reduce((sum, item) => sum + item.powerDraw, 0)
                    }}
                }};
                
                console.log('Layout saved:', layoutData);
                alert('Layout saved successfully! (Check console)');
            }}
            
            function setupKeyboardControls() {{
                document.addEventListener('keydown', (event) => {{
                    switch(event.key.toLowerCase()) {{
                        case 'r':
                            resetLayout();
                            break;
                        case 'p':
                            togglePlacementMode();
                            break;
                        case '1':
                            setView('overview', true, document.querySelector('#controls button:nth-child(1)'));
                            break;
                        case '2':
                            setView('front', true, document.querySelector('#controls button:nth-child(2)'));
                            break;
                        case '3':
                            setView('side', true, document.querySelector('#controls button:nth-child(3)'));
                            break;
                        case '4':
                            setView('top', true, document.querySelector('#controls button:nth-child(4)'));
                            break;
                        case 'escape':
                            if (draggedEquipment) {{
                                draggedEquipment = null;
                                document.getElementById('modeIndicator').textContent = 'PLACE MODE';
                            }}
                            if (selectedObject) {{
                                highlightEquipment(selectedObject, false);
                                selectedObject = null;
                            }}
                            break;
                    }}
                }});
            }}

            function animate() {{
                animationId = requestAnimationFrame(animate);
                renderer.render(scene, camera);
            }}

            window.addEventListener('load', init);
            window.addEventListener('resize', () => {{
                const container = document.getElementById('container');
                camera.aspect = container.clientWidth / container.clientHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(container.clientWidth, container.clientHeight);
            }});
        </script>
    </body>
    </html>
    """

    components.html(html_content, height=700)
