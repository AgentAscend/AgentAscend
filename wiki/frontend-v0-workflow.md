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
Logged-in frontend remains the biggest product bottleneck. Pages needing real backend-aligned polish include:
- `/app/overview`
- `/app/agents`
- `/app/deployments`
- `/app/workflows`
- `/app/tasks`
- `/app/outputs`
- `/app/executions`
- `/app/token`
- `/app/community`
- `/app/settings`

## Backend truth available now
Live OpenAPI includes Forge capability/templates, agent definitions, run/deploy/workflow bridges, Command Center, deployment events, Pump.fun routes, marketplace/access surfaces, and execution routes. The next v0 prompts should wire UI to these contracts instead of showing fake local data.

## Rules for v0 prompts
- No redesign unless explicitly requested.
- Patch only the named files/flows.
- No fake localStorage unlock/payment/access/settings persistence.
- Authenticated API empty state means real empty state, not demo fallback.
- Local drafts are acceptable only for unpublished draft UX, not production ownership/access/payment truth.
- Return changed-file summaries and verification output.

## Verification gates
- Fresh ZIP extraction in `/tmp`.
- `npm install`, typecheck/build/lint where available.
- API adapter contract check against live OpenAPI.
- Page-consumption gate: pages must actually render hook/API data, not merely import adapters.
- Live Vercel route/chunk marker scan after deploy.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[known-issues|Known Issues]]
- [[Roadmap]]
