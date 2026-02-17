"""
Time mapping module to convert regular times to Ramadan times
"""
import json
from typing import List, Dict, Optional, Tuple


class TimeMapper:
    def __init__(self, mapping_file: str = "time_mapping.json"):
        """Initialize with time mapping file"""
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.mappings = data['mappings']
        
        # Create quick lookup dictionary
        self.mapping_dict = {}
        for mapping in self.mappings:
            self.mapping_dict[mapping['before_ramadan']] = mapping['during_ramadan']
    
    def normalize_time(self, time_str: str) -> str:
        """
        Normalize time format to HH:MM
        Examples: "8.0" -> "08:00", "9.15" -> "09:15"
        """
        if '.' in time_str:
            # Format like "8.0" or "9.15"
            parts = time_str.split('.')
            hour = parts[0].zfill(2)
            minute = parts[1].zfill(2) if len(parts) > 1 else "00"
            return f"{hour}:{minute}"
        elif ':' in time_str:
            # Already in HH:MM format
            parts = time_str.split(':')
            hour = parts[0].zfill(2)
            minute = parts[1].zfill(2)
            return f"{hour}:{minute}"
        else:
            # Just hour
            return f"{time_str.zfill(2)}:00"
    
    def format_time_slot(self, start_time: str, end_time: str) -> str:
        """Format time slot as 'HH:MM-HH:MM'"""
        start = self.normalize_time(start_time)
        end = self.normalize_time(end_time)
        return f"{start}-{end}"
    
    def map_time_slot(self, start_time: str, end_time: str) -> Optional[Dict[str, str]]:
        """
        Map a time slot from before Ramadan to during Ramadan
        
        Args:
            start_time: Start time (e.g., "08:00" or "8.0")
            end_time: End time (e.g., "09:15" or "9.15")
        
        Returns:
            Dictionary with ramadan_start and ramadan_end, or None if not found
        """
        # Normalize the input times
        time_slot = self.format_time_slot(start_time, end_time)
        
        # Look up in mapping
        if time_slot in self.mapping_dict:
            ramadan_time = self.mapping_dict[time_slot]
            parts = ramadan_time.split('-')
            return {
                'ramadan_start': self.normalize_time(parts[0]),
                'ramadan_end': self.normalize_time(parts[1])
            }
        
        return None
    
    def convert_timetable(self, classes: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Convert entire timetable from regular to Ramadan times
        
        Args:
            classes: List of class dictionaries with start_time and end_time
        
        Returns:
            Tuple of (converted_classes, unmapped_classes)
        """
        converted = []
        unmapped = []
        
        for cls in classes:
            mapped_time = self.map_time_slot(cls['start_time'], cls['end_time'])
            
            if mapped_time:
                cls['ramadan_start_time'] = mapped_time['ramadan_start']
                cls['ramadan_end_time'] = mapped_time['ramadan_end']
                cls['original_start_time'] = cls['start_time']
                cls['original_end_time'] = cls['end_time']
                converted.append(cls)
            else:
                unmapped.append(cls)
        
        return converted, unmapped
    
    def get_all_mappings(self) -> List[Dict]:
        """Get all available time mappings"""
        return self.mappings
