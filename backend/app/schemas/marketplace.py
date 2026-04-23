from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ListingStatus = Literal["draft", "queued_review", "published", "rejected"]
TransitionAction = Literal["submit_for_review", "approve", "reject"]


class ListingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creator_user_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1)
    pricing_model: Literal["free", "one_time", "subscription", "rental"] = "free"
    price_amount: float = 0
    price_token: Literal["SOL", "ASND"] = "ASND"
    status: ListingStatus = "draft"
    tags: list[str] = Field(default_factory=list)
    idempotency_key: str | None = None


class ListingTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: TransitionAction
    actor_user_id: str = Field(min_length=1)
    reason: str | None = None
    idempotency_key: str | None = None


class ListingRecord(BaseModel):
    listing_id: str
    creator_user_id: str
    title: str
    description: str
    category: str
    pricing_model: str
    price_amount: float
    price_token: str
    status: ListingStatus
    tags: list[str]
    created_at: str
    updated_at: str
    published_at: str | None = None


class ListingCreateResponse(BaseModel):
    status: Literal["ok"] = "ok"
    listing: ListingRecord
    idempotency_replayed: bool = False


class ListingTransitionResponse(BaseModel):
    status: Literal["ok"] = "ok"
    listing: ListingRecord
    previous_status: ListingStatus
    idempotency_replayed: bool = False


class CreatorListingsResponse(BaseModel):
    status: Literal["ok"] = "ok"
    creator_user_id: str
    listings: list[ListingRecord]


class LiveListingsResponse(BaseModel):
    status: Literal["ok"] = "ok"
    listings: list[ListingRecord]
