from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.services.video_service import video_service

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
async def list_videos(
    path: Optional[str] = Query(None, description="Subdirectory path to browse"),
):
    """List video files and directories."""
    return video_service.list_videos(path)


@router.get("/info")
async def get_video_info(
    base: str = Query(..., description="Base path identifier"),
    path: str = Query(..., description="Video file path relative to base"),
):
    """Get video metadata including duration, resolution, and fps."""
    info = video_service.get_video_info(base, path)
    if not info:
        raise HTTPException(status_code=404, detail="Video not found")
    return info
