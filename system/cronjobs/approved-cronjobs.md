# Approved AgentAscend Cronjobs

This file records AgentAscend cronjobs explicitly approved by Reuben or activated from direct user instruction.

## 2026-04-25 — MEMORY.md Maintenance

- Job name: AgentAscend MEMORY.md maintenance
- Job ID: 7fede4bb3eb4
- Schedule: `30 19 * * *` daily at 7:30 PM
- Delivery: Telegram DM `telegram:7044198368`
- Workdir: `/home/agentascend/projects/AgentAscend`
- Output path: `raw/memory-maintenance/YYYY-MM-DD.md`
- Model tier: Reasoning
- Risk level: Low to Medium
- Allowed actions: read files, inspect git status/diffs, create one markdown report, propose MEMORY.md patch in report
- Forbidden actions: edit MEMORY.md automatically, expose secrets, add raw logs, add temporary debugging noise, modify payment/wallet/access/database/deployment code, commit, push, deploy, post externally, send emails, or send appeals
- Escalation condition: payment verification, wallets, access control, replay protection, ASND utility, database integrity, public launch, security, user funds, public claims, or conflicting autonomy rules
- Source proposal: `raw/cronjob-proposals/2026-04-25-0002.md`
