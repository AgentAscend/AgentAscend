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
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db_path = tmp_path / "agentascend-test.db"

    import backend.app.db.session as session
    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main
    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "HermesTest123!", "display_name": email.split("@", 1)[0]},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _listing_payload(user_id: str, status: str, title: str = "Queued Publish Probe") -> dict:
    return {
        "creator_user_id": user_id,
        "title": title,
        "description": "Temporary listing created by the marketplace publish e2e test.",
        "category": "Research",
        "pricing_model": "free",
        "price_amount": 0,
        "price_token": "ASND",
        "status": status,
        "tags": ["e2e"],
        "idempotency_key": f"test-{status}-{title}",
    }


def test_frontend_publish_queue_create_is_immediately_discoverable(client: TestClient):
    user_id, token = _signup(client, "marketplace-publish-owner@example.com")

    create_response = client.post(
        "/marketplace/listings",
        json=_listing_payload(user_id, "queued_review"),
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()["listing"]
    listing_id = created["listing_id"]

    assert created["creator_user_id"] == user_id
    assert created["status"] == "published"
    assert created["published_at"] is not None

    creator_response = client.get(
        f"/marketplace/listings?creator_user_id={user_id}",
        headers=_auth_header(token),
    )
    assert creator_response.status_code == 200, creator_response.text
    creator_listings = creator_response.json()["listings"]
    assert any(row["listing_id"] == listing_id and row["status"] == "published" for row in creator_listings)

    discover_response = client.get("/marketplace/discover")
    assert discover_response.status_code == 200, discover_response.text
    discover_listings = discover_response.json()["listings"]
    assert any(row["listing_id"] == listing_id and row["title"] == "Queued Publish Probe" for row in discover_listings)


def test_explicit_draft_create_remains_private_to_discover(client: TestClient):
    user_id, token = _signup(client, "marketplace-draft-owner@example.com")

    create_response = client.post(
        "/marketplace/listings",
        json=_listing_payload(user_id, "draft", title="Private Draft Probe"),
        headers=_auth_header(token),
    )
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()["listing"]

    assert created["status"] == "draft"
    assert created["published_at"] is None

    creator_response = client.get(
        f"/marketplace/listings?creator_user_id={user_id}",
        headers=_auth_header(token),
    )
    assert creator_response.status_code == 200, creator_response.text
    assert any(row["listing_id"] == created["listing_id"] for row in creator_response.json()["listings"])

    discover_response = client.get("/marketplace/discover")
    assert discover_response.status_code == 200, discover_response.text
    assert all(row["listing_id"] != created["listing_id"] for row in discover_response.json()["listings"])
