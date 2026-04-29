# Backend Runbook

## Scope
Canonical local/ops run steps for AgentAscend backend and scheduler worker.

## Prerequisites
- Python virtual environment available at `.venv`
- Dependencies installed for backend
- Project root: `/home/agentascend/projects/AgentAscend`

## Required environment variables (redacted)
Minimum expected in production-like runs:
- `SOLANA_RPC_URL`
- `SOLANA_RECEIVER_WALLET`
- `ASND_MINT_ADDRESS`
- `JWT_SECRET_KEY`
- `AGENT_RUNTIME_ADMIN_TOKEN` (for `/jobs` protection)

Optional but common:
- `DATABASE_URL` (Railway Postgres)
- `APP_ENV` / `ENV`
- `TELEGRAM_BOT_TOKEN` (if Telegram summaries enabled)
- `TELEGRAM_CHAT_ID`

Never commit secret values.

## Start API (local)
```bash
cd /home/agentascend/projects/AgentAscend
PYTHONPATH=. .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Start scheduler worker (separate process)
```bash
cd /home/agentascend/projects/AgentAscend
PYTHONPATH=. .venv/bin/python scripts/run_scheduler.py
```

Do not run scheduler inside the FastAPI web process.

## Health checks
Local:
```bash
curl -sS http://127.0.0.1:8000/health
```

Production:
```bash
curl -sS https://api.agentascend.ai/health
```

Expected response shape:
```json
{"status":"ok"}
```

## Jobs admin check (token protected)
Use `X-Agent-Runtime-Token` header when required by environment.

## Quick verification commands
```bash
cd /home/agentascend/projects/AgentAscend
PYTHONPATH=. .venv/bin/pytest -q tests/test_tasks_outputs_pipeline.py tests/test_execution_ledger_schema.py
```

## Common failure cases
1. **`/jobs` unauthorized/forbidden**: missing or invalid runtime admin token.
2. **Scheduler appears idle**: worker not running (`scripts/run_scheduler.py` not active).
3. **Persistence confusion**: local tests may use SQLite while production uses `DATABASE_URL`.
4. **Rate-limit issues on Solana RPC**: verify dedicated RPC endpoint is configured.

## Source-of-truth policy
- Backend controls payment verification and access grants.
- Frontend must not unlock paid tools without backend-verified access.