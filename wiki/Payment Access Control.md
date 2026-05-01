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
Payment access control defines how AgentAscend grants paid access only after backend-owned payment verification succeeds.

## Key Current Status
Backend remains the source of truth. Pump.fun access must be granted only after stored payment intent/invoice verification passes. Exact tx_signature binding is deployed; replay-index migration remains pending.

## Important Links
- [[Token Gated Access]]
- [[Payment System]]
- [[Payment Verification]]
- [[Pump.fun Tokenized Agent Payments]]
- [[Launch Readiness]]
- [[known-issues|Known Issues]]

## Recent Evidence
- [[raw/security-reviews/2026-04-27|2026-04-27 Security Review]].
- [[raw/launch-evidence/2026-04-30-pumpfun-live-payment-evidence|2026-04-30 Pump.fun Live Payment Evidence]].

## Open Questions / Next Steps
- Owner-approved replay-index migration.
- Preserve backend-only access authority; never use frontend-only paid flags.
- Keep unauthenticated payment/admin probes fail-closed.

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
