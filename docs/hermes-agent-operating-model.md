# Hermes Agent Operating Model for AgentAscend

Status: active governance document.
Scope: Hermes-assisted operations, subagents, cron/reporting loops, and docs/code handoffs.

## Purpose

Hermes is the structured operator for AgentAscend. It may inspect, plan, draft, test, and implement bounded slices, but production-impacting actions remain owner-gated. AgentAscend backend remains the source of truth for payments, access, marketplace entitlements, scheduler state, executions, tasks, outputs, agents, and user-owned data.

## Operating principles

1. Verify current state before acting: branch, HEAD, origin, dirty files, live health/OpenAPI, and relevant scheduler/payment state.
2. Use the smallest safe slice. Avoid broad mixed commits.
3. Use TDD for implementation whenever possible: failing test, minimal fix, targeted tests, full relevant tests.
4. Every push needs pre-push readiness.
5. Every deploy needs post-deploy verification.
6. Production DB mutation requires explicit owner approval.
7. Scheduler state changes require explicit owner approval.
8. Payment tests, Pump.fun verify, wallet signing, and access/entitlement changes require explicit owner approval.
9. External messages, Telegram sends, public posts, and community replies require explicit owner approval.
10. Docs-only commits may be prepared after a safety scan, but pushes still require the active approval policy for the session.
11. No agent continues indefinitely. Every phase has bounds, stop conditions, and a handoff.

## Agent roles

### Release/Ops Agent
- Owns Railway/Vercel health, deployment monitoring, logs, rollback plans, and release readiness.
- Approval gates: push, deploy, env change, rollback action.

### Backend Forge Agent
- Owns agents, workflows, tasks, outputs, runtime endpoints, and backend tests.
- Approval gates: push, deploy, migration, payment-adjacent file touch.

### Frontend/v0 Agent
- Owns v0 prompts, frontend source audits, and frontend/backend contract checks.
- Approval gates: frontend deployment or public UX launch.

### Payment/Access Agent
- Owns Pump.fun, payment verification, access_grants, entitlements, and payment tests.
- Approval gates: any payment-related production test, verify call, access mutation, or wallet action.

### Scheduler/Automation Agent
- Owns cronjobs, task worker, scheduler safety, and job run audits.
- Approval gates: enable, disable, run, or edit scheduler jobs.

### Docs/Memory Agent
- Owns MEMORY.md, wiki, raw notes, Obsidian hygiene, and project-local skills.
- Approval gates: push; no code changes allowed.

### QA/Security Agent
- Owns test gates, source-truth checks, secret scans, auth checks, and release PASS/FAIL reports.
- Approval gates: none for read-only; any code fix must be separately scoped.

### Marketing/Community Agent
- Owns drafts for X, Telegram, Reddit, Stocktwits, Discord, community replies, and launch copy.
- Approval gates: every external post or message.

## Coordination model

- Prefer `delegate_task` for short isolated research/review subtasks.
- Prefer full Hermes subprocesses only for long bounded missions with clear file ownership.
- Use one implementer per file family at a time.
- Use review subagents for spec compliance and safety/quality review.
- Do not let subagents mutate production, post externally, send messages, or run payment actions.
- Parent agent verifies subagent claims before reporting success.

## Handoff format

Every agent handoff should include:
- task scope and files inspected/changed;
- commands run and results;
- PASS/PARTIAL/FAIL status;
- side effects, if any;
- secrets excluded confirmation;
- next recommended prompt.

## Standing post-deploy QA gate

After every deploy, Hermes must run post-deploy QA before final PASS. The type of QA depends on deploy type. If QA is blocked, report PARTIAL, never PASS. Use `docs/post-deploy-qa-protocol.md` as the standing runbook.

Minimum universal checks include deployment status, `/health`, `/openapi.json`, security headers, critical OpenAPI route presence, auth gates, and sanitized logs. Frontend deploys additionally require live route/header checks, Playwright route/render smoke when available, live bundle marker checks, payment/wallet regression checks, admin/scheduler exposure checks, and localStorage authority checks. Backend/runtime deploys additionally require task-runtime aggregate checks when relevant. Docs-only deploys still require universal post-deploy checks because they can trigger Railway deploys.
