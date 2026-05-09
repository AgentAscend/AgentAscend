import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _assert_status(response, expected_status: int) -> None:
    assert response.status_code == expected_status, {
        "status_code": response.status_code,
        "expected_status": expected_status,
        "json_keys": sorted(response.json().keys()) if response.headers.get("content-type", "").startswith("application/json") else [],
        "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
    }


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "Password123!", "display_name": email.split("@", 1)[0]},
    )
    _assert_status(response, 200)
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_workflow(client: TestClient, token: str, name: str = "Private Workflow") -> str:
    response = client.post(
        "/workflows",
        headers=_auth_header(token),
        json={"name": name, "status": "draft"},
    )
    _assert_status(response, 200)
    return response.json()["workflow_id"]


def test_workflow_list_requires_auth_and_is_owner_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-workflow-auth.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as client:
        _owner_id, owner_token = _signup(client, "workflow-owner@example.com")
        _other_id, other_token = _signup(client, "workflow-other@example.com")
        owner_workflow_id = _create_workflow(client, owner_token, "Owner Workflow")

        no_auth = client.get("/workflows")
        _assert_status(no_auth, 401)

        owner_list = client.get("/workflows", headers=_auth_header(owner_token))
        _assert_status(owner_list, 200)
        assert [w["workflow_id"] for w in owner_list.json()["workflows"]] == [owner_workflow_id]

        other_list = client.get("/workflows", headers=_auth_header(other_token))
        _assert_status(other_list, 200)
        assert owner_workflow_id not in {w["workflow_id"] for w in other_list.json()["workflows"]}
        assert other_list.json()["workflows"] == []
        assert other_list.json()["recent_runs"] == []


def test_workflow_graph_and_runs_are_owner_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-workflow-detail-auth.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as client:
        _owner_id, owner_token = _signup(client, "workflow-detail-owner@example.com")
        _other_id, other_token = _signup(client, "workflow-detail-other@example.com")
        workflow_id = _create_workflow(client, owner_token, "Owner Detail Workflow")
        graph_payload = {
            "nodes": [
                {"node_id": "trigger", "node_type": "manual", "config": {"prompt": "Run"}, "position": {"x": 0, "y": 0}}
            ]
        }

        for method, path, kwargs in (
            (client.get, f"/workflows/{workflow_id}/graph", {}),
            (client.put, f"/workflows/{workflow_id}/graph", {"json": graph_payload}),
            (client.post, f"/workflows/{workflow_id}/run", {"json": {}}),
            (client.get, f"/workflows/{workflow_id}/runs", {}),
        ):
            blocked = method(path, headers=_auth_header(other_token), **kwargs)
            _assert_status(blocked, 403)

        owner_put = client.put(f"/workflows/{workflow_id}/graph", headers=_auth_header(owner_token), json=graph_payload)
        _assert_status(owner_put, 200)
        assert owner_put.json()["nodes"] == 1

        owner_get = client.get(f"/workflows/{workflow_id}/graph", headers=_auth_header(owner_token))
        _assert_status(owner_get, 200)
        assert owner_get.json()["nodes"] == graph_payload["nodes"]

        owner_run = client.post(f"/workflows/{workflow_id}/run", headers=_auth_header(owner_token), json={})
        _assert_status(owner_run, 200)
        assert owner_run.json()["workflow_id"] == workflow_id
        assert owner_run.json()["nodes"] == 1

        owner_runs = client.get(f"/workflows/{workflow_id}/runs", headers=_auth_header(owner_token))
        _assert_status(owner_runs, 200)
        assert [run["run_id"] for run in owner_runs.json()["runs"]] == [owner_run.json()["run_id"]]


def test_legacy_unowned_workflow_rows_fail_closed(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-workflow-legacy.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)

    import backend.app.main as main

    importlib.reload(main)

    with TestClient(main.app) as client:
        _user_id, token = _signup(client, "workflow-legacy-user@example.com")

        from backend.app.db.session import get_connection

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO workflows(workflow_id, name, status, runs_total, success_rate, updated_at)
                VALUES('wf_legacy_unowned', 'Legacy Unowned', 'draft', 0, 0, datetime('now'))
                """
            )
            conn.execute(
                """
                INSERT INTO workflow_nodes(workflow_id, node_id, node_type, config_json, position_json)
                VALUES('wf_legacy_unowned', 'trigger', 'manual', '{}', '{}')
                """
            )
            conn.commit()

        listed = client.get("/workflows", headers=_auth_header(token))
        _assert_status(listed, 200)
        assert listed.json()["workflows"] == []

        graph = client.get("/workflows/wf_legacy_unowned/graph", headers=_auth_header(token))
        _assert_status(graph, 403)
