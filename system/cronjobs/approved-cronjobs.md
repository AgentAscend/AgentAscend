# Approved AgentAscend Cronjobs

This file records AgentAscend cronjobs explicitly approved by Reuben or activated from direct user instruction.

## 2026-04-25 — MEMORY.md Maintenance

- Job name: AgentAscend MEMORY.md maintenance
- Job ID: 7fede4bb3eb4
- Schedule: `30 19 * * *` daily at 7:30 PM
- Delivery: Telegram DM (target redacted in docs; legacy external delivery)
- Workdir: `/home/agentascend/projects/AgentAscend`
- Output path: `raw/memory-maintenance/YYYY-MM-DD.md`
- Model tier: Reasoning
- Risk level: Low to Medium
- Allowed actions: read files, inspect git status/diffs, create one markdown report, propose MEMORY.md patch in report
- Forbidden actions: edit MEMORY.md automatically, expose secrets, add raw logs, add temporary debugging noise, modify payment/wallet/access/database/deployment code, commit, push, deploy, post externally, send emails, or send appeals
- Escalation condition: payment verification, wallets, access control, replay protection, ASND utility, database integrity, public launch, security, user funds, public claims, or conflicting autonomy rules
- Source proposal: `raw/cronjob-proposals/2026-04-25-0002.md`

## 2026-05-07 — Weekly System Hygiene and Cronjob Audit

- Job name: AgentAscend Weekly System Hygiene and Cronjob Audit
- Job ID: `5cf95fc08134`
- Schedule: `30 9 * * 0` (Sundays 09:30 local time)
- Delivery: local only
- Workdir: `/home/agentascend/projects/AgentAscend`
- Output path: `raw/automation-governance/YYYY-MM-DD-weekly-system-hygiene-cronjob-audit.md`
- Risk level: Low, report-only
- Allowed actions: read project knowledge, inspect git state, list Hermes cronjobs, read-only public API health/OpenAPI/header checks, safe aggregate scheduler posture checks, write one sanitized markdown report
- Forbidden actions: run existing cronjobs, pause/remove/enable/disable cronjobs, send Telegram/external messages, mutate production DB, run migrations/DDL, change scheduler jobs, call `/jobs/run-due`, run payments, create payment intents, call Pump.fun verify, change access grants/entitlements, push/deploy, edit backend/frontend code, print secrets or raw private data
- Source proposal: `raw/cronjob-proposals/2026-05-07-weekly-system-hygiene-cronjob-audit.md`
- Related audit: `raw/automation-governance/2026-05-07-cronjob-viability-audit.md`
