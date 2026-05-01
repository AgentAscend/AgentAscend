---
type: wiki
project: AgentAscend
aliases:
  - Ops Runbook
  - Operations Runbook
---

# Ops Runbook

## Summary
The Ops Runbook is the hub for safe production checks, launch-readiness gates, scheduler boundaries, docs maintenance, and owner-approval prompts.

## Key Current Status
Current safe ops posture: public health/OpenAPI/security checks are allowed; admin aggregate audits are read-only and sanitized; payments, migrations, scheduler changes, env changes, and deploy actions require explicit approval.

## Important Links
- [[Launch Readiness]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
- [[Cronjobs]]
- [[known-issues|Known Issues]]
- [[Deployment]]

## Recent Evidence
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-24-2332]]
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-25-0000]]
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-25-0401]]
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-25-0728]]
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-25-0731]]
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-25-0800]]
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-25-0806]]
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-25-1200]]
- [[raw/deploy-readiness/2026-04-29-payment-critical-env-vars|2026-04-29 Payment Critical Env Vars]].
- [[raw/post-deploy-audits/2026-04-27-marketplace-live-stability|2026-04-27 Post-deploy Audit]].

## Open Questions / Next Steps
- Keep preflight checks read-only unless owner approves a specific mutation.
- Use owner approval sentence before replay-index migration DDL.
- Keep secrets out of reports and docs.
