import importlib
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-legacy-payment-verify-test.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _sig(ch: str = "3") -> str:
    return ch * 88


def _safe_json(response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


def _assert_status(response, expected_status: int) -> dict[str, Any]:
    body = _safe_json(response)
    assert response.status_code == expected_status, {
        "expected_status": expected_status,
        "actual_status": response.status_code,
        "json_keys": sorted(body.keys()),
        "error_code": body.get("error", {}).get("code") if isinstance(body.get("error"), dict) else None,
        "status": body.get("status"),
    }
    return body


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "local-test-password-only",
            "display_name": email.split("@", 1)[0],
        },
    )
    body = _assert_status(response, 200)
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _configure_fake_sol_payment(monkeypatch, lamports: int = 200_000_000):
    monkeypatch.setenv("SOLANA_RECEIVER_WALLET", "ReceiverWallet111111111111111111111111111111")
    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    monkeypatch.setattr(
        "backend.app.routes.payments.received_lamports_for_wallet",
        lambda _tx, _wallet: lamports,
    )


def _create_legacy_sol_payment(client: TestClient, user_id: str) -> dict[str, Any]:
    response = client.post("/payments/create", json={"user_id": user_id, "token": "SOL"})
    return _assert_status(response, 200)


def test_legacy_payments_verify_requires_auth(client: TestClient, monkeypatch):
    user_id, _token = _signup(client, "verify-unauth@example.com")
    _configure_fake_sol_payment(monkeypatch)

    response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": _sig("4"),
            "token": "SOL",
            "reference": "missing-reference",
            "idempotency_key": "idem-verify-unauth",
        },
    )

    body = _assert_status(response, 401)
    assert body["error"]["code"] == "unauthorized"


def test_legacy_payments_verify_rejects_cross_user_auth(client: TestClient, monkeypatch):
    owner_user_id, _owner_token = _signup(client, "verify-owner@example.com")
    _attacker_user_id, attacker_token = _signup(client, "verify-attacker@example.com")
    _configure_fake_sol_payment(monkeypatch)
    payment = _create_legacy_sol_payment(client, owner_user_id)

    response = client.post(
        "/payments/verify",
        json={
            "user_id": owner_user_id,
            "tx_signature": _sig("5"),
            "token": "SOL",
            "reference": payment["reference"],
            "idempotency_key": "idem-verify-cross-user",
        },
        headers=_auth_header(attacker_token),
    )

    body = _assert_status(response, 403)
    assert body["error"]["code"] == "forbidden"


def test_legacy_payments_verify_requires_reference_binding(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "verify-reference@example.com")
    _configure_fake_sol_payment(monkeypatch)
    payment = _create_legacy_sol_payment(client, user_id)

    wrong_reference_response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": _sig("6"),
            "token": "SOL",
            "reference": "wrong-reference",
            "idempotency_key": "idem-reference-mismatch",
        },
        headers=_auth_header(token),
    )
    _assert_status(wrong_reference_response, 400)

    ok_response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": _sig("7"),
            "token": "SOL",
            "reference": payment["reference"],
            "idempotency_key": "idem-reference-ok",
        },
        headers=_auth_header(token),
    )
    ok_body = _assert_status(ok_response, 200)
    assert ok_body["status"] == "payment_verified"


def test_legacy_payments_verify_failed_idempotency_can_retry_same_key(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "verify-idempotency@example.com")
    monkeypatch.setenv("SOLANA_RECEIVER_WALLET", "ReceiverWallet111111111111111111111111111111")
    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    payment = _create_legacy_sol_payment(client, user_id)

    amounts = iter([10, 200_000_000])
    monkeypatch.setattr(
        "backend.app.routes.payments.received_lamports_for_wallet",
        lambda _tx, _wallet: next(amounts),
    )

    first_response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": _sig("8"),
            "token": "SOL",
            "reference": payment["reference"],
            "idempotency_key": "idem-retry-key",
        },
        headers=_auth_header(token),
    )
    _assert_status(first_response, 400)

    second_response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": _sig("9"),
            "token": "SOL",
            "reference": payment["reference"],
            "idempotency_key": "idem-retry-key",
        },
        headers=_auth_header(token),
    )
    second_body = _assert_status(second_response, 200)
    assert second_body["status"] == "payment_verified"


def test_legacy_payments_verify_rejects_consumed_reference(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "verify-consumed@example.com")
    _configure_fake_sol_payment(monkeypatch)
    payment = _create_legacy_sol_payment(client, user_id)

    first_response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": _sig("A"),
            "token": "SOL",
            "reference": payment["reference"],
            "idempotency_key": "idem-consumed-first",
        },
        headers=_auth_header(token),
    )
    _assert_status(first_response, 200)

    second_response = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": _sig("B"),
            "token": "SOL",
            "reference": payment["reference"],
            "idempotency_key": "idem-consumed-second",
        },
        headers=_auth_header(token),
    )
    _assert_status(second_response, 400)
