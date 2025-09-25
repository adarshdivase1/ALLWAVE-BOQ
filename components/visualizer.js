/**
 * AllWave AV Solutions - 3D Room Visualizer
 * This script powers the interactive three.js room planner.
 * It receives its initial data from the `window.APP_DATA` object,
 * which is injected by the Streamlit Python backend.
 */

// --- DATA INITIALIZATION ---
// Access the data passed from the Streamlit Python script
const { avEquipment, roomType, allRoomSpecs, roomDims } = window.APP_DATA;

// --- GLOBAL VARIABLES ---
let scene, camera, renderer, raycaster, mouse;
let animationId, selectedObject = null, placementMode = false;
let draggedEquipment = null;
let spaceAnalytics;

// --- UTILITY FUNCTIONS ---
const toUnits = (feet) => feet * 0.3048;
const toFeet = (units) => units / 0.3048;

// --- ANALYTICS ENGINE ---
class SpaceAnalytics {
    constructor() {
        this.placedEquipment = [];
        this.roomBounds = {
            minX: -toUnits(roomDims.length / 2),
            maxX: toUnits(roomDims.length / 2),
            minZ: -toUnits(roomDims.width / 2),
            maxZ: toUnits(roomDims.width / 2),
            height: toUnits(roomDims.height)
        };
        this.walls = this.calculateWalls();
    }

    calculateWalls() {
        return {
            front: { start: { x: this.roomBounds.minX, z: this.roomBounds.maxZ }, end: { x: this.roomBounds.maxX, z: this.roomBounds.maxZ }, length: roomDims.length },
            back: { start: { x: this.roomBounds.minX, z: this.roomBounds.minZ }, end: { x: this.roomBounds.maxX, z: this.roomBounds.minZ }, length: roomDims.length },
            left: { start: { x: this.roomBounds.minX, z: this.roomBounds.minZ }, end: { x: this.roomBounds.minX, z: this.roomBounds.maxZ }, length: roomDims.width },
            right: { start: { x: this.roomBounds.maxX, z: this.roomBounds.minZ }, end: { x: this.roomBounds.maxX, z: this.roomBounds.maxZ }, length: roomDims.width }
        };
    }

    addPlacedEquipment(obj, equipment) {
        const bbox = new THREE.Box3().setFromObject(obj);
        const size = bbox.getSize(new THREE.Vector3());
        const position = obj.position.clone();

        this.placedEquipment.push({
            object: obj,
            equipment: equipment,
            footprint: toFeet(size.x) * toFeet(size.z),
            position: position,
            bounds: bbox,
            powerDraw: equipment.power_requirements || 0,
            isWallMounted: this.isWallMounted(obj)
        });

        this.updateAnalytics();
    }

    removePlacedEquipment(obj) {
        this.placedEquipment = this.placedEquipment.filter(item => item.object !== obj);
        this.updateAnalytics();
    }

    isWallMounted(obj) {
        const tolerance = toUnits(1); // 1 foot tolerance
        const pos = obj.position;

        return (
            Math.abs(pos.z - this.roomBounds.minZ) < tolerance || // Back wall
            Math.abs(pos.z - this.roomBounds.maxZ) < tolerance || // Front wall
            Math.abs(pos.x - this.roomBounds.minX) < tolerance || // Left wall
            Math.abs(pos.x - this.roomBounds.maxX) < tolerance    // Right wall
        );
    }

    getWallSpaceUsed() {
        let totalUsed = 0;
        const wallMountedItems = this.placedEquipment.filter(item => item.isWallMounted);

        Object.values(this.walls).forEach(wall => {
            let wallUsed = 0;
            wallMountedItems.forEach(item => {
                const bbox = item.bounds;
                const size = bbox.getSize(new THREE.Vector3());
                if (this.isOnWall(item.position, wall)) {
                    wallUsed += toFeet(Math.max(size.x, size.z));
                }
            });
            totalUsed += Math.min(wallUsed / wall.length, 1);
        });

        return (totalUsed / 4) * 100; // Average across 4 walls
    }

    isOnWall(position, wall) {
        const tolerance = toUnits(1);
        if (wall === this.walls.front || wall === this.walls.back) {
            return Math.abs(position.z - wall.start.z) < tolerance;
        } else {
            return Math.abs(position.x - wall.start.x) < tolerance;
        }
    }

    updateAnalytics() {
        const totalRoomArea = roomDims.length * roomDims.width;
        const furnitureArea = this.calculateFurnitureFootprint();
        const equipmentFootprint = this.placedEquipment.reduce((sum, item) => sum + item.footprint, 0);
        const usableArea = totalRoomArea - furnitureArea;
        const remainingSpace = Math.max(0, usableArea - equipmentFootprint);
        const wallSpaceUsed = this.getWallSpaceUsed();
        const totalPowerDraw = this.placedEquipment.reduce((sum, item) => sum + item.powerDraw, 0);
        const cableRuns = this.calculateCableRuns();

        // Update UI
        document.getElementById('usableArea').textContent = `${usableArea.toFixed(0)} sq ft`;
        document.getElementById('equipmentFootprint').textContent = `${equipmentFootprint.toFixed(1)} sq ft`;
        document.getElementById('remainingSpace').textContent = `${remainingSpace.toFixed(1)} sq ft`;
        document.getElementById('wallSpaceUsed').textContent = `${wallSpaceUsed.toFixed(1)}%`;
        document.getElementById('powerLoad').textContent = `${totalPowerDraw}W`;
        document.getElementById('cableRuns').textContent = cableRuns;

        // Visual warnings
        const remainingMetric = document.getElementById('remainingSpace').parentElement;
        if (remainingSpace < totalRoomArea * 0.2) {
            remainingMetric.classList.add('space-warning');
        } else {
            remainingMetric.classList.remove('space-warning');
        }

        this.generateRecommendations(remainingSpace, wallSpaceUsed, totalPowerDraw);
    }

    calculateFurnitureFootprint() {
        const roomSpec = allRoomSpecs[roomType] || { table_size: [10, 4], chair_count: 8 };
        const tableArea = roomSpec.table_size[0] * roomSpec.table_size[1];
        const chairArea = roomSpec.chair_count * 4; // 2ft x 2ft per chair
        return tableArea + chairArea;
    }

    calculateCableRuns() {
        const displays = this.placedEquipment.filter(item => item.equipment.type === 'display');
        const audioDevices = this.placedEquipment.filter(item => item.equipment.type.includes('audio'));
        const networkDevices = this.placedEquipment.filter(item => item.equipment.type.includes('network'));
        return displays.length * 3 + audioDevices.length * 2 + networkDevices.length;
    }

    generateRecommendations(remainingSpace, wallSpaceUsed, totalPowerDraw) {
        const recommendations = [];
        if (remainingSpace < 50) {
            recommendations.push("⚠️ Very limited floor space remaining");
        }
        if (wallSpaceUsed > 80) {
            recommendations.push("⚠️ Wall space nearly fully utilized");
        }
        if (totalPowerDraw > 1500) {
            recommendations.push("⚡ May require dedicated 20A circuit");
        }
        if (recommendations.length === 0) {
            recommendations.push("✅ All metrics within normal ranges.");
        }
        document.getElementById('recommendationsList').innerHTML = recommendations.join('<br>');
    }
}

// --- MAIN 3D LOGIC ---
function init() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x2a3a4a);
    scene.fog = new THREE.Fog(0x2a3a4a, toUnits(30), toUnits(120));

    const container = document.getElementById('container');
    camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
    setView('overview', false);

    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
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
}

// --- SCENE CREATION FUNCTIONS ---
function createRealisticRoom() {
    const floorMaterial = new THREE.MeshStandardMaterial({ color: 0x8B7355, roughness: 0.8, metalness: 0.1 });
    const wallMaterial = new THREE.MeshStandardMaterial({ color: 0xF5F5F5, roughness: 0.9, metalness: 0.05 });
    const ceilingMaterial = new THREE.MeshStandardMaterial({ color: 0xFFFFFF, roughness: 0.95 });

    const wallHeight = toUnits(roomDims.height);

    const floor = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)), floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    floor.name = 'floor';
    scene.add(floor);

    const wallsConfig = [
        { pos: [0, wallHeight / 2, -toUnits(roomDims.width / 2)], rot: [0, 0, 0], size: [toUnits(roomDims.length), wallHeight] },
        { pos: [-toUnits(roomDims.length / 2), wallHeight / 2, 0], rot: [0, Math.PI / 2, 0], size: [toUnits(roomDims.width), wallHeight] },
        { pos: [toUnits(roomDims.length / 2), wallHeight / 2, 0], rot: [0, -Math.PI / 2, 0], size: [toUnits(roomDims.width), wallHeight] },
        { pos: [0, wallHeight / 2, toUnits(roomDims.width / 2)], rot: [0, Math.PI, 0], size: [toUnits(roomDims.length), wallHeight] }
    ];

    wallsConfig.forEach((config, index) => {
        const wall = new THREE.Mesh(new THREE.PlaneGeometry(config.size[0], config.size[1]), wallMaterial);
        wall.position.set(...config.pos);
        wall.rotation.set(...config.rot);
        wall.receiveShadow = true;
        wall.name = `wall_${index}`;
        scene.add(wall);
    });

    const ceiling = new THREE.Mesh(new THREE.PlaneGeometry(toUnits(roomDims.length), toUnits(roomDims.width)), ceilingMaterial);
    ceiling.position.y = wallHeight;
    ceiling.rotation.x = Math.PI / 2;
    ceiling.receiveShadow = true;
    ceiling.name = 'ceiling';
    scene.add(ceiling);
}

function createEnhancedLighting() {
    scene.add(new THREE.HemisphereLight(0x87CEEB, 0x8B7355, 0.6));
    const dirLight = new THREE.DirectionalLight(0xFFF8DC, 0.8);
    dirLight.position.set(toUnits(10), toUnits(15), toUnits(8));
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.set(2048, 2048);
    scene.add(dirLight);
}

function createRoomFurniture() {
    const roomSpec = allRoomSpecs[roomType] || {};
    const tableConfig = getTableConfig(roomType, roomSpec);
    const tableMaterial = new THREE.MeshStandardMaterial({ color: 0x8B4513, roughness: 0.3, metalness: 0.1 });

    const table = new THREE.Mesh(new THREE.BoxGeometry(toUnits(tableConfig.length), toUnits(tableConfig.height), toUnits(tableConfig.width)), tableMaterial);
    table.position.set(tableConfig.x, toUnits(tableConfig.height / 2), tableConfig.z);
    table.castShadow = true;
    table.receiveShadow = true;
    table.name = 'conference_table';
    scene.add(table);

    const chairPositions = calculateChairPositions(roomSpec, tableConfig);
    createChairs(chairPositions);
}

function getTableConfig(type, spec) {
    const tableSize = spec.table_size || [10, 4];
    const defaultConfig = { length: tableSize[0], width: tableSize[1], height: 2.5, x: 0, z: 0 };
    // This could be expanded with more specific configs per room type
    return defaultConfig;
}

function calculateChairPositions(spec, tableConfig) {
    const positions = [];
    const chairCount = spec.chair_count || 8;
    const tableLength = tableConfig.length;
    const tableWidth = tableConfig.width;

    const chairsPerSide = Math.ceil((chairCount - 2) / 2);
    const spacing = tableLength / (chairsPerSide + 1);

    for (let i = 1; i <= chairsPerSide; i++) {
        const x = -tableLength / 2 + i * spacing;
        if (positions.length < chairCount) positions.push({ x: x, z: tableWidth / 2 + 2, rotationY: Math.PI });
        if (positions.length < chairCount) positions.push({ x: x, z: -tableWidth / 2 - 2, rotationY: 0 });
    }
    if (positions.length < chairCount) positions.push({ x: tableLength / 2 + 1, z: 0, rotationY: -Math.PI / 2 });
    if (positions.length < chairCount) positions.push({ x: -tableLength / 2 - 1, z: 0, rotationY: Math.PI / 2 });

    return positions;
}

function createChairs(positions) {
    const chairMaterial = new THREE.MeshStandardMaterial({ color: 0x333333, roughness: 0.7 });
    positions.forEach((pos, index) => {
        const chair = new THREE.Group();
        const seat = new THREE.Mesh(new THREE.BoxGeometry(toUnits(1.5), toUnits(0.3), toUnits(1.5)), chairMaterial);
        seat.position.y = toUnits(1.5);
        const backrest = new THREE.Mesh(new THREE.BoxGeometry(toUnits(1.5), toUnits(2), toUnits(0.2)), chairMaterial);
        backrest.position.set(0, toUnits(2.5), toUnits(-0.65));
        chair.add(seat, backrest);
        chair.position.set(toUnits(pos.x), 0, toUnits(pos.z));
        chair.rotation.y = pos.rotationY || 0;
        chair.castShadow = true;
        chair.name = `chair_${index}`;
        scene.add(chair);
    });
}

function createPlaceableEquipmentObjects() {
    avEquipment.forEach(equipment => {
        const obj = createEquipmentMesh(equipment);
        obj.userData = { equipment: equipment, placed: false };
        obj.visible = false;
        scene.add(obj);
    });
}

function createEquipmentMesh(equipment) {
    const specs = equipment.specs;
    const material = new THREE.MeshStandardMaterial({
        color: 0x2a2a2a,
        roughness: 0.7,
        metalness: 0.1
    });
    const geometry = new THREE.BoxGeometry(toUnits(specs[0]), toUnits(specs[1]), toUnits(specs[2]));
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.name = `equipment_${equipment.id}`;
    return mesh;
}

// --- EVENT LISTENERS & CONTROLS ---
function setupEnhancedControls() {
    const container = document.getElementById('container');
    let isMouseDown = false;
    let previousMousePosition = { x: 0, y: 0 };

    container.addEventListener('mousedown', (e) => {
        if (e.button === 0 && !placementMode) {
            isMouseDown = true;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        }
    });

    container.addEventListener('mousemove', (e) => {
        const rect = container.getBoundingClientRect();
        mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

        if (isMouseDown && !placementMode) {
            const deltaX = e.clientX - previousMousePosition.x;
            const deltaY = e.clientY - previousMousePosition.y;
            camera.rotation.y -= deltaX * 0.005;
            camera.rotation.x -= deltaY * 0.005;
            previousMousePosition = { x: e.clientX, y: e.clientY };
        } else if (placementMode && draggedEquipment) {
            updateDraggedEquipmentPosition();
        }
    });

    container.addEventListener('mouseup', () => { isMouseDown = false; });
    container.addEventListener('wheel', onMouseWheel);
    container.addEventListener('drop', onDrop);
    container.addEventListener('dragover', (e) => e.preventDefault());
}

function onMouseWheel(event) {
    event.preventDefault();
    const zoomFactor = event.deltaY > 0 ? 1.1 : 0.9;
    camera.position.multiplyScalar(zoomFactor);
}

function onDrop(event) {
    event.preventDefault();
    if (!placementMode) return;
    const equipmentId = event.dataTransfer.getData('text/plain');
    draggedEquipment = avEquipment.find(eq => eq.id.toString() === equipmentId);
    if (draggedEquipment) {
        placeDraggedEquipment();
    }
}

function updateDraggedEquipmentPosition() {
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(scene.children, true);
    const targetIntersect = intersects.find(i => i.object.name === 'floor' || i.object.name.startsWith('wall_'));
    if (targetIntersect) {
        const obj = scene.getObjectByName(`equipment_${draggedEquipment.id}`);
        if (obj) {
            obj.visible = true;
            obj.position.copy(targetIntersect.point);
        }
    }
}

function placeDraggedEquipment() {
    const obj = scene.getObjectByName(`equipment_${draggedEquipment.id}`);
    if (obj) {
        obj.userData.placed = true;
        spaceAnalytics.addPlacedEquipment(obj, draggedEquipment);
        updateEquipmentList();
    }
    draggedEquipment = null;
    document.getElementById('modeIndicator').textContent = 'PLACE MODE';
}

function setupKeyboardControls() {
    document.addEventListener('keydown', (e) => {
        if (e.key === 'p') togglePlacementMode();
        if (e.key === '1') setView('overview', true, document.querySelector('#controls button:nth-child(1)'));
        if (e.key === '2') setView('front', true, document.querySelector('#controls button:nth-child(2)'));
        if (e.key === '3') setView('side', true, document.querySelector('#controls button:nth-child(3)'));
        if (e.key === '4') setView('top', true, document.querySelector('#controls button:nth-child(4)'));
    });
}

// --- UI UPDATE FUNCTIONS ---
function updateEquipmentList() {
    const listElement = document.getElementById('equipmentList');
    listElement.innerHTML = avEquipment.map(eq => {
        const obj = scene.getObjectByName(`equipment_${eq.id}`);
        const isPlaced = obj && obj.userData.placed;
        return `
            <div class="equipment-item ${isPlaced ? 'placed' : ''}" 
                 draggable="${!isPlaced}" 
                 ondragstart="event.dataTransfer.setData('text/plain', '${eq.id}')">
                <div class="equipment-name">${eq.name}</div>
                <div class="equipment-details">${eq.brand}</div>
            </div>`;
    }).join('');
}

function togglePlacementMode() {
    placementMode = !placementMode;
    const button = document.getElementById('placementToggle');
    const indicator = document.getElementById('modeIndicator');
    if (placementMode) {
        button.textContent = 'VIEW MODE';
        indicator.textContent = 'PLACE MODE';
        button.classList.add('active');
    } else {
        button.textContent = 'PLACE MODE';
        indicator.textContent = 'VIEW MODE';
        button.classList.remove('active');
        if (draggedEquipment) { // Cancel any active drag
            const obj = scene.getObjectByName(`equipment_${draggedEquipment.id}`);
            if (obj) obj.visible = false;
            draggedEquipment = null;
        }
    }
}

function setView(viewType, animate = true, buttonElement = null) {
    if (buttonElement) {
        document.querySelectorAll('.control-btn').forEach(btn => btn.classList.remove('active'));
        buttonElement.classList.add('active');
    }

    const dist = Math.max(roomDims.length, roomDims.width) * 0.8;
    let newPosition;
    switch (viewType) {
        case 'overview': newPosition = new THREE.Vector3(toUnits(dist * 0.7), toUnits(roomDims.height + dist * 0.4), toUnits(dist * 0.7)); break;
        case 'front': newPosition = new THREE.Vector3(0, toUnits(roomDims.height * 0.6), toUnits(roomDims.width / 2 + dist * 0.5)); break;
        case 'side': newPosition = new THREE.Vector3(toUnits(roomDims.length / 2 + dist * 0.5), toUnits(roomDims.height * 0.6), 0); break;
        case 'top': newPosition = new THREE.Vector3(0, toUnits(roomDims.height + dist), 0.1); break;
    }

    // Simple immediate move for now, animation can be added later
    camera.position.copy(newPosition);
    camera.lookAt(0, toUnits(roomDims.height * 0.3), 0);
}

function resetLayout() {
    scene.children.forEach(child => {
        if (child.name.startsWith('equipment_')) {
            child.visible = false;
            child.userData.placed = false;
        }
    });
    spaceAnalytics.placedEquipment = [];
    spaceAnalytics.updateAnalytics();
    updateEquipmentList();
}

function saveLayout() {
    const layout = spaceAnalytics.placedEquipment.map(item => ({
        id: item.equipment.id,
        position: item.position
    }));
    console.log('Layout Saved:', JSON.stringify(layout, null, 2));
    alert('Layout saved to browser console!');
}

// --- RENDER LOOP ---
function animate() {
    animationId = requestAnimationFrame(animate);
    renderer.render(scene, camera);
}

// --- INITIALIZATION ---
window.addEventListener('load', init);
window.addEventListener('resize', () => {
    const container = document.getElementById('container');
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
});
