from __future__ import annotations

from fastapi import APIRouter, Header

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
from backend.app.services.auth_service import resolve_session, update_profile
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
def list_agents():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT agent_id, name, category, description, status, tasks_completed, success_rate, created_at, updated_at
            FROM agents
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return {"status": "ok", "agents": [AgentRecord(**_row_dict(r)) for r in rows]}


@router.post("/agents/{agent_id}/actions", response_model=AgentActionResponse)
def act_on_agent(agent_id: str, payload: AgentActionRequest):
    status_by_action = {"start": "active", "resume": "active", "pause": "paused"}
    with get_connection() as conn:
        exists = conn.execute("SELECT 1 FROM agents WHERE agent_id=?", (agent_id,)).fetchone()
        if not exists:
            fail(404, "not_found", "Agent not found")

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
            SELECT post_id, author_user_id, title, body, likes, created_at
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
def token_balances(user_id: str):
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
def token_history(user_id: str):
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
def get_entitlements(user_id: str):
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
def creator_payout_totals(creator_user_id: str):
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
