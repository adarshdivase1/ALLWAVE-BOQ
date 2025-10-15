# NEW FILE: components/multi_room_optimizer.py

class MultiRoomOptimizer:
    """
    Consolidates equipment across multiple rooms for cost savings
    """
    
    def optimize_multi_room_project(self, rooms_data: List[Dict]) -> Dict:
        """
        Analyzes all rooms and consolidates shared infrastructure
        """
        if len(rooms_data) <= 1:
            return {'optimization': 'none', 'rooms': rooms_data}
        
        # 1. Network Infrastructure Consolidation
        consolidated_network = self._consolidate_network_infrastructure(rooms_data)
        
        # 2. Audio Amplification Consolidation (if rooms are adjacent)
        consolidated_audio = self._consolidate_audio_infrastructure(rooms_data)
        
        # 3. Rack Consolidation
        consolidated_racks = self._consolidate_equipment_racks(rooms_data)
        
        # 4. Cable Run Optimization
        optimized_cables = self._optimize_cable_runs(rooms_data)
        
        return {
            'optimization': 'multi-room',
            'savings_pct': self._calculate_savings(rooms_data, consolidated_network, consolidated_audio),
            'shared_infrastructure': {
                'network': consolidated_network,
                'audio': consolidated_audio,
                'racks': consolidated_racks,
                'cables': optimized_cables
            },
            'rooms': self._apply_consolidation_to_rooms(rooms_data, ...)
        }
    
    def _consolidate_network_infrastructure(self, rooms_data):
        """
        Replace individual room switches with centralized switch
        Example: 5 rooms with 8-port switches → 1x 48-port PoE switch
        """
        total_ports_needed = sum(
            room.get('network_ports_required', 8) for room in rooms_data
        )
        
        # Add 20% overhead for future expansion
        total_ports_needed = int(total_ports_needed * 1.2)
        
        # Select appropriate switch size
        if total_ports_needed <= 24:
            switch_type = '24-port Managed PoE+'
        elif total_ports_needed <= 48:
            switch_type = '48-port Managed PoE+'
        else:
            switch_type = 'Stacked 48-port switches'
        
        return {
            'type': switch_type,
            'ports': total_ports_needed,
            'location': 'Central IT Room',
            'eliminates_individual_switches': len(rooms_data)
        }
    
    def _consolidate_audio_infrastructure(self, rooms_data):
        """
        For adjacent rooms, use centralized amplification with zone control
        """
        # Only consolidate if rooms are on same floor/wing
        if self._rooms_are_adjacent(rooms_data):
            total_speaker_zones = sum(
                room.get('speaker_zones', 2) for room in rooms_data
            )
            
            return {
                'type': 'Centralized Multi-Zone Amplifier',
                'channels': total_speaker_zones,
                'zone_controllers_per_room': 1,
                'eliminates_individual_amps': len(rooms_data)
            }
        
        return None
