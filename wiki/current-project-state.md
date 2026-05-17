---
type: wiki
project: AgentAscend
aliases:
  - Current Project State
---

# Current Project State

## Summary
AgentAscend is in a soft-launch/product-integration posture. The backend remains the source of truth for payment/access/runtime state. The user-facing Run Agent path is now production verified from the visible UI; the next launch-risk investigation is payment↔grant ledger linkage/auditability, followed by continued runtime/product UI polish.

## Components
- Backend: FastAPI on Railway at the public API domain.
- Frontend: v0/Next.js on Vercel.
- Database: Railway Postgres for production persistence; local SQLite may still appear in report-only scheduler/cron audits.
- Scheduler: AgentAscend DB scheduler under systemd locally and Railway scheduler worker in production.
- Knowledge system: `MEMORY.md`, `raw/`, `wiki/`, `docs/`, `learning/`, `skills/`, and Obsidian `.obsidian/` metadata.

## Current production/status baseline — verified 2026-05-17
- Live frontend domain: `https://www.agentascend.ai`.
- Live API health: `GET https://api.agentascend.ai/health` returns HTTP 200 `{"status":"ok"}` in current checks.
- Live frontend post-deploy QA on 2026-05-11 passed route/header/CSP/Solana RPC/WSS/OpenAPI/private-read/bundle gates.
- Workflow Run-History / Execution Trace UX production verification on 2026-05-17 passed after AgentAscend-Web PR #5 merged to `origin/main` at `a010a7aff8ec2358c21fe088ac87d5ede3144f2a`: Vercel production success, `/app/workflows` HTTP 200, `/app/executions` HTTP 200, backend `/health` HTTP 200, backend `/openapi.json` HTTP 200 valid JSON, execution trace preview/link markers live, and no raw metadata/payload rendering or forbidden scheduler/admin/payment calls introduced.
- Deployment Events UX is separately merged/live from PR #4 at `ec4b59e68d7f26edeb43e8a48b122cfeff539fac`; PR #4 and PR #5 are separate successful slices and prior stale/mixed report references are resolved.
- Production Run Agent UI click-path QA on 2026-05-16 passed with caveat after AgentAscend-Web main included commit `0292142b39962c705069e3c5d6daf2fbf157622c`: throwaway signup → Ascend Forge create → visible Run Agent click → `POST /agents/{id}/run` HTTP 200 → Running/Pending UI → Tasks/Executions/Outputs/Overview runtime state. Exact `Agent run queued` toast was not observed.
- Live Output Library and signed-in runtime QA on 2026-05-13 passed with caveats using throwaway QA accounts: throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Output preview.
- Git safety: local `main` is diverged from `origin/main` (`ahead 8 / behind 8` observed 2026-05-12). Do not push/deploy without explicit reconciliation.

## Product status
- Runtime-worker backend is live.
- Runtime-aware frontend/source audit passed.
- User-facing Run Agent path is production verified from visible UI: throwaway signup, agent create, visible Run Agent click, backend run POST 200, Running/Pending state, task, execution, output, and overview runtime state.
- Workflow auth ownership backend is live; workflow-builder owner-isolation QA passed.
- `/app/workflows` production baseline: workflow ownership basics are live, create/save/read/run works for owner, cross-user access is blocked, graph save respects `{ nodes: [...] }`, and run-history now exposes execution trace preview plus links to execution/task/output where backend data exists. Full visual graph/editor features remain later.
- Pump.fun marketplace payment regression passed separately; keep payment/wallet flow separate from routine UI polish.
- Frontend no longer appears blocked on backend integration for tasks, outputs, executions, agent creation/run, Output Library preview/search basics, or workflow ownership basics.
- Output Library UX patch is live and browser-QA verified: backend output listing, local loaded-list search copy, disabled unsupported Export All/Load More, and backend output preview. Deployment Events UX and Workflow Run-History / Execution Trace UX are live. Run Agent UI click path is production verified; remaining Run Agent caveat is success-toast polish only. Payment, Pump.fun, and wallet flows were intentionally not tested in these frontend QA slices. Remaining product work: task/execution/output detail polish, settings/token/community polish, and optional throwaway QA cleanup planning if owner-approved.

## Current launch-risk watch
- 2026-05-11 read-only local DB/payment reports flagged completed payments without active grant linkage by `payment_id` and null-heavy grant linkage fields.
- Treat this as a payment/access auditability investigation until production-vs-local scope is confirmed and a TDD forward-invariant/backfill plan is approved.
- No production payment/access/DB mutation should happen without explicit owner approval.

## Notes
Throwaway QA resources from 2026-05-13 remain in production and require a separate owner-approved cleanup plan before deletion. Payment, Pump.fun, and wallet flows were intentionally not tested in that QA.

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
- [[raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass|2026-05-17 Workflow Run-History / Execution Trace UX live PASS]]
- [[raw/frontend-qa/2026-05-16-production-run-agent-click-path-pass-with-caveat|2026-05-16 production Run Agent UI click path QA PASS WITH CAVEAT]]
- [[raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats|2026-05-13 live Output Library and runtime QA PASS WITH CAVEATS]]
- [[raw/frontend-qa/2026-05-11-full-signed-in-functional-ux-qa-pass|2026-05-11 full signed-in functional UX QA PASS WITH CAVEATS]]
- [[raw/system-cleanup/2026-05-12-project-cleanup-cronjob-review|2026-05-12 project cleanup and cronjob review]]
- [[raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup|2026-05-12 Hermes paused cronjob cleanup]]
- [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa|2026-05-09 workflow-builder owner-isolation QA PASS]]
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]

## Next actions
1. Payment↔grant linkage investigation and local TDD hardening plan; verify production-vs-local scope before any data repair.
2. Next product slice can proceed: task/execution/output detail polish is the cleanest follow-up now that Deployment Events UX and Workflow Run-History / Execution Trace UX are live.
3. Settings/token/community polish, or a throwaway QA cleanup plan if owner approves production cleanup.
5. Keep recurring generated reports out of git noise unless intentionally archived.
