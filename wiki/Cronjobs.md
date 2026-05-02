---
type: wiki
project: AgentAscend
aliases:
  - Cronjobs
  - Scheduled Jobs
---

# Cronjobs

## Summary
Cronjobs are report-first recurring AgentAscend operating loops. They should produce findings and summaries, not perform high-risk actions without approval.

## Key Current Status
Approved scheduler jobs are enabled, including the audited task queue worker; three held jobs remain intentionally disabled. No scheduler flags/jobs should change without explicit owner approval.

## Important Links
- [[scheduler|Scheduler]]
- [[Execution Ledger]]
- [[Ops Runbook]]
- [[Hermes]]
- [[Roadmap]]

## Recent Evidence
- 2026-05-02: [[raw/scheduler-runtime-audits/2026-05-02-task-worker-enablement|Task worker scheduler enablement canary]] passed with 0 tasks processed and no payment/access/marketplace mutation.
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-29-0400]]
- [[raw/cronjob-audits/2026-04-27T11-20-17Z|2026-04-27 Cronjob Audit]].
- [[raw/cronjob-repair-report/2026-04-27T11-20-17Z|2026-04-27 Cronjob Repair Report]].

## Open Questions / Next Steps
- Audit remaining held jobs before enablement: `default-telegram-status-summary`, `default-git-status-summary`, and `default-roadmap-review`.
- Do not call /jobs/run-due or manually run scheduler jobs during docs/preflight phases.
- Keep token/payment/security jobs gated by Premium Strategic review.
