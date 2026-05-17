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
- Production Playwright QA on 2026-05-16 passed with caveat for throwaway signup → Ascend Forge create → visible Run Agent click → `POST /agents/{id}/run` HTTP 200 → Running/Pending UI state → Tasks/Executions/Outputs/Overview runtime state. Exact `Agent run queued` toast was not observed, but backend/frontend runtime propagation passed.
- Live Playwright QA on 2026-05-13 passed with caveats for throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Output preview; focused runtime verification showed one task, one execution, and one output after UI Run Agent.
- The task queue worker is enabled and can process queued production tasks during natural scheduler runs.
- Deployment events backend slice is live: `GET /deployments/{deployment_id}/events`.
- Command Center backend aggregate is live: `GET /dashboard/command-center`.
- Frontend tasks, executions, and workflows now need better detail/timeline UX rather than stale “backend integration required” copy; Output Library search/preview basics are live and browser-QA verified. Workflow owner-isolation QA passed on 2026-05-09: User A workflow create/save/read/run works, User B cross-user graph/run/runs access is blocked, and graph saves respect `{ nodes: [...] }`.
- Full visual workflow graph editing remains a later frontend/product slice; next workflow polish should focus on node configuration/labels and richer run-history detail.

## Recent Evidence
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
- Polish frontend Command Center, task detail, execution detail, workflow run-history/node configuration UX, deployment event/log-streaming UX, settings/token/community surfaces, and Run Agent success-toast copy.
- Keep execution artifacts/logs sanitized; do not expose raw task body/output in docs or UI reports.
