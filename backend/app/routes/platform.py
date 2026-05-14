from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Header, Query
from pydantic import BaseModel, Field

from backend.app.db.session import get_connection
from backend.app.schemas.platform import (
    AgentActionRequest,
    AgentActionResponse,
    AgentListResponse,
    AgentRecord,
    AvatarUpdateRequest,
    AvatarUpdateResponse,
    CommandCenterOutputRecord,
    CommandCenterResponse,
    CommandCenterWorkflowRunRecord,
    CommunityPost,
    CommunityResponse,
    CreatorPayoutTotalsResponse,
    DashboardActivity,
    DashboardAgent,
    DashboardOverviewResponse,
    DashboardStat,
    DeploymentActionRequest,
    DeploymentActionResponse,
    DeploymentEventListResponse,
    DeploymentEventRecord,
    DeploymentListResponse,
    DeploymentRecord,
    EntitlementRecord,
    EntitlementsResponse,
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionRecord,
    ExecutionSummaryResponse,
    InstallListingRequest,
    InstallListingResponse,
    LeaderboardEntry,
    MarketplaceBrowseRecord,
    MarketplaceBrowseResponse,
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationRecord,
    OutputListResponse,
    OutputRecord,
    SearchResponse,
    SearchResult,
    TaskListResponse,
    TaskRecord,
    TokenBalancesResponse,
    TokenHistoryRecord,
    TokenHistoryResponse,
    UserPreferences,
    UserPreferencesPatchRequest,
    UserPreferencesResponse,
    WorkflowListResponse,
    WorkflowRecord,
    WorkflowRunRecord,
)
from backend.app.services import execution_ledger
from backend.app.services.auth_service import require_user_access, resolve_session, update_profile
from backend.app.services.error_response import fail
from backend.app.services.job_runner import run_job_once

router = APIRouter()


def _require_user_id(authorization: str | None) -> str:
    auth = resolve_session(authorization)
    return auth["user"]["user_id"]


def _row_dict(row):
    if row is None:
        return None

    result = {}
    for k, v in dict(row).items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result


def _json_list(value) -> list[str]:
    if value in (None, ""):
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def _agent_payload(row) -> dict:
    payload = _row_dict(row)
    if payload is None:
        return None
    payload["tools"] = _json_list(payload.pop("tools_json", None))
    payload["skills"] = _json_list(payload.pop("skills_json", None))
    payload["autonomy_level"] = payload.get("autonomy_level") or "manual"
    payload["visibility"] = payload.get("visibility") or "private"
    payload["deployment_environment"] = payload.get("deployment_environment") or "draft"
    payload["monetization"] = payload.get("monetization") or "disabled"
    return payload


AGENT_SELECT_COLUMNS = """
    agent_id, name, category, description, status, tasks_completed, success_rate,
    instructions, tools_json, skills_json, autonomy_level, visibility,
    deployment_environment, monetization, workflow_id, deployment_id,
    marketplace_listing_id, created_at, updated_at
"""


def _authorized_scope_user_id(user_id: str | None, authorization: str | None) -> str:
    auth = resolve_session(authorization)
    actor = auth["user"]
    if user_id:
        if actor["user_id"] != user_id and actor.get("role") != "admin":
            fail(403, "forbidden", "Authenticated user cannot access another user's data")
        return user_id
    return actor["user_id"]


def _require_owned_workflow(conn, workflow_id: str, actor_user_id: str) -> None:
    row = conn.execute("SELECT owner_user_id FROM workflows WHERE workflow_id=?", (workflow_id,)).fetchone()
    if not row:
        fail(404, "not_found", "Workflow not found")
    if not row["owner_user_id"] or row["owner_user_id"] != actor_user_id:
        fail(403, "forbidden", "Authenticated user cannot access another user's workflow")


def _task_worker_background_enabled() -> bool:
    raw = os.getenv("AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED")
    if raw is None or raw.strip() == "":
        return True
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return True


def _trigger_task_queue_worker():
    try:
        run_job_once("default-task-queue-worker")
    except Exception:
        # Task creation must remain durable even if the asynchronous worker cannot run immediately.
        # The scheduled job can retry queued tasks on the next runtime/admin scheduler tick.
        return None


@router.get("/dashboard/overview", response_model=DashboardOverviewResponse)
def dashboard_overview():
    with get_connection() as conn:
        stats_row = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM agents) AS active_agents,
              (SELECT COUNT(*) FROM deployments) AS deployments,
              (SELECT COUNT(*) FROM tasks WHERE status='completed') AS tasks_completed,
              (SELECT COALESCE(AVG(success_rate), 0) FROM agents) AS avg_success
            """
        ).fetchone()

        agents_rows = conn.execute(
            """
            SELECT agent_id, name, category, status, description, success_rate
            FROM agents
            ORDER BY updated_at DESC
            LIMIT 4
            """
        ).fetchall()

        activity_rows = conn.execute(
            """
            SELECT source, action, occurred_at
            FROM activity_log
            ORDER BY occurred_at DESC
            LIMIT 8
            """
        ).fetchall()

    stats = [
        DashboardStat(label="Active Agents", value=str(stats_row["active_agents"]), change="+0", change_type="neutral"),
        DashboardStat(label="Deployments", value=str(stats_row["deployments"]), change="+0", change_type="neutral"),
        DashboardStat(label="Tasks Completed", value=str(stats_row["tasks_completed"]), change="+0", change_type="neutral"),
        DashboardStat(label="Success Rate", value=f"{float(stats_row['avg_success']):.1f}%", change="+0%", change_type="neutral"),
    ]

    active_agents = [
        DashboardAgent(
            agent_id=row["agent_id"],
            name=row["name"],
            category=row["category"],
            status=row["status"],
            task=row["description"],
            success_rate=float(row["success_rate"]),
        )
        for row in agents_rows
    ]

    recent_activity = [DashboardActivity(source=row["source"], action=row["action"], occurred_at=row["occurred_at"]) for row in activity_rows]

    return {"status": "ok", "stats": stats, "active_agents": active_agents, "recent_activity": recent_activity}


def _counts_by_status(rows) -> dict[str, int]:
    return {str(row["status"]): int(row["count"] or 0) for row in rows}


@router.get("/dashboard/command-center", response_model=CommandCenterResponse)
def dashboard_command_center(authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        agent_status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM agents
            WHERE owner_user_id=?
            GROUP BY status
            """,
            (actor,),
        ).fetchall()

        deployment_status_rows = conn.execute(
            """
            SELECT d.status, COUNT(*) AS count
            FROM deployments d
            JOIN agents a ON a.deployment_id=d.deployment_id
            WHERE a.owner_user_id=?
            GROUP BY d.status
            """,
            (actor,),
        ).fetchall()
        deployment_environment_rows = conn.execute(
            """
            SELECT d.environment AS status, COUNT(*) AS count
            FROM deployments d
            JOIN agents a ON a.deployment_id=d.deployment_id
            WHERE a.owner_user_id=?
            GROUP BY d.environment
            """,
            (actor,),
        ).fetchall()

        task_status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM tasks
            WHERE user_id=?
            GROUP BY status
            """,
            (actor,),
        ).fetchall()

        output_total = conn.execute("SELECT COUNT(*) AS count FROM outputs WHERE user_id=?", (actor,)).fetchone()
        output_rows = conn.execute(
            """
            SELECT output_id, task_id, user_id, title, output_type, size_bytes, download_url, created_at
            FROM outputs
            WHERE user_id=?
            ORDER BY created_at DESC, id DESC
            LIMIT 10
            """,
            (actor,),
        ).fetchall()

        recent_execution_rows = conn.execute(
            """
            SELECT execution_id, source_type, source_id, user_id, agent_id, status, started_at, finished_at, metadata_json,
                   0 AS event_count, 0 AS artifact_count
            FROM executions
            WHERE user_id=?
            ORDER BY started_at DESC, id DESC
            LIMIT 10
            """,
            (actor,),
        ).fetchall()
        recent_failure_rows = conn.execute(
            """
            SELECT execution_id, source_type, source_id, user_id, agent_id, status, started_at, finished_at, metadata_json,
                   0 AS event_count, 0 AS artifact_count
            FROM executions
            WHERE user_id=? AND status='failed'
            ORDER BY started_at DESC, id DESC
            LIMIT 10
            """,
            (actor,),
        ).fetchall()

        workflow_status_rows = conn.execute(
            """
            SELECT w.status, COUNT(*) AS count
            FROM workflows w
            JOIN audit_events ae ON ae.target_type='workflow'
                 AND ae.target_id=w.workflow_id
                 AND ae.event_type='workflow.create'
                 AND ae.actor_user_id=?
            GROUP BY w.status
            """,
            (actor,),
        ).fetchall()
        workflow_run_rows = conn.execute(
            """
            SELECT wr.run_id, wr.workflow_id, wr.status, wr.duration_ms, wr.started_at
            FROM workflow_runs wr
            JOIN audit_events ae ON ae.target_type='workflow'
                 AND ae.target_id=wr.workflow_id
                 AND ae.event_type='workflow.create'
                 AND ae.actor_user_id=?
            ORDER BY wr.started_at DESC, wr.id DESC
            LIMIT 10
            """,
            (actor,),
        ).fetchall()

    return {
        "status": "ok",
        "agent_counts_by_status": _counts_by_status(agent_status_rows),
        "deployment_counts_by_status": _counts_by_status(deployment_status_rows),
        "deployment_counts_by_environment": _counts_by_status(deployment_environment_rows),
        "task_counts_by_status": _counts_by_status(task_status_rows),
        "output_count": int(output_total["count"] or 0),
        "recent_outputs": [CommandCenterOutputRecord(**_row_dict(row)) for row in output_rows],
        "execution_summary": _execution_summary_for_user(actor),
        "recent_executions": [_execution_record_payload(_row_dict(row)) for row in recent_execution_rows],
        "recent_failures": [_execution_record_payload(_row_dict(row)) for row in recent_failure_rows],
        "workflow_counts_by_status": _counts_by_status(workflow_status_rows),
        "recent_workflow_runs": [CommandCenterWorkflowRunRecord(**_row_dict(row)) for row in workflow_run_rows],
    }


@router.get("/agents", response_model=AgentListResponse)
def list_agents(authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT {AGENT_SELECT_COLUMNS}
            FROM agents a
            WHERE COALESCE(
                a.owner_user_id,
                (
                    SELECT ae.actor_user_id
                    FROM audit_events ae
                    WHERE ae.target_type='agent'
                      AND ae.target_id=a.agent_id
                      AND ae.event_type='agent.create'
                    ORDER BY ae.created_at ASC, ae.id ASC
                    LIMIT 1
                )
            ) = ?
            ORDER BY a.updated_at DESC
            """,
            (actor,),
        ).fetchall()

    return {"status": "ok", "agents": [AgentRecord(**_agent_payload(r)) for r in rows]}


@router.post("/agents/{agent_id}/actions", response_model=AgentActionResponse)
def act_on_agent(agent_id: str, payload: AgentActionRequest, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    status_by_action = {"start": "active", "resume": "active", "pause": "paused"}
    with get_connection() as conn:
        _require_agent_owner(conn, agent_id, actor)

        conn.execute(
            "UPDATE agents SET status=?, updated_at=datetime('now') WHERE agent_id=?",
            (status_by_action[payload.action], agent_id),
        )
        conn.execute(
            "INSERT INTO activity_log(source, action, occurred_at) VALUES(?, ?, datetime('now'))",
            ("agent", f"{payload.action} {agent_id}"),
        )
        conn.commit()
        row = conn.execute(
            f"""
            SELECT {AGENT_SELECT_COLUMNS}
            FROM agents
            WHERE agent_id=?
            """,
            (agent_id,),
        ).fetchone()

    return {"status": "ok", "agent": AgentRecord(**_agent_payload(row))}


@router.get("/deployments", response_model=DeploymentListResponse)
def list_deployments(authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent,
                   requests_per_day, created_at, updated_at
            FROM deployments d
            WHERE EXISTS (
                SELECT 1
                FROM agents a
                WHERE a.deployment_id=d.deployment_id
                  AND a.owner_user_id=?
            )
            OR EXISTS (
                SELECT 1
                FROM audit_events ae
                WHERE ae.target_type='deployment'
                  AND ae.target_id=d.deployment_id
                  AND ae.actor_user_id=?
            )
            ORDER BY updated_at DESC
            """,
            (actor, actor),
        ).fetchall()

    return {"status": "ok", "deployments": [DeploymentRecord(**_row_dict(r)) for r in rows]}


@router.post("/deployments/{deployment_id}/actions", response_model=DeploymentActionResponse)
def act_on_deployment(
    deployment_id: str,
    payload: DeploymentActionRequest,
    authorization: str | None = Header(default=None),
):
    actor = _require_user_id(authorization)
    next_status = "running" if payload.action in {"resume", "restart"} else "paused"
    with get_connection() as conn:
        _require_deployment_owner(conn, deployment_id, actor)

        conn.execute(
            "UPDATE deployments SET status=?, updated_at=datetime('now') WHERE deployment_id=?",
            (next_status, deployment_id),
        )
        conn.execute(
            "INSERT INTO activity_log(source, action, occurred_at) VALUES(?, ?, datetime('now'))",
            ("deployment", f"{payload.action} {deployment_id}"),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent,
                   requests_per_day, created_at, updated_at
            FROM deployments
            WHERE deployment_id=?
            """,
            (deployment_id,),
        ).fetchone()

    _audit(actor, f"deployment.{payload.action}", "deployment", deployment_id)
    return {"status": "ok", "deployment": DeploymentRecord(**_row_dict(row))}


@router.get("/workflows", response_model=WorkflowListResponse)
def list_workflows(authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        workflows = conn.execute(
            """
            SELECT workflow_id, name, status, runs_total, success_rate, updated_at
            FROM workflows
            WHERE owner_user_id=?
            ORDER BY updated_at DESC
            """,
            (actor,),
        ).fetchall()

        runs = conn.execute(
            """
            SELECT wr.run_id, wr.workflow_id, wr.status, wr.duration_ms, wr.started_at
            FROM workflow_runs wr
            JOIN workflows w ON w.workflow_id=wr.workflow_id
            WHERE w.owner_user_id=?
            ORDER BY wr.started_at DESC
            LIMIT 20
            """,
            (actor,),
        ).fetchall()

    return {
        "status": "ok",
        "workflows": [WorkflowRecord(**_row_dict(r)) for r in workflows],
        "recent_runs": [WorkflowRunRecord(**_row_dict(r)) for r in runs],
    }


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(status: str | None = None, user_id: str | None = None, authorization: str | None = Header(default=None)):
    scoped_user_id = _authorized_scope_user_id(user_id, authorization)
    query = """
        SELECT task_id, user_id, agent_id, type, title, status, priority, assigned_to, error_message, created_at, updated_at
        FROM tasks
    """
    clauses: list[str] = []
    params: list[str] = []
    if status:
        clauses.append("status=?")
        params.append(status)
    clauses.append("user_id=?")
    params.append(scoped_user_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY updated_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    return {"status": "ok", "tasks": [TaskRecord(**_row_dict(r)) for r in rows]}


@router.get("/outputs", response_model=OutputListResponse)
def list_outputs(task_id: str | None = None, user_id: str | None = None, authorization: str | None = Header(default=None)):
    scoped_user_id = _authorized_scope_user_id(user_id, authorization)
    query = """
            SELECT output_id, task_id, user_id, title, output_type, content, text, file_url, size_bytes, download_url, created_at
            FROM outputs
    """
    clauses: list[str] = []
    params: list[str] = []
    if task_id:
        clauses.append("task_id=?")
        params.append(task_id)
    clauses.append("user_id=?")
    params.append(scoped_user_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()

    return {"status": "ok", "outputs": [OutputRecord(**_row_dict(r)) for r in rows]}


_SECRET_RESPONSE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "content",
    "credential",
    "database_url",
    "password",
    "passwd",
    "postgres_url",
    "private_key",
    "secret",
    "token",
)


def _safe_json_dict(value) -> dict:
    if not isinstance(value, dict):
        return {}
    cleaned: dict = {}
    for key, nested in value.items():
        key_text = str(key).lower()
        if any(part in key_text for part in _SECRET_RESPONSE_KEY_PARTS):
            continue
        if isinstance(nested, dict):
            cleaned[key] = _safe_json_dict(nested)
        elif isinstance(nested, list):
            cleaned[key] = [_safe_json_dict(item) if isinstance(item, dict) else item for item in nested]
        else:
            cleaned[key] = nested
    return cleaned


def _execution_record_payload(execution: dict) -> ExecutionRecord:
    return ExecutionRecord(
        execution_id=execution["execution_id"],
        source_type=execution.get("source_type"),
        source_id=execution.get("source_id"),
        user_id=execution.get("user_id"),
        agent_id=execution.get("agent_id"),
        status=execution["status"],
        started_at=execution.get("started_at"),
        finished_at=execution.get("finished_at"),
        metadata=_safe_json_dict(execution.get("metadata")),
        event_count=int(execution.get("event_count") or 0),
        artifact_count=int(execution.get("artifact_count") or 0),
    )


def _execution_detail_payload(execution: dict) -> dict:
    execution_id = execution["execution_id"]
    events = [
        {
            "event_id": event["event_id"],
            "execution_id": event["execution_id"],
            "step_id": event.get("step_id"),
            "event_type": event["event_type"],
            "level": event["level"],
            "message": event.get("message"),
            "payload": _safe_json_dict(event.get("payload")),
            "created_at": event["created_at"],
        }
        for event in execution_ledger.list_execution_events(execution_id)
    ]
    artifacts = [
        {
            "artifact_id": artifact["artifact_id"],
            "execution_id": artifact["execution_id"],
            "step_id": artifact.get("step_id"),
            "artifact_type": artifact["artifact_type"],
            "name": artifact["name"],
            "uri": artifact.get("uri"),
            "metadata": _safe_json_dict(artifact.get("metadata")),
            "created_at": artifact["created_at"],
        }
        for artifact in execution_ledger.list_execution_artifacts(execution_id)
    ]
    steps = [
        {
            "step_id": step["step_id"],
            "execution_id": step["execution_id"],
            "step_order": step["step_order"],
            "step_type": step["step_type"],
            "name": step["name"],
            "status": step["status"],
            "started_at": step.get("started_at"),
            "finished_at": step.get("finished_at"),
            "metadata": _safe_json_dict(step.get("metadata")),
        }
        for step in execution_ledger.list_execution_steps(execution_id)
    ]
    costs = [
        {
            "cost_id": cost["cost_id"],
            "execution_id": cost["execution_id"],
            "step_id": cost.get("step_id"),
            "provider": cost.get("provider"),
            "model": cost.get("model"),
            "input_tokens": cost["input_tokens"],
            "output_tokens": cost["output_tokens"],
            "cost_amount": cost["cost_amount"],
            "cost_currency": cost["cost_currency"],
            "metadata": _safe_json_dict(cost.get("metadata")),
            "created_at": cost["created_at"],
        }
        for cost in execution_ledger.list_execution_costs(execution_id)
    ]
    approvals = [
        {
            "approval_id": approval["approval_id"],
            "execution_id": approval["execution_id"],
            "step_id": approval.get("step_id"),
            "approval_type": approval["approval_type"],
            "status": approval["status"],
            "requested_by": approval.get("requested_by"),
            "approved_by": approval.get("approved_by"),
            "requested_at": approval["requested_at"],
            "decided_at": approval.get("decided_at"),
            "reason": approval.get("reason"),
            "metadata": _safe_json_dict(approval.get("metadata")),
        }
        for approval in execution_ledger.list_execution_approvals(execution_id)
    ]
    execution_with_counts = dict(execution)
    execution_with_counts["event_count"] = len(events)
    execution_with_counts["artifact_count"] = len(artifacts)
    return {
        "status": "ok",
        "execution": _execution_record_payload(execution_with_counts),
        "steps": steps,
        "events": events,
        "artifacts": artifacts,
        "costs": costs,
        "approvals": approvals,
    }


def _require_execution_owner(execution: dict, actor: dict) -> None:
    if execution.get("user_id") != actor["user_id"] and actor.get("role") != "admin":
        fail(403, "forbidden", "Authenticated user cannot access another user's execution")


def _execution_summary_for_user(user_id: str) -> dict:
    with get_connection() as conn:
        status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM executions
            WHERE user_id=?
            GROUP BY status
            """,
            (user_id,),
        ).fetchall()
        latest = conn.execute(
            "SELECT started_at FROM executions WHERE user_id=? ORDER BY started_at DESC, id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        totals = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM executions WHERE user_id=?) AS total_executions,
              (SELECT COUNT(*) FROM executions WHERE user_id=? AND status='failed') AS recent_failures,
              (SELECT COUNT(*) FROM execution_events ev JOIN executions e ON e.execution_id=ev.execution_id WHERE e.user_id=?) AS recent_event_count,
              (SELECT COUNT(*) FROM execution_artifacts art JOIN executions e ON e.execution_id=art.execution_id WHERE e.user_id=?) AS recent_artifact_count,
              (SELECT COUNT(*) FROM execution_events ev JOIN executions e ON e.execution_id=ev.execution_id WHERE e.user_id=? AND ev.payload_json IS NULL) AS malformed_event_json,
              (SELECT COUNT(*) FROM execution_artifacts art JOIN executions e ON e.execution_id=art.execution_id WHERE e.user_id=? AND art.metadata_json IS NULL) AS malformed_artifact_json
            """,
            (user_id, user_id, user_id, user_id, user_id, user_id),
        ).fetchone()
    counts_by_status = {row["status"]: int(row["count"]) for row in status_rows}
    return {
        "status": "ok",
        "scope": "user",
        "total_executions": int(totals["total_executions"] or 0),
        "counts_by_status": counts_by_status,
        "recent_event_count": int(totals["recent_event_count"] or 0),
        "recent_artifact_count": int(totals["recent_artifact_count"] or 0),
        "recent_failures": int(totals["recent_failures"] or 0),
        "latest_execution_timestamp": latest["started_at"] if latest else None,
        "health_flags": {
            "missing_executions": 0,
            "orphan_events": 0,
            "orphan_artifacts": 0,
            "malformed_json": int((totals["malformed_event_json"] or 0) + (totals["malformed_artifact_json"] or 0)),
            "sensitive_match": 0,
        },
    }


@router.get("/executions/me", response_model=ExecutionListResponse)
def list_my_executions(
    authorization: str | None = Header(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
):
    auth = resolve_session(authorization)
    user_id = auth["user"]["user_id"]
    effective_source_id = task_id or source_id
    effective_source_type = "task" if task_id else source_type
    executions = execution_ledger.list_executions_for_user(
        user_id,
        limit=limit,
        offset=offset,
        status=status,
        source_type=effective_source_type,
        source_id=effective_source_id,
        agent_id=agent_id,
    )
    total = execution_ledger.count_executions_for_user(
        user_id,
        status=status,
        source_type=effective_source_type,
        source_id=effective_source_id,
        agent_id=agent_id,
    )
    return {
        "status": "ok",
        "executions": [_execution_record_payload(execution) for execution in executions],
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get("/executions/summary", response_model=ExecutionSummaryResponse)
def execution_summary(authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    return _execution_summary_for_user(auth["user"]["user_id"])


@router.get("/executions/{execution_id}", response_model=ExecutionDetailResponse)
def get_execution_detail(execution_id: str, authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    execution = execution_ledger.get_execution(execution_id)
    if not execution:
        fail(404, "not_found", "Execution not found")
    _require_execution_owner(execution, auth["user"])
    return _execution_detail_payload(execution)


@router.get("/community", response_model=CommunityResponse)
def community_feed():
    with get_connection() as conn:
        posts_rows = conn.execute(
            """
            SELECT post_id, author_user_id, title, body, likes, created_at, updated_at
            FROM community_posts
            ORDER BY created_at DESC
            LIMIT 30
            """
        ).fetchall()
        leaderboard_rows = conn.execute(
            """
            SELECT author_user_id AS user_id, SUM(likes) AS score
            FROM community_posts
            GROUP BY author_user_id
            ORDER BY score DESC
            LIMIT 10
            """
        ).fetchall()

    posts = [CommunityPost(**_row_dict(r)) for r in posts_rows]
    leaderboard = [LeaderboardEntry(**_row_dict(r)) for r in leaderboard_rows]
    return {"status": "ok", "posts": posts, "leaderboard": leaderboard}


@router.get("/users/me/preferences", response_model=UserPreferencesResponse)
def get_preferences(authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT notifications_email, notifications_push, notifications_marketing, theme
            FROM user_preferences
            WHERE user_id=?
            """,
            (user_id,),
        ).fetchone()

        if row is None:
            conn.execute(
                """
                INSERT INTO user_preferences(user_id, notifications_email, notifications_push, notifications_marketing, theme, updated_at)
                VALUES (?, 1, 1, 0, 'dark', datetime('now'))
                """,
                (user_id,),
            )
            conn.commit()
            prefs = UserPreferences()
        else:
            prefs = UserPreferences(
                notifications_email=bool(row["notifications_email"]),
                notifications_push=bool(row["notifications_push"]),
                notifications_marketing=bool(row["notifications_marketing"]),
                theme=row["theme"],
            )

    return {"status": "ok", "preferences": prefs}


@router.patch("/users/me/preferences", response_model=UserPreferencesResponse)
def patch_preferences(payload: UserPreferencesPatchRequest, authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)

    current = get_preferences(authorization)["preferences"]
    updated = UserPreferences(
        notifications_email=current.notifications_email if payload.notifications_email is None else payload.notifications_email,
        notifications_push=current.notifications_push if payload.notifications_push is None else payload.notifications_push,
        notifications_marketing=current.notifications_marketing if payload.notifications_marketing is None else payload.notifications_marketing,
        theme=current.theme if payload.theme is None else payload.theme,
    )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_preferences(user_id, notifications_email, notifications_push, notifications_marketing, theme, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
              notifications_email=excluded.notifications_email,
              notifications_push=excluded.notifications_push,
              notifications_marketing=excluded.notifications_marketing,
              theme=excluded.theme,
              updated_at=datetime('now')
            """,
            (
                user_id,
                int(updated.notifications_email),
                int(updated.notifications_push),
                int(updated.notifications_marketing),
                updated.theme,
            ),
        )
        conn.commit()

    return {"status": "ok", "preferences": updated}


@router.patch("/users/me/avatar", response_model=AvatarUpdateResponse)
def update_avatar(payload: AvatarUpdateRequest, authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    user = update_profile(user_id=user_id, display_name=None, bio=None, avatar_url=payload.avatar_url)
    return {"status": "ok", "avatar_url": user["avatar_url"]}


@router.get("/search", response_model=SearchResponse)
def global_search(q: str = ""):
    query = (q or "").strip().lower()
    if not query:
        return {"status": "ok", "query": "", "results": []}

    results: list[SearchResult] = []
    with get_connection() as conn:
        for row in conn.execute("SELECT agent_id, name, category FROM agents WHERE lower(name) LIKE ? LIMIT 10", (f"%{query}%",)):
            results.append(SearchResult(result_type="agent", result_id=row["agent_id"], title=row["name"], subtitle=row["category"]))

        for row in conn.execute("SELECT workflow_id, name, status FROM workflows WHERE lower(name) LIKE ? LIMIT 10", (f"%{query}%",)):
            results.append(SearchResult(result_type="workflow", result_id=row["workflow_id"], title=row["name"], subtitle=row["status"]))

        for row in conn.execute("SELECT deployment_id, name, environment FROM deployments WHERE lower(name) LIKE ? LIMIT 10", (f"%{query}%",)):
            results.append(SearchResult(result_type="deployment", result_id=row["deployment_id"], title=row["name"], subtitle=row["environment"]))

    return {"status": "ok", "query": q, "results": results[:20]}


@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT notification_id, user_id, title, message, is_read, created_at
            FROM notifications
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (user_id,),
        ).fetchall()

    notifications = [NotificationRecord(**{**_row_dict(r), "is_read": bool(r["is_read"])}) for r in rows]
    return {"status": "ok", "notifications": notifications}


@router.post("/notifications/{notification_id}/read", response_model=NotificationMarkReadResponse)
def mark_notification_read(notification_id: str, authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT notification_id FROM notifications WHERE notification_id=? AND user_id=?",
            (notification_id, user_id),
        ).fetchone()
        if not row:
            fail(404, "not_found", "Notification not found")

        conn.execute(
            "UPDATE notifications SET is_read=1 WHERE notification_id=? AND user_id=?",
            (notification_id, user_id),
        )
        conn.commit()

    return {"status": "ok", "notification_id": notification_id, "is_read": True}


@router.get("/token/balances", response_model=TokenBalancesResponse)
def token_balances(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        payments = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total_paid FROM payments WHERE user_id=? AND status='paid'",
            (user_id,),
        ).fetchone()
        payout = conn.execute(
            "SELECT COALESCE(SUM(requested_amount), 0) AS total_requested FROM creator_payout_requests WHERE creator_user_id=?",
            (user_id,),
        ).fetchone()

    asnd_balance = max(0.0, float(payments["total_paid"]) - float(payout["total_requested"]))
    return {
        "status": "ok",
        "user_id": user_id,
        "asnd_balance": f"{asnd_balance:.4f}",
        "sol_balance": "0.0000",
        "staking_balance": "0.0000",
        "pending_rewards": "0.0000",
    }


@router.get("/token/history", response_model=TokenHistoryResponse)
def token_history(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT tx_signature, token, amount, status, created_at
            FROM payments
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (user_id,),
        ).fetchall()

    history = [
        TokenHistoryRecord(
            tx_signature=row["tx_signature"],
            token=row["token"],
            amount=f"{float(row['amount']):.4f}",
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
    return {"status": "ok", "user_id": user_id, "history": history}


@router.get("/marketplace/browse", response_model=MarketplaceBrowseResponse)
def marketplace_browse(category: str | None = None):
    query = """
        SELECT listing_id, creator_user_id, title, description, category, pricing_model, price_amount, price_token, published_at
        FROM marketplace_listings
        WHERE status='published'
    """
    params: tuple = ()
    if category:
        query += " AND category=?"
        params = (category,)
    query += " ORDER BY published_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    listings = [MarketplaceBrowseRecord(**_row_dict(r)) for r in rows]
    return {"status": "ok", "listings": listings}


@router.get("/marketplace/entitlements", response_model=EntitlementsResponse)
def get_entitlements(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT listing_id, user_id, installed_at
            FROM marketplace_entitlements
            WHERE user_id=?
            ORDER BY installed_at DESC
            """,
            (user_id,),
        ).fetchall()

    return {"status": "ok", "entitlements": [EntitlementRecord(**_row_dict(r)) for r in rows]}


@router.post("/marketplace/listings/{listing_id}/install", response_model=InstallListingResponse)
def install_listing(listing_id: str, payload: InstallListingRequest):
    with get_connection() as conn:
        listing = conn.execute(
            "SELECT listing_id FROM marketplace_listings WHERE listing_id=? AND status='published'",
            (listing_id,),
        ).fetchone()
        if not listing:
            fail(404, "not_found", "Listing not found or not published")

        conn.execute(
            """
            INSERT INTO marketplace_entitlements(listing_id, user_id, installed_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(listing_id, user_id) DO UPDATE SET installed_at=datetime('now')
            """,
            (listing_id, payload.user_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT listing_id, user_id, installed_at FROM marketplace_entitlements WHERE listing_id=? AND user_id=?",
            (listing_id, payload.user_id),
        ).fetchone()

    return {"status": "ok", "entitlement": EntitlementRecord(**_row_dict(row))}


@router.get("/marketplace/creators/{creator_user_id}/payouts/totals", response_model=CreatorPayoutTotalsResponse)
def creator_payout_totals(creator_user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(creator_user_id, authorization)
    with get_connection() as conn:
        pending = conn.execute(
            "SELECT COALESCE(SUM(requested_amount), 0) AS amount FROM creator_payout_requests WHERE creator_user_id=? AND status='pending'",
            (creator_user_id,),
        ).fetchone()
        paid = conn.execute(
            "SELECT COALESCE(SUM(requested_amount), 0) AS amount FROM creator_payout_requests WHERE creator_user_id=? AND status='paid'",
            (creator_user_id,),
        ).fetchone()

    return {
        "status": "ok",
        "creator_user_id": creator_user_id,
        "pending_amount": f"{float(pending['amount']):.4f}",
        "paid_amount": f"{float(paid['amount']):.4f}",
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit(actor_user_id: str, event_type: str, target_type: str, target_id: str, metadata: dict | None = None) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_events(event_id, actor_user_id, event_type, target_type, target_id, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                f"audit_{secrets.token_hex(6)}",
                actor_user_id,
                event_type,
                target_type,
                target_id,
                json.dumps(metadata or {}, separators=(",", ":")),
            ),
        )
        conn.commit()


def _require_agent_owner(conn, agent_id: str, actor_user_id: str) -> None:
    row = conn.execute(
        """
        SELECT a.owner_user_id,
               (
                   SELECT ae.actor_user_id
                   FROM audit_events ae
                   WHERE ae.target_type='agent'
                     AND ae.target_id=a.agent_id
                     AND ae.event_type='agent.create'
                   ORDER BY ae.created_at ASC, ae.id ASC
                   LIMIT 1
               ) AS audit_owner_user_id
        FROM agents a
        WHERE a.agent_id=?
        """,
        (agent_id,),
    ).fetchone()
    if not row:
        fail(404, "not_found", "Agent not found")

    owner_user_id = row["owner_user_id"] or row["audit_owner_user_id"]
    if owner_user_id != actor_user_id:
        fail(403, "forbidden", "Agent does not belong to authenticated user")


class AgentCrudInput(BaseModel):
    name: str
    category: str
    description: str
    status: str = "draft"
    instructions: str | None = None
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    autonomy_level: str = "manual"
    visibility: str = "private"
    deployment_environment: str = "draft"
    monetization: str = "disabled"
    workflow_id: str | None = None
    deployment_id: str | None = None
    marketplace_listing_id: str | None = None


class AgentConfigPatchInput(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    status: str | None = None
    instructions: str | None = None
    tools: list[str] | None = None
    skills: list[str] | None = None
    autonomy_level: str | None = None
    visibility: str | None = None
    deployment_environment: str | None = None
    monetization: str | None = None
    workflow_id: str | None = None
    deployment_id: str | None = None
    marketplace_listing_id: str | None = None


class AgentRunInput(BaseModel):
    title: str
    type: str = "general"
    priority: str = "medium"


class AgentDeployInput(BaseModel):
    environment: str = "production"
    region: str = "us-east"
    status: str = "running"


def _normalized_string_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    result = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _validate_agent_capabilities(tools: list[str], skills: list[str]) -> None:
    tool_ids = _registry_ids(AGENT_TOOL_REGISTRY, "tool_id")
    skill_ids = _registry_ids(AGENT_SKILL_REGISTRY, "skill_id")
    unknown_tools = [tool for tool in tools if tool not in tool_ids]
    unknown_skills = [skill for skill in skills if skill not in skill_ids]
    if unknown_tools or unknown_skills:
        fail(400, "invalid_agent_capability", "Agent config references unavailable tools or skills")


def _get_owned_agent_row(conn, agent_id: str, actor: str):
    _require_agent_owner(conn, agent_id, actor)
    return conn.execute(f"SELECT {AGENT_SELECT_COLUMNS} FROM agents WHERE agent_id=?", (agent_id,)).fetchone()


@router.post("/agents")
def create_agent(payload: AgentCrudInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    agent_id = f"agt_{secrets.token_hex(6)}"
    tools = _normalized_string_list(payload.tools)
    skills = _normalized_string_list(payload.skills)
    _validate_agent_capabilities(tools, skills)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agents(
                agent_id, owner_user_id, name, category, description, status,
                tasks_completed, success_rate, instructions, tools_json, skills_json,
                autonomy_level, visibility, deployment_environment, monetization,
                workflow_id, deployment_id, marketplace_listing_id, created_at, updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            (
                agent_id,
                actor,
                payload.name,
                payload.category,
                payload.description,
                payload.status,
                payload.instructions,
                json.dumps(tools),
                json.dumps(skills),
                payload.autonomy_level,
                payload.visibility,
                payload.deployment_environment,
                payload.monetization,
                payload.workflow_id,
                payload.deployment_id,
                payload.marketplace_listing_id,
            ),
        )
        conn.commit()
        row = conn.execute(f"SELECT {AGENT_SELECT_COLUMNS} FROM agents WHERE agent_id=?", (agent_id,)).fetchone()

    _audit(
        actor,
        "agent.create",
        "agent",
        agent_id,
        {
            "category": payload.category,
            "tools_count": len(tools),
            "skills_count": len(skills),
            "autonomy_level": payload.autonomy_level,
        },
    )
    return {"status": "ok", "agent_id": agent_id, "agent": _agent_payload(row)}


class AgentTemplateCreateInput(BaseModel):
    template_id: str
    name: str
    category: str | None = None
    description: str
    autonomy_level: str | None = None
    visibility: str | None = None
    deployment_environment: str | None = None


AGENT_TOOL_REGISTRY = [
    {
        "tool_id": "web_search",
        "name": "Web Search",
        "category": "research",
        "description": "Search public web sources for current information.",
        "risk_level": "low",
        "requires_approval": False,
        "enabled": True,
    },
    {
        "tool_id": "summarizer",
        "name": "Summarizer",
        "category": "analysis",
        "description": "Condense source material into structured summaries and reports.",
        "risk_level": "low",
        "requires_approval": False,
        "enabled": True,
    },
    {
        "tool_id": "workflow_runner",
        "name": "Workflow Runner",
        "category": "automation",
        "description": "Run approved AgentAscend workflow graphs for the agent owner.",
        "risk_level": "medium",
        "requires_approval": True,
        "enabled": True,
    },
    {
        "tool_id": "content_drafter",
        "name": "Content Drafter",
        "category": "creation",
        "description": "Draft user-reviewable content from instructions, research, and templates.",
        "risk_level": "low",
        "requires_approval": False,
        "enabled": True,
    },
]

AGENT_SKILL_REGISTRY = [
    {
        "skill_id": "research",
        "name": "Research",
        "category": "analysis",
        "description": "Collect, compare, and summarize public information with source-aware notes.",
        "output_schema": "structured_findings",
    },
    {
        "skill_id": "reporting",
        "name": "Reporting",
        "category": "writing",
        "description": "Turn findings into concise operator-ready reports.",
        "output_schema": "report",
    },
    {
        "skill_id": "workflow_orchestration",
        "name": "Workflow Orchestration",
        "category": "automation",
        "description": "Plan and coordinate safe workflow steps with explicit approval gates.",
        "output_schema": "workflow_run_plan",
    },
    {
        "skill_id": "content_generation",
        "name": "Content Generation",
        "category": "writing",
        "description": "Draft reviewable content from a user mission and gathered context.",
        "output_schema": "draft_content",
    },
    {
        "skill_id": "seo_planning",
        "name": "SEO Planning",
        "category": "marketing",
        "description": "Plan keywords, outlines, and metadata without fake traffic or ranking claims.",
        "output_schema": "seo_brief",
    },
]

AGENT_TEMPLATE_REGISTRY = [
    {
        "template_id": "research_agent",
        "name": "Research Agent",
        "category": "Research",
        "description": "Research public information and prepare a structured report.",
        "instructions": "Research public sources, summarize findings, note uncertainty, and avoid unsupported claims.",
        "tools": ["web_search", "summarizer"],
        "skills": ["research", "reporting"],
        "autonomy_level": "manual",
        "visibility": "private",
        "deployment_environment": "draft",
        "approval_required": True,
    },
    {
        "template_id": "workflow_automation_agent",
        "name": "Workflow Automation Agent",
        "category": "Automation",
        "description": "Coordinate approved workflow steps and produce execution summaries.",
        "instructions": "Run only owner-approved workflow steps, stop at approval gates, and record every output.",
        "tools": ["workflow_runner", "summarizer"],
        "skills": ["workflow_orchestration", "reporting"],
        "autonomy_level": "manual",
        "visibility": "private",
        "deployment_environment": "draft",
        "approval_required": True,
    },
    {
        "template_id": "seo_content_agent",
        "name": "SEO Content Agent",
        "category": "Marketing",
        "description": "Research keywords and draft reviewable SEO content.",
        "instructions": "Build SEO briefs and draft content from public research. Do not invent metrics, rankings, traffic, or authority claims.",
        "tools": ["web_search", "summarizer"],
        "skills": ["research", "content_generation", "seo_planning"],
        "autonomy_level": "manual",
        "visibility": "private",
        "deployment_environment": "draft",
        "approval_required": True,
    },
]


def _agent_template(template_id: str) -> dict | None:
    for template in AGENT_TEMPLATE_REGISTRY:
        if template["template_id"] == template_id:
            return template
    return None


def _registry_ids(items: list[dict], key: str) -> set[str]:
    return {str(item[key]) for item in items}


def _validate_template_capabilities(template: dict) -> None:
    tool_ids = _registry_ids(AGENT_TOOL_REGISTRY, "tool_id")
    skill_ids = _registry_ids(AGENT_SKILL_REGISTRY, "skill_id")
    missing_tools = [tool for tool in template["tools"] if tool not in tool_ids]
    missing_skills = [skill for skill in template["skills"] if skill not in skill_ids]
    if missing_tools or missing_skills:
        fail(500, "template_config_error", "Agent template references unavailable capabilities")


@router.get("/agent-capabilities")
def list_agent_capabilities():
    return {
        "status": "ok",
        "tools": AGENT_TOOL_REGISTRY,
        "skills": AGENT_SKILL_REGISTRY,
        "templates": AGENT_TEMPLATE_REGISTRY,
    }


@router.post("/agents/from-template")
def create_agent_from_template(payload: AgentTemplateCreateInput, authorization: str | None = Header(default=None)):
    template = _agent_template(payload.template_id)
    if not template:
        fail(404, "not_found", "Agent template not found")
    _validate_template_capabilities(template)
    agent_payload = AgentCrudInput(
        name=payload.name,
        category=payload.category or template["category"],
        description=payload.description,
        status="active",
        instructions=template["instructions"],
        tools=list(template["tools"]),
        skills=list(template["skills"]),
        autonomy_level=payload.autonomy_level or template["autonomy_level"],
        visibility=payload.visibility or template["visibility"],
        deployment_environment=payload.deployment_environment or template["deployment_environment"],
        monetization="private",
    )
    result = create_agent(agent_payload, authorization=authorization)
    result["template_id"] = payload.template_id
    result["capabilities"] = {"tools": list(template["tools"]), "skills": list(template["skills"])}
    return result


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        row = _get_owned_agent_row(conn, agent_id, actor)
    if not row:
        fail(404, "not_found", "Agent not found")
    return {"status": "ok", "agent": _agent_payload(row)}


@router.patch("/agents/{agent_id}/config")
def patch_agent_config(agent_id: str, payload: AgentConfigPatchInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    updates = payload.model_dump(exclude_unset=True)
    if "tools" in updates or "skills" in updates:
        with get_connection() as conn:
            current = _get_owned_agent_row(conn, agent_id, actor)
        current_payload = _agent_payload(current)
        tools = _normalized_string_list(updates.get("tools", current_payload["tools"]))
        skills = _normalized_string_list(updates.get("skills", current_payload["skills"]))
        _validate_agent_capabilities(tools, skills)
    allowed_columns = {
        "name": "name",
        "category": "category",
        "description": "description",
        "status": "status",
        "instructions": "instructions",
        "tools": "tools_json",
        "skills": "skills_json",
        "autonomy_level": "autonomy_level",
        "visibility": "visibility",
        "deployment_environment": "deployment_environment",
        "monetization": "monetization",
        "workflow_id": "workflow_id",
        "deployment_id": "deployment_id",
        "marketplace_listing_id": "marketplace_listing_id",
    }
    assignments: list[str] = []
    values: list[object] = []
    for field, value in updates.items():
        column = allowed_columns[field]
        assignments.append(f"{column}=?")
        if field in {"tools", "skills"}:
            values.append(json.dumps(_normalized_string_list(value)))
        else:
            values.append(value)
    if not assignments:
        return get_agent(agent_id, authorization=authorization)

    with get_connection() as conn:
        _require_agent_owner(conn, agent_id, actor)
        values.append(agent_id)
        conn.execute(
            f"UPDATE agents SET {', '.join(assignments)}, updated_at=datetime('now') WHERE agent_id=?",
            tuple(values),
        )
        conn.commit()
    _audit(actor, "agent.config.update", "agent", agent_id, {"fields": sorted(updates.keys())})
    return get_agent(agent_id, authorization=authorization)


@router.patch("/agents/{agent_id}")
def patch_agent(agent_id: str, payload: AgentCrudInput, authorization: str | None = Header(default=None)):
    return patch_agent_config(agent_id, AgentConfigPatchInput(**payload.model_dump()), authorization=authorization)


@router.post("/agents/{agent_id}/run")
def run_agent(agent_id: str, payload: AgentRunInput, background_tasks: BackgroundTasks, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        agent = _get_owned_agent_row(conn, agent_id, actor)
    if not agent:
        fail(404, "not_found", "Agent not found")

    task_result = create_task(
        TaskCreateInput(title=payload.title, type=payload.type, agent_id=agent_id, priority=payload.priority, assigned_to=agent_id),
        background_tasks,
        authorization=authorization,
    )
    _audit(actor, "agent.run", "agent", agent_id, {"task_id": task_result["task_id"], "priority": payload.priority})
    return {"status": "ok", "agent_id": agent_id, "task_id": task_result["task_id"]}


@router.post("/agents/{agent_id}/deploy")
def deploy_agent(agent_id: str, payload: AgentDeployInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        agent = _get_owned_agent_row(conn, agent_id, actor)
        if not agent:
            fail(404, "not_found", "Agent not found")
        deployment_id = f"dep_{secrets.token_hex(5)}"
        conn.execute(
            """
            INSERT INTO deployments(deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent, requests_per_day, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, 1, 0, 0, 0, datetime('now'), datetime('now'))
            """,
            (deployment_id, f"{agent['name']} deployment", payload.environment, payload.status, payload.region),
        )
        conn.execute(
            """
            INSERT INTO deployment_metrics(deployment_id, cpu_percent, memory_percent, p95_latency_ms, error_rate, recorded_at)
            VALUES (?, 0, 0, 0, 0, datetime('now'))
            """,
            (deployment_id,),
        )
        conn.execute(
            """
            UPDATE agents
            SET deployment_id=?, deployment_environment=?, status='active', updated_at=datetime('now')
            WHERE agent_id=?
            """,
            (deployment_id, payload.environment, agent_id),
        )
        conn.commit()
    _audit(actor, "agent.deploy", "agent", agent_id, {"deployment_id": deployment_id, "environment": payload.environment})
    return {"status": "ok", "agent_id": agent_id, "deployment_id": deployment_id}


@router.delete("/agents/{agent_id}")
def delete_agent(agent_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_agent_owner(conn, agent_id, actor)
        deleted = conn.execute("DELETE FROM agents WHERE agent_id=?", (agent_id,)).rowcount
        conn.commit()
    if deleted == 0:
        fail(404, "not_found", "Agent not found")
    _audit(actor, "agent.delete", "agent", agent_id)
    return {"status": "ok", "deleted": True}


class DeploymentCrudInput(BaseModel):
    name: str
    environment: str
    region: str
    status: str = "running"


@router.post("/deployments")
def create_deployment(payload: DeploymentCrudInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    deployment_id = f"dep_{secrets.token_hex(5)}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO deployments(deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent, requests_per_day, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, 0, 0, 0, 0, datetime('now'), datetime('now'))
            """,
            (deployment_id, payload.name, payload.environment, payload.status, payload.region),
        )
        conn.execute(
            """
            INSERT INTO deployment_metrics(deployment_id, cpu_percent, memory_percent, p95_latency_ms, error_rate, recorded_at)
            VALUES (?, 0, 0, 0, 0, datetime('now'))
            """,
            (deployment_id,),
        )
        conn.commit()
    _audit(actor, "deployment.create", "deployment", deployment_id, {"environment": payload.environment})
    return {"status": "ok", "deployment_id": deployment_id}


def _deployment_owner_user_id(conn, deployment_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT COALESCE(
            (
                SELECT a.owner_user_id
                FROM agents a
                WHERE a.deployment_id=? AND a.owner_user_id IS NOT NULL
                ORDER BY a.updated_at DESC, a.id DESC
                LIMIT 1
            ),
            (
                SELECT ae.actor_user_id
                FROM audit_events ae
                WHERE ae.target_type='deployment'
                  AND ae.target_id=?
                ORDER BY ae.created_at ASC, ae.id ASC
                LIMIT 1
            )
        ) AS owner_user_id
        """,
        (deployment_id, deployment_id),
    ).fetchone()
    if row and row["owner_user_id"]:
        return row["owner_user_id"]

    rows = conn.execute(
        """
        SELECT actor_user_id, metadata_json
        FROM audit_events
        WHERE target_type='agent' AND event_type='agent.deploy'
        ORDER BY created_at ASC, id ASC
        """
    ).fetchall()
    for audit_row in rows:
        try:
            metadata = json.loads(audit_row["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        if metadata.get("deployment_id") == deployment_id:
            return audit_row["actor_user_id"]
    return None


def _require_deployment_owner(conn, deployment_id: str, actor_user_id: str) -> None:
    exists = conn.execute("SELECT 1 FROM deployments WHERE deployment_id=?", (deployment_id,)).fetchone()
    if not exists:
        fail(404, "not_found", "Deployment not found")
    owner_user_id = _deployment_owner_user_id(conn, deployment_id)
    if owner_user_id != actor_user_id:
        fail(403, "forbidden", "Deployment does not belong to authenticated user")


def _deployment_event_message(event_type: str, deployment_id: str) -> str:
    if event_type == "agent.deploy":
        return f"Deployment {deployment_id} created from agent deploy"
    if event_type == "deployment.create":
        return f"Deployment {deployment_id} created"
    if event_type.startswith("deployment."):
        action = event_type.split(".", 1)[1].replace("_", " ")
        return f"Deployment {deployment_id} {action}"
    return f"Deployment {deployment_id} event recorded"


def _deployment_event_status(event_type: str, deployment_status: str) -> str:
    if event_type == "agent.deploy":
        return deployment_status
    if event_type == "deployment.create":
        return "created"
    if event_type.startswith("deployment."):
        return event_type.split(".", 1)[1]
    return deployment_status


@router.get("/deployments/{deployment_id}/events", response_model=DeploymentEventListResponse)
def deployment_events(deployment_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    events: list[DeploymentEventRecord] = []
    with get_connection() as conn:
        _require_deployment_owner(conn, deployment_id, actor)
        deployment = conn.execute("SELECT status FROM deployments WHERE deployment_id=?", (deployment_id,)).fetchone()
        deployment_status = deployment["status"] if deployment else "unknown"
        rows = conn.execute(
            """
            SELECT event_id, actor_user_id, event_type, target_type, target_id, metadata_json, created_at
            FROM audit_events
            WHERE actor_user_id=?
              AND (
                (target_type='deployment' AND target_id=?)
                OR (target_type='agent' AND event_type='agent.deploy')
              )
            ORDER BY created_at DESC, id DESC
            LIMIT 100
            """,
            (actor, deployment_id),
        ).fetchall()

    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        if row["target_type"] == "agent" and metadata.get("deployment_id") != deployment_id:
            continue
        event_type = str(row["event_type"])
        events.append(
            DeploymentEventRecord(
                event_id=row["event_id"],
                deployment_id=deployment_id,
                timestamp=row["created_at"],
                level="info",
                status=_deployment_event_status(event_type, deployment_status),
                message=_deployment_event_message(event_type, deployment_id),
                source=event_type,
            )
        )

    return {"status": "ok", "deployment_id": deployment_id, "events": events}


@router.get("/deployments/{deployment_id}")
def get_deployment(deployment_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_deployment_owner(conn, deployment_id, actor)
        row = conn.execute(
            """
            SELECT deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent, requests_per_day, created_at, updated_at
            FROM deployments WHERE deployment_id=?
            """,
            (deployment_id,),
        ).fetchone()
    if not row:
        fail(404, "not_found", "Deployment not found")
    return {"status": "ok", "deployment": _row_dict(row)}


@router.get("/deployments/{deployment_id}/metrics")
def deployment_metrics(deployment_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_deployment_owner(conn, deployment_id, actor)
        rows = conn.execute(
            """
            SELECT cpu_percent, memory_percent, p95_latency_ms, error_rate, recorded_at
            FROM deployment_metrics
            WHERE deployment_id=?
            ORDER BY recorded_at DESC
            LIMIT 100
            """,
            (deployment_id,),
        ).fetchall()
    return {"status": "ok", "deployment_id": deployment_id, "metrics": [_row_dict(r) for r in rows]}


class WorkflowCrudInput(BaseModel):
    name: str
    status: str = "draft"


class WorkflowNodeInput(BaseModel):
    node_id: str
    node_type: str
    config: dict
    position: dict


class WorkflowGraphInput(BaseModel):
    nodes: list[dict]


class WorkflowRunInput(BaseModel):
    metadata: dict = Field(default_factory=dict)


@router.post("/workflows")
def create_workflow(payload: WorkflowCrudInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    workflow_id = f"wf_{secrets.token_hex(5)}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO workflows(workflow_id, owner_user_id, name, status, runs_total, success_rate, updated_at)
            VALUES(?, ?, ?, ?, 0, 0, datetime('now'))
            """,
            (workflow_id, actor, payload.name, payload.status),
        )
        conn.commit()
    _audit(actor, "workflow.create", "workflow", workflow_id)
    return {"status": "ok", "workflow_id": workflow_id}


@router.put("/workflows/{workflow_id}/graph")
def put_workflow_graph(workflow_id: str, payload: WorkflowGraphInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_owned_workflow(conn, workflow_id, actor)
        conn.execute("DELETE FROM workflow_nodes WHERE workflow_id=?", (workflow_id,))
        for node in payload.nodes:
            conn.execute(
                """
                INSERT INTO workflow_nodes(workflow_id, node_id, node_type, config_json, position_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    str(node.get("node_id", "")),
                    str(node.get("node_type", "")),
                    json.dumps(node.get("config", {})),
                    json.dumps(node.get("position", {})),
                ),
            )
        conn.execute("UPDATE workflows SET updated_at=datetime('now') WHERE workflow_id=?", (workflow_id,))
        conn.commit()
    _audit(actor, "workflow.graph.update", "workflow", workflow_id, {"nodes": len(payload.nodes)})
    return {"status": "ok", "workflow_id": workflow_id, "nodes": len(payload.nodes)}


@router.get("/workflows/{workflow_id}/graph")
def get_workflow_graph(workflow_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_owned_workflow(conn, workflow_id, actor)
        rows = conn.execute(
            "SELECT node_id, node_type, config_json, position_json FROM workflow_nodes WHERE workflow_id=? ORDER BY node_id",
            (workflow_id,),
        ).fetchall()
    nodes = [
        {
            "node_id": r["node_id"],
            "node_type": r["node_type"],
            "config": json.loads(r["config_json"]),
            "position": json.loads(r["position_json"]),
        }
        for r in rows
    ]
    return {"status": "ok", "workflow_id": workflow_id, "nodes": nodes}


@router.get("/workflows/{workflow_id}/runs")
def list_workflow_runs(workflow_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_owned_workflow(conn, workflow_id, actor)
        rows = conn.execute(
            """
            SELECT run_id, workflow_id, status, duration_ms, started_at
            FROM workflow_runs WHERE workflow_id=?
            ORDER BY started_at DESC
            LIMIT 100
            """,
            (workflow_id,),
        ).fetchall()
    return {"status": "ok", "workflow_id": workflow_id, "runs": [_row_dict(r) for r in rows]}


@router.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str, payload: WorkflowRunInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    run_id = f"run_{secrets.token_hex(6)}"
    with get_connection() as conn:
        _require_owned_workflow(conn, workflow_id, actor)
        node_count = conn.execute("SELECT COUNT(*) AS count FROM workflow_nodes WHERE workflow_id=?", (workflow_id,)).fetchone()["count"]
        conn.execute(
            """
            INSERT INTO workflow_runs(run_id, workflow_id, status, duration_ms, started_at)
            VALUES (?, ?, 'success', 0, datetime('now'))
            """,
            (run_id, workflow_id),
        )
        conn.execute(
            """
            UPDATE workflows
            SET runs_total=runs_total + 1, success_rate=100, status='active', updated_at=datetime('now')
            WHERE workflow_id=?
            """,
            (workflow_id,),
        )
        conn.commit()
    _audit(actor, "workflow.run", "workflow", workflow_id, {"run_id": run_id, "nodes": node_count, "metadata": payload.metadata})
    return {"status": "ok", "workflow_id": workflow_id, "run_id": run_id, "run_status": "success", "nodes": node_count}


class TaskCreateInput(BaseModel):
    title: str
    type: str = "general"
    agent_id: str | None = None
    priority: str = "medium"
    assigned_to: str | None = None


def _write_task_creation_ledger(conn, task_id: str, actor: str, payload: TaskCreateInput, created_at: str | None) -> None:
    if not execution_ledger.is_execution_ledger_enabled():
        return

    execution = execution_ledger.create_execution(
        user_id=actor,
        source_type="task",
        source_id=task_id,
        agent_id=payload.agent_id or payload.assigned_to,
        status="queued",
        metadata={
            "task_id": task_id,
            "task_title": payload.title,
            "task_type": payload.type,
        },
        db=conn,
    )
    execution_ledger.append_execution_event(
        execution_id=execution["execution_id"],
        event_type="task_created",
        payload={
            "task_id": task_id,
            "status": "queued",
            "created_at": created_at,
        },
        db=conn,
    )


@router.post("/tasks")
def create_task(payload: TaskCreateInput, background_tasks: BackgroundTasks, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    task_id = f"tsk_{secrets.token_hex(5)}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tasks(task_id, user_id, agent_id, type, title, status, priority, assigned_to, error_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'queued', ?, ?, NULL, datetime('now'), datetime('now'))
            """,
            (task_id, actor, payload.agent_id or payload.assigned_to, payload.type, payload.title, payload.priority, payload.assigned_to),
        )
        conn.execute(
            "INSERT INTO task_logs(task_id, level, message, created_at) VALUES (?, 'info', ?, datetime('now'))",
            (task_id, f"Task created by {actor}"),
        )
        task_row = conn.execute("SELECT created_at FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        _write_task_creation_ledger(conn, task_id, actor, payload, task_row["created_at"] if task_row else None)
        conn.commit()
    _audit(actor, "task.create", "task", task_id, {"priority": payload.priority})
    if _task_worker_background_enabled():
        background_tasks.add_task(_trigger_task_queue_worker)
    return {"status": "ok", "task_id": task_id}


@router.get("/tasks/{task_id}/execution", response_model=ExecutionDetailResponse)
def get_task_execution(task_id: str, authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    actor = auth["user"]
    with get_connection() as conn:
        task = conn.execute("SELECT task_id, user_id FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not task:
            fail(404, "not_found", "Task not found")
        if task["user_id"] != actor["user_id"] and actor.get("role") != "admin":
            fail(403, "forbidden", "Authenticated user cannot access another user's task execution")
        execution = execution_ledger.get_execution_by_source("task", task_id, db=conn)
    if not execution:
        fail(404, "not_found", "Execution not found")
    return _execution_detail_payload(execution)


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT task_id, user_id, agent_id, type, title, status, priority, assigned_to, error_message, created_at, updated_at FROM tasks WHERE task_id=?",
            (task_id,),
        ).fetchone()
    if not row:
        fail(404, "not_found", "Task not found")
    return {"status": "ok", "task": _row_dict(row)}


def _set_task_status(task_id: str, new_status: str, actor: str, message: str):
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not exists:
            fail(404, "not_found", "Task not found")
        conn.execute("UPDATE tasks SET status=?, error_message=NULL, updated_at=datetime('now') WHERE task_id=?", (new_status, task_id))
        conn.execute(
            "INSERT INTO task_logs(task_id, level, message, created_at) VALUES (?, 'info', ?, datetime('now'))",
            (task_id, message),
        )
        conn.commit()
    _audit(actor, f"task.{new_status}", "task", task_id)


@router.post("/tasks/{task_id}/retry")
def retry_task(task_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    _set_task_status(task_id, "queued", actor, f"Task retried by {actor}")
    return {"status": "ok", "task_id": task_id, "new_status": "queued"}


@router.post("/tasks/{task_id}/cancel")
def cancel_task(task_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    _set_task_status(task_id, "failed", actor, f"Task cancelled by {actor}")
    return {"status": "ok", "task_id": task_id, "new_status": "failed"}


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str, authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    actor = auth["user"]

    with get_connection() as conn:
        task = conn.execute("SELECT task_id, user_id FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not task:
            fail(404, "not_found", "Task not found")
        if task["user_id"] != actor["user_id"] and actor.get("role") != "admin":
            fail(403, "forbidden", "Authenticated user cannot delete another user's task")

        conn.execute("DELETE FROM outputs WHERE task_id=?", (task_id,))
        conn.execute("DELETE FROM task_logs WHERE task_id=?", (task_id,))
        conn.execute("DELETE FROM tasks WHERE task_id=?", (task_id,))
        conn.commit()

    _audit(actor["user_id"], "task.delete", "task", task_id)
    return {"status": "ok", "deleted": True}


@router.get("/tasks/{task_id}/logs")
def get_task_logs(task_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT level, message, created_at FROM task_logs WHERE task_id=? ORDER BY created_at DESC LIMIT 200",
            (task_id,),
        ).fetchall()
    return {"status": "ok", "task_id": task_id, "logs": [_row_dict(r) for r in rows]}


@router.get("/outputs/{output_id}")
def get_output(output_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT output_id, task_id, user_id, title, output_type, content, text, file_url, size_bytes, download_url, created_at FROM outputs WHERE output_id=?",
            (output_id,),
        ).fetchone()
    if not row:
        fail(404, "not_found", "Output not found")
    return {"status": "ok", "output": _row_dict(row)}


@router.get("/outputs/{output_id}/download-url")
def output_download_url(output_id: str):
    data = get_output(output_id)
    return {"status": "ok", "output_id": output_id, "download_url": data["output"]["download_url"]}


@router.get("/community/stats")
def community_stats():
    with get_connection() as conn:
        totals = conn.execute(
            """
            SELECT COUNT(*) AS posts, COALESCE(SUM(likes),0) AS likes, COUNT(DISTINCT author_user_id) AS creators
            FROM community_posts
            """
        ).fetchone()
    return {"status": "ok", "posts": totals["posts"], "likes": totals["likes"], "active_creators": totals["creators"]}


class CommunityCreateInput(BaseModel):
    title: str
    body: str


class CommunityPatchInput(BaseModel):
    title: str | None = None
    body: str | None = None


def _community_post_payload(row) -> dict:
    if not row:
        fail(404, "not_found", "Community post not found")
    return {
        "post_id": row["post_id"],
        "author_user_id": row["author_user_id"],
        "title": row["title"],
        "body": row["body"],
        "likes": row["likes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get_community_post_row(conn, post_id: str):
    return conn.execute(
        """
        SELECT post_id, author_user_id, title, body, likes, created_at, updated_at
        FROM community_posts
        WHERE post_id=?
        """,
        (post_id,),
    ).fetchone()


@router.get("/community/posts/{post_id}")
def get_community_post(post_id: str):
    with get_connection() as conn:
        row = _get_community_post_row(conn, post_id)
    return {"status": "ok", "post": _community_post_payload(row)}


@router.patch("/community/posts/{post_id}")
def patch_community_post(
    post_id: str,
    payload: CommunityPatchInput,
    authorization: str | None = Header(default=None),
):
    auth = resolve_session(authorization)
    actor = auth["user"]["user_id"]
    role = auth["user"].get("role")

    with get_connection() as conn:
        row = _get_community_post_row(conn, post_id)
        if not row:
            fail(404, "not_found", "Community post not found")
        if row["author_user_id"] != actor and role != "admin":
            fail(403, "forbidden", "Authenticated user cannot edit this community post")

        title = payload.title if payload.title is not None else row["title"]
        body = payload.body if payload.body is not None else row["body"]
        conn.execute(
            """
            UPDATE community_posts
            SET title=?, body=?, updated_at=datetime('now')
            WHERE post_id=?
            """,
            (title, body, post_id),
        )
        updated = _get_community_post_row(conn, post_id)
        conn.commit()

    _audit(actor, "community.post.edit", "post", post_id)
    return {"status": "ok", "post": _community_post_payload(updated)}


@router.delete("/community/posts/{post_id}")
def delete_community_post(post_id: str, authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    actor = auth["user"]["user_id"]
    role = auth["user"].get("role")

    with get_connection() as conn:
        row = _get_community_post_row(conn, post_id)
        if not row:
            fail(404, "not_found", "Community post not found")
        if row["author_user_id"] != actor and role != "admin":
            fail(403, "forbidden", "Authenticated user cannot delete this community post")
        conn.execute("DELETE FROM community_posts WHERE post_id=?", (post_id,))
        conn.commit()

    _audit(actor, "community.post.delete", "post", post_id)
    return {"status": "ok", "deleted": True}


@router.post("/community/posts")
def create_community_post(payload: CommunityCreateInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    post_id = f"post_{secrets.token_hex(5)}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO community_posts(post_id, author_user_id, title, body, likes, created_at, updated_at)
            VALUES(?, ?, ?, ?, 0, datetime('now'), datetime('now'))
            """,
            (post_id, actor, payload.title, payload.body),
        )
        conn.commit()
    _audit(actor, "community.post.create", "post", post_id)
    return {"status": "ok", "post_id": post_id}


class ProfileExtrasPatch(BaseModel):
    timezone: str | None = None
    language: str | None = None
    website_url: str | None = None
    location: str | None = None


@router.get("/users/me/profile/extras")
def get_profile_extras(authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    with get_connection() as conn:
        row = conn.execute(
            "SELECT timezone, language, website_url, location, updated_at FROM user_profile_extras WHERE user_id=?",
            (user_id,),
        ).fetchone()
    return {"status": "ok", "user_id": user_id, "extras": _row_dict(row) if row else {}}


@router.patch("/users/me/profile/extras")
def patch_profile_extras(payload: ProfileExtrasPatch, authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    current = get_profile_extras(authorization)["extras"]
    merged = {
        "timezone": payload.timezone if payload.timezone is not None else current.get("timezone"),
        "language": payload.language if payload.language is not None else current.get("language"),
        "website_url": payload.website_url if payload.website_url is not None else current.get("website_url"),
        "location": payload.location if payload.location is not None else current.get("location"),
    }
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_profile_extras(user_id, timezone, language, website_url, location, updated_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
              timezone=excluded.timezone,
              language=excluded.language,
              website_url=excluded.website_url,
              location=excluded.location,
              updated_at=datetime('now')
            """,
            (user_id, merged["timezone"], merged["language"], merged["website_url"], merged["location"]),
        )
        conn.commit()
    return {"status": "ok", "user_id": user_id, "extras": merged}


class ApiKeyCreateInput(BaseModel):
    name: str


@router.get("/users/me/api-keys")
def list_api_keys(authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key_id, name, status, created_at, last_used_at FROM api_keys WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
    return {"status": "ok", "api_keys": [_row_dict(r) for r in rows]}


@router.post("/users/me/api-keys")
def create_api_key(payload: ApiKeyCreateInput, authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    key_id = f"key_{secrets.token_hex(6)}"
    raw_secret = f"asnd_{secrets.token_urlsafe(24)}"
    key_hash = hashlib.sha256(raw_secret.encode()).hexdigest()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO api_keys(key_id, user_id, name, key_hash, status, created_at, last_used_at)
            VALUES (?, ?, ?, ?, 'active', datetime('now'), NULL)
            """,
            (key_id, user_id, payload.name, key_hash),
        )
        conn.commit()
    _audit(user_id, "apikey.create", "api_key", key_id, {"name": payload.name})
    return {"status": "ok", "key_id": key_id, "secret": raw_secret}


@router.post("/users/me/api-keys/{key_id}/revoke")
def revoke_api_key(key_id: str, authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM api_keys WHERE key_id=? AND user_id=?", (key_id, user_id)).fetchone()
        if not row:
            fail(404, "not_found", "API key not found")
        conn.execute("UPDATE api_keys SET status='revoked' WHERE key_id=? AND user_id=?", (key_id, user_id))
        conn.commit()
    _audit(user_id, "apikey.revoke", "api_key", key_id)
    return {"status": "ok", "key_id": key_id, "revoked": True}


class IntegrationPatchInput(BaseModel):
    provider: str
    status: str
    config: dict = {}


@router.get("/users/me/integrations")
def list_integrations(authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT provider, status, config_json, updated_at FROM user_integrations WHERE user_id=? ORDER BY provider",
            (user_id,),
        ).fetchall()
    return {
        "status": "ok",
        "integrations": [
            {"provider": r["provider"], "status": r["status"], "config": json.loads(r["config_json"]), "updated_at": r["updated_at"]}
            for r in rows
        ],
    }


@router.patch("/users/me/integrations")
def patch_integration(payload: IntegrationPatchInput, authorization: str | None = Header(default=None)):
    user_id = _require_user_id(authorization)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_integrations(user_id, provider, status, config_json, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, provider) DO UPDATE SET
              status=excluded.status,
              config_json=excluded.config_json,
              updated_at=datetime('now')
            """,
            (user_id, payload.provider, payload.status, json.dumps(payload.config)),
        )
        conn.commit()
    _audit(user_id, "integration.patch", "integration", payload.provider, {"status": payload.status})
    return {"status": "ok", "provider": payload.provider, "integration_status": payload.status}


@router.get("/token/staking/positions")
def token_staking_positions(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT position_id, token, amount, apy, status, created_at, updated_at
            FROM staking_positions WHERE user_id=? ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return {"status": "ok", "user_id": user_id, "positions": [_row_dict(r) for r in rows]}


@router.get("/token/rewards/ledger")
def token_rewards_ledger(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT entry_id, token, amount, source, created_at
            FROM rewards_ledger WHERE user_id=? ORDER BY created_at DESC LIMIT 200
            """,
            (user_id,),
        ).fetchall()
    return {"status": "ok", "user_id": user_id, "entries": [_row_dict(r) for r in rows]}


@router.get("/token/transactions")
def token_transactions(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    history = token_history(user_id, authorization=authorization)["history"]
    rewards = token_rewards_ledger(user_id, authorization=authorization)["entries"]
    payouts = creator_payout_totals(user_id, authorization=authorization)
    return {
        "status": "ok",
        "user_id": user_id,
        "payments": history,
        "rewards": rewards,
        "payout_totals": {"pending_amount": payouts["pending_amount"], "paid_amount": payouts["paid_amount"]},
    }


@router.get("/marketplace/discover")
def marketplace_discover(query: str | None = None, category: str | None = None, sort: str = "latest"):
    sql = """
        SELECT listing_id, creator_user_id, title, description, category, pricing_model, price_amount, price_token, published_at
        FROM marketplace_listings
        WHERE status='published'
    """
    params: list[str] = []
    if category:
        sql += " AND category=?"
        params.append(category)
    if query:
        sql += " AND (lower(title) LIKE ? OR lower(description) LIKE ?)"
        q = f"%{query.lower()}%"
        params.extend([q, q])

    if sort == "price_low":
        sql += " ORDER BY price_amount ASC, published_at DESC"
    elif sort == "price_high":
        sql += " ORDER BY price_amount DESC, published_at DESC"
    elif sort == "popular":
        sql += " ORDER BY price_amount DESC, published_at DESC"
    else:
        sql += " ORDER BY published_at DESC"

    with get_connection() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return {"status": "ok", "query": query or "", "category": category, "sort": sort, "listings": [_row_dict(r) for r in rows]}


@router.get("/marketplace/licenses")
def marketplace_licenses(user_id: str, authorization: str | None = Header(default=None)):
    require_user_access(user_id, authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT listing_id, user_id, installed_at
            FROM marketplace_entitlements
            WHERE user_id=?
            ORDER BY installed_at DESC
            """,
            (user_id,),
        ).fetchall()
    return {"status": "ok", "user_id": user_id, "licenses": [_row_dict(r) for r in rows]}


@router.get("/marketplace/listings/{listing_id}/install-events")
def listing_install_events(listing_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_id, listing_id, user_id, event_type, created_at
            FROM marketplace_install_events
            WHERE listing_id=?
            ORDER BY created_at DESC
            LIMIT 200
            """,
            (listing_id,),
        ).fetchall()
    return {"status": "ok", "listing_id": listing_id, "events": [_row_dict(r) for r in rows]}


@router.post("/marketplace/listings/{listing_id}/install-track")
def install_track(listing_id: str, payload: InstallListingRequest, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    result = install_listing(listing_id, payload)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO marketplace_install_events(event_id, listing_id, user_id, event_type, created_at)
            VALUES (?, ?, ?, 'installed', datetime('now'))
            """,
            (f"inst_{secrets.token_hex(6)}", listing_id, payload.user_id),
        )
        conn.commit()
    _audit(actor, "marketplace.install", "listing", listing_id, {"user_id": payload.user_id})
    return result


@router.get("/ops/audit-events")
def audit_events(limit: int = 200):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_id, actor_user_id, event_type, target_type, target_id, metadata_json, created_at
            FROM audit_events
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (min(max(limit, 1), 1000),),
        ).fetchall()
    return {
        "status": "ok",
        "events": [
            {**_row_dict(r), "metadata": json.loads(r["metadata_json"])}
            for r in rows
        ],
    }


class OpsAlertInput(BaseModel):
    severity: str
    title: str
    message: str


@router.get("/ops/alerts")
def ops_alerts(status: str | None = None):
    sql = "SELECT alert_id, severity, title, message, status, created_at, updated_at FROM ops_alerts"
    params: tuple = ()
    if status:
        sql += " WHERE status=?"
        params = (status,)
    sql += " ORDER BY updated_at DESC"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return {"status": "ok", "alerts": [_row_dict(r) for r in rows]}


@router.post("/ops/alerts")
def create_ops_alert(payload: OpsAlertInput):
    alert_id = f"alert_{secrets.token_hex(5)}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ops_alerts(alert_id, severity, title, message, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'open', datetime('now'), datetime('now'))
            """,
            (alert_id, payload.severity, payload.title, payload.message),
        )
        conn.commit()
    return {"status": "ok", "alert_id": alert_id}


@router.post("/ops/alerts/{alert_id}/ack")
def ack_ops_alert(alert_id: str):
    with get_connection() as conn:
        updated = conn.execute(
            "UPDATE ops_alerts SET status='acknowledged', updated_at=datetime('now') WHERE alert_id=?",
            (alert_id,),
        ).rowcount
        conn.commit()
    if updated == 0:
        fail(404, "not_found", "Alert not found")
    return {"status": "ok", "alert_id": alert_id, "new_status": "acknowledged"}


@router.get("/ops/observability/dashboard")
def ops_observability_dashboard():
    with get_connection() as conn:
        totals = conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM audit_events) AS audit_events,
              (SELECT COUNT(*) FROM ops_alerts WHERE status='open') AS open_alerts,
              (SELECT COUNT(*) FROM notifications WHERE is_read=0) AS unread_notifications
            """
        ).fetchone()
        metrics = conn.execute(
            "SELECT metric_name, metric_value, labels_json, recorded_at FROM observability_metrics ORDER BY recorded_at DESC LIMIT 50"
        ).fetchall()

    return {
        "status": "ok",
        "summary": {
            "audit_events": totals["audit_events"],
            "open_alerts": totals["open_alerts"],
            "unread_notifications": totals["unread_notifications"],
        },
        "metrics": [
            {**dict(m), "labels": json.loads(m["labels_json"])}
            for m in metrics
        ],
        "generated_at": _utc_now(),
    }
