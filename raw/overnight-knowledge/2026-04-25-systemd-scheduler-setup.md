---
type: evidence
project: AgentAscend
date: 2026-04-25
status: archived
tags:
  - agentascend
  - overnight-knowledge
related:
  - "[[AgentAscend]]"
  - "[[Roadmap]]"
  - "[[Ops Runbook]]"
---

Related: [[AgentAscend]], [[Roadmap]], [[Ops Runbook]]

# systemd scheduler setup factual log - 2026-04-25

Timestamp: 2026-04-25 21:20 PDT

Facts observed:
- `agentascend-scheduler.service` is loaded and enabled.
- Service is active/running since 2026-04-25 17:49 PDT.
- Main PID observed: 1477.
- ExecStart observed: `/home/agentascend/projects/AgentAscend/.venv/bin/python scripts/run_scheduler.py`.
- WorkingDirectory observed: `/home/agentascend/projects/AgentAscend`.
- Restart policy observed: `Restart=always`.
- Exactly one `run_scheduler.py` process was visible in `ps` output.
- No tmux scheduler process was reported by the tmux inspection command.
- EnvironmentFile observed: `/etc/agentascend-scheduler.env`; direct `/proc/1477/environ` inspection was permission denied.
- Telegram delivery was confirmed by sending a safe test message to configured Telegram chat id.

Open verification:
- Use sudo/root if needed to verify env presence/length for `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `AGENTASCEND_HEALTH_URL` without exposing values.
- Confirm `AGENTASCEND_HEALTH_URL` equals `https://api.agentascend.ai/health` in the environment file.
