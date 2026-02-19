"""
Time mapping module to convert regular times to Ramadan times
with fuzzy matching for close-but-not-exact time matches
"""

import json
import logging
from typing import List, Dict, Optional, Tuple

from config import FUZZY_MATCHING

logger = logging.getLogger(__name__)


class TimeMapper:
    def __init__(self, mapping_file: str = "time_mapping.json"):
        """Initialize with time mapping file"""
        with open(mapping_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.mappings = data["mappings"]

        # Create quick lookup dictionary
        self.mapping_dict: Dict[str, str] = {}
        for mapping in self.mappings:
            self.mapping_dict[mapping["before_ramadan"]] = mapping["during_ramadan"]

        # Pre-parse all mappings into minutes for fuzzy matching
        self._parsed_mappings: List[Dict] = []
        for mapping in self.mappings:
            before = mapping["before_ramadan"]
            parts = before.split("-")
            start_minutes = self._time_to_minutes(parts[0])
            end_minutes = self._time_to_minutes(parts[1])
            self._parsed_mappings.append(
                {
                    "key": before,
                    "ramadan": mapping["during_ramadan"],
                    "start_minutes": start_minutes,
                    "end_minutes": end_minutes,
                    "duration": end_minutes - start_minutes,
                }
            )

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to total minutes since midnight"""
        time_str = self.normalize_time(time_str)
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _minutes_to_time(self, minutes: int) -> str:
        """Convert total minutes back to HH:MM"""
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def normalize_time(self, time_str: str) -> str:
        """
        Normalize time format to HH:MM
        Examples: "8.0" -> "08:00", "9.15" -> "09:15"
        """
        if "." in time_str:
            parts = time_str.split(".")
            hour = parts[0].zfill(2)
            minute = parts[1] if len(parts) > 1 else "00"
            if len(minute) == 1:
                minute = minute + "0"
            minute = minute.zfill(2)
            return f"{hour}:{minute}"
        elif ":" in time_str:
            parts = time_str.split(":")
            hour = parts[0].zfill(2)
            minute = parts[1]
            if len(minute) == 1:
                minute = minute + "0"
            minute = minute.zfill(2)
            return f"{hour}:{minute}"
        else:
            return f"{time_str.zfill(2)}:00"

    def format_time_slot(self, start_time: str, end_time: str) -> str:
        """Format time slot as 'HH:MM-HH:MM'"""
        start = self.normalize_time(start_time)
        end = self.normalize_time(end_time)
        return f"{start}-{end}"

    def _fuzzy_find_mapping(self, start_time: str, end_time: str) -> Optional[Dict]:
        """
        Find the closest matching time mapping within tolerance

        Uses a scoring system:
        - Exact match on start time is weighted higher
        - Duration similarity is considered
        - Total time difference must be within tolerance

        Returns:
            Dict with 'ramadan_start', 'ramadan_end', 'match_type', 'original_key'
            or None if no close match found
        """
        if not FUZZY_MATCHING.get("enabled", True):
            return None

        tolerance = FUZZY_MATCHING.get("time_tolerance_minutes", 5)
        start_minutes = self._time_to_minutes(start_time)
        end_minutes = self._time_to_minutes(end_time)
        input_duration = end_minutes - start_minutes

        best_match = None
        best_score = float("inf")

        for mapping in self._parsed_mappings:
            start_diff = abs(mapping["start_minutes"] - start_minutes)
            end_diff = abs(mapping["end_minutes"] - end_minutes)
            duration_diff = abs(mapping["duration"] - input_duration)

            # Both start and end must be within tolerance
            if start_diff > tolerance or end_diff > tolerance:
                continue

            # Score: lower is better
            # Weight start_time difference more heavily (it's more likely to be correct)
            score = (start_diff * 2) + (end_diff * 1.5) + duration_diff

            if score < best_score:
                best_score = score
                ramadan_parts = mapping["ramadan"].split("-")
                best_match = {
                    "ramadan_start": self.normalize_time(ramadan_parts[0]),
                    "ramadan_end": self.normalize_time(ramadan_parts[1]),
                    "match_type": "fuzzy",
                    "original_key": mapping["key"],
                    "score": score,
                    "start_diff": start_diff,
                    "end_diff": end_diff,
                }

        if best_match:
            logger.info(
                f"Fuzzy match: {start_time}-{end_time} → "
                f"{best_match['original_key']} "
                f"(start_diff={best_match['start_diff']}min, "
                f"end_diff={best_match['end_diff']}min)"
            )

        return best_match

    def map_time_slot(self, start_time: str, end_time: str) -> Optional[Dict[str, str]]:
        """
        Map a time slot from before Ramadan to during Ramadan
        First tries exact match, then falls back to fuzzy matching

        Args:
            start_time: Start time (e.g., "08:00" or "8.0")
            end_time: End time (e.g., "09:15" or "9.15")

        Returns:
            Dictionary with ramadan_start, ramadan_end, and match_type
            or None if not found
        """
        # Normalize the input times
        norm_start = self.normalize_time(start_time)
        norm_end = self.normalize_time(end_time)
        time_slot = f"{norm_start}-{norm_end}"

        # Try exact match first
        if time_slot in self.mapping_dict:
            ramadan_time = self.mapping_dict[time_slot]
            parts = ramadan_time.split("-")
            return {
                "ramadan_start": self.normalize_time(parts[0]),
                "ramadan_end": self.normalize_time(parts[1]),
                "match_type": "exact",
            }

        # Try fuzzy matching
        fuzzy_result = self._fuzzy_find_mapping(norm_start, norm_end)
        if fuzzy_result:
            return fuzzy_result

        logger.warning(f"No mapping found for time slot: {time_slot}")
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
            mapped_time = self.map_time_slot(cls["start_time"], cls["end_time"])

            if mapped_time:
                cls["ramadan_start_time"] = mapped_time["ramadan_start"]
                cls["ramadan_end_time"] = mapped_time["ramadan_end"]
                cls["original_start_time"] = cls["start_time"]
                cls["original_end_time"] = cls["end_time"]
                cls["match_type"] = mapped_time.get("match_type", "exact")

                if mapped_time.get("match_type") == "fuzzy":
                    cls["fuzzy_matched_from"] = mapped_time.get("original_key", "")
                    logger.info(
                        f"Fuzzy matched {cls['course_code']}: "
                        f"{cls['start_time']}-{cls['end_time']} → "
                        f"{cls['ramadan_start_time']}-{cls['ramadan_end_time']} "
                        f"(from {cls['fuzzy_matched_from']})"
                    )

                converted.append(cls)
            else:
                unmapped.append(cls)
                logger.warning(
                    f"Unmapped: {cls.get('course_code', '?')} "
                    f"{cls['start_time']}-{cls['end_time']}"
                )

        logger.info(
            f"Conversion complete: {len(converted)} converted, "
            f"{len(unmapped)} unmapped out of {len(classes)} total"
        )

        return converted, unmapped

    def get_all_mappings(self) -> List[Dict]:
        """Get all available time mappings"""
        return self.mappings

    def get_unmapped_suggestions(self, start_time: str, end_time: str) -> List[Dict]:
        """
        Get the top 3 closest mappings for an unmapped time slot
        Useful for suggesting possible matches to the user
        """
        start_minutes = self._time_to_minutes(start_time)
        end_minutes = self._time_to_minutes(end_time)

        scored = []
        for mapping in self._parsed_mappings:
            start_diff = abs(mapping["start_minutes"] - start_minutes)
            end_diff = abs(mapping["end_minutes"] - end_minutes)
            total_diff = start_diff + end_diff
            scored.append(
                {
                    "before_ramadan": mapping["key"],
                    "during_ramadan": mapping["ramadan"],
                    "total_diff_minutes": total_diff,
                    "start_diff": start_diff,
                    "end_diff": end_diff,
                }
            )

        scored.sort(key=lambda x: x["total_diff_minutes"])
        return scored[:3]
