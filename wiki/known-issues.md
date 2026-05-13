---
type: wiki
project: AgentAscend
aliases:
  - Known Issues
  - known-issues
---

# Known Issues

## Summary
Known issues are current unresolved product, integration, or hardening risks. Stale phase blockers should be marked superseded and should not be treated as current launch blockers.

## Components
- Payment/access auditability risks.
- Frontend/runtime truth and polish risks.
- Scheduler, cronjob, dependency, and git hygiene risks.
- Superseded blockers retained for historical clarity.

## Current high-priority issues
1. Historical/null-heavy payment↔grant linkage rows, if any, remain audit-only; future-path linkage hardening is deployed and no production backfill was performed. Any cleanup/backfill requires future owner approval.
2. v0 UI polish must continue to derive runtime truth from live backend Forge routes, Command Center, deployment events, tasks, outputs, executions, workflows, payment/access truth, and not stale placeholders.
3. Workflow builder remains partially live: owner-isolation passed, but node configuration/labels and richer run-history detail still need product polish; full visual graph editing remains later.
4. localStorage must not grant paid access, marketplace ownership/install, payment verification, auth bypass, production settings authority, Agent card metrics, workflow ownership, graph state, or runtime status.
5. Continue watching for stale user-facing `Backend Required` copy in live app advanced/preview surfaces.
6. Remaining Pump.fun/Solana runtime dependency advisories are accepted/monitored, not eliminated.
7. Multi-agent runtime architecture is still planning-only.
8. Git repository is diverged/noisy (`main` ahead/behind `origin/main` observed 8/8 on 2026-05-12); no push/deploy until reconciliation scope is explicit.

## Superseded / no longer current blockers
- HSTS absent: superseded by live HSTS/security-header checks.
- Replay-index migration pending: superseded by preflight PASS / DDL not needed now.
- Exact `tx_signature` binding future work: superseded by deployed hardening.
- Future-path payment↔grant linkage implementation pending: superseded by deployed commit `7cc1c6a986e1e2a1896b5e8e5b62b36917bccc70`; historical repair remains proposal-only.
- Controlled Pump.fun payment regression pending/partial: superseded by 2026-05-03 PASS archive.
- Forge routes not live: superseded by live OpenAPI evidence.
- Core logged-in runtime loop blocked: superseded by owner-assisted QA and Hermes 2026-05-11 full signed-in functional UX PASS WITH CAVEATS.
- Workflow auth/ownership privacy blocker: superseded by live workflow owner-isolation QA PASS archived at [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa]].
- Task queue worker disabled: superseded by audited enablement.
- Telegram auto-send risk: superseded by report-only/no-send default, though outbound sends still need owner approval.
- Old failed deploy baselines: superseded by later successful deploys and live health/OpenAPI checks.
- Paused Hermes documentation/strategy/roadmap cronjob errors: superseded by 2026-05-12 retirement/removal and safer active report-only jobs.

## Notes
- Keep unresolved items evidence-linked and avoid resurrecting superseded launch blockers.
- Do not treat local payment/access findings as production facts until scope is verified.

## Recent Evidence
- [[raw/system-cleanup/2026-05-12-project-cleanup-cronjob-review|2026-05-12 project cleanup and cronjob review]]
- [[raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup|2026-05-12 Hermes paused cronjob cleanup]]
- [[raw/db-integrity/2026-05-11|2026-05-11 database integrity check]]
- [[raw/payment-audits/2026-05-11|2026-05-11 payment system audit]]
- [[raw/frontend-qa/2026-05-11-full-signed-in-functional-ux-qa-pass|2026-05-11 full signed-in functional UX QA PASS WITH CAVEATS]]
- [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa|2026-05-09 workflow-builder owner-isolation QA PASS]]
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-12-payment-grant-linkage-tdd-report|2026-05-12 payment↔grant linkage TDD and deployment PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Roadmap]]
