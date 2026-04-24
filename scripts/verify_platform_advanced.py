#!/usr/bin/env python3
"""Verification for advanced domain/settings/token/marketplace/ops APIs."""

import importlib.util
import sys
import time
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
            return lambda fn: fn

        def post(self, *_args, **_kwargs):
            return lambda fn: fn

        def patch(self, *_args, **_kwargs):
            return lambda fn: fn

        def put(self, *_args, **_kwargs):
            return lambda fn: fn

        def delete(self, *_args, **_kwargs):
            return lambda fn: fn

    def Header(default=None):
        return default

    fastapi.HTTPException = HTTPException
    fastapi.APIRouter = APIRouter
    fastapi.Header = Header
    sys.modules["fastapi"] = fastapi
    return HTTPException


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bearer(token: str) -> str:
    return f"Bearer {token}"


def main() -> None:
    HTTPException = _install_fastapi_stub()

    sys.path.insert(0, ".")
    from backend.app.db.session import init_db

    init_db()
    auth = _load_module("backend/app/routes/auth.py", "auth_mod_adv")
    auth_schemas = _load_module("backend/app/schemas/auth.py", "auth_schemas_adv")
    platform = _load_module("backend/app/routes/platform.py", "platform_mod_adv")

    checks: list[tuple[str, bool, str]] = []

    email = f"verify_advanced_{int(time.time())}@example.com"
    signup = auth.auth_signup(
        auth_schemas.AuthSignupRequest(
            email=email,
            password="verysecure123",
            display_name="Verify Advanced",
        )
    )
    token = signup["session_token"]
    user_id = signup["user"]["user_id"]

    # agents CRUD
    a = platform.create_agent(platform.AgentCrudInput(name="Ops Agent", category="Automation", description="desc"), _bearer(token))
    agent_id = a["agent_id"]
    checks.append(("agents_create", a.get("status") == "ok", str(a)))
    g = platform.get_agent(agent_id)
    checks.append(("agents_get", g.get("status") == "ok" and g["agent"]["agent_id"] == agent_id, str(g)))
    p = platform.patch_agent(agent_id, platform.AgentCrudInput(name="Ops Agent 2", category="Automation", description="desc", status="paused"), _bearer(token))
    checks.append(("agents_patch", p["agent"]["status"] == "paused", str(p)))

    # deployment + metrics
    d = platform.create_deployment(platform.DeploymentCrudInput(name="Ops Deploy", environment="staging", region="US West"), _bearer(token))
    dep_id = d["deployment_id"]
    checks.append(("deployments_create", d.get("status") == "ok", str(d)))
    dm = platform.deployment_metrics(dep_id)
    checks.append(("deployments_metrics", dm.get("status") == "ok", str(dm)))

    # workflow graph
    w = platform.create_workflow(platform.WorkflowCrudInput(name="WF Advanced", status="active"), _bearer(token))
    wf_id = w["workflow_id"]
    graph = platform.put_workflow_graph(
        wf_id,
        platform.WorkflowGraphInput(nodes=[{"node_id": "n1", "node_type": "trigger", "config": {"k": 1}, "position": {"x": 0, "y": 0}}]),
        _bearer(token),
    )
    checks.append(("workflow_graph_put", graph.get("nodes") == 1, str(graph)))
    graph_get = platform.get_workflow_graph(wf_id)
    checks.append(("workflow_graph_get", len(graph_get.get("nodes", [])) == 1, str(graph_get)))

    # tasks queue/logs/retry/cancel
    t = platform.create_task(platform.TaskCreateInput(title="New task", priority="high", assigned_to=agent_id), _bearer(token))
    task_id = t["task_id"]
    checks.append(("tasks_create", t.get("status") == "ok", str(t)))
    retry = platform.retry_task(task_id, _bearer(token))
    cancel = platform.cancel_task(task_id, _bearer(token))
    logs = platform.get_task_logs(task_id)
    checks.append(("tasks_retry_cancel_logs", retry.get("status") == "ok" and cancel.get("status") == "ok" and len(logs.get("logs", [])) >= 2, str(logs)))

    # settings extras/api keys/integrations
    extras = platform.patch_profile_extras(platform.ProfileExtrasPatch(timezone="UTC", language="en"), _bearer(token))
    checks.append(("profile_extras", extras.get("status") == "ok", str(extras)))
    key = platform.create_api_key(platform.ApiKeyCreateInput(name="bot-key"), _bearer(token))
    checks.append(("api_key_create", key.get("status") == "ok" and key.get("secret", "").startswith("asnd_"), str(key)))
    revoke = platform.revoke_api_key(key["key_id"], _bearer(token))
    checks.append(("api_key_revoke", revoke.get("revoked") is True, str(revoke)))
    integ = platform.patch_integration(platform.IntegrationPatchInput(provider="telegram", status="connected", config={"chat_id": "1"}), _bearer(token))
    checks.append(("integrations_patch", integ.get("integration_status") == "connected", str(integ)))

    # token roadmap
    st = platform.token_staking_positions(user_id)
    rw = platform.token_rewards_ledger(user_id)
    tx = platform.token_transactions(user_id)
    checks.append(("token_endpoints", st.get("status") == "ok" and rw.get("status") == "ok" and tx.get("status") == "ok", str(tx)))

    # marketplace maturity
    disc = platform.marketplace_discover(query="verify", sort="latest")
    lic = platform.marketplace_licenses(user_id)
    checks.append(("marketplace_discover_licenses", disc.get("status") == "ok" and lic.get("status") == "ok", str({"discover": disc, "licenses": lic})))

    # install-track and events
    if disc.get("listings"):
        listing_id = disc["listings"][0]["listing_id"]
        track = platform.install_track(listing_id, platform.InstallListingRequest(user_id=user_id), _bearer(token))
        events = platform.listing_install_events(listing_id)
        checks.append(("marketplace_install_track", track.get("status") == "ok" and len(events.get("events", [])) >= 1, str(events)))
    else:
        checks.append(("marketplace_install_track", True, "no listing available in test dataset"))

    # ops hardening
    ae = platform.audit_events(limit=20)
    alert = platform.create_ops_alert(platform.OpsAlertInput(severity="warning", title="test", message="m"))
    ack = platform.ack_ops_alert(alert["alert_id"])
    obs = platform.ops_observability_dashboard()
    checks.append(("ops_audit_alert_obs", ae.get("status") == "ok" and ack.get("new_status") == "acknowledged" and obs.get("status") == "ok", str(obs)))

    # cleanup delete agent
    deleted = platform.delete_agent(agent_id, _bearer(token))
    checks.append(("agents_delete", deleted.get("deleted") is True, str(deleted)))

    failed = [c for c in checks if not c[1]]
    print("Platform advanced verification results:")
    for name, ok, detail in checks:
        print(f"- {'PASS' if ok else 'FAIL'}: {name} -> {detail}")

    if failed:
        print(f"\nFAILED checks: {len(failed)}")
        sys.exit(1)
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
