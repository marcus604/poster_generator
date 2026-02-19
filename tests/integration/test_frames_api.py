"""Integration tests for /api/frames routes."""
import base64
import pytest
from pathlib import Path
from unittest.mock import patch

FAKE_JPEG = b"\xff\xd8\xff" + b"\x00" * 50


@pytest.mark.asyncio
async def test_preview_frame_returns_jpeg(client):
    with patch("app.api.routes.frames.video_service") as mock_vs, \
         patch("app.api.routes.frames.frame_service") as mock_fs:
        mock_vs.get_full_path.return_value = Path("/fake/movie.mp4")
        mock_fs.get_preview_frame.return_value = FAKE_JPEG
        response = await client.get("/api/frames/preview?base=/videos&path=movie.mp4&t=5.0")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content == FAKE_JPEG


@pytest.mark.asyncio
async def test_preview_frame_404_when_video_not_found(client):
    with patch("app.api.routes.frames.video_service") as mock_vs:
        mock_vs.get_full_path.return_value = None
        response = await client.get("/api/frames/preview?base=/videos&path=missing.mp4&t=5.0")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_frame_500_when_ffmpeg_fails(client):
    with patch("app.api.routes.frames.video_service") as mock_vs, \
         patch("app.api.routes.frames.frame_service") as mock_fs:
        mock_vs.get_full_path.return_value = Path("/fake/movie.mp4")
        mock_fs.get_preview_frame.return_value = None
        response = await client.get("/api/frames/preview?base=/videos&path=movie.mp4&t=5.0")
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_preview_frame_rejects_negative_timestamp(client):
    response = await client.get("/api/frames/preview?base=/videos&path=movie.mp4&t=-1")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_preview_frame_requires_all_params(client):
    # Missing t
    response = await client.get("/api/frames/preview?base=/videos&path=movie.mp4")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_full_frame_returns_png(client):
    fake_png = b"\x89PNG" + b"\x00" * 50
    with patch("app.api.routes.frames.video_service") as mock_vs, \
         patch("app.api.routes.frames.frame_service") as mock_fs:
        mock_vs.get_full_path.return_value = Path("/fake/movie.mp4")
        mock_fs.get_full_frame.return_value = fake_png
        response = await client.get("/api/frames/full?base=/videos&path=movie.mp4&t=5.0")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_full_frame_404_when_video_not_found(client):
    with patch("app.api.routes.frames.video_service") as mock_vs:
        mock_vs.get_full_path.return_value = None
        response = await client.get("/api/frames/full?base=/videos&path=missing.mp4&t=5.0")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_thumbnails_returns_base64_list(client):
    frames = [b"frame1", b"frame2", b"frame3"]
    with patch("app.api.routes.frames.video_service") as mock_vs, \
         patch("app.api.routes.frames.frame_service") as mock_fs:
        mock_vs.get_full_path.return_value = Path("/fake/movie.mp4")
        mock_vs.get_video_info.return_value = {"duration": 10.0}
        mock_fs.get_thumbnails.return_value = frames
        response = await client.get("/api/frames/thumbnails?base=/videos&path=movie.mp4&count=3")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 3
    assert len(data["thumbnails"]) == 3
    assert base64.b64decode(data["thumbnails"][0]) == b"frame1"


@pytest.mark.asyncio
async def test_thumbnails_404_when_video_not_found(client):
    with patch("app.api.routes.frames.video_service") as mock_vs:
        mock_vs.get_full_path.return_value = None
        response = await client.get("/api/frames/thumbnails?base=/videos&path=missing.mp4")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_thumbnails_400_when_video_info_unavailable(client):
    with patch("app.api.routes.frames.video_service") as mock_vs:
        mock_vs.get_full_path.return_value = Path("/fake/movie.mp4")
        mock_vs.get_video_info.return_value = None
        response = await client.get("/api/frames/thumbnails?base=/videos&path=movie.mp4")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_thumbnails_rejects_count_over_100(client):
    response = await client.get("/api/frames/thumbnails?base=/videos&path=movie.mp4&count=101")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_thumbnails_rejects_count_zero(client):
    response = await client.get("/api/frames/thumbnails?base=/videos&path=movie.mp4&count=0")
    assert response.status_code == 422
