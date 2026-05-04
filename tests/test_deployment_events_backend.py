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
    db_path = tmp_path / "agentascend-deployment-events.db"

    import backend.app.db.session as session
    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main
    importlib.reload(main)

    with TestClient(main.app) as test_client:
        yield test_client


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "test-password-123", "display_name": email.split("@", 1)[0]},
    )
    _assert_status(response, 200)
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_status(response, expected_status: int) -> None:
    assert response.status_code == expected_status, {
        "status_code": response.status_code,
        "expected_status": expected_status,
        "json_keys": sorted(response.json().keys()) if response.headers.get("content-type", "").startswith("application/json") else [],
    }


def _insert_owned_deployment_without_events(owner_user_id: str, deployment_id: str = "dep_empty_owner") -> str:
    from backend.app.db.session import get_connection

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO deployments(deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent, requests_per_day, created_at, updated_at)
            VALUES(?, 'Empty owned deployment', 'production', 'running', 'us-east', 1, 0, 0, 0, datetime('now'), datetime('now'))
            """,
            (deployment_id,),
        )
        conn.execute(
            """
            INSERT INTO agents(agent_id, owner_user_id, name, category, description, status, deployment_id, created_at, updated_at)
            VALUES(?, ?, 'Owner deployment agent', 'Ops', 'Owns deployment', 'active', ?, datetime('now'), datetime('now'))
            """,
            (f"agent_{deployment_id}", owner_user_id, deployment_id),
        )
        conn.commit()
    return deployment_id


def test_deployment_events_requires_auth(client: TestClient):
    response = client.get("/deployments/dep_any/events")

    _assert_status(response, 401)


def test_deployment_events_blocks_cross_user(client: TestClient):
    owner_user_id, _owner_token = _signup(client, "deploy-events-owner@example.com")
    _other_user_id, other_token = _signup(client, "deploy-events-other@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_cross_user")

    response = client.get(f"/deployments/{deployment_id}/events", headers=_auth_header(other_token))

    _assert_status(response, 403)


def test_owned_deployment_with_no_events_returns_empty_list(client: TestClient):
    owner_user_id, token = _signup(client, "deploy-events-empty@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_empty_events")

    response = client.get(f"/deployments/{deployment_id}/events", headers=_auth_header(token))

    _assert_status(response, 200)
    body = response.json()
    assert body == {"status": "ok", "deployment_id": deployment_id, "events": []}


def test_agent_deploy_adds_safe_owner_scoped_deployment_event(client: TestClient):
    _owner_user_id, token = _signup(client, "deploy-events-agent-owner@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(token),
        json={"name": "Evented Forge Agent", "category": "Ops", "description": "Deploy with timeline"},
    )
    _assert_status(created, 200)
    agent_id = created.json()["agent_id"]

    deployed = client.post(
        f"/agents/{agent_id}/deploy",
        headers=_auth_header(token),
        json={"environment": "production", "region": "us-east", "status": "running"},
    )
    _assert_status(deployed, 200)
    deployment_id = deployed.json()["deployment_id"]

    response = client.get(f"/deployments/{deployment_id}/events", headers=_auth_header(token))

    _assert_status(response, 200)
    body = response.json()
    assert body["deployment_id"] == deployment_id
    assert len(body["events"]) >= 1
    event = body["events"][0]
    assert set(event) == {"event_id", "deployment_id", "timestamp", "level", "status", "message", "source"}
    assert event["deployment_id"] == deployment_id
    assert event["level"] == "info"
    assert event["status"] == "running"
    assert event["source"] == "agent.deploy"
    assert deployment_id in event["message"]


def test_deployment_events_do_not_leak_raw_metadata_or_secret_values(client: TestClient):
    owner_user_id, token = _signup(client, "deploy-events-redaction@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_redaction")

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_events(event_id, actor_user_id, event_type, target_type, target_id, metadata_json, created_at)
            VALUES('audit_secret_event', ?, 'deployment.create', 'deployment', ?, ?, datetime('now'))
            """,
            (
                owner_user_id,
                deployment_id,
                '{"message":"private_key=SHOULD_NOT_LEAK token=SECRET_TOKEN", "payload_json":{"password":"SECRET_PASSWORD"}}',
            ),
        )
        conn.commit()

    response = client.get(f"/deployments/{deployment_id}/events", headers=_auth_header(token))

    _assert_status(response, 200)
    serialized = str(response.json())
    assert "metadata_json" not in serialized
    assert "payload_json" not in serialized
    assert "private_key" not in serialized
    assert "SHOULD_NOT_LEAK" not in serialized
    assert "SECRET_TOKEN" not in serialized
    assert "SECRET_PASSWORD" not in serialized
