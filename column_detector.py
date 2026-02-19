"""
Column detector for university timetable images.

Detects the grid structure in a timetable image and crops individual day columns.
The timetable has 7 day columns (equal width, right-to-left) + 1 time column (narrower, rightmost).

Layout (physical left-to-right):
  | السبت | الجمعة | الخميس | الأربعاء | الثلاثاء | الاثنين | الأحد | TIME |

Detection algorithm:
1. Find header (dark blue row at top)
2. Find horizontal grid lines (gray rows below header)
3. Find vertical grid lines at h-line intersections
4. Use outer grid boundaries + equal-width interpolation to compute all 8 column dividers
"""

import logging
from PIL import Image
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from config import TIMETABLE_COLUMNS

logger = logging.getLogger(__name__)


class ColumnDetector:
    """Detects and crops individual day columns from a timetable image."""

    # Pixel color thresholds
    HEADER_BLUE_MIN = (30, 50, 70)
    HEADER_BLUE_MAX = (100, 130, 180)
    GRAY_NEUTRAL_TOLERANCE = 25  # max diff between r,g,b channels
    GRAY_BRIGHTNESS_RANGE = (90, 200)  # avg brightness for gray pixels

    def __init__(self):
        pass

    def detect_and_crop(self, image_path: str) -> Optional[List[Dict]]:
        """
        Detect columns in a timetable image and crop each day column.

        Args:
            image_path: Path to the timetable image

        Returns:
            List of dicts, each with:
                - 'day': Arabic day name from TIMETABLE_COLUMNS
                - 'column_index': 0-based index (0=الأحد rightmost, 6=السبت leftmost)
                - 'image': PIL Image of the cropped column
                - 'bounds': (x_left, y_top, x_right, y_bottom)
            Or None if detection fails.
        """
        try:
            img = Image.open(image_path).convert("RGB")
        except Exception as e:
            logger.error(f"Failed to open image: {e}")
            return None

        w, h = img.size
        pixels = img.load()
        logger.info(f"Image size: {w}x{h}")

        # Step 1: Find header
        header_top, header_bottom = self._find_header(pixels, w, h)
        if header_top is None or header_bottom is None:
            logger.error("Could not find header in image")
            return None
        logger.info(f"Header: y={header_top} to y={header_bottom}")

        # Step 2: Find horizontal grid lines
        h_lines = self._find_horizontal_lines(pixels, w, h, header_bottom)
        if len(h_lines) < 3:
            logger.error(f"Not enough horizontal lines found: {len(h_lines)}")
            return None
        logger.info(f"Found {len(h_lines)} horizontal grid lines")

        # Step 3: Find vertical lines at h-line positions
        scan_ys = self._expand_scan_rows(h_lines, header_bottom, h)
        v_lines = self._find_vertical_lines(pixels, w, scan_ys)
        if len(v_lines) < 2:
            logger.error(f"Not enough vertical lines found: {len(v_lines)}")
            return None
        logger.info(f"Detected vertical lines: {v_lines}")

        # Step 4: Compute column boundaries via interpolation
        grid_left = v_lines[0]
        grid_right = v_lines[-1]
        grid_width = grid_right - grid_left

        # Find optimal time column width by testing 9% and 10%
        best_time_pct, best_error = self._find_best_time_pct(
            grid_left, grid_right, grid_width, v_lines
        )
        time_col_width = int(grid_width * best_time_pct)
        day_total = grid_width - time_col_width
        day_col_width = day_total / 7

        logger.info(
            f"Grid: x={grid_left}-{grid_right} (w={grid_width}), "
            f"time_col={best_time_pct:.0%} ({time_col_width}px), "
            f"day_col={day_col_width:.1f}px"
        )

        # Generate column boundaries
        # Physical layout left-to-right: [السبت, الجمعة, ..., الأحد, TIME]
        # TIMETABLE_COLUMNS order: [الأحد(0), الاثنين(1), ..., السبت(6)]
        # So physical column i (0=leftmost=السبت) maps to TIMETABLE_COLUMNS[6-i]

        # Column boundaries from left to right (day columns only, excluding time)
        col_boundaries = []
        for i in range(8):  # 7 day columns = 8 boundaries
            x = int(grid_left + i * day_col_width)
            col_boundaries.append(x)
        # The last boundary should be where the time column starts
        time_col_start = col_boundaries[-1]

        logger.info(f"Column boundaries: {col_boundaries}")
        logger.info(f"Time column: x={time_col_start}-{grid_right}")

        # Step 5: Crop each day column
        # Grid content starts just below header, ends at last h-line or image bottom
        content_top = header_bottom
        content_bottom = h_lines[-1] if h_lines else h

        results = []
        for phys_col in range(7):  # 0=leftmost=السبت, 6=rightmost=الأحد
            x_left = col_boundaries[phys_col]
            x_right = col_boundaries[phys_col + 1]

            # Map physical column to day index
            # Physical 0 (leftmost) = السبت = TIMETABLE_COLUMNS[6]
            # Physical 6 (rightmost) = الأحد = TIMETABLE_COLUMNS[0]
            day_index = 6 - phys_col
            day_name = TIMETABLE_COLUMNS[day_index]

            # Crop the column
            crop_box = (x_left, content_top, x_right, content_bottom)
            col_img = img.crop(crop_box)

            # Check if column has content (colored blocks)
            has_content = self._column_has_content(col_img)

            results.append(
                {
                    "day": day_name,
                    "column_index": day_index,
                    "image": col_img,
                    "bounds": crop_box,
                    "has_content": has_content,
                    "width": x_right - x_left,
                }
            )

            logger.info(
                f"Column {day_index} ({day_name}): "
                f"x={x_left}-{x_right} (w={x_right - x_left}), "
                f"has_content={has_content}"
            )

        return results

    def _find_header(
        self, pixels, w: int, h: int
    ) -> Tuple[Optional[int], Optional[int]]:
        """Find the dark blue header bar at the top of the image."""
        header_top = None
        header_bottom = None
        min_r, min_g, min_b = self.HEADER_BLUE_MIN
        max_r, max_g, max_b = self.HEADER_BLUE_MAX

        for y in range(h):
            blue_count = 0
            for x in range(w):
                r, g, b = pixels[x, y]
                if min_r < r < max_r and min_g < g < max_g and min_b < b < max_b:
                    blue_count += 1

            if blue_count > w * 0.3:
                if header_top is None:
                    header_top = y
                header_bottom = y + 1
            elif header_top is not None:
                break

        return header_top, header_bottom

    def _find_horizontal_lines(self, pixels, w: int, h: int, start_y: int) -> List[int]:
        """Find horizontal gray grid lines below the header."""
        h_lines = []
        tol = self.GRAY_NEUTRAL_TOLERANCE
        bmin, bmax = self.GRAY_BRIGHTNESS_RANGE

        for y in range(start_y, h):
            gray_count = 0
            for x in range(w):
                r, g, b = pixels[x, y]
                if abs(r - g) < tol and abs(g - b) < tol:
                    avg = (r + g + b) / 3
                    if bmin < avg < bmax:
                        gray_count += 1
            if gray_count > w * 0.3:
                h_lines.append(y)

        if not h_lines:
            return []

        # Merge adjacent rows into single line positions
        groups = [[h_lines[0]]]
        for y in h_lines[1:]:
            if y - groups[-1][-1] <= 3:
                groups[-1].append(y)
            else:
                groups.append([y])

        return [int(sum(g) / len(g)) for g in groups]

    def _expand_scan_rows(
        self, h_lines: List[int], start_y: int, max_y: int
    ) -> List[int]:
        """Expand horizontal line positions to +-2 rows for scanning."""
        scan_ys = []
        for hy in h_lines:
            for dy in range(-2, 3):
                y = hy + dy
                if start_y <= y < max_y:
                    scan_ys.append(y)
        return scan_ys

    def _find_vertical_lines(self, pixels, w: int, scan_ys: List[int]) -> List[int]:
        """Find vertical gray lines by scanning at given y positions."""
        tol = self.GRAY_NEUTRAL_TOLERANCE
        bmin, bmax = self.GRAY_BRIGHTNESS_RANGE
        x_votes = defaultdict(int)

        for y in scan_ys:
            for x in range(w):
                r, g, b = pixels[x, y]
                if abs(r - g) < tol and abs(g - b) < tol:
                    avg = (r + g + b) / 3
                    if bmin < avg < bmax:
                        x_votes[x] += 1

        n_rows = len(scan_ys)
        threshold = max(1, n_rows * 0.3)
        strong = sorted([x for x, count in x_votes.items() if count >= threshold])

        if not strong:
            return []

        # Merge nearby x values
        groups = [[strong[0]]]
        for x in strong[1:]:
            if x - groups[-1][-1] <= 4:
                groups[-1].append(x)
            else:
                groups.append([x])

        return [int(sum(g) / len(g)) for g in groups]

    def _find_best_time_pct(
        self,
        grid_left: int,
        grid_right: int,
        grid_width: int,
        v_lines: List[int],
    ) -> Tuple[float, float]:
        """
        Find the best time column width percentage by testing candidates
        and checking which one best matches the detected vertical lines.
        """
        best_pct = 0.10
        best_error = float("inf")

        for time_pct_100 in range(7, 14):  # 7% to 13%
            time_pct = time_pct_100 / 100.0
            time_w = int(grid_width * time_pct)
            day_total = grid_width - time_w
            day_w = day_total / 7

            # Generate expected column boundaries
            expected = [grid_left]
            for i in range(7):
                expected.append(int(grid_left + (i + 1) * day_w))
            expected.append(grid_right)

            # Calculate match error against detected lines
            total_error = 0
            matched = 0
            inner_lines = v_lines[1:-1]  # Exclude outer boundaries
            for det in inner_lines:
                min_dist = min(abs(det - exp) for exp in expected)
                total_error += min_dist
                if min_dist <= 5:
                    matched += 1

            avg_error = total_error / max(len(inner_lines), 1)

            if avg_error < best_error:
                best_error = avg_error
                best_pct = time_pct

        logger.info(f"Best time column: {best_pct:.0%} (avg error: {best_error:.1f}px)")
        return best_pct, best_error

    def _column_has_content(self, col_img: Image.Image) -> bool:
        """
        Check if a cropped column has colored blocks (not just white/gray/grid).
        Returns True if there are significant colored (non-neutral) pixels.
        """
        w, h = col_img.size
        pixels = col_img.load()

        colored_count = 0
        total_checked = 0

        # Sample every 3rd pixel for speed
        for y in range(0, h, 3):
            for x in range(0, w, 3):
                r, g, b = pixels[x, y]
                total_checked += 1

                # Skip white/near-white
                if r > 230 and g > 230 and b > 230:
                    continue

                # Skip gray (neutral colors used for grid lines)
                avg = (r + g + b) / 3
                if abs(r - avg) < 15 and abs(g - avg) < 15 and abs(b - avg) < 15:
                    continue

                # Skip very dark (near black, borders)
                if r < 30 and g < 30 and b < 30:
                    continue

                # This pixel is colored
                colored_count += 1

        # If more than 3% of sampled pixels are colored, column has content
        ratio = colored_count / max(total_checked, 1)
        return ratio > 0.03
