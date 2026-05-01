---
type: evidence
project: AgentAscend
date: 2026-04-30
status: archived
tags:
  - agentascend
  - launch-evidence
related:
  - "[[Launch Readiness]]"
  - "[[Pump.fun Tokenized Agent Payments]]"
  - "[[marketplace|Marketplace]]"
  - "[[Payment Access Control]]"
  - "[[AgentAscend]]"
---

Related: [[Launch Readiness]], [[Pump.fun Tokenized Agent Payments]], [[marketplace|Marketplace]], [[Payment Access Control]], [[AgentAscend]]

# Pump.fun Live Payment Evidence Archive - 2026-04-30

## Status
READY FOR SOFT LAUNCH / HARDENING ITEMS REMAIN

This archive reconciles the existing AgentAscend launch-evidence notes, public blockchain read-only evidence, a sanitized production aggregate DB audit, a narrow admin-only read-only lookup by the known public purchase transaction signature, and owner-provided private-dashboard/UI confirmation. It does not run a new payment, does not call backend verify, does not create a payment intent, does not ask for wallet signing, and does not mutate production beyond read-only audit queries.

## Archive timestamp
- Created/updated: 2026-05-01T02:50:04Z
- Current production commit under audit: `9e4015595a7854646f1095ffca6700cdfbd9d890`
- Commit message: `Harden payment evidence entitlement matching`

## Public constants
- Agent token mint: `9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump`
- Currency: SOL / Wrapped SOL
- Currency mint: `So11111111111111111111111111111111111111112`
- Expected canary amount: `0.1 SOL` / `100000000` lamports
- Pump.fun Agent Deposit/payment address: `G3yF27myX5WdtAihoKEWtuSPxMBQYqxCMSsJaSEcBx2S`
- Creator/payment authority wallet: `DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D`
- Buyback/burn handling: Pump.fun-managed, not AgentAscend code.

## Existing evidence inspected
- `raw/launch-evidence/2026-04-29-pumpfun-live-payment-canary.md`
  - P8A readiness PASS.
  - P8B owner-side payment action was originally pending in that note.
  - No reference/tx signature/UI revenue observation was included there.
- `raw/launch-evidence/2026-04-29-pumpfun-marketplace-buy-click-failure.md`
  - Earlier failed marketplace click before successful owner-reported canary.
  - Useful as historical failure evidence, not final success evidence.
- `docs/payment-runbook.md`
  - Records owner-reported successful canary but asks to archive public/sanitized evidence before final launch claims.
- `wiki/current-project-state.md`
  - Records owner-reported live canary: marketplace purchase, buyer ownership/unlock, creator accounting, and claim payout.
- `MEMORY.md`
  - Records owner-reported canary and public constants.

## Public on-chain evidence found by read-only lookup
The following signatures were found by read-only public chain lookup for the known public Pump.fun Agent Deposit/payment address and creator/payment authority wallet. No backend verify call was made.

### Purchase/payment transaction
- Public tx signature: `2NQw8iUkTtY33CE48pz5z2bmY9LwacJEMMFo39csPTfUrXxHEBjucKQSmX4Q83wSHvG1Rfg7b7x7cQWR5FGSauKA`
- Observed time: `2026-04-30T03:08:37Z`
- Status: success / no transaction error observed.
- Relevant program markers observed in summarized transaction metadata:
  - `AgenTMiC2hvxGebTsgmsD4HHBa8WEcqGFf87iwRRxLo7`
  - SPL token / associated token / system / compute budget programs
- Token balance summary for Pump.fun Agent Deposit owner:
  - owner: `G3yF27...Bx2S`
  - mint: `So11111111111111111111111111111111111111112`
  - raw token delta: `100000000`
  - UI delta: `0.1`
- Interpretation: public on-chain evidence is consistent with a 0.1 wSOL/SOL payment into the Pump.fun tokenized-agent deposit-owned token path.

### Claim/settlement transaction
- Public tx signature: `3NksQfxGxpknjBcoBXJmW5dqdjK4A1Dm1zasfZw7wFmwQ1yPHNeXmxfdqmADns6FgcXyZZ6TxJfHBnzbCXrQ51Ut`
- Observed time: `2026-04-30T03:17:06Z`
- Status: success / no transaction error observed.
- Creator/payment authority wallet lamport delta summary:
  - wallet: `DTC729...4K6D`
  - lamport delta: `47995000`
  - SOL delta: `0.047995`
- Relevant program marker observed in summarized transaction metadata:
  - `AgenTMiC2hvxGebTsgmsD4HHBa8WEcqGFf87iwRRxLo7`
- Interpretation: public on-chain evidence is consistent with a later creator claim/settlement payout to the configured creator/payment authority wallet.

## Owner-reported evidence
Owner-reported successful loop:
- Marketplace purchase completed.
- Buyer ownership/unlock worked.
- Creator dashboard accounting updated.
- Creator claim payout was received.

Classification: owner-provided private-dashboard/UI confirmation plus public/admin evidence where separately noted. This archive does not contain screenshots or raw private dashboard exports.

## Owner-Provided UI and Pump.fun Accounting Confirmation
- Update timestamp: 2026-05-01T02:50:04Z.
- Classification: owner-provided private-dashboard/UI confirmation. Hermes did not directly view private dashboard state and did not archive screenshots.
- AgentAscend frontend ownership/unlock confirmation:
  - The agent shows as owned after payment.
  - The paid marketplace/install flow completed successfully.
  - Ownership/unlock state is visible in the AgentAscend frontend.
- Pump.fun creator/accounting confirmation:
  - Pump.fun shows revenue earned.
  - Pump.fun shows revenue claimed.
  - Pump.fun shows buybacks pending.
  - Pump.fun shows buybacks complete.
  - The owner confirmed the displayed amounts are correct and in order.
- Safety notes:
  - No private wallet data, private keys, seed phrases, auth tokens, cookies, DB URLs, RPC URLs, QuickNode URLs, `txBase64`, signed transactions, raw request bodies, raw response bodies, or raw private-dashboard exports were provided or archived.
  - This section records owner confirmation only; it does not claim Hermes independently viewed or verified private Pump.fun dashboard state.

## Admin payment evidence lookup update
- Update timestamp: 2026-05-01T02:50:04Z.
- Endpoint used: `GET /admin/audits/payment-evidence/{tx_signature}`.
- Implementation/deployment commit: `9e4015595a7854646f1095ffca6700cdfbd9d890`.
- Lookup input: known public purchase/payment tx signature already archived in this file.
- Safe lookup result summary:
  - `payment_found`: true.
  - `payment_id_present`: true.
  - `payment_status`: `completed`.
  - `payment_intent_found`: true.
  - `payment_reference_present`: true.
  - `payment_reference`: `pumpfun:agentascendai:f849ba8ff48243a98a58635bf005a4d8`.
  - `payment_intent_status`: `completed`.
  - `verification_status`: `verified`.
  - `access_grant_present`: true.
  - `duplicate_payment_tx_signature_group_count`: 0.
  - `duplicate_payment_intent_tx_signature_group_count`: 0.
  - Safety flags: raw metadata returned false, raw payloads returned false, DB URL printed false, secrets printed false, read-only mode true.
- Nuance preserved:
  - Exact payment/payment_intent/access_grant evidence for the public purchase tx is now present.
  - Exact marketplace entitlement linkage for this specific tx was not proven by the lookup response: `marketplace_entitlement_present` false and `listing_scoped` false.
  - Separate aggregate evidence still shows 3 marketplace entitlements and 0 duplicate listing/user entitlement groups.
- Safety notes:
  - The lookup was admin-authenticated and read-only.
  - The archive records only sanitized fields. It does not include raw DB rows, user IDs, raw metadata, raw payloads, auth tokens, cookies, DB URLs, RPC URLs, private keys, seed phrases, `txBase64`, signed transactions, raw request bodies, or raw response bodies.

## Backend/API evidence already verified in adjacent audit
- Backend health: `GET https://api.agentascend.ai/health` -> HTTP 200.
- OpenAPI: `GET https://api.agentascend.ai/openapi.json` -> HTTP 200 valid JSON.
- Pump.fun routes live:
  - `POST /payments/pumpfun/create`
  - `POST /payments/pumpfun/verify`
- Unauthenticated schema-valid Pump.fun create -> HTTP 401.
- Current backend supports `listing_id` in Pump.fun create and inserts `marketplace_entitlements` after verified payment, based on source inspection of `backend/app/routes/pumpfun_payments.py` at current commit.

## Evidence checklist
- Public purchase tx signature: PRESENT.
- Public claim/settlement tx signature: PRESENT.
- Payment reference: PRESENT from admin-only read-only payment evidence lookup for the public purchase tx.
- Amount `0.1 SOL / 100000000`: PRESENT in constants and public token delta.
- Token mint: PRESENT.
- Currency mint: PRESENT.
- Pump.fun Agent Deposit/payment address: PRESENT.
- Verify response safe summary: PARTIAL via admin DB lookup; payment status `completed`, payment_intent status `completed`, payment_id present, and verification_status `verified`; original browser verify response body remains unavailable.
- Payment/access DB safe summary: PRESENT as sanitized production aggregate counts and exact public tx lookup from admin-only audit endpoints.
- Marketplace entitlement safe summary: PRESENT as sanitized production aggregate count; exact entitlement linkage for this tx was not proven by the tx lookup response.
- Frontend unlock/ownership evidence: OWNER-PROVIDED private-dashboard/UI confirmation; screenshots/raw dashboard exports not archived.
- Pump.fun UI/revenue/accounting observation: OWNER-PROVIDED private-dashboard/UI confirmation for revenue earned, revenue claimed, buybacks pending, buybacks complete, and correct amounts/order; screenshots/raw dashboard exports not archived.
- Creator claim/payout observation: PUBLIC CLAIM TX PRESENT plus owner-provided Pump.fun accounting confirmation; screenshots/raw dashboard exports not archived.

## Remaining optional evidence checklist for stronger post-launch proof
The archive is sufficient for soft-launch evidence, with hardening items remaining. Optional future artifacts should still be safe public/sanitized artifacts only:
1. Original browser/backend verify response summary, if recoverable from owner-side notes, showing:
   - `status`: `payment_verified`
   - reference match: yes
   - `payment_id`: present
2. Sanitized screenshots of AgentAscend ownership/unlock, if the owner wants visual rather than written owner confirmation.
3. Sanitized Pump.fun UI/revenue/accounting screenshots, if the owner wants visual rather than written owner confirmation.

Do not provide or paste private keys, seed phrases, auth tokens, cookies, DB URLs, RPC URLs, QuickNode URLs, `txBase64`, signed transaction payloads, wallet private data, raw request bodies, raw response bodies, or raw private-dashboard exports.

## Aggregate audit helper update
- Update timestamp: 2026-05-01T00:56:33Z
- Helper commit: `f7c77e08db979feb36d828a1c703edc106e023a7`
- Helper deployment status: AgentAscend web deployment `7e96d07e-89aa-4d50-adf1-bfd5d4717ac5` and AgentAscend-Scheduler deployment `e1cfa31d-af52-4729-bb26-5932a70410c0` both reached SUCCESS at the helper commit; Postgres latest deployment is also SUCCESS.
- Helper scope: aggregate-only read-only script `scripts/prod_readonly_audit.py` with local tests in `tests/test_prod_readonly_audit.py`.
- Local output format check: PASSED against local SQLite; output includes only aggregate sections and safety booleans.
- Production aggregate audit attempt: BLOCKED.
- Railway CLI unblock findings:
  - `railway run --service AgentAscend --environment production` is a local command with production variables injected, not an in-Railway-network execution context.
  - The production database variable is present and points to a Railway private internal host class, but that private host does not resolve from the local Railway-run context.
  - The repo `.venv` can import the Postgres driver locally, so the strongest observed blocker is Railway private networking/runtime context, not helper source absence or missing local driver.
  - Railway SSH was attempted for the AgentAscend service but returned unauthorized, so the helper could not be run inside the deployed service runtime from Hermes.
  - No Railway CLI command that truly runs a one-off command inside the active service runtime was available other than SSH.
- Production audit blocker before endpoint fallback: sanitized `OperationalError` at connect/query stage caused most likely by running outside Railway private networking; no DB URL, DB host, DB rows, raw payloads, or secrets were printed.
- Production DB/access/marketplace summary at this helper-only stage: MISSING. This historical blocker was later superseded by the admin-only endpoint audit below.

## Production admin aggregate audit endpoint update
- Update timestamp: 2026-05-01T01:41:25Z
- Endpoint commit: `3595864f71ad83051bc3d2b565c575afb895d70d`
- Endpoint deployment status: AgentAscend web deployment `1564c07c-62a8-4b19-b5e9-08cfe9424b3e` reached SUCCESS after configuring the runtime admin token; AgentAscend-Scheduler remained at deployment `ce90fc7f-32c8-4219-88c5-cc4dee7d2403` SUCCESS.
- Endpoint: `GET /admin/audits/launch-readiness/aggregate`
- Auth behavior:
  - unauthenticated request: HTTP 403
  - wrong runtime-admin token: HTTP 403
  - correct runtime-admin token: HTTP 200
- Safety flags from aggregate response:
  - `raw_metadata_returned`: false
  - `raw_payloads_returned`: false
  - `db_url_printed`: false
  - `secrets_printed`: false
  - `read_only_mode`: true
- Sensitive-marker scan of aggregate response: no DB URL, RPC URL, QuickNode URL, auth token, cookie, private key, seed phrase, raw request/response body, `txBase64`, signed transaction, `metadata_json`, `payload_json`, `output_summary`, or `error_message` marker found.

### Sanitized production aggregate summary
Scheduler:
- Enabled jobs by type: backend_health_check 1, integration_drift_check 1, todo_fixme_scan 1, wiki_consistency_check 1.
- Held jobs disabled by type: access_grant_integrity_check 1, failed_payment_replay_review 1, git_status_summary 1, payment_route_audit 1, roadmap_review 1, task_queue_worker 1, telegram_status_summary 1.
- Recent job runs by type/status: backend_health_check failed 1, backend_health_check success 288, git_status_summary failed 1, integration_drift_check success 6, task_queue_worker success 14, todo_fixme_scan success 7, wiki_consistency_check success 7.
- Scheduled job run rows: 310.
- Scheduled job run rows with non-null user_id: 0.
- Scheduled job run rows with non-null agent_id: 0.
- Scheduler artifacts: 0.
- Scheduler nonempty content_text count: 0.
- Orphan execution_events: 0.
- Orphan execution_artifacts: 0.

Execution Ledger:
- Executions by source type: scheduled_job_run 310, task 6.
- Executions by status: completed 314, failed 2.
- Orphan execution_events: 0.
- Orphan execution_artifacts: 0.
- Execution artifacts with nonempty content_text: 0.

Payments:
- Payment intents by status: completed 3, pending 21.
- Payments by status: completed 3.
- Duplicate payment tx_signature groups: 0.
- Duplicate payment_intent tx_signature groups: 0.
- Completed payments missing intent link: 0.
- Expired pending payment_intents: 21.

Access:
- Access grants by status: active 3.
- Active access_grants: 3.
- Active grants without payment link: 0.
- Active grants without intent reference: 0.
- Duplicate active grant groups: 0.

Marketplace:
- Marketplace entitlements: 3.
- Duplicate listing/user entitlement groups: 0.
- Entitlements without payment reference: not computable from this aggregate response.
- Creator earnings events: 0.
- Payout requests by status: none.

DB aggregate audit classification: PASS for safe aggregate production DB/access/marketplace proof. Overall launch evidence is now sufficient for a soft-launch decision because public purchase/claim signals, admin-only payment/access lookup, aggregate DB checks, and owner-provided UI/accounting confirmation are all archived. Hardening items still remain: original browser verify response body is unavailable, exact marketplace entitlement linkage for the specific tx was not proven by the tx lookup response, replay-index migration is not run, exact tx_signature binding hardening remains future work, and held scheduler jobs remain disabled pending separate audits.

## Launch-readiness conclusion for evidence
READY FOR SOFT LAUNCH / HARDENING ITEMS REMAIN.

The public on-chain purchase and claim/settlement signatures are archived and consistent with the owner-reported successful canary. The admin-only aggregate endpoint produced safe production DB aggregate evidence showing 3 completed payment intents, 3 completed payments, 3 active access grants, and 3 marketplace entitlements, with no duplicate payment signatures or duplicate active grants detected. The admin-only payment evidence lookup recovered the exact payment reference and confirmed completed payment/payment_intent state, payment_id presence, access_grant presence, and zero duplicate tx-signature groups for the known public purchase tx. The owner also provided private-dashboard/UI confirmation that the AgentAscend frontend ownership/unlock state is visible after payment and that Pump.fun revenue earned, revenue claimed, buybacks pending, buybacks complete, and displayed amounts are correct and in order.

This is not a claim that every hardening item is complete. Remaining hardening/follow-up items are: original browser verify response body is not available, exact marketplace entitlement linkage for this specific tx was not proven by the tx lookup response, replay-index migration remains pending and owner-approved only, exact tx_signature binding remains future hardening, and held scheduler jobs remain disabled until separately audited and approved.
