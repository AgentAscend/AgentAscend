# Pump.fun Live Payment Evidence Archive - 2026-04-30

## Status
PARTIAL / OWNER-REPORTED COMPLETE, PUBLIC ON-CHAIN PURCHASE/CLAIM SIGNALS FOUND, PRODUCTION AGGREGATE DB AUDIT PASSED, VERIFY/UI EVIDENCE INCOMPLETE

This archive reconciles the existing AgentAscend launch-evidence notes, public blockchain read-only evidence, and a sanitized production aggregate DB audit. It does not run a new payment, does not call backend verify, does not create a payment intent, does not ask for wallet signing, and does not mutate production beyond read-only aggregate queries.

## Archive timestamp
- Created/updated: 2026-05-01T01:41:25Z
- Current production commit under audit: `3595864f71ad83051bc3d2b565c575afb895d70d`
- Commit message: `Add admin launch readiness audit endpoint`

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

Classification: owner-reported. This archive does not yet contain sanitized frontend screenshots, sanitized network metadata, or production DB aggregate proof for those UI/backend states.

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
- Payment reference: MISSING from archive.
- Amount `0.1 SOL / 100000000`: PRESENT in constants and public token delta.
- Token mint: PRESENT.
- Currency mint: PRESENT.
- Pump.fun Agent Deposit/payment address: PRESENT.
- Verify response safe summary: MISSING from archive.
- Payment/access DB safe summary: PRESENT as sanitized production aggregate counts from admin-only audit endpoint; exact payment reference still missing.
- Marketplace entitlement safe summary: PRESENT as sanitized production aggregate count; entitlement-to-reference detail remains limited by aggregate-only audit output.
- Frontend unlock/ownership evidence: OWNER-REPORTED; sanitized artifact missing.
- Pump.fun UI/revenue/accounting observation: OWNER-REPORTED; sanitized artifact missing.
- Creator claim/payout observation: PUBLIC CLAIM TX PRESENT and owner-reported UI/accounting; sanitized UI artifact missing.

## Owner evidence checklist for final launch proof
Provide only safe public/sanitized artifacts:
1. Payment reference from the successful canary purchase.
2. Safe backend verify response summary showing:
   - `status`: `payment_verified`
   - reference match: yes
   - `payment_id`: present
3. Sanitized frontend ownership/unlock artifact, such as a screenshot or written note showing buyer ownership/unlock after backend verification.
4. Sanitized Pump.fun UI/revenue/accounting artifact for the purchase.
5. Sanitized creator claim/payout evidence if the owner wants to prove the full creator loop beyond the public claim transaction.

Do not provide or paste private keys, seed phrases, auth tokens, cookies, DB URLs, RPC URLs, QuickNode URLs, `txBase64`, signed transaction payloads, wallet private data, raw request bodies, or raw response bodies.

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

DB aggregate audit classification: PASS for safe aggregate production DB/access/marketplace proof. Overall launch evidence remains PARTIAL because payment reference, safe verify response summary, sanitized frontend ownership/unlock evidence, and sanitized Pump.fun UI/revenue/accounting evidence are still missing from the archive.

## Launch-readiness conclusion for evidence
PARTIAL.

The public on-chain purchase and claim/settlement signatures are archived and consistent with the owner-reported successful canary. The admin-only aggregate endpoint produced safe production DB aggregate evidence showing 3 completed payment intents, 3 completed payments, 3 active access grants, and 3 marketplace entitlements, with no duplicate payment signatures or duplicate active grants detected. Final launch proof is still incomplete because the archive still lacks the exact payment reference, sanitized backend verify response summary, sanitized frontend ownership/unlock artifact, and sanitized Pump.fun UI/revenue/accounting artifact.
