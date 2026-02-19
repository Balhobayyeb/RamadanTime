"""
Ramadan timetable image generator
Creates a visual timetable similar to the original
"""

from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict


class TimetableImageGenerator:
    # Days of the week in Arabic (right to left)
    DAYS_AR = ["السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"]
    DAYS_EN = [
        "Saturday",
        "Sunday",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
    ]

    # Map between Arabic and English day names
    AR_TO_EN = dict(zip(DAYS_AR, DAYS_EN))
    EN_TO_AR = dict(zip(DAYS_EN, DAYS_AR))

    # Color palette for different courses
    COLORS = [
        "#C8E36D",  # Yellow-green
        "#9B6DB8",  # Purple
        "#FF8C42",  # Orange
        "#E87A90",  # Pink
        "#2D7D5E",  # Dark green
        "#4ECDC4",  # Cyan
        "#FF6B6B",  # Red
        "#95E1D3",  # Mint
        "#F38181",  # Coral
        "#AA96DA",  # Lavender
    ]

    def __init__(self, width=1000, height=800):
        """Initialize image generator with dimensions"""
        self.width = width
        self.height = height
        self.cell_width = 120
        self.cell_height = 60
        self.header_height = 50
        self.time_column_width = 100

    def _get_font(self, size=20, bold=False):
        """Get font (tries to use system fonts, falls back to default)"""
        try:
            if bold:
                return ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size
                )
            return ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
            )
        except Exception:
            return ImageFont.load_default()

    def _get_arabic_font(self, size=20):
        """Get Arabic-supporting font"""
        try:
            fonts = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            ]
            for font_path in fonts:
                try:
                    return ImageFont.truetype(font_path, size)
                except Exception:
                    continue
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    def _time_to_row(self, time_str: str) -> float:
        """Convert time string to row position (hours from 8:00)"""
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1])

        if hour < 8:
            hour += 12

        return (hour - 8) + (minute / 60.0)

    def _get_day_index(self, day_name: str) -> int:
        """Get day index from day name (supports both Arabic and English)"""
        # Try Arabic first
        for i, day in enumerate(self.DAYS_AR):
            if day == day_name:
                return i

        # Then try English
        day_name_lower = day_name.lower()
        for i, day in enumerate(self.DAYS_EN):
            if day.lower() == day_name_lower:
                return i

        return -1

    def generate_timetable(
        self, classes: List[Dict], output_path: str = "ramadan_timetable.png"
    ):
        """
        Generate Ramadan timetable image

        Args:
            classes: List of classes with ramadan_start_time and ramadan_end_time
            output_path: Path to save the image
        """
        img = Image.new("RGB", (self.width, self.height), "white")
        draw = ImageDraw.Draw(img)

        header_font = self._get_arabic_font(22)
        time_font = self._get_font(16)
        course_font = self._get_font(18, bold=True)
        small_font = self._get_font(12)

        start_x = self.time_column_width
        start_y = self.header_height

        # Draw title
        title = "جدول رمضان - Ramadan Timetable"
        draw.text(
            (self.width // 2, 20), title, fill="#2C3E50", font=header_font, anchor="mm"
        )

        # Draw grid headers (days in Arabic)
        for i, day in enumerate(self.DAYS_AR[::-1]):
            x = start_x + i * self.cell_width
            draw.rectangle(
                [x, start_y, x + self.cell_width, start_y + self.header_height],
                outline="#2C3E50",
                fill="#ECF0F1",
                width=2,
            )
            draw.text(
                (x + self.cell_width // 2, start_y + self.header_height // 2),
                day,
                fill="#2C3E50",
                font=header_font,
                anchor="mm",
            )

        # Draw time column header
        draw.rectangle(
            [0, start_y, self.time_column_width, start_y + self.header_height],
            outline="#2C3E50",
            fill="#ECF0F1",
            width=2,
        )
        draw.text(
            (self.time_column_width // 2, start_y + self.header_height // 2),
            "الوقت",
            fill="#2C3E50",
            font=header_font,
            anchor="mm",
        )

        # Draw time slots (10:00 to 18:00 for Ramadan)
        time_start_y = start_y + self.header_height
        for hour in range(10, 19):
            y = time_start_y + (hour - 10) * self.cell_height
            draw.rectangle(
                [0, y, self.time_column_width, y + self.cell_height],
                outline="#BDC3C7",
                width=1,
            )
            draw.text(
                (self.time_column_width // 2, y + self.cell_height // 2),
                f"{hour}:00",
                fill="#34495E",
                font=time_font,
                anchor="mm",
            )

        # Draw vertical grid lines for days
        for i in range(8):
            x = start_x + i * self.cell_width
            draw.line(
                [(x, start_y), (x, time_start_y + 9 * self.cell_height)],
                fill="#BDC3C7",
                width=1,
            )

        # Assign colors to courses
        course_colors: Dict[str, str] = {}
        color_idx = 0
        for cls in classes:
            course = cls["course_code"]
            if course not in course_colors:
                course_colors[course] = self.COLORS[color_idx % len(self.COLORS)]
                color_idx += 1

        # Draw class blocks
        for cls in classes:
            day_idx = self._get_day_index(cls["day"])
            if day_idx == -1:
                continue

            # Reverse day index for right-to-left layout
            day_idx = 6 - day_idx

            start_time_row = self._time_to_row(cls["ramadan_start_time"])
            end_time_row = self._time_to_row(cls["ramadan_end_time"])

            x1 = start_x + day_idx * self.cell_width + 5
            y1 = time_start_y + (start_time_row - 2) * self.cell_height + 5
            x2 = x1 + self.cell_width - 10
            y2 = time_start_y + (end_time_row - 2) * self.cell_height - 5

            color = course_colors.get(cls["course_code"], "#95A5A6")
            draw.rounded_rectangle(
                [x1, y1, x2, y2], radius=10, fill=color, outline="#2C3E50", width=2
            )

            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            draw.text(
                (center_x, center_y - 15),
                cls["course_code"],
                fill="white",
                font=course_font,
                anchor="mm",
                stroke_width=1,
                stroke_fill="#2C3E50",
            )

            time_text = f"{cls['ramadan_start_time']}-{cls['ramadan_end_time']}"
            draw.text(
                (center_x, center_y + 10),
                time_text,
                fill="white",
                font=small_font,
                anchor="mm",
            )

        img.save(output_path, quality=95)
        return output_path

    def generate_summary_text(self, classes: List[Dict], unmapped: List[Dict]) -> str:
        """Generate text summary of the conversion (Arabic days)"""
        text = "تحويل الجدول لأوقات رمضان - Timetable Converted to Ramadan Times\n\n"

        if classes:
            text += f"تم تحويل {len(classes)} محاضرة - Converted {len(classes)} classes:\n\n"

            # Group by day using Arabic day order
            by_day: Dict[str, List[Dict]] = {}
            for cls in classes:
                day = cls["day"]
                if day not in by_day:
                    by_day[day] = []
                by_day[day].append(cls)

            for day_ar in self.DAYS_AR:
                if day_ar in by_day:
                    text += f"{day_ar}:\n"
                    for cls in sorted(
                        by_day[day_ar], key=lambda c: c.get("ramadan_start_time", "")
                    ):
                        text += f"   {cls['course_code']}: "
                        text += (
                            f"{cls['original_start_time']}-{cls['original_end_time']}"
                        )
                        text += (
                            f" -> {cls['ramadan_start_time']}-{cls['ramadan_end_time']}"
                        )
                        match_type = cls.get("match_type", "exact")
                        if match_type == "fuzzy":
                            text += " (تقريبي)"
                        text += "\n"
                    text += "\n"

        if unmapped:
            text += f"\n{len(unmapped)} محاضرة لم يتم إيجاد التوقيت المناسب لها:\n"
            text += f"Warning - {len(unmapped)} classes could not be mapped:\n\n"
            for cls in unmapped:
                text += f"   {cls['course_code']} ({cls['day']}): {cls['start_time']}-{cls['end_time']}\n"
            text += "\nيرجى التواصل مع المسؤول لإضافة هذه الأوقات.\n"
            text += "Please contact the admin to add these time slots.\n"

        return text
