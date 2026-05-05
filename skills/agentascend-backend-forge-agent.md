# Backend Forge Agent

## Purpose
Backend agents/workflows/tasks/outputs/runtime endpoints and tests-first backend slices.

## Allowed scope
backend app/routes/schemas/services/tests for Forge/runtime only.

## Forbidden scope
payment routes, scheduler state, production DB mutation, frontend changes unless approved.


## Approval gates
Explicit owner approval is required before any push, deploy, production DB mutation, migration/DDL/index change, scheduler enable/disable/run, Railway/Vercel variable change, payment/Pump.fun verification/action, access_grant or marketplace_entitlement mutation, destructive git operation, or external/community message.
Backend Forge may implement local TDD slices only when scoped; runtime-worker pushes also require aggregate queued/running/pending_approval task-state verification.

## Required checks
Read MEMORY.md, inspect git scope, write failing tests first, run focused/full tests, OpenAPI check.

## Stop conditions
Stop before push/deploy/migration or payment-adjacent touch.

## Handoff output
Changed files, tests, OpenAPI impact, migration need, approval prompt.

## Related hubs
- [[Agent Architecture]]
- [[Hermes]]
- [[Ops Runbook]]
- [[Cronjobs]]
