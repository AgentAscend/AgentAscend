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
Pump.fun tokenized-agent payments are the marketplace payment path for AgentAscend. Backend-owned payment intent/invoice verification is required before access is granted.

## Key Current Status
Pump.fun create/verify routes are deployed and auth-gated. Exact tx_signature binding hardening is implemented and deployed at commit 453df65aec69f7aa95b20bb1752f7d3af97ad488.

## Important Links
- [[Payment Access Control]]
- [[marketplace|Marketplace]]
- [[Launch Readiness]]
- [[Payment System]]
- [[Tokenized Agents]]
- [[Solana Integration]]

## Recent Evidence
- [[raw/launch-evidence/2026-04-30-pumpfun-live-payment-evidence|2026-04-30 Pump.fun Live Payment Evidence]].
- [[raw/tokenized-agent-flow/2026-04-27|2026-04-27 Tokenized Agent Flow Notes]].

## Open Questions / Next Steps
- Run replay-index migration only after owner approval.
- Audit Node dependencies separately.
- Consider future pagination/version support for invoice PDA signature lookup and transaction versions.
- Run a future controlled payment regression only with explicit owner approval.

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
