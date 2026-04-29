# Scheduler

## Summary
Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved safe scheduler workload. Held scheduler jobs remain intentionally disabled and require separate scoped audits before enablement.

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
- Held jobs requiring separate audits:
  - payment route audit
  - failed payment replay review
  - access grant integrity check
  - Telegram status summary
  - task queue worker
  - git status summary
  - roadmap review

## What is working
- Approved safe scheduler workload is enabled for report-first checks.
- Recent read-only audit reported 11 scheduled jobs total, 4 enabled, 0 due-now enabled jobs, 0 scheduler artifacts with `content_text`, and no orphan execution events/artifacts.
- Live backend health endpoint is ok.

## What is broken or unproven
- Held scheduler jobs are intentionally disabled pending separate audits.
- Any scheduler flag/job change or manual run remains out of scope without explicit approval.
- Payment/security/tokenomics scheduler work needs Premium Strategic review before enablement.

## Next actions
- Preserve approved safe workload only.
- Audit held jobs one at a time before enablement.
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
