---
type: wiki
project: AgentAscend
aliases:
  - Ops Runbook
  - Operations Runbook
---

# Ops Runbook

## Summary
The Ops Runbook is the hub for safe production checks, release gates, scheduler boundaries, Telegram recovery, docs maintenance, and owner approval prompts.

## Components
- Pre-push readiness: exact git scope, tests, OpenAPI, live preflight, no push without approval.
- Post-deploy verification: Railway web/scheduler status, `/health`, `/openapi.json`, route/auth/security checks.
- Scheduler safety: no enable/disable/run jobs or `/jobs/run-due` without approval.
- Payment safety: no Pump.fun verify, payment intent, wallet signing, access_grant, entitlement, revenue claim, or buyback action without approval.
- Telegram recovery: diagnose Hermes cron and AgentAscend scheduler Telegram layers separately; no send canary without approval.
- Automation governance: report-only by default, bounded phases, explicit stop conditions.

## Relationships
- [[Launch Readiness]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Hermes]]
- [[Agent Architecture]]
- [[known-issues|Known Issues]]

## Notes
Safe checks include public health/OpenAPI/security headers, Railway deployment status, and sanitized aggregate logs. Unsafe actions include DB mutation, migrations, scheduler state changes, env changes, deploys, payments, external messages, and public posts. Use docs/automation-governance.md and docs/telegram-notification-runbook.md for current operating details.


Pending-commit rule: when local main is ahead by runtime-worker plus swarm-doc commits, either verify aggregate production queued/running/pending_approval task counts before pushing both, or explicitly split docs-only work on a clean branch. Do not push automatically.
