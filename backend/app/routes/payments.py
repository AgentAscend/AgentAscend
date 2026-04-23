from fastapi import APIRouter

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
def verify_payment(user_id: str):
    grant_access(user_id, FEATURE_RANDOM_NUMBER)
    return {
        "status": "payment_verified",
        "user_id": user_id,
    }



