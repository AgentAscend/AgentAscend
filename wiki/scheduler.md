---
type: wiki
project: AgentAscend
aliases:
  - Scheduler
---

# Scheduler

## Summary
Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved scheduler workload. Three held scheduler jobs remain intentionally disabled and require separate scoped audits before enablement.

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
- Held jobs requiring separate audits:
  - Telegram status summary
  - git status summary
  - roadmap review

## What is working
- Approved scheduler workload is enabled for report-first checks and audited task processing.
- `default-task-queue-worker` is enabled after a 2026-05-02 owner-approved empty-queue canary that processed 0 tasks and caused no payment/access/marketplace mutation.
- Task worker scheduler metadata is aggregate-only (`processed`, `completed`, `failed`, `output_count`), and `output_ids` is removed from job metadata.
- `AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED` controls `create_task` background triggering separately from `scheduled_jobs.enabled`.
- Scheduled enablement of `default-task-queue-worker` can process real queued production tasks in future natural scheduler runs.
- Recent read-only audit reported 11 scheduled jobs total, 4 enabled, 0 due-now enabled jobs, 0 scheduler artifacts with `content_text`, and no orphan execution events/artifacts.
- Live backend health endpoint is ok.

## What is broken or unproven
- Remaining held scheduler jobs are intentionally disabled pending separate audits.
- Any scheduler flag/job change or manual run remains out of scope without explicit approval.
- Payment/security/tokenomics scheduler work needs Premium Strategic review before enablement.

## Next actions
- Preserve approved enabled workload and keep task worker queue behavior monitored.
- Audit remaining held jobs one at a time before enablement.
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

## 2026-05-02 Task Worker Enablement
- `default-task-queue-worker` is now enabled after an owner-approved scoped canary.
- Canary processed 0 queued tasks and completed successfully.
- Protected task/output/log/execution aggregates were unchanged except for the expected scheduler run record.
- Payment/access/marketplace aggregates were unchanged.
- Remaining held jobs stayed disabled: `default-telegram-status-summary`, `default-git-status-summary`, and `default-roadmap-review`.
- Production `/health`, `/openapi.json`, Railway `AgentAscend`, Railway `AgentAscend-Scheduler`, and sanitized logs passed after enablement.
- See [[raw/scheduler-runtime-audits/2026-05-02-task-worker-enablement|2026-05-02 Task Worker Enablement]].
