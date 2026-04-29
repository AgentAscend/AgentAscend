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
    db_path = tmp_path / "agentascend-tools-access-test.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


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
    }
    return body


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={
            "email": email,
            "password": "not-a-real-secret-test-password",
            "display_name": email.split("@", 1)[0],
        },
    )
    body = _assert_status(response, 200)
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_tools_random_number_requires_auth(client: TestClient):
    owner_user_id, _owner_token = _signup(client, "tool-owner-unauth@example.com")

    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, grant_access

    grant_access(owner_user_id, FEATURE_RANDOM_NUMBER)

    response = client.post(f"/tools/random-number?user_id={owner_user_id}")

    body = _assert_status(response, 401)
    assert body["error"]["code"] == "unauthorized"


def test_tools_random_number_rejects_cross_user_access(client: TestClient):
    owner_user_id, owner_token = _signup(client, "tool-owner@example.com")
    _attacker_user_id, attacker_token = _signup(client, "tool-attacker@example.com")

    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, grant_access

    grant_access(owner_user_id, FEATURE_RANDOM_NUMBER)

    owner_response = client.post(
        f"/tools/random-number?user_id={owner_user_id}",
        headers=_auth_header(owner_token),
    )
    owner_body = _assert_status(owner_response, 200)
    assert owner_body["status"] == "success"

    attack_response = client.post(
        f"/tools/random-number?user_id={owner_user_id}",
        headers=_auth_header(attacker_token),
    )

    attack_body = _assert_status(attack_response, 403)
    assert attack_body["error"]["code"] == "forbidden"


def test_tools_random_number_owner_without_access_gets_payment_required(client: TestClient):
    owner_user_id, owner_token = _signup(client, "tool-owner-unpaid@example.com")

    response = client.post(
        f"/tools/random-number?user_id={owner_user_id}",
        headers=_auth_header(owner_token),
    )

    body = _assert_status(response, 200)
    assert body["status"] == "payment_required"
    assert body["payment_required"] is True


def test_telegram_random_uses_internal_tool_helper_without_web_auth(client: TestClient):
    telegram_user_id = 424242
    mapped_user_id = f"tg:{telegram_user_id}"

    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, grant_access

    grant_access(mapped_user_id, FEATURE_RANDOM_NUMBER)

    response = client.post(
        "/telegram/command",
        json={"telegram_user_id": telegram_user_id, "chat_id": 999, "command": "/random"},
    )

    body = _assert_status(response, 200)
    assert body["status"] == "success"
    assert body["user_id"] == mapped_user_id
    assert body["command"] == "/random"
    assert body["payment"] is None
    assert isinstance(body["result"], int)
