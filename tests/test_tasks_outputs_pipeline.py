import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-tasks-pipeline.db"

    import backend.app.db.session as session
    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main
    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _signup(client: TestClient, email: str = "tasks-owner@example.com"):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "HermesTest123!", "display_name": "Task Owner"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_create_task_requires_auth(client: TestClient):
    response = client.post(
        "/tasks",
        json={"title": "Unauthenticated task", "type": "analysis", "agent_id": "agt_test"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_create_task_stores_real_job_fields(client: TestClient):
    user_id, token = _signup(client)

    response = client.post(
        "/tasks",
        json={"title": "Summarize launch notes", "type": "analysis", "agent_id": "agt_research"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200, response.text
    task_id = response.json()["task_id"]

    detail = client.get(f"/tasks/{task_id}")
    assert detail.status_code == 200, detail.text
    task = detail.json()["task"]
    assert task["task_id"] == task_id
    assert task["user_id"] == user_id
    assert task["agent_id"] == "agt_research"
    assert task["type"] == "analysis"
    assert task["status"] in {"queued", "running", "completed"}
    assert task["created_at"]
    assert task["updated_at"]

    feed = client.get("/tasks").json()["tasks"]
    assert any(item["task_id"] == task_id and item["user_id"] == user_id for item in feed)


def test_scheduler_worker_completes_queued_task_and_creates_output(client: TestClient):
    user_id, token = _signup(client, "tasks-worker-owner@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Generate output", "type": "analysis", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    import backend.app.db.session as session
    from backend.app.services.job_runner import run_job_once

    with session.get_connection() as conn:
        job = conn.execute("SELECT id FROM scheduled_jobs WHERE job_type='task_queue_worker'").fetchone()
    assert job is not None

    run = run_job_once(job["id"])
    assert run["status"] == "success"

    task = client.get(f"/tasks/{task_id}").json()["task"]
    assert task["status"] == "completed"
    assert task["error_message"] is None

    outputs = client.get("/outputs").json()["outputs"]
    matching = [output for output in outputs if output["task_id"] == task_id]
    assert len(matching) == 1
    output = matching[0]
    assert output["user_id"] == user_id
    assert output["content"]
    assert output["text"] == output["content"]
    assert output["file_url"] is None


def test_scheduler_worker_records_failed_task_error_without_output(client: TestClient):
    _user_id, token = _signup(client, "tasks-fail-owner@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Expected failure", "type": "fail", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    import backend.app.db.session as session
    from backend.app.services.job_runner import run_job_once

    with session.get_connection() as conn:
        job = conn.execute("SELECT id FROM scheduled_jobs WHERE job_type='task_queue_worker'").fetchone()
    assert job is not None

    run = run_job_once(job["id"])
    assert run["status"] == "success"

    task = client.get(f"/tasks/{task_id}").json()["task"]
    assert task["status"] == "failed"
    assert "Simulated task failure" in task["error_message"]

    outputs = client.get("/outputs").json()["outputs"]
    assert all(output["task_id"] != task_id for output in outputs)


def test_outputs_can_be_filtered_by_task_and_user(client: TestClient):
    user_id, token = _signup(client, "tasks-output-filter-owner@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Filter output", "type": "analysis", "agent_id": "agt_filter"},
        headers=_auth_header(token),
    )
    task_id = create.json()["task_id"]

    import backend.app.db.session as session
    from backend.app.services.job_runner import run_job_once

    with session.get_connection() as conn:
        job = conn.execute("SELECT id FROM scheduled_jobs WHERE job_type='task_queue_worker'").fetchone()
    run_job_once(job["id"])

    by_task = client.get(f"/outputs?task_id={task_id}").json()["outputs"]
    by_user = client.get(f"/outputs?user_id={user_id}").json()["outputs"]
    assert len(by_task) == 1
    assert len(by_user) == 1
    assert by_task[0]["output_id"] == by_user[0]["output_id"]
