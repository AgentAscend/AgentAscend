import json

from fastapi.testclient import TestClient

from backend.app.db import session
from backend.app.main import app


SENSITIVE_MARKERS = [
    "metadata_json",
    "payload_json",
    "task-private-id",
    "user-private",
    "agent-private",
    "raw-task-body-secret",
    "raw-task-output-secret",
    "raw-metadata-secret",
    "raw-payload-secret",
    "postgres://",
    "postgresql://",
    "DATABASE_URL",
    "SOLANA_RPC_URL",
    "QUICKNODE",
    "auth token",
    "cookie",
    "private_key",
    "seed phrase",
    "txBase64",
    "signed transaction",
]


def _client_with_db(tmp_path, monkeypatch, *, token="test-admin-token", production=False):
    db_path = tmp_path / "agentascend-task-runtime-audit-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENT_RUNTIME_ADMIN_TOKEN", token)
    if production:
        monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    else:
        monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
        monkeypatch.delenv("RAILWAY_SERVICE_ID", raising=False)
        monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_ID", raising=False)
    client = TestClient(app)
    return client, original_db_path


def _restore_db_path(original_db_path):
    session.DB_PATH = original_db_path


def test_task_runtime_aggregate_requires_admin_token(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        response = client.get("/admin/audits/task-runtime/aggregate")
        assert response.status_code == 403

        response = client.get(
            "/admin/audits/task-runtime/aggregate",
            headers={"X-Agent-Runtime-Token": "wrong-token"},
        )
        assert response.status_code == 403
    finally:
        _restore_db_path(original_db_path)


def test_task_runtime_aggregate_fails_closed_without_token_in_production(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-task-runtime-audit-prod-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENT_RUNTIME_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    client = TestClient(app)
    try:
        response = client.get("/admin/audits/task-runtime/aggregate")
        assert response.status_code == 503
    finally:
        _restore_db_path(original_db_path)


def test_task_runtime_aggregate_returns_safe_task_execution_scheduler_and_flag_counts(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_EXECUTION_LEDGER_ENABLED", "1")
    monkeypatch.setenv("AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED", "0")
    try:
        session.init_db()
        with session.get_connection() as conn:
            for index, status in enumerate(["queued", "running", "pending_approval", "completed", "failed", "custom_status"]):
                conn.execute(
                    """
                    INSERT INTO tasks(task_id, user_id, agent_id, type, title, status, priority, assigned_to, error_message, updated_at)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        f"task-private-id-{index}",
                        f"user-private-{index}",
                        f"agent-private-{index}",
                        "general",
                        f"private task title {index} raw-task-body-secret",
                        status,
                        "medium",
                        f"agent-private-{index}",
                        "raw-task-output-secret",
                    ),
                )
            for index, status in enumerate(["pending", "queued", "running", "completed", "failed"]):
                conn.execute(
                    """
                    INSERT INTO executions(execution_id, source_type, source_id, user_id, agent_id, status, started_at, metadata_json)
                    VALUES(?, ?, ?, ?, ?, ?, datetime('now'), ?)
                    """,
                    (
                        f"exec-private-id-{index}",
                        "task",
                        f"task-private-id-{index}",
                        f"user-private-{index}",
                        f"agent-private-{index}",
                        status,
                        json.dumps({"leak": "raw-metadata-secret"}),
                    ),
                )
            conn.execute(
                """
                UPDATE scheduled_jobs
                SET enabled = 1, last_run_at = datetime('now')
                WHERE id = ?
                """,
                ("default-task-queue-worker",),
            )
            conn.execute(
                """
                INSERT INTO job_runs(id, scheduled_job_id, started_at, finished_at, status, output_summary, error_message, metadata_json)
                VALUES(?, ?, datetime('now', '-3 minutes'), datetime('now', '-2 minutes'), ?, ?, ?, ?)
                """,
                (
                    "run-private-id-success",
                    "default-task-queue-worker",
                    "success",
                    "raw-task-output-secret",
                    None,
                    json.dumps({"leak": "raw-payload-secret"}),
                ),
            )
            conn.execute(
                """
                INSERT INTO job_runs(id, scheduled_job_id, started_at, finished_at, status, output_summary, error_message, metadata_json)
                VALUES(?, ?, datetime('now', '-1 minutes'), datetime('now'), ?, ?, ?, ?)
                """,
                (
                    "run-private-id-failed",
                    "default-task-queue-worker",
                    "failed",
                    None,
                    "raw-task-output-secret",
                    json.dumps({"leak": "raw-payload-secret"}),
                ),
            )
            conn.commit()

        response = client.get(
            "/admin/audits/task-runtime/aggregate",
            headers={"X-Agent-Runtime-Token": "test-admin-token"},
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["status"] == "ok"
        assert payload["schema_version"] == 1
        assert payload["tasks"]["total"] == 6
        assert payload["tasks"]["by_status"] == {
            "queued": 1,
            "running": 1,
            "pending_approval": 1,
            "completed": 1,
            "failed": 1,
            "other": 1,
        }
        assert payload["executions"]["total"] == 5
        assert payload["executions"]["by_status"] == {
            "queued": 1,
            "pending": 1,
            "running": 1,
            "completed": 1,
            "failed": 1,
            "other": 0,
        }
        assert payload["task_worker"] == {
            "job_id": "default-task-queue-worker",
            "enabled": True,
            "last_run_at_present": True,
            "recent_status": "failed",
            "recent_success_count": 1,
        }
        assert payload["runtime_flags"] == {
            "execution_ledger_enabled_present": True,
            "execution_ledger_enabled_truthy": True,
            "scheduler_execution_ledger_enabled_present": True,
            "scheduler_execution_ledger_enabled_truthy": True,
            "task_worker_background_enabled_present": True,
            "task_worker_background_enabled_truthy": False,
        }
        assert payload["safety"] == {
            "raw_rows_returned": False,
            "raw_task_body_returned": False,
            "raw_task_output_returned": False,
            "raw_metadata_returned": False,
            "raw_payloads_returned": False,
            "db_url_printed": False,
            "secrets_printed": False,
            "read_only_mode": True,
        }

        text = json.dumps(payload)
        for marker in SENSITIVE_MARKERS:
            assert marker not in text
    finally:
        _restore_db_path(original_db_path)


def test_task_runtime_aggregate_handles_missing_optional_tables(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        response = client.get(
            "/admin/audits/task-runtime/aggregate",
            headers={"X-Agent-Runtime-Token": "test-admin-token"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["tasks"] == {
            "total": None,
            "by_status": {
                "queued": 0,
                "running": 0,
                "pending_approval": 0,
                "completed": 0,
                "failed": 0,
                "other": 0,
            },
        }
        assert payload["task_worker"]["enabled"] is None
        assert payload["safety"]["read_only_mode"] is True
    finally:
        _restore_db_path(original_db_path)


def test_task_runtime_aggregate_does_not_write_to_db(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        session.init_db()
        with session.get_connection() as conn:
            before = {
                "scheduled_jobs": conn.execute("SELECT COUNT(*) FROM scheduled_jobs").fetchone()[0],
                "job_runs": conn.execute("SELECT COUNT(*) FROM job_runs").fetchone()[0],
                "tasks": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
                "executions": conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0],
            }

        response = client.get(
            "/admin/audits/task-runtime/aggregate",
            headers={"X-Agent-Runtime-Token": "test-admin-token"},
        )
        assert response.status_code == 200

        with session.get_connection() as conn:
            after = {
                "scheduled_jobs": conn.execute("SELECT COUNT(*) FROM scheduled_jobs").fetchone()[0],
                "job_runs": conn.execute("SELECT COUNT(*) FROM job_runs").fetchone()[0],
                "tasks": conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
                "executions": conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0],
            }
        assert after == before
    finally:
        _restore_db_path(original_db_path)


def test_health_and_openapi_include_task_runtime_aggregate_endpoint(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        assert client.get("/health").status_code == 200
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200
        paths = openapi_response.json()["paths"]
        assert "/admin/audits/task-runtime/aggregate" in paths
    finally:
        _restore_db_path(original_db_path)
