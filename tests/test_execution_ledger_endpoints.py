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
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    db_path = tmp_path / "agentascend-execution-endpoints.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "TestPass123!", "display_name": email.split("@", 1)[0]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_task(client: TestClient, token: str, title: str, task_type: str = "analysis") -> str:
    response = client.post(
        "/tasks",
        json={"title": title, "type": task_type, "agent_id": "agt_execution_endpoint"},
        headers=_auth_header(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["task_id"]


def _run_task_worker():
    import backend.app.db.session as session
    from backend.app.services.job_runner import run_job_once

    with session.get_connection() as conn:
        job = conn.execute("SELECT id FROM scheduled_jobs WHERE job_type='task_queue_worker'").fetchone()
    assert job is not None
    run = run_job_once(job["id"])
    assert run["status"] == "success"


def test_execution_endpoints_require_auth(client: TestClient):
    assert client.get("/executions/me").status_code == 401
    assert client.get("/executions/exec_missing").status_code == 401
    assert client.get("/tasks/tsk_missing/execution").status_code == 401


def test_user_can_list_and_read_own_execution(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _user_id, token = _signup(client, "execution-endpoints-owner@example.com")
    task_id = _create_task(client, token, "Own execution endpoint task")
    _run_task_worker()

    list_response = client.get("/executions/me", headers=_auth_header(token))
    assert list_response.status_code == 200, list_response.text
    body = list_response.json()
    assert body["status"] == "ok"
    assert len(body["executions"]) == 1
    listed_execution = body["executions"][0]
    assert listed_execution["source_type"] == "task"
    assert listed_execution["source_id"] == task_id
    execution_id = listed_execution["execution_id"]

    detail_response = client.get(f"/executions/{execution_id}", headers=_auth_header(token))
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["status"] == "ok"
    assert detail["execution"]["execution_id"] == execution_id
    assert detail["execution"]["source_id"] == task_id
    event_types = [event["event_type"] for event in detail["events"]]
    assert "task_created" in event_types
    assert "execution_started" in event_types
    assert "execution_completed" in event_types
    assert "output_created" in event_types
    assert len(detail["artifacts"]) == 1
    artifact = detail["artifacts"][0]
    assert artifact["artifact_type"] == "output"
    assert artifact["metadata"]["task_id"] == task_id
    assert "content_text" not in artifact
    assert "content" not in artifact["metadata"]
    assert "text" not in artifact["metadata"]


def test_user_can_read_execution_by_own_task_id(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _user_id, token = _signup(client, "execution-by-task-owner@example.com")
    task_id = _create_task(client, token, "Execution by task endpoint")
    _run_task_worker()

    response = client.get(f"/tasks/{task_id}/execution", headers=_auth_header(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["execution"]["source_type"] == "task"
    assert body["execution"]["source_id"] == task_id
    assert [event["event_type"] for event in body["events"]]


def test_user_cannot_read_another_users_execution(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _owner_id, owner_token = _signup(client, "execution-owner@example.com")
    _other_id, other_token = _signup(client, "execution-other@example.com")
    task_id = _create_task(client, owner_token, "Private execution endpoint task")
    _run_task_worker()

    owner_response = client.get(f"/tasks/{task_id}/execution", headers=_auth_header(owner_token))
    assert owner_response.status_code == 200, owner_response.text
    execution_id = owner_response.json()["execution"]["execution_id"]

    forbidden_execution = client.get(f"/executions/{execution_id}", headers=_auth_header(other_token))
    assert forbidden_execution.status_code == 403
    assert forbidden_execution.json()["error"]["code"] == "forbidden"

    forbidden_task = client.get(f"/tasks/{task_id}/execution", headers=_auth_header(other_token))
    assert forbidden_task.status_code == 403
    assert forbidden_task.json()["error"]["code"] == "forbidden"

    other_list = client.get("/executions/me", headers=_auth_header(other_token))
    assert other_list.status_code == 200, other_list.text
    assert other_list.json()["executions"] == []


def test_missing_execution_for_own_task_returns_404(client: TestClient, monkeypatch):
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    _user_id, token = _signup(client, "execution-missing-owner@example.com")
    task_id = _create_task(client, token, "Missing ledger endpoint task")

    response = client.get(f"/tasks/{task_id}/execution", headers=_auth_header(token))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_execution_response_does_not_expose_secret_fields(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _user_id, token = _signup(client, "execution-safe-response@example.com")
    task_id = _create_task(client, token, "Safe execution response task")
    _run_task_worker()

    response = client.get(f"/tasks/{task_id}/execution", headers=_auth_header(token))
    assert response.status_code == 200, response.text
    response_text = response.text.lower()
    assert "password" not in response_text
    assert "authorization" not in response_text
    assert "bearer" not in response_text
    assert "database_url" not in response_text
    assert "postgres_url" not in response_text
    assert "private_key" not in response_text
