---
type: wiki
project: AgentAscend
aliases:
  - Frontend v0 Workflow
  - frontend-v0-workflow
---

# Frontend v0 Workflow

## Summary
The frontend source of truth is each newly exported v0 ZIP. Audits must be fresh extractions with compile/parity gates and patch-only prompts.

## Components
- Current state: The frontend source of truth is each newly exported v0 ZIP. Audits must be fresh extractions with compile/parity gates and patch-only prompts.
- Endpoints/files involved:
  - `latest v0 ZIP`
  - `lib/dashboard-api.ts`
  - `hooks/useDashboardData.ts`
  - `app/app/* pages`
  - `scripts/source-truth-check.mjs when present`
  - `live Vercel JS chunks`

## What is working
- Established workflow: fresh ZIP audit, static scans, live bundle verification, patch-only prompts.

## What is broken or unproven
- Current frontend issues remain: outputs SelectItem crash, task persistence/reload, workflow create incomplete, deployment/logs/scale missing actions.

## Next actions
- Ask v0 for minimal patch-only changes.
- Verify returned ZIP file identity and live Vercel bundle markers.
- Run source-truth, typecheck, lint, build, audit.

## Relationships
- [[Auth]]
- [[Database]]
- [[Marketplace]]
- [[Community]]
- [[Tasks Outputs]]
- [[Scheduler]]
- [[Frontend v0 Workflow]]
- [[Deployment]]
- [[Known Issues]]
- [[Roadmap]]

## Safety notes
- Do not redesign UI unless requested.
- Do not accept source PASS as deployed PASS.

## Notes
This page was created/updated during the 2026-04-25 overnight knowledge/runtime improvement cycle. Treat source-level facts separately from live-production verification.

## 2026-04-30 Knowledge Graph Status Update
- Raw launch evidence, tokenized-agent, scheduler/cronjob, deploy-readiness, security, and Hermes runtime notes now link back to this hub graph.
- Exact Pump.fun `tx_signature` binding hardening is implemented and deployed at commit `453df65aec69f7aa95b20bb1752f7d3af97ad488`.
- Replay-index migration remains pending and must not be run without owner approval.
- Node dependency audit remains pending as a separate hardening phase.
