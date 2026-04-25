from fastapi import APIRouter, Header

from backend.app.db.session import get_connection
from backend.app.services.auth_service import require_user_access

router = APIRouter()


@router.get("/users/{user_id}/access")
def get_user_access(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT feature_name, status, created_at
            FROM access_grants
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()

    return {
        "user_id": user_id,
        "access_grants": [dict(row) for row in rows],
    }


@router.get("/users/{user_id}/payments")
def get_user_payments(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, amount, token, status, created_at
            FROM payments
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()

    return {
        "user_id": user_id,
        "payments": [dict(row) for row in rows],
    }
