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
    db_path = tmp_path / "agentascend-legacy-atomicity.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app, raise_server_exceptions=False) as test_client:
        yield test_client


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "safe-password", "display_name": "atomicity"},
    )
    assert response.status_code == 200, _safe_response_diag(response)
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def test_legacy_verify_rolls_back_payment_when_grant_fails(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "legacy-atomicity@example.com")

    monkeypatch.setenv("SOLANA_RECEIVER_WALLET", "ReceiverWallet111111111111111111111111111111")
    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    monkeypatch.setattr("backend.app.routes.payments.received_lamports_for_wallet", lambda _tx, _wallet: 200_000_000)

    create = client.post("/payments/create", json={"user_id": user_id, "token": "SOL"})
    assert create.status_code == 200, _safe_response_diag(create)
    reference = create.json()["reference"]

    def fail_grant(*_args, **_kwargs):
        raise RuntimeError("grant failed")

    monkeypatch.setattr("backend.app.routes.payments.grant_access", fail_grant)

    verify = client.post(
        "/payments/verify",
        json={
            "user_id": user_id,
            "tx_signature": "3" * 88,
            "token": "SOL",
            "reference": reference,
            "idempotency_key": "atomicity-fail",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify.status_code >= 400

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        payments_count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        grants_count = conn.execute("SELECT COUNT(*) FROM access_grants").fetchone()[0]
        consumed = conn.execute(
            "SELECT consumed_at FROM payment_intents WHERE reference = ?",
            (reference,),
        ).fetchone()[0]

    assert payments_count == 0
    assert grants_count == 0
    assert consumed is None
