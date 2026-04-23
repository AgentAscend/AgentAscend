from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


WindowType = Literal["7d", "30d", "all"]
PayoutStatus = Literal["pending", "approved", "rejected", "paid"]
PayoutAction = Literal["approve", "reject", "mark_paid"]


class EarningsSummaryResponse(BaseModel):
    status: Literal["ok"] = "ok"
    creator_user_id: str
    window: WindowType
    gross_amount: str
    fee_amount: str
    creator_amount: str
    paid_out_amount: str
    net_available_amount: str


class EarningsEventRecord(BaseModel):
    id: int
    creator_user_id: str
    listing_id: str
    event_type: Literal["purchase", "subscription", "rental", "fee", "refund"]
    gross_amount: str
    fee_amount: str
    creator_amount: str
    token: Literal["SOL", "ASND"]
    created_at: str


class EarningsEventsResponse(BaseModel):
    status: Literal["ok"] = "ok"
    creator_user_id: str
    window: WindowType
    events: list[EarningsEventRecord]


class PayoutRequestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creator_user_id: str = Field(min_length=1)
    requested_amount: Decimal = Field(gt=0)
    token: Literal["ASND", "SOL"] = "ASND"
    destination_wallet: str = Field(min_length=1)
    note: str | None = None
    idempotency_key: str | None = None


class PayoutRecord(BaseModel):
    request_id: str
    creator_user_id: str
    requested_amount: str
    token: str
    destination_wallet: str
    note: str | None = None
    status: PayoutStatus
    tx_signature: str | None = None
    rejection_reason: str | None = None
    created_at: str
    updated_at: str


class PayoutRequestResponse(BaseModel):
    status: Literal["ok"] = "ok"
    payout: PayoutRecord
    idempotency_replayed: bool = False


class PayoutListResponse(BaseModel):
    status: Literal["ok"] = "ok"
    creator_user_id: str
    payouts: list[PayoutRecord]


class PayoutTransitionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: PayoutAction
    actor_user_id: str = Field(min_length=1)
    reason: str | None = None
    tx_signature: str | None = None
    idempotency_key: str | None = None


class PayoutTransitionResponse(BaseModel):
    status: Literal["ok"] = "ok"
    payout: PayoutRecord
    previous_status: PayoutStatus
    idempotency_replayed: bool = False
