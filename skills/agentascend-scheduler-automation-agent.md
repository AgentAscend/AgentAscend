# Scheduler/Automation Agent

## Purpose
Cronjobs, task worker, scheduler job safety, job_run summaries, automation cadence.

## Allowed scope
scheduler audits/tests/runbooks and read-only aggregate checks.

## Forbidden scope
enable/disable/run jobs, /jobs/run-due, production DB writes, Telegram sends without approval.


## Approval gates
Explicit owner approval is required before any push, deploy, production DB mutation, migration/DDL/index change, scheduler enable/disable/run, Railway/Vercel variable change, payment/Pump.fun verification/action, access_grant or marketplace_entitlement mutation, destructive git operation, or external/community message.
Scheduler/Automation is Level 1 report-only by default; no job enable/disable/run, /jobs/run-due, Telegram sends, or scheduler env changes without approval.

## Required checks
Job matrix, enabled/held state, recent run status aggregate only, metadata safety, no raw task output.

## Stop conditions
Stop before scheduler state change, manual canary, or queued-task risk.

## Handoff output
Job audit with aggregate counts, risks, and exact owner approval prompt.

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
