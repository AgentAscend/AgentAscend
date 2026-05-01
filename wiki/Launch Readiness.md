---
type: wiki
project: AgentAscend
aliases:
  - Launch Readiness
  - launch-readiness
---

# Launch Readiness

## Summary
Launch readiness tracks whether AgentAscend is safe to present publicly: live API health, frontend/backend contract, payment/access proof, scheduler posture, and remaining hardening.

## Key Current Status
Current soft-launch verdict: READY FOR SOFT LAUNCH / HARDENING ITEMS REMAIN. Live API health/OpenAPI/security gates are passing. Pump.fun exact tx_signature binding is implemented and deployed. Replay-index migration and Node dependency audit remain pending.

## Important Links
- [[AgentAscend]]
- [[Pump.fun Tokenized Agent Payments]]
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[scheduler|Scheduler]]
- [[known-issues|Known Issues]]
- [[Ops Runbook]]

## Recent Evidence
- 2026-05-01: Linked evidence [[raw/backend-health/2026-04-29-0803]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-25]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-26]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-27]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-28]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-29]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-30]]
- [[raw/launch-evidence/2026-04-30-pumpfun-live-payment-evidence|2026-04-30 Pump.fun Live Payment Evidence]] — public payment/claim evidence plus owner UI/accounting confirmation.
- [[raw/launch-evidence/2026-04-29-pumpfun-live-payment-canary|2026-04-29 Pump.fun Live Payment Canary]] — earlier canary archive.
- [[raw/post-deploy-audits/2026-04-27-marketplace-live-stability|2026-04-27 Marketplace Live Stability Audit]] — post-deploy audit context.

## Open Questions / Next Steps
- Owner-approved replay-index migration DDL phase.
- Separate dependency-audit/cleanup phase for Node vulnerabilities.
- Future owner-approved controlled payment regression for real valid payment and replay/wrong-signature rejection.
- Held scheduler-job audits before enabling any held jobs.

## Exact tx_signature Binding Hardening — Completed 2026-04-30
Status: implemented and deployed.

Commit: `453df65aec69f7aa95b20bb1752f7d3af97ad488` (`Harden Pump.fun verification tx signature binding`).

What changed:
- Backend passes the user-submitted `tx_signature` to the Node helper as `txSignature`.
- Node helper validates `txSignature` format.
- Helper derives the exact invoice PDA using Pump.fun SDK `getInvoiceIdPDA`.
- Helper checks the submitted signature appears in `getSignaturesForAddress(invoice PDA)`.
- Helper fetches the submitted transaction with confirmed commitment and rejects missing/failed transactions.
- Helper parses logs only while the current Solana log stack is inside the Pump.fun agent-payments program.
- Helper decodes `AgentAcceptPaymentEvent` and exact-matches user, tokenizedAgentMint, currencyMint, amount, memo, startTime, endTime, and invoiceId.
- Only after an exact event match does the helper call SDK `validateInvoicePayment`.
- Helper returns `signatureBound` on successful helper responses.

Remaining risks:
- `getSignaturesForAddress(invoice PDA, limit 1000)` could theoretically miss a submitted tx if the invoice PDA has more than 1000 newer transactions.
- `getTransaction` currently uses `maxSupportedTransactionVersion: 0`.
- A future owner-approved controlled payment regression should verify deployed acceptance of a real valid Pump.fun payment and rejection of replay/wrong-signature cases.
- Node dependency vulnerabilities remain for a separate dependency-audit phase.
