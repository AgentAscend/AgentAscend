---
type: wiki
project: AgentAscend
aliases:
  - Current Project State
---

# Current Project State

## Summary
AgentAscend is in a live runtime/product-polish posture. Payment/access regression, Forge/backend routes, runtime worker, execution/task/output loop, and post-deploy QA are live. The current bottleneck is frontend product polish and workflow/output UX against backend truth.

## Components
- Backend/API: Railway FastAPI at `https://api.agentascend.ai`.
- Frontend: v0/Next.js on Vercel at `https://www.agentascend.ai`.
- Database: Railway Postgres.
- Scheduler: separate Railway `AgentAscend-Scheduler` worker with DB-backed jobs.
- Automation: Hermes cronjobs and AgentAscend scheduler jobs are separate systems.
- Knowledge system: `MEMORY.md`, `raw/`, `wiki/`, `docs/`, `learning/`, `skills/`, `system/`.

## Current production status — verified 2026-05-07
- `origin/main`: `712c05e8d1c1b9c05bae5d8723713ff80b5c5567`.
- Railway `AgentAscend`: SUCCESS at commit `712c05e`, deployment `ddf9b9a6`.
- Railway `AgentAscend-Scheduler`: SUCCESS at commit `712c05e`, deployment `c2f213a7`.
- `/health`: HTTP 200.
- `/openapi.json`: HTTP 200 valid JSON.
- API security headers: HSTS, CSP, Permissions-Policy, Referrer-Policy, X-Content-Type-Options, X-Frame-Options present.
- Live OpenAPI includes Pump.fun create/verify, Forge capabilities/templates, agent definitions/run/deploy, workflow run, Command Center, tasks, outputs, executions, deployment events, and admin task-runtime aggregate routes.

## Product status
- Runtime worker is live.
- Runtime-aware frontend loop is owner-verified: Agent → Run Agent → Task → Execution → Output.
- Post-deploy QA protocol is active and mandatory before final PASS after every deploy.
- Local Playwright harness is available at `/tmp/agentascend-browser-qa/agentascend-browser-qa.js` for safe frontend route/render smoke.
- Replay-index DDL is not needed because equivalent protections already exist.
- Payment flow works and controlled Pump.fun regression passed.
- Telegram sends remain not approved by default.

## Remaining backend/product gaps
- Full visual workflow graph builder.
- Richer output search/export/bulk actions.
- Task and execution detail UX.
- Deployment scale/rollback/log streaming.
- Settings persistence polish.
- Token/community UX as future slices.

## Relationships
- [[AgentAscend]]
- [[Launch Readiness]]
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Hermes]]
- [[Execution Ledger]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[known-issues|Known Issues]]
- [[Roadmap]]

## Notes
Next product focus: frontend polish, workflow builder UX, output UX, task detail UX, execution detail UX, deployment events UX, and settings/community polish. Keep Pump.fun separate unless explicitly scoped.
