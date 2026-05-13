---
type: wiki
project: AgentAscend
aliases:
  - Roadmap
---

# Roadmap

## Summary
AgentAscend's near-term roadmap has moved from backend-hardening-only into runtime product integration, but a new payment↔grant auditability investigation should be handled before broader launch expansion. The core signed-in runtime loop is verified; the next work should combine local TDD payment invariant hardening with continued honest frontend/runtime polish.

## Components
- Payment↔grant linkage hardening and auditability planning.
- Frontend/v0 runtime polish against backend source-of-truth.
- Git reconciliation and cronjob/report-first hygiene.
- Later marketplace, ASND utility, and multi-agent architecture expansion.

## Immediate priorities
1. Payment↔grant linkage hardening plan:
   - verify production-vs-local scope without mutating data,
   - write failing tests for payment-created grants carrying `payment_id` and `intent_reference`,
   - design a safe backfill plan separately from code-level forward invariants,
   - do not run production backfill or payment/access mutations without owner approval.
2. Frontend/v0 runtime polish against live backend truth:
   - workflow node configuration labels/editing,
   - richer workflow run-history/runtime detail,
   - output search/export/bulk UX,
   - task/execution/output detail UX,
   - deployment events/log-streaming UX.
3. Keep removing fake/localStorage authority from logged-in app pages.
4. Add backend slices one at a time only when frontend polish proves a real missing endpoint.
5. Reconcile diverged git history before any push/deploy.

## Hardening watch items
- Treat payment↔grant linkage/auditability as active launch-risk investigation until closed.
- Monitor Pump.fun/Solana transitive dependency advisories; do not blindly run audit fixes.
- Keep replay-index DDL on hold unless schema drift appears; current preflight says DDL not needed.
- Keep `default-roadmap-review` disabled/manual unless owner approves enablement under documented conditions.
- Keep payment/security/tokenomics/public launch decisions under owner/Premium Strategic review.
- Keep Hermes cronjobs report-first; 2026-05-12 cleanup leaves 11 active/healthy jobs and retired three paused-error jobs.

## Notes
- Keep roadmap updates evidence-linked and manual; do not auto-reprioritize strategic/payment/tokenomics choices.
- Group implementation work into small isolated commits with standing QA after any future push/deploy.

## Later phases
- Multi-agent role setup after frontend/backend product contracts stabilize.
- Marketplace creator product polish and clearer install/use lifecycle.
- ASND utility expansion grounded in actual platform usage.

## Recent Evidence
- [[raw/system-cleanup/2026-05-12-project-cleanup-cronjob-review|2026-05-12 project cleanup and cronjob review]]
- [[raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup|2026-05-12 Hermes paused cronjob cleanup]]
- [[raw/frontend-qa/2026-05-11-full-signed-in-functional-ux-qa-pass|2026-05-11 full signed-in functional UX QA PASS WITH CAVEATS]]
- [[raw/db-integrity/2026-05-11|2026-05-11 database integrity check]]
- [[raw/payment-audits/2026-05-11|2026-05-11 payment system audit]]
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[known-issues|Known Issues]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Agent Architecture]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
