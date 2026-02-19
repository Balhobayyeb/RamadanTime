"""
Timetable extraction module using GPT-4o vision API
with hybrid column-based approach for accurate day detection.

Strategy:
1. Use ColumnDetector to detect grid structure and crop individual day columns
2. Send each non-empty column to GPT-4o separately (simple prompt: just read course codes + times)
3. Assign day from column position (deterministic, 100% accurate)
4. Fall back to full-image extraction if column detection fails
"""

import base64
import json
import re
import logging
from openai import OpenAI
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageEnhance
import io

from config import (
    OPENAI_CONFIG,
    VALIDATION_CONFIG,
    RETRY_CONFIG,
    IMAGE_CONFIG,
    TIMETABLE_COLUMNS,
)
from extraction_logger import ExtractionLogger
from column_detector import ColumnDetector

logger = logging.getLogger(__name__)


class TimetableExtractor:
    def __init__(self, api_key: str):
        """Initialize the extractor with OpenAI API key"""
        self.client = OpenAI(api_key=api_key)
        self.extraction_logger = ExtractionLogger()
        self.column_detector = ColumnDetector()

    def encode_image(self, image_path: str) -> str:
        """Encode image to base64, with optional preprocessing"""
        if IMAGE_CONFIG.get("preprocessing_enabled"):
            return self._preprocess_and_encode(image_path)
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def encode_pil_image(self, img: Image.Image) -> str:
        """Encode a PIL Image to base64"""
        if IMAGE_CONFIG.get("enhance_contrast"):
            try:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.5)
            except Exception:
                pass

        buffer = io.BytesIO()
        img.save(buffer, format="PNG", quality=95)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")

    def _preprocess_and_encode(self, image_path: str) -> str:
        """Preprocess image for better OCR results then encode to base64"""
        try:
            img = Image.open(image_path)

            # Resize if too large (saves API cost and can improve accuracy)
            max_size = IMAGE_CONFIG.get("max_image_size", (2048, 2048))
            if img.width > max_size[0] or img.height > max_size[1]:
                try:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                except AttributeError:
                    img.thumbnail(max_size)
                logger.info(f"Resized image to {img.size}")

            # Enhance contrast for better text readability
            if IMAGE_CONFIG.get("enhance_contrast"):
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.3)

                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.5)

            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=95)
            buffer.seek(0)
            return base64.b64encode(buffer.read()).decode("utf-8")

        except Exception as e:
            logger.warning(f"Image preprocessing failed, using original: {e}")
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")

    def _build_column_prompt(self) -> str:
        """Build a simple prompt for extracting classes from a SINGLE column image."""
        return """You are reading a single column from a university timetable image.

This image shows ONE day column only. It contains colored blocks representing classes.
Each class block has:
  - A COURSE CODE (e.g., "IT 352", "CS 222", "IC 103", "CS 214")
  - A TIME RANGE (e.g., "8.0-9.15", "9.45-11.0", "13.15-14.55")

RULES:
1. Read EVERY colored block that has text on it.
2. SKIP solid-color blocks with NO text (no course code, no time). These are empty/break blocks.
3. Read the time range written directly on each block, character by character.
4. Read the course code written on each block.

TIME FORMAT RULES:
- Convert "8.0-9.15" to start_time "08:00", end_time "09:15"
- Convert "9.45-11.0" to start_time "09:45", end_time "11:00"
- Convert "11.30-13.10" to start_time "11:30", end_time "13:10"
- Convert "13.15-14.55" to start_time "13:15", end_time "14:55"
- Convert "16.30-18.10" to start_time "16:30", end_time "18:10"
- Always use HH:MM with leading zeros. Always 24-hour format.

Return ONLY a JSON array with the classes found. No other text. 
If no classes are found (all blocks are empty), return an empty array [].

Example:
[
    {"course_code": "IT 352", "start_time": "08:00", "end_time": "09:15"},
    {"course_code": "CS 222", "start_time": "09:45", "end_time": "11:25"}
]"""

    def _build_fullimage_prompt(self, attempt: int = 0) -> str:
        """Build the extraction prompt for full-image fallback mode."""
        col_lines = []
        for i, day in enumerate(TIMETABLE_COLUMNS):
            position = (
                "rightmost"
                if i == 0
                else (
                    "leftmost"
                    if i == len(TIMETABLE_COLUMNS) - 1
                    else f"#{i + 1} from right"
                )
            )
            col_lines.append(f"  - Column {i + 1} ({position}) = {day}")
        columns_text = "\n".join(col_lines)

        base_prompt = f"""You are extracting class data from a university timetable image.

LAYOUT (THIS IS FIXED - DO NOT read the header text, use these positions):
The timetable is a grid. The columns represent days of the week, ordered RIGHT-TO-LEFT:
{columns_text}

The time grid is on the RIGHT side of the image (8.00, 9.00, 10.00, ... 18.00).
Colored blocks inside the grid represent classes. Each class block has:
  - A TIME RANGE written on it (e.g., "8.0-9.15", "9.45-11.0", "13.15-14.55")
  - A COURSE CODE written on it (e.g., "IT 352", "CS 222", "IC 103", "CS 214")

RULES:
1. Determine each block's DAY by its COLUMN POSITION (count from right), NOT by reading Arabic header text.
2. Read the TIME RANGE written directly on the block. Do NOT guess times from the grid.
3. Read the COURSE CODE written on the block.
4. SKIP any solid-color block that has NO text on it (no course code, no time). These are empty/break blocks.
5. If a course appears in multiple columns, create a SEPARATE entry for each one.

TIME FORMAT RULES:
- Convert "8.0-9.15" to start_time "08:00", end_time "09:15"
- Always use HH:MM with leading zeros. Always 24-hour format.

Return ONLY a JSON array. No other text. Example format:
[
    {{"course_code": "IT 352", "day": "الاثنين", "start_time": "08:00", "end_time": "09:15"}},
    {{"course_code": "CS 222", "day": "الاثنين", "start_time": "09:45", "end_time": "11:25"}}
]"""

        if attempt >= 1:
            base_prompt += """

IMPORTANT: This is retry attempt. The previous extraction had errors.
- Go through EVERY column one by one, right to left.
- Double-check each block's column position to assign the correct day.
- Double-check the time range written on each block character by character."""

        return base_prompt

    def _validate_extracted_classes(
        self, classes: List[Dict], require_day: bool = True
    ) -> Tuple[List[Dict], List[str]]:
        """
        Validate extracted classes and fix common issues.

        Args:
            classes: List of class dicts
            require_day: If True, validate day field. If False (column mode), skip day validation.

        Returns:
            Tuple of (valid_classes, list_of_issues)
        """
        valid_classes = []
        issues = []
        time_pattern = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
        valid_days = VALIDATION_CONFIG["valid_days_arabic"]

        # Determine required fields based on mode
        required_fields = ["course_code", "start_time", "end_time"]
        if require_day:
            required_fields.append("day")

        for i, cls in enumerate(classes):
            class_issues = []

            # Skip entries with empty/placeholder course codes
            code = str(cls.get("course_code", "")).strip()
            if not code or code.lower() in ("", "none", "n/a", "-", "break", "empty"):
                issues.append(f"Class {i + 1}: skipped (empty/placeholder course code)")
                continue

            # Check required fields
            for field in required_fields:
                if field not in cls or not cls[field]:
                    class_issues.append(f"Class {i + 1}: missing '{field}'")

            if class_issues:
                issues.extend(class_issues)
                continue

            # Normalize and validate day (only in full-image mode)
            if require_day:
                day = cls.get("day", "").strip()
                english_to_arabic = {
                    "saturday": "السبت",
                    "sunday": "الأحد",
                    "monday": "الاثنين",
                    "tuesday": "الثلاثاء",
                    "wednesday": "الأربعاء",
                    "thursday": "الخميس",
                    "friday": "الجمعة",
                }
                if day.lower() in english_to_arabic:
                    cls["day"] = english_to_arabic[day.lower()]
                    day = cls["day"]

                if day not in valid_days:
                    class_issues.append(f"Class {i + 1}: invalid day '{day}'")

            # Normalize and validate times
            for time_field in ["start_time", "end_time"]:
                time_val = cls.get(time_field, "")
                time_val = self._normalize_time_value(time_val)
                cls[time_field] = time_val

                if not time_pattern.match(time_val):
                    class_issues.append(
                        f"Class {i + 1}: invalid {time_field} '{time_val}'"
                    )

            # Validate start < end
            if not class_issues:
                start_parts = cls["start_time"].split(":")
                end_parts = cls["end_time"].split(":")
                start_minutes = int(start_parts[0]) * 60 + int(start_parts[1])
                end_minutes = int(end_parts[0]) * 60 + int(end_parts[1])
                if start_minutes >= end_minutes:
                    class_issues.append(
                        f"Class {i + 1} ({cls.get('course_code', '?')}): "
                        f"start_time {cls['start_time']} >= end_time {cls['end_time']}"
                    )

            if class_issues:
                issues.extend(class_issues)
            else:
                # Clean up course code
                cls["course_code"] = cls["course_code"].strip().upper()
                valid_classes.append(cls)

        return valid_classes, issues

    def _normalize_time_value(self, time_str: str) -> str:
        """Normalize various time formats to HH:MM"""
        time_str = time_str.strip()

        # Handle dot format: "8.0", "9.15", "13.30"
        if "." in time_str:
            parts = time_str.split(".")
            hour = parts[0].strip().zfill(2)
            minute = parts[1].strip()
            # Handle "0" meaning "00"
            if len(minute) == 1:
                minute = minute + "0"
            minute = minute.zfill(2)
            return f"{hour}:{minute}"

        # Handle colon format: "8:0", "09:15"
        if ":" in time_str:
            parts = time_str.split(":")
            hour = parts[0].strip().zfill(2)
            minute = parts[1].strip()
            if len(minute) == 1:
                minute = minute + "0"
            minute = minute.zfill(2)
            return f"{hour}:{minute}"

        # Handle bare number: "8" → "08:00"
        if time_str.isdigit():
            return f"{time_str.zfill(2)}:00"

        return time_str

    def _parse_response(self, content: str) -> Optional[List[Dict]]:
        """Parse the model response, handling various formats"""
        content = content.strip()

        # Remove markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            filtered = []
            inside = False
            for line in lines:
                if line.strip().startswith("```") and not inside:
                    inside = True
                    continue
                elif line.strip() == "```" and inside:
                    inside = False
                    continue
                elif inside:
                    filtered.append(line)
            content = "\n".join(filtered).strip()

        # Try to find JSON array in the content
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            content = match.group(0)

        try:
            classes = json.loads(content)
            if isinstance(classes, list):
                return classes
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")

            # Try to fix common JSON issues
            try:
                fixed = re.sub(r",\s*([}\]])", r"\1", content)
                classes = json.loads(fixed)
                if isinstance(classes, list):
                    return classes
            except json.JSONDecodeError:
                pass

        return None

    def _extract_single_column(self, col_img: Image.Image, day_name: str) -> List[Dict]:
        """
        Extract classes from a single column image using GPT-4o.

        Args:
            col_img: PIL Image of the cropped column
            day_name: Arabic day name to assign to extracted classes

        Returns:
            List of validated class dicts with 'day' field added
        """
        base64_image = self.encode_pil_image(col_img)
        prompt = self._build_column_prompt()

        try:
            response = self.client.chat.completions.create(
                model=OPENAI_CONFIG["model"],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1000,
                temperature=0,
            )

            content = response.choices[0].message.content
            if not content:
                logger.warning(f"Column {day_name}: Empty response from GPT-4o")
                return []

            raw_classes = self._parse_response(content)
            if not raw_classes:
                logger.warning(
                    f"Column {day_name}: Could not parse JSON: {content[:200]}"
                )
                return []

            # Validate without requiring day field (we'll add it ourselves)
            valid_classes, issues = self._validate_extracted_classes(
                raw_classes, require_day=False
            )

            if issues:
                logger.info(
                    f"Column {day_name}: Validation issues: {'; '.join(issues)}"
                )

            # Add day field to each class (deterministic from column position)
            for cls in valid_classes:
                cls["day"] = day_name

            logger.info(f"Column {day_name}: Found {len(valid_classes)} classes")
            return valid_classes

        except Exception as e:
            logger.error(f"Column {day_name}: GPT-4o extraction failed: {e}")
            return []

    def extract_from_image(
        self, image_path: str, user_id: int = 0
    ) -> Optional[List[Dict]]:
        """
        Extract timetable data from image using hybrid column-based approach.

        Strategy:
        1. Try column detection + per-column GPT extraction (accurate day assignment)
        2. Fall back to full-image extraction if column detection fails

        Args:
            image_path: Path to the timetable image
            user_id: Telegram user ID for logging

        Returns:
            List of validated classes, or None if all attempts fail
        """
        # === Phase 1: Try hybrid column-based extraction ===
        logger.info("Phase 1: Attempting column-based extraction")
        columns = self.column_detector.detect_and_crop(image_path)

        if columns is not None:
            # Filter to columns with content
            active_columns = [col for col in columns if col["has_content"]]
            logger.info(
                f"Column detection succeeded: {len(active_columns)}/{len(columns)} "
                f"columns have content"
            )

            if active_columns:
                all_classes = []
                for col in active_columns:
                    day_name = col["day"]
                    col_img = col["image"]
                    logger.info(f"Extracting from column: {day_name}")

                    classes = self._extract_single_column(col_img, day_name)
                    all_classes.extend(classes)

                if all_classes:
                    logger.info(
                        f"Column-based extraction complete: "
                        f"{len(all_classes)} total classes from "
                        f"{len(active_columns)} columns"
                    )

                    # Log successful extraction
                    self.extraction_logger.log_extraction_attempt(
                        user_id,
                        1,
                        "Column-based extraction",
                        True,
                        extracted_classes=all_classes,
                    )

                    return all_classes
                else:
                    logger.warning(
                        "Column-based extraction found no classes, falling back"
                    )
            else:
                logger.warning("No active columns detected, falling back")
        else:
            logger.warning("Column detection failed, falling back to full-image mode")

        # === Phase 2: Fallback to full-image extraction ===
        logger.info("Phase 2: Falling back to full-image extraction")
        return self._extract_fullimage(image_path, user_id)

    def _extract_fullimage(
        self, image_path: str, user_id: int = 0
    ) -> Optional[List[Dict]]:
        """
        Fallback: Extract from full image (original approach).
        Used when column detection fails.
        """
        base64_image = self.encode_image(image_path)
        strategies = RETRY_CONFIG["strategies"]
        max_retries = min(OPENAI_CONFIG["max_retries"], len(strategies))

        best_result = None
        best_count = 0

        for attempt in range(max_retries):
            strategy = strategies[attempt]
            logger.info(
                f"Fallback attempt {attempt + 1}/{max_retries}: "
                f"{strategy['description']}"
            )

            try:
                prompt = self._build_fullimage_prompt(attempt)

                response = self.client.chat.completions.create(
                    model=OPENAI_CONFIG["model"],
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                    max_tokens=strategy["max_tokens"],
                    temperature=strategy["temperature"],
                )

                content = response.choices[0].message.content
                if not content:
                    logger.warning(f"Attempt {attempt + 1}: Empty response")
                    self.extraction_logger.log_extraction_attempt(
                        user_id,
                        attempt + 1,
                        strategy["description"],
                        False,
                        error="Empty response",
                        image_path=image_path,
                    )
                    continue

                raw_classes = self._parse_response(content)
                if not raw_classes:
                    logger.warning(f"Attempt {attempt + 1}: Could not parse JSON")
                    self.extraction_logger.log_extraction_attempt(
                        user_id,
                        attempt + 1,
                        strategy["description"],
                        False,
                        error=f"JSON parse failed: {content[:200]}",
                        image_path=image_path,
                    )
                    continue

                valid_classes, issues = self._validate_extracted_classes(raw_classes)

                if issues:
                    logger.warning(
                        f"Attempt {attempt + 1}: Validation issues: {'; '.join(issues)}"
                    )

                if not valid_classes:
                    self.extraction_logger.log_extraction_attempt(
                        user_id,
                        attempt + 1,
                        strategy["description"],
                        False,
                        error=f"No valid classes. Issues: {issues}",
                        image_path=image_path,
                    )
                    continue

                self.extraction_logger.log_extraction_attempt(
                    user_id,
                    attempt + 1,
                    strategy["description"],
                    True,
                    extracted_classes=valid_classes,
                )

                if len(valid_classes) > best_count:
                    best_result = valid_classes
                    best_count = len(valid_classes)
                    logger.info(
                        f"Attempt {attempt + 1}: Found {len(valid_classes)} "
                        f"valid classes (best so far)"
                    )

                if (
                    attempt == 0
                    and len(valid_classes) >= VALIDATION_CONFIG["min_classes_expected"]
                ):
                    logger.info("First attempt succeeded, skipping retries")
                    return valid_classes

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed with error: {e}")
                self.extraction_logger.log_extraction_attempt(
                    user_id,
                    attempt + 1,
                    strategy["description"],
                    False,
                    error=str(e),
                    image_path=image_path,
                )

        if best_result:
            logger.info(f"Returning best result with {best_count} classes")
            return best_result

        logger.error("All extraction attempts failed")
        return None

    def format_time_slot(self, start_time: str, end_time: str) -> str:
        """Format time slot as 'HH:MM-HH:MM' for matching"""
        return f"{start_time}-{end_time}"
