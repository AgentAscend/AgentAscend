import importlib
import sys
from concurrent.futures import ThreadPoolExecutor
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
def app_client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-replay-race.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    monkeypatch.setenv("SOLANA_RECEIVER_WALLET", "ReceiverWallet111111111111111111111111111111")

    import backend.app.main as main

    importlib.reload(main)
    return main.app


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "safe-password", "display_name": "race"},
    )
    assert response.status_code == 200, _safe_response_diag(response)
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def test_replay_race_same_signature_creates_single_payment_and_grant(app_client, monkeypatch):
    monkeypatch.setattr("backend.app.routes.payments.fetch_transaction", lambda _sig: {"meta": {"err": None}})
    monkeypatch.setattr("backend.app.routes.payments.received_lamports_for_wallet", lambda _tx, _wallet: 200_000_000)

    with TestClient(app_client) as seed_client:
        user_id, token = _signup(seed_client, "race@example.com")
        create = seed_client.post("/payments/create", json={"user_id": user_id, "token": "SOL"})
        assert create.status_code == 200, _safe_response_diag(create)
        reference = create.json()["reference"]

    payload = {
        "user_id": user_id,
        "tx_signature": "4" * 88,
        "token": "SOL",
        "reference": reference,
    }
    headers = {"Authorization": f"Bearer {token}"}

    def call_verify(i: int):
        with TestClient(app_client) as c:
            return c.post("/payments/verify", json={**payload, "idempotency_key": f"race-{i}"}, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(call_verify, [1, 2]))

    assert sorted(results) == [200, 400]

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        payments = conn.execute("SELECT COUNT(*) FROM payments WHERE tx_signature = ?", ("4" * 88,)).fetchone()[0]
        grants = conn.execute(
            "SELECT COUNT(*) FROM access_grants WHERE user_id = ? AND intent_reference = ?",
            (user_id, reference),
        ).fetchone()[0]

    assert payments == 1
    assert grants == 1
