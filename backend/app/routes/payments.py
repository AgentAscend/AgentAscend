from fastapi import APIRouter

from backend.app.services.access_store import FAKE_USER_ACCESS

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
def verify_payment(user_id: str):
    FAKE_USER_ACCESS[user_id] = True
    return {
        "status": "payment_verified",
        "user_id": user_id,
    }



