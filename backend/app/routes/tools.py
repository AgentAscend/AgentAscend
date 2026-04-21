import random

from fastapi import APIRouter

from backend.app.services.access_store import FAKE_USER_ACCESS

router = APIRouter()


@router.post("/tools/random-number")
def random_number(user_id: str):
    if FAKE_USER_ACCESS.get(user_id) is not True:
        return {
            "status": "payment_required",
            "message": "Please pay 0.1 SOL to access this tool",
        }

    return {
        "status": "success",
        "user_id": user_id,
        "result": random.randint(0, 1000),
    }
