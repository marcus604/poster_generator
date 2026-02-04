from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import settings
from app.utils.ffmpeg_utils import get_video_info


class VideoService:
    def __init__(self):
        self.video_extensions = set(settings.video_extensions)

    def list_videos(self, path: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all video files from configured paths."""
        videos = []

        for base_path in settings.video_paths_list:
            if path:
                # Browse specific subdirectory
                search_path = base_path / path
                if not search_path.exists() or not search_path.is_dir():
                    continue
            else:
                search_path = base_path

            videos.extend(self._scan_directory(search_path, base_path))

        # Sort by name
        videos.sort(key=lambda x: x['name'].lower())
        return videos

    def _scan_directory(self, dir_path: Path, base_path: Path) -> List[Dict[str, Any]]:
        """Scan a directory for video files and subdirectories."""
        items = []

        if not dir_path.is_dir():
            return items

        try:
            for item in dir_path.iterdir():
                if item.is_dir():
                    # Check if directory contains any videos
                    has_videos = any(
                        f.suffix.lower() in self.video_extensions
                        for f in item.rglob('*') if f.is_file()
                    )
                    if has_videos:
                        items.append({
                            'name': item.name,
                            'path': str(item.relative_to(base_path)),
                            'type': 'directory',
                            'base': str(base_path)
                        })
                elif item.is_file() and item.suffix.lower() in self.video_extensions:
                    items.append({
                        'name': item.name,
                        'path': str(item.relative_to(base_path)),
                        'type': 'video',
                        'base': str(base_path),
                        'size': item.stat().st_size
                    })
        except PermissionError:
            pass

        return items

    def get_video_info(self, base: str, path: str) -> Optional[Dict[str, Any]]:
        """Get detailed video metadata."""
        video_path = Path(base) / path
        if not video_path.exists() or not video_path.is_file():
            return None

        info = get_video_info(str(video_path))
        if info:
            info['name'] = video_path.name
            info['path'] = path
            info['base'] = base
            info['full_path'] = str(video_path)
        return info

    def get_full_path(self, base: str, path: str) -> Optional[Path]:
        """Get full path to a video file."""
        video_path = Path(base) / path
        if video_path.exists() and video_path.is_file():
            return video_path
        return None


video_service = VideoService()
