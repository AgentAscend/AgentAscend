import random

from fastapi import APIRouter, Header

from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, has_access
from backend.app.services.payment_config import payment_required_tool_message
from backend.app.services.auth_service import require_user_access

router = APIRouter()


def random_number_for_user(user_id: str):
    if not has_access(user_id, FEATURE_RANDOM_NUMBER):
        return {
            "status": "payment_required",
            "payment_required": True,
            "message": payment_required_tool_message(),
        }

    return {
        "status": "success",
        "user_id": user_id,
        "result": random.randint(0, 1000),
    }


@router.post("/tools/random-number")
def random_number(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    return random_number_for_user(user_id)
