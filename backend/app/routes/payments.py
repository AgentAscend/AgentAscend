from fastapi import APIRouter

from backend.app.db.session import get_connection
from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, grant_access

router = APIRouter()


@router.post("/payments/create")
def create_payment(user_id: str):
    return {
        "status": "payment_required",
        "user_id": user_id,
        "amount": 0.1,
        "token": "SOL",
    }


@router.post("/payments/verify")
def verify_payment(user_id: str, tx_signature: str):
    # TODO: replace with real blockchain verification

    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,),
        )

        cursor = conn.execute(
            """
            INSERT INTO payments (user_id, amount, token, status)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, 0.1, "SOL", "completed"),
        )

        payment_id = cursor.lastrowid
        conn.commit()

    grant_access(user_id, FEATURE_RANDOM_NUMBER, payment_id)

    return {
        "status": "payment_verified",
        "user_id": user_id,
        "payment_id": payment_id,
        "tx_signature": tx_signature,
    }
