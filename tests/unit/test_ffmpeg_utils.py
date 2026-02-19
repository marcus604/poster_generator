"""Unit tests for ffmpeg_utils - the subprocess boundary."""
import json
import subprocess
import pytest
from unittest.mock import patch, MagicMock

from app.utils.ffmpeg_utils import get_video_info, extract_frame, extract_frame_high_quality


FAKE_FFPROBE_DATA = {
    "streams": [
        {
            "codec_type": "video",
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "24/1",
        }
    ],
    "format": {
        "duration": "120.0",
        "size": "1000000",
    },
}


def make_subprocess_result(returncode=0, stdout="", stdout_bytes=None):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout_bytes if stdout_bytes is not None else stdout
    return result


# ---------------------------------------------------------------------------
# get_video_info
# ---------------------------------------------------------------------------

class TestGetVideoInfo:
    def test_returns_parsed_metadata_on_success(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout=json.dumps(FAKE_FFPROBE_DATA))
            result = get_video_info("/fake/video.mp4")

        assert result is not None
        assert result["duration"] == 120.0
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["fps"] == 24.0
        assert result["codec"] == "h264"
        assert result["total_frames"] == 2880
        assert result["size"] == 1_000_000

    def test_returns_none_on_nonzero_exit_code(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(returncode=1)
            result = get_video_info("/fake/video.mp4")
        assert result is None

    def test_returns_none_on_timeout(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("ffprobe", 30)):
            result = get_video_info("/fake/video.mp4")
        assert result is None

    def test_returns_none_on_json_decode_error(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout="not valid json")
            result = get_video_info("/fake/video.mp4")
        assert result is None

    def test_returns_none_when_no_video_stream(self):
        data = {
            "streams": [{"codec_type": "audio"}],
            "format": {"duration": "60.0", "size": "500000"},
        }
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout=json.dumps(data))
            result = get_video_info("/fake/video.mp4")
        assert result is None

    def test_parses_fractional_fps_correctly(self):
        data = {**FAKE_FFPROBE_DATA}
        data["streams"] = [{**data["streams"][0], "r_frame_rate": "24000/1001"}]
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout=json.dumps(data))
            result = get_video_info("/fake/video.mp4")
        assert result is not None
        assert abs(result["fps"] - 23.976) < 0.001

    def test_falls_back_to_24fps_on_bad_fps_string(self):
        data = {**FAKE_FFPROBE_DATA}
        data["streams"] = [{**data["streams"][0], "r_frame_rate": "invalid"}]
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout=json.dumps(data))
            result = get_video_info("/fake/video.mp4")
        assert result["fps"] == 24.0

    def test_calls_ffprobe_with_correct_flags(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout=json.dumps(FAKE_FFPROBE_DATA))
            get_video_info("/fake/video.mp4")
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffprobe"
        assert "-show_format" in cmd
        assert "-show_streams" in cmd
        assert "/fake/video.mp4" in cmd


# ---------------------------------------------------------------------------
# extract_frame
# ---------------------------------------------------------------------------

class TestExtractFrame:
    def test_returns_bytes_on_success(self):
        fake_frame = b"\xff\xd8\xff" + b"\x00" * 50
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=fake_frame)
            result = extract_frame("/fake/video.mp4", 5.0)
        assert result == fake_frame

    def test_returns_none_on_nonzero_exit(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(returncode=1, stdout_bytes=b"")
            result = extract_frame("/fake/video.mp4", 5.0)
        assert result is None

    def test_returns_none_on_empty_output(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(returncode=0, stdout_bytes=b"")
            result = extract_frame("/fake/video.mp4", 5.0)
        assert result is None

    def test_returns_none_on_timeout(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("ffmpeg", 30)):
            result = extract_frame("/fake/video.mp4", 5.0)
        assert result is None

    def test_two_pass_seek_does_not_use_negative_fast_seek(self):
        """At timestamp 0, fast_seek should be 0 (not negative)."""
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=b"frame")
            extract_frame("/fake/video.mp4", 0.0)
        cmd = mock_run.call_args[0][0]
        # First -ss is the fast seek, should be >= 0
        first_ss_index = cmd.index("-ss")
        assert float(cmd[first_ss_index + 1]) >= 0.0

    def test_two_pass_seek_fast_seek_is_1_second_before(self):
        """At timestamp 5.0, fast_seek should be 4.0."""
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=b"frame")
            extract_frame("/fake/video.mp4", 5.0)
        cmd = mock_run.call_args[0][0]
        first_ss_index = cmd.index("-ss")
        assert float(cmd[first_ss_index + 1]) == 4.0

    def test_includes_scale_filter_when_width_provided(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=b"frame")
            extract_frame("/fake/video.mp4", 5.0, width=640)
        cmd = mock_run.call_args[0][0]
        assert "-vf" in cmd
        assert "scale=640:-1" in cmd

    def test_no_scale_filter_when_width_not_provided(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=b"frame")
            extract_frame("/fake/video.mp4", 5.0)
        cmd = mock_run.call_args[0][0]
        assert "-vf" not in cmd

    def test_outputs_mjpeg_format(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=b"frame")
            extract_frame("/fake/video.mp4", 5.0)
        cmd = mock_run.call_args[0][0]
        assert "mjpeg" in cmd


# ---------------------------------------------------------------------------
# extract_frame_high_quality
# ---------------------------------------------------------------------------

class TestExtractFrameHighQuality:
    def test_returns_bytes_on_success(self):
        fake_png = b"\x89PNG" + b"\x00" * 50
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=fake_png)
            result = extract_frame_high_quality("/fake/video.mp4", 5.0)
        assert result == fake_png

    def test_returns_none_on_failure(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(returncode=1, stdout_bytes=b"")
            result = extract_frame_high_quality("/fake/video.mp4", 5.0)
        assert result is None

    def test_returns_none_on_timeout(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("ffmpeg", 60)):
            result = extract_frame_high_quality("/fake/video.mp4", 5.0)
        assert result is None

    def test_outputs_png_codec(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=b"frame")
            extract_frame_high_quality("/fake/video.mp4", 5.0)
        cmd = mock_run.call_args[0][0]
        assert "png" in cmd

    def test_two_pass_seek_does_not_use_negative_fast_seek(self):
        with patch("app.utils.ffmpeg_utils.subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result(stdout_bytes=b"frame")
            extract_frame_high_quality("/fake/video.mp4", 0.0)
        cmd = mock_run.call_args[0][0]
        first_ss_index = cmd.index("-ss")
        assert float(cmd[first_ss_index + 1]) >= 0.0
