# AgentAscend MEMORY.md

## Current operating state — verified 2026-05-13
AgentAscend is a crypto-native AI agent platform and marketplace. The backend is the source of truth for payment, access, marketplace entitlements, scheduler state, executions, tasks, outputs, agents, workflows, and user-owned data. Runtime-worker backend is live, the runtime-aware frontend/source audit passed, workflow ownership hardening is live, and full signed-in functional UX QA on 2026-05-11 verified the core loop: Ascend Forge agent creation → Run Agent → Task → Execution → Output → UI/dashboard refresh. Frontend/v0 must display backend truth and must not use localStorage as authority for paid unlocks, access, ownership, settings, payments, marketplace installs, agent metrics, workflow ownership, or runtime status.

## Verified production baseline
- Git branch: `main`; local main is diverged from `origin/main` and must not be pushed without explicit reconciliation/scope review.
- Current git posture observed 2026-05-13: local `main` remains diverged/noisy from `origin/main` after the clean-worktree deployment push; do not push local main without explicit reconciliation/scope review.
- Latest recorded remote/deployment evidence points to `origin/main` commit `7cc1c6a986e1e2a1896b5e8e5b62b36917bccc70`; Railway AgentAscend and AgentAscend-Scheduler deployed it successfully, with live `/health` HTTP 200 and `/openapi.json` HTTP 200 valid JSON.
- Local systemd scheduler is active/enabled as `agentascend-scheduler.service`, using `.venv/bin/python scripts/run_scheduler.py`, `Restart=always`, and `/etc/agentascend-scheduler.env`.
- Live API: `GET https://api.agentascend.ai/health` returns HTTP 200 `{"status":"ok"}` in current checks; standard API security headers have been present in recent audits.

## Standing post-deploy QA rule
After every AgentAscend deploy, Hermes must run the matching post-deploy QA checklist before final PASS. This applies to Railway backend/API, Railway scheduler, Vercel/frontend/v0, docs-only deploys, backend commits, frontend ZIP/source deployments, and scheduler/runtime-worker deployments. If required QA is blocked, report PARTIAL with the exact blocker and next safe step; never mark deploy PASS. Use the local Playwright harness at `/tmp/agentascend-browser-qa/` for safe frontend visual/route smoke when available, with payment/admin/scheduler blockers enabled.

## Current product evidence
- 2026-05-11 standing Vercel/frontend post-deploy QA PASS: live routes, CSP/security headers, Solana RPC/WSS, API health/OpenAPI, no-auth private-read guards, and deployed bundle markers passed.
- 2026-05-11 full signed-in functional UX QA PASS WITH CAVEATS: throwaway account created, Ascend Forge create worked, Run Agent worked, backend showed 1 agent/1 task/1 execution/1 output, UI reflected Tasks 1 / Success 100% / Active and output/execution/task records.
- Workflow builder owner-isolation QA PASS remains current: User A create/save/read/run works; User B list exclusion and direct cross-user graph/run/runs access are blocked.
- Pump.fun payment flow remains separate from frontend polish; do not touch wallet/payment flows during routine UI/runtime polishing.

## Escalated payment/data-integrity watch
- Payment↔grant linkage hardening is deployed for future legacy `/payments/verify` successes: completed payments now carry intent/verification timestamps and matching payment_intents are completed/verified with tx_signature.
- Historical null-heavy linkage rows, if any, remain audit-only; no production DB mutation/backfill, payment replay, access grant edits, or payment verification can be run without explicit owner approval.

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
1. Return to frontend/product polish: output search/export/bulk UX, richer workflow run-history/runtime detail, and deployment events/log-streaming UX.
2. Keep historical payment↔grant linkage repair/backfill proposal-only unless owner-approved after sanitized aggregate preflight.
3. Add remaining backend gap slices one at a time only when frontend polish proves a real missing endpoint.
4. Continue knowledge/wiki/Obsidian cleanup in small batches; keep routine generated cron reports out of git noise unless intentionally archived.
5. Multi-agent architecture setup after frontend/backend product contracts are clearer.

## Safety rules that still matter
- Backend remains payment/access authority.
- Never print or commit secrets: DB URLs, private RPC URLs, auth tokens, cookies, private keys, seed phrases, API keys, signed transactions, raw payloads, or raw private response bodies.
- Public tx signatures, public wallet addresses, and public payment references may be documented when already part of launch evidence.
- No production DB mutations, migrations, payment actions, scheduler state changes, env changes, deploys, public posts, or account actions without explicit owner approval.
- Before project changes: read this file, verify git/live production state, keep commits isolated, and stage only intended files.
