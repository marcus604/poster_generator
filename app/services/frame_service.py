import hashlib
from pathlib import Path
from typing import Optional, List
from app.config import settings
from app.utils.ffmpeg_utils import extract_frame, extract_frame_high_quality


class FrameService:
    def __init__(self):
        self.cache_dir = Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_cache_bytes = settings.max_cache_size_mb * 1024 * 1024
        self.preview_width = settings.preview_max_width
        self.thumbnail_quality = settings.thumbnail_quality

    def get_preview_frame(self, video_path: str, timestamp: float) -> Optional[bytes]:
        """Get a preview-quality frame (cached)."""
        cache_key = self._cache_key(video_path, timestamp, self.preview_width, self.thumbnail_quality)
        cache_path = self.cache_dir / f"{cache_key}.jpg"

        # Return cached if exists
        if cache_path.exists():
            return cache_path.read_bytes()

        # Extract frame
        frame_data = extract_frame(
            video_path,
            timestamp,
            width=self.preview_width,
            quality=self.thumbnail_quality
        )

        if frame_data:
            # Cache the result
            cache_path.write_bytes(frame_data)
            self._enforce_cache_limit()
            return frame_data

        return None

    def get_full_frame(self, video_path: str, timestamp: float) -> Optional[bytes]:
        """Get a full-quality frame (not cached due to size)."""
        return extract_frame_high_quality(video_path, timestamp)

    def get_thumbnails(self, video_path: str, duration: float, count: int = 20) -> List[bytes]:
        """Generate evenly-spaced thumbnail frames for the slider."""
        thumbnails = []
        if duration <= 0 or count <= 0:
            return thumbnails

        interval = duration / count
        for i in range(count):
            timestamp = i * interval
            frame = self.get_preview_frame(video_path, timestamp)
            if frame:
                thumbnails.append(frame)

        return thumbnails

    def _cache_key(self, video_path: str, timestamp: float, width: int, quality: int) -> str:
        """Generate cache key for a frame."""
        key_str = f"{video_path}:{timestamp:.3f}:{width}:{quality}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _enforce_cache_limit(self):
        """Remove oldest cached frames if cache exceeds limit."""
        try:
            files = sorted(
                self.cache_dir.glob("*.jpg"),
                key=lambda p: p.stat().st_mtime
            )
            total_size = sum(f.stat().st_size for f in files)

            while total_size > self.max_cache_bytes and files:
                oldest = files.pop(0)
                total_size -= oldest.stat().st_size
                oldest.unlink()
        except (OSError, IOError):
            pass

    def clear_cache(self):
        """Clear all cached frames."""
        try:
            for f in self.cache_dir.glob("*.jpg"):
                f.unlink()
        except (OSError, IOError):
            pass


frame_service = FrameService()
