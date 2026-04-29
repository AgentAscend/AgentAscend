from fastapi import APIRouter, HTTPException

from backend.app.providers.telegram_identity import telegram_user_to_user_id
from backend.app.routes.payments import create_payment
from backend.app.routes.tools import random_number_for_user
from backend.app.schemas.payments import PaymentCreateRequest
from backend.app.schemas.telegram import TelegramCommandRequest, TelegramCommandResponse

router = APIRouter()


@router.post("/telegram/command", response_model=TelegramCommandResponse)
def telegram_command(payload: TelegramCommandRequest):
    try:
        user_id = telegram_user_to_user_id(payload.telegram_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.command != "/random":
        raise HTTPException(status_code=400, detail="Unsupported command")

    tool_result = random_number_for_user(user_id)
    if tool_result.get("status") == "payment_required":
        payment_payload = create_payment(PaymentCreateRequest(user_id=user_id, token="SOL"))
        return {
            "status": "payment_required",
            "user_id": user_id,
            "command": payload.command,
            "message": "Payment required before running /random.",
            "payment": payment_payload,
            "result": None,
        }

    return {
        "status": "success",
        "user_id": user_id,
        "command": payload.command,
        "message": "Command executed",
        "payment": None,
        "result": tool_result.get("result"),
    }
