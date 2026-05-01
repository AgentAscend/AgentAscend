---
type: redirect
project: AgentAscend
aliases:
  - roadmap
---

# roadmap

See [[Roadmap]].

This lowercase page is retained as a redirect/stub to avoid a Roadmap.md vs roadmap.md split in Obsidian.

## Previous content archived below

# Roadmap

## Summary
AgentAscend should evolve from backend CRUD + v0 dashboard parity into a durable AI agent execution platform. Near-term work should prove persistence, auth scoping, task/output execution, workflow orchestration, and marketplace trust before expanding autonomy or monetization complexity.

## Components
- Backend source of truth: auth, payments/access, marketplace, community, tasks, outputs, jobs.
- Runtime layer: DB-backed scheduler, job runs, findings, task queue worker.
- Frontend layer: v0/Vercel dashboard that must match backend contracts and render honest states.
- Marketplace layer: listings, creator ownership, entitlements, payouts, install events.
- Future agent layer: execution ledger, workflows, tool permissions, telemetry, pricing, governance.

## What is working
- Live backend health endpoint is up.
- Backend contains broad platform routes for agents, deployments, workflows, tasks, outputs, community, marketplace, token pages, settings, and ops surfaces.
- Scheduler foundation exists with `scheduled_jobs`, `job_runs`, `agent_findings`, systemd execution, and admin APIs.
- Local regression tests exist for auth persistence config, marketplace publish, community CRUD, no demo seed data, and tasks-output pipeline.
- Knowledge base now has raw/wiki/learning/skills organization for future Hermes sessions.

## What is broken or unproven
- Live Postgres write durability is not fully proven by current evidence.
- Task visibility after signout/signin remains a current issue until verified on live frontend/API.
- `/app/outputs` has a known Radix Select empty-value crash risk.
- Task/output frontend wiring needs latest v0 source and live bundle verification.
- Workflow create/execution is not fully productized.
- Deployment/logging/scale UI actions either need real endpoints or honest endpoint-needed states.
- Marketplace needs a stronger agent contract, verification, and governance model before serious creator monetization.

## Prioritized backend work

### P0 - Persistence and auth proof matrix
- Problem: Health checks do not prove Railway Postgres persistence or user-scoped reloads.
- Impact: Users may lose tasks/outputs across signin/redeploy, damaging trust.
- Proposed solution: Script a throwaway-user live matrix: signup/signin, create task, list task, signout/signin, list again, run/poll output, verify cross-user 403, repeat after approved redeploy/restart.
- Files/endpoints involved: `backend/app/db/session.py`, `/auth/*`, `/tasks`, `/outputs`, Railway env.
- Complexity: Medium.

### P0 - Execution ledger design
- Problem: Current `tasks` + `outputs` are a good start but too narrow for agent/workflow execution history.
- Impact: Hard to support retries, approvals, step logs, cost, tool calls, artifacts, marketplace billing, and debugging.
- Proposed solution: Design an execution ledger that unifies tasks, workflow runs, agent runs, logs, outputs, costs, and approvals. Implement incrementally after design approval.
- Files/endpoints involved: `tasks`, `outputs`, `task_logs`, `workflow_runs`, future `run_steps`, `run_events`, `run_artifacts`.
- Complexity: Medium/high.

### P1 - Workflow runtime MVP
- Problem: Workflows exist but need clear execution semantics.
- Impact: UI workflow creation will feel hollow without runs, logs, statuses, and outputs.
- Proposed solution: Define workflow node schema, trigger/run lifecycle, deterministic step executor, retry/cancel behavior, and output attachment.
- Files/endpoints involved: `/workflows`, `/workflows/{id}/graph`, `/workflows/{id}/runs`, `workflow_nodes`, `workflow_runs`.
- Complexity: Medium.

### P1 - Scheduler observability and job quality
- Problem: Scheduler exists but should become more informative before becoming more autonomous.
- Impact: Better findings and run metadata will prevent noisy or unsafe automation.
- Proposed solution: Improve job run summaries, categorize findings, add stale-job detection, queue-depth metrics, and one combined nightly report proposal.
- Files/endpoints involved: `backend/app/services/job_runner.py`, `scheduler_service.py`, `scripts/job_admin.py`, `/jobs`.
- Complexity: Low/medium.

### P2 - Marketplace contract and lifecycle backend
- Problem: Listings alone are insufficient for trusted paid agents.
- Impact: Marketplace cannot safely scale creator monetization without standard contracts and governance.
- Proposed solution: Define listing version, input/output schema, permissions, tool requirements, verification state, execution tier, telemetry, and review fields.
- Files/endpoints involved: `/marketplace/listings`, `/marketplace/discover`, entitlements, install events, creator payouts.
- Complexity: Medium.

## Prioritized frontend work

### P0 - Fix `/app/outputs` SelectItem crash
- Replace any empty Radix SelectItem value with a non-empty sentinel and map it at the filter/API boundary.
- Verify source ZIP, typecheck/lint/build, then live Vercel bundle markers.

### P0 - Verify task visibility after signin
- Ensure private API calls include bearer tokens and successful empty API responses do not fall back to local/demo arrays.
- Confirm signed-in user ID scopes task/output list consistently.

### P1 - Complete task/output wiring
- UI should show backend-created tasks, worker statuses, logs, and outputs from `/tasks`, `/tasks/{id}/logs`, and `/outputs`.
- Empty states must be honest.

### P1 - Workflow create and graph wiring
- Visible create workflow CTA should call backend, handle errors, refetch, and show backend source of truth.
- If execution is not ready, UI should say endpoint/runtime-needed rather than fake runs.

### P2 - Deployment/logging/scale action honesty
- Deployment/log/scale buttons should either call real endpoints or show controlled coming-soon/endpoint-needed states.

## Architecture improvements

### Durable execution principles
- Assign stable run/thread IDs to every task, workflow, and future agent execution.
- Record checkpoints or step events before/after side effects.
- Make side-effectful steps idempotent with keys and existence checks.
- Separate deterministic orchestration from non-deterministic tool/model calls.
- Persist outputs/artifacts independently from status fields.

### Worker/queue scaling principles
- Start with one safe polling worker; later separate queues by capability/risk/cost.
- Use explicit worker compatibility/version metadata before multiple worker types poll the same queue.
- Add queue depth, oldest queued age, failed/retry counts, and processing latency metrics.
- For Postgres scaling, consider `FOR UPDATE SKIP LOCKED` for multiple workers.

### Marketplace growth principles
- Treat marketplace as registry + governance + distribution + monetization.
- Require standardized agent metadata: capabilities, input/output schema, permissions, tools, pricing, verification, version, owner, telemetry.
- Keep payment/token utility gated by real working platform usage and manual approval.

## Research-backed ideas
- LangGraph-style durability: checkpoint execution and isolate side effects.
- Temporal-style task queues: persistent work, polling workers, capacity-based dispatch, clear worker registration per queue.
- CrewAI-style architecture: Flow-first orchestration, autonomous agents delegated inside controlled flow steps.
- Agent marketplace architecture: standardization, distribution, governance, observability, lifecycle.
- Postgres outbox: write business changes and event intents atomically, relay asynchronously with idempotency.

## Safety notes
- Do not deploy without explicit approval.
- Do not modify payment/auth logic during architecture planning.
- Do not make autonomous financial, trading, tokenomics, buyback, or public-launch decisions.
- Distinguish source PASS from Railway/Vercel live PASS.
- Use throwaway accounts/data for live verification.

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

## Notes
Updated during the 2026-04-25 overnight learning + system improvement mode. This is a strategic implementation roadmap, not authorization to execute large changes.
