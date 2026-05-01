# Post Soft Launch Hardening Roadmap

Related: [[Roadmap]], [[Launch Readiness]], [[Agent Architecture]], [[Ops Runbook]]

## Current verdict
READY FOR SOFT LAUNCH / HARDENING ITEMS REMAIN.

## Completed and deployed
- Exact `tx_signature` binding hardening: PASS.
- Payment/access/marketplace aggregate audit: PASS previously, but this run could not re-call authenticated aggregate without a runtime admin token in the tool environment.
- HSTS: implemented and live.
- Launch evidence: archived with public txs, sanitized DB aggregate/admin lookup, and owner UI/accounting confirmation.

## Prioritized hardening sequence
1. Replay-index migration approval package and owner-approved DDL phase.
2. Node helper dependency cleanup matrix; prefer dev dependency remediation first.
3. Controlled payment regression canary: valid real payment, replay rejected, wrong-signature rejected, expired intent rejected, wrong user/wallet rejected, duplicate tx rejected.
4. Held scheduler-job audits one class at a time.
5. Multi-agent architecture setup, starting with Docs/Memory and QA/Security.
6. Ongoing Obsidian graph maintenance automation.

## Next executable prompts
1. Replay DDL: see `docs/replay-index-migration-preflight.md`.
2. Dependency cleanup: see `docs/node-helper-dependency-audit-plan.md`.
3. Payment regression: see `docs/controlled-payment-regression-plan.md`.
4. Scheduler audits: see `docs/held-scheduler-job-audit-plan.md`.
5. Multi-agent setup: see `docs/multi-agent-architecture-plan.md`.
6. Graph maintenance cron proposal: see `docs/obsidian-graph-maintenance-runbook.md`.
