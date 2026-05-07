---
type: wiki
project: AgentAscend
aliases:
  - Cronjobs
  - Scheduled Jobs
---

# Cronjobs

## Summary
Cronjobs are recurring operating loops for AgentAscend. Hermes cronjobs and AgentAscend production scheduler jobs are separate systems. Current posture is local/report-only by default; Telegram/external sends, production mutation, scheduler changes, `/jobs/run-due`, payments, and deploys require explicit owner approval.

## Components
- Hermes cronjobs: managed by Hermes; can deliver locally or through messaging gateways.
- Legacy Hermes Telegram jobs: still enabled but high-risk until owner approves conversion/pause/remove or Telegram canary.
- Local Hermes swarm report jobs: current preferred automation layer.
- Weekly hygiene cronjob: `5cf95fc08134`, local-only, Sundays 09:30, writes/recommends `raw/automation-governance/YYYY-MM-DD-weekly-system-hygiene-cronjob-audit.md`.
- AgentAscend scheduler jobs: production DB-backed jobs run by Railway `AgentAscend-Scheduler`.

## Current Hermes cron posture — verified 2026-05-07
- Keep current local swarm reports: Daily Operator, Daily Knowledge Hygiene, Backend/Frontend Contract, Weekly Security Dependency.
- Keep new Weekly System Hygiene and Cronjob Audit.
- Keep but update/convert legacy Telegram jobs before relying on them.
- Pause candidates: legacy documentation gap scan and weekly strategy/security/ecosystem scan.
- Remove candidate: legacy weekly roadmap reprioritizer.

## Current AgentAscend scheduler posture
Enabled/audited: `default-backend-health-check`, `default-integration-drift-check`, `default-wiki-consistency-check`, `default-todo-fixme-scan`, `default-payment-route-audit`, `default-failed-payment-replay-review`, `default-access-grant-integrity-check`, `default-task-queue-worker`.

Disabled/held: `default-telegram-status-summary`, `default-git-status-summary`, `default-roadmap-review`.

## Relationships
- [[scheduler|Scheduler]]
- [[Hermes]]
- [[Ops Runbook]]
- [[Agent Architecture]]
- [[Execution Ledger]]
- [[current-project-state|Current Project State]]

## Notes
Do not run existing cronjobs or scheduler jobs during audits unless explicitly approved. Do not print Telegram IDs/tokens or raw logs. Use raw audit reports under `raw/automation-governance/` for detailed inventories.
