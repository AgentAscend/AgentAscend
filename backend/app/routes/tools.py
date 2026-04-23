import random

from fastapi import APIRouter

from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, has_access

router = APIRouter()


@router.post("/tools/random-number")
def random_number(user_id: str):
    if not has_access(user_id, FEATURE_RANDOM_NUMBER):
        return {
            "status": "payment_required",
            "payment_required": True,
            "message": "Please pay 0.1 SOL to access this tool",
        }

    return {
        "status": "success",
        "user_id": user_id,
        "result": random.randint(0, 1000),
    }
