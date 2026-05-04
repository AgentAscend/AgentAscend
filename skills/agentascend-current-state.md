# AgentAscend Current State

## When to use
Use before any AgentAscend planning, audit, docs, v0 prompt, or implementation session.

## Required checks
1. Read `MEMORY.md`.
2. Verify git branch, HEAD, origin/main, ahead/behind, status, recent log.
3. Verify production read-only before claiming deployed state:
   - `/health` HTTP 200
   - `/openapi.json` HTTP 200 valid JSON
   - Railway web/scheduler deployment status and commit when needed
4. Do not assume local commits are deployed unless origin/Railway/OpenAPI confirm it.

## Current baseline as of 2026-05-04
- Production backend-feature baseline: `26aa8abca8bc5bcf8f12a25a5fb9a222f5576eaa`; later docs-only cleanup commits may redeploy without changing OpenAPI/backend behavior. Verify Railway before acting.
- Forge backend routes live: capabilities/templates, agent definitions, run/deploy/workflow bridges, Command Center, deployment events.
- Pump.fun controlled regression PASS: [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]].
- Replay-index DDL not needed now: [[raw/security-reviews/2026-05-02-replay-index-preflight]].
- Scheduler eight-job workload enabled/audited; three jobs held.
- Frontend/v0 is the next major bottleneck.

## Stop conditions
Stop and report if live API is down, OpenAPI lacks expected routes, git has backend/frontend/test/package dirtiness outside scope, or any task would mutate production/payment/scheduler state without approval.
