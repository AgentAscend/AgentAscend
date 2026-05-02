---
type: wiki
project: AgentAscend
aliases:
  - Known Issues
  - known-issues
---

# Known Issues

## Summary
Known issues track currently unproven or broken flows. They are blockers until source and live verification pass.

## Components
- Current state: Known issues track currently unproven or broken flows. They are blockers until source and live verification pass.
- Endpoints/files involved:
  - `raw/investigations/2026-04-25-current-issue-queue.md`
  - `wiki/frontend-v0-workflow.md`
  - `wiki/tasks-outputs.md`
  - `wiki/database.md`

## What is working
- Issue queue is documented.
- Backend health/scheduler basics are operational.

## What is broken or unproven
- /app/outputs Radix SelectItem empty value crash.
- Tasks disappeared after signout/signin.
- Postgres live migration not fully proven.
- v0 task/output wiring status unknown.
- Workflow create incomplete.
- Deployment/logs/scale endpoints/actions missing.

## Next actions
- Triage issues in priority order: outputs crash, auth/task persistence, Postgres live persistence, v0 wiring, workflow create, ops action endpoints.

## Relationships
- [[Auth]]
- [[Database]]
- [[Marketplace]]
- [[Community]]
- [[Tasks Outputs]]
- [[Scheduler]]
- [[Frontend v0 Workflow]]
- [[Deployment]]
- [[Known Issues]]
- [[Roadmap]]

## Safety notes
- Do not patch production blindly.
- Use throwaway accounts and report-first probes.

## Notes
This page was created/updated during the 2026-04-25 overnight knowledge/runtime improvement cycle. Treat source-level facts separately from live-production verification.

## 2026-04-30 Knowledge Graph Status Update
- Raw launch evidence, tokenized-agent, scheduler/cronjob, deploy-readiness, security, and Hermes runtime notes now link back to this hub graph.
- Exact Pump.fun `tx_signature` binding hardening is implemented and deployed at commit `453df65aec69f7aa95b20bb1752f7d3af97ad488`.
- Replay-index preflight passed on 2026-05-02; DDL is not needed now because existing valid indexes/constraints already satisfy the hardening target.
- Node dependency audit completed read-only on 2026-05-02; dependency cleanup remains pending and should be split into dev-only cleanup first, then runtime Pump.fun/Solana compatibility review.

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

## Recent Evidence
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-25]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-26]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-27]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-28]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-29]]
- 2026-05-01: Linked evidence [[raw/db-integrity/2026-04-30]]

## 2026-05-02 Replay-index Preflight Update
- Replay-index hardening target is satisfied by existing valid production indexes/constraints.
- Migration DDL should not be run unless future schema drift or duplicate risk appears.
- Future DDL should inspect semantic equivalence first, not just `IF NOT EXISTS` by name.
- Existing production constraints/indexes must not be dropped unless separately inspected and approved.
- If future replay-index DDL is ever needed, concurrent index create/drop statements cannot run inside normal transactions.
- Remaining hardening focus moves to Node dependency audit/cleanup, controlled payment regression, optional held scheduler enablement decisions, multi-agent architecture setup, and frontend/product polish.

## 2026-05-02 Node Helper Dependency Audit Update
- Read-only `npm audit --json`, `npm outdated --json`, and selected `npm view` checks completed for `node-payment-helper`.
- No package files were changed, no packages were installed/upgraded, and `npm audit fix` was not run.
- Current audit summary remains 16 vulnerabilities: 4 high and 12 moderate.
- Runtime risk centers on Pump.fun SDK / Solana dependency chain; npm audit suggests unsafe incompatible downgrades, so do not auto-fix.
- Dev/test risk centers on Vitest/Vite/Vite-node/esbuild; a dev-only update is the preferred first cleanup candidate after explicit owner approval.
- Runtime Pump.fun/Solana updates require a separate compatibility review because changes can affect transaction building, invoice PDA derivation, signature binding, and `validateInvoicePayment`.
