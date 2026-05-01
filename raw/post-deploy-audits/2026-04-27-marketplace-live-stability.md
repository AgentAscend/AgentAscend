---
type: evidence
project: AgentAscend
date: 2026-04-27
status: archived
tags:
  - agentascend
  - post-deploy-audit
related:
  - "[[Launch Readiness]]"
  - "[[Ops Runbook]]"
  - "[[AgentAscend]]"
  - "[[known-issues|Known Issues]]"
---

Related: [[Launch Readiness]], [[Ops Runbook]], [[AgentAscend]], [[known-issues|Known Issues]]

# Post-Deploy Stability Audit — 2026-04-27 Marketplace Live Fix

## Scope
Audit executed after commit `b65257d4365c66b3de45e2bb7f4d39b52653343b` and successful Railway deploy.

Constraints respected:
- No code changes made
- No deploy triggered manually
- No approval-gated jobs executed

---

## 1) Cronjobs after latest deploy

### Hermes cron registry
Source: `cronjob(action='list')`
- Total jobs: **9**
- Enabled: **9**
- Last status: all with run history show `ok`
- Not yet run (still scheduled):
  - `0402b231934b` (MVP readiness/local dev check)
  - `af4423ba979c` (weekly strategy/security/ecosystem)

### Repo-local scheduler (SQLite)
Source: local `scheduled_jobs`/`job_runs`
- Total scheduled jobs: **11**
- Enabled: **10**
- Approval-gated disabled job: `default-roadmap-review` (`premium`, `requires_manual_approval=true`)
- Scheduler service: `agentascend-scheduler.service` is active/running (single process)

### Production DB scheduler snapshot (Railway Postgres)
Source: read-only query inside Railway web container
- `scheduled_jobs` table present
- `job_runs` table present
- `executions` table present
- Enabled scheduled jobs: **10**
- `job_runs_total`: **16**
- `job_runs_since_commit`: **0**
- `job_runs_failed_since_commit`: **0**

Observation: no production scheduler runs occurred after this commit window.

---

## 2) Required route checks

### Public/runtime routes
- `GET /health` → **200** ✅
- `GET /openapi.json` → **200** ✅
- `GET /marketplace/live` → **200** ✅
- `GET /marketplace/browse` → **200** ✅

### Payment-gated MVP route behavior (no real payment creation)
- `GET /users/real3/access` (no auth) → **401** (expected protected route) ✅
- `GET /users/real3/payments` (no auth) → **401** (expected protected route) ✅
- `POST /tools/random-number` with incomplete payload → **422** (input validation gate) ✅
- `POST /payments/create` with empty body → **422** (no payment intent created from invalid request) ✅
- `POST /payments/verify` with empty body → **422** (input validation gate) ✅

No real payment transaction or verification flow was executed.

---

## 3) Scheduler job history after commit `b65257d`

### Local DB
- Commit timestamp (UTC): `2026-04-27T11:25:41+00:00`
- `runs_since_commit`: **0**
- `failed_runs_since_commit`: **0**

### Production DB
- `job_runs_since_commit`: **0**
- `job_runs_failed_since_commit`: **0**

No new scheduler failures after the commit because no post-commit job executions were recorded in the queried windows.

---

## 4) Execution ledger linkage (`scheduled_job_run`)

- Local SQLite: `executions` entries with `source_type='scheduled_job_run'` = **0**
- Production Postgres: `executions` entries with `source_type='scheduled_job_run'` = **2**

Interpretation: linkage exists in production history, but there are no new linked entries after this commit because no scheduler runs were recorded post-commit.

---

## 5) Railway logs after successful deploy

Source: `railway logs --service AgentAscend --environment production --lines 400`
- Startup healthy
- `/health`, `/openapi.json`, `/marketplace/live`, `/marketplace/browse` requests logged as 200
- No `ERROR`, no `Traceback`, no `ValidationError`, no `500 Internal Server Error` found in captured post-deploy logs

Expected warning-class entries from audit probes:
- 401 for unauthorized protected routes
- 422 for intentionally incomplete POST payload checks

These were expected and non-breaking.

---

## Stability verdict
- Marketplace live regression appears resolved and stable in current checks.
- Core public routes healthy.
- No hidden runtime errors detected in post-deploy logs.
- No new scheduler failures after commit (but also no new scheduler runs recorded in production window).

---

## Recommended next safe fixes (non-mandatory)
1. **Scheduler observability check (safe, read-only first):** verify why production `job_runs_since_commit=0` and confirm whether scheduler worker is intentionally disabled/not running.
2. **Add a low-risk synthetic scheduler heartbeat job** (read-only) if missing, to make post-deploy scheduler liveness easier to verify.
3. **Keep approval-gated roadmap job disabled** unless explicitly approved.

---

## Items requiring your approval
1. If you want active production scheduler execution verified end-to-end, approve a read-only operator step to inspect/confirm Railway scheduler worker process/service state.
2. If you want scheduler ledger throughput increased, approve runtime-flag/worker changes (not done in this audit).

No urgent approval is required for the marketplace-live fix itself based on this audit.
