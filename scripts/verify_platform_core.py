#!/usr/bin/env python3
"""Verification script for P1/P2 platform-readiness backend endpoints."""

import importlib.util
import sys
import types


def _install_fastapi_stub():
    fastapi = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail):
            super().__init__(str(detail))
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def get(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def post(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def patch(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def put(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def delete(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

    def Header(default=None):  # noqa: N802
        return default

    class FastAPI:
        def __init__(self, *_, **__):
            self.routers = []

        def add_middleware(self, *_args, **_kwargs):
            return None

        def include_router(self, router):
            self.routers.append(router)

        def exception_handler(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def on_event(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

    class Request:  # pragma: no cover
        pass

    fastapi.HTTPException = HTTPException
    fastapi.APIRouter = APIRouter
    fastapi.Header = Header
    fastapi.FastAPI = FastAPI
    fastapi.Request = Request
    sys.modules["fastapi"] = fastapi

    fastapi_responses = types.ModuleType("fastapi.responses")

    class JSONResponse:
        def __init__(self, status_code: int, content: dict):
            self.status_code = status_code
            self.content = content

    fastapi_responses.JSONResponse = JSONResponse
    sys.modules["fastapi.responses"] = fastapi_responses

    fastapi_cors = types.ModuleType("fastapi.middleware.cors")

    class CORSMiddleware:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

    fastapi_cors.CORSMiddleware = CORSMiddleware
    sys.modules["fastapi.middleware.cors"] = fastapi_cors



def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bearer(token: str) -> str:
    return f"Bearer {token}"


def main() -> None:
    _install_fastapi_stub()

    sys.path.insert(0, ".")
    from backend.app.db.session import get_connection, init_db

    init_db()

    auth = _load_module("backend/app/routes/auth.py", "auth_mod")
    auth_schemas = _load_module("backend/app/schemas/auth.py", "auth_schema_mod")
    platform = _load_module("backend/app/routes/platform.py", "platform_mod")

    checks: list[tuple[str, bool, str]] = []

    # deterministic test user
    with get_connection() as conn:
        conn.execute("DELETE FROM auth_sessions")
        conn.execute("DELETE FROM users WHERE email='verify_platform@example.com'")
        conn.execute("DELETE FROM notifications WHERE user_id='verify_platform_user'")
        conn.commit()

    signup = auth.auth_signup(
        auth_schemas.AuthSignupRequest(
            email="verify_platform@example.com",
            password="verysecure123",
            display_name="Verify Platform",
        )
    )
    token = signup["session_token"]
    user_id = signup["user"]["user_id"]

    # Seed one notification for this test user
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO notifications(notification_id, user_id, title, message, is_read, created_at)
            VALUES(?, ?, ?, ?, 0, datetime('now'))
            """,
            ("notif_verify_001", user_id, "Welcome", "Platform test notification"),
        )
        conn.commit()

    overview = platform.dashboard_overview()
    checks.append(("dashboard_overview", overview.get("status") == "ok" and len(overview.get("stats", [])) == 4, str(overview.get("stats", []))))

    agents = platform.list_agents()
    checks.append(("agents_list", agents.get("status") == "ok" and len(agents.get("agents", [])) >= 1, str(len(agents.get("agents", [])))))

    first_agent_id = agents["agents"][0].agent_id
    agent_action = platform.act_on_agent(first_agent_id, platform.AgentActionRequest(action="pause"))
    checks.append(("agents_action", agent_action["agent"].status == "paused", str(agent_action["agent"])))

    deployments = platform.list_deployments()
    checks.append(("deployments_list", deployments.get("status") == "ok" and len(deployments.get("deployments", [])) >= 1, str(len(deployments.get("deployments", [])))))

    dep_id = deployments["deployments"][0].deployment_id
    dep_action = platform.act_on_deployment(dep_id, platform.DeploymentActionRequest(action="restart"))
    checks.append(("deployments_action", dep_action["deployment"].status == "running", str(dep_action["deployment"])))

    workflows = platform.list_workflows()
    checks.append(("workflows_list", workflows.get("status") == "ok" and len(workflows.get("workflows", [])) >= 1, str(workflows.get("workflows", []))))

    tasks = platform.list_tasks()
    checks.append(("tasks_list", tasks.get("status") == "ok" and len(tasks.get("tasks", [])) >= 1, str(len(tasks.get("tasks", [])))))

    outputs = platform.list_outputs()
    checks.append(("outputs_list", outputs.get("status") == "ok" and len(outputs.get("outputs", [])) >= 1, str(len(outputs.get("outputs", [])))))

    community = platform.community_feed()
    checks.append(("community_feed", community.get("status") == "ok" and isinstance(community.get("leaderboard", []), list), str(community.get("leaderboard", []))))

    prefs = platform.get_preferences(_bearer(token))
    checks.append(("preferences_get", prefs.get("status") == "ok", str(prefs)))

    prefs_updated = platform.patch_preferences(
        platform.UserPreferencesPatchRequest(notifications_push=False, theme="system"),
        _bearer(token),
    )
    checks.append(("preferences_patch", prefs_updated["preferences"].notifications_push is False and prefs_updated["preferences"].theme == "system", str(prefs_updated["preferences"])))

    avatar = platform.update_avatar(platform.AvatarUpdateRequest(avatar_url="https://example.com/avatar.png"), _bearer(token))
    checks.append(("avatar_patch", avatar.get("status") == "ok" and avatar.get("avatar_url") == "https://example.com/avatar.png", str(avatar)))

    search = platform.global_search("research")
    checks.append(("search", search.get("status") == "ok" and len(search.get("results", [])) >= 1, str(search.get("results", []))))

    notifications = platform.list_notifications(_bearer(token))
    checks.append(("notifications_list", notifications.get("status") == "ok" and len(notifications.get("notifications", [])) >= 1, str(notifications.get("notifications", []))))

    mark = platform.mark_notification_read("notif_verify_001", _bearer(token))
    checks.append(("notifications_mark_read", mark.get("status") == "ok" and mark.get("is_read") is True, str(mark)))

    balances = platform.token_balances(user_id)
    checks.append(("token_balances", balances.get("status") == "ok" and "asnd_balance" in balances, str(balances)))

    history = platform.token_history(user_id)
    checks.append(("token_history", history.get("status") == "ok" and isinstance(history.get("history", []), list), str(history.get("history", []))))

    browse = platform.marketplace_browse()
    checks.append(("marketplace_browse", browse.get("status") == "ok" and isinstance(browse.get("listings", []), list), str(browse.get("listings", []))))

    with get_connection() as conn:
        listing = conn.execute(
            "SELECT listing_id FROM marketplace_listings WHERE status='published' LIMIT 1"
        ).fetchone()
        if listing is None:
            conn.execute(
                """
                INSERT INTO marketplace_listings(
                    listing_id, creator_user_id, title, description, category,
                    pricing_model, price_amount, price_token, status, tags_json,
                    created_at, updated_at, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'published', '[]', datetime('now'), datetime('now'), datetime('now'))
                """,
                (
                    "lst_verify_platform",
                    "creator_verify",
                    "Verify Listing",
                    "Listing for platform verification",
                    "productivity",
                    "one_time",
                    1,
                    "ASND",
                ),
            )
            conn.commit()
            listing = conn.execute(
                "SELECT listing_id FROM marketplace_listings WHERE listing_id='lst_verify_platform'"
            ).fetchone()

    install = platform.install_listing(listing["listing_id"], platform.InstallListingRequest(user_id=user_id))
    checks.append(("install_listing", install.get("status") == "ok" and install.get("entitlement").user_id == user_id, str(install)))

    entitlements = platform.get_entitlements(user_id)
    checks.append(("entitlements", entitlements.get("status") == "ok" and len(entitlements.get("entitlements", [])) >= 1, str(entitlements)))

    payout_totals = platform.creator_payout_totals("creator_1")
    checks.append(("payout_totals", payout_totals.get("status") == "ok" and "pending_amount" in payout_totals, str(payout_totals)))

    failed = [c for c in checks if not c[1]]

    print("Platform core verification results:")
    for name, ok, detail in checks:
        print(f"- {'PASS' if ok else 'FAIL'}: {name} -> {detail}")

    if failed:
        print(f"\nFAILED checks: {len(failed)}")
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
