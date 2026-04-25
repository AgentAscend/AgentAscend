import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header

from backend.app.db.session import get_connection
from backend.app.schemas.marketplace import (
    CreatorListingsResponse,
    ListingCreateResponse,
    ListingInput,
    ListingRecord,
    ListingTransitionRequest,
    ListingTransitionResponse,
    LiveListingsResponse,
)
from backend.app.services.error_response import fail
from backend.app.services.auth_service import require_user_access
from backend.app.services.idempotency import check_or_begin, finalize

router = APIRouter()
logger = logging.getLogger(__name__)

_TRANSITIONS: dict[str, dict[str, str]] = {
    "draft": {"submit_for_review": "queued_review"},
    "queued_review": {"approve": "published", "reject": "rejected"},
    "published": {},
    "rejected": {},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _listing_from_row(row) -> ListingRecord:
    return ListingRecord(
        listing_id=row["listing_id"],
        creator_user_id=row["creator_user_id"],
        title=row["title"],
        description=row["description"],
        category=row["category"],
        pricing_model=row["pricing_model"],
        price_amount=float(row["price_amount"]),
        price_token=row["price_token"],
        status=row["status"],
        tags=json.loads(row["tags_json"] or "[]"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row["published_at"],
    )


def _validate_listing_payload(payload: ListingInput) -> None:
    if payload.pricing_model == "free" and payload.price_amount != 0:
        fail(400, "validation_error", "price_amount must be 0 for free listings")
    if payload.pricing_model != "free" and payload.price_amount <= 0:
        fail(400, "validation_error", "price_amount must be greater than 0 for paid listings")


@router.post("/marketplace/listings", response_model=ListingCreateResponse)
def create_listing(payload: ListingInput, authorization: str | None = Header(default=None)):
    require_user_access(payload.creator_user_id, authorization)
    _validate_listing_payload(payload)

    idempotency_key = payload.idempotency_key or f"listing_{uuid.uuid4().hex}"
    scope = f"listing_create:{payload.creator_user_id}"
    payload_for_idempotency = payload.model_dump(mode="json")

    replay = check_or_begin(scope, idempotency_key, payload_for_idempotency)
    if replay:
        return {
            "status": "ok",
            "listing": replay["payload"]["listing"],
            "idempotency_replayed": True,
        }

    listing_id = f"lst_{uuid.uuid4().hex[:12]}"
    now_iso = _now_iso()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO marketplace_listings (
                listing_id, creator_user_id, title, description, category,
                pricing_model, price_amount, price_token, status,
                tags_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                listing_id,
                payload.creator_user_id,
                payload.title,
                payload.description,
                payload.category,
                payload.pricing_model,
                payload.price_amount,
                payload.price_token,
                payload.status,
                json.dumps(payload.tags),
                now_iso,
                now_iso,
            ),
        )
        row = conn.execute(
            "SELECT * FROM marketplace_listings WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        conn.commit()

    listing = _listing_from_row(row)
    response_payload = {"status": "ok", "listing": listing.model_dump(mode="json")}
    finalize(scope, idempotency_key, response_payload)

    logger.info("listing_publish_queued listing_id=%s creator_user_id=%s", listing_id, payload.creator_user_id)

    return {**response_payload, "idempotency_replayed": False}


@router.post("/marketplace/listings/{listing_id}/transition", response_model=ListingTransitionResponse)
def transition_listing(listing_id: str, payload: ListingTransitionRequest):
    scope = f"listing_transition:{listing_id}"
    idempotency_key = payload.idempotency_key or f"listing_transition_{uuid.uuid4().hex}"
    payload_for_idempotency = payload.model_dump(mode="json")

    logger.info("listing_publish_attempted listing_id=%s action=%s", listing_id, payload.action)

    replay = check_or_begin(scope, idempotency_key, payload_for_idempotency)
    if replay:
        return {
            "status": "ok",
            "listing": replay["payload"]["listing"],
            "previous_status": replay["payload"]["previous_status"],
            "idempotency_replayed": True,
        }

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM marketplace_listings WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        if not row:
            fail(404, "validation_error", "Listing not found")

        current_status = row["status"]
        next_status = _TRANSITIONS.get(current_status, {}).get(payload.action)
        if not next_status:
            logger.info(
                "listing_publish_fail listing_id=%s action=%s current_status=%s",
                listing_id,
                payload.action,
                current_status,
            )
            fail(
                400,
                "transition_invalid",
                f"Action '{payload.action}' is not allowed from status '{current_status}'",
            )

        now_iso = _now_iso()
        published_at = now_iso if next_status == "published" else row["published_at"]

        conn.execute(
            """
            UPDATE marketplace_listings
            SET status = ?, updated_at = ?, published_at = ?
            WHERE listing_id = ?
            """,
            (next_status, now_iso, published_at, listing_id),
        )
        new_row = conn.execute(
            "SELECT * FROM marketplace_listings WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        conn.commit()

    listing = _listing_from_row(new_row)
    response_payload = {
        "status": "ok",
        "listing": listing.model_dump(mode="json"),
        "previous_status": current_status,
    }
    finalize(scope, idempotency_key, response_payload)

    if next_status == "published":
        logger.info("listing_publish_success listing_id=%s actor_user_id=%s", listing_id, payload.actor_user_id)
    elif next_status == "queued_review":
        logger.info("listing_publish_queued listing_id=%s actor_user_id=%s", listing_id, payload.actor_user_id)

    return {**response_payload, "idempotency_replayed": False}


@router.delete("/marketplace/listings/{listing_id}")
def delete_listing(listing_id: str, authorization: str | None = Header(default=None)):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT creator_user_id FROM marketplace_listings WHERE listing_id = ?",
            (listing_id,),
        ).fetchone()
        if not row:
            fail(404, "not_found", "Listing not found")

        require_user_access(row["creator_user_id"], authorization)
        conn.execute("DELETE FROM marketplace_listings WHERE listing_id = ?", (listing_id,))
        conn.commit()

    logger.info("listing_delete_success listing_id=%s creator_user_id=%s", listing_id, row["creator_user_id"])
    return {"status": "ok", "deleted": True, "listing_id": listing_id}


@router.get("/marketplace/listings", response_model=CreatorListingsResponse)
def creator_listings(creator_user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(creator_user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM marketplace_listings
            WHERE creator_user_id = ?
            ORDER BY updated_at DESC
            """,
            (creator_user_id,),
        ).fetchall()

    return {
        "status": "ok",
        "creator_user_id": creator_user_id,
        "listings": [_listing_from_row(row).model_dump(mode="json") for row in rows],
    }


@router.get("/marketplace/live", response_model=LiveListingsResponse)
def live_listings():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM marketplace_listings
            WHERE status = 'published'
            ORDER BY published_at DESC, updated_at DESC
            """
        ).fetchall()

    return {
        "status": "ok",
        "listings": [_listing_from_row(row).model_dump(mode="json") for row in rows],
    }
