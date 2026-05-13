---
type: wiki
project: AgentAscend
aliases:
  - Current Project State
---

# Current Project State

## Summary
AgentAscend is in a soft-launch/product-integration posture. The backend remains the source of truth for payment/access/runtime state. The core logged-in runtime loop is verified end-to-end in the deployed frontend, and future-path payment↔grant linkage hardening is deployed; next focus can return to runtime/product UI polish.

## Components
- Backend: FastAPI on Railway at the public API domain.
- Frontend: v0/Next.js on Vercel.
- Database: Railway Postgres for production persistence; local SQLite may still appear in report-only scheduler/cron audits.
- Scheduler: AgentAscend DB scheduler under systemd locally and Railway scheduler worker in production.
- Knowledge system: `MEMORY.md`, `raw/`, `wiki/`, `docs/`, `learning/`, `skills/`, and Obsidian `.obsidian/` metadata.

## Current production/status baseline — verified 2026-05-13
- Live frontend domain: `https://www.agentascend.ai`.
- Live API health: `GET https://api.agentascend.ai/health` returns HTTP 200 `{"status":"ok"}` in current checks.
- Live frontend post-deploy QA on 2026-05-11 passed route/header/CSP/Solana RPC/WSS/OpenAPI/private-read/bundle gates.
- Full signed-in functional UX QA on 2026-05-11 passed with caveats using a throwaway QA account: Ascend Forge create → Run Agent → Task → Execution → Output → UI/dashboard refresh.
- Payment↔grant linkage hardening commit `7cc1c6a986e1e2a1896b5e8e5b62b36917bccc70` is deployed; Railway AgentAscend and AgentAscend-Scheduler reported SUCCESS, live `/health` was HTTP 200, and `/openapi.json` was HTTP 200 valid JSON.
- Git safety: local `main` remains diverged/noisy and must not be pushed; use clean `origin/main` worktrees for scoped changes.

## Product status
- Runtime-worker backend is live.
- Runtime-aware frontend/source audit passed.
- Core runtime loop is verified in live deployed frontend: agent create, run, task, execution, output, dashboard/agents refresh.
- Workflow auth ownership backend is live; workflow-builder owner-isolation QA passed.
- `/app/workflows` partially-live baseline: create/save/read/run works for owner; cross-user access is blocked; graph save respects `{ nodes: [...] }`; full visual graph/editor features remain later.
- Pump.fun marketplace payment regression passed separately and Pump.fun code was not changed by the legacy linkage hardening; keep payment/wallet flow separate from routine UI polish.
- Frontend no longer appears blocked on backend integration for tasks, outputs, executions, agent creation/run, or workflow ownership basics.
- Remaining product work: workflow node configuration editing/labels, richer run-history detail, output search/export/bulk UX, deployment events/log-streaming UX, task/execution/output detail UX, and workflow execution UX.

## Current launch-risk watch
- Future-path payment↔grant linkage hardening is deployed for legacy `/payments/verify`: successful verifies now link completed payments, payment_intents, and existing grant creation more auditably.
- No production backfill was performed. Historical null-heavy linkage rows, if any, remain audit-only unless a future owner-approved cleanup/backfill occurs.
- No production payment/access/DB mutation should happen without explicit owner approval.

## Relationships
- [[AgentAscend]]
- [[Launch Readiness]]
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Execution Ledger]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[known-issues|Known Issues]]
- [[Roadmap]]

## Recent Evidence
- [[raw/frontend-qa/2026-05-11-full-signed-in-functional-ux-qa-pass|2026-05-11 full signed-in functional UX QA PASS WITH CAVEATS]]
- [[raw/system-cleanup/2026-05-12-project-cleanup-cronjob-review|2026-05-12 project cleanup and cronjob review]]
- [[raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup|2026-05-12 Hermes paused cronjob cleanup]]
- [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa|2026-05-09 workflow-builder owner-isolation QA PASS]]
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-12-payment-grant-linkage-tdd-report|2026-05-12 payment↔grant linkage TDD and deployment PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]

## Notes
- Keep launch-risk findings scoped: local read-only payment/access findings are not production facts until verified.
- Keep generated recurring reports out of git unless intentionally archived as evidence.
- Do not push or deploy from the diverged local `main` line.

## Next actions
1. Output search/export/bulk UX.
2. Richer workflow run-history/runtime detail.
3. Deployment events/log-streaming UX.
4. Local main cleanup after all useful work is ported.
5. Keep recurring generated reports out of git noise unless intentionally archived.
