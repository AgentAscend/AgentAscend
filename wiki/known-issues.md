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
- Launch-risk investigations.
- Superseded blockers.
- Frontend/backend source-of-truth risks.
- Payment/access hardening watch items.

## Current high-priority issues
1. Payment↔grant ledger linkage/auditability needs investigation: 2026-05-11 read-only local DB/payment reports found completed payments without active grant linkage by `payment_id` and active grants null-heavy for `payment_id`/`intent_reference`. Treat as a launch-risk investigation until production-vs-local scope, backfill path, and forward invariants are verified.
2. v0 UI polish must continue to derive runtime truth from live backend Forge routes, Command Center, deployment events, tasks, outputs, executions, workflows, payment/access truth, and not stale placeholders. Run Agent runtime path plus Latest Run `Open Task`, Output Library search/preview basics, Deployment Events UX, Workflow Run-History / Execution Trace UX, and Runtime Detail / Output Polish are production/browser-QA verified; do not reintroduce fake runtime/export/load-more/search authority or raw metadata/payload rendering.
3. Workflow builder remains partially live: owner-isolation and run-history execution trace preview passed, but node configuration/labels and full visual graph editing remain later product polish.
4. localStorage must not grant paid access, marketplace ownership/install, payment verification, auth bypass, production settings authority, Agent card metrics, workflow ownership, graph state, or runtime status.
5. Continue watching for stale user-facing `Backend Required` copy in live app advanced/preview surfaces; exact Run Agent success toast/action visibility remains optional polish because `Agent run queued` was not observed after successful production runs, while runtime and Latest Run `Open Task` navigation passed. Prior stale/mixed PR #4 report references are resolved; current run-history state is PR #5.
6. Remaining Pump.fun/Solana runtime dependency advisories are accepted/monitored, not eliminated.
7. Multi-agent runtime architecture is still planning-only.
8. Git repository is diverged/noisy (`main` ahead/behind `origin/main` observed 8/8 on 2026-05-12); no push/deploy until reconciliation scope is explicit.

## Superseded / no longer current blockers
- Output search/export/bulk UX not live: superseded by 2026-05-13 live Output Library QA PASS WITH CAVEATS; backend listing, local loaded-list search copy, disabled unsupported Export All/Load More, and output preview are verified.
- HSTS absent: superseded by live HSTS/security-header checks.
- Replay-index migration pending: superseded by preflight PASS / DDL not needed now.
- Exact `tx_signature` binding future work: superseded by deployed hardening.
- Controlled Pump.fun payment regression pending/partial: superseded by 2026-05-03 PASS archive.
- Forge routes not live: superseded by live OpenAPI evidence.
- Core logged-in runtime loop blocked: superseded by owner-assisted QA, Hermes 2026-05-13 live Output Library/runtime QA PASS WITH CAVEATS, 2026-05-16 production Run Agent UI click-path QA, and 2026-05-17 Run Agent toast/drawer follow-up QA PASS WITH POLISH CAVEAT.
- Task/execution/output detail polish not live: superseded by 2026-05-17 Runtime Detail / Output Polish live PASS archived at [[raw/frontend-qa/2026-05-17-runtime-detail-output-polish-live-pass]].
- Workflow run-history detail not live: superseded by 2026-05-17 Workflow Run-History / Execution Trace UX live PASS archived at [[raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass]].
- Deployment Events UX not live: superseded by PR #4 merge/live evidence recorded with the 2026-05-17 current-state update.
- Workflow auth/ownership privacy blocker: superseded by live workflow owner-isolation QA PASS archived at [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa]].
- Task queue worker disabled: superseded by audited enablement.
- Telegram auto-send risk: superseded by report-only/no-send default, though outbound sends still need owner approval.
- Old failed deploy baselines: superseded by later successful deploys and live health/OpenAPI checks.
- Paused Hermes documentation/strategy/roadmap cronjob errors: superseded by 2026-05-12 retirement/removal and safer active report-only jobs.

## Recent Evidence
- [[raw/frontend-qa/2026-05-17-runtime-detail-output-polish-live-pass|2026-05-17 Runtime Detail / Output Polish live PASS]]
- [[raw/frontend-qa/2026-05-17-run-agent-toast-drawer-followup-production-qa|2026-05-17 Run Agent toast/drawer follow-up QA PASS WITH POLISH CAVEAT]]
- [[raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass|2026-05-17 Workflow Run-History / Execution Trace UX live PASS]]
- [[raw/frontend-qa/2026-05-16-production-run-agent-click-path-pass-with-caveat|2026-05-16 production Run Agent UI click path QA PASS WITH CAVEAT]]
- [[raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats|2026-05-13 live Output Library and runtime QA PASS WITH CAVEATS]]
- [[raw/system-cleanup/2026-05-12-project-cleanup-cronjob-review|2026-05-12 project cleanup and cronjob review]]
- [[raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup|2026-05-12 Hermes paused cronjob cleanup]]
- [[raw/db-integrity/2026-05-11|2026-05-11 database integrity check]]
- [[raw/payment-audits/2026-05-11|2026-05-11 payment system audit]]
- [[raw/frontend-qa/2026-05-11-full-signed-in-functional-ux-qa-pass|2026-05-11 full signed-in functional UX QA PASS WITH CAVEATS]]
- [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa|2026-05-09 workflow-builder owner-isolation QA PASS]]
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]

## Notes
Known issues should stay current and should not preserve stale blockers as active risks after live QA or source-of-truth evidence supersedes them.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Roadmap]]
