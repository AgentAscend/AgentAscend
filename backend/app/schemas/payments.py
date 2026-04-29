from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TokenType = Literal["SOL", "ASND"]


class PaymentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    token: TokenType = "SOL"


class PaymentVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    tx_signature: str = Field(min_length=1)
    token: TokenType = "SOL"
    reference: str = Field(min_length=1)
    idempotency_key: str | None = None


class PaymentCreateResponse(BaseModel):
    status: Literal["payment_required"]
    payment_required: Literal[True] = True
    user_id: str
    amount: float | str
    token: TokenType
    receiver: str
    receiver_wallet: str
    receiver_token_account: str | None = None
    reference: str
    ttl_seconds: int
    amount_lamports: int | None = None


class PaymentVerifyResponse(BaseModel):
    status: Literal["payment_verified"]
    user_id: str
    payment_id: int
    tx_signature: str
    token: TokenType
    received_lamports: int | None = None
    received_amount: str | None = None
    receiver_token_account: str | None = None
