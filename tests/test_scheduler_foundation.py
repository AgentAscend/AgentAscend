import json
from pathlib import Path

from backend.app.db import session


def test_scheduler_tables_and_seed_jobs_are_created(tmp_path):
    db_path = tmp_path / "agentascend-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        with session.get_connection() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert "scheduled_jobs" in tables
            assert "job_runs" in tables
            assert "agent_findings" in tables

            jobs = conn.execute(
                "SELECT job_type, schedule_type, enabled, model_tier FROM scheduled_jobs"
            ).fetchall()
            job_types = {row[0] for row in jobs}
            assert "backend_health_check" in job_types
            assert "payment_route_audit" in job_types
            assert "telegram_status_summary" in job_types
            assert all(row[1] in {"interval", "cron"} for row in jobs)
            assert all(row[2] in {0, 1} for row in jobs)
            assert all(row[3] in {"cheap", "standard", "premium"} for row in jobs)
    finally:
        session.DB_PATH = original_db_path


def test_run_job_once_records_successful_run(tmp_path):
    db_path = tmp_path / "agentascend-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        from backend.app.services.job_runner import run_job_once

        with session.get_connection() as conn:
            job = conn.execute(
                "SELECT * FROM scheduled_jobs WHERE job_type = ?",
                ("git_status_summary",),
            ).fetchone()
            assert job is not None

        result = run_job_once(job["id"])
        assert result["status"] in {"success", "failed"}
        assert result["run_id"]

        with session.get_connection() as conn:
            run = conn.execute(
                "SELECT status, scheduled_job_id, output_summary FROM job_runs WHERE id = ?",
                (result["run_id"],),
            ).fetchone()
            assert run is not None
            assert run["scheduled_job_id"] == job["id"]
            assert run["status"] == result["status"]
            assert run["output_summary"] is not None
    finally:
        session.DB_PATH = original_db_path


def test_scheduler_execution_ledger_stays_off_without_narrow_flag(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    monkeypatch.delenv("SCHEDULER_EXECUTION_LEDGER_ENABLED", raising=False)
    db_path = tmp_path / "agentascend-scheduler-ledger-off.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        from backend.app.services.job_runner import run_job_once

        with session.get_connection() as conn:
            job = conn.execute("SELECT * FROM scheduled_jobs WHERE job_type = ?", ("git_status_summary",)).fetchone()
            assert job is not None

        result = run_job_once(job["id"])
        assert result["status"] == "success"

        with session.get_connection() as conn:
            run_count = conn.execute("SELECT COUNT(*) FROM job_runs WHERE id = ?", (result["run_id"],)).fetchone()[0]
            scheduler_execution_count = conn.execute(
                "SELECT COUNT(*) FROM executions WHERE source_type='scheduled_job_run' AND source_id=?",
                (result["run_id"],),
            ).fetchone()[0]
        assert run_count == 1
        assert scheduler_execution_count == 0
    finally:
        session.DB_PATH = original_db_path


def test_scheduler_execution_ledger_records_safe_system_run_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_EXECUTION_LEDGER_ENABLED", "true")
    db_path = tmp_path / "agentascend-scheduler-ledger-on.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        from backend.app.services.job_runner import run_job_once

        with session.get_connection() as conn:
            job = conn.execute("SELECT * FROM scheduled_jobs WHERE job_type = ?", ("git_status_summary",)).fetchone()
            assert job is not None

        result = run_job_once(job["id"])
        assert result["status"] == "success"

        with session.get_connection() as conn:
            execution = conn.execute(
                "SELECT * FROM executions WHERE source_type='scheduled_job_run' AND source_id=?",
                (result["run_id"],),
            ).fetchone()
            assert execution is not None
            events = conn.execute(
                "SELECT event_type, payload_json FROM execution_events WHERE execution_id=? ORDER BY id ASC",
                (execution["execution_id"],),
            ).fetchall()

        assert execution["user_id"] is None
        assert execution["agent_id"] is None
        assert execution["status"] == "completed"
        metadata = json.loads(execution["metadata_json"])
        assert metadata["run_id"] == result["run_id"]
        assert metadata["scheduled_job_id"] == job["id"]
        assert metadata["job_type"] == "git_status_summary"
        assert metadata["final_status"] == "success"
        assert metadata["has_error"] is False
        assert isinstance(metadata["output_summary_length"], int)
        metadata_text = json.dumps(metadata).lower()
        assert "git branch=" not in metadata_text
        for word in "error_message token password secret database_url raw_request raw_response authorization prompt raw_tool_output".split():
            assert word not in metadata_text
        assert [event["event_type"] for event in events] == ["scheduler_job_started", "scheduler_job_completed"]
    finally:
        session.DB_PATH = original_db_path


def test_scheduler_execution_ledger_failed_run_event_is_safe(tmp_path, monkeypatch):
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "true")
    monkeypatch.setenv("SCHEDULER_EXECUTION_LEDGER_ENABLED", "true")
    db_path = tmp_path / "agentascend-scheduler-ledger-failed.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        from backend.app.services import job_runner

        def fake_urlopen(*_args, **_kwargs):
            raise TimeoutError("health timed out with raw secret text")

        monkeypatch.setattr(job_runner, "urlopen", fake_urlopen)
        monkeypatch.setattr(job_runner, "_send_telegram_notification", lambda _message: {"enabled": True, "sent": True})

        with session.get_connection() as conn:
            job = conn.execute("SELECT * FROM scheduled_jobs WHERE job_type = ?", ("backend_health_check",)).fetchone()
            assert job is not None

        result = job_runner.run_job_once(job["id"])
        assert result["status"] == "failed"

        with session.get_connection() as conn:
            execution = conn.execute(
                "SELECT * FROM executions WHERE source_type='scheduled_job_run' AND source_id=?",
                (result["run_id"],),
            ).fetchone()
            assert execution is not None
            failed_event = conn.execute(
                "SELECT payload_json FROM execution_events WHERE execution_id=? AND event_type='scheduler_job_failed'",
                (execution["execution_id"],),
            ).fetchone()

        assert execution["status"] == "failed"
        payload = json.loads(failed_event["payload_json"])
        assert payload["run_id"] == result["run_id"]
        assert payload["final_status"] == "failed"
        assert payload["has_error"] is True
        payload_text = json.dumps(payload).lower()
        assert "health timed out" not in payload_text
        assert "raw secret text" not in payload_text
        assert "error_message" not in payload_text
    finally:
        session.DB_PATH = original_db_path


def test_scheduler_ledger_metadata_builder_rejects_sensitive_result_keys():
    from backend.app.services import job_runner

    job = {
        "id": "job_sensitive",
        "job_type": "git_status_summary",
        "schedule_type": "interval",
        "model_tier": "cheap",
        "priority": 10,
        "created_by": "system",
    }
    result = {
        "status": "success",
        "summary": "safe summary body must not be stored",
        "error": "raw error must not be stored",
        "metadata": {
            "token": "should-not-pass-through",
            "authorization": "Bearer should-not-pass-through",
            "api_key": "should-not-pass-through",
            "secret": "should-not-pass-through",
            "password": "should-not-pass-through",
            "database_url": "should-not-pass-through",
            "private_key": "should-not-pass-through",
            "raw_request": "should-not-pass-through",
            "raw_response": "should-not-pass-through",
            "request_body": "should-not-pass-through",
            "response_body": "should-not-pass-through",
        },
    }

    metadata = job_runner._build_scheduler_ledger_metadata(
        job,
        "run_sensitive",
        "2026-01-01T00:00:00+00:00",
        finished_at="2026-01-01T00:00:01+00:00",
        result=result,
    )

    metadata_text = json.dumps(metadata).lower()
    assert metadata["output_summary_length"] == len(result["summary"])
    assert metadata["has_error"] is True
    for word in [
        "token",
        "authorization",
        "api_key",
        "secret",
        "password",
        "database_url",
        "private_key",
        "raw_request",
        "raw_response",
        "request_body",
        "response_body",
        "safe summary body",
        "raw error",
    ]:
        assert word not in metadata_text


def test_spawned_jobs_are_disabled_by_default_and_deduplicated(tmp_path):
    db_path = tmp_path / "agentascend-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        from backend.app.services.scheduler_service import create_suggested_job

        first = create_suggested_job(
            name="Review suspicious payment retries",
            description="Investigate retry spike before any code changes.",
            job_type="suggested_payment_retry_review",
            reason="payment route audit noticed retry growth",
            source_job_id="default-payment-route-audit",
            priority=80,
            risk_level="high",
        )
        second = create_suggested_job(
            name="Review suspicious payment retries",
            description="Duplicate should not create a second row.",
            job_type="suggested_payment_retry_review",
            reason="same finding",
            source_job_id="default-payment-route-audit",
            priority=80,
            risk_level="high",
        )
        assert first["id"] == second["id"]
        assert first["enabled"] == 0
        assert first["metadata"]["risk_level"] == "high"

        with session.get_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM scheduled_jobs WHERE job_type = ?",
                ("suggested_payment_retry_review",),
            ).fetchone()[0]
            assert count == 1
    finally:
        session.DB_PATH = original_db_path



def test_jobs_api_fails_closed_in_production_without_admin_token(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.delenv("AGENT_RUNTIME_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    from backend.app.main import app

    response = TestClient(app).get("/jobs")
    assert response.status_code == 503
    assert "AGENT_RUNTIME_ADMIN_TOKEN" in response.text


def test_jobs_api_requires_configured_admin_token(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AGENT_RUNTIME_ADMIN_TOKEN", "test-runtime-token")

    from backend.app.main import app

    client = TestClient(app)
    assert client.get("/jobs").status_code == 403
    assert client.get("/jobs", headers={"X-Agent-Runtime-Token": "wrong"}).status_code == 403
    assert client.get("/jobs", headers={"X-Agent-Runtime-Token": "test-runtime-token"}).status_code == 200


def test_jobs_api_allows_safe_local_dev_without_admin_token(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.delenv("AGENT_RUNTIME_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AGENT_RUNTIME_SAFE_MODE", "true")

    from backend.app.main import app

    response = TestClient(app).get("/jobs")
    assert response.status_code == 200


def test_failed_jobs_send_telegram_alert_without_crashing(tmp_path, monkeypatch):
    import json

    db_path = tmp_path / "agentascend-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()

        from backend.app.services import job_runner

        sent_messages = []

        def fake_send_telegram_notification(message):
            sent_messages.append(message)
            return {"enabled": True, "sent": True, "status_code": 200}

        def fake_urlopen(_url, timeout=10):
            raise TimeoutError("health timed out")

        monkeypatch.setattr(job_runner, "_send_telegram_notification", fake_send_telegram_notification)
        monkeypatch.setattr(job_runner, "urlopen", fake_urlopen)

        with session.get_connection() as conn:
            job = conn.execute(
                "SELECT * FROM scheduled_jobs WHERE job_type = ?",
                ("backend_health_check",),
            ).fetchone()
            assert job is not None

        result = job_runner.run_job_once(job["id"])
        assert result["status"] == "failed"
        assert len(sent_messages) == 1
        assert "AgentAscend scheduler job failed" in sent_messages[0]
        assert "Backend health check" in sent_messages[0]
        assert "default-backend-health-check" in sent_messages[0]
        assert "Backend health failed" in sent_messages[0]

        with session.get_connection() as conn:
            run = conn.execute(
                "SELECT metadata_json FROM job_runs WHERE id = ?",
                (result["run_id"],),
            ).fetchone()
        metadata = json.loads(run["metadata_json"])
        assert metadata["telegram_failure_alert"]["sent"] is True
    finally:
        session.DB_PATH = original_db_path


def test_successful_non_telegram_jobs_do_not_send_telegram_alert(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()

        from backend.app.services import job_runner

        sent_messages = []
        monkeypatch.setattr(
            job_runner,
            "_send_telegram_notification",
            lambda message: sent_messages.append(message) or {"enabled": True, "sent": True},
        )

        with session.get_connection() as conn:
            job = conn.execute(
                "SELECT * FROM scheduled_jobs WHERE job_type = ?",
                ("git_status_summary",),
            ).fetchone()
            assert job is not None

        result = job_runner.run_job_once(job["id"])
        assert result["status"] == "success"
        assert sent_messages == []
    finally:
        session.DB_PATH = original_db_path


def test_backend_health_uses_agentascend_health_url_and_records_metadata(tmp_path, monkeypatch):
    import json

    db_path = tmp_path / "agentascend-test.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    monkeypatch.setenv("AGENTASCEND_HEALTH_URL", "https://api.agentascend.ai/health")
    try:
        session.init_db()

        from backend.app.services import job_runner

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self, _limit):
                return b'{"status":"ok"}'

        requested_urls = []

        def fake_urlopen(url, timeout=10):
            requested_urls.append(url)
            return FakeResponse()

        monkeypatch.setattr(job_runner, "urlopen", fake_urlopen)

        with session.get_connection() as conn:
            job = conn.execute(
                "SELECT * FROM scheduled_jobs WHERE job_type = ?",
                ("backend_health_check",),
            ).fetchone()
            assert job is not None

        result = job_runner.run_job_once(job["id"])
        assert result["status"] == "success"
        assert requested_urls == ["https://api.agentascend.ai/health"]

        with session.get_connection() as conn:
            run = conn.execute(
                "SELECT metadata_json FROM job_runs WHERE id = ?",
                (result["run_id"],),
            ).fetchone()
        metadata = json.loads(run["metadata_json"])
        assert metadata["url"] == "https://api.agentascend.ai/health"
        assert metadata["active_url"] == "https://api.agentascend.ai/health"
        assert metadata["url_source"] == "AGENTASCEND_HEALTH_URL"
    finally:
        session.DB_PATH = original_db_path
