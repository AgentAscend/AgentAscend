---
type: wiki
project: AgentAscend
aliases:
  - Frontend v0 Workflow
  - frontend-v0-workflow
---

# Frontend v0 Workflow

## Summary
The frontend is managed through v0/Vercel iterations. Current work should be patch-only, backend-truth-first, and verified from fresh ZIP extraction plus live bundle/API/browser checks.

## Components
- v0/Next.js frontend source and ZIP exports.
- Live Vercel deployment at `https://www.agentascend.ai`.
- Backend API contract from live OpenAPI.
- Playwright QA harness at `/tmp/agentascend-browser-qa/`.

## Current frontend/product status
Production Playwright QA on 2026-05-16 passed with caveat for the merged Run Agent UI click path: throwaway signup → Ascend Forge create → visible Run Agent click → `POST /agents/{id}/run` HTTP 200 → Running/Pending state → Tasks/Executions/Outputs/Overview runtime state. Exact `Agent run queued` toast copy was not observed and remains UI polish. Live Playwright QA on 2026-05-13 also passed with caveats for the deployed Output Library UX patch and the broader runtime loop. Workflow-builder owner-isolation QA passed on 2026-05-09 and is archived at [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa]]. Frontend no longer appears blocked on backend integration for agents, tasks, outputs, executions, Output Library preview/search basics, or workflow ownership basics.

`/app/workflows` is partially live: User A create/save/read/run works through live routes; User B cannot list or directly access User A workflow graph/run/runs. The frontend respected the backend graph payload boundary `{ nodes: [...] }`, did not send unsupported `edges`, and showed honest partially-live/template/settings copy.

Remaining Swarm Cycle 003 focus pages:
- `/app/overview`
- `/app/agents`
- `/app/tasks`
- `/app/outputs`
- `/app/executions`
- `/app/workflows`
- `/app/deployments`

Primary work is polish and clarity: deployment events/log-streaming UX, richer workflow run-history details, settings/token/community polish, Run Agent success-toast polish, task/execution/output detail polish, and optional throwaway QA cleanup planning if owner approves production cleanup. Output Library now honestly shows backend output listing, local loaded-list search, disabled unsupported Export All/Load More, and backend output preview. Full visual workflow graph editing remains not live; keep workflow copy honest without implying agents cannot run.

## Backend truth available now
Live OpenAPI includes Forge capability/templates, agent definitions, run/deploy/workflow bridges, Command Center, deployment events, Pump.fun routes, marketplace/access surfaces, and execution routes. The next v0 prompts should wire UI to these contracts instead of showing fake local data.

## Rules for v0 prompts
- No redesign unless explicitly requested.
- Patch only the named files/flows.
- No fake localStorage unlock/payment/access/settings persistence.
- No localStorage authority for Agent card metrics, task count, success rate, workflow ownership, graph state, or runtime status.
- Authenticated API empty state means real empty state, not demo fallback.
- Local drafts are acceptable only for unpublished draft UX, not production ownership/access/payment truth.
- Return changed-file summaries and verification output.

## Verification gates
- Fresh ZIP extraction in `/tmp`.
- `npm install`, typecheck/build/lint where available.
- API adapter contract check against live OpenAPI.
- Page-consumption gate: pages must actually render hook/API data, not merely import adapters.
- Live Vercel route/chunk marker scan after deploy.
- Logged-in post-run QA: create a throwaway account/agent, Run Agent from the visible agent action/menu, confirm `POST /agents/{id}/run` returns HTTP 200, verify Tasks/Executions/Outputs/Overview remain backend-truthful, and verify Output Library search/preview/disabled unsupported actions when in scope. Archive caveats and do not delete throwaway resources without separate owner-approved cleanup.
- Workflow owner-isolation QA: create/save/run as User A, verify User B list exclusion and 403 on cross-user graph/PUT/run/runs, and confirm graph saves only send `{ nodes: [...] }`.

## Notes
Patch-only frontend work must preserve backend authority, avoid fake local state, and separate source-candidate PASS from live deployment QA PASS.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[known-issues|Known Issues]]
- [[Roadmap]]

## Recent Evidence
- [[raw/frontend-qa/2026-05-16-production-run-agent-click-path-pass-with-caveat|2026-05-16 production Run Agent UI click path QA PASS WITH CAVEAT]]
- [[raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats|2026-05-13 live Output Library and runtime QA PASS WITH CAVEATS]]
