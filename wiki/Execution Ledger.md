---
type: wiki
project: AgentAscend
aliases:
  - Execution Ledger
  - Scheduler Ledger
---

# Execution Ledger

## Summary
The Execution Ledger records runtime events, artifacts, execution summaries, and scheduler run history for AgentAscend operations.

## Components
- Task records.
- Execution records.
- Output records and artifacts.
- Command Center aggregates.
- Scheduler/runtime event history.

## Current status
- Execution Ledger/Scheduler Ledger is production-enabled for the approved workload.
- Runtime-worker backend is live and can support the verified runtime loop.
- Workflow Run-History / Execution Trace UX production verification passed on 2026-05-17: PR #5 is merged/live at `a010a7aff8ec2358c21fe088ac87d5ede3144f2a`, `/app/workflows` and `/app/executions` are HTTP 200, backend health/OpenAPI are HTTP 200, execution trace preview/link markers are live, workflow run-history links to execution/task/output where backend data exists, and no raw `metadata_json` or `payload_json` rendering was introduced.
- Production Playwright follow-up QA on 2026-05-17 passed with polish caveat for throwaway signup → Ascend Forge create → exactly one visible Run Agent click → `POST /agents/{id}/run` HTTP 200 → task_id returned → no false failure → Pending/Running UI state → Latest Run drawer without reload → `Open Task` link to `/app/tasks?task_id=...` → Tasks/Executions/Outputs/Overview runtime state. Exact `Agent run queued` / toast action visibility remains optional polish, not a blocker.
- Live Playwright QA on 2026-05-13 passed with caveats for throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Output preview; focused runtime verification showed one task, one execution, and one output after UI Run Agent.
- The task queue worker is enabled and can process queued production tasks during natural scheduler runs.
- Deployment Events UX is merged/live separately from PR #4 at `ec4b59e68d7f26edeb43e8a48b122cfeff539fac`; PR #4 is separate from PR #5 Workflow Run-History / Execution Trace UX.
- Deployment events backend slice is live: `GET /deployments/{deployment_id}/events`.
- Command Center backend aggregate is live: `GET /dashboard/command-center`.
- Frontend tasks, executions, and workflows now need better detail/timeline UX rather than stale “backend integration required” copy; Output Library search/preview basics are live and browser-QA verified. Workflow owner-isolation QA passed on 2026-05-09: User A workflow create/save/read/run works, User B cross-user graph/run/runs access is blocked, and graph saves respect `{ nodes: [...] }`.
- Full visual workflow graph editing remains a later frontend/product slice; workflow run-history trace preview is live, so next workflow polish should focus on node configuration/labels or broader task/execution/output detail polish.

## Recent Evidence
- [[raw/frontend-qa/2026-05-17-run-agent-toast-drawer-followup-production-qa|2026-05-17 Run Agent toast/drawer follow-up QA PASS WITH POLISH CAVEAT]]
- [[raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass|2026-05-17 Workflow Run-History / Execution Trace UX live PASS]]
- [[raw/frontend-qa/2026-05-16-production-run-agent-click-path-pass-with-caveat|2026-05-16 production Run Agent UI click path QA PASS WITH CAVEAT]]
- [[raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats|2026-05-13 live Output Library and runtime QA PASS WITH CAVEATS]]
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/scheduler-runtime-audits/2026-05-02-task-worker-enablement|2026-05-02 task worker enablement canary]]
- Commit `26aa8ab` live OpenAPI verification for deployment events.
- Commit `34a8c21` Command Center backend slice.
- [[raw/frontend-qa/2026-05-07-logged-in-runtime-qa-pass-with-caveats|2026-05-07 logged-in runtime QA PASS WITH CAVEATS]]
- [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa|2026-05-09 workflow-builder owner-isolation QA PASS]]

## Notes
Execution artifact and output previews must remain sanitized in docs and UI reporting; do not archive raw task body/output or raw metadata/payload JSON.

## Relationships
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Agent Architecture]]
- [[agent-execution-system]]
- [[workflow-orchestration]]
- [[current-project-state|Current Project State]]

## Next actions
- Polish frontend task detail, execution detail, output detail, workflow node configuration UX, settings/token/community surfaces, and optional Run Agent success-toast persistence. Deployment Events UX, Workflow Run-History / Execution Trace UX, and Run Agent Latest Run `Open Task` navigation are live.
- Keep execution artifacts/logs sanitized; do not expose raw task body/output in docs or UI reports.
