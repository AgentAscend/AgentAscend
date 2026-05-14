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


def test_deployment_list_requires_auth(client: TestClient):
    response = client.get("/deployments")

    _assert_status(response, 401)


def test_deployment_detail_requires_auth(client: TestClient):
    response = client.get("/deployments/dep_any")

    _assert_status(response, 401)


def test_deployment_metrics_requires_auth(client: TestClient):
    response = client.get("/deployments/dep_any/metrics")

    _assert_status(response, 401)


def test_deployment_actions_require_auth(client: TestClient):
    response = client.post("/deployments/dep_any/actions", json={"action": "pause"})

    _assert_status(response, 401)


def test_deployment_events_blocks_cross_user(client: TestClient):
    owner_user_id, _owner_token = _signup(client, "deploy-events-owner@example.com")
    _other_user_id, other_token = _signup(client, "deploy-events-other@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_cross_user")

    response = client.get(f"/deployments/{deployment_id}/events", headers=_auth_header(other_token))

    _assert_status(response, 403)


def test_deployment_list_is_scoped_to_authenticated_owner(client: TestClient):
    owner_user_id, owner_token = _signup(client, "deploy-list-owner@example.com")
    other_user_id, other_token = _signup(client, "deploy-list-other@example.com")
    owner_deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_owner_visible")
    other_deployment_id = _insert_owned_deployment_without_events(other_user_id, "dep_other_visible")

    owner_response = client.get("/deployments", headers=_auth_header(owner_token))
    other_response = client.get("/deployments", headers=_auth_header(other_token))

    _assert_status(owner_response, 200)
    _assert_status(other_response, 200)
    owner_ids = {deployment["deployment_id"] for deployment in owner_response.json()["deployments"]}
    other_ids = {deployment["deployment_id"] for deployment in other_response.json()["deployments"]}
    assert owner_deployment_id in owner_ids
    assert other_deployment_id not in owner_ids
    assert other_deployment_id in other_ids
    assert owner_deployment_id not in other_ids


def test_deployment_detail_blocks_cross_user(client: TestClient):
    owner_user_id, _owner_token = _signup(client, "deploy-detail-owner@example.com")
    _other_user_id, other_token = _signup(client, "deploy-detail-other@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_detail_cross_user")

    response = client.get(f"/deployments/{deployment_id}", headers=_auth_header(other_token))

    _assert_status(response, 403)


def test_deployment_metrics_blocks_cross_user(client: TestClient):
    owner_user_id, _owner_token = _signup(client, "deploy-metrics-owner@example.com")
    _other_user_id, other_token = _signup(client, "deploy-metrics-other@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_metrics_cross_user")

    response = client.get(f"/deployments/{deployment_id}/metrics", headers=_auth_header(other_token))

    _assert_status(response, 403)


def test_deployment_actions_block_cross_user_without_status_change(client: TestClient):
    owner_user_id, owner_token = _signup(client, "deploy-action-owner@example.com")
    _other_user_id, other_token = _signup(client, "deploy-action-other@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_action_cross_user")

    response = client.post(f"/deployments/{deployment_id}/actions", headers=_auth_header(other_token), json={"action": "pause"})
    owner_read = client.get(f"/deployments/{deployment_id}", headers=_auth_header(owner_token))

    _assert_status(response, 403)
    _assert_status(owner_read, 200)
    assert owner_read.json()["deployment"]["status"] == "running"


def test_owner_can_pause_resume_restart_own_deployment(client: TestClient):
    owner_user_id, token = _signup(client, "deploy-action-self@example.com")
    deployment_id = _insert_owned_deployment_without_events(owner_user_id, "dep_action_owner")

    for action, expected_status in [("pause", "paused"), ("resume", "running"), ("restart", "running")]:
        response = client.post(f"/deployments/{deployment_id}/actions", headers=_auth_header(token), json={"action": action})

        _assert_status(response, 200)
        assert response.json()["deployment"]["status"] == expected_status


def test_deployment_openapi_documents_auth_header_requirements(client: TestClient):
    spec = client.get("/openapi.json").json()
    required_operations = [
        ("/deployments", "get"),
        ("/deployments/{deployment_id}", "get"),
        ("/deployments/{deployment_id}/metrics", "get"),
        ("/deployments/{deployment_id}/actions", "post"),
        ("/deployments/{deployment_id}/events", "get"),
    ]

    for path, method in required_operations:
        parameters = spec["paths"][path][method].get("parameters", [])
        authorization = [parameter for parameter in parameters if parameter.get("name") == "authorization"]
        assert authorization, f"Missing authorization header parameter for {method.upper()} {path}"
        assert authorization[0]["in"] == "header"


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
