from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TelegramCommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    telegram_user_id: int | str
    chat_id: int | str
    command: Literal["/random"] = "/random"


class TelegramCommandResponse(BaseModel):
    status: Literal["payment_required", "success", "error"]
    user_id: str
    command: str
    message: str
    payment: dict | None = None
    result: int | None = None
