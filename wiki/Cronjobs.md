---
type: wiki
project: AgentAscend
aliases:
  - Cronjobs
  - Scheduled Jobs
---

# Cronjobs

## Summary
Cronjobs are recurring operating loops for AgentAscend. They must remain report-first by default and must not mutate production systems, scheduler state, payments, access, or external messaging without explicit approval.

## Components
- Hermes cronjobs: managed by Hermes. After 2026-05-12 cleanup there are 11 active/healthy recurring jobs.
- AgentAscend DB scheduler jobs: product scheduler records run by the AgentAscend scheduler worker/systemd process.
- Telegram status summary: `default-telegram-status-summary`; enabled as a report/status job, but outbound-message risk remains gated by configured environment and owner approval.
- Task queue worker: enabled/audited production scheduler job that processes queued tasks and persists outputs; recent local runs processed zero queued tasks successfully.

## Active Hermes jobs — 2026-05-12
- `4472b9af1cce` — daily morning operator cycle — Telegram — OK.
- `9600858f2a1d` — backend health monitor — Telegram — OK.
- `3c6b73c24cf9` — daily evening audit cycle — Telegram — OK.
- `88c926f33ab3` — integration quality and test planning — Telegram — OK.
- `0402b231934b` — MVP readiness and local dev check — Telegram — OK.
- `7fede4bb3eb4` — MEMORY.md maintenance — Telegram — OK.
- `77986833403e` — swarm daily operator report — local — OK.
- `0d6d5816aee6` — swarm daily knowledge hygiene report — local — OK.
- `df768cdc7c99` — swarm backend/frontend contract report — local — OK.
- `afd8fa8cc7b9` — swarm weekly security/dependency report — local — OK.
- `5cf95fc08134` — weekly system hygiene and cronjob audit — local — OK.

## Retired Hermes jobs — 2026-05-12
The following paused-error jobs were removed because safer active report-only jobs cover their useful scope:
- `3e2c67fffbfe` — documentation gap scan.
- `af4423ba979c` — weekly strategy security and ecosystem scan.
- `c778a3e0a264` — weekly roadmap reprioritizer.

## AgentAscend DB scheduler state — 2026-05-12
Enabled/audited local scheduler jobs:
- `default-backend-health-check`
- `default-integration-drift-check`
- `default-wiki-consistency-check`
- `default-todo-fixme-scan`
- `default-payment-route-audit`
- `default-failed-payment-replay-review`
- `default-access-grant-integrity-check`
- `default-task-queue-worker`
- `default-telegram-status-summary`
- `default-git-status-summary`

Disabled/manual by design:
- `default-roadmap-review` — Premium Strategic/manual review gated.

## Notes
- Local systemd scheduler is active/enabled as `agentascend-scheduler.service` with one `run_scheduler.py` process observed on 2026-05-12.
- Do not call `/jobs/run-due`, run scheduler jobs manually, change scheduler enablement, or send Telegram canaries without owner approval.
- Keep generated report noise out of source control unless intentionally archived as evidence.

## Relationships
- [[scheduler|Scheduler]]
- [[Hermes]]
- [[Ops Runbook]]
- [[Agent Architecture]]
- [[Execution Ledger]]
- [[current-project-state|Current Project State]]

## Recent Evidence
- [[raw/system-cleanup/2026-05-12-project-cleanup-cronjob-review|2026-05-12 project cleanup and cronjob review]]
- [[raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup|2026-05-12 Hermes paused cronjob cleanup]]
