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
1. Frontend product polish remains the main bottleneck now that the runtime loop is live and owner-verified.
2. Full visual workflow graph editing, branching, output schemas, output UX, task detail, execution detail, deployment events/log UX, settings persistence, token/community polish remain incomplete; owner-isolation for basic workflow create/save/read/run is verified.
3. localStorage must not grant paid access, marketplace ownership/install, workflow ownership, graph state, payment verification, auth bypass, or production settings authority.
4. Remaining Pump.fun/Solana runtime dependency advisories are accepted/monitored, not eliminated.
5. Legacy Telegram Hermes cronjobs remain enabled but are high-risk until converted/paused/removed with owner approval.
6. Original local `main` is diverged from `origin/main`; use clean worktrees until reconciled.

## Superseded / no longer current blockers
- HSTS absent: superseded by live HSTS/security-header checks.
- Replay-index migration pending: superseded by preflight PASS / DDL not needed now.
- Exact `tx_signature` binding future work: superseded by deployed hardening.
- Controlled Pump.fun payment regression pending/partial: superseded by 2026-05-03 PASS archive.
- Forge routes not live: superseded by live OpenAPI.
- Tasks/outputs/executions backend-required blocker: superseded by runtime worker and owner-verified frontend loop.
- Workflow owner-isolation unverified: superseded by 2026-05-09 live QA PASS archived at [[raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa]].
- Task queue worker disabled: superseded by audited enablement.
- Telegram auto-send risk: superseded by report-only/no-send default, though outbound sends still need owner approval.
- Old failed deploy notes: superseded by later successful Railway deployments.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[Roadmap]]
