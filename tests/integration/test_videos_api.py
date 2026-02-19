"""Integration tests for /api/videos routes."""
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_health_endpoint_returns_healthy(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_videos_returns_200(client):
    with patch("app.api.routes.videos.video_service") as mock_svc:
        mock_svc.list_videos.return_value = []
        response = await client.get("/api/videos")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_videos_returns_items(client):
    fake_videos = [
        {"name": "movie.mp4", "type": "video", "path": "movie.mp4", "base": "/videos", "size": 1000}
    ]
    with patch("app.api.routes.videos.video_service") as mock_svc:
        mock_svc.list_videos.return_value = fake_videos
        response = await client.get("/api/videos")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "movie.mp4"


@pytest.mark.asyncio
async def test_list_videos_passes_path_param(client):
    with patch("app.api.routes.videos.video_service") as mock_svc:
        mock_svc.list_videos.return_value = []
        await client.get("/api/videos?path=movies/action")
    mock_svc.list_videos.assert_called_once_with("movies/action")


@pytest.mark.asyncio
async def test_get_video_info_returns_data(client):
    fake_info = {"name": "movie.mp4", "duration": 120.0, "width": 1920, "height": 1080}
    with patch("app.api.routes.videos.video_service") as mock_svc:
        mock_svc.get_video_info.return_value = fake_info
        response = await client.get("/api/videos/info?base=/videos&path=movie.mp4")
    assert response.status_code == 200
    assert response.json()["duration"] == 120.0


@pytest.mark.asyncio
async def test_get_video_info_returns_404_when_not_found(client):
    with patch("app.api.routes.videos.video_service") as mock_svc:
        mock_svc.get_video_info.return_value = None
        response = await client.get("/api/videos/info?base=/videos&path=missing.mp4")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_video_info_requires_base_param(client):
    response = await client.get("/api/videos/info?path=movie.mp4")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_video_info_requires_path_param(client):
    response = await client.get("/api/videos/info?base=/videos")
    assert response.status_code == 422
