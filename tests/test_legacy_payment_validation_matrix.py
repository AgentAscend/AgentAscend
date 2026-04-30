import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _safe_response_diag(response):
    try:
        body = response.json()
    except Exception:
        body = {}
    error = body.get("error") if isinstance(body, dict) else None
    error_code = error.get("code") if isinstance(error, dict) else None
    keys = sorted(body.keys()) if isinstance(body, dict) else []
    return f"status_code={response.status_code} error_code={error_code!r} keys={keys}"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-legacy-validation-matrix.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "safe-password", "display_name": "matrix"},
    )
    assert response.status_code == 200, _safe_response_diag(response)
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def test_legacy_validation_matrix_rejects_malformed_signature(client: TestClient):
    user_id, token = _signup(client, "matrix-format@example.com")
    r = client.post(
        "/payments/verify",
        json={"user_id": user_id, "tx_signature": "bad", "token": "SOL", "reference": "x", "idempotency_key": "sig-shape"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_legacy_validation_matrix_rejects_wrong_user(client: TestClient, monkeypatch):
    user_id, owner_token = _signup(client, "matrix-owner@example.com")
    _attacker_id, attacker_token = _signup(client, "matrix-attacker@example.com")

    monkeypatch.setenv("SOLANA_RECEIVER_WALLET", "ReceiverWallet111111111111111111111111111111")
    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    monkeypatch.setattr("backend.app.routes.payments.received_lamports_for_wallet", lambda _tx, _wallet: 200_000_000)

    create = client.post("/payments/create", json={"user_id": user_id, "token": "SOL"}, headers={"Authorization": f"Bearer {owner_token}"})
    assert create.status_code == 200

    r = client.post(
        "/payments/verify",
        json={"user_id": user_id, "tx_signature": "5" * 88, "token": "SOL", "reference": create.json()["reference"], "idempotency_key": "wrong-user"},
        headers={"Authorization": f"Bearer {attacker_token}"},
    )
    assert r.status_code == 403


@pytest.mark.parametrize(
    "token,env,patches,expected_status",
    [
        ("SOL", {"SOLANA_RECEIVER_WALLET": "ReceiverWallet111111111111111111111111111111"}, {"lamports": 1}, 400),
        ("ASND", {"SOLANA_RECEIVER_WALLET": "ReceiverWallet111111111111111111111111111111"}, {}, 500),
        (
            "ASND",
            {
                "SOLANA_RECEIVER_WALLET": "ReceiverWallet111111111111111111111111111111",
                "ASND_MINT_ADDRESS": "Mint111111111111111111111111111111111111111",
            },
            {"token_amount": 0},
            400,
        ),
    ],
)
def test_legacy_validation_matrix_amount_and_mint_failures(client: TestClient, monkeypatch, token, env, patches, expected_status):
    user_id, session_token = _signup(client, f"matrix-{token.lower()}@example.com")

    for k, v in env.items():
        monkeypatch.setenv(k, v)

    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    monkeypatch.setattr("backend.app.routes.payments.received_lamports_for_wallet", lambda _tx, _wallet: patches.get("lamports", 200_000_000))
    monkeypatch.setattr("backend.app.routes.payments.get_receiver_token_account", lambda _wallet, _mint: "ReceiverTokenAcct")
    monkeypatch.setattr("backend.app.routes.payments.received_token_amount_for_wallet", lambda _tx, _acct, _mint: patches.get("token_amount", "100"))

    create = client.post("/payments/create", json={"user_id": user_id, "token": token})
    assert create.status_code == 200, _safe_response_diag(create)

    verify = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": "6" * 88,
            "token": token,
            "reference": create.json()["reference"],
            "idempotency_key": f"matrix-{token}",
        },
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert verify.status_code == expected_status


def test_legacy_validation_matrix_reused_signature_is_rejected(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "matrix-reuse@example.com")

    monkeypatch.setenv("SOLANA_RECEIVER_WALLET", "ReceiverWallet111111111111111111111111111111")
    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    monkeypatch.setattr("backend.app.routes.payments.received_lamports_for_wallet", lambda _tx, _wallet: 200_000_000)

    create = client.post("/payments/create", json={"user_id": user_id, "token": "SOL"})
    assert create.status_code == 200
    reference = create.json()["reference"]

    first = client.post(
        "/payments/verify",
        json={"user_id": user_id, "tx_signature": "7" * 88, "token": "SOL", "reference": reference, "idempotency_key": "first"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200

    create2 = client.post("/payments/create", json={"user_id": user_id, "token": "SOL"})
    second = client.post(
        "/payments/verify",
        json={"user_id": user_id, "tx_signature": "7" * 88, "token": "SOL", "reference": create2.json()["reference"], "idempotency_key": "second"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 400
