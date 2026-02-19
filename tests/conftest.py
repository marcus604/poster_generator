"""Shared fixtures for all tests."""
import io
import pytest
from PIL import Image
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Async client for integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
async def client():
    """Async HTTP client wired to the FastAPI app."""
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# In-memory image helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_jpeg_bytes():
    """A real 1x1 red JPEG in memory - no file needed."""
    img = Image.new("RGB", (100, 150), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def minimal_png_bytes():
    """A real 100x150 blue PNG in memory."""
    img = Image.new("RGB", (100, 150), color=(0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# ffprobe subprocess mock helpers
# ---------------------------------------------------------------------------

FAKE_FFPROBE_DATA = {
    "streams": [
        {
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "24/1",
        }
    ],
    "format": {
        "duration": "120.0",
        "size": "1000000",
    },
}


@pytest.fixture
def mock_ffprobe_success():
    """Patch subprocess.run so ffprobe returns valid video metadata."""
    import json
    with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
        result = MagicMock()
        result.returncode = 0
        result.stdout = json.dumps(FAKE_FFPROBE_DATA)
        mock_run.return_value = result
        yield mock_run


@pytest.fixture
def mock_ffprobe_failure():
    """Patch subprocess.run so ffprobe returns a non-zero exit code."""
    with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
        result = MagicMock()
        result.returncode = 1
        result.stdout = ""
        mock_run.return_value = result
        yield mock_run


# ---------------------------------------------------------------------------
# Service-level mocks for integration tests
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_video_service():
    with patch("app.api.routes.videos.video_service") as mock, \
         patch("app.api.routes.frames.video_service", mock), \
         patch("app.api.routes.posters.poster_service") as _:
        mock.list_videos.return_value = []
        mock.get_video_info.return_value = None
        mock.get_full_path.return_value = None
        yield mock


@pytest.fixture
def mock_frame_service():
    with patch("app.api.routes.frames.frame_service") as mock:
        mock.get_preview_frame.return_value = None
        mock.get_full_frame.return_value = None
        mock.get_thumbnails.return_value = []
        yield mock


@pytest.fixture
def mock_poster_service():
    with patch("app.api.routes.posters.poster_service") as mock:
        mock.generate_poster.return_value = "/output/test_poster.png"
        yield mock
