# Hermes Swarm 24/7 Activation Plan

Status: initial report-only operating plan for AgentAscend while the owner is away.

Scope: Hermes swarm operation, local/report-only cron cadence, escalation gates, and future Telegram activation. This document is governance only; it does not approve production-risk actions.

## Purpose

Make the AgentAscend Hermes swarm usable for continuous observation and recommendations without giving agents authority to mutate production, run payments, change scheduler state, or send external messages.

## Operating levels

### Level 1 — Report-only

Allowed:
- Inspect local repo state.
- Inspect public production health and OpenAPI.
- Inspect Railway deployment status read-only.
- List Hermes cronjobs read-only.
- Produce local report files under `raw/automation-governance/` or Hermes local cron output.
- Recommend next owner-approved actions.

Forbidden:
- Code changes.
- Commits.
- Pushes.
- Deploys.
- Production DB mutation.
- Scheduler state changes.
- `/jobs/run-due`.
- Payment actions.
- Pump.fun verify.
- Access grant or marketplace entitlement changes.
- Telegram or external messages.

### Level 2 — Local implementation

Allowed only after explicit owner approval for the slice:
- Implement bounded local backend/frontend/docs/QA slices.
- Run local tests.
- Create local commits.
- Produce implementation and test reports.

Still forbidden by default:
- Push without an explicit safe-push approval.
- Deploys.
- Migrations or DB mutation.
- Scheduler changes or scheduler runs.
- Payment/Pump.fun verify/access/entitlement actions.
- External messages.

### Level 3 — Safe push

Allowed only after gates and explicit owner approval:
- Push isolated low-risk commits after exact commit scope review.
- Monitor automatic Railway deployment read-only if GitHub-to-Railway triggers.
- Verify `/health` and `/openapi.json` after deployment.

Still forbidden:
- Migrations/DDL/index creation or deletion.
- Railway/Vercel variable changes.
- Scheduler enable/disable/run.
- Payment actions or Pump.fun verify.
- Access/entitlement mutations.
- Telegram/external messages.

### Level 4 — Production-risk

Always requires explicit owner approval for the exact action.

Includes:
- Production DB mutation.
- Migrations, DDL, index creation/drop.
- Railway or Vercel variable changes.
- AgentAscend scheduler enable/disable/run.
- `/jobs/run-due`.
- Payment intents, payments, Pump.fun verify, wallet signing, revenue claims, buyback settings.
- Access grant or marketplace entitlement changes.
- Telegram sends, public posts, community replies, emails, or account actions.

## Recommended initial 24/7 mode

- All swarm agents start at Level 1 report-only.
- Backend Forge, Frontend/v0, Docs/Memory, and QA/Security may move to Level 2 only after the owner explicitly approves a bounded local slice.
- Payment/Access, Scheduler/Automation, and Marketing/Community stay Level 1 by default.
- Telegram reporting remains off until the owner approves exactly one no-secret Telegram canary.

## Initial local-only Hermes cron cadence

All initial cronjobs should use local delivery only. They should write local summaries and never send Telegram.

1. AgentAscend Swarm Daily Operator Report
   - Practical cadence: every 12 hours.
   - Purpose: health/OpenAPI, Railway status, git/origin status, pending local commits, current blockers, recommended next slice.

2. AgentAscend Swarm Daily Knowledge Hygiene Report
   - Practical cadence: daily.
   - Purpose: MEMORY/wiki/raw/skills drift, orphan notes, stale blockers, cleanup recommendations.

3. AgentAscend Swarm Backend/Frontend Contract Report
   - Practical cadence: every 2 days.
   - Purpose: OpenAPI route drift, frontend page gaps, v0/backend integration gaps.

4. AgentAscend Swarm Weekly Security/Dependency Report
   - Practical cadence: weekly.
   - Purpose: dependency audit summary, auth gate checks, payment/access aggregate health posture, secret scan status.

## Universal cron safety rules

Every local-only swarm cron prompt must be self-contained and include these hard rules:

- Deliver locally only.
- Do not send Telegram.
- Do not send external messages.
- Do not mutate production.
- Do not run AgentAscend scheduler jobs.
- Do not call `/jobs/run-due`.
- Do not run payments.
- Do not create payment intents.
- Do not call Pump.fun verify.
- Do not create/revoke access grants.
- Do not change marketplace entitlements.
- Do not change Railway or Vercel variables.
- Do not push or deploy.
- Do not print secrets, DB URLs, private RPC URLs, auth tokens, cookies, private keys, seed phrases, signed transactions, wallet-private data, raw task bodies, raw task outputs, raw DB rows, raw metadata, or raw payloads.
- Only write intentionally scoped local report output.

## Report paths

Preferred durable local reports:
- `raw/automation-governance/YYYY-MM-DD-swarm-daily-operator-report.md`
- `raw/automation-governance/YYYY-MM-DD-swarm-knowledge-hygiene-report.md`
- `raw/automation-governance/YYYY-MM-DD-swarm-contract-report.md`
- `raw/automation-governance/YYYY-MM-DD-swarm-security-dependency-report.md`

Hermes cron output artifacts may also be used for routine reports when the repo should not accumulate generated report noise.

## Future Telegram activation plan

Do not send Telegram until explicitly approved.

When approved, run exactly one no-secret Telegram canary:
- Message includes only health/OpenAPI booleans and local cron identity.
- No raw errors.
- No payment references.
- No wallet data.
- No DB data.
- No raw logs.
- No stack traces.

If the canary passes, propose a small subset of report summaries for Telegram delivery. Keep full reports local.

## Stop conditions

Stop and report PARTIAL/BLOCKED if:
- Current git state differs from expected scope.
- Production health/OpenAPI is down.
- Railway deployment is BUILDING or failed.
- A prompt would require production mutation or scheduler/payment action.
- Any secret-like value appears in a report.
- A cronjob cannot be created with local/no-delivery delivery.
- A local report would include raw logs, raw DB rows, raw task body/output, raw metadata, or raw payload.
