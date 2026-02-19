"""Unit tests for VideoService - filesystem scanning and metadata."""
import pytest
from pathlib import Path
from unittest.mock import patch


def make_service():
    from app.services.video_service import VideoService
    return VideoService()


# ---------------------------------------------------------------------------
# get_full_path
# ---------------------------------------------------------------------------

class TestGetFullPath:
    def test_returns_path_for_existing_file(self, tmp_path):
        svc = make_service()
        (tmp_path / "movie.mp4").touch()
        result = svc.get_full_path(str(tmp_path), "movie.mp4")
        assert result == tmp_path / "movie.mp4"

    def test_returns_none_for_missing_file(self, tmp_path):
        svc = make_service()
        result = svc.get_full_path(str(tmp_path), "missing.mp4")
        assert result is None

    def test_returns_none_for_directory(self, tmp_path):
        svc = make_service()
        (tmp_path / "subdir").mkdir()
        result = svc.get_full_path(str(tmp_path), "subdir")
        assert result is None


# ---------------------------------------------------------------------------
# get_video_info
# ---------------------------------------------------------------------------

class TestGetVideoInfo:
    def test_returns_none_for_missing_file(self, tmp_path):
        svc = make_service()
        result = svc.get_video_info(str(tmp_path), "nonexistent.mp4")
        assert result is None

    def test_returns_enriched_info_on_success(self, tmp_path):
        (tmp_path / "movie.mp4").touch()
        fake_info = {"duration": 120.0, "width": 1920, "height": 1080, "fps": 24.0}

        svc = make_service()
        with patch("app.services.video_service.get_video_info", return_value=fake_info):
            result = svc.get_video_info(str(tmp_path), "movie.mp4")

        assert result["name"] == "movie.mp4"
        assert result["path"] == "movie.mp4"
        assert result["base"] == str(tmp_path)
        assert result["full_path"] == str(tmp_path / "movie.mp4")
        assert result["duration"] == 120.0

    def test_returns_none_when_ffmpeg_returns_none(self, tmp_path):
        (tmp_path / "movie.mp4").touch()
        svc = make_service()
        with patch("app.services.video_service.get_video_info", return_value=None):
            result = svc.get_video_info(str(tmp_path), "movie.mp4")
        assert result is None


# ---------------------------------------------------------------------------
# list_videos / _scan_directory
# ---------------------------------------------------------------------------

class TestListVideos:
    def test_returns_video_files_in_directory(self, tmp_path, monkeypatch):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "movie.mp4").touch()
        (video_dir / "clip.mkv").touch()

        monkeypatch.setattr("app.config.settings.video_paths", str(video_dir))
        svc = make_service()
        result = svc.list_videos()

        names = [r["name"] for r in result]
        assert "movie.mp4" in names
        assert "clip.mkv" in names

    def test_ignores_non_video_files(self, tmp_path, monkeypatch):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "movie.mp4").touch()
        (video_dir / "readme.txt").touch()
        (video_dir / "image.jpg").touch()

        monkeypatch.setattr("app.config.settings.video_paths", str(video_dir))
        svc = make_service()
        result = svc.list_videos()

        names = [r["name"] for r in result]
        assert "readme.txt" not in names
        assert "image.jpg" not in names
        assert "movie.mp4" in names

    def test_results_sorted_by_name_case_insensitive(self, tmp_path, monkeypatch):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "Zebra.mp4").touch()
        (video_dir / "apple.mp4").touch()
        (video_dir / "Mango.mkv").touch()

        monkeypatch.setattr("app.config.settings.video_paths", str(video_dir))
        svc = make_service()
        result = svc.list_videos()

        names = [r["name"] for r in result]
        assert names == sorted(names, key=str.lower)

    def test_includes_directory_that_has_videos(self, tmp_path, monkeypatch):
        video_dir = tmp_path / "videos"
        subdir = video_dir / "series"
        subdir.mkdir(parents=True)
        (subdir / "episode1.mp4").touch()

        monkeypatch.setattr("app.config.settings.video_paths", str(video_dir))
        svc = make_service()
        result = svc.list_videos()

        types = [r["type"] for r in result]
        assert "directory" in types

    def test_excludes_empty_directory(self, tmp_path, monkeypatch):
        video_dir = tmp_path / "videos"
        empty_dir = video_dir / "empty"
        empty_dir.mkdir(parents=True)

        monkeypatch.setattr("app.config.settings.video_paths", str(video_dir))
        svc = make_service()
        result = svc.list_videos()

        names = [r["name"] for r in result]
        assert "empty" not in names

    def test_each_item_has_required_keys(self, tmp_path, monkeypatch):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "movie.mp4").touch()

        monkeypatch.setattr("app.config.settings.video_paths", str(video_dir))
        svc = make_service()
        result = svc.list_videos()

        assert len(result) == 1
        item = result[0]
        assert "name" in item
        assert "path" in item
        assert "type" in item
        assert "base" in item

    def test_video_item_includes_size(self, tmp_path, monkeypatch):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        f = video_dir / "movie.mp4"
        f.write_bytes(b"x" * 1000)

        monkeypatch.setattr("app.config.settings.video_paths", str(video_dir))
        svc = make_service()
        result = svc.list_videos()

        video_items = [r for r in result if r["type"] == "video"]
        assert video_items[0]["size"] == 1000

    def test_returns_empty_when_no_video_paths_configured(self, monkeypatch):
        # Point video_paths at a non-existent path so video_paths_list is empty
        monkeypatch.setattr("app.config.settings.video_paths", "/dev/null/nonexistent")
        svc = make_service()
        result = svc.list_videos()
        assert result == []
