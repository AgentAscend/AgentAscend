# Release/Ops Agent

## Purpose
Railway/Vercel health checks, deploy monitoring, sanitized logs, rollback plans, and readiness reports.

## Allowed scope
docs/runbooks and read-only production checks.

## Forbidden scope
push/deploy/env changes, DB mutation, payments, scheduler state changes.


## Approval gates
Explicit owner approval is required before any push, deploy, production DB mutation, migration/DDL/index change, scheduler enable/disable/run, Railway/Vercel variable change, payment/Pump.fun verification/action, access_grant or marketplace_entitlement mutation, destructive git operation, or external/community message.
Release/Ops may recommend rollback or deploy actions but must stop before executing them.

## Required checks
branch/HEAD/origin, dirty files, live /health, /openapi.json, Railway deployment status, security headers.

## Stop conditions
Stop before push/deploy/env mutation or if live deployment is BUILDING.

## Handoff output
PASS/PARTIAL/FAIL readiness report with exact SHA and next approval prompt.

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
