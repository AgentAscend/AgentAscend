# AgentAscend scheduler runtime

The scheduler is a separate persistent worker. It should not run inside the FastAPI web process.

## Railway process split

Use two Railway services/processes from the same repo:

- web: FastAPI API service
  - example command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- worker: scheduler service
  - command: `python3 scripts/run_scheduler.py`

The web process serves HTTP routes. The worker process is the clock that loads enabled due jobs from SQLite and records every execution in `job_runs`.

## Required runtime admin token

`/jobs` routes must be protected outside explicit safe local development.

Set this as an environment variable in production/Railway:

```bash
AGENT_RUNTIME_ADMIN_TOKEN=[REDACTED]
```

Requests to `/jobs` must include:

```http
X-Agent-Runtime-Token: [REDACTED]
```

If `AGENT_RUNTIME_ADMIN_TOKEN` is missing in production/Railway, `/jobs` fails closed.

Local development may access `/jobs` without the token only when:

- `APP_ENV`/`ENV`/`RAILWAY_ENVIRONMENT` is not production/Railway,
- `safe_mode=true`, and
- the request comes from a local/private client.

## Telegram summaries

Do not commit Telegram secrets.

Scheduler-originated Telegram summaries are attempted only when both variables are set:

```bash
TELEGRAM_BOT_TOKEN=[REDACTED]
TELEGRAM_CHAT_ID=[REDACTED]
```

If either is missing, the Telegram summary job records a finding instead of crashing the scheduler.

## Health URL

Backend health checks use:

1. `AGENTASCEND_HEALTH_URL` when set.
2. Otherwise `backend_base_url` from `backend/app/config/agent_runtime.yaml` plus `/health`.
3. Default fallback: `http://127.0.0.1:8000/health`.

The active URL is stored in each health job run metadata.

## Hermes execution policy

Jobs remain report-first for now.

Allowed now:

- findings
- summaries
- safe read-only checks
- suggested jobs

Not allowed yet:

- destructive Hermes CLI actions
- autonomous commits
- autonomous deploys
- payment/security/tokenomics rewrites
- autonomous premium strategic decisions

Spawned jobs are disabled by default unless explicitly approved/configured. High-risk and premium actions require manual approval.
