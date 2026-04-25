#!/usr/bin/env python3
"""Verification script for marketplace + creator payout parity endpoints.

Covers:
- idempotency replay behavior
- invalid transition rejection
- malformed payload rejection
- admin gate enforcement
- response schema shape assertions
"""

import os
import sys
import types
import importlib.util
from decimal import Decimal


def _install_fastapi_stub():
    fastapi = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail):
            super().__init__(str(detail))
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def post(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def get(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

    class Request:  # pragma: no cover - compatibility shim
        pass

    def Header(default=None):  # noqa: N802
        return default

    fastapi.HTTPException = HTTPException
    fastapi.APIRouter = APIRouter
    fastapi.Header = Header
    fastapi.Request = Request
    sys.modules["fastapi"] = fastapi

    fastapi_responses = types.ModuleType("fastapi.responses")

    class JSONResponse:
        def __init__(self, status_code: int, content: dict):
            self.status_code = status_code
            self.content = content

    fastapi_responses.JSONResponse = JSONResponse
    sys.modules["fastapi.responses"] = fastapi_responses

    return HTTPException


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bearer(token: str) -> str:
    return f"Bearer {token}"


def main():
    HTTPException = _install_fastapi_stub()

    sys.path.insert(0, ".")
    from backend.app.db.session import get_connection, init_db
    from backend.app.services.auth_service import create_session_for_user

    init_db()
    marketplace = _load_module("backend/app/routes/marketplace.py", "marketplace_mod")
    creator = _load_module("backend/app/routes/creator.py", "creator_mod")

    checks = []

    # Clean local verification records for deterministic runs.
    with get_connection() as conn:
        conn.execute("DELETE FROM idempotency_records")
        conn.execute("DELETE FROM marketplace_listings")
        conn.execute("DELETE FROM creator_earnings_events")
        conn.execute("DELETE FROM creator_payout_requests")
        conn.execute("DELETE FROM auth_sessions")
        conn.execute("DELETE FROM users WHERE user_id IN ('creator_1', 'admin_1', 'non_admin')")
        conn.execute("INSERT INTO users (user_id, email, display_name, bio, avatar_url) VALUES (?, ?, ?, '', '')", ("creator_1", "creator_1@example.com", "Creator One"))
        conn.execute("INSERT INTO users (user_id, email, display_name, bio, avatar_url) VALUES (?, ?, ?, '', '')", ("admin_1", "admin_1@example.com", "Admin One"))
        conn.execute("INSERT INTO users (user_id, email, display_name, bio, avatar_url) VALUES (?, ?, ?, '', '')", ("non_admin", "non_admin@example.com", "Non Admin"))
        conn.commit()

    _creator_user, creator_token, _ = create_session_for_user("creator_1")
    _admin_user, admin_token, _ = create_session_for_user("admin_1")
    _non_admin_user, non_admin_token, _ = create_session_for_user("non_admin")

    # 1) Idempotency replay: listing create
    create_payload = marketplace.ListingInput(
        creator_user_id="creator_1",
        title="Agent One",
        description="Test listing",
        category="productivity",
        pricing_model="one_time",
        price_amount=10,
        price_token="ASND",
        status="draft",
        tags=["test"],
        idempotency_key="idem_listing_create_1",
    )
    first = marketplace.create_listing(create_payload, _bearer(creator_token))
    second = marketplace.create_listing(create_payload, _bearer(creator_token))
    checks.append(
        (
            "idempotency_listing_create",
            bool(first.get("listing", {}).get("listing_id"))
            and second.get("idempotency_replayed") is True
            and first["listing"]["listing_id"] == second["listing"]["listing_id"],
            f"first={first.get('idempotency_replayed')} second={second.get('idempotency_replayed')}",
        )
    )

    listing_id = first["listing"]["listing_id"]

    # 2) Invalid transition rejection
    try:
        marketplace.transition_listing(
            listing_id,
            marketplace.ListingTransitionRequest(
                action="approve",
                actor_user_id="admin_1",
                idempotency_key="idem_bad_transition",
            ),
        )
        checks.append(("invalid_listing_transition", False, "expected HTTP 400 transition_invalid"))
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, dict) else {"code": "", "message": str(e.detail)}
        checks.append(
            (
                "invalid_listing_transition",
                e.status_code == 400 and detail.get("code") == "transition_invalid",
                f"{e.status_code} {detail}",
            )
        )

    # 3) Malformed payload rejection (free listing with non-zero amount)
    try:
        marketplace.create_listing(
            marketplace.ListingInput(
                creator_user_id="creator_1",
                title="Bad Listing",
                description="Invalid",
                category="tools",
                pricing_model="free",
                price_amount=1,
                price_token="ASND",
                status="draft",
                tags=[],
            ),
            _bearer(creator_token),
        )
        checks.append(("malformed_listing_payload", False, "expected HTTP 400 validation_error"))
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, dict) else {"code": "", "message": str(e.detail)}
        checks.append(
            (
                "malformed_listing_payload",
                e.status_code == 400 and detail.get("code") == "validation_error",
                f"{e.status_code} {detail}",
            )
        )

    # Seed earnings so payout request has available balance.
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO creator_earnings_events (
                creator_user_id, listing_id, event_type, gross_amount,
                fee_amount, creator_amount, token, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            ("creator_1", listing_id, "purchase", 10, 2, 8, "ASND"),
        )
        conn.commit()

    payout_created = creator.request_payout(
        creator.PayoutRequestInput(
            creator_user_id="creator_1",
            requested_amount=Decimal("3"),
            token="ASND",
            destination_wallet="DestWallet111",
            note="first payout",
            idempotency_key="idem_payout_request_1",
        ),
        _bearer(creator_token),
    )

    # 4) Admin gate check for transition
    os.environ["ADMIN_USER_IDS"] = "admin_1"
    try:
        creator.transition_payout(
            payout_created["payout"]["request_id"],
            creator.PayoutTransitionInput(
                action="approve",
                actor_user_id="non_admin",
                idempotency_key="idem_payout_transition_non_admin",
            ),
            _bearer(non_admin_token),
        )
        checks.append(("admin_gate_transition", False, "expected HTTP 403 forbidden"))
    except HTTPException as e:
        detail = e.detail if isinstance(e.detail, dict) else {"code": "", "message": str(e.detail)}
        checks.append(
            (
                "admin_gate_transition",
                e.status_code == 403 and detail.get("code") == "forbidden",
                f"{e.status_code} {detail}",
            )
        )

    # 5) Schema assertions for earnings and payouts list
    summary = creator.earnings_summary("creator_1", "all", _bearer(creator_token))
    events = creator.earnings_events("creator_1", "all", _bearer(creator_token))
    payouts = creator.list_payouts("creator_1", _bearer(creator_token))

    checks.append(
        (
            "earnings_summary_schema",
            all(k in summary for k in ["gross_amount", "fee_amount", "creator_amount", "net_available_amount"]),
            str(summary),
        )
    )

    checks.append(
        (
            "earnings_events_schema",
            len(events.get("events", [])) >= 1
            and all(
                k in events["events"][0]
                for k in ["event_type", "fee_amount", "creator_amount", "token", "listing_id"]
            ),
            str(events.get("events", [])[:1]),
        )
    )

    checks.append(
        (
            "payouts_schema",
            len(payouts.get("payouts", [])) >= 1
            and all(
                k in payouts["payouts"][0]
                for k in ["request_id", "requested_amount", "status", "token", "destination_wallet"]
            ),
            str(payouts.get("payouts", [])[:1]),
        )
    )

    failed = [c for c in checks if not c[1]]

    print("Marketplace + creator payout verification results:")
    for name, ok, detail in checks:
        print(f"- {'PASS' if ok else 'FAIL'}: {name} -> {detail}")

    if failed:
        print(f"\nFAILED checks: {len(failed)}")
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
