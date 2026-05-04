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


def test_forge_create_applies_safe_backend_owned_defaults(client: TestClient):
    _user_id, token = _signup(client, "forge-defaults-owner@example.com")

    response = client.post(
        "/agents",
        headers=_auth_header(token),
        json={"name": "Defaulted Forge Agent", "category": "Ops", "description": "Persist safe defaults"},
    )

    _assert_status(response, 200)
    body = response.json()
    agent_id = body["agent_id"]
    agent = body["agent"]
    assert agent["agent_id"] == agent_id
    assert agent["status"] == "draft"
    assert agent["visibility"] == "private"
    assert agent["autonomy_level"] == "manual"
    assert agent["deployment_environment"] == "draft"
    assert agent["monetization"] == "disabled"
    assert agent["tools"] == []
    assert agent["skills"] == []
    assert agent["instructions"] is None
    assert agent["workflow_id"] is None
    assert agent["deployment_id"] is None
    assert agent["marketplace_listing_id"] is None

    detail = client.get(f"/agents/{agent_id}", headers=_auth_header(token))
    _assert_status(detail, 200)
    assert detail.json()["agent"] == agent


def test_forge_create_rejects_unknown_or_malformed_capability_ids(client: TestClient):
    _user_id, token = _signup(client, "forge-capability-validation@example.com")

    unknown = client.post(
        "/agents",
        headers=_auth_header(token),
        json={
            "name": "Unknown Capability Agent",
            "category": "Ops",
            "description": "Should fail cleanly",
            "tools": ["web_search", "not_registered"],
            "skills": ["research"],
        },
    )
    _assert_status(unknown, 400)
    assert unknown.json()["error"]["code"] == "invalid_agent_capability"

    malformed = client.post(
        "/agents",
        headers=_auth_header(token),
        json={
            "name": "Malformed Capability Agent",
            "category": "Ops",
            "description": "Should fail schema validation",
            "tools": "web_search",
        },
    )
    _assert_status(malformed, 422)


def test_forge_patch_revalidates_capabilities_and_preserves_payment_state(client: TestClient):
    user_id, token = _signup(client, "forge-payment-side-effect-owner@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(token),
        json={"name": "No Payment Side Effects", "category": "Ops", "description": "Local-only config"},
    )
    _assert_status(created, 200)
    agent_id = created.json()["agent_id"]

    from backend.app.db.session import get_connection

    with get_connection() as conn:
        before = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM access_grants WHERE user_id=?) AS access_grants,
              (SELECT COUNT(*) FROM marketplace_entitlements WHERE user_id=?) AS marketplace_entitlements,
              (SELECT COUNT(*) FROM payment_intents WHERE user_id=?) AS payment_intents,
              (SELECT COUNT(*) FROM payments WHERE user_id=?) AS payments
            """,
            (user_id, user_id, user_id, user_id),
        ).fetchone()

    invalid_patch = client.patch(
        f"/agents/{agent_id}/config",
        headers=_auth_header(token),
        json={"tools": ["workflow_runner"], "skills": ["not_registered"]},
    )
    _assert_status(invalid_patch, 400)
    assert invalid_patch.json()["error"]["code"] == "invalid_agent_capability"

    valid_patch = client.patch(
        f"/agents/{agent_id}/config",
        headers=_auth_header(token),
        json={"tools": ["workflow_runner", "workflow_runner"], "skills": ["workflow_orchestration"]},
    )
    _assert_status(valid_patch, 200)
    agent = valid_patch.json()["agent"]
    assert agent["tools"] == ["workflow_runner"]
    assert agent["skills"] == ["workflow_orchestration"]

    with get_connection() as conn:
        after = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM access_grants WHERE user_id=?) AS access_grants,
              (SELECT COUNT(*) FROM marketplace_entitlements WHERE user_id=?) AS marketplace_entitlements,
              (SELECT COUNT(*) FROM payment_intents WHERE user_id=?) AS payment_intents,
              (SELECT COUNT(*) FROM payments WHERE user_id=?) AS payments
            """,
            (user_id, user_id, user_id, user_id),
        ).fetchone()

    assert dict(after) == dict(before)


def test_forge_agent_detail_is_owner_scoped(client: TestClient):
    _owner_id, owner_token = _signup(client, "forge-detail-owner@example.com")
    _other_id, other_token = _signup(client, "forge-detail-attacker@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(owner_token),
        json={"name": "Private Forge Agent", "category": "Ops", "description": "Owner only"},
    )
    _assert_status(created, 200)
    agent_id = created.json()["agent_id"]

    blocked = client.get(f"/agents/{agent_id}", headers=_auth_header(other_token))
    _assert_status(blocked, 403)

    missing_auth = client.get(f"/agents/{agent_id}")
    _assert_status(missing_auth, 401)


def test_forge_agent_definition_routes_are_in_openapi(client: TestClient):
    response = client.get("/openapi.json")
    _assert_status(response, 200)
    paths = response.json()["paths"]
    assert "post" in paths["/agents"]
    assert "get" in paths["/agents/{agent_id}"]
    assert "patch" in paths["/agents/{agent_id}/config"]

    create_schema = paths["/agents"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    patch_schema = paths["/agents/{agent_id}/config"]["patch"]["requestBody"]["content"]["application/json"]["schema"]
    assert create_schema["$ref"].endswith("AgentCrudInput")
    assert patch_schema["$ref"].endswith("AgentConfigPatchInput")


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

    _assert_status(response, 200)
    agent_id = response.json()["agent_id"]

    detail = client.get(f"/agents/{agent_id}", headers=_auth_header(token))
    _assert_status(detail, 200)
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
    _assert_status(created, 200)
    agent_id = created.json()["agent_id"]

    blocked = client.patch(
        f"/agents/{agent_id}/config",
        headers=_auth_header(other_token),
        json={"instructions": "stolen"},
    )
    _assert_status(blocked, 403)

    patched = client.patch(
        f"/agents/{agent_id}/config",
        headers=_auth_header(owner_token),
        json={
            "instructions": "Updated runtime instructions",
            "tools": ["web_search"],
            "skills": ["reporting"],
            "autonomy_level": "suggest",
        },
    )
    _assert_status(patched, 200)
    agent = patched.json()["agent"]
    assert agent["name"] == "Patchable Forge Agent"
    assert agent["description"] == "Initial mission"
    assert agent["instructions"] == "Updated runtime instructions"
    assert agent["tools"] == ["web_search"]
    assert agent["skills"] == ["reporting"]
    assert agent["autonomy_level"] == "suggest"


def test_forge_agent_run_creates_owned_task_and_execution_bridge(client: TestClient):
    _user_id, token = _signup(client, "forge-run-owner@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(token),
        json={"name": "Runnable Forge Agent", "category": "Ops", "description": "Run safe tasks"},
    )
    _assert_status(created, 200)
    agent_id = created.json()["agent_id"]

    run = client.post(
        f"/agents/{agent_id}/run",
        headers=_auth_header(token),
        json={"title": "Summarize current AgentAscend status", "type": "research", "priority": "high"},
    )

    _assert_status(run, 200)
    body = run.json()
    assert body["status"] == "ok"
    assert body["agent_id"] == agent_id
    assert body["task_id"].startswith("tsk_")

    task = client.get(f"/tasks/{body['task_id']}")
    _assert_status(task, 200)
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
    _assert_status(workflow, 200)
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
    _assert_status(graph, 200)

    run = client.post(f"/workflows/{workflow_id}/run", headers=_auth_header(token), json={})
    _assert_status(run, 200)
    body = run.json()
    assert body["status"] == "ok"
    assert body["workflow_id"] == workflow_id
    assert body["run_id"].startswith("run_")
    assert body["run_status"] == "success"

    runs = client.get(f"/workflows/{workflow_id}/runs")
    _assert_status(runs, 200)
    recorded = runs.json()["runs"][0]
    assert recorded["run_id"] == body["run_id"]
    assert recorded["workflow_id"] == workflow_id
    assert recorded["status"] == "success"


def test_forge_capability_registry_exposes_backend_owned_templates_tools_and_skills(client: TestClient):
    response = client.get("/agent-capabilities")

    _assert_status(response, 200)
    body = response.json()
    assert body["status"] == "ok"
    tool_ids = {tool["tool_id"] for tool in body["tools"]}
    skill_ids = {skill["skill_id"] for skill in body["skills"]}
    template_ids = {template["template_id"] for template in body["templates"]}
    assert {"web_search", "summarizer", "workflow_runner"}.issubset(tool_ids)
    assert {"research", "reporting", "workflow_orchestration"}.issubset(skill_ids)
    assert {"research_agent", "workflow_automation_agent", "seo_content_agent"}.issubset(template_ids)

    research_template = next(template for template in body["templates"] if template["template_id"] == "research_agent")
    assert research_template["tools"] == ["web_search", "summarizer"]
    assert research_template["skills"] == ["research", "reporting"]
    assert research_template["autonomy_level"] == "manual"
    assert research_template["approval_required"] is True


def test_forge_create_from_template_resolves_real_backend_capabilities(client: TestClient):
    _user_id, token = _signup(client, "forge-template-owner@example.com")

    response = client.post(
        "/agents/from-template",
        headers=_auth_header(token),
        json={
            "template_id": "seo_content_agent",
            "name": "SEO Content Operator",
            "description": "Research keywords and draft SEO content for AgentAscend.",
            "category": "Marketing",
        },
    )

    _assert_status(response, 200)
    body = response.json()
    assert body["status"] == "ok"
    assert body["template_id"] == "seo_content_agent"
    agent_id = body["agent_id"]

    detail = client.get(f"/agents/{agent_id}", headers=_auth_header(token))
    _assert_status(detail, 200)
    agent = detail.json()["agent"]
    assert agent["name"] == "SEO Content Operator"
    assert agent["category"] == "Marketing"
    assert agent["tools"] == ["web_search", "summarizer"]
    assert agent["skills"] == ["research", "content_generation", "seo_planning"]
    assert agent["autonomy_level"] == "manual"
    assert "SEO" in agent["instructions"]


def test_forge_template_create_rejects_unknown_template(client: TestClient):
    _user_id, token = _signup(client, "forge-template-unknown@example.com")

    response = client.post(
        "/agents/from-template",
        headers=_auth_header(token),
        json={"template_id": "not_real", "name": "Bad", "category": "Ops", "description": "Bad template"},
    )

    _assert_status(response, 404)


def test_forge_agent_deploy_creates_agent_scoped_deployment(client: TestClient):
    _user_id, token = _signup(client, "forge-deploy-owner@example.com")
    created = client.post(
        "/agents",
        headers=_auth_header(token),
        json={"name": "Deployable Forge Agent", "category": "Ops", "description": "Deploy safely"},
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
    assert deployment_id.startswith("dep_")

    detail = client.get(f"/agents/{agent_id}", headers=_auth_header(token))
    _assert_status(detail, 200)
    agent = detail.json()["agent"]
    assert agent["deployment_id"] == deployment_id
    assert agent["deployment_environment"] == "production"
