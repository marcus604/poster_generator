import subprocess
import json
from typing import Optional, Dict, Any


def get_video_info(video_path: str) -> Optional[Dict[str, Any]]:
    """Extract video metadata using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        video_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            video_stream = next(
                (s for s in data.get("streams", []) if s["codec_type"] == "video"), None
            )
            if video_stream:
                # Parse frame rate (can be "24/1" or "24000/1001" format)
                fps_str = video_stream.get("r_frame_rate", "24/1")
                try:
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        fps = float(num) / float(den)
                    else:
                        fps = float(fps_str)
                except (ValueError, ZeroDivisionError):
                    fps = 24.0

                duration = float(data["format"].get("duration", 0))
                return {
                    "duration": duration,
                    "width": video_stream.get("width"),
                    "height": video_stream.get("height"),
                    "fps": round(fps, 3),
                    "total_frames": int(duration * fps),
                    "codec": video_stream.get("codec_name"),
                    "size": int(data["format"].get("size", 0)),
                }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        pass
    return None


def extract_frame(
    video_path: str, timestamp: float, width: Optional[int] = None, quality: int = 85
) -> Optional[bytes]:
    """
    Extract a frame using two-pass seek for accuracy.
    First seek gets close quickly, second seek is precise.
    """
    # Two-pass seek: fast seek to 1 second before, then precise seek
    fast_seek = max(0, timestamp - 1.0)
    precise_seek = timestamp - fast_seek

    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-ss",
        str(fast_seek),  # Fast seek (before input)
        "-i",
        video_path,
        "-ss",
        str(precise_seek),  # Precise seek (after input)
        "-frames:v",
        "1",
        "-q:v",
        str(max(1, min(31, (100 - quality) // 3))),  # Quality (1-31, lower is better)
    ]

    # Scale if width specified
    if width:
        cmd.extend(["-vf", f"scale={width}:-1"])

    cmd.extend(["-f", "image2pipe", "-vcodec", "mjpeg", "-y", "pipe:1"])

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except subprocess.TimeoutExpired:
        pass

    return None


def extract_frame_high_quality(video_path: str, timestamp: float) -> Optional[bytes]:
    """Extract a high-quality PNG frame for final poster generation."""
    fast_seek = max(0, timestamp - 1.0)
    precise_seek = timestamp - fast_seek

    cmd = [
        "ffmpeg",
        "-ss",
        str(fast_seek),
        "-i",
        video_path,
        "-ss",
        str(precise_seek),
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "-y",
        "pipe:1",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except subprocess.TimeoutExpired:
        pass

    return None
