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

## Current high-priority issues
1. Logged-in frontend remains placeholder-heavy across overview, agents, deployments, workflows, tasks, outputs, executions, token, community, and settings.
2. v0 UI must be wired to live backend Forge routes, Command Center, deployment events, and execution/payment/access truth.
3. localStorage must not grant paid access, marketplace ownership/install, payment verification, auth bypass, or production settings authority.
4. Remaining Pump.fun/Solana runtime dependency advisories are accepted/monitored, not eliminated.
5. Multi-agent runtime architecture is still planning-only.

## Superseded / no longer current blockers
- HSTS absent: superseded by live HSTS/security-header checks.
- Replay-index migration pending: superseded by preflight PASS / DDL not needed now.
- Exact `tx_signature` binding future work: superseded by deployed hardening.
- Controlled Pump.fun payment regression pending/partial: superseded by 2026-05-03 PASS archive.
- Forge routes not live: superseded by live OpenAPI at commit `26aa8ab`.
- Task queue worker disabled: superseded by audited enablement.
- Telegram auto-send risk: superseded by report-only/no-send default, though outbound sends still need owner approval.
- Old c9253a5 failed deploy: superseded by later successful deploys through commit `26aa8ab`.

## Recent Evidence
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/security-reviews/2026-05-02-node-helper-dependency-audit|2026-05-02 Node helper dependency audit baseline]]
- Commits: `239fa79` dev dependency cleanup, `a8ad3ba` Pump.fun SDK 3.0.3, `2d00a31` controlled regression evidence, `5ac6d06` Forge definitions, `34a8c21` Command Center, `{prod_short}` deployment events.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Roadmap]]
