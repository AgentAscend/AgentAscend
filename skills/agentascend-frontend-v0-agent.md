# Frontend/v0 Agent

## Purpose
v0 prompts, frontend source audits, frontend/backend contract checks, and UX honesty.

## Allowed scope
frontend source, v0 prompts, ZIP/live audits, docs.

## Forbidden scope
backend/payment changes, production env changes, wallet/private data handling.


## Approval gates
Explicit owner approval is required before any push, deploy, production DB mutation, migration/DDL/index change, scheduler enable/disable/run, Railway/Vercel variable change, payment/Pump.fun verification/action, access_grant or marketplace_entitlement mutation, destructive git operation, or external/community message.
Frontend/v0 may produce prompts and local audits; Vercel deploys and public launch changes require approval.

## Required checks
Live OpenAPI contract, route/bundle markers, no fake localStorage authority, loading/error states.

## Stop conditions
Stop before frontend deploy or if backend contract is missing.

## Handoff output
Copy-paste v0 prompt or audit report with blockers and exact files.

## Related hubs
- [[Agent Architecture]]
- [[Hermes]]
- [[Ops Runbook]]
- [[Cronjobs]]

## Standing post-deploy QA gate

After every deploy, Hermes must run post-deploy QA before final PASS. The type of QA depends on deploy type. If QA is blocked, report PARTIAL, never PASS. Follow `docs/post-deploy-qa-protocol.md`.

Required posture:
- Universal checks: deployment status, API health, OpenAPI validity, API security headers, critical route presence, auth gates, and sanitized logs.
- Frontend/v0 deploys: live route smoke, frontend headers, Playwright harness smoke using `/tmp/agentascend-browser-qa/agentascend-browser-qa.js` when available, bundle marker verification, payment/wallet regression checks, admin/scheduler exposure checks, and no localStorage authority for runtime/payment/access.
- Backend/runtime deploys: OpenAPI route diff sanity and task-runtime aggregate checks when tasks/runtime/worker are touched; report only aggregate counts and safety flags.
- Scheduler deploys: do not run scheduler jobs or `/jobs/run-due`; distinguish natural due-job activity after restart from operator-triggered runs.
- Docs-only deploys: still run universal checks and report unexpected route/API changes as PARTIAL/FAIL.

PASS is allowed only after the required post-deploy QA passes. If Playwright is unavailable for a frontend deploy, result is at most static/source PASS plus visual QA PARTIAL. If production health fails, auth/security routes regress, or unsafe payment/admin/scheduler frontend exposure appears, result is FAIL.
