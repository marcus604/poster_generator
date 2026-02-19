"""Unit tests for FrameService - caching and thumbnail logic."""
import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def make_service(tmp_path):
    """Create a FrameService with a temp cache dir, bypassing the singleton."""
    from app.services.frame_service import FrameService
    svc = FrameService.__new__(FrameService)
    svc.cache_dir = tmp_path / "cache"
    svc.cache_dir.mkdir(parents=True, exist_ok=True)
    svc.max_cache_bytes = 500 * 1024 * 1024  # 500MB default
    svc.preview_width = 640
    svc.thumbnail_quality = 85
    return svc


FAKE_JPEG = b"\xff\xd8\xff" + b"\x00" * 50  # minimal JPEG-like bytes


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_same_inputs_produce_same_key(self, tmp_path):
        svc = make_service(tmp_path)
        k1 = svc._cache_key("/video.mp4", 5.0, 640, 85)
        k2 = svc._cache_key("/video.mp4", 5.0, 640, 85)
        assert k1 == k2

    def test_different_timestamps_produce_different_keys(self, tmp_path):
        svc = make_service(tmp_path)
        k1 = svc._cache_key("/video.mp4", 5.0, 640, 85)
        k2 = svc._cache_key("/video.mp4", 5.001, 640, 85)
        assert k1 != k2

    def test_different_paths_produce_different_keys(self, tmp_path):
        svc = make_service(tmp_path)
        k1 = svc._cache_key("/a.mp4", 5.0, 640, 85)
        k2 = svc._cache_key("/b.mp4", 5.0, 640, 85)
        assert k1 != k2

    def test_different_widths_produce_different_keys(self, tmp_path):
        svc = make_service(tmp_path)
        k1 = svc._cache_key("/video.mp4", 5.0, 640, 85)
        k2 = svc._cache_key("/video.mp4", 5.0, 320, 85)
        assert k1 != k2

    def test_key_is_a_hex_string(self, tmp_path):
        svc = make_service(tmp_path)
        key = svc._cache_key("/video.mp4", 5.0, 640, 85)
        # MD5 hex = 32 chars
        assert len(key) == 32
        assert all(c in "0123456789abcdef" for c in key)


# ---------------------------------------------------------------------------
# get_preview_frame - caching behaviour
# ---------------------------------------------------------------------------

class TestGetPreviewFrame:
    def test_returns_frame_data_on_success(self, tmp_path):
        svc = make_service(tmp_path)
        with patch("app.services.frame_service.extract_frame", return_value=FAKE_JPEG):
            result = svc.get_preview_frame("/fake/video.mp4", 5.0)
        assert result == FAKE_JPEG

    def test_caches_result_on_disk(self, tmp_path):
        svc = make_service(tmp_path)
        with patch("app.services.frame_service.extract_frame", return_value=FAKE_JPEG):
            svc.get_preview_frame("/fake/video.mp4", 5.0)
        cache_files = list(svc.cache_dir.glob("*.jpg"))
        assert len(cache_files) == 1
        assert cache_files[0].read_bytes() == FAKE_JPEG

    def test_second_call_hits_cache_not_ffmpeg(self, tmp_path):
        svc = make_service(tmp_path)
        with patch("app.services.frame_service.extract_frame", return_value=FAKE_JPEG) as mock_extract:
            svc.get_preview_frame("/fake/video.mp4", 5.0)
            svc.get_preview_frame("/fake/video.mp4", 5.0)
        assert mock_extract.call_count == 1  # ffmpeg called only once

    def test_second_call_returns_same_data(self, tmp_path):
        svc = make_service(tmp_path)
        with patch("app.services.frame_service.extract_frame", return_value=FAKE_JPEG):
            r1 = svc.get_preview_frame("/fake/video.mp4", 5.0)
            r2 = svc.get_preview_frame("/fake/video.mp4", 5.0)
        assert r1 == r2

    def test_returns_none_when_ffmpeg_fails(self, tmp_path):
        svc = make_service(tmp_path)
        with patch("app.services.frame_service.extract_frame", return_value=None):
            result = svc.get_preview_frame("/fake/video.mp4", 5.0)
        assert result is None

    def test_no_cache_file_written_on_failure(self, tmp_path):
        svc = make_service(tmp_path)
        with patch("app.services.frame_service.extract_frame", return_value=None):
            svc.get_preview_frame("/fake/video.mp4", 5.0)
        assert list(svc.cache_dir.glob("*.jpg")) == []

    def test_different_timestamps_cached_separately(self, tmp_path):
        svc = make_service(tmp_path)
        with patch("app.services.frame_service.extract_frame", return_value=FAKE_JPEG) as mock_extract:
            svc.get_preview_frame("/fake/video.mp4", 1.0)
            svc.get_preview_frame("/fake/video.mp4", 2.0)
        assert mock_extract.call_count == 2
        assert len(list(svc.cache_dir.glob("*.jpg"))) == 2


# ---------------------------------------------------------------------------
# _enforce_cache_limit
# ---------------------------------------------------------------------------

class TestEnforceCacheLimit:
    def test_deletes_oldest_file_when_over_limit(self, tmp_path):
        svc = make_service(tmp_path)
        svc.max_cache_bytes = 150  # tiny limit

        # Create files with ascending mtime: old (mtime=0), new (mtime=2)
        old_file = svc.cache_dir / "old.jpg"
        new_file = svc.cache_dir / "new.jpg"
        old_file.write_bytes(b"x" * 100)
        new_file.write_bytes(b"x" * 100)
        os.utime(old_file, (0, 0))
        os.utime(new_file, (2, 2))

        svc._enforce_cache_limit()

        assert not old_file.exists()
        assert new_file.exists()

    def test_does_not_delete_when_under_limit(self, tmp_path):
        svc = make_service(tmp_path)
        svc.max_cache_bytes = 10_000  # generous limit

        f = svc.cache_dir / "keep.jpg"
        f.write_bytes(b"x" * 100)

        svc._enforce_cache_limit()

        assert f.exists()

    def test_handles_empty_cache_dir_gracefully(self, tmp_path):
        svc = make_service(tmp_path)
        svc.max_cache_bytes = 1  # force eviction attempt
        svc._enforce_cache_limit()  # should not raise


# ---------------------------------------------------------------------------
# get_thumbnails
# ---------------------------------------------------------------------------

class TestGetThumbnails:
    def test_returns_empty_list_for_zero_duration(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.get_thumbnails("/fake.mp4", duration=0, count=20)
        assert result == []

    def test_returns_empty_list_for_negative_duration(self, tmp_path):
        svc = make_service(tmp_path)
        result = svc.get_thumbnails("/fake.mp4", duration=-1, count=20)
        assert result == []

    def test_calls_preview_frame_count_times(self, tmp_path):
        svc = make_service(tmp_path)
        with patch.object(svc, "get_preview_frame", return_value=FAKE_JPEG) as mock:
            svc.get_thumbnails("/fake.mp4", duration=10.0, count=5)
        assert mock.call_count == 5

    def test_evenly_spaced_timestamps(self, tmp_path):
        svc = make_service(tmp_path)
        called_timestamps = []
        def capture_call(path, ts):
            called_timestamps.append(ts)
            return FAKE_JPEG
        with patch.object(svc, "get_preview_frame", side_effect=capture_call):
            svc.get_thumbnails("/fake.mp4", duration=10.0, count=5)
        assert called_timestamps == pytest.approx([0.0, 2.0, 4.0, 6.0, 8.0])

    def test_skips_failed_frames(self, tmp_path):
        svc = make_service(tmp_path)
        # Return None for every other frame
        responses = [FAKE_JPEG, None, FAKE_JPEG, None, FAKE_JPEG]
        with patch.object(svc, "get_preview_frame", side_effect=responses):
            result = svc.get_thumbnails("/fake.mp4", duration=10.0, count=5)
        assert len(result) == 3

    def test_returns_bytes_list(self, tmp_path):
        svc = make_service(tmp_path)
        with patch.object(svc, "get_preview_frame", return_value=FAKE_JPEG):
            result = svc.get_thumbnails("/fake.mp4", duration=5.0, count=3)
        assert all(isinstance(r, bytes) for r in result)


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------

class TestClearCache:
    def test_removes_all_jpg_files(self, tmp_path):
        svc = make_service(tmp_path)
        (svc.cache_dir / "a.jpg").write_bytes(b"data")
        (svc.cache_dir / "b.jpg").write_bytes(b"data")
        svc.clear_cache()
        assert list(svc.cache_dir.glob("*.jpg")) == []

    def test_does_not_raise_on_empty_cache(self, tmp_path):
        svc = make_service(tmp_path)
        svc.clear_cache()  # should not raise
