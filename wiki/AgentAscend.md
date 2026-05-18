---
type: wiki
project: AgentAscend
aliases:
  - AgentAscend
---

# AgentAscend

## Summary
AgentAscend is a monetized AI x Web3 agent platform. It combines backend-authoritative payments/access, Forge agent creation/runtime routes, marketplace entitlements, scheduler-ledger operations, and a v0 frontend that must be aligned to backend truth.

## Components
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[scheduler|Scheduler]]
- [[Execution Ledger]]
- [[Agent Architecture]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Hermes]]
- [[Roadmap]]

## Current status
- Production API is healthy at runtime-worker commit `5e7afb1`; workflow auth ownership hardening is live.
- Runtime-worker backend is live.
- Runtime-aware frontend/source audit passed.
- Workflow Run-History / Execution Trace UX production verification passed on 2026-05-17: PR #5 is merged/live at `a010a7aff8ec2358c21fe088ac87d5ede3144f2a`, `/app/workflows` and `/app/executions` are HTTP 200, backend health/OpenAPI are HTTP 200, execution trace preview/link markers are live, and no raw metadata/payload rendering or forbidden scheduler/admin/payment calls were introduced. Evidence is archived at [[raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass]].
- Deployment Events UX is separately merged/live from PR #4 at `ec4b59e68d7f26edeb43e8a48b122cfeff539fac`; PR #4 and PR #5 are separate successful slices and prior stale/mixed PR #4 references are resolved.
- Production Playwright follow-up QA on 2026-05-17 passed with polish caveat for the merged Run Agent toast/drawer path: throwaway signup → Ascend Forge create → exactly one visible Run Agent click → backend run POST 200 → task_id returned → no false failure → Pending/Running state → Latest Run drawer without reload → `Open Task` link to `/app/tasks?task_id=...` → Tasks/Executions/Outputs/Overview runtime state. Evidence is archived at [[raw/frontend-qa/2026-05-17-run-agent-toast-drawer-followup-production-qa]].
- Live Playwright QA on 2026-05-13 passed with caveats for the broader core loop and Output Library: throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Output preview. Evidence is archived at [[raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats]].
- Workflow-builder owner-isolation QA passed on 2026-05-09; User A create/save/read/run works, User B cross-user access is blocked with 403, graph saves respect `{ nodes: [...] }`, workflow copy is honest/partially-live, and no payment/scheduler/admin exposure occurred. Evidence is archived at [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa]].
- Pump.fun payment/access regression passed; Pump.fun payment flow remains separate from the next frontend polish phase.
- Forge backend routes are live through deployment events, Command Center, agent definitions, capabilities/templates, and run/deploy bridges.
- Scheduler workload is report-first/owner-gated.
- Output Library UX patch is live and browser-QA verified: backend output listing, local loaded-list search, disabled unsupported Export All/Load More, and backend output preview. Deployment Events UX and Workflow Run-History / Execution Trace UX are live. Run Agent runtime path and Latest Run `Open Task` navigation are production verified; exact success toast/action visibility remains optional polish. Frontend product work now shifts to task/execution/output detail polish, settings/token/community polish, and optional throwaway QA cleanup planning. Full visual workflow graph editing is not live yet.

## Notes
- Backend remains the authority for payment, access, marketplace entitlements, tasks, outputs, executions, and agents.
- ASND utility should be grounded in real platform usage, not price or return promises.
- Multi-agent architecture remains planning until frontend/backend contracts are clearer.

## Relationships
- [[current-project-state|Current Project State]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Execution Ledger]]
- [[known-issues|Known Issues]]
- [[Launch Readiness]]

## Recent Evidence
- [[raw/frontend-qa/2026-05-17-run-agent-toast-drawer-followup-production-qa|2026-05-17 Run Agent toast/drawer follow-up QA PASS WITH POLISH CAVEAT]]
- [[raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass|2026-05-17 Workflow Run-History / Execution Trace UX live PASS]]
- [[raw/frontend-qa/2026-05-16-production-run-agent-click-path-pass-with-caveat|2026-05-16 production Run Agent UI click path QA PASS WITH CAVEAT]]
- [[raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats|2026-05-13 live Output Library and runtime QA PASS WITH CAVEATS]]
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/security-reviews/2026-05-02-node-helper-dependency-audit|2026-05-02 Node helper dependency audit baseline]]
- [[raw/frontend-qa/2026-05-07-logged-in-runtime-qa-pass-with-caveats|2026-05-07 logged-in runtime QA PASS WITH CAVEATS]]
- [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa|2026-05-09 workflow-builder owner-isolation QA PASS]]
- Commits: `239fa79` dev dependency cleanup, `a8ad3ba` Pump.fun SDK 3.0.3, `2d00a31` controlled regression evidence, `5ac6d06` Forge definitions, `34a8c21` Command Center, `{prod_short}` deployment events.
