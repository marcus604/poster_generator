from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from typing import List
import base64

from app.services.video_service import video_service
from app.services.frame_service import frame_service

router = APIRouter()


@router.get("/preview")
async def get_preview_frame(
    base: str = Query(..., description="Base path identifier"),
    path: str = Query(..., description="Video file path"),
    t: float = Query(..., description="Timestamp in seconds", ge=0)
):
    """Get a preview-quality frame at the specified timestamp."""
    video_path = video_service.get_full_path(base, path)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    frame_data = frame_service.get_preview_frame(str(video_path), t)
    if not frame_data:
        raise HTTPException(status_code=500, detail="Failed to extract frame")

    return Response(content=frame_data, media_type="image/jpeg")


@router.get("/full")
async def get_full_frame(
    base: str = Query(..., description="Base path identifier"),
    path: str = Query(..., description="Video file path"),
    t: float = Query(..., description="Timestamp in seconds", ge=0)
):
    """Get a full-quality frame for poster generation."""
    video_path = video_service.get_full_path(base, path)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    frame_data = frame_service.get_full_frame(str(video_path), t)
    if not frame_data:
        raise HTTPException(status_code=500, detail="Failed to extract frame")

    return Response(content=frame_data, media_type="image/png")


@router.get("/thumbnails")
async def get_thumbnails(
    base: str = Query(..., description="Base path identifier"),
    path: str = Query(..., description="Video file path"),
    count: int = Query(20, description="Number of thumbnails", ge=1, le=100)
):
    """Get evenly-spaced thumbnail frames for the slider preview."""
    video_path = video_service.get_full_path(base, path)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")

    # Get video duration
    info = video_service.get_video_info(base, path)
    if not info or info.get('duration', 0) <= 0:
        raise HTTPException(status_code=400, detail="Could not determine video duration")

    thumbnails = frame_service.get_thumbnails(str(video_path), info['duration'], count)

    # Return as base64 encoded list for easy frontend consumption
    return {
        "count": len(thumbnails),
        "duration": info['duration'],
        "thumbnails": [base64.b64encode(t).decode('utf-8') for t in thumbnails]
    }
