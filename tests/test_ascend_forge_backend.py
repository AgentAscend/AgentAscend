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
    db_path = tmp_path / "agentascend-ascend-forge.db"

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
    assert response.status_code == 200, response.text
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_forge_create_persists_agent_config_without_fake_advanced_execution(client: TestClient):
    _user_id, token = _signup(client, "forge-config-owner@example.com")

    response = client.post(
        "/agents",
        headers=_auth_header(token),
        json={
            "name": "Forge Research Operator",
            "category": "Research",
            "description": "Research public information and summarize findings.",
            "instructions": "Use approved research sources and summarize with citations.",
            "tools": ["web_search", "summarizer"],
            "skills": ["research", "reporting"],
            "autonomy_level": "manual",
            "visibility": "private",
            "deployment_environment": "production",
            "monetization": "private",
        },
    )

    assert response.status_code == 200, response.text
    agent_id = response.json()["agent_id"]

    detail = client.get(f"/agents/{agent_id}", headers=_auth_header(token))
    assert detail.status_code == 200, detail.text
    agent = detail.json()["agent"]
    assert agent["instructions"] == "Use approved research sources and summarize with citations."
    assert agent["tools"] == ["web_search", "summarizer"]
    assert agent["skills"] == ["research", "reporting"]
    assert agent["autonomy_level"] == "manual"
    assert agent["visibility"] == "private"
    assert agent["deployment_environment"] == "production"
    assert agent["monetization"] == "private"
    assert agent["workflow_id"] is None
    assert agent["deployment_id"] is None


def test_forge_config_patch_is_owner_scoped_and_partial(client: TestClient):
    _owner_id, owner_token = _signup(client, "forge-config-patch-owner@example.com")
    _other_id, other_token = _signup(client, "forge-config-patch-attacker@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(owner_token),
        json={"name": "Patchable Forge Agent", "category": "Ops", "description": "Initial mission"},
    )
    assert created.status_code == 200, created.text
    agent_id = created.json()["agent_id"]

    blocked = client.patch(
        f"/agents/{agent_id}/config",
        headers=_auth_header(other_token),
        json={"instructions": "stolen"},
    )
    assert blocked.status_code == 403, blocked.text

    patched = client.patch(
        f"/agents/{agent_id}/config",
        headers=_auth_header(owner_token),
        json={
            "instructions": "Updated runtime instructions",
            "tools": ["web_search"],
            "skills": ["analysis"],
            "autonomy_level": "suggest",
        },
    )
    assert patched.status_code == 200, patched.text
    agent = patched.json()["agent"]
    assert agent["name"] == "Patchable Forge Agent"
    assert agent["description"] == "Initial mission"
    assert agent["instructions"] == "Updated runtime instructions"
    assert agent["tools"] == ["web_search"]
    assert agent["skills"] == ["analysis"]
    assert agent["autonomy_level"] == "suggest"


def test_forge_agent_run_creates_owned_task_and_execution_bridge(client: TestClient):
    _user_id, token = _signup(client, "forge-run-owner@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(token),
        json={"name": "Runnable Forge Agent", "category": "Ops", "description": "Run safe tasks"},
    )
    assert created.status_code == 200, created.text
    agent_id = created.json()["agent_id"]

    run = client.post(
        f"/agents/{agent_id}/run",
        headers=_auth_header(token),
        json={"title": "Summarize current AgentAscend status", "type": "research", "priority": "high"},
    )

    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "ok"
    assert body["agent_id"] == agent_id
    assert body["task_id"].startswith("tsk_")

    task = client.get(f"/tasks/{body['task_id']}")
    assert task.status_code == 200, task.text
    payload = task.json()["task"]
    assert payload["agent_id"] == agent_id
    assert payload["title"] == "Summarize current AgentAscend status"
    assert payload["status"] in {"queued", "running", "completed"}
    assert payload["priority"] == "high"


def test_forge_workflow_run_endpoint_records_real_run(client: TestClient):
    _user_id, token = _signup(client, "forge-workflow-run-owner@example.com")
    workflow = client.post(
        "/workflows",
        headers=_auth_header(token),
        json={"name": "Forge Workflow", "status": "draft"},
    )
    assert workflow.status_code == 200, workflow.text
    workflow_id = workflow.json()["workflow_id"]

    graph = client.put(
        f"/workflows/{workflow_id}/graph",
        headers=_auth_header(token),
        json={
            "nodes": [
                {"node_id": "trigger", "node_type": "manual", "config": {"prompt": "Run"}, "position": {"x": 0, "y": 0}}
            ]
        },
    )
    assert graph.status_code == 200, graph.text

    run = client.post(f"/workflows/{workflow_id}/run", headers=_auth_header(token), json={})
    assert run.status_code == 200, run.text
    body = run.json()
    assert body["status"] == "ok"
    assert body["workflow_id"] == workflow_id
    assert body["run_id"].startswith("run_")
    assert body["run_status"] == "success"

    runs = client.get(f"/workflows/{workflow_id}/runs")
    assert runs.status_code == 200, runs.text
    recorded = runs.json()["runs"][0]
    assert recorded["run_id"] == body["run_id"]
    assert recorded["workflow_id"] == workflow_id
    assert recorded["status"] == "success"


def test_forge_agent_deploy_creates_agent_scoped_deployment(client: TestClient):
    _user_id, token = _signup(client, "forge-deploy-owner@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(token),
        json={"name": "Deployable Forge Agent", "category": "Ops", "description": "Deploy safely"},
    )
    assert created.status_code == 200, created.text
    agent_id = created.json()["agent_id"]

    deployed = client.post(
        f"/agents/{agent_id}/deploy",
        headers=_auth_header(token),
        json={"environment": "production", "region": "us-east", "status": "running"},
    )

    assert deployed.status_code == 200, deployed.text
    deployment_id = deployed.json()["deployment_id"]
    assert deployment_id.startswith("dep_")

    detail = client.get(f"/agents/{agent_id}", headers=_auth_header(token))
    assert detail.status_code == 200, detail.text
    agent = detail.json()["agent"]
    assert agent["deployment_id"] == deployment_id
    assert agent["deployment_environment"] == "production"
