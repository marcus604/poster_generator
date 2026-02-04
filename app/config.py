from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    video_paths: str = "/videos/source1,/videos/source2,/videos/source3"
    output_path: str = "/output"
    cache_dir: str = "/tmp/poster_cache"
    max_cache_size_mb: int = 500
    preview_max_width: int = 640
    thumbnail_quality: int = 85

    # Poster dimensions (Plex standard)
    poster_width: int = 1000
    poster_height: int = 1500

    # Supported video extensions
    video_extensions: List[str] = [
        ".mp4",
        ".mkv",
        ".avi",
        ".mov",
        ".webm",
        ".m4v",
        ".wmv",
        ".flv",
    ]

    @property
    def video_paths_list(self) -> List[Path]:
        """Parse comma-separated video paths into list of Path objects."""
        paths = []
        for p in self.video_paths.split(","):
            p = p.strip()
            if p and p != "/dev/null":
                path = Path(p)
                if path.exists():
                    paths.append(path)
        return paths

    class Config:
        env_file = ".env"


settings = Settings()
