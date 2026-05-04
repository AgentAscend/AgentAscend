import importlib
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-command-center.db"
    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    import backend.app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "safe-test-password", "display_name": email.split("@", 1)[0]},
    )
    assert response.status_code == 200, {"status_code": response.status_code, "json_keys": sorted(response.json().keys())}
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_command_center_requires_authentication(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        response = client.get("/dashboard/command-center")

    assert response.status_code == 401


def test_command_center_empty_account_returns_zero_counts_and_empty_recent_lists(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        _user_id, token = _signup(client, "empty-command-center@example.com")

        response = client.get("/dashboard/command-center", headers=_auth(token))

    assert response.status_code == 200, {"status_code": response.status_code, "json_keys": sorted(response.json().keys())}
    body = response.json()
    assert body["status"] == "ok"
    assert body["agent_counts_by_status"] == {}
    assert body["deployment_counts_by_status"] == {}
    assert body["deployment_counts_by_environment"] == {}
    assert body["task_counts_by_status"] == {}
    assert body["output_count"] == 0
    assert body["recent_outputs"] == []
    assert body["execution_summary"]["total_executions"] == 0
    assert body["recent_executions"] == []
    assert body["recent_failures"] == []
    assert body["workflow_counts_by_status"] == {}
    assert body["recent_workflow_runs"] == []


def test_command_center_is_owner_scoped_and_aggregates_owned_records(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        owner_id, owner_token = _signup(client, "command-center-owner@example.com")
        other_id, other_token = _signup(client, "command-center-other@example.com")

        owner_agent = client.post(
            "/agents",
            headers=_auth(owner_token),
            json={"name": "Owner Agent", "category": "Ops", "description": "Owner agent"},
        )
        assert owner_agent.status_code == 200
        owner_agent_id = owner_agent.json()["agent_id"]
        owner_deploy = client.post(
            f"/agents/{owner_agent_id}/deploy",
            headers=_auth(owner_token),
            json={"environment": "production", "region": "us-east", "status": "running"},
        )
        assert owner_deploy.status_code == 200

        other_agent = client.post(
            "/agents",
            headers=_auth(other_token),
            json={"name": "Other Agent", "category": "Ops", "description": "Other agent"},
        )
        assert other_agent.status_code == 200
        other_agent_id = other_agent.json()["agent_id"]

        from backend.app.db.session import get_connection

        with get_connection() as conn:
            conn.execute(
                "UPDATE agents SET status='active', tasks_completed=3, success_rate=75 WHERE agent_id=?",
                (owner_agent_id,),
            )
            conn.execute(
                "UPDATE agents SET status='error', tasks_completed=9, success_rate=10 WHERE agent_id=?",
                (other_agent_id,),
            )
            conn.execute(
                """
                INSERT INTO tasks(task_id, user_id, agent_id, type, title, status, priority, assigned_to, error_message, created_at, updated_at)
                VALUES
                  ('task_owner_done', ?, ?, 'analysis', 'Owner Done', 'completed', 'medium', ?, NULL, datetime('now'), datetime('now')),
                  ('task_owner_failed', ?, ?, 'analysis', 'Owner Failed', 'failed', 'high', ?, 'summarized failure only', datetime('now'), datetime('now')),
                  ('task_other_done', ?, ?, 'analysis', 'Other Done', 'completed', 'medium', ?, NULL, datetime('now'), datetime('now'))
                """,
                (owner_id, owner_agent_id, owner_agent_id, owner_id, owner_agent_id, owner_agent_id, other_id, other_agent_id, other_agent_id),
            )
            conn.execute(
                """
                INSERT INTO outputs(output_id, task_id, user_id, title, output_type, content, text, file_url, size_bytes, download_url, created_at)
                VALUES
                  ('out_owner', 'task_owner_done', ?, 'Owner Output', 'report', 'safe summary', 'safe text', NULL, 12, '/outputs/out_owner/download', datetime('now')),
                  ('out_other', 'task_other_done', ?, 'Other Output', 'report', 'other content', 'other text', NULL, 12, '/outputs/out_other/download', datetime('now'))
                """,
                (owner_id, other_id),
            )
            conn.execute(
                """
                INSERT INTO executions(execution_id, source_type, source_id, user_id, agent_id, status, started_at, finished_at, metadata_json)
                VALUES
                  ('exec_owner_failed', 'task', 'task_owner_failed', ?, ?, 'failed', '2026-01-01T00:00:00Z', '2026-01-01T00:01:00Z', ?),
                  ('exec_other_failed', 'task', 'task_other_done', ?, ?, 'failed', '2026-01-01T00:00:00Z', '2026-01-01T00:01:00Z', ?)
                """,
                (
                    owner_id,
                    owner_agent_id,
                    json.dumps({"api_key": "do-not-leak", "safe": "visible"}),
                    other_id,
                    other_agent_id,
                    json.dumps({"safe": "other"}),
                ),
            )
            conn.execute(
                "INSERT INTO workflows(workflow_id, name, status, runs_total, success_rate, updated_at) VALUES('wf_owner', 'Owner Workflow', 'active', 1, 100, datetime('now'))"
            )
            conn.execute(
                "INSERT INTO workflow_runs(run_id, workflow_id, status, duration_ms, started_at) VALUES('run_owner', 'wf_owner', 'success', 50, datetime('now'))"
            )
            conn.execute(
                """
                INSERT INTO audit_events(event_id, actor_user_id, event_type, target_type, target_id, metadata_json, created_at)
                VALUES('audit_wf_owner', ?, 'workflow.create', 'workflow', 'wf_owner', '{}', datetime('now'))
                """,
                (owner_id,),
            )
            conn.commit()

        response = client.get("/dashboard/command-center", headers=_auth(owner_token))

    assert response.status_code == 200, {"status_code": response.status_code, "json_keys": sorted(response.json().keys())}
    body = response.json()
    assert body["agent_counts_by_status"] == {"active": 1}
    assert body["deployment_counts_by_status"] == {"running": 1}
    assert body["deployment_counts_by_environment"] == {"production": 1}
    assert body["task_counts_by_status"] == {"completed": 1, "failed": 1}
    assert body["output_count"] == 1
    assert [output["output_id"] for output in body["recent_outputs"]] == ["out_owner"]
    assert body["execution_summary"]["total_executions"] == 1
    assert body["execution_summary"]["counts_by_status"] == {"failed": 1}
    assert [execution["execution_id"] for execution in body["recent_executions"]] == ["exec_owner_failed"]
    assert [failure["execution_id"] for failure in body["recent_failures"]] == ["exec_owner_failed"]
    assert body["workflow_counts_by_status"] == {"active": 1}
    assert [run["run_id"] for run in body["recent_workflow_runs"]] == ["run_owner"]


def test_command_center_response_does_not_leak_raw_payload_or_metadata(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        owner_id, token = _signup(client, "command-center-redaction@example.com")
        agent = client.post(
            "/agents",
            headers=_auth(token),
            json={"name": "Redaction Agent", "category": "Ops", "description": "Redaction agent"},
        )
        assert agent.status_code == 200
        agent_id = agent.json()["agent_id"]

        from backend.app.db.session import get_connection

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO executions(execution_id, source_type, source_id, user_id, agent_id, status, started_at, metadata_json)
                VALUES('exec_sensitive', 'agent', ?, ?, ?, 'failed', '2026-01-01T00:00:00Z', ?)
                """,
                (agent_id, owner_id, agent_id, json.dumps({"api_key": "secret-value", "token": "secret-token", "safe": "visible"})),
            )
            conn.execute(
                """
                INSERT INTO execution_events(event_id, execution_id, event_type, level, message, payload_json, created_at)
                VALUES('event_sensitive', 'exec_sensitive', 'tool.error', 'error', 'sanitized failure', ?, '2026-01-01T00:00:01Z')
                """,
                (json.dumps({"private_key": "secret", "safe": "event"}),),
            )
            conn.commit()

        response = client.get("/dashboard/command-center", headers=_auth(token))

    assert response.status_code == 200
    body_text = json.dumps(response.json(), sort_keys=True).lower()
    assert "secret-value" not in body_text
    assert "secret-token" not in body_text
    assert "private_key" not in body_text
    assert "payload_json" not in body_text
    assert "metadata_json" not in body_text
    assert "raw" not in body_text
