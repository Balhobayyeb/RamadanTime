"""
Timetable extraction module using GPT-4o-mini vision API
"""
import base64
import json
from openai import OpenAI
from typing import List, Dict, Optional


class TimetableExtractor:
    def __init__(self, api_key: str):
        """Initialize the extractor with OpenAI API key"""
        self.client = OpenAI(api_key=api_key)
        
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def extract_from_image(self, image_path: str) -> Optional[List[Dict]]:
        """
        Extract timetable data from image using GPT-4o-mini
        
        Returns:
            List of classes with format:
            [
                {
                    "course_code": "IT 352",
                    "day": "Monday",
                    "start_time": "08:00",
                    "end_time": "09:15"
                },
                ...
            ]
        """
        try:
            base64_image = self.encode_image(image_path)
            
            prompt = """
You are analyzing a university class timetable image. This is a weekly schedule grid with:
- Days of the week as columns (in Arabic: السبت=Saturday, الأحد=Sunday, الاثنين=Monday, الثلاثاء=Tuesday, الأربعاء=Wednesday, الخميس=Thursday, الجمعة=Friday)
- Time slots as rows (shown on the right side)
- Colored blocks representing classes with course codes and time ranges

Extract ALL classes from this timetable and return them in JSON format.

For each class block, extract:
1. course_code (e.g., "IT 352", "CS 222", "IC 103")
2. day (convert Arabic day to English: السبت→Saturday, الأحد→Sunday, الاثنين→Monday, الثلاثاء→Tuesday, الأربعاء→Wednesday, الخميس→Thursday, الجمعة→Friday)
3. start_time (in HH:MM format, e.g., "08:00")
4. end_time (in HH:MM format, e.g., "09:15")

The time is usually written on the block itself (e.g., "8.0-9.15" or "9.45-11.0").
Convert times like "8.0-9.15" to "08:00-09:15" format.

Return ONLY a valid JSON array with this exact structure:
[
    {
        "course_code": "IT 352",
        "day": "Monday",
        "start_time": "08:00",
        "end_time": "09:15"
    }
]

Important:
- Return ONLY the JSON array, no additional text
- Include ALL classes you can see in the image
- Convert all times to HH:MM format (add leading zeros)
- Convert Arabic day names to English
"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.1  # Low temperature for consistent extraction
            )
            
            # Extract the response text
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            # Parse JSON
            classes = json.loads(content)
            
            return classes
            
        except Exception as e:
            print(f"Error extracting timetable: {e}")
            return None
    
    def format_time_slot(self, start_time: str, end_time: str) -> str:
        """Format time slot as 'HH:MM-HH:MM' for matching"""
        return f"{start_time}-{end_time}"
