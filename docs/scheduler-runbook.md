# AgentAscend Scheduler Runbook

## Purpose
Operate and audit the AgentAscend DB-backed scheduler safely without accidentally enabling held jobs or mutating production state.

## Current production wording
Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved safe scheduler workload. Held scheduler jobs remain intentionally disabled and require separate scoped audits before enablement.

## Production services
- `AgentAscend`: Railway FastAPI web service.
- `AgentAscend-Scheduler`: Railway worker service running scheduler loop.
- `Postgres`: Railway production database.

## Approved safe enabled jobs
- Backend health check
- Frontend/backend integration drift check
- Wiki/Obsidian consistency check
- TODO/FIXME scan

## Held disabled jobs
- Payment route audit
- Failed payment/replay protection review
- Access grant integrity check
- Telegram status summary
- Task queue worker
- Git status/change summary
- AgentAscend roadmap review

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
- Do not enable held jobs.
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

## Held-job enablement process
Each held job requires a separate scoped audit before enablement:
1. Define exact job behavior and forbidden actions.
2. Review source code and tests.
3. Run local-only dry checks where possible.
4. Confirm output contains no secrets and no raw sensitive logs.
5. Confirm ledger behavior is report-first.
6. Get owner approval before changing production flags.
