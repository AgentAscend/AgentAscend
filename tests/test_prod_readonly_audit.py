from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "prod_readonly_audit.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("prod_readonly_audit", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def init_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE scheduled_jobs (
                id TEXT PRIMARY KEY,
                job_type TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE job_runs (
                id TEXT PRIMARY KEY,
                scheduled_job_id TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                output_summary TEXT,
                error_message TEXT,
                metadata_json TEXT
            );
            CREATE TABLE executions (
                execution_id TEXT PRIMARY KEY,
                source_type TEXT,
                user_id TEXT,
                agent_id TEXT,
                status TEXT NOT NULL
            );
            CREATE TABLE execution_events (
                event_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                payload_json TEXT
            );
            CREATE TABLE execution_artifacts (
                artifact_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                content_text TEXT,
                metadata_json TEXT
            );
            CREATE TABLE payment_intents (
                reference TEXT PRIMARY KEY,
                status TEXT,
                tx_signature TEXT,
                expires_at DATETIME
            );
            CREATE TABLE payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                tx_signature TEXT,
                intent_reference TEXT
            );
            CREATE TABLE access_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                status TEXT NOT NULL,
                payment_id INTEGER,
                intent_reference TEXT,
                metadata_json TEXT
            );
            CREATE TABLE marketplace_entitlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                user_id TEXT NOT NULL
            );
            CREATE TABLE creator_earnings_events (id INTEGER PRIMARY KEY AUTOINCREMENT);
            CREATE TABLE creator_payout_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL
            );
            """
        )
        conn.executemany(
            "INSERT INTO scheduled_jobs (id, job_type, enabled) VALUES (?, ?, ?)",
            [
                ("default-backend-health-check", "backend_health_check", 1),
                ("default-payment-route-audit", "payment_route_audit", 0),
            ],
        )
        conn.executemany(
            "INSERT INTO job_runs (id, scheduled_job_id, status, started_at, output_summary, error_message, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("run-1", "default-backend-health-check", "succeeded", "2026-04-30T00:00:00Z", "SECRET_OUTPUT", "RAW_ERROR", '{"secret":"do-not-return"}'),
                ("run-2", "default-payment-route-audit", "failed", "2026-04-30T00:01:00Z", "SECRET_OUTPUT", "RAW_ERROR", '{"secret":"do-not-return"}'),
            ],
        )
        conn.executemany(
            "INSERT INTO executions (execution_id, source_type, user_id, agent_id, status) VALUES (?, ?, ?, ?, ?)",
            [
                ("exec-1", "scheduled_job_run", "user-private", None, "completed"),
                ("exec-2", "manual", None, "agent-private", "failed"),
            ],
        )
        conn.executemany(
            "INSERT INTO execution_events (event_id, execution_id, payload_json) VALUES (?, ?, ?)",
            [("event-1", "exec-1", '{"raw":"secret"}'), ("event-orphan", "missing", '{"raw":"secret"}')],
        )
        conn.executemany(
            "INSERT INTO execution_artifacts (artifact_id, execution_id, content_text, metadata_json) VALUES (?, ?, ?, ?)",
            [("artifact-1", "exec-1", "artifact text", '{"raw":"secret"}'), ("artifact-orphan", "missing", "", '{"raw":"secret"}')],
        )
        conn.executemany(
            "INSERT INTO payment_intents (reference, status, tx_signature, expires_at) VALUES (?, ?, ?, ?)",
            [("intent-1", "pending", "dupe-intent", "2000-01-01T00:00:00Z"), ("intent-2", "pending", "dupe-intent", "2000-01-01T00:00:00Z")],
        )
        conn.executemany(
            "INSERT INTO payments (status, tx_signature, intent_reference) VALUES (?, ?, ?)",
            [("completed", "dupe-payment", "intent-1"), ("completed", "dupe-payment", None), ("failed", "unique", None)],
        )
        conn.executemany(
            "INSERT INTO access_grants (user_id, feature_name, status, payment_id, intent_reference, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("user-1", "feature", "active", 1, "intent-1", '{"raw":"secret"}'),
                ("user-1", "feature", "active", 1, "intent-1", '{"raw":"secret"}'),
                ("user-2", "feature", "active", None, None, '{"raw":"secret"}'),
                ("user-3", "feature", "revoked", None, None, '{"raw":"secret"}'),
            ],
        )
        conn.executemany(
            "INSERT INTO marketplace_entitlements (listing_id, user_id) VALUES (?, ?)",
            [("listing-1", "user-1"), ("listing-1", "user-1"), ("listing-2", "user-2")],
        )
        conn.executemany("INSERT INTO creator_earnings_events (id) VALUES (?)", [(1,), (2,)])
        conn.executemany("INSERT INTO creator_payout_requests (status) VALUES (?)", [("pending",), ("paid",), ("pending",)])


def test_audit_returns_aggregate_json_without_raw_sensitive_values(tmp_path):
    db_path = tmp_path / "audit.db"
    init_db(db_path)
    module = load_audit_module()

    result = module.audit_sqlite_path(db_path)

    assert result["safety"] == {
        "raw_metadata_returned": False,
        "raw_payloads_returned": False,
        "db_url_printed": False,
        "secrets_printed": False,
        "read_only_mode": True,
    }
    assert result["scheduler"]["enabled_jobs_by_type"] == {"backend_health_check": 1}
    assert result["scheduler"]["disabled_held_jobs_by_type"] == {"payment_route_audit": 1}
    assert result["scheduler"]["recent_job_runs_by_type_status"] == {
        "backend_health_check:succeeded": 1,
        "payment_route_audit:failed": 1,
    }
    assert result["scheduler"]["orphan_execution_events_count"] == 1
    assert result["scheduler"]["orphan_execution_artifacts_count"] == 1
    assert result["scheduler"]["scheduler_content_text_nonempty_count"] == 1
    assert result["execution_ledger"]["executions_count_by_source_type"] == {"manual": 1, "scheduled_job_run": 1}
    assert result["payments"]["duplicate_payment_tx_signature_groups"] == 1
    assert result["payments"]["duplicate_payment_intent_tx_signature_groups"] == 1
    assert result["access"]["active_access_grants_count"] == 3
    assert result["access"]["duplicate_active_grant_groups"] == 1
    assert result["marketplace"]["marketplace_entitlements_count"] == 3
    assert result["marketplace"]["duplicate_listing_user_entitlements"] == 1
    assert result["marketplace"]["payout_requests_count_by_status"] == {"paid": 1, "pending": 2}

    encoded = json.dumps(result, sort_keys=True)
    assert "SECRET_OUTPUT" not in encoded
    assert "RAW_ERROR" not in encoded
    assert "do-not-return" not in encoded
    assert "user-private" not in encoded
    assert "agent-private" not in encoded


def test_audit_handles_empty_or_missing_optional_tables(tmp_path):
    db_path = tmp_path / "minimal.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE payments (id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT NOT NULL)")

    module = load_audit_module()
    result = module.audit_sqlite_path(db_path)

    assert result["payments"]["payments_count_by_status"] == {}
    assert result["payments"]["duplicate_payment_tx_signature_groups"] is None
    assert result["scheduler"]["enabled_jobs_by_type"] is None
    assert result["access"]["active_access_grants_count"] is None
    assert result["marketplace"]["marketplace_entitlements_count"] is None
    assert result["safety"]["read_only_mode"] is True


def test_audit_sqlite_path_opens_database_read_only(tmp_path):
    db_path = tmp_path / "readonly.db"
    init_db(db_path)
    module = load_audit_module()

    before = db_path.read_bytes()
    result = module.audit_sqlite_path(db_path)
    after = db_path.read_bytes()

    assert result["safety"]["read_only_mode"] is True
    assert after == before
