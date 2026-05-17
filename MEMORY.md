# AgentAscend MEMORY.md

## Current operating state — verified 2026-05-16
AgentAscend is a crypto-native AI agent platform and marketplace. The backend is the source of truth for payment, access, marketplace entitlements, scheduler state, executions, tasks, outputs, agents, workflows, and user-owned data. Runtime-worker backend is live, workflow ownership hardening is live, and 2026-05-16 production QA verified the merged Run Agent UI click path from visible UI: throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Overview. Frontend/v0 must display backend truth and must not use localStorage as authority for paid unlocks, access, ownership, settings, payments, marketplace installs, agent metrics, workflow ownership, or runtime status.

## Verified production baseline
- Git branch: `main`; local main is diverged from `origin/main` and must not be pushed without explicit reconciliation/scope review.
- Current git posture observed 2026-05-12: `main...origin/main [ahead 8, behind 8]` plus broad untracked raw/wiki/skills artifacts and local `.obsidian/*` changes.
- Latest recorded remote/deployment evidence points to `origin/main` commit `74bd6e92d2129500dc92261eda9f9b09ea2a5ae5`; live `/health` and `/openapi.json` should be rechecked before any deploy/release claim.
- Local systemd scheduler is active/enabled as `agentascend-scheduler.service`, using `.venv/bin/python scripts/run_scheduler.py`, `Restart=always`, and `/etc/agentascend-scheduler.env`.
- Live API: `GET https://api.agentascend.ai/health` returns HTTP 200 `{"status":"ok"}` in current checks; standard API security headers have been present in recent audits.

## Standing post-deploy QA rule
After every AgentAscend deploy, Hermes must run the matching post-deploy QA checklist before final PASS. This applies to Railway backend/API, Railway scheduler, Vercel/frontend/v0, docs-only deploys, backend commits, frontend ZIP/source deployments, and scheduler/runtime-worker deployments. If required QA is blocked, report PARTIAL with the exact blocker and next safe step; never mark deploy PASS. Use the local Playwright harness at `/tmp/agentascend-browser-qa/` for safe frontend visual/route smoke when available, with payment/admin/scheduler blockers enabled.

## Current product evidence
- 2026-05-11 standing Vercel/frontend post-deploy QA PASS: live routes, CSP/security headers, Solana RPC/WSS, API health/OpenAPI, no-auth private-read guards, and deployed bundle markers passed.
- 2026-05-16 production Run Agent UI click-path QA PASS WITH CAVEAT: AgentAscend-Web `fix/run-agent-ui-click-path` merged to main at `0292142b39962c705069e3c5d6daf2fbf157622c` (`app/app/agents/page.tsx` only). Production throwaway signup, safe agent create, visible Run Agent click, `POST /agents/{id}/run` HTTP 200, Running/Pending UI state, and Tasks/Executions/Outputs/Overview propagation passed. Only caveat: exact `Agent run queued` toast was not observed.
- 2026-05-13 live Output Library + signed-in runtime QA PASS WITH CAVEATS: local Playwright no-sandbox harness verified public/app routes, throwaway signup, Ascend Forge create, Run Agent from agent-card menu, backend 1 agent/1 task/1 execution/1 output, Output Library local search copy, disabled Export All/Load More, and backend output preview. Throwaway QA resources remain in production; do not delete without separate owner-approved cleanup.
- Workflow builder owner-isolation QA PASS remains current: User A create/save/read/run works; User B list exclusion and direct cross-user graph/run/runs access are blocked.
- Pump.fun payment flow remains separate from frontend polish; do not touch wallet/payment flows during routine UI/runtime polishing.

## Escalated P0 privacy/data-integrity watch
- 2026-05-14 P0 multi-user isolation audit found deployment privacy gaps: unauthenticated `GET /deployments` and deployment metrics returned deployment data, and source inspection showed deployment direct read/actions lack auth/owner checks. Keep deployment owner-isolation as a separate launch/security track; Run Agent UI click-path is no longer blocking normal runtime/product polish.
- Read-only local scheduler/DB reports from 2026-05-11 flagged completed payment rows without active grant linkage by `payment_id` and active grants that are null-heavy for `payment_id`/`intent_reference`.
- Treat payment linkage as a launch-risk investigation until production-vs-local scope is verified, a backfill/forward-invariant plan is approved, and tests prove future payment-created grants carry durable linkage.
- No production DB mutation/backfill, payment replay, access grant edits, or payment verification can be run without explicit owner approval.

## Pump.fun payment state
- Pump.fun create/verify routes are live and auth-gated: `POST /payments/pumpfun/create`, `POST /payments/pumpfun/verify`.
- Controlled Pump.fun payment regression PASS is archived at [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]].
- Public tx: `2ydGT5uPArgKx2WkiBZ9xNm17ap6WB4BVznJTNwThDThS8qia6zT5vq76CHgEDFwW4gj7FfMyTHJweobt9K5UhrR`.
- Payment reference: `pumpfun:agentascendai:0967b710095e47bba1e12d4149639d9e`.
- Evidence showed payment found, payment_id present, payment intent completed, verified access grant, listing scope, marketplace entitlement, and zero duplicate groups.
- Exact `tx_signature` binding hardening is implemented/deployed; Pump.fun helper runtime dependency is `@pump-fun/agent-payments-sdk` 3.0.3.

## Scheduler and automation state
Enabled/audited production scheduler jobs include backend health, integration drift, wiki consistency, TODO/FIXME scan, payment route audit, failed-payment replay review, access-grant integrity check, task queue worker, git status summary, and Telegram status summary. `default-roadmap-review` remains disabled/manual because it is premium/strategy-gated. Hermes cronjobs are separate from AgentAscend DB scheduler jobs; keep report-only defaults and do not send external messages or run risky jobs unless explicitly approved.

## Current next recommended phases
1. Verify payment↔grant linkage scope and write/execute a TDD local hardening plan before any launch expansion.
2. Continue frontend/runtime product work: deployment events/log-streaming UX, richer workflow run-history details, settings/token/community polish, success-toast polish for Run Agent, and optional throwaway QA cleanup plan only if owner approves production cleanup.
3. Add remaining backend gap slices one at a time only when frontend polish proves a real missing endpoint.
4. Continue knowledge/wiki/Obsidian cleanup in small batches; keep routine generated cron reports out of git noise unless intentionally archived.
5. Multi-agent architecture setup after frontend/backend product contracts are clearer.

## Safety rules that still matter
- Backend remains payment/access authority.
- Never print or commit secrets: DB URLs, private RPC URLs, auth tokens, cookies, private keys, seed phrases, API keys, signed transactions, raw payloads, or raw private response bodies.
- Public tx signatures, public wallet addresses, and public payment references may be documented when already part of launch evidence.
- No production DB mutations, migrations, payment actions, scheduler state changes, env changes, deploys, public posts, or account actions without explicit owner approval.
- Before project changes: read this file, verify git/live production state, keep commits isolated, and stage only intended files.
