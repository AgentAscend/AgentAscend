# AgentAscend Payment Runbook

## Purpose
Keep AgentAscend payment verification and access control safe while the project uses the Pump.fun/tokenized-agent flow.

## Current model
- Backend is the source of truth for payment status and access.
- Frontend may display progress but must not unlock access from client-only state.
- Pump.fun payment flow uses SDK invoice semantics, not arbitrary SOL transfer scanning.
- Access is granted only after backend verification succeeds for the exact stored invoice/payment intent.

## Known constants
- Agent token mint: `9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump`.
- Currency mint: `So11111111111111111111111111111111111111112`.
- Price: `0.1 SOL` = `100000000` lamports/smallest unit.
- Pump.fun Agent Deposit/payment address: `G3yF27myX5WdtAihoKEWtuSPxMBQYqxCMSsJaSEcBx2S`.
- Creator/payment authority wallet: `DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D`.

## Required SDK-aligned flow
1. Authenticated user requests payment creation.
2. Backend creates immutable invoice/payment-intent parameters.
3. Backend or helper builds an unsigned transaction using `buildAcceptPaymentInstructions`.
4. Client wallet signs and sends the transaction.
5. Client submits only the public transaction signature and reference to backend verify endpoint.
6. Backend verifies with `validateInvoicePayment` using exact stored invoice params.
7. Backend records completed payment and access grant atomically.
8. Frontend unlocks only after backend returns `status === "payment_verified"` and reference matches.

## Live endpoints
- `POST /payments/pumpfun/create`
- `POST /payments/pumpfun/verify`

Read-only verification:
```bash
curl -fsS https://api.agentascend.ai/health
python3 - <<'PY'
import json, urllib.request
spec=json.load(urllib.request.urlopen('https://api.agentascend.ai/openapi.json'))
for p in ['/payments/pumpfun/create','/payments/pumpfun/verify']:
    print(p, p in spec.get('paths',{}), sorted(spec.get('paths',{}).get(p,{}).keys()))
PY
```

No-auth smoke expectation:
- Schema-valid unauthenticated create/verify probes should return 401.
- Do not include bearer tokens in an audit probe unless explicitly doing an authenticated owner-approved canary.
- Do not create payment intents during overnight/documentation audits.

## Frontend verification checklist
- Active paid pages use `PumpfunPaymentModal`.
- Active paid pages call `/payments/pumpfun/create` and `/payments/pumpfun/verify`.
- Verify response check uses `status === "payment_verified"` and exact reference match.
- Active paid pages do not use legacy `PaymentRequiredModal` for Pump.fun paid flows.
- No `verifyResponse.success` or old `/payments/verify` unlock path in active paid route bundles.
- No localStorage-based paid/access source of truth.
- Production CSP includes the approved public browser RPC/WSS origins; do not paste private RPC URLs into this runbook.

## What must never happen
- Do not ask users to paste private keys or seed phrases.
- Do not sign user transactions server-side.
- Do not print `txBase64`, signed transactions, auth tokens, DB URLs, private RPC URLs, cookies, or raw sensitive request/response bodies.
- Do not grant access from frontend confirmation alone.
- Do not manually create access grants for payment canaries.
- Do not implement AgentAscend buyback/burn bots; Pump.fun handles tokenized-agent buyback/burn mechanics.
- Do not repeatedly click payment or claim if an error occurs; first inspect transaction status and network response.

## Current live canary status
Owner reported a successful live canary: marketplace purchase completed, ownership/unlock appeared, creator earnings and buyback accounting updated, and claimable funds were received in the creator wallet. Archive public tx evidence and sanitized UI/network evidence before using this as final launch documentation.

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

## Payment↔grant linkage hardening status — 2026-05-13
Status: deployed PASS.

Commit: `7cc1c6a986e1e2a1896b5e8e5b62b36917bccc70` (`backend: harden payment grant linkage`).

What changed for future successful legacy `/payments/verify`:
- Completed `payments` rows now carry `intent_reference`, `verification_status = "verified"`, `updated_at`, and `verified_at`.
- Matching `payment_intents` rows are marked completed/verified with `tx_signature`, `completed_at`, and `updated_at` while preserving existing `consumed_at`.
- Existing legacy access-grant creation already carries `payment_id`, `intent_reference`, and `source = legacy_verify`.

Deployment evidence:
- Railway AgentAscend: SUCCESS.
- Railway AgentAscend-Scheduler: SUCCESS.
- Live `/health`: HTTP 200.
- Live `/openapi.json`: HTTP 200 valid JSON with Pump.fun create/verify and admin evidence/aggregate routes present.
- `/jobs/run-due` remains present from base API state and was not called.

Boundaries:
- Pump.fun payment route/helper behavior was not changed.
- No production backfill was performed.
- Historical null-heavy linkage rows, if any, remain audit-only unless future owner-approved cleanup occurs.

## Replay-index hardening status — 2026-05-02
Status: PASS preflight / DDL not needed now.

Production replay-index preflight confirmed:
- No DDL was run.
- No production DB mutation occurred.
- Duplicate payment `tx_signature` groups: 0.
- Duplicate payment_intent `tx_signature` groups: 0.
- Duplicate active grant groups: 0.
- Duplicate listing/user entitlement groups: 0.
- Existing valid indexes/constraints already protect replay-sensitive payment/access/marketplace records.

Operational rules:
- Do not run replay-index DDL now.
- Run future DDL only if schema drift or duplicate-risk evidence appears and the owner explicitly approves.
- Inspect semantic equivalence before using `IF NOT EXISTS` by name.
- Do not drop existing production constraints/indexes unless separately inspected and approved.
- `CREATE INDEX CONCURRENTLY` and `DROP INDEX CONCURRENTLY` cannot run inside normal transactions.
