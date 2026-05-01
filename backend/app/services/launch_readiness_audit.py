from __future__ import annotations

from typing import Any

from backend.app.db.session import get_connection
from scripts.prod_readonly_audit import AuditConnection, _safe_unavailable, audit_connection


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


def _empty_payment_evidence(tx_signature: str) -> dict[str, Any]:
    normalized_tx_signature = tx_signature.strip()
    return {
        "tx_signature_present": bool(normalized_tx_signature),
        "payment_found": False,
        "payment_id_present": False,
        "payment_status": None,
        "payment_intent_found": False,
        "payment_reference_present": False,
        "payment_reference": None,
        "payment_intent_status": None,
        "verification_status": None,
        "access_grant_present": False,
        "marketplace_entitlement_present": False,
        "listing_scoped": False,
        "duplicate_payment_tx_signature_group_count": 0,
        "duplicate_payment_intent_tx_signature_group_count": 0,
        "safety": {
            "raw_metadata_returned": False,
            "raw_payloads_returned": False,
            "db_url_printed": False,
            "secrets_printed": False,
            "read_only_mode": True,
        },
    }


def _fetch_one_by_column(audit: AuditConnection, table: str, column: str, value: Any, select_columns: list[str]) -> dict[str, Any] | None:
    columns = audit.columns(table)
    if column not in columns:
        return None
    available_columns = [selected for selected in select_columns if selected in columns]
    if not available_columns:
        return None
    selected_sql = ", ".join(available_columns)
    row = audit.execute(
        f"SELECT {selected_sql} FROM {table} WHERE {column} = {audit.placeholder()} LIMIT 1",
        (value,),
    ).fetchone()
    if row is None:
        return None
    return {selected: row[index] for index, selected in enumerate(available_columns)}


def _exists_by_conditions(audit: AuditConnection, table: str, conditions: list[tuple[str, Any]]) -> bool:
    columns = audit.columns(table)
    usable = [(column, value) for column, value in conditions if column in columns and value is not None and value != ""]
    if not usable:
        return False
    where_sql = " OR ".join(f"{column} = {audit.placeholder()}" for column, _value in usable)
    row = audit.execute(f"SELECT 1 FROM {table} WHERE {where_sql} LIMIT 1", [value for _column, value in usable]).fetchone()
    return row is not None


def _exists_by_all_conditions(audit: AuditConnection, table: str, conditions: list[tuple[str, Any]]) -> bool:
    columns = audit.columns(table)
    usable = [(column, value) for column, value in conditions if column in columns and value is not None and value != ""]
    if len(usable) != len(conditions):
        return False
    where_sql = " AND ".join(f"{column} = {audit.placeholder()}" for column, _value in usable)
    row = audit.execute(f"SELECT 1 FROM {table} WHERE {where_sql} LIMIT 1", [value for _column, value in usable]).fetchone()
    return row is not None


def _duplicate_tx_group_count(audit: AuditConnection, table: str, tx_signature: str) -> int:
    if "tx_signature" not in audit.columns(table):
        return 0
    row = audit.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT tx_signature
            FROM {table}
            WHERE tx_signature = {audit.placeholder()}
            GROUP BY tx_signature
            HAVING COUNT(*) > 1
        ) AS duplicate_groups
        """,
        (tx_signature,),
    ).fetchone()
    return int((row[0] if row else 0) or 0)


def _payment_evidence_for_connection(conn: Any, dialect: str, tx_signature: str) -> dict[str, Any]:
    audit = AuditConnection(conn, dialect)
    result = _empty_payment_evidence(tx_signature)
    tx_signature = tx_signature.strip()
    if not tx_signature:
        return result

    payment_columns = ["id", "status", "intent_reference", "verification_status", "user_id"]
    payment = _fetch_one_by_column(audit, "payments", "tx_signature", tx_signature, payment_columns)
    if payment is not None:
        result["payment_found"] = True
        payment_id = payment.get("id")
        payment_status = payment.get("status")
        payment_reference = payment.get("intent_reference")
        payment_verification_status = payment.get("verification_status")
        payment_user_id = payment.get("user_id")
        result["payment_id_present"] = payment_id is not None
        result["payment_status"] = payment_status
        if payment_reference:
            result["payment_reference_present"] = True
            result["payment_reference"] = payment_reference
        if payment_verification_status:
            result["verification_status"] = payment_verification_status
    else:
        payment_id = None
        payment_reference = None
        payment_user_id = None

    intent_columns = ["reference", "status", "verification_status", "product_id", "tool_id", "access_tier", "user_id"]
    intent = None
    if payment_reference:
        intent = _fetch_one_by_column(audit, "payment_intents", "reference", payment_reference, intent_columns)
    if intent is None:
        intent = _fetch_one_by_column(audit, "payment_intents", "tx_signature", tx_signature, intent_columns)

    if intent is not None:
        result["payment_intent_found"] = True
        intent_reference = intent.get("reference")
        intent_status = intent.get("status")
        intent_verification_status = intent.get("verification_status")
        product_id = intent.get("product_id")
        tool_id = intent.get("tool_id")
        access_tier = intent.get("access_tier")
        intent_user_id = intent.get("user_id")
        if intent_reference:
            result["payment_reference_present"] = True
            result["payment_reference"] = intent_reference
            payment_reference = intent_reference
        result["payment_intent_status"] = intent_status
        if intent_verification_status:
            result["verification_status"] = intent_verification_status
    else:
        product_id = None
        tool_id = None
        access_tier = None
        intent_user_id = None

    user_id = payment_user_id or intent_user_id
    result["access_grant_present"] = _exists_by_conditions(
        audit,
        "access_grants",
        [("payment_id", payment_id), ("intent_reference", payment_reference)],
    )
    result["marketplace_entitlement_present"] = _exists_by_all_conditions(
        audit,
        "marketplace_entitlements",
        [("listing_id", product_id), ("user_id", user_id)],
    )
    result["listing_scoped"] = bool(product_id and result["marketplace_entitlement_present"])
    if not result["listing_scoped"] and isinstance(product_id, str):
        result["listing_scoped"] = product_id.startswith("listing") or product_id.startswith("marketplace")
    if not result["listing_scoped"] and isinstance(tool_id, str):
        result["listing_scoped"] = tool_id.startswith("marketplace")
    if not result["listing_scoped"] and isinstance(access_tier, str):
        result["listing_scoped"] = access_tier.startswith("marketplace")

    result["duplicate_payment_tx_signature_group_count"] = _duplicate_tx_group_count(audit, "payments", tx_signature)
    result["duplicate_payment_intent_tx_signature_group_count"] = _duplicate_tx_group_count(
        audit,
        "payment_intents",
        tx_signature,
    )
    return result


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


def run_payment_evidence_lookup(tx_signature: str) -> dict[str, Any]:
    """Return sanitized read-only payment evidence for a public transaction signature."""

    conn = None
    try:
        conn = get_connection()
        dialect = _dialect_for_connection(conn)
        _set_read_only(conn, dialect)
        return _payment_evidence_for_connection(conn, dialect, tx_signature)
    except Exception as exc:
        unavailable = _safe_unavailable(type(exc).__name__)
        unavailable.setdefault("safety", {})["read_only_mode"] = True
        return unavailable
    finally:
        if conn is not None:
            _rollback_and_close(conn)
