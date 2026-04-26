import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-no-demo-seed.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    import backend.app.main as main
    importlib.reload(main)
    return TestClient(main.app)


def _signup(client: TestClient):
    response = client.post(
        "/auth/signup",
        json={
            "email": "no-demo-seed@example.com",
            "password": "HermesTest123!",
            "display_name": "No Demo Seed",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["session_token"]


def test_fresh_database_does_not_seed_demo_platform_or_community_rows(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        token = _signup(client)
        headers = {"Authorization": f"Bearer {token}"}

        assert client.get("/community").json()["posts"] == []
        assert client.get("/agents", headers=headers).json()["agents"] == []
        assert client.get("/deployments", headers=headers).json()["deployments"] == []
        assert client.get("/workflows", headers=headers).json()["workflows"] == []
        assert client.get("/tasks", headers=headers).json()["tasks"] == []
        assert client.get("/outputs", headers=headers).json()["outputs"] == []
