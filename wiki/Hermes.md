---
type: wiki
project: AgentAscend
aliases:
  - Hermes
  - Hermes Agent
---

# Hermes

## Summary
Hermes is the structured AgentAscend operator for reasoning, tool use, docs, audits, implementation support, cron delivery, and subagent orchestration.

## Components
- Skills: reusable procedures for AgentAscend audits, implementation slices, and platform operations.
- Memory: compact durable facts and current operating constraints.
- Cronjobs: report-only recurring Hermes jobs with local or external delivery.
- Delegation: short-lived subagents for isolated research/review workstreams.
- Gateway: messaging layer for Telegram and other platforms, separate from the AgentAscend production scheduler Telegram job.

## Current automation posture
- Local/report-only swarm jobs are active.
- Weekly local-only hygiene job `5cf95fc08134` is active.
- Legacy Telegram cronjobs still exist and need owner approval before pause/remove/conversion or send canaries.
- AgentAscend scheduler Telegram remains held separately.

## Relationships
- [[AgentAscend]]
- [[Agent Architecture]]
- [[Cronjobs]]
- [[Ops Runbook]]
- [[current-project-state|Current Project State]]
- [[scheduler|Scheduler]]

## Notes
Hermes must preserve raw/wiki/system/learning/skills boundaries. It may propose automation, docs, and safe implementation slices, but must not perform production mutation, payments, scheduler state changes, or external messaging without explicit approval.
