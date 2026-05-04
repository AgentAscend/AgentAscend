---
type: wiki
project: AgentAscend
aliases:
  - Cronjobs
  - Scheduled Jobs
---

# Cronjobs

## Summary
Cronjobs and scheduler jobs should be report-first operating loops. They create summaries/findings and must not mutate payments, access, production DB, scheduler flags, or deployments without explicit owner approval.

## Current status
The production scheduler has eight enabled/audited jobs and three disabled/held jobs. See [[scheduler|Scheduler]] for the current job matrix.

## Safety posture
- Enabled payment-adjacent jobs are report/aggregate-oriented.
- Telegram status summary does not send externally by default.
- Roadmap review is placeholder/report-first and does not mutate files.
- Git status summary fails closed when git is unavailable.
- Do not call `/jobs/run-due` during docs or audit cleanup.

## Recent Evidence
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/scheduler-runtime-audits/2026-05-02-task-worker-enablement|2026-05-02 task worker enablement canary]]
- [[raw/cronjob-audits/2026-04-27T11-20-17Z|2026-04-27 cronjob audit]]

## Relationships
- [[scheduler|Scheduler]]
- [[Execution Ledger]]
- [[Ops Runbook]]
- [[Hermes]]
- [[Roadmap]]
