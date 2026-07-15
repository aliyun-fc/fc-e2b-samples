from fastapi.testclient import TestClient

from src.main import create_app


def test_health():
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_create_run_and_receive_initial_sse_event():
    with TestClient(create_app()) as client:
        response = client.post("/api/runs", json={"task": "打开 https://example.com 并截图"})
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "queued"
        assert body["events_url"].endswith("/events")
        with client.stream("GET", body["events_url"]) as stream:
            first_chunk = next(stream.iter_text())
        assert "event: run.queued" in first_chunk


def test_missing_run_is_404():
    with TestClient(create_app()) as client:
        assert client.get("/api/runs/nope").status_code == 404
