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

## Current status
- Execution Ledger/Scheduler Ledger is production-enabled for the approved workload.
- The task queue worker is enabled and can process queued production tasks during natural scheduler runs.
- Deployment events backend slice is live: `GET /deployments/{deployment_id}/events`.
- Command Center backend aggregate is live: `GET /dashboard/command-center`.
- Workflow run QA confirmed the owner run-history surface works for a throwaway workflow: one UI run, followed by `GET /workflows/{workflow_id}/runs` returning HTTP 200 with one run.
- Full autonomous runtime worker behavior and full visual workflow graph editing remain later product/runtime slices.

## Recent Evidence
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/scheduler-runtime-audits/2026-05-02-task-worker-enablement|2026-05-02 task worker enablement canary]]
- Commit `26aa8ab` live OpenAPI verification for deployment events.
- Commit `34a8c21` Command Center backend slice.
- [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa|2026-05-09 workflow owner-isolation QA PASS]]

## Relationships
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Agent Architecture]]
- [[agent-execution-system]]
- [[workflow-orchestration]]
- [[current-project-state|Current Project State]]

## Next actions
- Wire frontend Command Center, workflow run-history detail, and deployment event UI to backend truth.
- Keep execution artifacts/logs sanitized; do not expose raw task body/output in docs or UI reports.
