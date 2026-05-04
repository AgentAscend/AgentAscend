---
type: wiki
project: AgentAscend
aliases:
  - Agent Architecture
  - Multi-agent Architecture
---

# Agent Architecture

## Summary
Agent Architecture covers Hermes as project operator, Ascend Forge as product/runtime surface, and future specialized agents.

## Current status
- Ascend Forge backend foundations are live: capabilities/templates, full agent definitions, run/deploy/workflow bridges, Command Center, and deployment events.
- Full autonomous multi-agent marketplace/runtime execution is not yet the current focus.
- Specialized agent setup should wait until v0 frontend/backend contracts are clearer.

## Future agent roles
- Payment/Access Agent: audits payment/access contracts only; no production mutation without approval.
- Frontend/v0 Agent: patch prompts and frontend parity gates.
- Ledger/Scheduler Agent: execution/scheduler report-first checks; no scheduler changes without approval.
- QA/Security Agent: release gates, secret scans, security regressions.
- Docs/Memory Agent: wiki/raw/skills hygiene only.
- Release/Ops Agent: deploy readiness reports and live verification.
- Marketplace/Product Agent: listing/install/creator contract analysis.

## Relationships
- [[AgentAscend]]
- [[Execution Ledger]]
- [[scheduler|Scheduler]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Roadmap]]
- [[current-project-state|Current Project State]]

## Next actions
Do not create autonomous agents yet. First complete frontend/product polish against live backend truth and define exact allowed/forbidden scopes per agent role.
