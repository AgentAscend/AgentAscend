# Cronjob and runtime review - 2026-04-25

## Hermes cronjobs
- Count: 9.
- All listed Hermes cronjobs are enabled and scheduled.
- Delivery target observed: `[REDACTED_TARGET]`.
- Recent jobs show successful delivery/no delivery errors.

## Local DB-backed scheduler
- `agentascend-scheduler.service` is enabled and active/running.
- ExecStart: `/home/agentascend/projects/AgentAscend/.venv/bin/python scripts/run_scheduler.py`.
- WorkingDirectory: `/home/agentascend/projects/AgentAscend`.
- Restart policy: `always`.
- Exactly one `run_scheduler.py` process observed.
- No stale tmux/nohup scheduler process observed by the check.

## Telegram alerting
- A safe Telegram test message was sent successfully.
- Process env inspection through `/proc/1477/environ` was permission denied, so root/sudo is needed to verify env key presence/length without printing values.

## Backend health URL
- Live health check `https://api.agentascend.ai/health` returned `{"status":"ok"}`.
- Need root/sudo verification that systemd environment file sets `AGENTASCEND_HEALTH_URL=https://api.agentascend.ai/health`.

## Safety posture
- No production deployment was performed.
- No scheduler process was killed.
- No new active cronjobs were created.
- Proposed extra overnight jobs were saved as proposals only.
