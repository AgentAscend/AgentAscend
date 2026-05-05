---
type: wiki
project: AgentAscend
aliases:
  - Cronjobs
  - Scheduled Jobs
---

# Cronjobs

## Summary
Cronjobs are recurring operating loops for AgentAscend. They must be report-first by default and must not mutate production systems, scheduler state, payments, access, or external messaging without explicit approval.

## Components
- Hermes cronjobs: managed by Hermes; can deliver reports through the Hermes gateway. Current audit found nine scheduled Hermes cronjobs with Telegram delivery targets, but most recent runs show error status before delivery.
- AgentAscend DB scheduler jobs: production jobs stored in scheduler tables and run by the AgentAscend-Scheduler service.
- Telegram status summary: `default-telegram-status-summary`; report-only by default and held unless owner approves enablement/sends.
- Task queue worker: enabled/audited production scheduler job that can process queued tasks.

## Relationships
- [[scheduler|Scheduler]]
- [[Hermes]]
- [[Ops Runbook]]
- [[Agent Architecture]]
- [[Execution Ledger]]

## Notes
Telegram stopped for two distinct reasons depending on layer: AgentAscend scheduler Telegram sends are intentionally disabled/report-only with missing send env vars, while Hermes cronjobs currently appear to be failing during job execution/provider/network handling before final Telegram delivery. Do not call `/jobs/run-due`, run scheduler jobs, or send Telegram messages during diagnosis.


Hermes cron recovery note: nine Hermes cronjobs target Telegram delivery, but recent errors show `cannot import name cfg_get from hermes_cli.config` and no delivery error, so diagnose Hermes execution/import state before testing Telegram delivery. Do not run jobs or send canaries without owner approval.
