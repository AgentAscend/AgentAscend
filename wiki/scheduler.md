---
type: wiki
project: AgentAscend
aliases:
  - Scheduler
---

# Scheduler

## Summary
The AgentAscend scheduler is a separate Railway worker using DB-backed scheduled jobs and job run records. It is production-live and currently runs an audited enabled set, with external-message and placeholder jobs held.

## Components
- Railway service: `AgentAscend-Scheduler`.
- Scheduler tables: scheduled jobs and job runs.
- Execution Ledger integration for scheduler runs.
- Task queue worker for production queued tasks.

## Current verified production — 2026-05-07
- `AgentAscend-Scheduler`: SUCCESS at commit `712c05e`, deployment `c2f213a7`.
- Recent runs show natural scheduler activity, including frequent successful task queue worker runs.
- Do not manually run scheduler jobs or call `/jobs/run-due` during docs/audit cleanup.

## Enabled / audited jobs
- `default-backend-health-check`
- `default-integration-drift-check`
- `default-wiki-consistency-check`
- `default-todo-fixme-scan`
- `default-payment-route-audit`
- `default-failed-payment-replay-review`
- `default-access-grant-integrity-check`
- `default-task-queue-worker`

## Disabled / held jobs
- `default-telegram-status-summary`: report-only by default; outbound sends require separate owner approval.
- `default-roadmap-review`: placeholder/report-first; enable only with owner approval.
- `default-git-status-summary`: fails closed when git is unavailable; keep held unless unavailable reports are acceptable.

## Relationships
- [[Cronjobs]]
- [[Execution Ledger]]
- [[Ops Runbook]]
- [[current-project-state|Current Project State]]
- [[Hermes]]

## Notes
`default-task-queue-worker` can mutate task/output/execution state by processing real queued production tasks. It is audited/live, but do not run manual canaries without explicit approval.
