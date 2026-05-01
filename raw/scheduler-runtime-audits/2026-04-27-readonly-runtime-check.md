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

# Production Scheduler Runtime Verification (READ-ONLY)

Date: 2026-04-27
Target commit: `b65257d4365c66b3de45e2bb7f4d39b52653343b`
Mode: Read-only verification only (no code changes, no deploy, no job toggles, no DB mutation, no approval-gated execution)

## Executive result

`job_runs_since_commit = 0` and `job_runs_failed_since_commit = 0` are explained by scheduler runtime not currently active in production after the latest web deploy.

---

## Evidence collected

## 1) Is scheduler worker/process running in production?

- Railway service inventory shows only:
  - `AgentAscend` (web)
  - `Postgres`
- No `AgentAscend-Scheduler` (or equivalent scheduler worker service) exists.
- Inside running production container, PID 1 command line is:
  - `/app/.venv/bin/python /app/.venv/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8080`
- This confirms web-only runtime in production container.

Conclusion: no dedicated scheduler process currently running in production.

---

## 2) Railway services/processes related to scheduler/worker

- `railway service list --json` confirms absence of scheduler worker service.
- Latest successful deployment (`a0898b18-34cb-4008-92e0-d699464f33c6`) start command is web-only uvicorn.
- No Railway service configured with `python3 scripts/run_scheduler.py`.

Conclusion: scheduler is not deployed as separate worker in current production topology.

---

## 3) Scheduler logs since commit `b65257d`

- Production logs for `AgentAscend` show web startup and HTTP traffic only.
- No scheduler-loop signatures present:
  - no `AgentAscend scheduler started`
  - no `Ran X due job(s)`
  - no `Scheduler cycle error`

Conclusion: no scheduler runtime activity observed post-commit in production logs.

---

## 4) Are scheduled jobs due but not executing?

Read-only DB checks (production Postgres):
- `scheduled_jobs_total = 11`
- `scheduled_jobs_enabled = 10`
- `scheduled_jobs_due_now = 10`
- Many enabled jobs have stale `next_run_at` in the past (e.g., 2026-04-26 / early 2026-04-27 UTC).

`job_runs` checks:
- `job_runs_total = 16`
- Most recent `started_at` observed: `2026-04-27T03:43:53+00:00`
- No runs recorded after commit/deploy window.

Conclusion: jobs are due and backlogged, but no scheduler process is advancing them.

---

## 5) Is scheduler disabled by env/config?

Environment flags in running web container:
- `EXECUTION_LEDGER_ENABLED = true`
- `SCHEDULER_EXECUTION_LEDGER_ENABLED = false`
- `AGENT_RUNTIME_SCHEDULER_ENABLED` not set

Code-level runtime facts:
- Scheduler loop lives in `scripts/run_scheduler.py` / `SchedulerService.run_forever()`.
- Web app startup (`backend/app/main.py`) only runs `init_db()` and router setup; it does not start scheduler loop.

Interpretation:
- Main blocker is missing scheduler runtime process.
- `SCHEDULER_EXECUTION_LEDGER_ENABLED=false` affects ledger linkage behavior, not whether scheduler loop exists.

---

## 6) Scheduler inside backend web service vs separate worker?

Observed current reality:
- Web service is uvicorn-only.
- Scheduler not embedded in web startup path.
- No separate scheduler service currently deployed.

Conclusion: scheduler runs neither in web process nor separate worker at this moment.

---

## 7) Are job_runs writing to expected production DB?

- Production checks were executed inside web runtime with its live `DATABASE_URL`.
- `scheduled_jobs`, `job_runs`, and `executions` tables all present and populated.
- `executions` has `source_type='scheduled_job_run'` entries (count = 2), matching historical scheduler-linked activity.

Conclusion: when scheduler runs, it writes to the expected production DB. Current issue is runtime absence, not DB misrouting.

---

## 8) Timezone/schedule timing explanation?

- DB `NOW()` is UTC; container timezone reports UTC.
- Cron/interval timestamps in DB are UTC ISO strings.
- `scheduled_jobs_due_now=10` proves this is not merely a timezone mismatch.

Conclusion: timezone does not explain zero post-commit runs.

---

## Likely reason no post-commit runs are recorded

Primary cause: no active scheduler runtime in production after latest deploy (no scheduler worker service and no in-process scheduler in web app), while jobs remain enabled and due.

---

## Health classification

- Web/API health: healthy.
- Scheduler subsystem: degraded/backlogged.
- Classification: **BLOCKER for scheduled automation**, but **not an immediate web-uptime blocker**.

---

## Exact recommended next command/action (safe, read-only first)

1) Confirm service topology (already indicates missing scheduler service):
```bash
export PATH="$HOME/.local/node/node-v22.13.1-linux-x64/bin:$PATH"
railway service list --json
```

2) If you approve provisioning scheduler worker (non-read-only operational change), perform UI-assisted creation of `AgentAscend-Scheduler` with start command:
```bash
python3 scripts/run_scheduler.py
```
and keep disabled-first guardrails per your rollout policy.

---

## Items requiring your approval

Required approval before any change action:
1. Create/deploy a dedicated Railway scheduler worker service.
2. Any subsequent enablement/tuning actions for scheduler runtime flags or due-job catch-up strategy.

No mutation was performed in this verification pass.
