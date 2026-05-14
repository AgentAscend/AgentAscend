#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

BASE = "https://api.agentascend.ai"
RUN = str(int(time.time()))
PASSWORD = "test-password-12345"


@dataclass
class ApiResult:
    status: int
    body: dict[str, Any] | list[Any] | str | None


def request(method: str, path: str, *, token: str | None = None, json_body: dict[str, Any] | None = None) -> ApiResult:
    data = None
    headers: dict[str, str] = {}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return ApiResult(resp.status, json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            body: dict[str, Any] | list[Any] | str | None = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw[:120]
        return ApiResult(exc.code, body)


def ok(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS" if condition else "FAIL") + " " + name + (f" :: {detail}" if detail else ""))
    if not condition:
        raise SystemExit(1)


def idset(body: dict[str, Any], key: str, id_key: str) -> set[str]:
    return {str(item.get(id_key)) for item in body.get(key, []) if isinstance(item, dict)}


def contains_marker(value: Any, marker: str) -> bool:
    return marker in json.dumps(value, sort_keys=True)


def search_results_contain_marker(body: Any, marker: str) -> bool:
    """Return whether search result items contain marker, ignoring echoed query fields."""
    if isinstance(body, dict):
        results = body.get("results", [])
    elif isinstance(body, list):
        results = body
    else:
        return False
    if not isinstance(results, list):
        return False
    return contains_marker(results, marker)


def main() -> None:
    marker = f"iso-live-{RUN}"
    a_email = f"aa-iso-a-{RUN}@example.com"
    b_email = f"aa-iso-b-{RUN}@example.com"

    unauth_paths = [
        "/agents",
        "/workflows",
        "/tasks",
        "/outputs",
        "/executions/me",
        "/dashboard/command-center",
        "/deployments",
    ]
    for path in unauth_paths:
        result = request("GET", path)
        ok(f"unauth {path} blocked", result.status in (401, 403), f"status={result.status}")

    a = request("POST", "/auth/signup", json_body={"email": a_email, "password": PASSWORD, "display_name": "Isolation A"})
    b = request("POST", "/auth/signup", json_body={"email": b_email, "password": PASSWORD, "display_name": "Isolation B"})
    ok("user A signup", a.status == 200, f"status={a.status}")
    ok("user B signup", b.status == 200, f"status={b.status}")
    a_token = a.body["session_token"]  # type: ignore[index]
    b_token = b.body["session_token"]  # type: ignore[index]

    agent_name = f"{marker}-agent-a"
    workflow_name = f"{marker}-workflow-a"
    deployment_name = f"{marker}-deployment-a"
    task_title = f"{marker}-task-a"
    run_title = f"{marker}-agent-run-a"

    agent = request("POST", "/agents", token=a_token, json_body={"name": agent_name, "category": "QA", "description": "isolation audit", "visibility": "private"})
    ok("user A create private agent", agent.status == 200, f"status={agent.status}")
    agent_id = agent.body["agent_id"]  # type: ignore[index]

    workflow = request("POST", "/workflows", token=a_token, json_body={"name": workflow_name, "status": "draft"})
    ok("user A create workflow", workflow.status == 200, f"status={workflow.status}")
    workflow_id = workflow.body["workflow_id"]  # type: ignore[index]

    task = request("POST", "/tasks", token=a_token, json_body={"title": task_title, "type": "general", "agent_id": agent_id, "priority": "medium"})
    ok("user A create task", task.status == 200, f"status={task.status}")
    task_id = task.body["task_id"]  # type: ignore[index]

    run = request("POST", f"/agents/{agent_id}/run", token=a_token, json_body={"title": run_title, "type": "general", "priority": "medium"})
    ok("user A run agent creates execution/output", run.status == 200, f"status={run.status}")
    execution_id = run.body.get("execution_id") or run.body.get("execution", {}).get("execution_id")  # type: ignore[union-attr]

    deploy = request("POST", "/deployments", token=a_token, json_body={"name": deployment_name, "environment": "qa", "region": "us-east", "status": "running"})
    ok("user A create deployment", deploy.status == 200, f"status={deploy.status}")
    deployment_id = deploy.body["deployment_id"]  # type: ignore[index]

    # User A can see own records in list endpoints.
    ok("user A agents list includes own", agent_id in idset(request("GET", "/agents", token=a_token).body, "agents", "agent_id"))  # type: ignore[arg-type]
    ok("user A workflows list includes own", workflow_id in idset(request("GET", "/workflows", token=a_token).body, "workflows", "workflow_id"))  # type: ignore[arg-type]
    ok("user A tasks list includes own", task_id in idset(request("GET", "/tasks", token=a_token).body, "tasks", "task_id"))  # type: ignore[arg-type]
    ok("user A deployments list includes own", deployment_id in idset(request("GET", "/deployments", token=a_token).body, "deployments", "deployment_id"))  # type: ignore[arg-type]

    a_outputs = request("GET", "/outputs", token=a_token)
    ok("user A outputs request succeeds", a_outputs.status == 200, f"status={a_outputs.status}")
    output_ids = idset(a_outputs.body, "outputs", "output_id") if isinstance(a_outputs.body, dict) else set()
    output_id = next(iter(output_ids), None)

    # User B list endpoints exclude User A records.
    ok("user B agents list excludes A", agent_id not in idset(request("GET", "/agents", token=b_token).body, "agents", "agent_id"))  # type: ignore[arg-type]
    ok("user B workflows list excludes A", workflow_id not in idset(request("GET", "/workflows", token=b_token).body, "workflows", "workflow_id"))  # type: ignore[arg-type]
    ok("user B tasks list excludes A", task_id not in idset(request("GET", "/tasks", token=b_token).body, "tasks", "task_id"))  # type: ignore[arg-type]
    ok("user B deployments list excludes A", deployment_id not in idset(request("GET", "/deployments", token=b_token).body, "deployments", "deployment_id"))  # type: ignore[arg-type]

    # User B direct-ID probes are blocked.
    direct_checks = [
        ("agent detail", "GET", f"/agents/{agent_id}"),
        ("workflow graph", "GET", f"/workflows/{workflow_id}/graph"),
        ("workflow runs", "GET", f"/workflows/{workflow_id}/runs"),
        ("task detail", "GET", f"/tasks/{task_id}"),
        ("task execution", "GET", f"/tasks/{task_id}/execution"),
        ("task logs", "GET", f"/tasks/{task_id}/logs"),
        ("deployment detail", "GET", f"/deployments/{deployment_id}"),
        ("deployment metrics", "GET", f"/deployments/{deployment_id}/metrics"),
        ("deployment events", "GET", f"/deployments/{deployment_id}/events"),
    ]
    if execution_id:
        direct_checks.append(("execution detail", "GET", f"/executions/{execution_id}"))
    if output_id:
        direct_checks.extend([
            ("output detail", "GET", f"/outputs/{output_id}"),
            ("output download", "GET", f"/outputs/{output_id}/download-url"),
        ])
    for name, method, path in direct_checks:
        result = request(method, path, token=b_token)
        ok(f"user B direct {name} blocked", result.status in (403, 404), f"status={result.status}")

    # User B cannot mutate User A deployment status.
    before = request("GET", f"/deployments/{deployment_id}", token=a_token)
    blocked_action = request("POST", f"/deployments/{deployment_id}/actions", token=b_token, json_body={"action": "pause"})
    after = request("GET", f"/deployments/{deployment_id}", token=a_token)
    before_status = before.body.get("deployment", {}).get("status") if isinstance(before.body, dict) else None
    after_status = after.body.get("deployment", {}).get("status") if isinstance(after.body, dict) else None
    ok("user B deployment action blocked", blocked_action.status in (403, 404), f"status={blocked_action.status}")
    ok("blocked deployment action did not change status", before_status == after_status == "running", f"before={before_status} after={after_status}")

    # Query-spoof probes: private markers must not appear to unauthenticated or other-user search.
    encoded = urllib.parse.quote(marker)
    unauth_search = request("GET", f"/search?q={encoded}")
    b_search = request("GET", f"/search?q={encoded}", token=b_token)
    ok("unauth search does not expose private marker", not search_results_contain_marker(unauth_search.body, marker), f"status={unauth_search.status}")
    ok("user B search does not expose user A private marker", not search_results_contain_marker(b_search.body, marker), f"status={b_search.status}")

    # OpenAPI auth/header guard for patched deployment endpoints.
    spec = request("GET", "/openapi.json")
    ok("openapi available", spec.status == 200, f"status={spec.status}")
    for path, method in [
        ("/deployments", "get"),
        ("/deployments/{deployment_id}", "get"),
        ("/deployments/{deployment_id}/metrics", "get"),
        ("/deployments/{deployment_id}/actions", "post"),
        ("/deployments/{deployment_id}/events", "get"),
    ]:
        params = spec.body["paths"][path][method].get("parameters", [])  # type: ignore[index]
        ok(f"openapi documents authorization for {method.upper()} {path}", any(p.get("name") == "authorization" and p.get("in") == "header" for p in params))

    print("LIVE_TWO_USER_ISOLATION_AUDIT_PASS")
    print(f"SANITIZED_CREATED_COUNTS users=2 agents=1 workflows=1 tasks=1 deployments=1 outputs_observed={len(output_ids)}")


if __name__ == "__main__":
    main()
