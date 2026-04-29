import importlib
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


AGENT_MINT = "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump"
WSOL_MINT = "So11111111111111111111111111111111111111112"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-pumpfun-routes-test.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    monkeypatch.setenv("AGENT_TOKEN_MINT_ADDRESS", AGENT_MINT)
    monkeypatch.setenv("CURRENCY_MINT", WSOL_MINT)
    monkeypatch.setenv("PRICE_AMOUNT_SMALLEST_UNIT", "100000000")

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "safe-test-password", "display_name": email.split("@", 1)[0]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _intent_row(reference: str):
    from backend.app.db.session import get_connection

    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM payment_intents WHERE reference = ?",
            (reference,),
        ).fetchone()


def test_pumpfun_agent_mint_missing_fails_closed(monkeypatch):
    monkeypatch.delenv("AGENT_TOKEN_MINT_ADDRESS", raising=False)

    from backend.app.routes import pumpfun_payments

    with pytest.raises(Exception):
        pumpfun_payments._agent_token_mint()


def test_pumpfun_create_requires_auth(client: TestClient):
    response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": "user_without_auth", "user_wallet": "Wallet111111111111111111111111111111111111"},
    )

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_pumpfun_create_missing_payment_config_returns_payment_config_error(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-missing-config@example.com")
    monkeypatch.delenv("AGENT_TOKEN_MINT_ADDRESS", raising=False)

    response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet111111111111111111111111111111111111"},
        headers=_auth_header(token),
    )
    assert response.status_code == 500, response.text
    assert response.json()["error"]["code"] == "payment_config_error"


def test_pumpfun_create_rejects_rpc_url_input(client: TestClient):
    user_id, token = _signup(client, "pumpfun-forbidden@example.com")

    response = client.post(
        "/payments/pumpfun/create",
        json={
            "user_id": user_id,
            "user_wallet": "Wallet111111111111111111111111111111111111",
            "rpcUrl": "https://must-not-be-accepted.invalid",
        },
        headers=_auth_header(token),
    )

    assert response.status_code == 422, response.text


def test_pumpfun_create_builds_unsigned_transaction_and_stores_immutable_invoice(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-create@example.com")
    calls = []

    def fake_build_payment_transaction(payload):
        calls.append(payload)
        return {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-123"}

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        fake_build_payment_transaction,
    )

    response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet111111111111111111111111111111111111"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "payment_transaction_built"
    assert body["txBase64"] == "unsigned-tx-base64"
    assert body["invoiceId"] == "invoice-123"
    assert "rpcUrl" not in body
    assert "privateKey" not in body
    assert "secretKey" not in body

    assert len(calls) == 1
    helper_payload = calls[0]
    assert helper_payload["userWallet"] == "Wallet111111111111111111111111111111111111"
    assert helper_payload["agentTokenMint"] == AGENT_MINT
    assert helper_payload["currencyMint"] == WSOL_MINT
    assert helper_payload["amount"] == 100000000
    assert isinstance(helper_payload["memo"], int)
    assert isinstance(helper_payload["startTime"], int)
    assert isinstance(helper_payload["endTime"], int)
    assert helper_payload["endTime"] > helper_payload["startTime"]
    assert "rpcUrl" not in helper_payload

    row = _intent_row(body["reference"])
    assert row is not None
    assert row["user_id"] == user_id
    assert row["user_wallet"] == "Wallet111111111111111111111111111111111111"
    assert row["agent_token_mint"] == AGENT_MINT
    assert row["currency_mint"] == WSOL_MINT
    assert row["currency_symbol"] == "SOL"
    assert row["amount_smallest_unit"] == 100000000
    assert row["memo"] == helper_payload["memo"]
    assert row["start_time"] == helper_payload["startTime"]
    assert row["end_time"] == helper_payload["endTime"]
    assert row["invoice_id"] == "invoice-123"
    assert row["tool_id"] == "random_number"
    assert row["status"] == "pending"
    assert row["verification_status"] == "unverified"
    assert row["tx_signature"] is None


def test_pumpfun_create_helper_failure_returns_safe_error_without_storing_intent(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-create-fail@example.com")

    def fake_build_payment_transaction(_payload):
        return {"ok": False, "errorCode": "RPC_MISSING"}

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        fake_build_payment_transaction,
    )

    response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet222222222222222222222222222222222222"},
        headers=_auth_header(token),
    )

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "payment_helper_error"
    assert "http" not in response.text.lower()

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM payment_intents").fetchone()[0]
    assert count == 0


def test_pumpfun_verify_requires_auth(client: TestClient):
    response = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": "some_user", "reference": "ref", "tx_signature": "3" * 88},
    )

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_pumpfun_verify_malformed_signature_returns_validation_error(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-malformed@example.com")
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-malformed"},
    )
    create_response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet311111111111111111111111111111111111"},
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text

    verify_response = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": user_id, "reference": create_response.json()["reference"], "tx_signature": "bad-sig"},
        headers=_auth_header(token),
    )
    assert verify_response.status_code == 400, verify_response.text
    assert verify_response.json()["error"]["code"] == "validation_error"


def test_pumpfun_verify_rejects_cross_user_reference(client: TestClient, monkeypatch):
    owner_id, owner_token = _signup(client, "pumpfun-owner@example.com")
    _attacker_id, attacker_token = _signup(client, "pumpfun-attacker@example.com")

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-owner"},
    )
    create_response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": owner_id, "user_wallet": "Wallet333333333333333333333333333333333333"},
        headers=_auth_header(owner_token),
    )
    assert create_response.status_code == 200, create_response.text

    attack_response = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": owner_id, "reference": create_response.json()["reference"], "tx_signature": "4" * 88},
        headers=_auth_header(attacker_token),
    )

    assert attack_response.status_code == 403, attack_response.text
    assert attack_response.json()["error"]["code"] == "forbidden"


def test_pumpfun_verify_uses_exact_stored_invoice_params_and_grants_access(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-verify@example.com")
    build_calls = []
    validate_calls = []

    def fake_build_payment_transaction(payload):
        build_calls.append(payload)
        return {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-verify"}

    def fake_validate_invoice_payment(payload):
        validate_calls.append(payload)
        return {"ok": True, "verified": True, "invoiceId": "invoice-verify"}

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        fake_build_payment_transaction,
    )
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.validate_invoice_payment",
        fake_validate_invoice_payment,
    )

    create_response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet444444444444444444444444444444444444"},
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text
    reference = create_response.json()["reference"]

    verify_response = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": user_id, "reference": reference, "tx_signature": "5" * 88},
        headers=_auth_header(token),
    )

    assert verify_response.status_code == 200, verify_response.text
    body = verify_response.json()
    assert body["status"] == "payment_verified"
    assert body["reference"] == reference
    assert body["token"] == "SOL"
    assert body["payment_id"] > 0

    assert validate_calls == [
        {
            "userWallet": build_calls[0]["userWallet"],
            "agentTokenMint": build_calls[0]["agentTokenMint"],
            "currencyMint": build_calls[0]["currencyMint"],
            "amount": build_calls[0]["amount"],
            "memo": build_calls[0]["memo"],
            "startTime": build_calls[0]["startTime"],
            "endTime": build_calls[0]["endTime"],
        }
    ]

    row = _intent_row(reference)
    assert row["status"] == "completed"
    assert row["verification_status"] == "verified"
    assert row["tx_signature"] == "5" * 88
    assert row["completed_at"] is not None

    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, has_access
    from backend.app.db.session import get_connection

    assert has_access(user_id, FEATURE_RANDOM_NUMBER) is True
    with get_connection() as conn:
        grant = conn.execute(
            "SELECT * FROM access_grants WHERE user_id = ? AND intent_reference = ?",
            (user_id, reference),
        ).fetchone()
    assert grant is not None
    assert grant["payment_id"] == body["payment_id"]
    assert grant["source"] == "pumpfun_sdk"


def test_pumpfun_verify_unverified_payment_does_not_grant_access(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-unverified@example.com")

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-unverified"},
    )
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.validate_invoice_payment",
        lambda _payload: {"ok": True, "verified": False, "invoiceId": "invoice-unverified"},
    )

    create_response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet555555555555555555555555555555555555"},
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text

    verify_response = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": user_id, "reference": create_response.json()["reference"], "tx_signature": "6" * 88},
        headers=_auth_header(token),
    )

    assert verify_response.status_code == 400, verify_response.text
    assert verify_response.json()["error"]["code"] == "payment_not_verified"

    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, has_access

    assert has_access(user_id, FEATURE_RANDOM_NUMBER) is False
    assert _intent_row(create_response.json()["reference"])["status"] == "pending"


def test_pumpfun_verify_duplicate_tx_signature_returns_safe_error_without_second_grant(client: TestClient, monkeypatch):
    first_user_id, first_token = _signup(client, "pumpfun-dup-one@example.com")
    second_user_id, second_token = _signup(client, "pumpfun-dup-two@example.com")

    invoice_counter = iter(["invoice-dup-one", "invoice-dup-two"])
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": next(invoice_counter)},
    )
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.validate_invoice_payment",
        lambda _payload: {"ok": True, "verified": True, "invoiceId": "invoice-verified"},
    )

    first_create = client.post(
        "/payments/pumpfun/create",
        json={"user_id": first_user_id, "user_wallet": "Wallet666666666666666666666666666666666666"},
        headers=_auth_header(first_token),
    )
    assert first_create.status_code == 200, first_create.text
    second_create = client.post(
        "/payments/pumpfun/create",
        json={"user_id": second_user_id, "user_wallet": "Wallet777777777777777777777777777777777777"},
        headers=_auth_header(second_token),
    )
    assert second_create.status_code == 200, second_create.text

    tx_signature = "7" * 88
    first_verify = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": first_user_id, "reference": first_create.json()["reference"], "tx_signature": tx_signature},
        headers=_auth_header(first_token),
    )
    assert first_verify.status_code == 200, first_verify.text

    duplicate_verify = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": second_user_id, "reference": second_create.json()["reference"], "tx_signature": tx_signature},
        headers=_auth_header(second_token),
    )
    assert duplicate_verify.status_code == 400, duplicate_verify.text
    assert duplicate_verify.json()["error"]["code"] == "transaction_signature_used"

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        duplicate_grants = conn.execute(
            "SELECT COUNT(*) FROM access_grants WHERE user_id = ? AND intent_reference = ?",
            (second_user_id, second_create.json()["reference"]),
        ).fetchone()[0]
    assert duplicate_grants == 0


def test_pumpfun_verify_expired_intent_does_not_call_helper_or_grant_access(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-expired@example.com")

    monkeypatch.setenv("PAYMENT_TTL_SECONDS", "1")
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-expired"},
    )
    validate_calls = []
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.validate_invoice_payment",
        lambda payload: validate_calls.append(payload) or {"ok": True, "verified": True, "invoiceId": "invoice-expired"},
    )

    create_response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet888888888888888888888888888888888888"},
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        conn.execute(
            "UPDATE payment_intents SET end_time = ?, expires_at_epoch = ? WHERE reference = ?",
            (1, 1, create_response.json()["reference"]),
        )
        conn.commit()

    verify_response = client.post(
        "/payments/pumpfun/verify",
        json={"user_id": user_id, "reference": create_response.json()["reference"], "tx_signature": "8" * 88},
        headers=_auth_header(token),
    )
    assert verify_response.status_code == 400, verify_response.text
    assert verify_response.json()["error"]["code"] == "payment_intent_expired"
    assert validate_calls == []

    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, has_access

    assert has_access(user_id, FEATURE_RANDOM_NUMBER) is False


def test_pumpfun_verify_concurrent_same_signature_single_success_or_safe_replay(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-concurrent@example.com")
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-concurrent"},
    )
    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.validate_invoice_payment",
        lambda _payload: {"ok": True, "verified": True, "invoiceId": "invoice-concurrent"},
    )

    create_response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet121212121212121212121212121212121212"},
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text

    payload = {
        "user_id": user_id,
        "reference": create_response.json()["reference"],
        "tx_signature": "C" * 88,
    }

    def _verify_once():
        return client.post("/payments/pumpfun/verify", json=payload, headers=_auth_header(token))

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _i: _verify_once(), [0, 1]))

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 400], [r.text for r in responses]

    error_codes = [r.json().get("error", {}).get("code") for r in responses if r.status_code == 400]
    assert error_codes[0] in {"transaction_signature_used", "payment_intent_consumed"}

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        payment_count = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE tx_signature = ?",
            ("C" * 88,),
        ).fetchone()[0]
        grant_count = conn.execute(
            "SELECT COUNT(*) FROM access_grants WHERE user_id = ? AND intent_reference = ?",
            (user_id, payload["reference"]),
        ).fetchone()[0]

    assert payment_count == 1
    assert grant_count == 1


def test_record_verified_payment_and_access_handles_postgres_cursor_without_lastrowid(client: TestClient, monkeypatch):
    user_id, token = _signup(client, "pumpfun-postgres-id@example.com")

    monkeypatch.setattr(
        "backend.app.routes.pumpfun_payments.pumpfun_node_helper.build_payment_transaction",
        lambda _payload: {"ok": True, "txBase64": "unsigned-tx-base64", "invoiceId": "invoice-postgres-id"},
    )
    create_response = client.post(
        "/payments/pumpfun/create",
        json={"user_id": user_id, "user_wallet": "Wallet999999999999999999999999999999999999"},
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text
    row = _intent_row(create_response.json()["reference"])

    from backend.app.routes import pumpfun_payments
    from backend.app.db.session import get_connection as real_get_connection

    class CursorWithoutLastrowid:
        def __init__(self, cursor):
            self._cursor = cursor

        def fetchone(self):
            return self._cursor.fetchone()

        def fetchall(self):
            return self._cursor.fetchall()

        def __iter__(self):
            return iter(self._cursor)

    class ConnectionReturningInsertCursorWithoutLastrowid:
        def __init__(self, conn):
            self._conn = conn

        def execute(self, sql, params=()):
            cursor = self._conn.execute(sql, params)
            if sql.lstrip().upper().startswith("INSERT INTO PAYMENTS"):
                return CursorWithoutLastrowid(cursor)
            return cursor

        def commit(self):
            self._conn.commit()

        def rollback(self):
            self._conn.rollback()

        def close(self):
            self._conn.close()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
            self.close()
            return False

    def wrapped_get_connection():
        return ConnectionReturningInsertCursorWithoutLastrowid(real_get_connection())

    monkeypatch.setattr(pumpfun_payments, "get_connection", wrapped_get_connection)

    payment_id = pumpfun_payments._record_verified_payment_and_access(
        row=row,
        tx_signature="9" * 88,
        invoice_id="invoice-postgres-id",
    )

    with real_get_connection() as conn:
        payment = conn.execute(
            "SELECT id FROM payments WHERE tx_signature = ?",
            ("9" * 88,),
        ).fetchone()
        grant = conn.execute(
            "SELECT payment_id FROM access_grants WHERE intent_reference = ?",
            (row["reference"],),
        ).fetchone()

    assert payment is not None
    assert payment_id == payment["id"]
    assert grant is not None
    assert grant["payment_id"] == payment_id
