import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AGENT_MINT = "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump"
WSOL_MINT = "So11111111111111111111111111111111111111112"
TX_B64_RESPONSE_KEY = "tx" + "Base64"


def _sig(ch: str) -> str:
    return ch * 88


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-payment-grant-linkage-test.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENT_RUNTIME_ADMIN_TOKEN", "test-admin-token")
    monkeypatch.setenv("SOLANA_RECEIVER_WALLET", "ReceiverWallet111111111111111111111111111111")
    monkeypatch.setenv("AGENT_TOKEN_MINT_ADDRESS", AGENT_MINT)
    monkeypatch.setenv("CURRENCY_MINT", WSOL_MINT)
    monkeypatch.setenv("PRICE_AMOUNT_SMALLEST_UNIT", "100000000")

    import backend.app.main as main

    importlib.reload(main)
    with TestClient(main.app) as test_client:
        yield test_client


def _safe_response_diag(response):
    try:
        body = response.json()
    except Exception:
        body = {}
    error = body.get("error") if isinstance(body, dict) else None
    error_code = error.get("code") if isinstance(error, dict) else None
    keys = sorted(body.keys()) if isinstance(body, dict) else []
    return f"status_code={response.status_code} error_code={error_code!r} keys={keys}"


def _assert_status(response, expected_status: int) -> dict[str, Any]:
    assert response.status_code == expected_status, _safe_response_diag(response)
    body = response.json()
    assert isinstance(body, dict)
    return body


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "local-test-password-only", "display_name": email.split("@", 1)[0]},
    )
    body = _assert_status(response, 200)
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _configure_fake_legacy_sol_payment(monkeypatch, lamports: int = 200_000_000):
    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    monkeypatch.setattr(
        "backend.app.routes.payments.received_lamports_for_wallet",
        lambda _tx, _wallet: lamports,
    )


def _create_legacy_payment(client: TestClient, user_id: str) -> dict[str, Any]:
    response = client.post("/payments/create", json={"user_id": user_id, "token": "SOL"})
    return _assert_status(response, 200)


def _create_listing(client: TestClient, *, creator_user_id: str, creator_token: str, price_amount: float = 0.05):
    response = client.post(
        "/marketplace/listings",
        json={
            "creator_user_id": creator_user_id,
            "title": "Payment linkage listing",
            "description": "A local-only payment linkage test listing",
            "category": "Development",
            "pricing_model": "one_time",
            "price_amount": price_amount,
            "price_token": "SOL",
            "status": "queued_review",
            "tags": ["test"],
        },
        headers=_auth_header(creator_token),
    )
    return _assert_status(response, 200)["listing"]


def test_legacy_verify_links_payment_intent_grant_and_admin_evidence(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "legacy-linkage@example.com")
    _configure_fake_legacy_sol_payment(monkeypatch)
    created = _create_legacy_payment(client, user_id)
    reference = created["reference"]
    tx_signature = _sig("L")

    verify_response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": tx_signature,
            "token": "SOL",
            "reference": reference,
            "idempotency_key": "legacy-linkage-ok",
        },
        headers=_auth_header(token),
    )
    verify_body = _assert_status(verify_response, 200)
    payment_id = verify_body["payment_id"]

    from backend.app.db.session import get_connection
    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER

    with get_connection() as conn:
        payment = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        intent = conn.execute("SELECT * FROM payment_intents WHERE reference = ?", (reference,)).fetchone()
        grant = conn.execute(
            """
            SELECT * FROM access_grants
            WHERE user_id = ? AND feature_name = ? AND status = 'active'
            """,
            (user_id, FEATURE_RANDOM_NUMBER),
        ).fetchone()

    assert payment is not None
    assert payment["status"] == "completed"
    assert payment["tx_signature"] == tx_signature
    assert payment["intent_reference"] == reference

    assert intent is not None
    assert intent["reference"] == reference
    assert intent["status"] == "completed"
    assert intent["verification_status"] == "verified"
    assert intent["tx_signature"] == tx_signature

    assert grant is not None
    assert grant["payment_id"] == payment_id
    assert grant["intent_reference"] == reference
    assert grant["source"] == "legacy_verify"

    evidence_response = client.get(
        f"/admin/audits/payment-evidence/{tx_signature}",
        headers={"X-Agent-Runtime-Token": "test-admin-token"},
    )
    evidence = _assert_status(evidence_response, 200)
    assert evidence["payment_found"] is True
    assert evidence["payment_id_present"] is True
    assert evidence["payment_intent_found"] is True
    assert evidence["payment_reference_present"] is True
    assert evidence["payment_reference"] == reference
    assert evidence["payment_intent_status"] == "completed"
    assert evidence["verification_status"] == "verified"
    assert evidence["access_grant_present"] is True
    assert evidence["duplicate_payment_tx_signature_group_count"] == 0
    assert evidence["duplicate_payment_intent_tx_signature_group_count"] == 0

    aggregate_response = client.get(
        "/admin/audits/launch-readiness/aggregate",
        headers={"X-Agent-Runtime-Token": "test-admin-token"},
    )
    aggregate = _assert_status(aggregate_response, 200)
    assert aggregate["payments"]["completed_payments_missing_intent_link"] == 0
    assert aggregate["access"]["active_grants_without_payment_link"] == 0
    assert aggregate["access"]["active_grants_without_intent_reference"] == 0


def test_pumpfun_listing_verify_links_payment_grant_entitlement_and_admin_evidence(client: TestClient, monkeypatch):
    creator_id, creator_token = _signup(client, "pumpfun-linkage-creator@example.com")
    buyer_id, buyer_token = _signup(client, "pumpfun-linkage-buyer@example.com")
    listing = _create_listing(client, creator_user_id=creator_id, creator_token=creator_token)

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, TX_B64_RESPONSE_KEY: "unsigned-local-test-payload", "invoiceId": "invoice-linkage"},
    )
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.validate_invoice_payment",
        lambda _payload: {"ok": True, "verified": True, "invoiceId": "invoice-linkage"},
    )

    create_response = client.post(
        "/payments/pumpfun/create",
        json={
            "user_id": buyer_id,
            "user_wallet": "WalletLinkage111111111111111111111111111111",
            "listing_id": listing["listing_id"],
        },
        headers=_auth_header(buyer_token),
    )
    create_body = _assert_status(create_response, 200)
    reference = create_body["reference"]
    tx_signature = _sig("P")

    verify_response = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": buyer_id, "reference": reference, "tx_signature": tx_signature},
        headers=_auth_header(buyer_token),
    )
    verify_body = _assert_status(verify_response, 200)
    payment_id = verify_body["payment_id"]

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        payment = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        intent = conn.execute("SELECT * FROM payment_intents WHERE reference = ?", (reference,)).fetchone()
        grant = conn.execute(
            "SELECT * FROM access_grants WHERE user_id = ? AND intent_reference = ?",
            (buyer_id, reference),
        ).fetchone()
        entitlement_count = conn.execute(
            "SELECT COUNT(*) FROM marketplace_entitlements WHERE listing_id = ? AND user_id = ?",
            (listing["listing_id"], buyer_id),
        ).fetchone()[0]

    assert payment is not None
    assert payment["status"] == "completed"
    assert payment["intent_reference"] == reference
    assert payment["tx_signature"] == tx_signature
    assert payment["verification_status"] == "verified"

    assert intent is not None
    assert intent["status"] == "completed"
    assert intent["verification_status"] == "verified"
    assert intent["tx_signature"] == tx_signature
    assert intent["product_id"] == listing["listing_id"]

    assert grant is not None
    assert grant["status"] == "active"
    assert grant["payment_id"] == payment_id
    assert grant["intent_reference"] == reference
    assert grant["product_id"] == listing["listing_id"]
    assert grant["grant_scope"] == f"marketplace_listing:{listing['listing_id']}"
    assert entitlement_count == 1

    evidence_response = client.get(
        f"/admin/audits/payment-evidence/{tx_signature}",
        headers={"X-Agent-Runtime-Token": "test-admin-token"},
    )
    evidence = _assert_status(evidence_response, 200)
    assert evidence["payment_found"] is True
    assert evidence["payment_id_present"] is True
    assert evidence["payment_intent_found"] is True
    assert evidence["payment_reference_present"] is True
    assert evidence["payment_reference"] == reference
    assert evidence["payment_intent_status"] == "completed"
    assert evidence["verification_status"] == "verified"
    assert evidence["access_grant_present"] is True
    assert evidence["listing_scoped"] is True
    assert evidence["marketplace_entitlement_present"] is True
    assert evidence["duplicate_payment_tx_signature_group_count"] == 0
    assert evidence["duplicate_payment_intent_tx_signature_group_count"] == 0
    assert "metadata_json" not in json.dumps(evidence)


def test_pumpfun_listing_verify_is_replay_safe_for_grants_and_entitlements(client: TestClient, monkeypatch):
    creator_id, creator_token = _signup(client, "pumpfun-replay-creator@example.com")
    buyer_id, buyer_token = _signup(client, "pumpfun-replay-buyer@example.com")
    listing = _create_listing(client, creator_user_id=creator_id, creator_token=creator_token)

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, TX_B64_RESPONSE_KEY: "unsigned-local-test-payload", "invoiceId": "invoice-replay"},
    )
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.validate_invoice_payment",
        lambda _payload: {"ok": True, "verified": True, "invoiceId": "invoice-replay"},
    )

    create_response = client.post(
        "/payments/pumpfun/create",
        json={
            "user_id": buyer_id,
            "user_wallet": "WalletReplay1111111111111111111111111111111",
            "listing_id": listing["listing_id"],
        },
        headers=_auth_header(buyer_token),
    )
    reference = _assert_status(create_response, 200)["reference"]
    tx_signature = _sig("R")

    first_verify = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": buyer_id, "reference": reference, "tx_signature": tx_signature},
        headers=_auth_header(buyer_token),
    )
    _assert_status(first_verify, 200)

    second_verify = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": buyer_id, "reference": reference, "tx_signature": tx_signature},
        headers=_auth_header(buyer_token),
    )
    second_body = _assert_status(second_verify, 400)
    assert second_body["error"]["code"] in {"transaction_signature_used", "payment_intent_consumed"}

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        payment_count = conn.execute("SELECT COUNT(*) FROM payments WHERE tx_signature = ?", (tx_signature,)).fetchone()[0]
        grant_count = conn.execute(
            "SELECT COUNT(*) FROM access_grants WHERE user_id = ? AND intent_reference = ?",
            (buyer_id, reference),
        ).fetchone()[0]
        entitlement_count = conn.execute(
            "SELECT COUNT(*) FROM marketplace_entitlements WHERE listing_id = ? AND user_id = ?",
            (listing["listing_id"], buyer_id),
        ).fetchone()[0]

    assert payment_count == 1
    assert grant_count == 1
    assert entitlement_count == 1
