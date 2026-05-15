import json

from fastapi.testclient import TestClient

from backend.app.db import session
from backend.app.main import app


ADMIN_TOKEN = "test-admin-token"
SENSITIVE_RESPONSE_MARKERS = [
    "metadata_json",
    "payload_json",
    "postgres://",
    "postgresql://",
    "DATABASE_URL",
    "SOLANA_RPC_URL",
    "QUICKNODE",
    "auth token",
    "cookie",
    "txBase64",
    "signed transaction",
    "private_key",
    "seed phrase",
    "raw-metadata-secret",
    "raw request body secret",
    "raw response body secret",
    "raw task output secret",
    "wallet-private-secret",
]


def _client_with_db(tmp_path, monkeypatch, *, token=ADMIN_TOKEN):
    db_path = tmp_path / "agentascend-ops-audit-events-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENT_RUNTIME_ADMIN_TOKEN", token)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_SERVICE_ID", raising=False)
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_ID", raising=False)
    client = TestClient(app)
    return client, original_db_path


def _restore_db_path(original_db_path):
    session.DB_PATH = original_db_path


def _insert_audit_event(event_id: str, metadata: dict):
    with session.get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_events(event_id, actor_user_id, event_type, target_type, target_id, metadata_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                event_id,
                "private-user-1",
                "task.output.created",
                "task",
                "private-task-1",
                json.dumps(metadata),
            ),
        )
        conn.commit()


def test_ops_audit_events_requires_runtime_admin_token(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        session.init_db()

        response = client.get("/ops/audit-events")
        assert response.status_code == 403

        response = client.get(
            "/ops/audit-events",
            headers={"Authorization": "Bearer normal-user-token"},
        )
        assert response.status_code == 403

        response = client.get(
            "/ops/audit-events",
            headers={"X-Agent-Runtime-Token": "wrong-token"},
        )
        assert response.status_code == 403
    finally:
        _restore_db_path(original_db_path)


def test_ops_audit_events_valid_runtime_admin_token_returns_sanitized_events(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        session.init_db()
        _insert_audit_event(
            "audit_private_1",
            {
                "safe_category": "runtime",
                "raw_secret": "raw-metadata-secret",
                "request_body": "raw request body secret",
                "response_body": "raw response body secret",
                "task_output": "raw task output secret",
                "wallet_private": "wallet-private-secret",
            },
        )

        response = client.get(
            "/ops/audit-events",
            headers={"X-Agent-Runtime-Token": ADMIN_TOKEN},
        )
        assert response.status_code == 200
        payload = response.json()

        assert payload["status"] == "ok"
        assert len(payload["events"]) == 1
        event = payload["events"][0]
        assert event["event_id"] == "audit_private_1"
        assert event["actor_user_id"] == "private-user-1"
        assert event["event_type"] == "task.output.created"
        assert event["target_type"] == "task"
        assert event["target_id"] == "private-task-1"
        assert "created_at" in event
        assert "metadata_json" not in event
        assert "metadata" not in event
        assert event["metadata_keys"] == [
            "raw_secret",
            "request_body",
            "response_body",
            "safe_category",
            "task_output",
            "wallet_private",
        ]

        response_text = json.dumps(payload)
        for marker in SENSITIVE_RESPONSE_MARKERS:
            assert marker not in response_text
    finally:
        _restore_db_path(original_db_path)


def test_ops_audit_events_limit_remains_bounded(tmp_path, monkeypatch):
    client, original_db_path = _client_with_db(tmp_path, monkeypatch)
    try:
        session.init_db()
        _insert_audit_event("audit_private_1", {"category": "one"})
        _insert_audit_event("audit_private_2", {"category": "two"})

        limited_response = client.get(
            "/ops/audit-events?limit=1",
            headers={"X-Agent-Runtime-Token": ADMIN_TOKEN},
        )
        assert limited_response.status_code == 200
        assert len(limited_response.json()["events"]) == 1

        min_bounded_response = client.get(
            "/ops/audit-events?limit=0",
            headers={"X-Agent-Runtime-Token": ADMIN_TOKEN},
        )
        assert min_bounded_response.status_code == 200
        assert len(min_bounded_response.json()["events"]) == 1

        max_bounded_response = client.get(
            "/ops/audit-events?limit=5000",
            headers={"X-Agent-Runtime-Token": ADMIN_TOKEN},
        )
        assert max_bounded_response.status_code == 200
        assert len(max_bounded_response.json()["events"]) == 2
    finally:
        _restore_db_path(original_db_path)
