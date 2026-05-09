# AgentAscend MEMORY.md

## Current operating state — verified 2026-05-09
AgentAscend is a crypto-native AI agent platform and marketplace. The backend is the source of truth for payment, access, marketplace entitlements, scheduler state, executions, tasks, outputs, agents, workflows, and user-owned data. Runtime-worker backend is live. The runtime-aware v0/frontend loop has been owner-verified: Agent → Run Agent → Task → Execution → Output. Workflow auth ownership backend is live, and workflow-builder owner-isolation QA passed: User A create/save/read/run works through the live workflow UI/API; User B cross-user graph/save/run/runs probes fail closed with 403; graph save remains `{ nodes: [...] }`; unsupported `edges` were not sent; workflow copy is honest and partially-live. Frontend/v0 must display backend truth and must not use localStorage as authority for paid unlocks, access, ownership, settings, payments, marketplace installs, workflow ownership, or graph state.

## Verified production baseline
- Git branch for normal work: `main`; original local `main` is currently diverged from `origin/main` and should not be pushed without exact scope review.
- Current production/docs baseline: `origin/main` `712c05e8d1c1b9c05bae5d8723713ff80b5c5567`.
- Original local main observed during hygiene audit: HEAD `c8f024655ff51d9bcb8630f503553d5953f1f52e`; ahead/behind `5 / 5`; staged files none; dirty/untracked docs/raw/wiki/skills plus `.obsidian` workspace/graph files exist. Prefer clean worktrees until reconciled.
- Railway `AgentAscend`: SUCCESS at commit `712c05e` (deployment `ddf9b9a6`, verified 2026-05-07).
- Railway `AgentAscend-Scheduler`: SUCCESS at commit `712c05e` (deployment `c2f213a7`, verified 2026-05-07).
- Live API: `GET /health` HTTP 200; `GET /openapi.json` HTTP 200 valid JSON; HSTS and standard API security headers present.

## Standing post-deploy QA rule
After every AgentAscend deploy, Hermes must run the matching post-deploy QA checklist before final PASS. This applies to Railway backend/API, Railway scheduler, Vercel/frontend/v0, docs-only deploys, backend commits, frontend ZIP/source deployments, and scheduler/runtime-worker deployments. If required QA is blocked, report PARTIAL with the exact blocker and next safe step; never mark deploy PASS. Use the local Playwright harness at `/tmp/agentascend-browser-qa/agentascend-browser-qa.js` for safe frontend visual/route smoke when available, with payment/admin/scheduler blockers enabled.

## Forge/runtime/backend state
Live OpenAPI confirms Forge capability/templates, full agent definitions, agent run/deploy bridge routes, workflow run, Command Center aggregate, deployment events, tasks, outputs, and execution routes are deployed. Runtime bridges create/record backend work, but full autonomous worker behavior and full visual workflow graph editing remain later product slices.

## Pump.fun payment state
- Pump.fun create/verify routes are live and auth-gated: `POST /payments/pumpfun/create`, `POST /payments/pumpfun/verify`.
- Controlled Pump.fun payment regression PASS is archived at [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]].
- Payment found, payment_id present, payment intent completed, verification_status verified, access grant present, listing-scoped true, marketplace entitlement present, and duplicate groups remained zero.
- Exact `tx_signature` binding hardening is implemented and deployed.
- Replay-index DDL is not needed now because equivalent/target unique indexes/constraints already exist.
- Pump.fun/Solana dependency advisories remain monitored; do not run audit fixes blindly.

## Scheduler and automation state
Enabled/audited production jobs: `default-backend-health-check`, `default-integration-drift-check`, `default-wiki-consistency-check`, `default-todo-fixme-scan`, `default-payment-route-audit`, `default-failed-payment-replay-review`, `default-access-grant-integrity-check`, `default-task-queue-worker`.

Disabled/held jobs: `default-telegram-status-summary`, `default-roadmap-review`, `default-git-status-summary`.

Hermes cronjobs are separate from AgentAscend scheduler jobs. Legacy Telegram-delivered Hermes cronjobs still exist and require owner approval before pause/remove/conversion. Local-only swarm report jobs are active. Weekly local-only hygiene cronjob `5cf95fc08134` was created on 2026-05-07 to report on cron viability, scheduler posture, stale docs, and next cleanup actions.

Do not change scheduler jobs, run `/jobs/run-due`, or run payment/scheduler canaries without explicit approval.

## Frontend/product state
Owner-assisted logged-in QA verified the runtime product loop. Workflow-builder owner-isolation QA PASS is archived at [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa]]. The frontend is no longer blocked on backend integration for tasks, outputs, executions, or workflow ownership basics. Next work should focus on workflow node configuration editing/labels, richer run-history details, output search/export/bulk UX, task/execution detail UX, deployment events/log-streaming UX, and settings/community polish. Pump.fun payment flow remains separate and should not be touched during the next frontend polish phase.

## Current next recommended phases
1. Workflow node configuration editing and labels while preserving `{ nodes: [...] }`.
2. Richer workflow run-history details, output search/export/bulk UX, task/execution/output detail, deployment log-streaming UX, and settings persistence UX.
3. Add remaining backend slices one at a time only when frontend polish proves a real missing endpoint.
4. Continue docs/wiki/Obsidian cleanup in small batches; mark stale phase-blocker notes as superseded instead of deleting raw evidence.

## Safety rules that still matter
- Backend remains payment/access authority.
- Never print or commit secrets: DB URLs, private RPC URLs, auth tokens, cookies, private keys, seed phrases, signed transactions, raw payloads, or raw request/response bodies.
- Public tx signatures, public wallet addresses, and public payment references may be documented when already part of launch evidence.
- No production DB mutations, migrations, payment actions, scheduler changes, env changes, deploys, public posts, or account actions without explicit owner approval.
- Before project changes: read this file, verify git/live production state, keep commits isolated, and stage only intended files.
