---
type: wiki
project: AgentAscend
aliases:
  - Pump.fun Tokenized Agent Payments
  - Pumpfun Payments
  - Tokenized Agent Payments
---

# Pump.fun Tokenized Agent Payments

## Summary
Pump.fun tokenized-agent payments are AgentAscend's current marketplace payment path. Backend-owned payment intents and exact SDK verification are required before access or marketplace entitlement is granted.

## Current status
- Live routes: `POST /payments/pumpfun/create`, `POST /payments/pumpfun/verify`.
- Controlled regression PASS: public tx `2ydGT5uPArgKx2WkiBZ9xNm17ap6WB4BVznJTNwThDThS8qia6zT5vq76CHgEDFwW4gj7FfMyTHJweobt9K5UhrR`.
- Payment reference: `pumpfun:agentascendai:0967b710095e47bba1e12d4149639d9e`.
- Backend evidence: payment found, payment_id present, payment intent completed, verification_status verified, access grant present, listing-scoped true, marketplace entitlement present.
- Duplicate/replay aggregate groups remained zero.
- Exact submitted `tx_signature` binding is implemented and deployed.
- Runtime helper dependency: `@pump-fun/agent-payments-sdk` 3.0.3.

## Boundaries
- AgentAscend does not sign user transactions.
- AgentAscend does not implement duplicate Pump.fun buyback/burn logic.
- Access must not be granted from browser confirmation alone.
- Do not call verify or create payment intents during documentation/audit cleanup.

## Recent Evidence
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/security-reviews/2026-05-02-node-helper-dependency-audit|2026-05-02 Node helper dependency audit baseline]]
- Commits: `239fa79` dev dependency cleanup, `a8ad3ba` Pump.fun SDK 3.0.3, `2d00a31` controlled regression evidence, `5ac6d06` Forge definitions, `34a8c21` Command Center, `{prod_short}` deployment events.

## Relationships
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[Launch Readiness]]
- [[current-project-state|Current Project State]]
- [[Solana Integration]]

## Superseded notes
- The 2026-05-03 partial/no-response canary is superseded by the later PASS archive.
- Older abandoned-intent evidence is retained as recovery context, not current blocker status.
- Runtime dependency audit advisories remain monitored; do not treat npm audit suggestions as safe automatic fixes.
