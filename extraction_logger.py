"""
Extraction logging module for debugging and tracking extraction accuracy
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import shutil

logger = logging.getLogger(__name__)


class ExtractionLogger:
    def __init__(self, log_directory: str = "logs"):
        """Initialize the extraction logger"""
        self.log_directory = log_directory
        self.ensure_log_directory()

    def ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
            logger.info(f"Created log directory: {self.log_directory}")

    def log_extraction_attempt(
        self,
        user_id: int,
        attempt_number: int,
        strategy: str,
        success: bool,
        extracted_classes: Optional[List[Dict]] = None,
        error: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> str:
        """
        Log an extraction attempt

        Returns:
            Path to the log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{timestamp}_user{user_id}_attempt{attempt_number}.json"
        log_path = os.path.join(self.log_directory, log_filename)

        log_data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "attempt_number": attempt_number,
            "strategy": strategy,
            "success": success,
            "extracted_classes_count": len(extracted_classes)
            if extracted_classes
            else 0,
            "extracted_classes": extracted_classes,
            "error": error,
        }

        # Save log file
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        # Save failed image for debugging
        if not success and image_path and os.path.exists(image_path):
            image_filename = f"{timestamp}_user{user_id}_failed.jpg"
            image_log_path = os.path.join(self.log_directory, image_filename)
            shutil.copy2(image_path, image_log_path)
            logger.info(f"Saved failed image: {image_log_path}")

        logger.info(f"Logged extraction attempt: {log_path}")
        return log_path

    def log_conversion_result(
        self,
        user_id: int,
        extracted_count: int,
        converted_count: int,
        unmapped_count: int,
        unmapped_times: List[str],
    ) -> str:
        """
        Log time conversion results

        Returns:
            Path to the log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"{timestamp}_user{user_id}_conversion.json"
        log_path = os.path.join(self.log_directory, log_filename)

        log_data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "extracted_count": extracted_count,
            "converted_count": converted_count,
            "unmapped_count": unmapped_count,
            "unmapped_times": unmapped_times,
            "conversion_rate": f"{(converted_count / extracted_count * 100):.1f}%"
            if extracted_count > 0
            else "0%",
        }

        # Save log file
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Logged conversion result: {log_path}")
        return log_path

    def get_stats(self) -> Dict:
        """Get statistics from all logged extractions"""
        stats = {
            "total_attempts": 0,
            "successful_attempts": 0,
            "failed_attempts": 0,
            "success_rate": 0.0,
            "average_classes_extracted": 0.0,
        }

        log_files = [
            f
            for f in os.listdir(self.log_directory)
            if f.endswith(".json") and "attempt" in f
        ]

        if not log_files:
            return stats

        total_classes = 0
        successful = 0

        for log_file in log_files:
            try:
                with open(os.path.join(self.log_directory, log_file), "r") as f:
                    data = json.load(f)
                    stats["total_attempts"] += 1
                    if data.get("success"):
                        successful += 1
                        total_classes += data.get("extracted_classes_count", 0)
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")

        stats["successful_attempts"] = successful
        stats["failed_attempts"] = stats["total_attempts"] - successful
        stats["success_rate"] = (
            (successful / stats["total_attempts"] * 100)
            if stats["total_attempts"] > 0
            else 0
        )
        stats["average_classes_extracted"] = (
            (total_classes / successful) if successful > 0 else 0
        )

        return stats

    def cleanup_old_logs(self, days: int = 7):
        """Delete logs older than specified days"""
        import time

        current_time = time.time()
        deleted_count = 0

        for filename in os.listdir(self.log_directory):
            file_path = os.path.join(self.log_directory, filename)
            if os.path.isfile(file_path):
                file_age_days = (current_time - os.path.getmtime(file_path)) / 86400
                if file_age_days > days:
                    os.remove(file_path)
                    deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old log files")
