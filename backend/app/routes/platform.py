from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Header
from pydantic import BaseModel

from backend.app.db.session import get_connection
from backend.app.schemas.platform import (
    AgentActionRequest,
    AgentActionResponse,
    AgentListResponse,
    AgentRecord,
    AvatarUpdateRequest,
    AvatarUpdateResponse,
    CommunityPost,
    CommunityResponse,
    CreatorPayoutTotalsResponse,
    DashboardActivity,
    DashboardAgent,
    DashboardOverviewResponse,
    DashboardStat,
    DeploymentActionRequest,
    DeploymentActionResponse,
    DeploymentListResponse,
    DeploymentRecord,
    EntitlementRecord,
    EntitlementsResponse,
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
from backend.app.services.auth_service import require_user_access, resolve_session, update_profile
from backend.app.services.error_response import fail

router = APIRouter()


def _require_user_id(authorization: str | None) -> str:
    auth = resolve_session(authorization)
    return auth["user"]["user_id"]


def _row_dict(row):
    return dict(row) if row is not None else None


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


@router.get("/agents", response_model=AgentListResponse)
def list_agents(authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.agent_id, a.name, a.category, a.description, a.status,
                   a.tasks_completed, a.success_rate, a.created_at, a.updated_at
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

    return {"status": "ok", "agents": [AgentRecord(**_row_dict(r)) for r in rows]}


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
            """
            SELECT agent_id, name, category, description, status, tasks_completed, success_rate, created_at, updated_at
            FROM agents
            WHERE agent_id=?
            """,
            (agent_id,),
        ).fetchone()

    return {"status": "ok", "agent": AgentRecord(**_row_dict(row))}


@router.get("/deployments", response_model=DeploymentListResponse)
def list_deployments():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent,
                   requests_per_day, created_at, updated_at
            FROM deployments
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return {"status": "ok", "deployments": [DeploymentRecord(**_row_dict(r)) for r in rows]}


@router.post("/deployments/{deployment_id}/actions", response_model=DeploymentActionResponse)
def act_on_deployment(deployment_id: str, payload: DeploymentActionRequest):
    next_status = "running" if payload.action in {"resume", "restart"} else "paused"
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM deployments WHERE deployment_id=?", (deployment_id,)).fetchone()
        if not exists:
            fail(404, "not_found", "Deployment not found")

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

    return {"status": "ok", "deployment": DeploymentRecord(**_row_dict(row))}


@router.get("/workflows", response_model=WorkflowListResponse)
def list_workflows():
    with get_connection() as conn:
        workflows = conn.execute(
            """
            SELECT workflow_id, name, status, runs_total, success_rate, updated_at
            FROM workflows
            ORDER BY updated_at DESC
            """
        ).fetchall()

        runs = conn.execute(
            """
            SELECT run_id, workflow_id, status, duration_ms, started_at
            FROM workflow_runs
            ORDER BY started_at DESC
            LIMIT 20
            """
        ).fetchall()

    return {
        "status": "ok",
        "workflows": [WorkflowRecord(**_row_dict(r)) for r in workflows],
        "recent_runs": [WorkflowRunRecord(**_row_dict(r)) for r in runs],
    }


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(status: str | None = None):
    query = """
        SELECT task_id, title, status, priority, assigned_to, updated_at
        FROM tasks
    """
    params: tuple = ()
    if status:
        query += " WHERE status=?"
        params = (status,)
    query += " ORDER BY updated_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return {"status": "ok", "tasks": [TaskRecord(**_row_dict(r)) for r in rows]}


@router.get("/outputs", response_model=OutputListResponse)
def list_outputs():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT output_id, title, output_type, size_bytes, download_url, created_at
            FROM outputs
            ORDER BY created_at DESC
            """
        ).fetchall()

    return {"status": "ok", "outputs": [OutputRecord(**_row_dict(r)) for r in rows]}


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
    status: str = "active"


@router.post("/agents")
def create_agent(payload: AgentCrudInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    agent_id = f"agt_{secrets.token_hex(6)}"

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agents(agent_id, owner_user_id, name, category, description, status, tasks_completed, success_rate, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?, 0, 0, datetime('now'), datetime('now'))
            """,
            (agent_id, actor, payload.name, payload.category, payload.description, payload.status),
        )
        conn.commit()

    _audit(actor, "agent.create", "agent", agent_id, {"category": payload.category})
    return {"status": "ok", "agent_id": agent_id}


@router.get("/agents/{agent_id}")
def get_agent(agent_id: str, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_agent_owner(conn, agent_id, actor)
        row = conn.execute(
            """
            SELECT agent_id, name, category, description, status, tasks_completed, success_rate, created_at, updated_at
            FROM agents WHERE agent_id=?
            """,
            (agent_id,),
        ).fetchone()
    if not row:
        fail(404, "not_found", "Agent not found")
    return {"status": "ok", "agent": dict(row)}


@router.patch("/agents/{agent_id}")
def patch_agent(agent_id: str, payload: AgentCrudInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        _require_agent_owner(conn, agent_id, actor)
        conn.execute(
            """
            UPDATE agents
            SET name=?, category=?, description=?, status=?, updated_at=datetime('now')
            WHERE agent_id=?
            """,
            (payload.name, payload.category, payload.description, payload.status, agent_id),
        )
        conn.commit()
    _audit(actor, "agent.update", "agent", agent_id, {"category": payload.category, "status": payload.status})
    return get_agent(agent_id, authorization=authorization)


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


@router.get("/deployments/{deployment_id}")
def get_deployment(deployment_id: str):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent, requests_per_day, created_at, updated_at
            FROM deployments WHERE deployment_id=?
            """,
            (deployment_id,),
        ).fetchone()
    if not row:
        fail(404, "not_found", "Deployment not found")
    return {"status": "ok", "deployment": dict(row)}


@router.get("/deployments/{deployment_id}/metrics")
def deployment_metrics(deployment_id: str):
    with get_connection() as conn:
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
    return {"status": "ok", "deployment_id": deployment_id, "metrics": [dict(r) for r in rows]}


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


@router.post("/workflows")
def create_workflow(payload: WorkflowCrudInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    workflow_id = f"wf_{secrets.token_hex(5)}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO workflows(workflow_id, name, status, runs_total, success_rate, updated_at)
            VALUES(?, ?, ?, 0, 0, datetime('now'))
            """,
            (workflow_id, payload.name, payload.status),
        )
        conn.commit()
    _audit(actor, "workflow.create", "workflow", workflow_id)
    return {"status": "ok", "workflow_id": workflow_id}


@router.put("/workflows/{workflow_id}/graph")
def put_workflow_graph(workflow_id: str, payload: WorkflowGraphInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM workflows WHERE workflow_id=?", (workflow_id,)).fetchone()
        if not exists:
            fail(404, "not_found", "Workflow not found")
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
def get_workflow_graph(workflow_id: str):
    with get_connection() as conn:
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
def list_workflow_runs(workflow_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT run_id, workflow_id, status, duration_ms, started_at
            FROM workflow_runs WHERE workflow_id=?
            ORDER BY started_at DESC
            LIMIT 100
            """,
            (workflow_id,),
        ).fetchall()
    return {"status": "ok", "workflow_id": workflow_id, "runs": [dict(r) for r in rows]}


class TaskCreateInput(BaseModel):
    title: str
    priority: str = "medium"
    assigned_to: str | None = None


@router.post("/tasks")
def create_task(payload: TaskCreateInput, authorization: str | None = Header(default=None)):
    actor = _require_user_id(authorization)
    task_id = f"tsk_{secrets.token_hex(5)}"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO tasks(task_id, title, status, priority, assigned_to, updated_at)
            VALUES (?, ?, 'queued', ?, ?, datetime('now'))
            """,
            (task_id, payload.title, payload.priority, payload.assigned_to),
        )
        conn.execute(
            "INSERT INTO task_logs(task_id, level, message, created_at) VALUES (?, 'info', ?, datetime('now'))",
            (task_id, f"Task created by {actor}"),
        )
        conn.commit()
    _audit(actor, "task.create", "task", task_id, {"priority": payload.priority})
    return {"status": "ok", "task_id": task_id}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT task_id, title, status, priority, assigned_to, updated_at FROM tasks WHERE task_id=?",
            (task_id,),
        ).fetchone()
    if not row:
        fail(404, "not_found", "Task not found")
    return {"status": "ok", "task": dict(row)}


def _set_task_status(task_id: str, new_status: str, actor: str, message: str):
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if not exists:
            fail(404, "not_found", "Task not found")
        conn.execute("UPDATE tasks SET status=?, updated_at=datetime('now') WHERE task_id=?", (new_status, task_id))
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


@router.get("/tasks/{task_id}/logs")
def get_task_logs(task_id: str):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT level, message, created_at FROM task_logs WHERE task_id=? ORDER BY created_at DESC LIMIT 200",
            (task_id,),
        ).fetchall()
    return {"status": "ok", "task_id": task_id, "logs": [dict(r) for r in rows]}


@router.get("/outputs/{output_id}")
def get_output(output_id: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT output_id, title, output_type, size_bytes, download_url, created_at FROM outputs WHERE output_id=?",
            (output_id,),
        ).fetchone()
    if not row:
        fail(404, "not_found", "Output not found")
    return {"status": "ok", "output": dict(row)}


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
    return {"status": "ok", "user_id": user_id, "extras": dict(row) if row else {}}


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
    return {"status": "ok", "api_keys": [dict(r) for r in rows]}


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
    return {"status": "ok", "user_id": user_id, "positions": [dict(r) for r in rows]}


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
    return {"status": "ok", "user_id": user_id, "entries": [dict(r) for r in rows]}


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
    return {"status": "ok", "query": query or "", "category": category, "sort": sort, "listings": [dict(r) for r in rows]}


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
    return {"status": "ok", "user_id": user_id, "licenses": [dict(r) for r in rows]}


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
    return {"status": "ok", "listing_id": listing_id, "events": [dict(r) for r in rows]}


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
            {**dict(r), "metadata": json.loads(r["metadata_json"])}
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
    return {"status": "ok", "alerts": [dict(r) for r in rows]}


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
