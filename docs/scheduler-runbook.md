# AgentAscend Scheduler Runbook

## Purpose
Operate and audit the AgentAscend DB-backed scheduler safely without accidentally enabling held jobs or mutating production state.

## Current production wording
Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved scheduler workload. Three held scheduler jobs remain intentionally disabled and require separate scoped audits before enablement.

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
- `default-git-status-summary`
- `default-roadmap-review`

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
Each held job requires a separate scoped audit before enablement:
1. Define exact job behavior and forbidden actions.
2. Review source code and tests.
3. Run local-only dry checks where possible.
4. Confirm output contains no secrets and no raw sensitive logs.
5. Confirm ledger behavior is report-first.
6. Get owner approval before changing production flags.
