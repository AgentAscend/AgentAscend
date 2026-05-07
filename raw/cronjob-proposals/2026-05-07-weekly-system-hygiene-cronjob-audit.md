---
type: cronjob-proposal
project: AgentAscend
date: 2026-05-07
status: approved-by-direct-owner-request
---

# Weekly System Hygiene and Cronjob Audit Cronjob

## Summary
The owner requested a weekly local-only Hermes report job for system hygiene and cronjob audits. The job was created as report-only/local-only.

## Job
- Name: AgentAscend Weekly System Hygiene and Cronjob Audit
- Job ID: `5cf95fc08134`
- Schedule: `30 9 * * 0` (Sundays 09:30 local time)
- Delivery: local only
- Workdir: `/home/agentascend/projects/AgentAscend`
- Output target: `raw/automation-governance/YYYY-MM-DD-weekly-system-hygiene-cronjob-audit.md`

## Allowed scope
- Read MEMORY/docs/wiki/raw/skills/system state.
- Read-only live health/OpenAPI/header checks.
- Read-only Hermes cronjob inventory.
- Read-only AgentAscend scheduler posture if safe admin aggregate access is available.
- Write one sanitized local markdown report.

## Forbidden scope
No Telegram/external messages, production mutation, scheduler job changes/runs, `/jobs/run-due`, payments, Pump.fun verify, push/deploy, code changes, secrets, raw DB rows, raw metadata/payload/request/response/task bodies or outputs.

## Related
- [[Cronjobs]]
- [[Hermes]]
- [[scheduler]]
- [[current-project-state]]
