"""Integration tests for /api/posters/generate route."""
import pytest
from unittest.mock import patch

SOLID_REQUEST = {
    "backgroundMode": "solid",
    "backgroundColor": "#ff0000",
    "filename": "test_poster",
    "canvasWidth": 400,
    "canvasHeight": 600,
}


@pytest.mark.asyncio
async def test_generate_poster_returns_200(client):
    with patch("app.api.routes.posters.poster_service") as mock_svc:
        mock_svc.generate_poster.return_value = "/output/test_poster.png"
        response = await client.post("/api/posters/generate", json=SOLID_REQUEST)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "test_poster.png" in data["filename"]


@pytest.mark.asyncio
async def test_generate_poster_missing_filename_fails_validation(client):
    request = {k: v for k, v in SOLID_REQUEST.items() if k != "filename"}
    response = await client.post("/api/posters/generate", json=request)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_poster_missing_background_mode_fails_validation(client):
    request = {k: v for k, v in SOLID_REQUEST.items() if k != "backgroundMode"}
    response = await client.post("/api/posters/generate", json=request)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generate_poster_returns_500_on_service_exception(client):
    with patch("app.api.routes.posters.poster_service") as mock_svc:
        mock_svc.generate_poster.side_effect = RuntimeError("disk full")
        response = await client.post("/api/posters/generate", json=SOLID_REQUEST)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_generate_poster_passes_text_layers_to_service(client):
    with patch("app.api.routes.posters.poster_service") as mock_svc:
        mock_svc.generate_poster.return_value = "/output/test.png"
        request = {
            **SOLID_REQUEST,
            "textLayers": [{
                "content": "MOVIE TITLE",
                "left": 0.1,
                "top": 0.7,
            }]
        }
        await client.post("/api/posters/generate", json=request)

    call_kwargs = mock_svc.generate_poster.call_args.kwargs
    assert len(call_kwargs["text_layers"]) == 1
    assert call_kwargs["text_layers"][0]["content"] == "MOVIE TITLE"


@pytest.mark.asyncio
async def test_generate_poster_passes_line_elements_to_service(client):
    with patch("app.api.routes.posters.poster_service") as mock_svc:
        mock_svc.generate_poster.return_value = "/output/test.png"
        request = {
            **SOLID_REQUEST,
            "lineElements": [{
                "x1": 0.05, "y1": 0.1, "x2": 0.05, "y2": 0.9,
                "stroke": "#ffffff", "strokeWidth": 2
            }]
        }
        await client.post("/api/posters/generate", json=request)

    call_kwargs = mock_svc.generate_poster.call_args.kwargs
    assert len(call_kwargs["line_elements"]) == 1
    assert call_kwargs["line_elements"][0]["stroke"] == "#ffffff"


@pytest.mark.asyncio
async def test_generate_poster_with_gradient_background(client):
    with patch("app.api.routes.posters.poster_service") as mock_svc:
        mock_svc.generate_poster.return_value = "/output/gradient.png"
        request = {
            **SOLID_REQUEST,
            "backgroundMode": "gradient",
            "gradientColors": ["#000000", "#ffffff"],
            "gradientDirection": "vertical",
        }
        response = await client.post("/api/posters/generate", json=request)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_generate_poster_with_video_background(client):
    with patch("app.api.routes.posters.poster_service") as mock_svc:
        mock_svc.generate_poster.return_value = "/videos/movie.png"
        request = {
            **SOLID_REQUEST,
            "backgroundMode": "image",
            "videoBase": "/videos",
            "videoPath": "movie.mp4",
            "timestamp": 30.0,
            "selectionCoords": {"left": 0.1, "top": 0.0, "width": 0.5, "height": 1.0},
        }
        response = await client.post("/api/posters/generate", json=request)
    assert response.status_code == 200
    call_kwargs = mock_svc.generate_poster.call_args.kwargs
    assert call_kwargs["video_base"] == "/videos"
    assert call_kwargs["video_path"] == "movie.mp4"
    assert call_kwargs["timestamp"] == 30.0
