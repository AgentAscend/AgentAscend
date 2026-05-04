# AgentAscend Scheduler Safety

## When to use
Use before scheduler, cronjob, job-run, task-worker, Telegram summary, roadmap review, or git-status work.

## Hard boundaries
- Do not change job state, run jobs, call `/jobs/run-due`, mutate DB, or change Railway variables without explicit owner approval.
- Do not enable outbound Telegram sends without separate approval.
- Do not expose raw job metadata, raw task bodies, raw task output, tokens, DB URLs, or secrets.

## Current posture
Enabled/audited jobs:
- default-backend-health-check
- default-integration-drift-check
- default-wiki-consistency-check
- default-todo-fixme-scan
- default-payment-route-audit
- default-failed-payment-replay-review
- default-access-grant-integrity-check
- default-task-queue-worker

Held jobs:
- default-telegram-status-summary: report-only/no-send default; safe to enable later only as approved.
- default-roadmap-review: placeholder/report-first; no model/file mutation; approval required.
- default-git-status-summary: fails closed; production lacks git; keep disabled unless owner accepts unavailable reports.

## Evidence
See [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture]].
