# Telegram Notification Runbook

Status: active runbook.
Scope: diagnosing and recovering AgentAscend/Hermes Telegram updates without accidental sends.

## Two separate Telegram layers

1. Hermes cron delivery
   - Hermes cronjobs can deliver final reports to a Telegram target through the Hermes gateway.
   - These jobs are managed by Hermes cron, not the AgentAscend production scheduler DB.

2. AgentAscend scheduler Telegram status summary
   - `default-telegram-status-summary` is a production scheduler job.
   - It is report-only by default and does not send unless explicitly configured.
   - Outbound sending requires `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED=true` plus Telegram credentials.

## Current diagnosis from 2026-05-04 audit

- Hermes cronjobs exist and are scheduled with Telegram delivery, but recent runs mostly show `last_status=error` and no delivery error. This points to job execution/provider/network failure before final delivery rather than a Telegram delivery rejection.
- Local Hermes logs contain Telegram/cron/error markers and network-style exception categories including ConnectError, ReadError, NetworkError, and RemoteProtocolError. No secret-like markers were counted in recent scanned log windows.
- AgentAscend production Telegram scheduler configuration has Telegram send variables and Telegram credentials missing on both web and scheduler services by name-only inspection.
- AgentAscend runtime defaults are report-only for Telegram status sends.
- Production DB job state for `default-telegram-status-summary` could not be re-queried from this environment because read-only Railway DB access was blocked. MEMORY.md and scheduler runbooks identify it as held/disabled.

## Safe read-only checks

Do not send a Telegram message during diagnosis.

Check Hermes cron layer:
```bash
hermes cron list
hermes cron status
```

Check AgentAscend live API:
```bash
curl -fsS https://api.agentascend.ai/health
curl -fsS https://api.agentascend.ai/openapi.json >/tmp/agentascend-openapi.json
```

Check Railway deployment status and variable presence only:
```bash
railway deployment list --service AgentAscend --environment production --limit 5 --json
railway deployment list --service AgentAscend-Scheduler --environment production --limit 5 --json
railway variables --service AgentAscend-Scheduler --environment production --json
```

When inspecting variables, print only presence/categories for:
- `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED`
- `AGENT_RUNTIME_TELEGRAM_NOTIFICATIONS_ENABLED`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Never print values.

## Recovery options

### Option 1: Keep report-only
- No Telegram sends.
- Status remains visible in logs/admin/job_runs only.
- Safest default.

### Option 2: Enable scheduled report-only job
- Enable `default-telegram-status-summary` only after owner approval.
- Keep `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED=false` or unset.
- Job records run output but sends no Telegram message.

### Option 3: Enable Telegram sends later
Requires owner approval, Telegram credentials, explicit send flag, and a one-message no-secret canary. Message template must be approved first. Do not include secrets, payment refs, wallet data, raw errors, raw DB output, raw metadata, or raw payloads.

### Option 4: Use Hermes Telegram bot only
Keep AgentAscend scheduler Telegram disabled and send owner-facing reports through Hermes cron/gateway after fixing cron execution reliability.

## 2026-05-04 no-send cron recovery audit update

- `hermes cron status` shows the gateway is currently active/running and nine active jobs are scheduled.
- `hermes cron list` shows the recent failing jobs ended with `cannot import name cfg_get from hermes_cli.config`; `last_delivery_error` remains null, so the failure occurs before Telegram delivery.
- The local Hermes source currently contains `cfg_get` in `hermes_cli/config.py`; the gateway was restarted after the latest failing run, so the next safe check is a no-send/dry-run execution validation only after owner approval.
- Do not enable AgentAscend scheduler Telegram sends to fix this; it is a Hermes cron execution/import/version issue, not an AgentAscend scheduler Telegram configuration issue.

## Recommended path

Use Option 4 for owner-facing Telegram updates and keep AgentAscend scheduler Telegram disabled/report-only. First fix Hermes cron execution errors without sending new messages. Use Option 3 only after an explicit no-secret canary approval.

## Approved message template shape

If owner later approves a send canary, use a minimal message:

`AgentAscend status canary: health=ok, openapi=ok, scheduler=not changed. No secrets included.`

Stop after exactly one message and report delivery status only.
