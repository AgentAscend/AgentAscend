---
type: wiki
project: AgentAscend
aliases:
  - Scheduler
---

# Scheduler

## Summary
The AgentAscend scheduler is a separate Railway worker using DB-backed scheduled jobs and job run records. Current posture is report-first and audited for the enabled workload.

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
- `default-telegram-status-summary`: report-only by default; no-send canary passed; outbound sends require separate owner approval.
- `default-roadmap-review`: placeholder/report-first; no model call; no file mutation; canary passed; enable only with owner approval.
- `default-git-status-summary`: fails closed safely when git is unavailable; production currently lacks git; keep disabled unless sanitized unavailable reports are acceptable.

## Current verified production
- `AgentAscend-Scheduler` Railway deployment: SUCCESS at `26aa8abca8bc5bcf8f12a25a5fb9a222f5576eaa`.
- Do not change scheduler job state, run scheduler jobs, or call `/jobs/run-due` during docs-only cleanup.

## Recent Evidence
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/scheduler-runtime-audits/2026-05-02-task-worker-enablement|2026-05-02 task worker enablement canary]]
- [[Cronjobs]]
- [[Execution Ledger]]

## Relationships
- [[Cronjobs]]
- [[Execution Ledger]]
- [[Ops Runbook]]
- [[current-project-state|Current Project State]]

## Superseded blockers
- “task_queue_worker disabled” is superseded by audited enablement.
- “Telegram status summary auto-sends” is superseded by report-only default with sends disabled.
- “git status job unsafe” is superseded by fail-closed behavior, but the job remains held because production lacks git.
