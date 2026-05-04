---
type: wiki
project: AgentAscend
aliases:
  - Payment Access Control
  - Access Control
  - Token Gated Access
---

# Payment Access Control

## Summary
Payment access control defines how AgentAscend grants paid access only after backend-owned payment verification succeeds. The backend is always the authority for payment, access grants, and marketplace entitlements.

## Current status
- Pump.fun create/verify routes are live and auth-gated.
- Controlled regression proved a listing-scoped payment can create/verify a completed payment, access grant, and marketplace entitlement.
- Exact `tx_signature` binding is deployed.
- Replay-index preflight found duplicate groups at zero and existing equivalent unique constraints/indexes; no DDL is needed now.
- Frontend must refresh access/entitlement from backend and must not use localStorage as paid-access authority.

## Rules
- Never grant access from client-side flags.
- Never trust browser-supplied payment status, ownership, amount authority, or install entitlement.
- Payment/access/scheduler mutations require explicit owner approval and are out of scope for docs cleanup.
- Public tx signatures and public payment references may be recorded only when already part of launch evidence.

## Recent Evidence
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/security-reviews/2026-05-02-node-helper-dependency-audit|2026-05-02 Node helper dependency audit baseline]]
- Commits: `239fa79` dev dependency cleanup, `a8ad3ba` Pump.fun SDK 3.0.3, `2d00a31` controlled regression evidence, `5ac6d06` Forge definitions, `34a8c21` Command Center, `{prod_short}` deployment events.

## Relationships
- [[Pump.fun Tokenized Agent Payments]]
- [[Launch Readiness]]
- [[marketplace|Marketplace]]
- [[known-issues|Known Issues]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]

## Superseded blockers
- “Access grant integrity blocked by DB aggregate audit” is superseded by admin aggregate/pass evidence for current duplicate groups.
- “Replay-index migration pending” is superseded by DDL-not-needed preflight.
- “Exact tx_signature binding future work” is superseded by deployed hardening.
