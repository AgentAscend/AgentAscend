#!/usr/bin/env python3
"""Aggregate-only production launch-readiness audit helper.

This helper is intentionally read-only and emits counts/booleans only. It must not
print connection strings, raw metadata/payloads, request/response bodies, raw
scheduler output, raw errors, wallet-private data, signed transactions, or txBase64.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

HELD_JOB_TYPES = {
    "payment_route_audit",
    "failed_payment_replay_review",
    "access_grant_integrity_check",
    "telegram_status_summary",
    "task_queue_worker",
    "git_status_summary",
    "roadmap_review",
}

SENSITIVE_ERROR_TYPES = {
    "OperationalError",
    "InterfaceError",
    "DatabaseError",
    "ImportError",
    "ModuleNotFoundError",
    "FileNotFoundError",
    "ValueError",
}


class AuditConnection:
    def __init__(self, conn: Any, dialect: str):
        self.conn = conn
        self.dialect = dialect

    def execute(self, sql: str, params: Iterable[Any] | None = None):
        return self.conn.execute(sql, tuple(params or ()))

    def placeholder(self) -> str:
        return "%s" if self.dialect == "postgres" else "?"

    def table_exists(self, table: str) -> bool:
        if self.dialect == "postgres":
            row = self.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s LIMIT 1",
                (table,),
            ).fetchone()
            return row is not None
        row = self.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)).fetchone()
        return row is not None

    def columns(self, table: str) -> set[str]:
        if not self.table_exists(table):
            return set()
        if self.dialect == "postgres":
            rows = self.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
                (table,),
            ).fetchall()
            return {str(row[0]) for row in rows}
        rows = self.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row[1]) for row in rows}


def _safe_unavailable(error_type: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "stage": "connect_or_query",
        "error_type": error_type if error_type in SENSITIVE_ERROR_TYPES else "DatabaseError",
    }


def _count_by(audit: AuditConnection, table: str, column: str) -> dict[str, int] | None:
    if column not in audit.columns(table):
        return None
    rows = audit.execute(
        f"SELECT COALESCE({column}, 'unknown') AS key, COUNT(*) AS count FROM {table} GROUP BY COALESCE({column}, 'unknown')"
    ).fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


def _scalar(audit: AuditConnection, sql: str, unavailable: int | None = None) -> int | None:
    try:
        row = audit.execute(sql).fetchone()
        if row is None:
            return 0
        return int(row[0] or 0)
    except Exception:
        return unavailable


def _duplicate_groups(audit: AuditConnection, table: str, columns: list[str], where: str | None = None) -> int | None:
    table_columns = audit.columns(table)
    if not table_columns or any(column not in table_columns for column in columns):
        return None
    where_clause = f"WHERE {where}" if where else ""
    grouped = ", ".join(columns)
    sql = f"SELECT COUNT(*) FROM (SELECT {grouped} FROM {table} {where_clause} GROUP BY {grouped} HAVING COUNT(*) > 1) AS duplicate_groups"
    return _scalar(audit, sql)


def _table_count(audit: AuditConnection, table: str) -> int | None:
    if not audit.table_exists(table):
        return None
    return _scalar(audit, f"SELECT COUNT(*) FROM {table}")


def _enabled_jobs_by_type(audit: AuditConnection, enabled: bool, held_only: bool = False) -> dict[str, int] | None:
    columns = audit.columns("scheduled_jobs")
    if not {"job_type", "enabled"}.issubset(columns):
        return None
    wanted = 1 if enabled else 0
    rows = audit.execute(
        f"SELECT job_type, COUNT(*) FROM scheduled_jobs WHERE enabled = {audit.placeholder()} GROUP BY job_type",
        (wanted,),
    ).fetchall()
    result = {str(row[0]): int(row[1]) for row in rows}
    if held_only:
        result = {job_type: count for job_type, count in result.items() if job_type in HELD_JOB_TYPES}
    return result


def _recent_job_runs_by_type_status(audit: AuditConnection) -> dict[str, int] | None:
    if not audit.table_exists("job_runs") or not audit.table_exists("scheduled_jobs"):
        return None
    job_run_columns = audit.columns("job_runs")
    job_columns = audit.columns("scheduled_jobs")
    if not {"scheduled_job_id", "status"}.issubset(job_run_columns) or not {"id", "job_type"}.issubset(job_columns):
        return None
    rows = audit.execute(
        """
        SELECT sj.job_type, jr.status, COUNT(*)
        FROM job_runs jr
        JOIN scheduled_jobs sj ON sj.id = jr.scheduled_job_id
        GROUP BY sj.job_type, jr.status
        """
    ).fetchall()
    return {f"{row[0]}:{row[1]}": int(row[2]) for row in rows}


def _orphan_count(audit: AuditConnection, child_table: str, parent_table: str = "executions") -> int | None:
    if not audit.table_exists(child_table) or not audit.table_exists(parent_table):
        return None
    child_columns = audit.columns(child_table)
    parent_columns = audit.columns(parent_table)
    if "execution_id" not in child_columns or "execution_id" not in parent_columns:
        return None
    return _scalar(
        audit,
        f"""
        SELECT COUNT(*)
        FROM {child_table} c
        LEFT JOIN {parent_table} e ON e.execution_id = c.execution_id
        WHERE e.execution_id IS NULL
        """,
    )


def _nonempty_content_count(audit: AuditConnection) -> int | None:
    if "content_text" not in audit.columns("execution_artifacts"):
        return None
    return _scalar(audit, "SELECT COUNT(*) FROM execution_artifacts WHERE content_text IS NOT NULL AND content_text <> ''")


def _scheduled_job_run_field_count(audit: AuditConnection, field: str) -> int | None:
    columns = audit.columns("executions")
    if not {"source_type", field}.issubset(columns):
        return None
    return _scalar(
        audit,
        f"SELECT COUNT(*) FROM executions WHERE source_type = 'scheduled_job_run' AND {field} IS NOT NULL AND {field} <> ''",
    )


def _payments_summary(audit: AuditConnection) -> dict[str, Any]:
    payment_columns = audit.columns("payments")
    intent_columns = audit.columns("payment_intents")
    pending_expired = None
    if {"status", "expires_at"}.issubset(intent_columns):
        now_expr = "CURRENT_TIMESTAMP" if audit.dialect == "postgres" else "datetime('now')"
        pending_expired = _scalar(audit, f"SELECT COUNT(*) FROM payment_intents WHERE status = 'pending' AND expires_at < {now_expr}")
    completed_missing_intent = None
    if {"status", "intent_reference"}.issubset(payment_columns):
        completed_missing_intent = _scalar(
            audit,
            "SELECT COUNT(*) FROM payments WHERE status = 'completed' AND (intent_reference IS NULL OR intent_reference = '')",
        )
    return {
        "payment_intents_count_by_status": _count_by(audit, "payment_intents", "status"),
        "payments_count_by_status": _count_by(audit, "payments", "status"),
        "duplicate_payment_tx_signature_groups": _duplicate_groups(
            audit,
            "payments",
            ["tx_signature"],
            "tx_signature IS NOT NULL AND tx_signature <> ''",
        ),
        "duplicate_payment_intent_tx_signature_groups": _duplicate_groups(
            audit,
            "payment_intents",
            ["tx_signature"],
            "tx_signature IS NOT NULL AND tx_signature <> ''",
        ),
        "completed_payments_missing_intent_link": completed_missing_intent,
        "pending_payment_intents_expired_count": pending_expired,
    }


def _access_summary(audit: AuditConnection) -> dict[str, Any]:
    columns = audit.columns("access_grants")
    active_count = None
    without_payment = None
    without_intent = None
    if "status" in columns:
        active_count = _scalar(audit, "SELECT COUNT(*) FROM access_grants WHERE status = 'active'")
    if {"status", "payment_id"}.issubset(columns):
        without_payment = _scalar(
            audit,
            "SELECT COUNT(*) FROM access_grants WHERE status = 'active' AND payment_id IS NULL",
        )
    if {"status", "intent_reference"}.issubset(columns):
        without_intent = _scalar(
            audit,
            "SELECT COUNT(*) FROM access_grants WHERE status = 'active' AND (intent_reference IS NULL OR intent_reference = '')",
        )
    duplicate_columns = ["user_id", "feature_name", "payment_id"]
    duplicate_where = "status = 'active' AND payment_id IS NOT NULL"
    if not all(column in columns for column in duplicate_columns):
        duplicate_columns = ["user_id", "feature_name", "intent_reference"]
        duplicate_where = "status = 'active' AND intent_reference IS NOT NULL"
    return {
        "access_grants_count_by_status": _count_by(audit, "access_grants", "status"),
        "active_access_grants_count": active_count,
        "active_grants_without_payment_link": without_payment,
        "active_grants_without_intent_reference": without_intent,
        "duplicate_active_grant_groups": _duplicate_groups(audit, "access_grants", duplicate_columns, duplicate_where),
    }


def _marketplace_summary(audit: AuditConnection) -> dict[str, Any]:
    payout_key = "creator_payout_requests"
    if not audit.table_exists(payout_key) and audit.table_exists("payout_requests"):
        payout_key = "payout_requests"
    ent_columns = audit.columns("marketplace_entitlements")
    entitlements_without_ref = None
    for maybe_ref in ("payment_reference", "intent_reference", "payment_id"):
        if maybe_ref in ent_columns:
            entitlements_without_ref = _scalar(
                audit,
                f"SELECT COUNT(*) FROM marketplace_entitlements WHERE {maybe_ref} IS NULL OR {maybe_ref} = ''",
            )
            break
    return {
        "marketplace_entitlements_count": _table_count(audit, "marketplace_entitlements"),
        "duplicate_listing_user_entitlements": _duplicate_groups(
            audit,
            "marketplace_entitlements",
            ["listing_id", "user_id"],
        ),
        "entitlements_without_payment_reference": entitlements_without_ref,
        "creator_earnings_events_count": _table_count(audit, "creator_earnings_events"),
        "payout_requests_count_by_status": _count_by(audit, payout_key, "status"),
    }


def _scheduler_summary(audit: AuditConnection) -> dict[str, Any]:
    return {
        "enabled_jobs_by_type": _enabled_jobs_by_type(audit, enabled=True),
        "disabled_held_jobs_by_type": _enabled_jobs_by_type(audit, enabled=False, held_only=True),
        "recent_job_runs_by_type_status": _recent_job_runs_by_type_status(audit),
        "scheduler_artifacts_count": _scalar(
            audit,
            "SELECT COUNT(*) FROM execution_artifacts WHERE execution_id IN (SELECT execution_id FROM executions WHERE source_type = 'scheduled_job_run')",
        )
        if audit.table_exists("execution_artifacts") and audit.table_exists("executions")
        else None,
        "scheduler_content_text_nonempty_count": _scalar(
            audit,
            "SELECT COUNT(*) FROM execution_artifacts WHERE content_text IS NOT NULL AND content_text <> '' AND execution_id IN (SELECT execution_id FROM executions WHERE source_type = 'scheduled_job_run')",
        )
        if audit.table_exists("execution_artifacts") and audit.table_exists("executions") and "content_text" in audit.columns("execution_artifacts")
        else None,
        "orphan_execution_events_count": _orphan_count(audit, "execution_events"),
        "orphan_execution_artifacts_count": _orphan_count(audit, "execution_artifacts"),
        "scheduled_job_run_count": _scalar(audit, "SELECT COUNT(*) FROM executions WHERE source_type = 'scheduled_job_run'")
        if "source_type" in audit.columns("executions")
        else None,
        "scheduled_job_run_user_id_not_null_count": _scheduled_job_run_field_count(audit, "user_id"),
        "scheduled_job_run_agent_id_not_null_count": _scheduled_job_run_field_count(audit, "agent_id"),
    }


def _execution_summary(audit: AuditConnection) -> dict[str, Any]:
    return {
        "executions_count_by_source_type": _count_by(audit, "executions", "source_type"),
        "executions_count_by_status": _count_by(audit, "executions", "status"),
        "execution_events_orphans": _orphan_count(audit, "execution_events"),
        "execution_artifacts_orphans": _orphan_count(audit, "execution_artifacts"),
        "execution_artifacts_content_text_nonempty": _nonempty_content_count(audit),
    }


def audit_connection(conn: Any, dialect: str) -> dict[str, Any]:
    audit = AuditConnection(conn, dialect)
    return {
        "schema_version": 1,
        "scheduler": _scheduler_summary(audit),
        "execution_ledger": _execution_summary(audit),
        "payments": _payments_summary(audit),
        "access": _access_summary(audit),
        "marketplace": _marketplace_summary(audit),
        "safety": {
            "raw_metadata_returned": False,
            "raw_payloads_returned": False,
            "db_url_printed": False,
            "secrets_printed": False,
            "read_only_mode": True,
        },
    }


def audit_sqlite_path(path: str | Path) -> dict[str, Any]:
    db_path = Path(path).resolve()
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return audit_connection(conn, "sqlite")
    finally:
        conn.close()


def audit_postgres_url(database_url: str) -> dict[str, Any]:
    try:
        import psycopg2  # type: ignore
    except Exception as exc:  # pragma: no cover - driver availability depends on runtime
        return _safe_unavailable(type(exc).__name__)
    try:
        conn = psycopg2.connect(database_url, connect_timeout=10)
        conn.set_session(readonly=True, autocommit=False)
        try:
            with conn.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '10s'")
            result = audit_connection(conn, "postgres")
            conn.rollback()
            return result
        finally:
            conn.close()
    except Exception as exc:  # pragma: no cover - production connectivity dependent
        return _safe_unavailable(type(exc).__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit sanitized aggregate-only launch-readiness DB audit JSON.")
    parser.add_argument("--sqlite-path", help="Local SQLite DB path for read-only audit.")
    parser.add_argument("--database-url-env", default="DATABASE_URL", help="Environment variable name containing DB URL.")
    args = parser.parse_args(argv)

    if args.sqlite_path:
        result = audit_sqlite_path(args.sqlite_path)
    else:
        database_url = os.getenv(args.database_url_env, "")
        if not database_url:
            result = _safe_unavailable("ValueError")
        else:
            result = audit_postgres_url(database_url)

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
