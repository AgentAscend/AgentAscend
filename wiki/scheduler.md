---
type: wiki
project: AgentAscend
aliases:
  - Scheduler
---

# Scheduler

## Summary
Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved scheduler workload. The current scheduler posture is report-first: eight jobs are enabled/audited, and three held jobs remain disabled after scoped audits/patches unless the owner separately approves enablement.

## Components
- Scheduler runtime:
  - `scripts/run_scheduler.py`
  - `scripts/job_admin.py`
  - `backend/app/services/scheduler_service.py`
  - `backend/app/services/job_runner.py`
- Execution ledger surfaces:
  - execution events
  - execution artifacts
  - scheduler run history
- Approved safe workload:
  - backend health check
  - frontend/backend integration drift check
  - wiki/Obsidian consistency check
  - TODO/FIXME scan
  - payment route audit
  - failed payment replay review
  - access grant integrity check
  - task queue worker
- Held jobs requiring separate owner-approved enablement:
  - Telegram status summary: patched report-only by default, no-send canary passed, safe to enable later only with outbound sends disabled unless separately approved.
  - git status summary: patched to fail closed safely, production git unavailable, keep disabled unless sanitized unavailable reports are acceptable.
  - roadmap review: placeholder/report-first, no model/file mutation, canary passed and safe to enable later.

## What is working
- Approved scheduler workload is enabled for report-first checks and audited task processing.
- `default-task-queue-worker` is enabled after a 2026-05-02 owner-approved empty-queue canary that processed 0 tasks and caused no payment/access/marketplace mutation.
- Task worker scheduler metadata is aggregate-only (`processed`, `completed`, `failed`, `output_count`), and `output_ids` is removed from job metadata.
- `AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED` controls `create_task` background triggering separately from `scheduled_jobs.enabled`.
- Scheduled enablement of `default-task-queue-worker` can process real queued production tasks in future natural scheduler runs.
- Recent read-only audit reported 11 scheduled jobs total, 4 enabled, 0 due-now enabled jobs, 0 scheduler artifacts with `content_text`, and no orphan execution events/artifacts.
- Live backend health endpoint is ok.

## What is broken or unproven
- Remaining held scheduler jobs are intentionally disabled after scoped audits/patches; enablement still requires explicit owner approval.
- Outbound Telegram status summary sends are disabled by default and require `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED=true` plus separate owner approval.
- Production git status reports currently fail/unavailable because git is not available in the production runtime; keep disabled unless that sanitized failed report is desired.
- Any scheduler flag/job change or manual run remains out of scope without explicit approval.
- Payment/security/tokenomics scheduler work needs Premium Strategic review before enablement.

## Next actions
- Preserve approved enabled workload and keep task worker queue behavior monitored.
- If desired, enable `default-telegram-status-summary` later as report-only with outbound sends still disabled; do not enable outbound sends without separate owner approval.
- If desired, enable `default-roadmap-review` later as placeholder/report-first.
- Keep `default-git-status-summary` disabled unless owner accepts sanitized unavailable/failure reports from production.
- Do not run `/jobs/run-due` or manually trigger scheduler jobs during docs-only phases.
- Keep scheduler reporting separated from payment/access enforcement changes.

## Relationships
- [[Auth]]
- [[Database]]
- [[Deployment]]
- [[Marketplace]]
- [[Tasks Outputs]]
- [[Known Issues]]
- [[Roadmap]]

## Safety notes
- No duplicate tmux/nohup schedulers.
- No destructive jobs or premium/security decisions without approval.
- Do not change scheduler flags/jobs or run scheduler jobs without explicit approval.

## Notes
This page was updated during the 2026-04-29 post-audit knowledge curation. Treat source-level facts separately from live-production verification.

## 2026-04-30 Knowledge Graph Status Update
- Raw launch evidence, tokenized-agent, scheduler/cronjob, deploy-readiness, security, and Hermes runtime notes now link back to this hub graph.
- Exact Pump.fun `tx_signature` binding hardening is implemented and deployed at commit `453df65aec69f7aa95b20bb1752f7d3af97ad488`.
- Replay-index migration remains pending and must not be run without owner approval.
- Node dependency audit remains pending as a separate hardening phase.

## Recent Evidence
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-29-0400]]

## 2026-05-02 Final Scheduler Posture
- Enabled/audited jobs: `default-backend-health-check`, `default-integration-drift-check`, `default-wiki-consistency-check`, `default-todo-fixme-scan`, `default-payment-route-audit`, `default-failed-payment-replay-review`, `default-access-grant-integrity-check`, and `default-task-queue-worker`.
- Held disabled jobs: `default-telegram-status-summary`, `default-git-status-summary`, and `default-roadmap-review`.
- `default-telegram-status-summary` is report-only by default behind `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED=false`; commit `31642a0ed52d8172759561eb5fe2788fe16745dc` deployed successfully and the no-send canary passed with no protected deltas.
- `default-roadmap-review` is a safe placeholder/report-first job with no model or file mutation and can be enabled later with owner approval.
- `default-git-status-summary` fails closed safely when git is unavailable; production currently lacks git, so keep it disabled unless sanitized unavailable reports are acceptable.
- See [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 Final Scheduler Posture]].
