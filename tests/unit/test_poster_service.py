"""Unit tests for PosterService - image generation logic."""
import io
import pytest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_service(tmp_path):
    """Create a PosterService instance pointing at tmp_path for output."""
    from app.services.poster_service import PosterService
    svc = PosterService.__new__(PosterService)
    svc.output_path = tmp_path
    svc.poster_width = 100
    svc.poster_height = 150
    svc.fonts_path = Path("/nonexistent/fonts")  # force PIL default font
    return svc


def make_png_bytes(width=100, height=150, color=(255, 0, 0)):
    """Create a PNG image and return its bytes."""
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


SOLID_POSTER_ARGS = dict(
    background_mode="solid",
    background_color="#ff0000",
    gradient_colors=["#000000", "#ffffff"],
    gradient_direction="vertical",
    video_base=None,
    video_path=None,
    timestamp=0,
    selection_coords={"left": 0, "top": 0, "width": 1, "height": 1},
    blur=0,
    canvas_width=400,
    canvas_height=600,
    text_layers=[],
    line_elements=[],
    filename="test_poster",
)


# ---------------------------------------------------------------------------
# _hex_to_rgb
# ---------------------------------------------------------------------------

class TestHexToRgb:
    def test_standard_six_char_red(self, tmp_path):
        svc = make_service(tmp_path)
        assert svc._hex_to_rgb("#ff0000") == (255, 0, 0)

    def test_standard_six_char_black(self, tmp_path):
        svc = make_service(tmp_path)
        assert svc._hex_to_rgb("#000000") == (0, 0, 0)

    def test_standard_six_char_white(self, tmp_path):
        svc = make_service(tmp_path)
        assert svc._hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_shorthand_three_char(self, tmp_path):
        svc = make_service(tmp_path)
        assert svc._hex_to_rgb("#f00") == (255, 0, 0)

    def test_shorthand_three_char_white(self, tmp_path):
        svc = make_service(tmp_path)
        assert svc._hex_to_rgb("#fff") == (255, 255, 255)

    def test_mixed_color(self, tmp_path):
        svc = make_service(tmp_path)
        r, g, b = svc._hex_to_rgb("#1a2b3c")
        assert r == 0x1a
        assert g == 0x2b
        assert b == 0x3c


# ---------------------------------------------------------------------------
# _apply_solid_background
# ---------------------------------------------------------------------------

class TestApplySolidBackground:
    def test_fills_with_correct_color(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        result = svc._apply_solid_background(poster, "#00ff00")
        pixel = result.getpixel((50, 75))
        assert pixel[:3] == (0, 255, 0)

    def test_returns_correct_size(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150))
        result = svc._apply_solid_background(poster, "#ffffff")
        assert result.size == (100, 150)


# ---------------------------------------------------------------------------
# _apply_gradient_background
# ---------------------------------------------------------------------------

class TestApplyGradientBackground:
    def test_vertical_top_near_from_color(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150))
        result = svc._apply_gradient_background(poster, ["#000000", "#ffffff"], "vertical")
        top_pixel = result.getpixel((50, 0))[:3]
        assert top_pixel[0] < 10  # near black

    def test_vertical_bottom_near_to_color(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150))
        result = svc._apply_gradient_background(poster, ["#000000", "#ffffff"], "vertical")
        bottom_pixel = result.getpixel((50, 149))[:3]
        assert bottom_pixel[0] > 240  # near white

    def test_horizontal_left_near_from_color(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150))
        result = svc._apply_gradient_background(poster, ["#000000", "#ffffff"], "horizontal")
        left_pixel = result.getpixel((0, 75))[:3]
        assert left_pixel[0] < 10

    def test_horizontal_right_near_to_color(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150))
        result = svc._apply_gradient_background(poster, ["#000000", "#ffffff"], "horizontal")
        right_pixel = result.getpixel((99, 75))[:3]
        assert right_pixel[0] > 240

    def test_diagonal_does_not_raise(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150))
        result = svc._apply_gradient_background(poster, ["#ff0000", "#0000ff"], "diagonal")
        assert result.size == (100, 150)

    def test_returns_correct_size(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150))
        result = svc._apply_gradient_background(poster, ["#000000", "#ffffff"], "vertical")
        assert result.size == (100, 150)


# ---------------------------------------------------------------------------
# _render_line
# ---------------------------------------------------------------------------

class TestRenderLine:
    def test_horizontal_line_draws_white_pixels(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        line_config = {"x1": 0.0, "y1": 0.5, "x2": 1.0, "y2": 0.5, "stroke": "#ffffff", "strokeWidth": 2}
        svc._render_line(draw, line_config, scale_x=1.0)
        # Midpoint of the horizontal line should be white
        pixel = poster.getpixel((50, 75))
        assert pixel[:3] == (255, 255, 255)

    def test_vertical_line_does_not_raise(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        line_config = {"x1": 0.1, "y1": 0.0, "x2": 0.1, "y2": 1.0, "stroke": "#ff0000", "strokeWidth": 2}
        svc._render_line(draw, line_config, scale_x=1.0)

    def test_uses_stroke_color(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        line_config = {"x1": 0.0, "y1": 0.5, "x2": 1.0, "y2": 0.5, "stroke": "#ff0000", "strokeWidth": 4}
        svc._render_line(draw, line_config, scale_x=1.0)
        pixel = poster.getpixel((50, 75))
        assert pixel[0] > 200  # red channel dominant


# ---------------------------------------------------------------------------
# _render_text
# ---------------------------------------------------------------------------

class TestRenderText:
    def _base_text_config(self, **overrides):
        config = {
            "content": "TEST",
            "left": 0.05,
            "top": 0.05,
            "fontSize": 12,
            "fill": "#ffffff",
            "textAlign": "left",
            "fontFamily": "Arial",
            "fontWeight": "normal",
            "fontStyle": "normal",
            "underline": False,
            "scaleY": 1.0,
            "width": 0.9,
        }
        config.update(overrides)
        return config

    def test_does_not_raise_left_aligned(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        svc._render_text(poster, draw, self._base_text_config(textAlign="left"), 1.0, 1.0)

    def test_does_not_raise_center_aligned(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        svc._render_text(poster, draw, self._base_text_config(textAlign="center"), 1.0, 1.0)

    def test_does_not_raise_right_aligned(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        svc._render_text(poster, draw, self._base_text_config(textAlign="right"), 1.0, 1.0)

    def test_does_not_raise_with_underline(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        svc._render_text(poster, draw, self._base_text_config(underline=True), 1.0, 1.0)

    def test_does_not_raise_multiline(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        svc._render_text(poster, draw, self._base_text_config(content="LINE1\nLINE2"), 1.0, 1.0)

    def test_empty_lines_skipped_without_error(self, tmp_path):
        svc = make_service(tmp_path)
        poster = Image.new("RGBA", (100, 150), (0, 0, 0, 255))
        draw = ImageDraw.Draw(poster)
        svc._render_text(poster, draw, self._base_text_config(content="\n\nTEXT"), 1.0, 1.0)


# ---------------------------------------------------------------------------
# generate_poster - solid/gradient (no ffmpeg)
# ---------------------------------------------------------------------------

class TestGeneratePoster:
    def test_solid_background_creates_png_file(self, tmp_path):
        svc = make_service(tmp_path)
        output = svc.generate_poster(**SOLID_POSTER_ARGS)
        assert Path(output).exists()
        assert output.endswith(".png")

    def test_solid_background_correct_dimensions(self, tmp_path):
        svc = make_service(tmp_path)
        output = svc.generate_poster(**SOLID_POSTER_ARGS)
        img = Image.open(output)
        assert img.size == (100, 150)

    def test_gradient_background_creates_file(self, tmp_path):
        svc = make_service(tmp_path)
        args = {**SOLID_POSTER_ARGS, "background_mode": "gradient",
                "gradient_colors": ["#000000", "#ffffff"], "gradient_direction": "vertical"}
        output = svc.generate_poster(**args)
        assert Path(output).exists()

    def test_duplicate_filename_increments_counter(self, tmp_path):
        svc = make_service(tmp_path)
        # Create the first poster normally
        out1 = svc.generate_poster(**SOLID_POSTER_ARGS)
        assert Path(out1).exists()
        # Second poster with same filename should get _1 suffix
        out2 = svc.generate_poster(**SOLID_POSTER_ARGS)
        assert Path(out2).exists()
        assert out1 != out2
        assert "_1" in Path(out2).name

    def test_third_duplicate_gets_counter_2(self, tmp_path):
        svc = make_service(tmp_path)
        svc.generate_poster(**SOLID_POSTER_ARGS)
        svc.generate_poster(**SOLID_POSTER_ARGS)
        out3 = svc.generate_poster(**SOLID_POSTER_ARGS)
        assert "_2" in Path(out3).name

    def test_unsafe_filename_chars_stripped(self, tmp_path):
        svc = make_service(tmp_path)
        args = {**SOLID_POSTER_ARGS, "filename": "my poster!! (2024)", "video_base": None, "video_path": None}
        output = svc.generate_poster(**args)
        assert Path(output).exists()
        # No spaces or special chars in filename
        assert " " not in Path(output).name
        assert "!" not in Path(output).name

    def test_empty_filename_falls_back_to_poster(self, tmp_path):
        svc = make_service(tmp_path)
        args = {**SOLID_POSTER_ARGS, "filename": "!!!"}
        output = svc.generate_poster(**args)
        assert "poster" in Path(output).name

    def test_with_text_layer_does_not_raise(self, tmp_path):
        svc = make_service(tmp_path)
        args = {**SOLID_POSTER_ARGS, "text_layers": [{
            "content": "MOVIE TITLE",
            "left": 0.05, "top": 0.7,
            "fontSize": 12, "fill": "#ffffff",
            "textAlign": "left", "fontFamily": "Arial",
            "fontWeight": "normal", "fontStyle": "normal",
            "underline": False, "scaleY": 1.0, "width": 0.9,
        }]}
        output = svc.generate_poster(**args)
        assert Path(output).exists()

    def test_with_line_element_does_not_raise(self, tmp_path):
        svc = make_service(tmp_path)
        args = {**SOLID_POSTER_ARGS, "line_elements": [{
            "x1": 0.05, "y1": 0.1, "x2": 0.05, "y2": 0.9,
            "stroke": "#ffffff", "strokeWidth": 2,
        }]}
        output = svc.generate_poster(**args)
        assert Path(output).exists()

    def test_saves_next_to_video_when_video_provided(self, tmp_path):
        """When video_base/video_path are given, poster saves in the video's directory."""
        svc = make_service(tmp_path)
        video_dir = tmp_path / "mymovies"
        video_dir.mkdir()
        (video_dir / "movie.mp4").touch()

        with patch("app.services.poster_service.extract_frame_high_quality") as mock_extract:
            mock_extract.return_value = make_png_bytes()
            args = {**SOLID_POSTER_ARGS,
                    "background_mode": "image",
                    "video_base": str(video_dir),
                    "video_path": "movie.mp4"}
            output = svc.generate_poster(**args)

        assert Path(output).parent == video_dir
        assert Path(output).stem == "movie"

    def test_frame_background_falls_back_gracefully_when_ffmpeg_fails(self, tmp_path):
        """If ffmpeg fails, generate_poster should still produce a black PNG."""
        svc = make_service(tmp_path)
        video_dir = tmp_path / "vids"
        video_dir.mkdir()
        (video_dir / "film.mp4").touch()

        with patch("app.services.poster_service.extract_frame_high_quality", return_value=None):
            args = {**SOLID_POSTER_ARGS,
                    "background_mode": "image",
                    "video_base": str(video_dir),
                    "video_path": "film.mp4"}
            output = svc.generate_poster(**args)

        assert Path(output).exists()
        img = Image.open(output)
        assert img.size == (100, 150)
