"""
Configuration file for Ramadan Timetable Bot
"""

# Fixed column order in the timetable image (right-to-left)
# Column 1 (rightmost) = الأحد (Sunday), Column 7 (leftmost) = السبت (Saturday)
# This NEVER changes across timetable images.
TIMETABLE_COLUMNS = [
    "الأحد",  # Column 1 (rightmost)
    "الاثنين",  # Column 2
    "الثلاثاء",  # Column 3
    "الأربعاء",  # Column 4
    "الخميس",  # Column 5
    "الجمعة",  # Column 6
    "السبت",  # Column 7 (leftmost)
]

# OpenAI API Configuration
OPENAI_CONFIG = {
    "model": "gpt-4o",  # Upgraded from gpt-4o-mini for better vision accuracy
    "max_tokens": 2000,  # Increased for better extraction coverage
    "temperature": 0,  # 0 for most consistent results (was 0.1)
    "max_retries": 3,  # Number of retry attempts if extraction fails
}

# Extraction Validation
VALIDATION_CONFIG = {
    "min_classes_expected": 1,  # Minimum number of classes to consider valid
    "max_classes_expected": 50,  # Maximum reasonable number of classes
    "required_fields": ["course_code", "day", "start_time", "end_time"],
    "valid_days": [
        "Saturday",
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
    ],
    "valid_days_arabic": [
        "السبت",
        "الأحد",
        "الاثنين",
        "الثلاثاء",
        "الأربعاء",
        "الخميس",
        "الجمعة",
    ],
}

# Fuzzy Matching Configuration
FUZZY_MATCHING = {
    "enabled": True,
    "time_tolerance_minutes": 5,  # Allow ±5 minutes difference for fuzzy matching
    "similarity_threshold": 0.85,  # Minimum similarity score (0-1) for fuzzy match
}

# Logging Configuration
LOGGING_CONFIG = {
    "enabled": True,
    "log_extractions": True,  # Log all extraction attempts
    "log_directory": "logs",  # Directory to store extraction logs
    "save_failed_images": True,  # Save images that failed extraction for debugging
}

# Retry Strategy
RETRY_CONFIG = {
    "strategies": [
        # First attempt: Standard extraction
        {"temperature": 0, "max_tokens": 2000, "description": "Standard extraction"},
        # Second attempt: Higher tokens, ask model to be more thorough
        {
            "temperature": 0.1,
            "max_tokens": 3000,
            "description": "Thorough extraction with more tokens",
        },
        # Third attempt: Slightly higher temperature for alternative interpretation
        {
            "temperature": 0.3,
            "max_tokens": 3000,
            "description": "Alternative interpretation",
        },
    ]
}

# Image Preprocessing
IMAGE_CONFIG = {
    "preprocessing_enabled": True,
    "enhance_contrast": True,
    "denoise": False,  # Can be enabled if images are noisy
    "max_image_size": (2048, 2048),  # Resize large images to save API costs
}
