import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-test.db"

    import backend.app.db.session as session
    monkeypatch.setattr(session, "DB_PATH", db_path)

    # Import after DB_PATH is patched so startup initializes the isolated DB.
    import backend.app.main as main
    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "AuditPass123!", "display_name": email.split("@", 1)[0]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "path_template",
    [
        "/users/{user_id}/payments",
        "/token/balances?user_id={user_id}",
        "/token/history?user_id={user_id}",
        "/marketplace/entitlements?user_id={user_id}",
        "/marketplace/licenses?user_id={user_id}",
        "/marketplace/listings?creator_user_id={user_id}",
        "/marketplace/creators/{user_id}/earnings/summary",
        "/marketplace/creators/{user_id}/earnings/events",
        "/marketplace/creators/{user_id}/payouts",
    ],
)
def test_private_user_reads_require_authentication(client: TestClient, path_template: str):
    user_id, _token = _signup(client, "private-read-owner@example.com")

    response = client.get(path_template.format(user_id=user_id))

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "path_template",
    [
        "/users/{user_id}/payments",
        "/token/balances?user_id={user_id}",
        "/token/history?user_id={user_id}",
        "/marketplace/entitlements?user_id={user_id}",
        "/marketplace/licenses?user_id={user_id}",
        "/marketplace/listings?creator_user_id={user_id}",
        "/marketplace/creators/{user_id}/earnings/summary",
        "/marketplace/creators/{user_id}/earnings/events",
        "/marketplace/creators/{user_id}/payouts",
    ],
)
def test_private_user_reads_reject_cross_user_access(client: TestClient, path_template: str):
    owner_id, _owner_token = _signup(client, "private-read-owner2@example.com")
    _other_id, other_token = _signup(client, "private-read-attacker@example.com")

    response = client.get(path_template.format(user_id=owner_id), headers=_auth_header(other_token))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(
    "path_template",
    [
        "/users/{user_id}/payments",
        "/token/balances?user_id={user_id}",
        "/token/history?user_id={user_id}",
        "/marketplace/entitlements?user_id={user_id}",
        "/marketplace/licenses?user_id={user_id}",
        "/marketplace/listings?creator_user_id={user_id}",
        "/marketplace/creators/{user_id}/earnings/summary",
        "/marketplace/creators/{user_id}/earnings/events",
        "/marketplace/creators/{user_id}/payouts",
    ],
)
def test_private_user_reads_allow_owner(client: TestClient, path_template: str):
    user_id, token = _signup(client, "private-read-allowed@example.com")

    response = client.get(path_template.format(user_id=user_id), headers=_auth_header(token))

    assert response.status_code == 200, response.text


def test_agents_list_requires_authentication(client: TestClient):
    response = client.get("/agents")

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_agents_list_returns_only_owned_agents(client: TestClient):
    _owner_id, owner_token = _signup(client, "agent-list-owner@example.com")
    _other_id, other_token = _signup(client, "agent-list-other@example.com")

    owner_create = client.post(
        "/agents",
        json={"name": "Owner Only Agent", "category": "Research", "description": "Owner scoped"},
        headers=_auth_header(owner_token),
    )
    assert owner_create.status_code == 200, owner_create.text
    other_create = client.post(
        "/agents",
        json={"name": "Other User Agent", "category": "Research", "description": "Hidden from owner"},
        headers=_auth_header(other_token),
    )
    assert other_create.status_code == 200, other_create.text

    response = client.get("/agents", headers=_auth_header(owner_token))

    assert response.status_code == 200, response.text
    names = [agent["name"] for agent in response.json()["agents"]]
    assert "Owner Only Agent" in names
    assert "Other User Agent" not in names


def test_agent_detail_rejects_cross_user_access(client: TestClient):
    _owner_id, owner_token = _signup(client, "agent-detail-owner@example.com")
    _other_id, other_token = _signup(client, "agent-detail-attacker@example.com")
    create_response = client.post(
        "/agents",
        json={"name": "Detail Owner Probe", "category": "Research", "description": "Temporary agent"},
        headers=_auth_header(owner_token),
    )
    assert create_response.status_code == 200, create_response.text
    agent_id = create_response.json()["agent_id"]

    response = client.get(f"/agents/{agent_id}", headers=_auth_header(other_token))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"


def test_agent_delete_requires_authentication(client: TestClient):
    _owner_id, owner_token = _signup(client, "agent-delete-owner@example.com")
    create_response = client.post(
        "/agents",
        json={"name": "Delete Auth Probe", "category": "Research", "description": "Temporary agent"},
        headers=_auth_header(owner_token),
    )
    assert create_response.status_code == 200, create_response.text
    agent_id = create_response.json()["agent_id"]

    response = client.delete(f"/agents/{agent_id}")

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_agent_delete_rejects_cross_user_access(client: TestClient):
    _owner_id, owner_token = _signup(client, "agent-delete-owner2@example.com")
    _other_id, other_token = _signup(client, "agent-delete-attacker@example.com")
    create_response = client.post(
        "/agents",
        json={"name": "Delete Owner Probe", "category": "Research", "description": "Temporary agent"},
        headers=_auth_header(owner_token),
    )
    assert create_response.status_code == 200, create_response.text
    agent_id = create_response.json()["agent_id"]

    response = client.delete(f"/agents/{agent_id}", headers=_auth_header(other_token))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"

    owner_response = client.delete(f"/agents/{agent_id}", headers=_auth_header(owner_token))
    assert owner_response.status_code == 200, owner_response.text


def test_marketplace_listing_delete_requires_authentication(client: TestClient):
    owner_id, owner_token = _signup(client, "listing-delete-owner@example.com")
    create_response = client.post(
        "/marketplace/listings",
        json={
            "creator_user_id": owner_id,
            "title": "Delete Listing Auth Probe",
            "description": "Temporary listing",
            "category": "Research",
            "pricing_model": "free",
            "price_amount": 0,
            "price_token": "ASND",
            "status": "draft",
            "tags": [],
        },
        headers=_auth_header(owner_token),
    )
    assert create_response.status_code == 200, create_response.text
    listing_id = create_response.json()["listing"]["listing_id"]

    response = client.delete(f"/marketplace/listings/{listing_id}")

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_marketplace_listing_delete_rejects_cross_user_access(client: TestClient):
    owner_id, owner_token = _signup(client, "listing-delete-owner2@example.com")
    _other_id, other_token = _signup(client, "listing-delete-attacker@example.com")
    create_response = client.post(
        "/marketplace/listings",
        json={
            "creator_user_id": owner_id,
            "title": "Delete Listing Owner Probe",
            "description": "Temporary listing",
            "category": "Research",
            "pricing_model": "free",
            "price_amount": 0,
            "price_token": "ASND",
            "status": "draft",
            "tags": [],
        },
        headers=_auth_header(owner_token),
    )
    assert create_response.status_code == 200, create_response.text
    listing_id = create_response.json()["listing"]["listing_id"]

    response = client.delete(f"/marketplace/listings/{listing_id}", headers=_auth_header(other_token))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "forbidden"

    owner_response = client.delete(f"/marketplace/listings/{listing_id}", headers=_auth_header(owner_token))
    assert owner_response.status_code == 200, owner_response.text


def test_public_marketplace_browse_remains_public(client: TestClient):
    response = client.get("/marketplace/browse")

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"
