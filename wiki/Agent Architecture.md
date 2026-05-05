---
type: wiki
project: AgentAscend
aliases:
  - Agent Architecture
  - Multi-agent Architecture
---

# Agent Architecture

## Summary
Agent Architecture defines the safe Hermes/AgentAscend multi-agent operating model: specialized agents may audit, draft, test, and implement bounded slices, but production-impacting actions stay owner-gated.

## Components
- Release/Ops Agent: Railway/Vercel readiness, deploy monitoring, logs, rollback plans.
- Backend Forge Agent: agents, workflows, tasks, outputs, runtime endpoints, backend tests.
- Frontend/v0 Agent: v0 prompts, frontend audits, contract checks.
- Payment/Access Agent: Pump.fun, payment verification, access_grants, entitlements, replay checks.
- Scheduler/Automation Agent: cronjobs, task worker, job safety, report-only automation.
- Docs/Memory Agent: MEMORY.md, wiki, raw notes, Obsidian hygiene, skills.
- QA/Security Agent: tests, secret scans, auth checks, release gates.
- Marketing/Community Agent: drafts only; no auto-posting.

## Relationships
- [[AgentAscend]]
- [[Hermes]]
- [[Cronjobs]]
- [[Ops Runbook]]
- [[Execution Ledger]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Payment Access Control]]

## Notes
The default autonomy level is report-only. Use `delegate_task` for short isolated reviews and full Hermes subprocesses only for bounded longer missions with explicit file ownership. Every agent must stop before push, deploy, DB mutation, scheduler state change, payment action, or external message unless the owner explicitly approves that action.


Swarm activation status: local manifest/report-only first. The local docs commit `99f811a` sits on top of backend runtime-worker commit `6aac0e3`; do not treat a normal push as docs-only unless commits are split with explicit owner approval.
