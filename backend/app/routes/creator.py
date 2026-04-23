import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter

from backend.app.db.session import get_connection
from backend.app.schemas.creator import (
    EarningsEventsResponse,
    EarningsSummaryResponse,
    PayoutListResponse,
    PayoutRecord,
    PayoutRequestInput,
    PayoutRequestResponse,
    PayoutTransitionInput,
    PayoutTransitionResponse,
    WindowType,
)
from backend.app.services.error_response import fail
from backend.app.services.idempotency import check_or_begin, finalize

router = APIRouter()
logger = logging.getLogger(__name__)

_PAYOUT_TRANSITIONS: dict[str, dict[str, str]] = {
    "pending": {"approve": "approved", "reject": "rejected"},
    "approved": {"mark_paid": "paid"},
    "rejected": {},
    "paid": {},
}


def _window_start(window: WindowType) -> datetime | None:
    now = datetime.now(timezone.utc)
    if window == "7d":
        return now - timedelta(days=7)
    if window == "30d":
        return now - timedelta(days=30)
    return None


def _event_where_clause(window: WindowType) -> tuple[str, tuple]:
    start = _window_start(window)
    if not start:
        return "", tuple()
    return " AND created_at >= ?", (start.isoformat(),)


def _sum_earnings(creator_user_id: str, window: WindowType) -> tuple[Decimal, Decimal, Decimal]:
    extra_sql, extra_params = _event_where_clause(window)
    with get_connection() as conn:
        row = conn.execute(
            f"""
            SELECT
                COALESCE(SUM(gross_amount), 0) AS gross_amount,
                COALESCE(SUM(fee_amount), 0) AS fee_amount,
                COALESCE(SUM(creator_amount), 0) AS creator_amount
            FROM creator_earnings_events
            WHERE creator_user_id = ?{extra_sql}
            """,
            (creator_user_id, *extra_params),
        ).fetchone()

    return Decimal(str(row["gross_amount"])), Decimal(str(row["fee_amount"])), Decimal(str(row["creator_amount"]))


def _sum_paid_out(creator_user_id: str) -> Decimal:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(requested_amount), 0) AS paid_out
            FROM creator_payout_requests
            WHERE creator_user_id = ? AND status = 'paid'
            """,
            (creator_user_id,),
        ).fetchone()

    return Decimal(str(row["paid_out"]))


def _payout_from_row(row) -> PayoutRecord:
    return PayoutRecord(
        request_id=row["request_id"],
        creator_user_id=row["creator_user_id"],
        requested_amount=str(row["requested_amount"]),
        token=row["token"],
        destination_wallet=row["destination_wallet"],
        note=row["note"],
        status=row["status"],
        tx_signature=row["tx_signature"],
        rejection_reason=row["rejection_reason"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _require_admin(actor_user_id: str) -> None:
    admin_set = {x.strip() for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()}
    if actor_user_id not in admin_set:
        fail(403, "forbidden", "Admin role required for payout settlement actions")


@router.get("/creator/earnings/summary", response_model=EarningsSummaryResponse)
def earnings_summary(creator_user_id: str, window: WindowType = "30d"):
    gross_amount, fee_amount, creator_amount = _sum_earnings(creator_user_id, window)
    paid_out = _sum_paid_out(creator_user_id)
    net_available = creator_amount - paid_out

    return {
        "status": "ok",
        "creator_user_id": creator_user_id,
        "window": window,
        "gross_amount": str(gross_amount),
        "fee_amount": str(fee_amount),
        "creator_amount": str(creator_amount),
        "paid_out_amount": str(paid_out),
        "net_available_amount": str(net_available if net_available > 0 else Decimal("0")),
    }


@router.get("/creator/earnings/events", response_model=EarningsEventsResponse)
def earnings_events(creator_user_id: str, window: WindowType = "30d"):
    extra_sql, extra_params = _event_where_clause(window)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, creator_user_id, listing_id, event_type, gross_amount, fee_amount, creator_amount, token, created_at
            FROM creator_earnings_events
            WHERE creator_user_id = ?{extra_sql}
            ORDER BY id DESC
            """,
            (creator_user_id, *extra_params),
        ).fetchall()

    events = []
    for row in rows:
        # Guard malformed records at API boundary: missing canonical fields are skipped.
        if row["creator_amount"] is None or row["fee_amount"] is None or row["event_type"] is None:
            logger.warning("earnings_malformed_skipped creator_user_id=%s event_id=%s", creator_user_id, row["id"])
            continue

        events.append(
            {
                "id": row["id"],
                "creator_user_id": row["creator_user_id"],
                "listing_id": row["listing_id"],
                "event_type": row["event_type"],
                "gross_amount": str(row["gross_amount"]),
                "fee_amount": str(row["fee_amount"]),
                "creator_amount": str(row["creator_amount"]),
                "token": row["token"],
                "created_at": row["created_at"],
            }
        )

    return {
        "status": "ok",
        "creator_user_id": creator_user_id,
        "window": window,
        "events": events,
    }


@router.post("/creator/payouts/request", response_model=PayoutRequestResponse)
def request_payout(payload: PayoutRequestInput):
    idempotency_key = payload.idempotency_key or f"payout_{uuid.uuid4().hex}"
    scope = f"payout_request:{payload.creator_user_id}"
    payload_for_idempotency = payload.model_dump(mode="json")

    replay = check_or_begin(scope, idempotency_key, payload_for_idempotency)
    if replay:
        return {
            "status": "ok",
            "payout": replay["payload"]["payout"],
            "idempotency_replayed": True,
        }

    _, _, creator_amount = _sum_earnings(payload.creator_user_id, "all")
    pending_or_approved = Decimal("0")
    paid_out = Decimal("0")

    with get_connection() as conn:
        agg = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN status IN ('pending', 'approved') THEN requested_amount ELSE 0 END), 0) AS reserved_amount,
                COALESCE(SUM(CASE WHEN status = 'paid' THEN requested_amount ELSE 0 END), 0) AS paid_amount
            FROM creator_payout_requests
            WHERE creator_user_id = ?
            """,
            (payload.creator_user_id,),
        ).fetchone()

        pending_or_approved = Decimal(str(agg["reserved_amount"]))
        paid_out = Decimal(str(agg["paid_amount"]))

        available = creator_amount - pending_or_approved - paid_out
        if payload.requested_amount > available:
            fail(400, "validation_error", "Requested amount exceeds available creator balance")

        request_id = f"payout_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO creator_payout_requests (
                request_id, creator_user_id, requested_amount, token, destination_wallet,
                note, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                request_id,
                payload.creator_user_id,
                str(payload.requested_amount),
                payload.token,
                payload.destination_wallet,
                payload.note,
                now_iso,
                now_iso,
            ),
        )

        row = conn.execute(
            "SELECT * FROM creator_payout_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        conn.commit()

    payout = _payout_from_row(row)
    response_payload = {"status": "ok", "payout": payout.model_dump(mode="json")}
    finalize(scope, idempotency_key, response_payload)

    logger.info("payout_requested request_id=%s creator_user_id=%s", payout.request_id, payout.creator_user_id)

    return {**response_payload, "idempotency_replayed": False}


@router.get("/creator/payouts", response_model=PayoutListResponse)
def list_payouts(creator_user_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM creator_payout_requests
            WHERE creator_user_id = ?
            ORDER BY created_at DESC
            """,
            (creator_user_id,),
        ).fetchall()

    return {
        "status": "ok",
        "creator_user_id": creator_user_id,
        "payouts": [_payout_from_row(row).model_dump(mode="json") for row in rows],
    }


@router.post("/creator/payouts/{request_id}/transition", response_model=PayoutTransitionResponse)
def transition_payout(request_id: str, payload: PayoutTransitionInput):
    _require_admin(payload.actor_user_id)

    scope = f"payout_transition:{request_id}"
    idempotency_key = payload.idempotency_key or f"settle_{uuid.uuid4().hex}"
    payload_for_idempotency = payload.model_dump(mode="json")

    replay = check_or_begin(scope, idempotency_key, payload_for_idempotency)
    if replay:
        return {
            "status": "ok",
            "payout": replay["payload"]["payout"],
            "previous_status": replay["payload"]["previous_status"],
            "idempotency_replayed": True,
        }

    logger.info("payout_transition_attempted request_id=%s action=%s", request_id, payload.action)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM creator_payout_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        if not row:
            fail(404, "validation_error", "Payout request not found")

        current_status = row["status"]
        next_status = _PAYOUT_TRANSITIONS.get(current_status, {}).get(payload.action)
        if not next_status:
            logger.info("payout_transition_fail request_id=%s action=%s", request_id, payload.action)
            fail(
                400,
                "transition_invalid",
                f"Action '{payload.action}' is not allowed from status '{current_status}'",
            )

        if payload.action == "mark_paid" and not payload.tx_signature:
            fail(400, "validation_error", "tx_signature is required for mark_paid action")

        now_iso = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            UPDATE creator_payout_requests
            SET status = ?,
                rejection_reason = ?,
                tx_signature = ?,
                updated_at = ?,
                approved_at = CASE WHEN ? = 'approved' THEN ? ELSE approved_at END,
                rejected_at = CASE WHEN ? = 'rejected' THEN ? ELSE rejected_at END,
                paid_at = CASE WHEN ? = 'paid' THEN ? ELSE paid_at END
            WHERE request_id = ?
            """,
            (
                next_status,
                payload.reason if next_status == "rejected" else row["rejection_reason"],
                payload.tx_signature if next_status == "paid" else row["tx_signature"],
                now_iso,
                next_status,
                now_iso,
                next_status,
                now_iso,
                next_status,
                now_iso,
                request_id,
            ),
        )

        updated_row = conn.execute(
            "SELECT * FROM creator_payout_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        conn.commit()

    payout = _payout_from_row(updated_row)
    response_payload = {
        "status": "ok",
        "payout": payout.model_dump(mode="json"),
        "previous_status": current_status,
    }
    finalize(scope, idempotency_key, response_payload)

    logger.info("payout_transition_success request_id=%s action=%s", request_id, payload.action)

    return {**response_payload, "idempotency_replayed": False}
