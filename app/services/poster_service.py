import logging
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import io

from app.config import settings
from app.utils.ffmpeg_utils import extract_frame_high_quality

logger = logging.getLogger(__name__)


class PosterService:
    def __init__(self):
        self.output_path = Path(settings.output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)

        self.poster_width = settings.poster_width
        self.poster_height = settings.poster_height

        # Try to find fonts directory
        self.fonts_path = Path("/app/static/fonts")

    def generate_poster(
        self,
        background_mode: str,
        background_color: str,
        gradient_colors: List[str],
        gradient_direction: str,
        video_base: Optional[str],
        video_path: Optional[str],
        timestamp: float,
        selection_coords: Dict[str, float],
        blur: float,
        canvas_width: float,
        canvas_height: float,
        text_layers: List[Dict],
        line_elements: List[Dict],
        filename: str,
    ) -> str:
        """Generate final poster and save to output directory."""

        # Create poster canvas
        poster = Image.new(
            "RGBA", (self.poster_width, self.poster_height), (0, 0, 0, 255)
        )

        # Apply background
        if background_mode == "image" and video_base and video_path:
            poster = self._apply_frame_background(
                poster, video_base, video_path, timestamp, selection_coords, blur
            )
        elif background_mode == "gradient" and gradient_colors:
            poster = self._apply_gradient_background(
                poster, gradient_colors, gradient_direction
            )
        else:
            poster = self._apply_solid_background(poster, background_color)

        # Convert to RGB for drawing
        poster = poster.convert("RGBA")
        draw = ImageDraw.Draw(poster)

        # Calculate scale factors from canvas to poster
        scale_x = self.poster_width / canvas_width
        scale_y = self.poster_height / canvas_height

        # Apply line elements
        for line_elem in line_elements:
            self._render_line(draw, line_elem, scale_x)

        # Apply text layers
        for text_layer in text_layers:
            self._render_text(poster, draw, text_layer, scale_x, scale_y)

        # Convert to RGB for final output
        if poster.mode == "RGBA":
            background = Image.new("RGB", poster.size, (0, 0, 0))
            background.paste(poster, mask=poster.split()[3])
            poster = background

        # Save poster
        safe_filename = "".join(c for c in filename if c.isalnum() or c in ("_", "-"))
        if not safe_filename:
            safe_filename = "poster"

        output_file = self.output_path / f"{safe_filename}.png"

        # Handle duplicate filenames
        counter = 1
        while output_file.exists():
            output_file = self.output_path / f"{safe_filename}_{counter}.png"
            counter += 1

        poster.save(output_file, "PNG", quality=95)

        return str(output_file.name)

    def _apply_frame_background(
        self,
        poster: Image.Image,
        video_base: str,
        video_path: str,
        timestamp: float,
        selection_coords: Dict[str, float],
        blur: float,
    ) -> Image.Image:
        """Extract video frame and crop to selection area."""
        full_path = Path(video_base) / video_path

        frame_data = extract_frame_high_quality(str(full_path), timestamp)
        if not frame_data:
            return poster

        frame = Image.open(io.BytesIO(frame_data))

        # Calculate crop region from normalized selection coordinates
        crop_left = int(selection_coords.get("left", 0) * frame.width)
        crop_top = int(selection_coords.get("top", 0) * frame.height)
        crop_width = int(selection_coords.get("width", 1) * frame.width)
        crop_height = int(selection_coords.get("height", 1) * frame.height)

        # Ensure crop region is within bounds
        crop_left = max(0, min(crop_left, frame.width - 1))
        crop_top = max(0, min(crop_top, frame.height - 1))
        crop_right = min(crop_left + crop_width, frame.width)
        crop_bottom = min(crop_top + crop_height, frame.height)

        # Crop to selection region
        cropped = frame.crop((crop_left, crop_top, crop_right, crop_bottom))

        # Apply blur if specified (after scaling to match preview appearance)
        # Scale cropped region to poster dimensions first
        cropped = cropped.resize((self.poster_width, self.poster_height), Image.LANCZOS)

        if blur > 0:
            # Match the preview blur appearance
            # Preview uses Fabric.js blur filter with blur/50, which roughly maps to blur * 0.5 pixels at preview scale
            # Since poster is 2.5x larger than preview (1000 vs 400), scale the blur accordingly
            blur_radius = blur * 1.25  # Adjusted to match preview visually
            cropped = cropped.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        # Paste onto poster
        if cropped.mode == "RGBA":
            poster.paste(cropped, (0, 0), cropped)
        else:
            poster.paste(cropped, (0, 0))

        return poster

    def _apply_gradient_background(
        self, poster: Image.Image, colors: List[str], direction: str
    ) -> Image.Image:
        """Create gradient background."""
        draw = ImageDraw.Draw(poster)

        from_color = self._hex_to_rgb(colors[0])
        to_color = self._hex_to_rgb(colors[1])

        if direction == "horizontal":
            for x in range(self.poster_width):
                ratio = x / self.poster_width
                r = int(from_color[0] + (to_color[0] - from_color[0]) * ratio)
                g = int(from_color[1] + (to_color[1] - from_color[1]) * ratio)
                b = int(from_color[2] + (to_color[2] - from_color[2]) * ratio)
                draw.line([(x, 0), (x, self.poster_height)], fill=(r, g, b, 255))
        elif direction == "diagonal":
            for i in range(self.poster_width + self.poster_height):
                ratio = i / (self.poster_width + self.poster_height)
                r = int(from_color[0] + (to_color[0] - from_color[0]) * ratio)
                g = int(from_color[1] + (to_color[1] - from_color[1]) * ratio)
                b = int(from_color[2] + (to_color[2] - from_color[2]) * ratio)

                # Draw diagonal line
                x1 = max(0, i - self.poster_height)
                y1 = min(i, self.poster_height)
                x2 = min(i, self.poster_width)
                y2 = max(0, i - self.poster_width)
                draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 255))
        else:  # vertical
            for y in range(self.poster_height):
                ratio = y / self.poster_height
                r = int(from_color[0] + (to_color[0] - from_color[0]) * ratio)
                g = int(from_color[1] + (to_color[1] - from_color[1]) * ratio)
                b = int(from_color[2] + (to_color[2] - from_color[2]) * ratio)
                draw.line([(0, y), (self.poster_width, y)], fill=(r, g, b, 255))

        return poster

    def _apply_solid_background(self, poster: Image.Image, color: str) -> Image.Image:
        """Fill with solid color."""
        rgb = self._hex_to_rgb(color)
        return Image.new("RGBA", (self.poster_width, self.poster_height), (*rgb, 255))

    def _render_line(self, draw: ImageDraw.Draw, line_config: Dict, scale_x: float):
        """Render a line element onto the poster."""
        # x1, y1, x2, y2 are normalized (0-1) absolute positions from frontend
        x1 = int(line_config.get("x1", 0) * self.poster_width)
        y1 = int(line_config.get("y1", 0) * self.poster_height)
        x2 = int(line_config.get("x2", 0) * self.poster_width)
        y2 = int(line_config.get("y2", 0) * self.poster_height)

        stroke = line_config.get("stroke", "#ffffff")
        stroke_width = int(line_config.get("strokeWidth", 2) * scale_x)

        draw.line([(x1, y1), (x2, y2)], fill=stroke, width=max(1, stroke_width))

    def _render_text(
        self,
        poster: Image.Image,
        draw: ImageDraw.Draw,
        text_config: Dict,
        scale_x: float,
        scale_y: float,
    ):
        """Render a text layer onto the poster with multi-line and alignment support."""
        # Bounding box coordinates (normalized 0-1, from Fabric.js getBoundingRect())
        # These represent the TRUE top-left corner of the text bounding box
        bbox_left = int(text_config["left"] * self.poster_width)
        bbox_top = int(text_config["top"] * self.poster_height)

        # Bounding box dimensions (normalized 0-1)
        bbox_width = int(text_config.get("width", 0.5) * self.poster_width)

        # Font size scaled from canvas to poster dimensions
        font_size = int(
            text_config.get("fontSize", 32) * scale_y * text_config.get("scaleY", 1)
        )

        # Load font
        font = self._get_font(
            text_config.get("fontFamily", "Arial"),
            font_size,
            text_config.get("fontWeight") == "bold",
            text_config.get("fontStyle") == "italic",
        )

        # Text content and alignment
        text = text_config.get("content", "")
        fill = text_config.get("fill", "#ffffff")
        text_align = text_config.get("textAlign", "center")

        # Split text into lines
        lines = text.split("\n")

        # Calculate line height (roughly 1.2x font size)
        line_height = int(font_size * 1.2)

        # Draw each line
        # The frontend now calculates the actual text position based on alignment,
        # so bbox_left is where the actual text content starts (not the textbox container)
        for i, line in enumerate(lines):
            if not line.strip():
                continue  # Skip empty lines but keep spacing

            line_y = bbox_top + (i * line_height)

            # Get line width for multi-line alignment
            text_bbox_result = draw.textbbox((0, 0), line, font=font)
            line_width = text_bbox_result[2] - text_bbox_result[0]

            # For multi-line text with varying line widths, align within the text block
            if text_align == "left":
                line_x = bbox_left
            elif text_align == "right":
                line_x = bbox_left + bbox_width - line_width
            else:  # center
                line_x = bbox_left + (bbox_width - line_width) // 2

            # Draw text at calculated position
            draw.text((line_x, line_y), line, font=font, fill=fill)

            # Apply underline if needed
            if text_config.get("underline") and line.strip():
                underline_y = line_y + font_size + 2
                draw.line(
                    [(line_x, underline_y), (line_x + line_width, underline_y)],
                    fill=fill,
                    width=max(1, font_size // 16),
                )

    def _get_font(
        self, family: str, size: int, bold: bool = False, italic: bool = False
    ) -> ImageFont.FreeTypeFont:
        """Load font with fallback to default."""
        # Build font variant suffix
        suffix = ""
        if bold and italic:
            suffix = "-BoldItalic"
        elif bold:
            suffix = "-Bold"
        elif italic:
            suffix = "-Italic"

        # Build list of font paths to try (in priority order)
        font_paths = [
            # Custom fonts with variant
            self.fonts_path / f"{family}{suffix}.ttf",
            self.fonts_path / f"{family}{suffix}.otf",
            # Custom fonts without variant
            self.fonts_path / f"{family}.ttf",
            self.fonts_path / f"{family}.otf",
            # System fonts
            Path(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix or ''}.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ]

        for font_path in font_paths:
            if font_path.exists():
                try:
                    return ImageFont.truetype(str(font_path), size)
                except OSError:
                    continue

        # Final fallback to PIL default
        return ImageFont.load_default()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


poster_service = PosterService()
