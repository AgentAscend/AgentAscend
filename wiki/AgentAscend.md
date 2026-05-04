---
type: wiki
project: AgentAscend
aliases:
  - AgentAscend
---

# AgentAscend

## Summary
AgentAscend is a monetized AI x Web3 agent platform. It combines backend-authoritative payments/access, Forge agent creation/runtime routes, marketplace entitlements, scheduler-ledger operations, and a v0 frontend that must be aligned to backend truth.

## Components
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[scheduler|Scheduler]]
- [[Execution Ledger]]
- [[Agent Architecture]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Hermes]]
- [[Roadmap]]

## Current status
- Production API is healthy at commit `26aa8ab`.
- Pump.fun payment/access regression passed.
- Forge backend routes are live through deployment events, Command Center, agent definitions, capabilities/templates, and run/deploy bridges.
- Scheduler workload is report-first and audited.
- Frontend product polish is the next bottleneck.

## Notes
- Backend remains the authority for payment, access, marketplace entitlements, tasks, outputs, executions, and agents.
- ASND utility should be grounded in real platform usage, not price or return promises.
- Multi-agent architecture remains planning until frontend/backend contracts are clearer.

## Recent Evidence
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/security-reviews/2026-05-02-node-helper-dependency-audit|2026-05-02 Node helper dependency audit baseline]]
- Commits: `239fa79` dev dependency cleanup, `a8ad3ba` Pump.fun SDK 3.0.3, `2d00a31` controlled regression evidence, `5ac6d06` Forge definitions, `34a8c21` Command Center, `{prod_short}` deployment events.
