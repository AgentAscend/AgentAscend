---
type: wiki
project: AgentAscend
aliases:
  - AgentAscend
---

# AgentAscend

## Summary
AgentAscend is a monetized AI x Web3 agent platform. It combines backend-authoritative payments/access, Forge agent creation/runtime routes, marketplace entitlements, scheduler-ledger operations, Hermes automation, and a v0 frontend aligned to backend truth.

## Components
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[scheduler|Scheduler]]
- [[Execution Ledger]]
- [[Agent Architecture]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Hermes]]
- [[Cronjobs]]
- [[Roadmap]]

## Current status
- Production API and scheduler are healthy at commit `712c05e` docs/evidence baseline.
- Runtime-worker backend is live.
- Runtime-aware frontend loop is owner-verified: Agent → Run Agent → Task → Execution → Output. Workflow owner-isolation is also verified live: create/save/read/run works for the owner and cross-user workflow access is blocked.
- Pump.fun payment/access regression passed; Pump.fun payment flow remains separate from the next frontend polish phase.
- Forge backend routes are live through capabilities/templates, definitions, Command Center, deployment events, and run/deploy bridges.
- Post-deploy QA protocol is active.
- Hermes local/report-only swarm and weekly hygiene jobs are active.
- Telegram sends are not approved by default.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[Roadmap]]

## Notes
Backend remains the authority for payment, access, marketplace entitlements, tasks, outputs, executions, agents, and workflow ownership. ASND utility should be grounded in real platform usage, not price or return promises.
