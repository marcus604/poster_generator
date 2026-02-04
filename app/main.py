from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.routes import videos, frames, posters
from app.config import settings

app = FastAPI(
    title="Plex Poster Generator",
    description="Generate custom posters from video frames",
    version="1.0.0"
)

# Include API routes
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(frames.router, prefix="/api/frames", tags=["frames"])
app.include_router(posters.router, prefix="/api/posters", tags=["posters"])

# Serve static files
static_path = Path(__file__).parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def root():
    """Serve the main application page."""
    return FileResponse(static_path / "index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "video_paths": len(settings.video_paths_list)}
