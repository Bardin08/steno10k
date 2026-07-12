from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from steno10k.api import create_app


def test_enqueue_and_stream(tmp_path: Path) -> None:
    with TestClient(create_app(data_root=tmp_path)) as c:
        c.post("/api/v1/projects", json={"title": "Law"})
        c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
        r = c.post("/api/v1/runs", json={"project": "law", "set": "week-1"})
        assert r.status_code == 200
        run_id = r.json()["data"]["id"]

        # SSE: read the stream until run_completed appears
        with c.stream("GET", f"/api/v1/runs/{run_id}/events") as s:
            body = ""
            for line in s.iter_lines():
                body += line + "\n"
                if "run_completed" in line:
                    break
        assert "run_completed" in body


def test_list_and_get_run(tmp_path: Path) -> None:
    with TestClient(create_app(data_root=tmp_path)) as c:
        c.post("/api/v1/projects", json={"title": "Law"})
        c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
        r = c.post("/api/v1/runs", json={"project": "law", "set": "week-1"})
        run_id = r.json()["data"]["id"]

        r = c.get("/api/v1/runs")
        assert r.status_code == 200
        assert any(run["id"] == run_id for run in r.json()["data"])

        r = c.get(f"/api/v1/runs/{run_id}")
        assert r.status_code == 200
        assert r.json()["data"]["id"] == run_id
        assert r.json()["data"]["project"] == "law"
        assert r.json()["data"]["set_"] == "week-1"


def test_get_missing_run_404(tmp_path: Path) -> None:
    with TestClient(create_app(data_root=tmp_path)) as c:
        r = c.get("/api/v1/runs/nope")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "run_not_found"


def test_cancel_run(tmp_path: Path) -> None:
    with TestClient(create_app(data_root=tmp_path)) as c:
        c.post("/api/v1/projects", json={"title": "Law"})
        c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
        r = c.post("/api/v1/runs", json={"project": "law", "set": "week-1"})
        run_id = r.json()["data"]["id"]

        r = c.delete(f"/api/v1/runs/{run_id}")
        assert r.status_code == 200


def test_cancel_missing_run_404(tmp_path: Path) -> None:
    with TestClient(create_app(data_root=tmp_path)) as c:
        r = c.delete("/api/v1/runs/nope")
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "run_not_found"


def test_create_run_threads_force(tmp_path: Path) -> None:
    from steno10k.api import create_app  # noqa: F811 (explicit for readability)

    with TestClient(create_app(data_root=tmp_path)) as c:
        c.post("/api/v1/projects", json={"title": "Law"})
        c.post("/api/v1/projects/law/sets", json={"title": "Week 1"})
        run_id = c.post(
            "/api/v1/runs",
            json={"project": "law", "set": "week-1", "force": True},
        ).json()["data"]["id"]

        rq = c.app.state.run_queue  # type: ignore[attr-defined]
        assert rq.get(run_id).force is True
