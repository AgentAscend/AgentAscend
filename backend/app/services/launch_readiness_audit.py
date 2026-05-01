from __future__ import annotations

from typing import Any

from backend.app.db.session import get_connection
from scripts.prod_readonly_audit import _safe_unavailable, audit_connection


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


def run_launch_readiness_audit() -> dict[str, Any]:
    """Return sanitized aggregate-only launch-readiness DB audit output.

    This function intentionally performs aggregate read-only checks only. It must
    not return raw DB rows, metadata/payload values, DB URLs, secrets, request or
    response bodies, transaction payloads, or wallet-private data.
    """

    conn = None
    try:
        conn = get_connection()
        dialect = _dialect_for_connection(conn)
        _set_read_only(conn, dialect)
        result = audit_connection(conn, dialect)
        result.setdefault("safety", {})["read_only_mode"] = True
        return result
    except Exception as exc:
        return _safe_unavailable(type(exc).__name__)
    finally:
        if conn is not None:
            _rollback_and_close(conn)
