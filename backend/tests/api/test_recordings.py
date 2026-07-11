from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from steno10k.api import create_app
from steno10k.api.routers import recordings as recordings_router


def _client(tmp_path: Path) -> TestClient:
    c = TestClient(create_app(data_root=tmp_path))
    c.post("/api/v1/projects", json={"title": "Law"})
    c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
    return c


def test_upload_and_list_recordings(tmp_path: Path) -> None:
    c = _client(tmp_path)
    files = [("files", ("lecture.m4a", b"fake-audio-bytes", "audio/mp4"))]
    r = c.post("/api/v1/projects/law/sets/week-1/recordings", files=files)
    assert r.status_code == 200
    assert r.json()["data"][0]["source_name"] == "lecture.m4a"
    assert r.json()["data"][0]["normalized_name"] == "lecture.m4a"

    r = c.get("/api/v1/projects/law/sets/week-1/recordings")
    assert len(r.json()["data"]) == 1

    # the uploaded bytes actually landed on disk under the set dir
    assert (tmp_path / "law" / "week-1" / "lecture.m4a").read_bytes() == b"fake-audio-bytes"


def test_upload_normalizes_and_dedupes_names(tmp_path: Path) -> None:
    c = _client(tmp_path)
    files = [("files", ("My Lecture!!.m4a", b"one", "audio/mp4"))]
    r = c.post("/api/v1/projects/law/sets/week-1/recordings", files=files)
    assert r.json()["data"][0]["normalized_name"] == "my-lecture.m4a"

    files2 = [("files", ("My Lecture!!.m4a", b"two", "audio/mp4"))]
    r2 = c.post("/api/v1/projects/law/sets/week-1/recordings", files=files2)
    assert r2.json()["data"][0]["normalized_name"] == "my-lecture_2.m4a"


def test_upload_rejects_unsupported_extension(tmp_path: Path) -> None:
    c = _client(tmp_path)
    files = [("files", ("notes.txt", b"hello", "text/plain"))]
    r = c.post("/api/v1/projects/law/sets/week-1/recordings", files=files)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unsupported_type"


def test_upload_rejects_oversize_file_without_buffering(
    tmp_path: Path, monkeypatch: object
) -> None:
    import pytest

    mp = monkeypatch
    assert isinstance(mp, pytest.MonkeyPatch)
    # Shrink the cap + chunk size so the test doesn't need to move real gigabytes.
    mp.setattr(recordings_router, "_MAX_FILE_BYTES", 10)
    mp.setattr(recordings_router, "_READ_CHUNK_BYTES", 4)

    c = _client(tmp_path)
    files = [("files", ("lecture.m4a", b"x" * 11, "audio/mp4"))]
    r = c.post("/api/v1/projects/law/sets/week-1/recordings", files=files)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "file_too_large"
    # rejected file must not be left behind on disk
    assert not (tmp_path / "law" / "week-1" / "lecture.m4a").exists()


def test_upload_mixed_multi_file_rolls_back_orphans_on_failure(
    tmp_path: Path, monkeypatch: object
) -> None:
    import pytest

    mp = monkeypatch
    assert isinstance(mp, pytest.MonkeyPatch)
    # Shrink the cap + chunk size so the test doesn't need to move real gigabytes.
    mp.setattr(recordings_router, "_MAX_FILE_BYTES", 10)
    mp.setattr(recordings_router, "_READ_CHUNK_BYTES", 4)

    c = _client(tmp_path)
    files = [
        ("files", ("first.m4a", b"small", "audio/mp4")),
        ("files", ("second.m4a", b"x" * 11, "audio/mp4")),
    ]
    r = c.post("/api/v1/projects/law/sets/week-1/recordings", files=files)
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "file_too_large"

    set_dir = tmp_path / "law" / "week-1"
    # no orphan recording files left behind from the earlier, successfully-written
    # entry (manifest.json is pre-existing set metadata, not a recording)
    assert not (set_dir / "first.m4a").exists()
    assert not (set_dir / "second.m4a").exists()
    assert [p.name for p in set_dir.iterdir()] == ["manifest.json"]

    r = c.get("/api/v1/projects/law/sets/week-1/recordings")
    assert r.json()["data"] == []


def test_upload_missing_set_returns_404(tmp_path: Path) -> None:
    c = _client(tmp_path)
    files = [("files", ("lecture.m4a", b"data", "audio/mp4"))]
    r = c.post("/api/v1/projects/law/sets/nope/recordings", files=files)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "set_not_found"


def test_delete_recording(tmp_path: Path) -> None:
    c = _client(tmp_path)
    files = [("files", ("lecture.m4a", b"data", "audio/mp4"))]
    c.post("/api/v1/projects/law/sets/week-1/recordings", files=files)

    r = c.delete("/api/v1/projects/law/sets/week-1/recordings/lecture.m4a")
    assert r.status_code == 200

    r = c.get("/api/v1/projects/law/sets/week-1/recordings")
    assert r.json()["data"] == []
    assert not (tmp_path / "law" / "week-1" / "lecture.m4a").exists()


def test_delete_missing_recording_returns_404(tmp_path: Path) -> None:
    c = _client(tmp_path)
    r = c.delete("/api/v1/projects/law/sets/week-1/recordings/nope.m4a")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "recording_not_found"
