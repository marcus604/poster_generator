import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.poster_service import poster_service

logger = logging.getLogger(__name__)

router = APIRouter()


class TextLayer(BaseModel):
    content: str
    left: float  # Bounding box left (normalized 0-1)
    top: float   # Bounding box top (normalized 0-1)
    fontFamily: str = "Arial"
    fontSize: int = 32
    fill: str = "#ffffff"
    fontWeight: str = "normal"
    fontStyle: str = "normal"
    underline: bool = False
    textAlign: str = "center"
    angle: float = 0
    scaleX: float = 1
    scaleY: float = 1
    width: Optional[float] = None   # Bounding box width (normalized 0-1)
    height: Optional[float] = None  # Bounding box height (normalized 0-1)


class LineElement(BaseModel):
    x1: float  # Normalized (0-1) absolute X position of first endpoint
    y1: float  # Normalized (0-1) absolute Y position of first endpoint
    x2: float  # Normalized (0-1) absolute X position of second endpoint
    y2: float  # Normalized (0-1) absolute Y position of second endpoint
    stroke: str = "#ffffff"
    strokeWidth: float = 2  # Already scaled from frontend


class PosterGenerateRequest(BaseModel):
    backgroundMode: str
    backgroundColor: str = "#000000"
    gradientColors: List[str] = ["#000000", "#333333"]
    gradientDirection: str = "vertical"
    videoBase: Optional[str] = None
    videoPath: Optional[str] = None
    timestamp: float = 0
    selectionCoords: Dict[str, float] = {"left": 0, "top": 0, "width": 1, "height": 1}
    blur: float = 0
    canvasWidth: float = 400
    canvasHeight: float = 600
    textLayers: List[TextLayer] = []
    lineElements: List[LineElement] = []
    filename: str


@router.post("/generate")
async def generate_poster(request: PosterGenerateRequest):
    """Generate and save a poster based on the provided configuration."""
    try:
        output_filename = poster_service.generate_poster(
            background_mode=request.backgroundMode,
            background_color=request.backgroundColor,
            gradient_colors=request.gradientColors,
            gradient_direction=request.gradientDirection,
            video_base=request.videoBase,
            video_path=request.videoPath,
            timestamp=request.timestamp,
            selection_coords=request.selectionCoords,
            blur=request.blur,
            canvas_width=request.canvasWidth,
            canvas_height=request.canvasHeight,
            text_layers=[layer.model_dump() for layer in request.textLayers],
            line_elements=[elem.model_dump() for elem in request.lineElements],
            filename=request.filename
        )

        return {
            "success": True,
            "filename": output_filename,
            "message": f"Poster saved as {output_filename}"
        }

    except Exception as e:
        logger.exception("Error generating poster")
        raise HTTPException(status_code=500, detail=str(e))
