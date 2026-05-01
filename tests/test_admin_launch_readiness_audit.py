import json

from fastapi.testclient import TestClient

from backend.app.db import session
from backend.app.main import app


SENSITIVE_MARKERS = [
    "metadata_json",
    "payload_json",
    "postgres://",
    "postgresql://",
    "DATABASE_URL",
    "SOLANA_RPC_URL",
    "QUICKNODE",
    "auth token",
    "txBase64",
    "signed transaction",
    "private_key",
    "secretKey",
    "raw-metadata-secret",
    "raw-payload-secret",
]


def _client_with_db(tmp_path, monkeypatch, *, token="test-admin-token", production=False):
    db_path = tmp_path / "agentascend-audit-test.db"
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


def test_launch_readiness_audit_requires_admin_token(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        response = client.get("/admin/audits/launch-readiness/aggregate")
        assert response.status_code == 403

        response = client.get(
            "/admin/audits/launch-readiness/aggregate",
            headers={"X-Agent-Runtime-Token": "wrong-token"},
        )
        assert response.status_code == 403
    finally:
        _restore_db_path(original_db_path)


def test_launch_readiness_audit_fails_closed_without_token_in_production(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-audit-prod-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AGENT_RUNTIME_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    client = TestClient(app)
    try:
        response = client.get("/admin/audits/launch-readiness/aggregate")
        assert response.status_code == 503
    finally:
        _restore_db_path(original_db_path)


def test_launch_readiness_audit_returns_safe_aggregate_json(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        session.init_db()
        with session.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO executions(execution_id, source_type, source_id, user_id, agent_id, status, started_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, ?, datetime('now'), ?)
                """,
                (
                    "exec_audit_1",
                    "scheduled_job_run",
                    "run_audit_1",
                    None,
                    None,
                    "completed",
                    json.dumps({"leak": "raw-metadata-secret"}),
                ),
            )
            conn.execute(
                """
                INSERT INTO execution_events(event_id, execution_id, event_type, created_at, payload_json)
                VALUES(?, ?, ?, datetime('now'), ?)
                """,
                (
                    "event_audit_1",
                    "exec_audit_1",
                    "scheduler_job_completed",
                    json.dumps({"leak": "raw-payload-secret"}),
                ),
            )
            conn.execute(
                """
                INSERT INTO execution_artifacts(artifact_id, execution_id, artifact_type, name, content_text, created_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, datetime('now'), ?)
                """,
                (
                    "artifact_audit_1",
                    "exec_audit_1",
                    "text",
                    "audit-artifact",
                    "safe content",
                    json.dumps({"leak": "raw-metadata-secret"}),
                ),
            )
            conn.commit()

        response = client.get(
            "/admin/audits/launch-readiness/aggregate",
            headers={"X-Agent-Runtime-Token": "test-admin-token"},
        )
        assert response.status_code == 200
        payload = response.json()

        assert set(payload) >= {"schema_version", "scheduler", "execution_ledger", "payments", "access", "marketplace", "safety"}
        assert payload["safety"] == {
            "raw_metadata_returned": False,
            "raw_payloads_returned": False,
            "db_url_printed": False,
            "secrets_printed": False,
            "read_only_mode": True,
        }
        assert payload["scheduler"]["scheduler_artifacts_count"] >= 1
        assert payload["scheduler"]["scheduler_content_text_nonempty_count"] >= 1
        assert payload["scheduler"]["orphan_execution_events_count"] == 0
        assert payload["scheduler"]["orphan_execution_artifacts_count"] == 0
        assert payload["scheduler"]["scheduled_job_run_user_id_not_null_count"] == 0
        assert payload["scheduler"]["scheduled_job_run_agent_id_not_null_count"] == 0

        text = json.dumps(payload)
        for marker in SENSITIVE_MARKERS:
            assert marker not in text
    finally:
        _restore_db_path(original_db_path)


def test_launch_readiness_audit_does_not_write_to_db(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        session.init_db()
        with session.get_connection() as conn:
            before = {
                "scheduled_jobs": conn.execute("SELECT COUNT(*) FROM scheduled_jobs").fetchone()[0],
                "executions": conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0],
                "payment_intents": conn.execute("SELECT COUNT(*) FROM payment_intents").fetchone()[0],
                "payments": conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0],
                "access_grants": conn.execute("SELECT COUNT(*) FROM access_grants").fetchone()[0],
                "marketplace_entitlements": conn.execute("SELECT COUNT(*) FROM marketplace_entitlements").fetchone()[0],
            }

        response = client.get(
            "/admin/audits/launch-readiness/aggregate",
            headers={"X-Agent-Runtime-Token": "test-admin-token"},
        )
        assert response.status_code == 200

        with session.get_connection() as conn:
            after = {
                "scheduled_jobs": conn.execute("SELECT COUNT(*) FROM scheduled_jobs").fetchone()[0],
                "executions": conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0],
                "payment_intents": conn.execute("SELECT COUNT(*) FROM payment_intents").fetchone()[0],
                "payments": conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0],
                "access_grants": conn.execute("SELECT COUNT(*) FROM access_grants").fetchone()[0],
                "marketplace_entitlements": conn.execute("SELECT COUNT(*) FROM marketplace_entitlements").fetchone()[0],
            }
        assert after == before
    finally:
        _restore_db_path(original_db_path)


def test_launch_readiness_audit_handles_missing_optional_tables(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        # Deliberately do not call init_db; the route should return a safe aggregate shape
        # rather than crash when optional audit tables are absent.
        response = client.get(
            "/admin/audits/launch-readiness/aggregate",
            headers={"X-Agent-Runtime-Token": "test-admin-token"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["scheduler"]["enabled_jobs_by_type"] is None
        assert payload["payments"]["payment_intents_count_by_status"] is None
        assert payload["safety"]["read_only_mode"] is True
    finally:
        _restore_db_path(original_db_path)


def test_health_and_openapi_include_launch_readiness_audit_endpoint(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        assert client.get("/health").status_code == 200
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200
        assert "/admin/audits/launch-readiness/aggregate" in openapi_response.json()["paths"]
    finally:
        _restore_db_path(original_db_path)
