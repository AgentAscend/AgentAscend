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
    db_path = tmp_path / "agentascend-community-test.db"

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


def _create_post(client: TestClient, token: str, title: str = "Real community post", body: str = "Real post body"):
    response = client.post(
        "/community/posts",
        json={"title": title, "body": body},
        headers=_auth_header(token),
    )
    assert response.status_code == 200, response.text
    return response.json()["post_id"]


def test_create_community_post_requires_auth(client: TestClient):
    response = client.post("/community/posts", json={"title": "No auth", "body": "Should fail"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_get_community_post_returns_real_post(client: TestClient):
    user_id, token = _signup(client, "community-get-owner@example.com")
    post_id = _create_post(client, token)

    response = client.get(f"/community/posts/{post_id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["post"]["post_id"] == post_id
    assert body["post"]["author_user_id"] == user_id
    assert body["post"]["title"] == "Real community post"
    assert body["post"]["body"] == "Real post body"
    assert body["post"]["likes"] == 0
    assert body["post"]["created_at"]
    assert body["post"]["updated_at"]


def test_get_missing_community_post_returns_404(client: TestClient):
    response = client.get("/community/posts/post_missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_author_can_edit_community_post(client: TestClient):
    _user_id, token = _signup(client, "community-edit-owner@example.com")
    post_id = _create_post(client, token)

    response = client.patch(
        f"/community/posts/{post_id}",
        json={"title": "Edited title", "body": "Edited body"},
        headers=_auth_header(token),
    )

    assert response.status_code == 200, response.text
    post = response.json()["post"]
    assert post["post_id"] == post_id
    assert post["title"] == "Edited title"
    assert post["body"] == "Edited body"
    assert post["updated_at"]

    detail = client.get(f"/community/posts/{post_id}").json()["post"]
    assert detail["title"] == "Edited title"
    assert detail["body"] == "Edited body"


def test_non_author_cannot_edit_community_post(client: TestClient):
    _owner_id, owner_token = _signup(client, "community-edit-owner2@example.com")
    _other_id, other_token = _signup(client, "community-edit-attacker@example.com")
    post_id = _create_post(client, owner_token)

    response = client.patch(
        f"/community/posts/{post_id}",
        json={"title": "Hijacked"},
        headers=_auth_header(other_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_admin_can_edit_community_post(client: TestClient, monkeypatch):
    _owner_id, owner_token = _signup(client, "community-edit-admin-owner@example.com")
    admin_id, admin_token = _signup(client, "community-edit-admin@example.com")
    monkeypatch.setenv("ADMIN_USER_IDS", admin_id)
    post_id = _create_post(client, owner_token)

    response = client.patch(
        f"/community/posts/{post_id}",
        json={"title": "Admin edited"},
        headers=_auth_header(admin_token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["post"]["title"] == "Admin edited"


def test_patch_community_post_requires_auth(client: TestClient):
    _owner_id, owner_token = _signup(client, "community-edit-auth-owner@example.com")
    post_id = _create_post(client, owner_token)

    response = client.patch(f"/community/posts/{post_id}", json={"title": "No auth"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_author_can_delete_community_post(client: TestClient):
    _user_id, token = _signup(client, "community-delete-owner@example.com")
    post_id = _create_post(client, token)

    response = client.delete(f"/community/posts/{post_id}", headers=_auth_header(token))

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "deleted": True}
    assert client.get(f"/community/posts/{post_id}").status_code == 404


def test_non_author_cannot_delete_community_post(client: TestClient):
    _owner_id, owner_token = _signup(client, "community-delete-owner2@example.com")
    _other_id, other_token = _signup(client, "community-delete-attacker@example.com")
    post_id = _create_post(client, owner_token)

    response = client.delete(f"/community/posts/{post_id}", headers=_auth_header(other_token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert client.get(f"/community/posts/{post_id}").status_code == 200


def test_admin_can_delete_community_post(client: TestClient, monkeypatch):
    _owner_id, owner_token = _signup(client, "community-delete-admin-owner@example.com")
    admin_id, admin_token = _signup(client, "community-delete-admin@example.com")
    monkeypatch.setenv("ADMIN_USER_IDS", admin_id)
    post_id = _create_post(client, owner_token)

    response = client.delete(f"/community/posts/{post_id}", headers=_auth_header(admin_token))

    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok", "deleted": True}
    assert client.get(f"/community/posts/{post_id}").status_code == 404


def test_delete_community_post_requires_auth(client: TestClient):
    _owner_id, owner_token = _signup(client, "community-delete-auth-owner@example.com")
    post_id = _create_post(client, owner_token)

    response = client.delete(f"/community/posts/{post_id}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_deleted_post_no_longer_appears_in_feed(client: TestClient):
    _user_id, token = _signup(client, "community-feed-owner@example.com")
    post_id = _create_post(client, token, title="Feed-visible post")

    feed_before = client.get("/community").json()["posts"]
    assert any(post["post_id"] == post_id for post in feed_before)

    delete_response = client.delete(f"/community/posts/{post_id}", headers=_auth_header(token))
    assert delete_response.status_code == 200, delete_response.text

    feed_after = client.get("/community").json()["posts"]
    assert all(post["post_id"] != post_id for post in feed_after)


def test_existing_community_create_and_list_behavior_still_passes(client: TestClient):
    user_id, token = _signup(client, "community-list-owner@example.com")
    post_id = _create_post(client, token, title="Listed post", body="Listed body")

    response = client.get("/community")

    assert response.status_code == 200, response.text
    posts = response.json()["posts"]
    assert any(
        post["post_id"] == post_id
        and post["author_user_id"] == user_id
        and post["title"] == "Listed post"
        and post["body"] == "Listed body"
        for post in posts
    )
