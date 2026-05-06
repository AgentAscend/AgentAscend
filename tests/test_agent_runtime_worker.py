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
        "body": response.text[:1000],
    }


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _signup(client: TestClient, email: str):
    response = client.post(
        "/auth/signup",
        json={"email": email, "password": "password123", "display_name": email.split("@", 1)[0]},
    )
    _assert_status(response, 200)
    body = response.json()
    return body["user"]["user_id"], body["session_token"]


def _runtime_client(tmp_path, monkeypatch):
    db_path = tmp_path / "agentascend-runtime-worker.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "1")
    monkeypatch.setenv("AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED", "0")

    import backend.app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def test_runtime_worker_consumes_queued_agent_run_and_persists_steps_output_and_frontend_visible_status(tmp_path, monkeypatch):
    with _runtime_client(tmp_path, monkeypatch) as client:
        _user_id, token = _signup(client, "runtime-worker-owner@example.com")
        created = client.post(
            "/agents",
            headers=_auth_header(token),
            json={
                "name": "Runtime Research Agent",
                "category": "Research",
                "description": "Execute backend-owned research runtime",
                "instructions": "Research AgentAscend status and produce a concise report.",
                "tools": ["web_search", "summarizer"],
                "skills": ["research", "reporting"],
                "autonomy_level": "assist",
            },
        )
        _assert_status(created, 200)
        agent_id = created.json()["agent_id"]

        run = client.post(
            f"/agents/{agent_id}/run",
            headers=_auth_header(token),
            json={"title": "Prepare runtime status report", "type": "research", "priority": "high"},
        )
        _assert_status(run, 200)
        task_id = run.json()["task_id"]

        from backend.app.services.job_runner import run_job_once

        result = run_job_once("default-task-queue-worker")
        assert result["status"] == "success"
        assert "processed=1" in result["summary"]
        assert "completed=1" in result["summary"]

        task = client.get(f"/tasks/{task_id}", headers=_auth_header(token))
        _assert_status(task, 200)
        assert task.json()["task"]["status"] == "completed"

        outputs = client.get(f"/outputs?task_id={task_id}", headers=_auth_header(token))
        _assert_status(outputs, 200)
        output_list = outputs.json()["outputs"]
        assert len(output_list) == 1
        output = output_list[0]
        assert output["task_id"] == task_id
        assert output["user_id"] == _user_id
        assert "Runtime Research Agent" in output["text"]
        assert "Tool results" in output["text"]
        assert "Skill results" in output["text"]

        execution = client.get(f"/tasks/{task_id}/execution", headers=_auth_header(token))
        _assert_status(execution, 200)
        body = execution.json()
        assert body["execution"]["status"] == "completed"
        step_types = [step["step_type"] for step in body["steps"]]
        assert step_types == ["plan", "tool", "tool", "skill", "skill", "output"]
        assert all(step["status"] == "completed" for step in body["steps"])
        event_types = {event["event_type"] for event in body["events"]}
        assert {"agent_runtime_started", "agent_tool_executed", "agent_skill_executed", "output_created", "execution_completed"}.issubset(event_types)
        assert body["artifacts"]

        command_center = client.get("/dashboard/command-center", headers=_auth_header(token))
        _assert_status(command_center, 200)
        assert command_center.json()["task_counts_by_status"].get("completed") == 1
        assert command_center.json()["output_count"] == 1
        assert command_center.json()["execution_summary"]["counts_by_status"].get("completed") == 1


def test_runtime_worker_stops_at_approval_gate_for_approval_required_tool(tmp_path, monkeypatch):
    with _runtime_client(tmp_path, monkeypatch) as client:
        _user_id, token = _signup(client, "runtime-approval-owner@example.com")
        created = client.post(
            "/agents",
            headers=_auth_header(token),
            json={
                "name": "Approval Gated Agent",
                "category": "Automation",
                "description": "Requires approval before workflow execution",
                "instructions": "Coordinate a workflow but stop at approval gates.",
                "tools": ["workflow_runner", "summarizer"],
                "skills": ["workflow_orchestration", "reporting"],
                "autonomy_level": "manual",
            },
        )
        _assert_status(created, 200)
        agent_id = created.json()["agent_id"]
        run = client.post(
            f"/agents/{agent_id}/run",
            headers=_auth_header(token),
            json={"title": "Run gated workflow", "type": "automation", "priority": "medium"},
        )
        _assert_status(run, 200)
        task_id = run.json()["task_id"]

        from backend.app.services.job_runner import run_job_once

        result = run_job_once("default-task-queue-worker")
        assert result["status"] == "success"
        assert "approval_required=1" in result["summary"]

        task = client.get(f"/tasks/{task_id}", headers=_auth_header(token))
        _assert_status(task, 200)
        assert task.json()["task"]["status"] == "pending_approval"
        assert "workflow_runner requires approval" in task.json()["task"]["error_message"]

        outputs = client.get(f"/outputs?task_id={task_id}", headers=_auth_header(token))
        _assert_status(outputs, 200)
        assert outputs.json()["outputs"] == []

        execution = client.get(f"/tasks/{task_id}/execution", headers=_auth_header(token))
        _assert_status(execution, 200)
        body = execution.json()
        assert body["execution"]["status"] == "pending_approval"
        assert body["approvals"]
        assert body["approvals"][0]["status"] == "pending"
        assert body["approvals"][0]["approval_type"] == "tool_execution"
        assert any(step["step_type"] == "approval_gate" and step["status"] == "pending_approval" for step in body["steps"])
        assert any(event["event_type"] == "agent_approval_required" for event in body["events"])
