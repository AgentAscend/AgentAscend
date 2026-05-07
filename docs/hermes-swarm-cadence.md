# Hermes Swarm Cadence

Status: phased automation plan. AgentAscend should begin report-only and raise autonomy only after gates are proven.

## Level 0 — Manual
Owner prompts each step. Hermes reports or performs one explicitly requested scoped action at a time.

## Level 1 — Report-only swarm
Agents audit and report. No code changes, no push, no production mutation, no scheduler changes, no external messages.

## Level 2 — Local implementation swarm
Agents may implement local Backend/Frontend/Docs/QA slices when explicitly scoped. Tests, diff checks, and secret scans are required. No push without gates.

## Level 3 — Safe push/deploy swarm
Agents may push low-risk commits only after exact owner approval, clean scope, passing tests, production preflight, and post-push deploy monitoring. Still excludes migrations/env/scheduler/payment/access/external messages.

## Level 4 — Production-risk actions
Always requires explicit owner approval for the exact action. Includes production DB mutation, migrations/DDL/index creation/drop, Railway/Vercel variable changes, scheduler enable/disable/run, /jobs/run-due, Telegram/external messages, payment/Pump.fun verification/actions, wallet signing, revenue claims, buyback settings, and access/entitlement changes.

## Current recommendation
- Backend Forge, Frontend/v0, Docs/Memory, QA/Security: Level 2 locally; Level 3 only for exact low-risk commits after gates.
- Payment/Access, Scheduler/Automation, Marketing/Community: Level 1 by default.
- Production DB/payment/scheduler/external messaging: Level 4 always.

## Daily report-only rhythm
- Release/Ops: health/OpenAPI/deployment/git state.
- Scheduler/Automation: scheduler posture and Hermes cron health without sends/runs.
- Docs/Memory: stale notes and MEMORY/wiki drift proposal.
- QA/Security: test/security/dependency gates.

## Weekly rhythm
- Frontend/backend contract drift.
- Runtime/Forge backlog reprioritization.
- Payment/access aggregate audit design review without production verification.
- Community drafts for internal review only.

## Standing post-deploy QA gate

Level 3 push/deploy work cannot end at deployment success. After every deploy, Hermes must run the matching post-deploy QA checklist from `docs/post-deploy-qa-protocol.md` before final PASS. If required QA is blocked, report PARTIAL with the blocker and next safe step. Frontend deploys must use the local Playwright harness when available; backend/scheduler deploys must include health/OpenAPI/routes/auth/security/log checks and task-runtime aggregate checks when relevant.

## Related
- [[current-project-state|Current Project State]]
- [[AgentAscend]]
- [[Hermes]]
- [[Cronjobs]]
