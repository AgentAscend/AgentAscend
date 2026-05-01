---
type: evidence
project: AgentAscend
date: 2026-04-27
status: archived
tags:
  - agentascend
  - scheduler-runtime
related:
  - "[[scheduler|Scheduler]]"
  - "[[Cronjobs]]"
  - "[[Execution Ledger]]"
  - "[[Ops Runbook]]"
---

Related: [[scheduler|Scheduler]], [[Cronjobs]], [[Execution Ledger]], [[Ops Runbook]]

# Dedicated Railway Scheduler Worker Service Plan (PLANNING ONLY)

Date: 2026-04-27
Status: Planning only (no execution performed)

Constraints respected in planning:
- No code changes
- No deploy executed
- No job execution triggered
- No DB mutations
- No job enable/disable changes
- No approval-gated job execution

---

## 1) `scripts/run_scheduler.py` existence and behavior

Verified file exists:
- `scripts/run_scheduler.py`

Behavior:
- Entrypoint calls `SchedulerService().run_forever()`.
- `SchedulerService.run_forever()` performs:
  1. `init_db()`
  2. poll loop (`scheduler_poll_seconds`, default 30)
  3. `run_due_jobs_once()` each cycle
  4. catches cycle exceptions and continues

---

## 2) Safe startup behavior assessment

Safe characteristics:
- Loop is resilient (`try/except` around each cycle).
- Global scheduler kill switch exists: `AGENT_RUNTIME_SCHEDULER_ENABLED` -> `scheduler_enabled` runtime config.
- Per-hour throttle exists: `AGENT_RUNTIME_MAX_JOB_RUNS_PER_HOUR` (default 20).
- Premium guard exists: premium jobs are skipped when `premium_model_requires_manual_approval=true` (default true).

Important startup caveat:
- With scheduler enabled and current backlog, due jobs can start immediately on first poll.

---

## 3) Manual/approval-gated job protections

Confirmed protections:
- `default-roadmap-review` seeded disabled (`enabled=0`) and metadata marks manual approval required.
- Scheduler logic also skips premium model jobs when manual premium approval guard is on.
- Therefore roadmap review will not auto-run under normal config.

---

## 4) Catch-up risk (dangerous immediate execution?)

Observed production state indicates backlog:
- 10 enabled jobs due.

Scheduler behavior:
- `run_due_jobs_once()` runs due jobs in priority order up to max/hour.

Risk:
- Not all jobs are read-only. `task_queue_worker` performs DB writes to tasks/outputs/logs.
- If max/hour remains high, writes could occur on first runtime window.

Guardrail strategy:
- Start worker with `AGENT_RUNTIME_SCHEDULER_ENABLED=false` first (smoke startup only).
- For first live run, enable scheduler with `AGENT_RUNTIME_MAX_JOB_RUNS_PER_HOUR=1` to constrain first-hour execution to a single highest-priority due job (read-only class in current queue ordering).

---

## 5) Required Railway env vars for scheduler worker

## Required
- `DATABASE_URL` (same production Postgres as web service; use Railway reference variable, not a copied literal secret)

## Strongly recommended
- `AGENT_RUNTIME_SCHEDULER_ENABLED=false` (initial smoke-start guard)
- `AGENT_RUNTIME_MAX_JOB_RUNS_PER_HOUR=1` (safe first-run throttle)
- `AGENT_RUNTIME_POLL_SECONDS=30`
- `AGENT_RUNTIME_PREMIUM_REQUIRES_APPROVAL=true`
- `EXECUTION_LEDGER_ENABLED=true`
- `SCHEDULER_EXECUTION_LEDGER_ENABLED=false` (keep ledger-write expansion off initially)
- `AGENTASCEND_HEALTH_URL=https://api.agentascend.ai/health`

## Optional (notifications)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

---

## 6) DB target decision

Worker should use the same production DB as web (`DATABASE_URL` in production env) so scheduler state (`scheduled_jobs`, `job_runs`, `executions`) remains consistent.

---

## 7) Exact Railway service setup command sequence (DO NOT RUN YET)

Note: Railway CLI can create/link service + set env vars. Start command configuration may require Railway UI service settings.

```bash
# 0) CLI path
export PATH="$HOME/.local/node/node-v22.13.1-linux-x64/bin:$PATH"

# 1) Precheck current services
railway service list --json

# 2) Create scheduler service linked to same repo, with disabled-first env
railway add \
  --service AgentAscend-Scheduler \
  --repo AgentAscend/AgentAscend \
  --variables "AGENT_RUNTIME_SCHEDULER_ENABLED=false" \
  --variables "AGENT_RUNTIME_MAX_JOB_RUNS_PER_HOUR=1" \
  --variables "AGENT_RUNTIME_POLL_SECONDS=30" \
  --variables "AGENT_RUNTIME_PREMIUM_REQUIRES_APPROVAL=true" \
  --variables "EXECUTION_LEDGER_ENABLED=true" \
  --variables "SCHEDULER_EXECUTION_LEDGER_ENABLED=false" \
  --variables "AGENTASCEND_HEALTH_URL=https://api.agentascend.ai/health" \
  --json

# 3) Set/confirm worker uses shared production DB reference
railway variable set DATABASE_URL='${{Postgres.DATABASE_URL}}' \
  --service AgentAscend-Scheduler --environment production

# 4) Ensure start command in Railway Service Settings is exactly:
#    python3 scripts/run_scheduler.py
#    (configure in UI if CLI cannot set start command directly)

# 5) Verify service and deployment status
railway service list --json
railway deployment list --service AgentAscend-Scheduler --environment production --limit 5 --json
```

---

## 8) Safe first-run strategy (DO NOT RUN YET)

Phase A — startup smoke (scheduler disabled)
1. Create service with `AGENT_RUNTIME_SCHEDULER_ENABLED=false`.
2. Confirm logs show process startup and no due-job execution lines.

Phase B — constrained first execution (requires explicit approval)
1. Flip only `AGENT_RUNTIME_SCHEDULER_ENABLED=true`.
2. Keep `AGENT_RUNTIME_MAX_JOB_RUNS_PER_HOUR=1` for first hour.
3. Monitor logs + DB metrics.
4. Confirm no approval-gated/premium job execution.
5. Confirm first executed job is low-risk read-only class.

Phase C — gradual ramp (requires explicit approval)
1. Raise max/hour stepwise (e.g., 1 -> 3 -> 10).
2. Continue monitoring for unexpected writes/errors.

---

## 9) Exact first-run monitoring commands (DO NOT RUN YET)

```bash
export PATH="$HOME/.local/node/node-v22.13.1-linux-x64/bin:$PATH"

# scheduler service logs
railway logs --service AgentAscend-Scheduler --environment production --lines 300

# web logs (ensure no API regression)
railway logs --service AgentAscend --environment production --lines 200

# deployment status
railway deployment list --service AgentAscend-Scheduler --environment production --limit 5 --json

# read-only DB verification from production container
railway ssh --service AgentAscend --environment production \
  "python3 - <<'PY'
import os, psycopg2
conn=psycopg2.connect(os.environ['DATABASE_URL']); cur=conn.cursor()
cur.execute(\"SELECT COUNT(*) FROM job_runs\"); print('job_runs_total', cur.fetchone()[0])
cur.execute(\"SELECT COUNT(*) FROM job_runs WHERE started_at::timestamptz >= NOW() - INTERVAL '1 hour'\"); print('job_runs_last_hour', cur.fetchone()[0])
cur.execute(\"SELECT COUNT(*) FROM scheduled_jobs WHERE enabled=1 AND next_run_at IS NOT NULL AND next_run_at::timestamptz <= NOW()\"); print('due_now', cur.fetchone()[0])
cur.execute(\"SELECT COUNT(*) FROM job_runs WHERE scheduled_job_id='default-roadmap-review'\"); print('roadmap_runs', cur.fetchone()[0])
cur.close(); conn.close()
PY"
```

---

## 10) Rollback plan (exact command)

Fast rollback command:
```bash
export PATH="$HOME/.local/node/node-v22.13.1-linux-x64/bin:$PATH"
railway variable set AGENT_RUNTIME_SCHEDULER_ENABLED=false --service AgentAscend-Scheduler --environment production
```

Hard stop fallback (if required):
```bash
railway service delete AgentAscend-Scheduler --environment production
```

---

## Is `scripts/run_scheduler.py` safe to use as-is?

Answer: **Conditionally yes**.
- Safe **with disabled-first startup + throttled first-run guardrails**.
- Not safe to start unguarded right now because 10 due jobs are backlogged and at least one handler (`task_queue_worker`) writes to DB.

---

## Key risks

1. Immediate backlog processing without throttle may execute write-capable jobs early.
2. Scheduler worker misconfiguration (missing DB/start command) could fail silently.
3. If guardrails are loosened too quickly, observability lag may hide side effects.

---

## Approval requirement

Yes. Approval is required before executing this plan because service creation/deployment and runtime activation are production-mutating operations.
