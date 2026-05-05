# AgentAscend MEMORY.md

## Current operating state — verified 2026-05-04
AgentAscend is a crypto-native AI agent platform and marketplace. The backend is the source of truth for payment, access, marketplace entitlements, scheduler state, executions, tasks, outputs, agents, and user-owned data. Frontend/v0 must display backend truth and must not use localStorage as authority for paid unlocks, access, ownership, settings, payments, or marketplace installs.

## Verified production baseline
- Git branch: `main`.
- Backend-feature baseline: `26aa8abca8bc5bcf8f12a25a5fb9a222f5576eaa` (`backend: add owner scoped deployment events`). Latest Railway commit can be a docs-only cleanup commit; verify before acting.
- Ahead/behind: `0 / 0` at cleanup start.
- Railway `AgentAscend`: SUCCESS at `26aa8abca8bc5bcf8f12a25a5fb9a222f5576eaa` (deployment `1bd2d398-fd7e-4916-80ce-a6c90f5c6010`).
- Railway `AgentAscend-Scheduler`: SUCCESS at `26aa8abca8bc5bcf8f12a25a5fb9a222f5576eaa` (deployment `51f5f065-2e74-4824-b607-2477c5c7241e`).
- Live API: `GET /health` HTTP 200; `GET /openapi.json` HTTP 200 valid JSON; HSTS and standard API security headers present.

## Forge backend state
Live OpenAPI confirms these backend routes are deployed:
- `GET /agent-capabilities`
- `POST /agents/from-template`
- `POST /agents`
- `GET /agents/{agent_id}`
- `PATCH /agents/{agent_id}/config`
- `POST /agents/{agent_id}/run`
- `POST /agents/{agent_id}/deploy`
- `POST /workflows/{workflow_id}/run`
- `GET /dashboard/command-center`
- `GET /deployments/{deployment_id}/events`

Interpretation: Forge capability registry/templates, runtime bridge routes, full agent definitions, Command Center aggregate, and deployment events slice are all live as of commit `26aa8ab`. Product copy should stay honest: runtime bridges create/record backend work, but full autonomous worker behavior remains a later slice.

## Pump.fun payment state
- Pump.fun create/verify routes are live and auth-gated: `POST /payments/pumpfun/create`, `POST /payments/pumpfun/verify`.
- Controlled Pump.fun payment regression PASS is archived at [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]].
- Public tx: `2ydGT5uPArgKx2WkiBZ9xNm17ap6WB4BVznJTNwThDThS8qia6zT5vq76CHgEDFwW4gj7FfMyTHJweobt9K5UhrR`.
- Payment reference: `pumpfun:agentascendai:0967b710095e47bba1e12d4149639d9e`.
- Evidence showed: payment found, payment_id present, payment intent completed, verification_status verified, access grant present, listing-scoped true, marketplace entitlement present, and duplicate groups remained zero.
- Exact `tx_signature` binding hardening is implemented and deployed.
- Pump.fun helper runtime dependency is updated to `@pump-fun/agent-payments-sdk` 3.0.3.

## Replay-index and dependency state
- Replay-index preflight PASS is archived at [[raw/security-reviews/2026-05-02-replay-index-preflight]].
- DDL is not needed now because equivalent/target unique indexes/constraints already exist for payments, payment_intents, active grants, and marketplace entitlements.
- Node helper dev-only cleanup is complete: Vitest updated to 3.2.4.
- Runtime dependency audit still has remaining Pump.fun/Solana-chain advisories. They are accepted/monitored for now; do not run `npm audit fix` blindly.

## Scheduler and automation state
Enabled/audited production jobs:
- `default-backend-health-check`
- `default-integration-drift-check`
- `default-wiki-consistency-check`
- `default-todo-fixme-scan`
- `default-payment-route-audit`
- `default-failed-payment-replay-review`
- `default-access-grant-integrity-check`
- `default-task-queue-worker`

Disabled/held jobs:
- `default-telegram-status-summary`: report-only by default; no-send canary passed; outbound Telegram sends need separate owner approval.
- `default-roadmap-review`: placeholder/report-first; no model call; no file mutation; canary passed; enable only with owner approval.
- `default-git-status-summary`: fails closed safely when git is unavailable; production currently lacks git; keep disabled unless owner accepts sanitized unavailable reports.

Telegram recovery audit 2026-05-04 / Hermes cron no-send recovery audit: AgentAscend scheduler Telegram sends are intentionally off by default and production Telegram env/credential variables were missing by name-only inspection. Hermes cronjobs are a separate layer; nine Hermes cronjobs still target Telegram delivery, but recent runs mostly show execution errors before delivery. Keep AgentAscend scheduler Telegram disabled/report-only unless owner approves env setup and a one-message no-secret canary. Prefer recovering owner-facing Telegram reports through Hermes cron/gateway after fixing cron execution reliability.

Hermes multi-agent automation policy: use specialized report-first agents for Release/Ops, Backend Forge, Frontend/v0, Payment/Access, Scheduler/Automation, Docs/Memory, QA/Security, and Marketing/Community. Every agent must verify current state, use bounded smallest-safe slices, and stop before push, deploy, DB mutation, scheduler state changes, payment actions, access/entitlement changes, or external messages unless explicitly approved. Local swarm operating docs exist in commit `99f811a` on top of runtime-worker commit `6aac0e3`; neither is pushed as long as origin/main remains `1bb536a`. Pushing main would push both unless the owner approves a split/cherry-pick or first resolves runtime-worker queued/running task risk.

Do not change scheduler jobs, run `/jobs/run-due`, or run payment/scheduler canaries without explicit approval.

## Frontend/product state
The logged-in frontend is the biggest product bottleneck. Many `/app` pages remain placeholder-heavy or only partially wired to backend truth: overview, agents, deployments, workflows, tasks, outputs, executions, token, community, and settings. Next product work should be v0/frontend polish around live Forge/backend routes and live dashboard contracts. No fake localStorage unlock/payment/access/settings persistence.

## Current next recommended phases
1. Frontend/v0 implementation against live backend truth: Forge agent creation/config/run/deploy, Command Center, deployment events, and placeholder cleanup.
2. Remaining backend gap slices one at a time only when a frontend contract needs them.
3. Multi-agent architecture setup after frontend/backend product contracts are clearer.
4. Continue docs/wiki/Obsidian cleanup in small batches; do not preserve stale phase-blocker language as current status.

## Safety rules that still matter
- Backend remains payment/access authority.
- Never print or commit secrets: DB URLs, private RPC URLs, auth tokens, cookies, private keys, seed phrases, signed transactions, raw payloads, or raw request/response bodies.
- Public tx signatures, public wallet addresses, and public payment references may be documented when already part of launch evidence.
- No production DB mutations, migrations, payment actions, scheduler changes, env changes, deploys, public posts, or account actions without explicit owner approval.
- Before project changes: read this file, verify git/live production state, keep commits isolated, and stage only intended files.
