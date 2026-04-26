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


def test_legacy_demo_rows_are_removed_on_startup(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        token = _signup(client)
        headers = {"Authorization": f"Bearer {token}"}

        import backend.app.db.session as session

        with session.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO agents(agent_id, name, category, description, status, tasks_completed, success_rate, created_at, updated_at)
                VALUES('agt_research_alpha', 'Research Alpha', 'Research', 'Analyzing market trends', 'active', 156, 98.5, datetime('now'), datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO deployments(deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent, requests_per_day, created_at, updated_at)
                VALUES('dep_prod', 'Production Cluster', 'production', 'running', 'US East', 12, 45, 62, 2400000, datetime('now'), datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO workflows(workflow_id, name, status, runs_total, success_rate, updated_at)
                VALUES('wf_market_scan', 'Market Scan', 'active', 120, 98.0, datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO tasks(task_id, title, status, priority, assigned_to, updated_at)
                VALUES('tsk_001', 'Analyze token velocity', 'queued', 'high', 'agt_research_alpha', datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO outputs(output_id, title, output_type, size_bytes, download_url, created_at)
                VALUES('out_001', 'Weekly market report', 'report', 184320, '/downloads/out_001', datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO community_posts(post_id, author_user_id, title, body, likes, created_at)
                VALUES('post_001', 'creator_alpha', 'How I scaled my agent', 'Playbook for scaling automation.', 32, datetime('now'))
                """
            )
            conn.commit()

        session.init_db()

        assert client.get("/community").json()["posts"] == []
        assert client.get("/agents", headers=headers).json()["agents"] == []
        assert client.get("/deployments", headers=headers).json()["deployments"] == []
        assert client.get("/workflows", headers=headers).json()["workflows"] == []
        assert client.get("/tasks", headers=headers).json()["tasks"] == []
        assert client.get("/outputs", headers=headers).json()["outputs"] == []
