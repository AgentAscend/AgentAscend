# AgentAscend Scheduler Runbook

## Purpose
Operate and audit the AgentAscend DB-backed scheduler safely without accidentally enabling held jobs or mutating production state.

## Current production wording
Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved scheduler workload. Current posture is report-first: eight jobs are enabled/audited, and three held jobs remain disabled after scoped audits/patches unless separately approved.

## Production services
- `AgentAscend`: Railway FastAPI web service.
- `AgentAscend-Scheduler`: Railway worker service running scheduler loop.
- `Postgres`: Railway production database.

## Enabled and audited jobs
- `default-backend-health-check`
- `default-integration-drift-check`
- `default-wiki-consistency-check`
- `default-todo-fixme-scan`
- `default-payment-route-audit`
- `default-failed-payment-replay-review`
- `default-access-grant-integrity-check`
- `default-task-queue-worker`

## Held disabled jobs
- `default-telegram-status-summary`
  - patched report-only by default at commit `31642a0ed52d8172759561eb5fe2788fe16745dc`
  - no-send canary passed with `mode=report_only`, `external_message_sent=false`, `send_enabled=false`
  - safe to enable later only as report-only unless outbound sending receives separate owner approval
  - outbound sends require `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED=true`
- `default-git-status-summary`
  - patched to fail closed safely when git is unavailable
  - production currently lacks git
  - keep disabled unless owner accepts sanitized failed/unavailable reports
- `default-roadmap-review`
  - placeholder/report-first
  - no model call or file mutation
  - canary passed and safe to enable later with owner approval

## Read-only audit commands
Do not run jobs manually.

```bash
export PATH="$HOME/.local/node/node-v22.13.1-linux-x64/bin:$PATH"
railway service list --json
railway variable list --service AgentAscend-Scheduler --environment production --json
curl -fsS https://api.agentascend.ai/health
```

When inspecting variables, print only safe presence/categories:
- scheduler flags may print true/false
- `DATABASE_URL`: print SET/MISSING only
- RPC/API secrets: print SET/MISSING only; never print values

## Read-only DB audit shape
Use a read-only Postgres session. Aggregate only; do not print raw metadata, raw job output summaries, raw errors, tokens, DB URLs, or secrets.

Useful aggregate checks:
- scheduled job names and enabled flags
- enabled job count
- due-now enabled job count
- total job runs
- recent job run names/status/timestamps only
- executions where `source_type='scheduled_job_run'`
- scheduler artifacts count through execution join
- scheduler artifacts with non-empty `content_text`
- orphan execution events/artifacts

## Safety rules
- Do not call `/jobs/run-due` during audits.
- Do not modify scheduler flags.
- Do not enable held jobs without explicit owner approval and scoped canary.
- Do not disable approved jobs unless explicitly instructed.
- Do not deploy or redeploy scheduler from an audit pass.
- Do not run `scripts/run_scheduler.py` manually against production.
- Do not mutate production DB rows.

## Current 2026-04-29 read-only findings
- Railway services present and latest deployment state was reported as SUCCESS for `AgentAscend`, `AgentAscend-Scheduler`, and `Postgres`.
- Scheduler worker has runtime flags set true for natural scheduler and scheduler ledger operation.
- Production DB showed 11 scheduled jobs total, 4 enabled.
- Due-now enabled job count was 0 during audit.
- Recent job runs were successful backend health checks.
- Scheduler artifacts count was 0 and content_text count was 0.
- Orphan execution events/artifacts count was 0.

## Current 2026-05-02 final scheduler posture
- Enabled/audited jobs:
  - `default-backend-health-check`
  - `default-integration-drift-check`
  - `default-wiki-consistency-check`
  - `default-todo-fixme-scan`
  - `default-payment-route-audit`
  - `default-failed-payment-replay-review`
  - `default-access-grant-integrity-check`
  - `default-task-queue-worker`
- Disabled/held jobs:
  - `default-telegram-status-summary`
  - `default-git-status-summary`
  - `default-roadmap-review`
- Payment-adjacent jobs are report-first/aggregate-only where applicable:
  - `default-payment-route-audit`
  - `default-failed-payment-replay-review`
  - `default-access-grant-integrity-check`
- `default-task-queue-worker` is enabled and can process real queued tasks if present.
- `AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED` controls `create_task` background triggering separately from scheduled job enabled state.
- `default-telegram-status-summary` is safe to enable later as report-only; do not enable outbound sends without separate owner approval.
- `default-roadmap-review` is safe to enable later as placeholder/report-first.
- `default-git-status-summary` should remain disabled unless sanitized unavailable reports are acceptable.

## Current 2026-05-02 task worker enablement findings
- `default-task-queue-worker` is enabled after an owner-approved scoped canary.
- Canary processed 0 tasks.
- Task worker scheduler metadata is aggregate-only: `processed`, `completed`, `failed`, and `output_count`.
- `output_ids` is removed from job metadata.
- `AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED` controls `create_task` background triggering separately from scheduled job enabled state.
- Scheduled enablement can process real queued production tasks in future natural scheduler runs.
- No payment/access/marketplace mutation occurred during enablement.
- Remaining held jobs stayed disabled: `default-telegram-status-summary`, `default-git-status-summary`, and `default-roadmap-review`.

## Held-job enablement process
Each held job requires separate owner approval before enablement:
1. Define exact job behavior and forbidden actions.
2. Review source code and tests.
3. Confirm any canary output contains no secrets and no raw sensitive logs.
4. Confirm ledger behavior is report-first and aggregate-only where applicable.
5. Confirm payment/access/marketplace deltas remain zero.
6. Get owner approval before changing production flags.

Known held-job conditions:
- `default-telegram-status-summary`: enable later only as report-only unless outbound Telegram sending receives separate owner approval and `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED=true` is intentionally configured.
- `default-roadmap-review`: enable later only as placeholder/report-first; no model/file mutation is expected.
- `default-git-status-summary`: keep disabled unless production git becomes available or owner accepts sanitized unavailable reports.
