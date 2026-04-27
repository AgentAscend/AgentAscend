from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from backend.app.db.session import get_connection, utc_now_iso

_TRUTHY_VALUES = {"1", "true", "yes", "on"}
_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "token",
    "credential",
    "database_url",
    "postgres_url",
    "private_key",
)


def is_execution_ledger_enabled() -> bool:
    return os.getenv("EXECUTION_LEDGER_ENABLED", "").strip().lower() in _TRUTHY_VALUES


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _assert_no_sensitive_keys(value: Any, path: str = "payload") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            key_text = str(key).lower()
            if any(part in key_text for part in _SENSITIVE_KEY_PARTS):
                raise ValueError(f"Execution ledger {path} contains sensitive key: {key}")
            _assert_no_sensitive_keys(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _assert_no_sensitive_keys(nested, f"{path}[{index}]")


def _normalize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _normalize_json_value(nested) for key, nested in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_json_value(nested) for nested in value]
    return value


def _json_dumps(value: dict[str, Any] | None) -> str:
    payload = value or {}
    _assert_no_sensitive_keys(payload)
    normalized_payload = _normalize_json_value(payload)
    return json.dumps(normalized_payload, sort_keys=True, separators=(",", ":"))


def _json_loads(value: str | None) -> dict[str, Any]:
    try:
        loaded = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _row_to_record(row: Any, json_fields: tuple[str, ...] = ("metadata_json",)) -> dict[str, Any]:
    data = dict(row)
    if "metadata_json" in json_fields and "metadata_json" in data:
        data["metadata"] = _json_loads(data.get("metadata_json"))
    if "payload_json" in json_fields and "payload_json" in data:
        data["payload"] = _json_loads(data.get("payload_json"))
    return data


def create_execution(
    user_id: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    status: str = "pending",
    metadata: dict[str, Any] | None = None,
    execution_id: str | None = None,
    agent_id: str | None = None,
    db: Any | None = None,
) -> dict[str, Any]:
    execution_id = execution_id or _new_id("exec")
    now = utc_now_iso()

    def insert(conn: Any) -> dict[str, Any] | None:
        conn.execute(
            """
            INSERT INTO executions(execution_id, source_type, source_id, user_id, agent_id, status, started_at, metadata_json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (execution_id, source_type, source_id, user_id, agent_id, status, now, _json_dumps(metadata)),
        )
        row = conn.execute("SELECT * FROM executions WHERE execution_id = ?", (execution_id,)).fetchone()
        return _row_to_record(row) if row is not None else None

    if db is not None:
        record = insert(db)
    else:
        with get_connection() as conn:
            insert(conn)
            conn.commit()
        record = get_execution(execution_id)
    if record is None:
        raise RuntimeError(f"Execution was not created: {execution_id}")
    return record


def get_execution(execution_id: str, db: Any | None = None) -> dict[str, Any] | None:
    if db is not None:
        row = db.execute("SELECT * FROM executions WHERE execution_id = ?", (execution_id,)).fetchone()
    else:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM executions WHERE execution_id = ?", (execution_id,)).fetchone()
    return _row_to_record(row) if row is not None else None


def get_execution_by_source(source_type: str, source_id: str, db: Any | None = None) -> dict[str, Any] | None:
    if db is not None:
        row = db.execute(
            "SELECT * FROM executions WHERE source_type = ? AND source_id = ? ORDER BY id DESC LIMIT 1",
            (source_type, source_id),
        ).fetchone()
    else:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM executions WHERE source_type = ? AND source_id = ? ORDER BY id DESC LIMIT 1",
                (source_type, source_id),
            ).fetchone()
    return _row_to_record(row) if row is not None else None


def _execution_filter_clause(
    user_id: str,
    status: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    agent_id: str | None = None,
) -> tuple[str, list[Any]]:
    clauses = ["e.user_id = ?"]
    params: list[Any] = [user_id]
    if status:
        clauses.append("e.status = ?")
        params.append(status)
    if source_type:
        clauses.append("e.source_type = ?")
        params.append(source_type)
    if source_id:
        clauses.append("e.source_id = ?")
        params.append(source_id)
    if agent_id:
        clauses.append("e.agent_id = ?")
        params.append(agent_id)
    return " AND ".join(clauses), params


def list_executions_for_user(
    user_id: str,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    agent_id: str | None = None,
) -> list[dict[str, Any]]:
    where_clause, params = _execution_filter_clause(user_id, status, source_type, source_id, agent_id)
    query = """
            SELECT e.*,
                   (SELECT COUNT(*) FROM execution_events ev WHERE ev.execution_id = e.execution_id) AS event_count,
                   (SELECT COUNT(*) FROM execution_artifacts art WHERE art.execution_id = e.execution_id) AS artifact_count
            FROM executions e
            WHERE {where_clause}
            ORDER BY e.started_at DESC, e.id DESC
            LIMIT ? OFFSET ?
            """.format(where_clause=where_clause)
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params + [limit, offset])).fetchall()
    return [_row_to_record(row) for row in rows]


def count_executions_for_user(
    user_id: str,
    status: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    agent_id: str | None = None,
) -> int:
    where_clause, params = _execution_filter_clause(user_id, status, source_type, source_id, agent_id)
    query = "SELECT COUNT(*) AS count FROM executions e WHERE {where_clause}".format(where_clause=where_clause)
    with get_connection() as conn:
        row = conn.execute(query, tuple(params)).fetchone()
    return int(row["count"] if row is not None else 0)


def _execution_status_from_task_status(task_status: str | None) -> str:
    normalized = (task_status or "").strip().lower()
    if normalized in {"queued", "running", "completed", "failed"}:
        return normalized
    return normalized or "unknown"


def backfill_task_executions(limit: int = 100) -> dict[str, Any]:
    """Create missing task execution ledger rows without running any tasks.

    This helper is intentionally internal/idempotent. It does not run automatically
    and should not be pointed at production unless a separate canary/runbook has
    been approved.
    """
    backfilled: list[str] = []
    skipped_existing = 0
    with get_connection() as conn:
        task_rows = conn.execute(
            """
            SELECT task_id, user_id, agent_id, type, title, status, created_at
            FROM tasks
            ORDER BY created_at ASC, id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        for task in task_rows:
            existing = conn.execute(
                "SELECT execution_id FROM executions WHERE source_type='task' AND source_id=? LIMIT 1",
                (task["task_id"],),
            ).fetchone()
            if existing:
                skipped_existing += 1
                continue
            status = _execution_status_from_task_status(task["status"])
            metadata = {
                "backfilled": True,
                "original_task_status": task["status"],
                "task_id": task["task_id"],
                "task_type": task["type"],
            }
            execution = create_execution(
                user_id=task["user_id"],
                source_type="task",
                source_id=task["task_id"],
                status=status,
                agent_id=task["agent_id"],
                metadata=metadata,
                db=conn,
            )
            append_execution_event(
                execution["execution_id"],
                "task_created",
                payload={
                    "backfilled": True,
                    "original_task_status": task["status"],
                    "status": status,
                    "task_id": task["task_id"],
                },
                message="Backfilled task execution ledger row",
                db=conn,
            )
            backfilled.append(task["task_id"])
        conn.commit()
    return {
        "status": "ok",
        "backfilled": len(backfilled),
        "skipped_existing": skipped_existing,
        "task_ids": backfilled,
    }


def create_execution_step(
    execution_id: str,
    step_order: int,
    step_type: str,
    name: str,
    status: str = "pending",
    metadata: dict[str, Any] | None = None,
    step_id: str | None = None,
) -> dict[str, Any]:
    step_id = step_id or _new_id("step")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO execution_steps(step_id, execution_id, step_order, step_type, name, status, metadata_json)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (step_id, execution_id, step_order, step_type, name, status, _json_dumps(metadata)),
        )
        conn.commit()
    return _get_required_by_id("execution_steps", "step_id", step_id)


def list_execution_steps(execution_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_steps WHERE execution_id = ? ORDER BY step_order ASC, id ASC",
            (execution_id,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def append_execution_event(
    execution_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    level: str = "info",
    message: str | None = None,
    step_id: str | None = None,
    event_id: str | None = None,
    db: Any | None = None,
) -> dict[str, Any]:
    event_id = event_id or _new_id("evt")

    def insert(conn: Any) -> dict[str, Any] | None:
        conn.execute(
            """
            INSERT INTO execution_events(event_id, execution_id, step_id, event_type, level, message, payload_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, execution_id, step_id, event_type, level, message, _json_dumps(payload), utc_now_iso()),
        )
        row = conn.execute("SELECT * FROM execution_events WHERE event_id = ?", (event_id,)).fetchone()
        return _row_to_record(row, json_fields=("payload_json",)) if row is not None else None

    if db is not None:
        record = insert(db)
    else:
        with get_connection() as conn:
            insert(conn)
            conn.commit()
        record = _get_required_by_id("execution_events", "event_id", event_id, json_fields=("payload_json",))
    if record is None:
        raise RuntimeError(f"Execution event was not created: {event_id}")
    return record


def list_execution_events(execution_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_events WHERE execution_id = ? ORDER BY created_at ASC, id ASC",
            (execution_id,),
        ).fetchall()
    return [_row_to_record(row, json_fields=("payload_json",)) for row in rows]


def attach_execution_artifact(
    execution_id: str,
    artifact_type: str,
    name: str,
    step_id: str | None = None,
    uri: str | None = None,
    content_text: str | None = None,
    metadata: dict[str, Any] | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    payload: dict[str, Any] | None = None,
    artifact_id: str | None = None,
    db: Any | None = None,
) -> dict[str, Any]:
    artifact_id = artifact_id or _new_id("art")
    artifact_metadata = dict(metadata or {})
    if source_type is not None:
        artifact_metadata["source_type"] = source_type
    if source_id is not None:
        artifact_metadata["source_id"] = source_id
    if payload is not None:
        artifact_metadata["payload"] = payload

    def insert(conn: Any) -> dict[str, Any] | None:
        conn.execute(
            """
            INSERT INTO execution_artifacts(artifact_id, execution_id, step_id, artifact_type, name, uri, content_text, metadata_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, execution_id, step_id, artifact_type, name, uri, content_text, _json_dumps(artifact_metadata), utc_now_iso()),
        )
        row = conn.execute("SELECT * FROM execution_artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        return _row_to_record(row) if row is not None else None

    if db is not None:
        record = insert(db)
    else:
        with get_connection() as conn:
            insert(conn)
            conn.commit()
        record = _get_required_by_id("execution_artifacts", "artifact_id", artifact_id)
    if record is None:
        raise RuntimeError(f"Execution artifact was not created: {artifact_id}")
    return record


def list_execution_artifacts(execution_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_artifacts WHERE execution_id = ? ORDER BY created_at ASC, id ASC",
            (execution_id,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def record_execution_cost(
    execution_id: str,
    step_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_amount: float = 0,
    cost_currency: str = "USD",
    metadata: dict[str, Any] | None = None,
    cost_type: str | None = None,
    cost_id: str | None = None,
) -> dict[str, Any]:
    cost_id = cost_id or _new_id("cost")
    cost_metadata = dict(metadata or {})
    if cost_type is not None:
        cost_metadata["cost_type"] = cost_type
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO execution_costs(cost_id, execution_id, step_id, provider, model, input_tokens, output_tokens,
                                        cost_amount, cost_currency, metadata_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cost_id,
                execution_id,
                step_id,
                provider,
                model,
                input_tokens,
                output_tokens,
                cost_amount,
                cost_currency,
                _json_dumps(cost_metadata),
                utc_now_iso(),
            ),
        )
        conn.commit()
    return _get_required_by_id("execution_costs", "cost_id", cost_id)


def list_execution_costs(execution_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_costs WHERE execution_id = ? ORDER BY created_at ASC, id ASC",
            (execution_id,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def request_execution_approval(
    execution_id: str,
    approval_type: str,
    status: str = "pending",
    step_id: str | None = None,
    requested_by: str | None = None,
    approved_by: str | None = None,
    reason: str | None = None,
    metadata: dict[str, Any] | None = None,
    approval_id: str | None = None,
) -> dict[str, Any]:
    approval_id = approval_id or _new_id("appr")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO execution_approvals(approval_id, execution_id, step_id, approval_type, status, requested_by,
                                            approved_by, requested_at, reason, metadata_json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval_id,
                execution_id,
                step_id,
                approval_type,
                status,
                requested_by,
                approved_by,
                utc_now_iso(),
                reason,
                _json_dumps(metadata),
            ),
        )
        conn.commit()
    return _get_required_by_id("execution_approvals", "approval_id", approval_id)


def list_execution_approvals(execution_id: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM execution_approvals WHERE execution_id = ? ORDER BY requested_at ASC, id ASC",
            (execution_id,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def mark_execution_running(execution_id: str, db: Any | None = None) -> dict[str, Any]:
    return _update_execution_status(execution_id, "running", finished_at=None, db=db)


def mark_execution_completed(execution_id: str, db: Any | None = None) -> dict[str, Any]:
    return _update_execution_status(execution_id, "completed", finished_at=utc_now_iso(), db=db)


def mark_execution_failed(execution_id: str, db: Any | None = None) -> dict[str, Any]:
    return _update_execution_status(execution_id, "failed", finished_at=utc_now_iso(), db=db)


def mark_execution_step_running(step_id: str) -> dict[str, Any]:
    now = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            "UPDATE execution_steps SET status = ?, started_at = COALESCE(started_at, ?) WHERE step_id = ?",
            ("running", now, step_id),
        )
        conn.commit()
    return _get_required_by_id("execution_steps", "step_id", step_id)


def mark_execution_step_completed(step_id: str) -> dict[str, Any]:
    return _update_step_status(step_id, "completed")


def mark_execution_step_failed(step_id: str) -> dict[str, Any]:
    return _update_step_status(step_id, "failed")


def _update_execution_status(execution_id: str, status: str, finished_at: str | None, db: Any | None = None) -> dict[str, Any]:
    def update(conn: Any) -> None:
        if finished_at is None:
            conn.execute("UPDATE executions SET status = ?, finished_at = NULL WHERE execution_id = ?", (status, execution_id))
        else:
            conn.execute("UPDATE executions SET status = ?, finished_at = ? WHERE execution_id = ?", (status, finished_at, execution_id))

    if db is not None:
        update(db)
        record = get_execution(execution_id, db=db)
    else:
        with get_connection() as conn:
            update(conn)
            conn.commit()
        record = get_execution(execution_id)
    if record is None:
        raise ValueError(f"Execution not found: {execution_id}")
    return record


def _update_step_status(step_id: str, status: str) -> dict[str, Any]:
    now = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            "UPDATE execution_steps SET status = ?, finished_at = ? WHERE step_id = ?",
            (status, now, step_id),
        )
        conn.commit()
    return _get_required_by_id("execution_steps", "step_id", step_id)


def _get_required_by_id(
    table: str,
    id_column: str,
    id_value: str,
    json_fields: tuple[str, ...] = ("metadata_json",),
) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE {id_column} = ?", (id_value,)).fetchone()
    if row is None:
        raise ValueError(f"{table} row not found: {id_value}")
    return _row_to_record(row, json_fields=json_fields)
