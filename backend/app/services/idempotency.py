import hashlib
import json
from typing import Any

from fastapi import HTTPException

from backend.app.db.session import get_connection


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def check_or_begin(scope: str, idempotency_key: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    payload_digest = _payload_hash(payload)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT payload_hash, response_json, status_code
            FROM idempotency_records
            WHERE operation_scope = ? AND idempotency_key = ?
            """,
            (scope, idempotency_key),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO idempotency_records (operation_scope, idempotency_key, payload_hash)
                VALUES (?, ?, ?)
                """,
                (scope, idempotency_key, payload_digest),
            )
            conn.commit()
            return None

        if row["payload_hash"] != payload_digest:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "validation_error",
                    "message": "Idempotency key already used with different payload",
                },
            )

        if row["response_json"]:
            return {
                "status_code": row["status_code"] or 200,
                "payload": json.loads(row["response_json"]),
                "replayed": True,
            }

        raise HTTPException(
            status_code=409,
            detail={
                "code": "validation_error",
                "message": "Idempotent request is currently being processed",
            },
        )


def finalize(scope: str, idempotency_key: str, response_payload: dict[str, Any], status_code: int = 200) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE idempotency_records
            SET response_json = ?, status_code = ?
            WHERE operation_scope = ? AND idempotency_key = ?
            """,
            (json.dumps(response_payload, sort_keys=True), status_code, scope, idempotency_key),
        )
        conn.commit()
