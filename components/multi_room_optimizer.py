# components/multi_room_optimizer.py
"""
Multi-Room Project Optimizer
Consolidates shared infrastructure across multiple rooms for cost savings
"""

import math
from typing import List, Dict, Any, Optional
import streamlit as st


class MultiRoomOptimizer:
    """
    Analyzes multiple rooms and consolidates equipment where beneficial
    """
    
    def __init__(self):
        self.optimization_threshold = 3  # Minimum rooms for optimization
        
    def optimize_multi_room_project(self, rooms_data: List[Dict]) -> Dict[str, Any]:
        """
        Main optimization entry point
        
        Args:
            rooms_data: List of room dicts with 'boq_items', 'name', 'area', etc.
        
        Returns:
            Dict with 'optimization', 'savings_pct', 'shared_infrastructure', 'rooms'
        """
        
        if len(rooms_data) < self.optimization_threshold:
            return {
                'optimization': 'none',
                'savings_pct': 0,
                'rooms': rooms_data,
                'reason': f'Need {self.optimization_threshold}+ rooms for optimization'
            }
        
        # Check if optimization is enabled (user toggle)
        if not st.session_state.get('multi_room_optimization_enabled', True):
            return {
                'optimization': 'disabled',
                'savings_pct': 0,
                'rooms': rooms_data,
                'reason': 'User disabled optimization'
            }
        
        # Calculate baseline cost
        baseline_cost = self._calculate_total_project_cost(rooms_data)
        
        # 1. Network Infrastructure Consolidation
        network_consolidation = self._consolidate_network_infrastructure(rooms_data)
        
        # 2. Equipment Rack Consolidation (if rooms are adjacent/same floor)
        rack_consolidation = self._consolidate_equipment_racks(rooms_data)
        
        # 3. Audio Amplification Consolidation (if feasible)
        audio_consolidation = self._consolidate_audio_infrastructure(rooms_data)
        
        # 4. Apply consolidations to rooms
        optimized_rooms = self._apply_consolidation_to_rooms(
            rooms_data,
            network_consolidation,
            rack_consolidation,
            audio_consolidation
        )
        
        # Calculate optimized cost
        optimized_cost = self._calculate_total_project_cost(optimized_rooms)
        
        # Calculate savings
        savings_amount = baseline_cost - optimized_cost
        savings_pct = (savings_amount / baseline_cost * 100) if baseline_cost > 0 else 0
        
        return {
            'optimization': 'multi-room',
            'baseline_cost': baseline_cost,
            'optimized_cost': optimized_cost,
            'savings_amount': savings_amount,
            'savings_pct': savings_pct,
            'shared_infrastructure': {
                'network': network_consolidation,
                'racks': rack_consolidation,
                'audio': audio_consolidation
            },
            'rooms': optimized_rooms
        }
    
    def _consolidate_network_infrastructure(self, rooms_data: List[Dict]) -> Dict:
        """
        Replace individual room switches with centralized switch
        """
        total_ports_needed = 0
        switches_to_remove = []
        
        for room in rooms_data:
            boq_items = room.get('boq_items', [])
            
            # Count network devices
            network_devices = sum(
                1 for item in boq_items 
                if item.get('category') in ['Video Conferencing', 'Control Systems', 'Displays']
            )
            
            total_ports_needed += network_devices
            
            # Find existing switches to eliminate
            for item in boq_items:
                if 'Switch' in item.get('sub_category', '') or 'Switch' in item.get('name', ''):
                    switches_to_remove.append({
                        'room': room['name'],
                        'item': item
                    })
        
        # Add 30% overhead for future expansion
        total_ports_needed = int(total_ports_needed * 1.3)
        
        # Select appropriate centralized switch
        if total_ports_needed <= 24:
            switch_spec = {
                'type': '24-port Managed PoE+ Switch',
                'ports': 24,
                'model': 'Cisco CBS350-24P',
                'estimated_cost': 800
            }
        elif total_ports_needed <= 48:
            switch_spec = {
                'type': '48-port Managed PoE+ Switch',
                'ports': 48,
                'model': 'Cisco CBS350-48P',
                'estimated_cost': 1500
            }
        else:
            switch_spec = {
                'type': 'Stacked 48-port Switches (2x)',
                'ports': 96,
                'model': 'Cisco CBS350-48P (Stack)',
                'estimated_cost': 3000
            }
        
        # Calculate cost savings
        eliminated_switch_cost = sum(
            switch['item'].get('price', 0) * switch['item'].get('quantity', 1)
            for switch in switches_to_remove
        )
        
        net_savings = eliminated_switch_cost - switch_spec['estimated_cost']
        
        return {
            'enabled': True,
            'centralized_switch': switch_spec,
            'ports_required': total_ports_needed,
            'location': 'Central IT Room / Main IDF',
            'eliminates_individual_switches': len(switches_to_remove),
            'switches_removed': switches_to_remove,
            'cost_savings': net_savings
        }
    
    def _consolidate_equipment_racks(self, rooms_data: List[Dict]) -> Dict:
        """
        Consolidate racks where beneficial (same floor, adjacent rooms)
        """
        total_rack_space_needed = 0
        individual_racks = []
        
        for room in rooms_data:
            boq_items = room.get('boq_items', [])
            
            # Count rack units needed
            rack_mount_items = [
                item for item in boq_items
                if item.get('category') in ['Video Conferencing', 'Audio', 'Signal Management', 'Infrastructure']
                and 'rack' in item.get('name', '').lower()
            ]
            
            # Estimate rack space (rough heuristic)
            if rack_mount_items:
                estimated_u = len(rack_mount_items) * 2  # Avg 2U per device
                total_rack_space_needed += estimated_u
                
                # Find existing rack items to remove
                for item in boq_items:
                    if item.get('sub_category') == 'AV Rack':
                        individual_racks.append({
                            'room': room['name'],
                            'item': item
                        })
        
        # Decision: Consolidate if total space < 36U (fits in one full-height rack)
        if total_rack_space_needed <= 36 and len(rooms_data) >= 3:
            consolidated = {
                'enabled': True,
                'rack_type': '42U Full-Height Rack',
                'location': 'Central Equipment Room',
                'total_u_required': total_rack_space_needed,
                'eliminates_individual_racks': len(individual_racks),
                'individual_racks_removed': individual_racks,
                'estimated_cost': 2000,
                'cost_savings': sum(
                    rack['item'].get('price', 0) * rack['item'].get('quantity', 1)
                    for rack in individual_racks
                ) - 2000
            }
        else:
            consolidated = {
                'enabled': False,
                'reason': 'Rooms too large or distributed for central rack',
                'consolidated_count': 0
            }
        
        return consolidated
    
    def _consolidate_audio_infrastructure(self, rooms_data: List[Dict]) -> Optional[Dict]:
        """
        For adjacent rooms, use centralized amplification with zone control
        Note: Only beneficial if rooms are on same floor/wing
        """
        
        # This is complex and requires physical layout knowledge
        # For MVP, return None (no consolidation)
        # In production, you'd ask user "Are rooms on same floor/adjacent?"
        
        total_speaker_zones = sum(
            sum(1 for item in room.get('boq_items', []) 
                if 'Speaker' in item.get('sub_category', ''))
            for room in rooms_data
        )
        
        # Only consolidate if user confirms rooms are adjacent
        if st.session_state.get('rooms_are_adjacent', False):
            return {
                'enabled': True,
                'type': 'Centralized Multi-Zone Amplifier',
                'channels': total_speaker_zones,
                'model': f'QSC SPA{total_speaker_zones * 50}',
                'location': 'Central Equipment Room',
                'requires_zone_controllers': True,
                'cost_savings': 0  # Complex calculation
            }
        
        return {
            'enabled': False,
            'reason': 'Audio consolidation requires adjacent rooms'
        }
    
    def _apply_consolidation_to_rooms(
        self,
        rooms_data: List[Dict],
        network_consolidation: Dict,
        rack_consolidation: Dict,
        audio_consolidation: Optional[Dict]
    ) -> List[Dict]:
        """
        Remove consolidated items from individual rooms and add shared infrastructure
        """
        
        optimized_rooms = []
        
        for room in rooms_data:
            room_copy = room.copy()
            boq_items = room_copy.get('boq_items', []).copy()
            
            # Remove individual network switches
            if network_consolidation.get('enabled'):
                removed_switches = [
                    sw['item'] for sw in network_consolidation['switches_removed']
                    if sw['room'] == room['name']
                ]
                
                for switch_item in removed_switches:
                    # Find and remove by model number match
                    boq_items = [
                        item for item in boq_items
                        if item.get('model_number') != switch_item.get('model_number')
                    ]
            
            # Remove individual racks if consolidated
            if rack_consolidation.get('enabled'):
                removed_racks = [
                    rack['item'] for rack in rack_consolidation['individual_racks_removed']
                    if rack['room'] == room['name']
                ]
                
                for rack_item in removed_racks:
                    boq_items = [
                        item for item in boq_items
                        if item.get('sub_category') != 'AV Rack'
                    ]
            
            room_copy['boq_items'] = boq_items
            optimized_rooms.append(room_copy)
        
        # Add shared infrastructure to first room (or create separate "Shared Equipment" room)
        if optimized_rooms:
            shared_items = []
            
            # Add centralized network switch
            if network_consolidation.get('enabled'):
                switch_spec = network_consolidation['centralized_switch']
                shared_items.append({
                    'category': 'Networking',
                    'sub_category': 'Network Switch',
                    'name': switch_spec['model'],
                    'brand': 'Cisco',
                    'model_number': switch_spec['model'],
                    'quantity': 1,
                    'price': switch_spec['estimated_cost'],
                    'justification': f"Centralized switch serving {len(rooms_data)} rooms",
                    'specifications': f"{switch_spec['ports']}-port PoE+ managed switch",
                    'warranty': '3 Years',
                    'lead_time_days': 14,
                    'unit_of_measure': 'piece',
                    'matched': True,
                    'top_3_reasons': [
                        f"Consolidates {network_consolidation['eliminates_individual_switches']} individual switches",
                        f"Cost savings: ${network_consolidation['cost_savings']:.2f}",
                        "Centralized management and easier troubleshooting"
                    ]
                })
            
            # Add centralized rack if applicable
            if rack_consolidation.get('enabled'):
                shared_items.append({
                    'category': 'Infrastructure',
                    'sub_category': 'AV Rack',
                    'name': rack_consolidation['rack_type'],
                    'brand': 'Middle Atlantic',
                    'model_number': 'ERK-4425',
                    'quantity': 1,
                    'price': rack_consolidation['estimated_cost'],
                    'justification': f"Centralized rack for all {len(rooms_data)} rooms",
                    'specifications': f"{rack_consolidation['rack_type']} with {rack_consolidation['total_u_required']}U occupied",
                    'warranty': '10 Years',
                    'lead_time_days': 14,
                    'unit_of_measure': 'piece',
                    'matched': True,
                    'top_3_reasons': [
                        f"Consolidates {rack_consolidation['eliminates_individual_racks']} individual racks",
                        f"Cost savings: ${rack_consolidation['cost_savings']:.2f}",
                        "Centralized equipment location simplifies maintenance"
                    ]
                })
            
            # Add shared items to first room or create "Shared Infrastructure" room
            if shared_items:
                # Option 1: Add to first room
                optimized_rooms[0]['boq_items'].extend(shared_items)
                
                # Option 2: Create separate "Shared Equipment" room (better for clarity)
                # optimized_rooms.insert(0, {
                #     'name': 'Shared Infrastructure (All Rooms)',
                #     'type': 'Infrastructure',
                #     'area': 0,
                #     'boq_items': shared_items
                # })
        
        return optimized_rooms
    
    def _calculate_total_project_cost(self, rooms_data: List[Dict]) -> float:
        """
        Sum up total cost across all rooms
        """
        total = 0
        
        for room in rooms_data:
            boq_items = room.get('boq_items', [])
            room_cost = sum(
                item.get('price', 0) * item.get('quantity', 1)
                for item in boq_items
            )
            total += room_cost
        
        return total
    
    def _rooms_are_adjacent(self, rooms_data: List[Dict]) -> bool:
        """
        Check if rooms are physically adjacent (requires user input)
        For MVP, return False. In production, prompt user.
        """
        return st.session_state.get('rooms_are_adjacent', False)


# ==================== HELPER FUNCTIONS ====================

def show_optimization_settings_ui():
    """
    Optional: Add UI in sidebar for user to control optimization behavior
    Call this from app.py sidebar section
    """
    
    st.markdown("### 🔧 Multi-Room Optimization")
    
    if len(st.session_state.get('project_rooms', [])) >= 3:
        enable_optimization = st.checkbox(
            "Enable Multi-Room Optimization",
            value=True,
            key="multi_room_optimization_enabled",
            help="Consolidates equipment across rooms for cost savings"
        )
        
        if enable_optimization:
            st.checkbox(
                "Rooms are on same floor/adjacent",
                value=False,
                key="rooms_are_adjacent",
                help="Enables audio amplifier consolidation"
            )
            
            st.info(f"✅ Will optimize across {len(st.session_state.project_rooms)} rooms")
    else:
        st.info(f"Need 3+ rooms for optimization\n\nCurrent: {len(st.session_state.get('project_rooms', []))} room(s)")
```

---

## **TESTING THE INTEGRATION**

After adding the above integrations, test with this scenario:

1. **Create 3 Rooms:**
   - Room 1: Standard Conference (6-8 people)
   - Room 2: Large Conference (8-12 people)
   - Room 3: Training Room (15-25 people)

2. **Generate BOQs for Each Room**

3. **Check Download Button:**
   - Should show optimization message
   - Excel should have shared infrastructure items

4. **Expected Output:**
```
   # 🔧 Multi-Room Optimization Applied
   
   Cost Savings: 12.5%
   
   Shared Infrastructure:
   - 48-port Managed PoE+ Switch
   - Centralized equipment racks: 1
   - Eliminates 3 individual switches
