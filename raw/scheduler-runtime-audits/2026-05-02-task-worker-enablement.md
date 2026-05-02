# 2026-05-02 Task Worker Scheduler Enablement

## Scope
Documentation record for the owner-approved enablement canary of `default-task-queue-worker`. This note records sanitized results only. No secrets, raw DB rows, raw metadata, raw payloads, raw task bodies, or raw task outputs are included.

## Result
PASS — `default-task-queue-worker` is enabled.

## Canary summary
- Exactly one scoped manual canary was run for `default-task-queue-worker`.
- `/jobs/run-due` was not called.
- Canary processed 0 tasks.
- Completed count was 0.
- Failed count was 0.
- Output count was 0.
- `output_ids` was absent from job metadata.
- Metadata was aggregate-only.
- The job remained disabled after canary until the explicit enablement step.

## Safety outcome
- No payment mutation occurred.
- No payment intent creation occurred.
- No access grant creation or revocation occurred.
- No marketplace entitlement mutation occurred.
- Protected aggregates were unchanged except for the expected scheduler run record.
- Production `/health` passed after enablement.
- Production `/openapi.json` passed after enablement.
- Railway `AgentAscend` passed.
- Railway `AgentAscend-Scheduler` passed.
- Sanitized logs showed no forbidden scheduler/payment/access markers.

## Current scheduler state

Enabled and audited:
- `default-backend-health-check`
- `default-integration-drift-check`
- `default-wiki-consistency-check`
- `default-todo-fixme-scan`
- `default-payment-route-audit`
- `default-failed-payment-replay-review`
- `default-access-grant-integrity-check`
- `default-task-queue-worker`

Still disabled / held:
- `default-telegram-status-summary`
- `default-git-status-summary`
- `default-roadmap-review`

## Task worker notes
- Task worker scheduler metadata is aggregate-only: `processed`, `completed`, `failed`, and `output_count`.
- `output_ids` has been removed from job metadata.
- `AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED` controls `create_task` background triggering separately from the scheduled job enabled state.
- Scheduled enablement of `default-task-queue-worker` can process real queued production tasks in future natural scheduler runs.

## Follow-up
Recommended next phase: audit the remaining held jobs one at a time, starting with a low-risk non-external job before any Telegram/status-message enablement. Keep `/jobs/run-due` out of scope unless separately approved.
