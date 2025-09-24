import streamlit as st
import pandas as pd
import google.generativeai as genai
import re
from datetime import datetime, timedelta
import json
import time
import streamlit.components.v1 as components

# --- Page Configuration ---
st.set_page_config(
    page_title="Professional AV BOQ Generator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Base64 Encoded Textures for 3D Visualization ---
# To avoid needing external files, we embed small, tileable textures directly.
TEXTURES = {
    "wood": "data:image/jpeg;base64,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",
    "carpet": "data:image/jpeg;base64,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",
    "wall": "data:image/jpeg;base64,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"
}

# --- Enhanced Room Specifications Database ---
ROOM_SPECS = {
    "Small Huddle Room (2-3 People)": {
        "area_sqft": (40, 80), "recommended_display_size": (32, 43), "viewing_distance_ft": (4, 6),
        "audio_coverage": "Near-field single speaker", "camera_type": "Fixed wide-angle", "power_requirements": "Standard 15A circuit",
        "network_ports": 1, "typical_budget_range": (3000, 8000), "table_size": [4, 2.5], "chair_count": 3
    },
    "Medium Huddle Room (4-6 People)": {
        "area_sqft": (80, 150), "recommended_display_size": (43, 55), "viewing_distance_ft": (6, 10),
        "audio_coverage": "Near-field stereo", "camera_type": "Fixed wide-angle with auto-framing", "power_requirements": "Standard 15A circuit",
        "network_ports": 2, "typical_budget_range": (8000, 18000), "table_size": [6, 3], "chair_count": 6
    },
    "Standard Conference Room (6-8 People)": {
        "area_sqft": (150, 250), "recommended_display_size": (55, 65), "viewing_distance_ft": (8, 12),
        "audio_coverage": "Room-wide with ceiling mics", "camera_type": "PTZ or wide-angle with tracking", "power_requirements": "20A dedicated circuit recommended",
        "network_ports": 2, "typical_budget_range": (15000, 30000), "table_size": [10, 4], "chair_count": 8
    },
    "Large Conference Room (8-12 People)": {
        "area_sqft": (250, 400), "recommended_display_size": (65, 75), "viewing_distance_ft": (10, 16),
        "audio_coverage": "Distributed ceiling mics with expansion", "camera_type": "PTZ with presenter tracking", "power_requirements": "20A dedicated circuit",
        "network_ports": 3, "typical_budget_range": (25000, 50000), "table_size": [14, 5], "chair_count": 12
    },
    "Executive Boardroom (10-16 People)": {
        "area_sqft": (350, 600), "recommended_display_size": (75, 86), "viewing_distance_ft": (12, 20),
        "audio_coverage": "Distributed ceiling and table mics", "camera_type": "Multiple cameras with auto-switching", "power_requirements": "30A dedicated circuit",
        "network_ports": 4, "typical_budget_range": (50000, 100000), "table_size": [16, 6], "chair_count": 16
    },
    "Training Room (15-25 People)": {
        "area_sqft": (300, 500), "recommended_display_size": (65, 86), "viewing_distance_ft": (10, 18),
        "audio_coverage": "Distributed with wireless mic support", "camera_type": "Fixed or PTZ for presenter tracking", "power_requirements": "20A circuit with UPS backup",
        "network_ports": 3, "typical_budget_range": (30000, 70000), "table_size": [8, 4], "chair_count": 25
    },
    "Large Training/Presentation Room (25-40 People)": {
        "area_sqft": (500, 800), "recommended_display_size": (86, 98), "viewing_distance_ft": (15, 25),
        "audio_coverage": "Full distributed system with handheld mics", "camera_type": "Multiple PTZ cameras", "power_requirements": "30A circuit with UPS backup",
        "network_ports": 4, "typical_budget_range": (60000, 120000), "table_size": [10, 4], "chair_count": 40
    }
}

# --- Core Helper Functions ---

@st.cache_data(ttl=3600)
def get_usd_to_inr_rate():
    return 83.0

def convert_currency(amount_usd, to_currency="INR"):
    if to_currency == "INR":
        return amount_usd * get_usd_to_inr_rate()
    return amount_usd

def format_currency(amount, currency="USD"):
    if currency == "INR":
        return f"₹{amount:,.0f}"
    return f"${amount:,.2f}"

@st.cache_data
def load_and_validate_data():
    try:
        df = pd.read_csv("master_product_catalog.csv")
        validation_issues = []
        if df['name'].isnull().sum() > 0:
            validation_issues.append("Products missing names")
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        df['brand'] = df['brand'].fillna('Unknown')
        df['category'] = df['category'].fillna('General')
        df['features'] = df['features'].fillna('')
        try:
            with open("avixa_guidelines.md", "r", encoding="utf-8") as f:
                guidelines = f.read()
        except FileNotFoundError:
            guidelines = "AVIXA guidelines not found."
            validation_issues.append("AVIXA guidelines file missing")
        return df, guidelines, validation_issues
    except FileNotFoundError:
        return None, None, ["Product catalog file not found"]
    except Exception as e:
        return None, None, [f"Data loading error: {str(e)}"]

def setup_gemini():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Gemini API configuration failed: {e}")
        return None

def generate_with_retry(model, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return model.generate_content(prompt)
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(2 ** attempt)
    return None

# --- BOQ Processing and Validation ---

def extract_boq_items_from_response(boq_content, product_df):
    items = []
    lines = boq_content.split('\n')
    in_table = False
    for line in lines:
        line = line.strip()
        if '|' in line and any(k in line.lower() for k in ['category', 'product', 'brand']):
            in_table = True
            continue
        if in_table and line.startswith('|') and all(c in '|-: ' for c in line):
            continue
        if in_table and line.startswith('|') and 'TOTAL' not in line.upper():
            parts = [part.strip() for part in line.split('|') if part.strip()]
            if len(parts) >= 3:
                quantity = 1
                for part in parts:
                    if part.isdigit():
                        quantity = int(part)
                        break
                product_name = parts[2] if len(parts) > 2 else parts[1]
                brand = parts[1]
                matched = match_product_in_database(product_name, brand, product_df)
                items.append({
                    'category': matched.get('category', 'General') if matched else 'General',
                    'name': matched.get('name', product_name) if matched else product_name,
                    'brand': matched.get('brand', brand) if matched else brand,
                    'quantity': quantity,
                    'price': float(matched.get('price', 0)) if matched else 0,
                    'matched': matched is not None
                })
        elif in_table and not line.startswith('|'):
            in_table = False
    return items

def match_product_in_database(product_name, brand, product_df):
    if product_df is None: return None
    brand_matches = product_df[product_df['brand'].str.contains(brand, case=False, na=False)]
    if not brand_matches.empty:
        name_matches = brand_matches[brand_matches['name'].str.contains(product_name[:20], case=False, na=False)]
        if not name_matches.empty:
            return name_matches.iloc[0].to_dict()
    name_matches = product_df[product_df['name'].str.contains(product_name[:15], case=False, na=False)]
    if not name_matches.empty:
        return name_matches.iloc[0].to_dict()
    return None

# --- 3D Visualization Utilities ---

def map_equipment_type(category, product_name="", brand=""):
    """Improved mapping to categorize BOQ items for 3D visualization."""
    if not category or pd.isna(category): category = ""
    if not product_name or pd.isna(product_name): product_name = ""
    
    text = f"{str(category).lower()} {str(product_name).lower()}"
    
    if any(k in text for k in ['display', 'monitor', 'screen', 'tv', 'panel']): return 'display'
    if any(k in text for k in ['camera', 'rally bar', 'studio x']): return 'ptz_camera'
    if any(k in text for k in ['speaker', 'soundbar']): return 'audio_speaker'
    if any(k in text for k in ['switch', 'processor', 'control', 'extender']): return 'rack_equipment'
    if any(k in text for k in ['tap', 'scheduler', 'touch']): return 'touch_panel'
    if any(k in text for k in ['mic', 'microphone']): return 'audio_microphone'
    if any(k in text for k in ['mount', 'bracket']): return 'mount' # Non-visualized
    if any(k in text for k in ['cable', 'connector', 'kit']): return 'cable' # Non-visualized
    if any(k in text for k in ['service', 'installation', 'labor']): return 'service' # Non-visualized
    
    return 'generic_equipment'

def get_equipment_specs(equipment_type, product_name=""):
    """Provides default dimensions (in feet) for equipment types."""
    specs = {
        'display': [5, 3, 0.2], 'ptz_camera': [0.8, 0.8, 0.8],
        'audio_speaker': [3, 0.5, 0.4], 'rack_equipment': [1.58, 0.15, 1],
        'touch_panel': [0.8, 0.5, 0.1], 'audio_microphone': [0.4, 0.3, 0.4],
        'generic_equipment': [1, 1, 1]
    }
    base_specs = specs.get(equipment_type, [0, 0, 0])
    
    if equipment_type == 'display' and product_name:
        size_match = re.search(r'(\d+)"', product_name)
        if size_match:
            size_inches = int(size_match.group(1))
            width_ft = (size_inches * 0.87) / 12
            height_ft = (size_inches * 0.49) / 12
            return [width_ft, height_ft, 0.2]
    return base_specs

# --- UI Components ---

def create_project_header():
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("Professional AV BOQ Generator")
    with col2:
        project_id = st.text_input("Project ID", value=f"AVP-{datetime.now().strftime('%Y%m%d')}")
    with col3:
        quote_days = st.number_input("Quote Valid (Days)", 15, 90, 30)
    return project_id, quote_days

# ... Other UI functions like create_interactive_boq_editor, etc. can be added here if needed

# --- 3D VISUALIZATION FUNCTION (PHOTOREALISTIC OVERHAUL) ---
def create_3d_visualization():
    """Create an interactive, photorealistic 3D room visualization."""
    st.subheader("3D Room Visualization")
    
    equipment_data = st.session_state.get('boq_items', [])
    if not equipment_data:
        st.info("Generate or add items to the BOQ to visualize the room.")
        return

    # Process equipment for visualization, filtering out non-physical items
    js_equipment = []
    type_counts = {}
    visualizable_types = [
        'display', 'interactive_display', 'audio_speaker', 'video_conferencing',
        'ptz_camera', 'touch_panel', 'audio_microphone', 'rack_equipment',
        'av_network_switch', 'control_system', 'amplifier', 'audio_processor',
        'generic_equipment'
    ]
    
    total_boq_items = sum(int(item.get('quantity', 1)) for item in equipment_data)
    
    for item in equipment_data:
        equipment_type = map_equipment_type(item.get('category', ''), item.get('name', ''), item.get('brand', ''))
        
        if equipment_type not in visualizable_types:
            continue
            
        specs = get_equipment_specs(equipment_type, item.get('name', ''))
        quantity = int(item.get('quantity', 1))
            
        for _ in range(quantity):
            type_counts[equipment_type] = type_counts.get(equipment_type, 0) + 1
            js_equipment.append({
                'id': f"{item.get('name', 'item')}_{type_counts[equipment_type]}".replace(" ", "_"),
                'type': equipment_type, 'name': item.get('name', 'Unknown'),
                'brand': item.get('brand', 'Unknown'), 'price': float(item.get('price', 0)),
                'instance_index': type_counts[equipment_type] - 1, 'specs': specs
            })

    if not js_equipment:
        st.warning("No visualizable hardware found in the current BOQ.")
        return

    room_length = st.session_state.get('room_length_input', 24.0)
    room_width = st.session_state.get('room_width_input', 16.0)
    room_height = st.session_state.get('ceiling_height_input', 9.0)
    room_type_str = st.session_state.get('room_type_select', 'Standard Conference Room (6-8 People)')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AV Room Visualization</title>
        <script type="importmap">
        {{
            "imports": {{
                "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
                "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
            }}
        }}
        </script>
        <style>
            body {{ margin: 0; font-family: 'Segoe UI', sans-serif; }}
            #container {{ width: 100%; height: 650px; position: relative; cursor: grab; }}
            #container:active {{ cursor: grabbing; }}
            #info-panel {{ position: absolute; top: 15px; left: 15px; color: #fff; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 12px; backdrop-filter: blur(10px); width: 320px; display: flex; flex-direction: column; max-height: 620px; }}
            .equipment-manifest {{ flex-grow: 1; overflow-y: auto; margin-top: 10px; }}
            .equipment-item {{ margin: 4px 0; padding: 8px; background: rgba(255,255,255,0.05); border-radius: 4px; border-left: 3px solid transparent; cursor: pointer; transition: all 0.2s ease; }}
            .equipment-item:hover {{ background: rgba(255,255,255,0.15); }}
            .equipment-item.selected-item {{ background: rgba(79, 195, 247, 0.2); border-left: 3px solid #4FC3F7; }}
            .equipment-name {{ color: #FFD54F; font-weight: bold; font-size: 13px; }}
            #controls {{ position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); padding: 10px; border-radius: 25px; display: flex; gap: 10px; }}
            .control-btn {{ background: rgba(255,255,255,0.2); border: none; color: white; padding: 8px 16px; border-radius: 15px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div id="container">
            <div id="info-panel">
                 <div>
                    <h3 style="margin-top:0;color:#4FC3F7;">Equipment Manifest</h3>
                    <div style="font-size:12px;color:#ccc;">Visualizing {len(js_equipment)} of {total_boq_items} equipment instances</div>
                </div>
                <div class="equipment-manifest" id="equipmentList"></div>
            </div>
            <div id="controls">
                <button class="control-btn" onclick="setView('overview')">Overview</button>
                <button class="control-btn" onclick="setView('front')">Front</button>
            </div>
        </div>
        
        <script type="module">
            import * as THREE from 'three';
            import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
            import {{ RoomEnvironment }} from 'three/addons/environments/RoomEnvironment.js';
            import {{ EffectComposer }} from 'three/addons/postprocessing/EffectComposer.js';
            import {{ RenderPass }} from 'three/addons/postprocessing/RenderPass.js';
            import {{ SAOPass }} from 'three/addons/postprocessing/SAOPass.js';

            const avEquipment = {json.dumps(js_equipment)};
            const roomDims = {{ length: {room_length}, width: {room_width}, height: {room_height} }};
            const roomSpec = {json.dumps(ROOM_SPECS.get(room_type_str, {}))};
            const textures = {json.dumps(TEXTURES)};

            let scene, camera, renderer, composer, controls, raycaster, mouse, selectedObject = null;
            const toMeters = (feet) => feet * 0.3048;

            function init() {{
                const container = document.getElementById('container');
                renderer = new THREE.WebGLRenderer({{ antialias: true }});
                renderer.setSize(container.clientWidth, container.clientHeight);
                renderer.setPixelRatio(window.devicePixelRatio);
                renderer.shadowMap.enabled = true;
                renderer.toneMapping = THREE.ACESFilmicToneMapping;
                container.appendChild(renderer.domElement);

                scene = new THREE.Scene();
                const pmremGenerator = new THREE.PMREMGenerator(renderer);
                scene.environment = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture;
                
                camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 100);
                controls = new OrbitControls(camera, renderer.domElement);
                controls.target.set(0, toMeters(2.5), 0);
                controls.enableDamping = true;
                
                composer = new EffectComposer(renderer);
                composer.addPass(new RenderPass(scene, camera));
                const saoPass = new SAOPass(scene, camera, false, true);
                saoPass.params.saoIntensity = 0.02; saoPass.params.saoScale = 20; saoPass.params.saoKernelRadius = 25;
                composer.addPass(saoPass);

                raycaster = new THREE.Raycaster();
                mouse = new THREE.Vector2();

                createScene();
                updateEquipmentList();
                setView('overview');
                
                window.addEventListener('resize', () => {{
                    camera.aspect = container.clientWidth / container.clientHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(container.clientWidth, container.clientHeight);
                    composer.setSize(container.clientWidth, container.clientHeight);
                }});
                renderer.domElement.addEventListener('click', (event) => {{
                    const rect = renderer.domElement.getBoundingClientRect();
                    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
                    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
                    raycaster.setFromCamera(mouse, camera);
                    const intersects = raycaster.intersectObjects(scene.children, true);
                    if (intersects.length > 0) {{
                        let obj = intersects[0].object;
                        while(obj.parent && !obj.userData.id) {{ obj = obj.parent; }}
                        if(obj.userData.id) selectObject(obj);
                    }} else {{
                        selectObject(null);
                    }}
                }});
                
                animate();
            }}

            function createScene() {{
                const textureLoader = new THREE.TextureLoader();
                const woodTexture = textureLoader.load(textures.wood);
                woodTexture.wrapS = woodTexture.wrapT = THREE.RepeatWrapping;
                const carpetTexture = textureLoader.load(textures.carpet);
                carpetTexture.wrapS = carpetTexture.wrapT = THREE.RepeatWrapping;

                const floorMat = new THREE.MeshStandardMaterial({{ map: carpetTexture, roughness: 0.8 }});
                const wallMat = new THREE.MeshStandardMaterial({{ color: 0xe0e0e0, roughness: 0.9 }});
                const tableMat = new THREE.MeshStandardMaterial({{ map: woodTexture, roughness: 0.4 }});
                const legMat = new THREE.MeshStandardMaterial({{ color: 0x424242, roughness: 0.3 }});

                const roomL = toMeters(roomDims.length), roomW = toMeters(roomDims.width), wallH = toMeters(roomDims.height);
                carpetTexture.repeat.set(roomL, roomW);
                
                const floor = new THREE.Mesh(new THREE.PlaneGeometry(roomL, roomW), floorMat);
                floor.rotation.x = -Math.PI / 2;
                floor.receiveShadow = true;
                scene.add(floor);

                [[0, wallH/2, -roomW/2, 0, roomL], [-roomL/2, wallH/2, 0, Math.PI/2, roomW]].forEach(p => {{
                    const wall1 = new THREE.Mesh(new THREE.PlaneGeometry(p[4], wallH), wallMat);
                    wall1.position.set(p[0],p[1],p[2]); wall1.rotation.y = p[3]; wall1.receiveShadow = true; scene.add(wall1);
                    const wall2 = wall1.clone(); wall2.position.set(-p[0],p[1],-p[2]); wall2.rotation.y = p[3]+Math.PI; scene.add(wall2);
                }});

                const tableL = toMeters(roomSpec.table_size[0]), tableW = toMeters(roomSpec.table_size[1]);
                woodTexture.repeat.set(tableL/2, tableW/2);
                const table = new THREE.Mesh(new THREE.BoxGeometry(tableL, toMeters(0.2), tableW), tableMat);
                table.position.y = toMeters(2.5); table.castShadow = true; scene.add(table);

                avEquipment.forEach(item => scene.add(createEquipmentMesh(item)));
            }}

            function createEquipmentMesh(item) {{
                const group = new THREE.Group();
                const size = item.specs.map(dim => toMeters(dim));
                const blackPlasticMat = new THREE.MeshStandardMaterial({{ color: 0x111, roughness: 0.4 }});
                
                if (item.type.includes('display')) {{
                    const bezel = new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), blackPlasticMat);
                    const screen = new THREE.Mesh(new THREE.PlaneGeometry(size[0]*0.95, size[1]*0.95), new THREE.MeshStandardMaterial({{color:0x000, emissive: 0x080820}}));
                    screen.position.z = size[2]/2 + 0.001;
                    bezel.add(screen);
                    group.add(bezel);
                }} else if (item.type.includes('camera')) {{
                    group.add(new THREE.Mesh(new THREE.SphereGeometry(size[0]*0.4), blackPlasticMat));
                }} else if (item.type.includes('speaker')) {{
                    group.add(new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), new THREE.MeshStandardMaterial({{color: 0xeeeeee, roughness: 0.6}})));
                }} else {{
                    group.add(new THREE.Mesh(new THREE.BoxGeometry(toMeters(1.58), toMeters(0.15), toMeters(1)), new THREE.MeshStandardMaterial({{ color: 0x1a1a1a, metalness: 0.8 }})));
                }}

                const pos = getSmartPosition(item.type, item.instance_index);
                group.position.set(pos.x, pos.y, pos.z);
                
                group.traverse(obj => {{ obj.castShadow = true; }});
                group.userData = item;
                return group;
            }}

            function getSmartPosition(type, index) {{
                const wallZ = -toMeters(roomDims.width / 2) + 0.05;
                if (type.includes('display')) return {{ x: 0, y: toMeters(4.5), z: wallZ }};
                if (type.includes('camera')) return {{ x: 0, y: toMeters(6.5), z: wallZ }};
                if (type.includes('speaker')) return {{ x: (index % 2 === 0 ? 1:-1) * toMeters(roomDims.length / 4), y: toMeters(5), z: wallZ }};
                return {{ x: toMeters(roomDims.length / 2 - 1), y: toMeters(1 + index * 0.1), z: wallZ, rotation: Math.PI }};
            }}

            function selectObject(target) {{
                if (selectedObject) selectedObject.children[0].material.emissive.setHex(selectedObject.userData.originalEmissive || 0x000000);
                document.querySelectorAll('.equipment-item').forEach(li => li.classList.remove('selected-item'));
                selectedObject = target;
                if (!target) return;
                const item = target.userData;
                target.userData.originalEmissive = target.children[0].material.emissive.getHex();
                target.children[0].material.emissive.setHex(0x555555);
                const listItem = document.getElementById(`list-item-${{item.id.replace(" ", "_")}}`);
                if(listItem) listItem.classList.add('selected-item');
            }}
            
            function updateEquipmentList() {{
                const list = document.getElementById('equipmentList');
                list.innerHTML = '';
                avEquipment.forEach(item => {{
                    const div = document.createElement('div');
                    div.className = 'equipment-item';
                    div.id = `list-item-${{item.id.replace(" ", "_")}}`;
                    div.innerHTML = `<div class="equipment-name">${{item.name}}</div>`;
                    div.onclick = () => selectObject(scene.children.find(c => c.userData.id === item.id));
                    list.appendChild(div);
                }});
            }}

            window.setView = function(view) {{
                const targetY = toMeters(2.5);
                if (view === 'overview') camera.position.set(toMeters(roomDims.length*0.4), toMeters(roomDims.height*0.7), toMeters(roomDims.width*0.7));
                if (view === 'front') camera.position.set(0, targetY, toMeters(roomDims.width/2 + 5));
                controls.update();
            }}

            function animate() {{
                requestAnimationFrame(animate);
                controls.update();
                composer.render();
            }}

            init();
        </script>
    </body>
    </html>
    """
    st.components.v1.html(html_content, height=670, scrolling=False)

# --- Main Application Logic ---
def main():
    if 'boq_items' not in st.session_state: st.session_state.boq_items = []
    if 'boq_content' not in st.session_state: st.session_state.boq_content = None
    if 'validation_results' not in st.session_state: st.session_state.validation_results = None

    product_df, guidelines, data_issues = load_and_validate_data()
    if data_issues:
        with st.expander("⚠️ Data Quality Issues"):
            for issue in data_issues: st.warning(issue)
    if product_df is None:
        st.error("Cannot load product catalog. Please check `master_product_catalog.csv`."); return

    model = setup_gemini()
    if not model: return
    
    project_id, quote_valid_days = create_project_header()

    with st.sidebar:
        st.header("Project Configuration")
        st.text_input("Client Name")
        st.text_input("Project Name")
        currency = st.selectbox("Currency", ["USD", "INR"], index=1, key="currency_select")
        st.session_state['currency'] = currency
        st.markdown("---")
        room_type = st.selectbox("Primary Space Type:", list(ROOM_SPECS.keys()), key="room_type_select")
        budget_tier = st.select_slider("Budget Tier:", options=["Economy", "Standard", "Premium"], value="Standard")
        
        room_spec = ROOM_SPECS[room_type]
        st.markdown("### Room Guidelines")
        st.caption(f"Area: {room_spec['area_sqft'][0]}-{room_spec['area_sqft'][1]} sq ft")
        st.caption(f"Display: {room_spec['recommended_display_size'][0]}\"-{room_spec['recommended_display_size'][1]}\"")

    tabs = st.tabs(["Room & Requirements", "Generate & Edit BOQ", "3D Visualization"])

    with tabs[0]:
        st.subheader("Room Dimensions")
        c1, c2, c3 = st.columns(3)
        c1.number_input("Room Length (ft)", 8.0, 100.0, 24.0, key="room_length_input")
        c2.number_input("Room Width (ft)", 6.0, 100.0, 16.0, key="room_width_input")
        c3.number_input("Ceiling Height (ft)", 8.0, 30.0, 9.0, key="ceiling_height_input")
        st.text_area("Specific Requirements", "Dual 75 inch displays, ceiling microphones for 12 people, and a simple touch controller on the table for Zoom calls.", key="features_text_area")

    with tabs[1]:
        if st.button("Generate Professional BOQ", type="primary", use_container_width=True):
            with st.spinner("Engineering professional BOQ..."):
                prompt = f"""
                Create a Bill of Quantities for a '{room_type}' with a '{budget_tier}' budget.
                Requirements: {st.session_state.features_text_area}.
                Use ONLY products from this catalog:\n{product_df.head(100).to_csv()}
                Format the output as a markdown table with columns: Category, Brand, Product Name, Quantity.
                """
                response = generate_with_retry(model, prompt)
                if response:
                    st.session_state.boq_content = response.text
                    st.session_state.boq_items = extract_boq_items_from_response(response.text, product_df)
                    st.success(f"Generated BOQ with {len(st.session_state.boq_items)} items.")
                else:
                    st.error("Failed to generate BOQ.")
        
        if st.session_state.get('boq_items'):
            st.markdown("---")
            st.subheader("Bill of Quantities")
            df = pd.DataFrame(st.session_state.boq_items)
            st.dataframe(df[['category', 'brand', 'name', 'quantity', 'price']])
            
            total_cost = (df['price'] * df['quantity']).sum()
            st.metric("Hardware Subtotal (USD)", f"${total_cost:,.2f}")


    with tabs[2]:
        create_3d_visualization()

if __name__ == "__main__":
    main()
