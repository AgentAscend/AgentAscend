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


def test_execution_list_supports_pagination_filters_and_safe_summaries(client: TestClient):
    from backend.app.services import execution_ledger

    user_id, token = _signup(client, "execution-list-filters@example.com")
    other_user_id, _other_token = _signup(client, "execution-list-filters-other@example.com")

    first = execution_ledger.create_execution(
        user_id=user_id,
        source_type="task",
        source_id="tsk_filter_first",
        agent_id="agt_filter_a",
        status="completed",
        metadata={"purpose": "first"},
    )
    second = execution_ledger.create_execution(
        user_id=user_id,
        source_type="task",
        source_id="tsk_filter_second",
        agent_id="agt_filter_b",
        status="failed",
        metadata={"purpose": "second"},
    )
    execution_ledger.append_execution_event(second["execution_id"], "execution_failed", payload={"safe": True})
    execution_ledger.attach_execution_artifact(
        second["execution_id"],
        artifact_type="output",
        name="Safe output reference",
        uri="output://out_filter_second",
        content_text="raw output body should not be exposed in summaries",
        metadata={"task_id": "tsk_filter_second", "output_id": "out_filter_second"},
    )
    execution_ledger.create_execution(
        user_id=other_user_id,
        source_type="task",
        source_id="tsk_filter_other",
        agent_id="agt_filter_b",
        status="failed",
    )

    filtered = client.get(
        "/executions/me?status=failed&source_type=task&agent_id=agt_filter_b&limit=1&offset=0",
        headers=_auth_header(token),
    )
    assert filtered.status_code == 200, filtered.text
    body = filtered.json()
    assert body["status"] == "ok"
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert body["total"] == 1
    assert [execution["execution_id"] for execution in body["executions"]] == [second["execution_id"]]
    assert body["executions"][0]["event_count"] == 1
    assert body["executions"][0]["artifact_count"] == 1
    assert "content_text" not in str(body).lower()
    assert "raw output body" not in str(body).lower()

    page_two = client.get("/executions/me?limit=1&offset=1", headers=_auth_header(token))
    assert page_two.status_code == 200, page_two.text
    assert page_two.json()["total"] == 2
    assert len(page_two.json()["executions"]) == 1
    assert page_two.json()["executions"][0]["execution_id"] == first["execution_id"]

    by_task = client.get("/executions/me?task_id=tsk_filter_second", headers=_auth_header(token))
    assert by_task.status_code == 200, by_task.text
    assert [execution["execution_id"] for execution in by_task.json()["executions"]] == [second["execution_id"]]


def test_execution_list_rejects_invalid_limit(client: TestClient):
    _user_id, token = _signup(client, "execution-list-invalid-limit@example.com")

    too_large = client.get("/executions/me?limit=101", headers=_auth_header(token))
    assert too_large.status_code == 422

    zero = client.get("/executions/me?limit=0", headers=_auth_header(token))
    assert zero.status_code == 422


def test_execution_summary_is_authenticated_user_scoped_and_safe(client: TestClient):
    from backend.app.services import execution_ledger

    user_id, token = _signup(client, "execution-summary-owner@example.com")
    other_user_id, other_token = _signup(client, "execution-summary-other@example.com")

    completed = execution_ledger.create_execution(user_id=user_id, source_type="task", source_id="tsk_summary_done", status="completed")
    failed = execution_ledger.create_execution(user_id=user_id, source_type="task", source_id="tsk_summary_failed", status="failed")
    execution_ledger.append_execution_event(completed["execution_id"], "execution_completed", payload={"safe": True})
    execution_ledger.append_execution_event(failed["execution_id"], "execution_failed", payload={"safe": True})
    execution_ledger.attach_execution_artifact(
        failed["execution_id"],
        artifact_type="output",
        name="Failure output reference",
        uri="output://out_summary_failed",
        content_text="raw failure output must stay hidden",
        metadata={"output_id": "out_summary_failed"},
    )
    execution_ledger.create_execution(user_id=other_user_id, source_type="task", source_id="tsk_summary_other", status="running")

    unauthenticated = client.get("/executions/summary")
    assert unauthenticated.status_code == 401

    response = client.get("/executions/summary", headers=_auth_header(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["scope"] == "user"
    assert body["total_executions"] == 2
    assert body["counts_by_status"] == {"completed": 1, "failed": 1}
    assert body["recent_event_count"] == 2
    assert body["recent_artifact_count"] == 1
    assert body["recent_failures"] == 1
    assert body["latest_execution_timestamp"] is not None
    assert body["health_flags"]["orphan_events"] == 0
    assert body["health_flags"]["orphan_artifacts"] == 0
    assert body["health_flags"]["malformed_json"] == 0
    assert body["health_flags"]["sensitive_match"] == 0
    assert "raw failure output" not in response.text.lower()
    assert "content_text" not in response.text.lower()

    other_response = client.get("/executions/summary", headers=_auth_header(other_token))
    assert other_response.status_code == 200, other_response.text
    assert other_response.json()["total_executions"] == 1
    assert other_response.json()["counts_by_status"] == {"running": 1}


def test_system_owned_scheduler_execution_is_hidden_from_user_endpoints(client: TestClient):
    from backend.app.services import execution_ledger

    _user_id, token = _signup(client, "scheduler-system-hidden@example.com")
    scheduler_execution = execution_ledger.create_execution(
        user_id=None,
        source_type="scheduled_job_run",
        source_id="run_system_hidden",
        status="completed",
        metadata={"scheduled_job_id": "default-git-status-summary", "job_type": "git_status_summary"},
    )
    execution_ledger.append_execution_event(
        scheduler_execution["execution_id"],
        "scheduler_job_completed",
        payload={"run_id": "run_system_hidden", "scheduled_job_id": "default-git-status-summary", "has_error": False},
    )

    list_response = client.get("/executions/me", headers=_auth_header(token))
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["executions"] == []

    summary_response = client.get("/executions/summary", headers=_auth_header(token))
    assert summary_response.status_code == 200, summary_response.text
    assert summary_response.json()["total_executions"] == 0

    detail_response = client.get(f"/executions/{scheduler_execution['execution_id']}", headers=_auth_header(token))
    assert detail_response.status_code in {403, 404}
