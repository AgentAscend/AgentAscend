from __future__ import annotations

import os
from typing import Any

from backend.app.db.session import get_connection
from scripts.prod_readonly_audit import AuditConnection, _safe_unavailable

TASK_WORKER_JOB_ID = "default-task-queue-worker"
TASK_STATUS_KEYS = ("queued", "running", "pending_approval", "completed", "failed")
EXECUTION_STATUS_KEYS = ("queued", "pending", "running", "completed", "failed")
TRUTHY_VALUES = {"1", "true", "yes", "on"}


def _dialect_for_connection(conn: Any) -> str:
    return "postgres" if hasattr(conn, "_conn") else "sqlite"


def _set_read_only(conn: Any, dialect: str) -> None:
    if dialect == "postgres":
        raw_conn = getattr(conn, "_conn", None)
        if raw_conn is not None and hasattr(raw_conn, "set_session"):
            raw_conn.set_session(readonly=True, autocommit=False)
        conn.execute("SET LOCAL statement_timeout = '10s'")
        return

    conn.execute("PRAGMA query_only = ON")


def _rollback_and_close(conn: Any) -> None:
    try:
        rollback = getattr(conn, "rollback", None)
        if callable(rollback):
            rollback()
    finally:
        close = getattr(conn, "close", None)
        if callable(close):
            close()


def _safe_status_counts(status_counts: dict[str, int] | None, expected_statuses: tuple[str, ...]) -> dict[str, int]:
    result = {status: 0 for status in expected_statuses}
    result["other"] = 0
    if not status_counts:
        return result
    for status, count in status_counts.items():
        if status in result:
            result[status] += int(count)
        else:
            result["other"] += int(count)
    return result


def _count_by_status(audit: AuditConnection, table: str) -> dict[str, int] | None:
    if "status" not in audit.columns(table):
        return None
    rows = audit.execute(
        f"SELECT COALESCE(status, 'unknown') AS status_key, COUNT(*) AS count FROM {table} GROUP BY COALESCE(status, 'unknown')"
    ).fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


def _total_count(audit: AuditConnection, table: str) -> int | None:
    if not audit.table_exists(table):
        return None
    row = audit.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
    return int((row[0] if row else 0) or 0)


def _runtime_flag(name: str) -> tuple[bool, bool]:
    raw = os.getenv(name)
    present = raw is not None and raw.strip() != ""
    truthy = raw.strip().lower() in TRUTHY_VALUES if raw is not None else False
    return present, truthy


def _runtime_flags() -> dict[str, bool]:
    execution_present, execution_truthy = _runtime_flag("EXECUTION_LEDGER_ENABLED")
    scheduler_present, scheduler_truthy = _runtime_flag("SCHEDULER_EXECUTION_LEDGER_ENABLED")
    background_present, background_truthy = _runtime_flag("AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED")
    return {
        "execution_ledger_enabled_present": execution_present,
        "execution_ledger_enabled_truthy": execution_truthy,
        "scheduler_execution_ledger_enabled_present": scheduler_present,
        "scheduler_execution_ledger_enabled_truthy": scheduler_truthy,
        "task_worker_background_enabled_present": background_present,
        "task_worker_background_enabled_truthy": background_truthy,
    }


def _task_worker_summary(audit: AuditConnection) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "job_id": TASK_WORKER_JOB_ID,
        "enabled": None,
        "last_run_at_present": False,
        "recent_status": None,
        "recent_success_count": None,
    }
    scheduled_columns = audit.columns("scheduled_jobs")
    if {"id", "enabled"}.issubset(scheduled_columns):
        selected_columns = ["enabled"]
        if "last_run_at" in scheduled_columns:
            selected_columns.append("last_run_at")
        select_sql = ", ".join(selected_columns)
        row = audit.execute(
            f"SELECT {select_sql} FROM scheduled_jobs WHERE id = {audit.placeholder()} LIMIT 1",
            (TASK_WORKER_JOB_ID,),
        ).fetchone()
        if row is not None:
            row_values = {column: row[index] for index, column in enumerate(selected_columns)}
            summary["enabled"] = bool(row_values.get("enabled"))
            summary["last_run_at_present"] = bool(row_values.get("last_run_at"))

    job_run_columns = audit.columns("job_runs")
    if {"scheduled_job_id", "status", "started_at"}.issubset(job_run_columns):
        recent = audit.execute(
            f"""
            SELECT status
            FROM job_runs
            WHERE scheduled_job_id = {audit.placeholder()}
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (TASK_WORKER_JOB_ID,),
        ).fetchone()
        if recent is not None:
            summary["recent_status"] = str(recent[0])
        success = audit.execute(
            f"""
            SELECT COUNT(*)
            FROM job_runs
            WHERE scheduled_job_id = {audit.placeholder()} AND status = {audit.placeholder()}
            """,
            (TASK_WORKER_JOB_ID, "success"),
        ).fetchone()
        summary["recent_success_count"] = int((success[0] if success else 0) or 0)

    return summary


def _audit_connection(conn: Any, dialect: str) -> dict[str, Any]:
    audit = AuditConnection(conn, dialect)
    task_status_counts = _count_by_status(audit, "tasks")
    execution_status_counts = _count_by_status(audit, "executions")
    return {
        "status": "ok",
        "schema_version": 1,
        "tasks": {
            "total": _total_count(audit, "tasks"),
            "by_status": _safe_status_counts(task_status_counts, TASK_STATUS_KEYS),
        },
        "executions": {
            "total": _total_count(audit, "executions"),
            "by_status": _safe_status_counts(execution_status_counts, EXECUTION_STATUS_KEYS),
        },
        "task_worker": _task_worker_summary(audit),
        "runtime_flags": _runtime_flags(),
        "safety": {
            "raw_rows_returned": False,
            "raw_task_body_returned": False,
            "raw_task_output_returned": False,
            "raw_metadata_returned": False,
            "raw_payloads_returned": False,
            "db_url_printed": False,
            "secrets_printed": False,
            "read_only_mode": True,
        },
    }


def run_task_runtime_audit() -> dict[str, Any]:
    """Return aggregate-only task/runtime state for the runtime-worker push gate.

    The output is intentionally limited to counts/booleans. It must not return raw
    task rows, user IDs, agent IDs, task IDs, task body/output content,
    metadata/payload values, DB URLs, secrets, transaction payloads, or wallet data.
    """

    conn = None
    try:
        conn = get_connection()
        dialect = _dialect_for_connection(conn)
        _set_read_only(conn, dialect)
        return _audit_connection(conn, dialect)
    except Exception as exc:
        unavailable = _safe_unavailable(type(exc).__name__)
        unavailable.setdefault("safety", {})["read_only_mode"] = True
        return unavailable
    finally:
        if conn is not None:
            _rollback_and_close(conn)
