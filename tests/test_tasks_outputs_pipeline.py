import importlib
import json
import sys
from datetime import datetime, timezone
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
        json={"email": email, "password": "testpass", "display_name": "Task Owner"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _signin(client: TestClient, email: str):
    response = client.post(
        "/auth/signin",
        json={"email": email, "password": "testpass"},
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
    assert set(response.json().keys()) == {"status", "task_id"}
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

    feed_response = client.get("/tasks", headers=_auth_header(token))
    assert feed_response.status_code == 200, feed_response.text
    feed = feed_response.json()["tasks"]
    assert any(item["task_id"] == task_id and item["user_id"] == user_id for item in feed)


def test_create_task_does_not_write_execution_ledger_when_disabled(client: TestClient, monkeypatch):
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    _user_id, token = _signup(client, "tasks-ledger-disabled@example.com")

    response = client.post(
        "/tasks",
        json={"title": "Ledger disabled task", "type": "analysis", "agent_id": "agt_disabled"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200, response.text
    assert set(response.json().keys()) == {"status", "task_id"}

    import backend.app.db.session as session

    with session.get_connection() as conn:
        executions_count = conn.execute("SELECT COUNT(*) AS count FROM executions").fetchone()["count"]
        events_count = conn.execute("SELECT COUNT(*) AS count FROM execution_events").fetchone()["count"]

    assert executions_count == 0
    assert events_count == 0


def test_create_task_writes_execution_ledger_when_enabled(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    import backend.app.routes.platform as platform

    monkeypatch.setattr(platform, "_trigger_task_queue_worker", lambda: None)
    user_id, token = _signup(client, "tasks-ledger-enabled@example.com")

    response = client.post(
        "/tasks",
        json={"title": "Ledger enabled task", "type": "analysis", "agent_id": "agt_enabled"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200, response.text
    assert set(response.json().keys()) == {"status", "task_id"}
    task_id = response.json()["task_id"]

    import backend.app.db.session as session

    with session.get_connection() as conn:
        executions = conn.execute("SELECT * FROM executions WHERE source_type='task' AND source_id=?", (task_id,)).fetchall()

    assert len(executions) == 1
    execution = executions[0]
    assert execution["user_id"] == user_id
    assert execution["agent_id"] == "agt_enabled"
    assert execution["status"] == "queued"
    execution_metadata = json.loads(execution["metadata_json"])
    assert execution_metadata == {
        "task_id": task_id,
        "task_title": "Ledger enabled task",
        "task_type": "analysis",
    }

    with session.get_connection() as conn:
        events = conn.execute(
            "SELECT * FROM execution_events WHERE execution_id=? AND event_type='task_created'",
            (execution["execution_id"],),
        ).fetchall()

    assert len(events) == 1
    event = events[0]
    assert event["execution_id"] == execution["execution_id"]
    payload = json.loads(event["payload_json"])
    assert payload["task_id"] == task_id
    assert payload["status"] == "queued"
    assert payload["created_at"]


def test_create_task_rolls_back_task_and_ledger_when_enabled_event_write_fails(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _user_id, token = _signup(client, "tasks-ledger-failure@example.com")

    from backend.app.services import execution_ledger

    def fail_event_write(*args, **kwargs):
        raise RuntimeError("simulated execution event write failure")

    monkeypatch.setattr(execution_ledger, "append_execution_event", fail_event_write)

    with pytest.raises(RuntimeError, match="simulated execution event write failure"):
        client.post(
            "/tasks",
            json={"title": "Ledger atomic failure task", "type": "analysis", "agent_id": "agt_atomic"},
            headers=_auth_header(token),
        )

    import backend.app.db.session as session

    with session.get_connection() as conn:
        task_count = conn.execute("SELECT COUNT(*) AS count FROM tasks WHERE title=?", ("Ledger atomic failure task",)).fetchone()["count"]
        executions_count = conn.execute("SELECT COUNT(*) AS count FROM executions WHERE source_type='task'").fetchone()["count"]
        events_count = conn.execute("SELECT COUNT(*) AS count FROM execution_events").fetchone()["count"]

    assert task_count == 0
    assert executions_count == 0
    assert events_count == 0


def _task_worker_job_id():
    import backend.app.db.session as session

    with session.get_connection() as conn:
        job = conn.execute("SELECT id FROM scheduled_jobs WHERE job_type='task_queue_worker'").fetchone()
    assert job is not None
    return job["id"]


def _execution_for_task(task_id: str):
    import backend.app.db.session as session

    with session.get_connection() as conn:
        return conn.execute("SELECT * FROM executions WHERE source_type='task' AND source_id=?", (task_id,)).fetchone()


def _events_for_execution(execution_id: str):
    import backend.app.db.session as session

    with session.get_connection() as conn:
        return conn.execute(
            "SELECT * FROM execution_events WHERE execution_id=? ORDER BY id ASC",
            (execution_id,),
        ).fetchall()


def _artifacts_for_execution(execution_id: str):
    import backend.app.db.session as session

    with session.get_connection() as conn:
        return conn.execute(
            "SELECT * FROM execution_artifacts WHERE execution_id=? ORDER BY id ASC",
            (execution_id,),
        ).fetchall()


def test_scheduler_worker_does_not_write_lifecycle_events_when_execution_ledger_disabled(client: TestClient, monkeypatch):
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    _user_id, token = _signup(client, "tasks-ledger-worker-disabled@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Disabled lifecycle task", "type": "analysis", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text

    from backend.app.services.job_runner import run_job_once

    run = run_job_once(_task_worker_job_id())
    assert run["status"] == "success"

    import backend.app.db.session as session

    with session.get_connection() as conn:
        events_count = conn.execute(
            "SELECT COUNT(*) AS count FROM execution_events WHERE event_type IN ('execution_started', 'execution_completed', 'execution_failed')"
        ).fetchone()["count"]

    assert events_count == 0


def test_scheduler_worker_writes_started_and_completed_lifecycle_events_when_enabled(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _user_id, token = _signup(client, "tasks-ledger-worker-complete@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Completed lifecycle task", "type": "analysis", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    from backend.app.services.job_runner import run_job_once

    run = run_job_once(_task_worker_job_id())
    assert run["status"] == "success"

    execution = _execution_for_task(task_id)
    assert execution is not None
    assert execution["status"] == "completed"
    assert execution["finished_at"]
    events = _events_for_execution(execution["execution_id"])
    event_types = [event["event_type"] for event in events]
    assert "execution_started" in event_types
    assert "execution_completed" in event_types
    started_payload = json.loads(next(event["payload_json"] for event in events if event["event_type"] == "execution_started"))
    assert started_payload["task_id"] == task_id
    assert started_payload["previous_status"] == "queued"
    assert started_payload["new_status"] == "running"
    assert started_payload["timestamp"]
    completed_payload = json.loads(next(event["payload_json"] for event in events if event["event_type"] == "execution_completed"))
    assert completed_payload["task_id"] == task_id
    assert completed_payload["status"] == "completed"
    assert completed_payload["timestamp"]


def test_scheduler_worker_writes_failed_lifecycle_event_with_safe_error_when_enabled(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _user_id, token = _signup(client, "tasks-ledger-worker-fail@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Failed lifecycle task", "type": "fail", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    from backend.app.services.job_runner import run_job_once

    run = run_job_once(_task_worker_job_id())
    assert run["status"] == "success"

    execution = _execution_for_task(task_id)
    assert execution is not None
    assert execution["status"] == "failed"
    assert execution["finished_at"]
    events = _events_for_execution(execution["execution_id"])
    event_types = [event["event_type"] for event in events]
    assert "execution_started" in event_types
    assert "execution_failed" in event_types
    failed_payload = json.loads(next(event["payload_json"] for event in events if event["event_type"] == "execution_failed"))
    assert failed_payload["task_id"] == task_id
    assert failed_payload["status"] == "failed"
    assert "Simulated task failure" in failed_payload["error"]
    assert "token" not in json.dumps(failed_payload).lower()
    assert "password" not in json.dumps(failed_payload).lower()
    assert failed_payload["timestamp"]


def test_scheduler_worker_skips_lifecycle_events_when_execution_row_is_missing(client: TestClient, monkeypatch):
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    _user_id, token = _signup(client, "tasks-ledger-worker-missing@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Missing execution lifecycle task", "type": "analysis", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]
    assert _execution_for_task(task_id) is None
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")

    from backend.app.services.job_runner import run_job_once

    run = run_job_once(_task_worker_job_id())
    assert run["status"] == "success"

    assert _execution_for_task(task_id) is None
    import backend.app.db.session as session

    with session.get_connection() as conn:
        lifecycle_events_count = conn.execute(
            "SELECT COUNT(*) AS count FROM execution_events WHERE event_type IN ('execution_started', 'execution_completed', 'execution_failed')"
        ).fetchone()["count"]
    assert lifecycle_events_count == 0


def test_scheduler_worker_does_not_write_output_artifact_when_execution_ledger_disabled(client: TestClient, monkeypatch):
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    _user_id, token = _signup(client, "tasks-ledger-output-disabled@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Disabled output artifact task", "type": "analysis", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text

    from backend.app.services.job_runner import run_job_once

    run = run_job_once(_task_worker_job_id())
    assert run["status"] == "success"

    import backend.app.db.session as session

    with session.get_connection() as conn:
        artifacts_count = conn.execute("SELECT COUNT(*) AS count FROM execution_artifacts").fetchone()["count"]
        output_created_count = conn.execute(
            "SELECT COUNT(*) AS count FROM execution_events WHERE event_type='output_created'"
        ).fetchone()["count"]
        outputs_count = conn.execute("SELECT COUNT(*) AS count FROM outputs").fetchone()["count"]

    assert outputs_count == 1
    assert artifacts_count == 0
    assert output_created_count == 0


def test_scheduler_worker_writes_output_artifact_and_event_when_execution_ledger_enabled(client: TestClient, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    _user_id, token = _signup(client, "tasks-ledger-output-enabled@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Enabled output artifact task", "type": "analysis", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    from backend.app.services.job_runner import run_job_once

    run = run_job_once(_task_worker_job_id())
    assert run["status"] == "success"

    execution = _execution_for_task(task_id)
    assert execution is not None
    artifacts = _artifacts_for_execution(execution["execution_id"])
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact["artifact_type"] == "output"
    assert artifact["content_text"] is None
    artifact_metadata = json.loads(artifact["metadata_json"])
    assert artifact_metadata["task_id"] == task_id
    assert artifact_metadata["output_id"]
    assert artifact_metadata["output_type"] == "text"
    assert artifact_metadata["status"] == "completed"
    assert artifact_metadata["source_type"] == "output"
    assert artifact_metadata["source_id"] == artifact_metadata["output_id"]
    assert "content" not in artifact_metadata
    assert "text" not in artifact_metadata

    events = _events_for_execution(execution["execution_id"])
    output_events = [event for event in events if event["event_type"] == "output_created"]
    assert len(output_events) == 1
    payload = json.loads(output_events[0]["payload_json"])
    assert payload["task_id"] == task_id
    assert payload["output_id"] == artifact_metadata["output_id"]
    assert payload["timestamp"]
    assert "content" not in payload
    assert "text" not in payload


def test_scheduler_worker_skips_output_artifact_when_execution_row_is_missing(client: TestClient, monkeypatch):
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    _user_id, token = _signup(client, "tasks-ledger-output-missing@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Missing execution output task", "type": "analysis", "agent_id": "agt_worker"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]
    assert _execution_for_task(task_id) is None
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")

    from backend.app.services.job_runner import run_job_once

    run = run_job_once(_task_worker_job_id())
    assert run["status"] == "success"

    import backend.app.db.session as session

    with session.get_connection() as conn:
        outputs_count = conn.execute("SELECT COUNT(*) AS count FROM outputs WHERE task_id=?", (task_id,)).fetchone()["count"]
        artifacts_count = conn.execute("SELECT COUNT(*) AS count FROM execution_artifacts").fetchone()["count"]
        output_created_count = conn.execute(
            "SELECT COUNT(*) AS count FROM execution_events WHERE event_type='output_created'"
        ).fetchone()["count"]

    assert outputs_count == 1
    assert artifacts_count == 0
    assert output_created_count == 0


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

    outputs_response = client.get("/outputs", headers=_auth_header(token))
    assert outputs_response.status_code == 200, outputs_response.text
    outputs = outputs_response.json()["outputs"]
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

    outputs_response = client.get("/outputs", headers=_auth_header(token))
    assert outputs_response.status_code == 200, outputs_response.text
    outputs = outputs_response.json()["outputs"]
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

    by_task_response = client.get(f"/outputs?task_id={task_id}", headers=_auth_header(token))
    by_user_response = client.get(f"/outputs?user_id={user_id}", headers=_auth_header(token))
    assert by_task_response.status_code == 200, by_task_response.text
    assert by_user_response.status_code == 200, by_user_response.text
    by_task = by_task_response.json()["outputs"]
    by_user = by_user_response.json()["outputs"]
    assert len(by_task) == 1
    assert len(by_user) == 1
    assert by_task[0]["output_id"] == by_user[0]["output_id"]


def test_task_list_requires_auth_and_is_scoped_to_signed_in_user(client: TestClient):
    owner_id, owner_token = _signup(client, "tasks-scoped-owner@example.com")
    other_id, other_token = _signup(client, "tasks-scoped-other@example.com")

    create_owner = client.post(
        "/tasks",
        json={"title": "Owner private task", "type": "analysis", "agent_id": "agt_owner"},
        headers=_auth_header(owner_token),
    )
    create_other = client.post(
        "/tasks",
        json={"title": "Other private task", "type": "analysis", "agent_id": "agt_other"},
        headers=_auth_header(other_token),
    )
    assert create_owner.status_code == 200, create_owner.text
    assert create_other.status_code == 200, create_other.text
    owner_task_id = create_owner.json()["task_id"]
    other_task_id = create_other.json()["task_id"]

    no_auth = client.get("/tasks")
    assert no_auth.status_code == 401

    owner_tasks_response = client.get("/tasks", headers=_auth_header(owner_token))
    assert owner_tasks_response.status_code == 200, owner_tasks_response.text
    owner_tasks = owner_tasks_response.json()["tasks"]
    assert any(task["task_id"] == owner_task_id and task["user_id"] == owner_id for task in owner_tasks)
    assert all(task["user_id"] == owner_id for task in owner_tasks)
    assert all(task["task_id"] != other_task_id for task in owner_tasks)

    forbidden = client.get(f"/tasks?user_id={other_id}", headers=_auth_header(owner_token))
    assert forbidden.status_code == 403


def test_task_list_persists_after_signin_again(client: TestClient):
    email = "tasks-resignin-owner@example.com"
    user_id, token = _signup(client, email)
    create = client.post(
        "/tasks",
        json={"title": "Persist after signin", "type": "analysis", "agent_id": "agt_resignin"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    signed_in_user_id, second_token = _signin(client, email)
    assert signed_in_user_id == user_id

    response = client.get("/tasks", headers=_auth_header(second_token))
    assert response.status_code == 200, response.text
    tasks = response.json()["tasks"]
    assert any(task["task_id"] == task_id and task["user_id"] == user_id for task in tasks)


def test_output_list_requires_auth_and_is_scoped_to_signed_in_user(client: TestClient):
    owner_id, owner_token = _signup(client, "outputs-scoped-owner@example.com")
    other_id, other_token = _signup(client, "outputs-scoped-other@example.com")

    owner_create = client.post(
        "/tasks",
        json={"title": "Owner output", "type": "analysis", "agent_id": "agt_output_owner"},
        headers=_auth_header(owner_token),
    )
    other_create = client.post(
        "/tasks",
        json={"title": "Other output", "type": "analysis", "agent_id": "agt_output_other"},
        headers=_auth_header(other_token),
    )
    assert owner_create.status_code == 200, owner_create.text
    assert other_create.status_code == 200, other_create.text
    owner_task_id = owner_create.json()["task_id"]
    other_task_id = other_create.json()["task_id"]

    import backend.app.db.session as session
    from backend.app.services.job_runner import run_job_once

    with session.get_connection() as conn:
        job = conn.execute("SELECT id FROM scheduled_jobs WHERE job_type='task_queue_worker'").fetchone()
    run_job_once(job["id"])

    no_auth = client.get("/outputs")
    assert no_auth.status_code == 401

    owner_outputs_response = client.get("/outputs", headers=_auth_header(owner_token))
    assert owner_outputs_response.status_code == 200, owner_outputs_response.text
    owner_outputs = owner_outputs_response.json()["outputs"]
    assert any(output["task_id"] == owner_task_id and output["user_id"] == owner_id for output in owner_outputs)
    assert all(output["user_id"] == owner_id for output in owner_outputs)
    assert all(output["task_id"] != other_task_id for output in owner_outputs)

    forbidden = client.get(f"/outputs?user_id={other_id}", headers=_auth_header(owner_token))
    assert forbidden.status_code == 403


def test_delete_task_requires_auth(client: TestClient):
    _user_id, token = _signup(client, "tasks-delete-auth-owner@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Delete auth task", "type": "analysis", "agent_id": "agt_delete"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text

    response = client.delete(f"/tasks/{create.json()['task_id']}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_task_owner_can_delete_task_and_it_disappears_from_task_list(client: TestClient):
    _user_id, token = _signup(client, "tasks-delete-owner@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Delete visible task", "type": "analysis", "agent_id": "agt_delete"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    response = client.delete(f"/tasks/{task_id}", headers=_auth_header(token))

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "deleted": True}
    detail = client.get(f"/tasks/{task_id}")
    assert detail.status_code == 404
    tasks_response = client.get("/tasks", headers=_auth_header(token))
    assert tasks_response.status_code == 200, tasks_response.text
    assert all(task["task_id"] != task_id for task in tasks_response.json()["tasks"])


def test_user_cannot_delete_another_users_task(client: TestClient):
    _owner_id, owner_token = _signup(client, "tasks-delete-real-owner@example.com")
    _other_id, other_token = _signup(client, "tasks-delete-attacker@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Protected task", "type": "analysis", "agent_id": "agt_delete"},
        headers=_auth_header(owner_token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    forbidden = client.delete(f"/tasks/{task_id}", headers=_auth_header(other_token))

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "forbidden"
    owner_tasks = client.get("/tasks", headers=_auth_header(owner_token)).json()["tasks"]
    assert any(task["task_id"] == task_id for task in owner_tasks)


def test_admin_can_delete_another_users_task(client: TestClient, monkeypatch):
    _owner_id, owner_token = _signup(client, "tasks-delete-admin-owner@example.com")
    admin_id, admin_token = _signup(client, "tasks-delete-admin@example.com")
    monkeypatch.setenv("ADMIN_USER_IDS", admin_id)
    create = client.post(
        "/tasks",
        json={"title": "Admin deletable task", "type": "analysis", "agent_id": "agt_delete"},
        headers=_auth_header(owner_token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    response = client.delete(f"/tasks/{task_id}", headers=_auth_header(admin_token))

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "deleted": True}
    assert client.get(f"/tasks/{task_id}").status_code == 404


def test_delete_task_removes_related_outputs_and_logs(client: TestClient):
    _user_id, token = _signup(client, "tasks-delete-outputs-owner@example.com")
    create = client.post(
        "/tasks",
        json={"title": "Delete output task", "type": "analysis", "agent_id": "agt_delete"},
        headers=_auth_header(token),
    )
    assert create.status_code == 200, create.text
    task_id = create.json()["task_id"]

    import backend.app.db.session as session
    from backend.app.services.job_runner import run_job_once

    with session.get_connection() as conn:
        job = conn.execute("SELECT id FROM scheduled_jobs WHERE job_type='task_queue_worker'").fetchone()
    assert job is not None
    run_job_once(job["id"])

    outputs_before = client.get(f"/outputs?task_id={task_id}", headers=_auth_header(token))
    assert outputs_before.status_code == 200, outputs_before.text
    assert len(outputs_before.json()["outputs"]) == 1
    logs_before = client.get(f"/tasks/{task_id}/logs")
    assert logs_before.status_code == 200, logs_before.text
    assert logs_before.json()["logs"]

    response = client.delete(f"/tasks/{task_id}", headers=_auth_header(token))

    assert response.status_code == 200, response.text
    outputs_after = client.get(f"/outputs?task_id={task_id}", headers=_auth_header(token))
    assert outputs_after.status_code == 200, outputs_after.text
    assert outputs_after.json()["outputs"] == []
    with session.get_connection() as conn:
        output_count = conn.execute("SELECT COUNT(*) AS count FROM outputs WHERE task_id=?", (task_id,)).fetchone()["count"]
        log_count = conn.execute("SELECT COUNT(*) AS count FROM task_logs WHERE task_id=?", (task_id,)).fetchone()["count"]
    assert output_count == 0
    assert log_count == 0


def test_delete_missing_task_returns_404(client: TestClient):
    _user_id, token = _signup(client, "tasks-delete-missing-owner@example.com")

    response = client.delete("/tasks/tsk_missing", headers=_auth_header(token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_row_dict_serializes_datetime_values_for_postgres_rows():
    from backend.app.routes.platform import _row_dict

    class FakeRow:
        def __iter__(self):
            return iter({
                "task_id": "tsk_datetime",
                "created_at": datetime(2026, 4, 26, 3, 59, 52, tzinfo=timezone.utc),
                "title": "Datetime task",
            }.items())

    result = _row_dict(FakeRow())

    assert result == {
        "task_id": "tsk_datetime",
        "created_at": "2026-04-26T03:59:52+00:00",
        "title": "Datetime task",
    }
