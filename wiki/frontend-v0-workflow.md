---
type: wiki
project: AgentAscend
aliases:
  - Frontend v0 Workflow
  - frontend-v0-workflow
---

# Frontend v0 Workflow

## Summary
The frontend is managed through v0/Vercel iterations. Current work should be patch-only, backend-truth-first, and verified from fresh ZIP extraction plus live bundle/API checks.

## Current frontend/product status
Owner-assisted logged-in QA has passed for the verified runtime loop: Agent → Run Agent → Task → Execution → Output. The prior runtime-aware source/build audit warning is closed for this loop. Frontend no longer appears blocked on backend integration for tasks, outputs, or executions.

## Current focus pages
- `/app/overview`
- `/app/agents`
- `/app/tasks`
- `/app/outputs`
- `/app/executions`
- `/app/workflows`
- `/app/deployments`
- `/app/settings`
- `/app/community`

## Backend truth available now
Live OpenAPI includes Forge capability/templates, agent definitions, run/deploy/workflow bridges, Command Center, deployment events, Pump.fun routes, marketplace/access surfaces, and execution routes. The next v0 prompts should wire UI to these contracts instead of showing fake local data.

## Remaining frontend/product gaps
- Workflow builder graph UX.
- Output search/export/bulk UX.
- Task detail UX.
- Execution detail UX.
- Deployment events timeline/log UX.
- Settings persistence polish.
- Token/community UX.

## Rules for v0 prompts
- No redesign unless explicitly requested.
- Patch only the named files/flows.
- No fake localStorage unlock/payment/access/settings persistence.
- Authenticated API empty state means real empty state, not demo fallback.
- Local drafts are acceptable only for unpublished draft UX, not production ownership/access/payment truth.
- Return changed-file summaries and verification output.

## Verification gates
- Fresh ZIP extraction in `/tmp`.
- Pinned package-manager install, source-truth check, typecheck, lint, build, and audit.
- API adapter contract check against live OpenAPI.
- Page-consumption gate: pages must actually render hook/API data, not merely import adapters.
- Live Vercel route/header/chunk marker scan after deploy.
- Safe Playwright route/render smoke when available.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[known-issues|Known Issues]]
- [[Roadmap]]
