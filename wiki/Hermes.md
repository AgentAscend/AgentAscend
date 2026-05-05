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
- Cronjobs: report-only recurring Hermes jobs that can deliver through the Hermes gateway.
- Delegation: short-lived subagents for research, review, and isolated workstreams.
- Gateway: messaging layer for Telegram and other platforms; separate from AgentAscend production scheduler Telegram status job.

## Relationships
- [[AgentAscend]]
- [[Agent Architecture]]
- [[Cronjobs]]
- [[Ops Runbook]]
- [[current-project-state|Current Project State]]

## Notes
Hermes must preserve raw/wiki/system/learning/skills boundaries. It may propose automation, docs, and safe implementation slices, but must not perform production mutation, payments, scheduler state changes, or external messaging without explicit approval. Recent Telegram audit distinguishes Hermes cron Telegram delivery from the AgentAscend scheduler `default-telegram-status-summary` job.


Hermes swarm activation is currently local/report-only: `docs/hermes-swarm-manifest.md`, `docs/hermes-swarm-cycle-001.md`, and `docs/hermes-swarm-cadence.md` define lanes and maturity levels. Current cron failure evidence points to stale Hermes cron execution/import state (`cfg_get`) before Telegram delivery, while the gateway is currently running.
