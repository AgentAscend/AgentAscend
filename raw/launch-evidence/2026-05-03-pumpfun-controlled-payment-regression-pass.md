---
type: launch evidence
project: AgentAscend
date: 2026-05-03
status: archived
tags:
  - agentascend
related:
  - "[[Launch Readiness]]"
  - "[[Pump.fun Tokenized Agent Payments]]"
  - "[[Payment Access Control]]"
  - "[[marketplace|Marketplace]]"
---

Related: [[Launch Readiness]], [[Pump.fun Tokenized Agent Payments]], [[Payment Access Control]], [[marketplace|Marketplace]]

# Pump.fun Controlled Payment Regression Canary — PASS

Timestamp UTC: 2026-05-03T04:24:38Z

## Result

PASS.

One owner-approved controlled Pump.fun payment regression canary completed successfully after the prior abandoned-intent recovery. The owner performed exactly one new frontend/wallet payment attempt. The payment was signed/sent by the owner, confirmed on public Solana evidence, verified by the normal deployed application flow, and recorded by backend/admin evidence as a completed listing-scoped payment with access grant and marketplace entitlement present.

No second payment attempt was performed by Hermes. No manual production DB mutation, access grant creation/revocation, marketplace entitlement mutation, migration, scheduler change, Pump.fun revenue claim, or buyback setting change was performed.

## Commit / Deploy Under Test

- Git branch: main
- HEAD: a8ad3ba4b6412538267798ed4951a427370c96ee
- origin/main: a8ad3ba4b6412538267798ed4951a427370c96ee
- ahead/behind origin/main...HEAD: 0 / 0
- AgentAscend Railway deployment: SUCCESS at a8ad3ba4b6412538267798ed4951a427370c96ee
- AgentAscend-Scheduler Railway deployment: SUCCESS at a8ad3ba4b6412538267798ed4951a427370c96ee

## Prior Recovery State

The previous attempt was classified as PARTIAL / ABANDONED INTENT:

- wallet popup opened
- owner did not sign/send
- no public tx signature existed from the prior attempt
- no backend verify succeeded
- aggregate evidence showed one new pending/expired payment_intent only
- completed payments, access grants, marketplace entitlements, and duplicate/replay counts stayed unchanged

This PASS archive does not reuse the abandoned intent.

## Fresh Precheck Summary

### Git / local scope

- branch: main
- HEAD equals origin/main: yes
- backend/test/node-helper/package dirty count: 0
- node-payment-helper/node_modules: absent
- node-payment-helper/dist: absent

### Production API

- GET /health: HTTP 200
- GET /openapi.json: HTTP 200, valid JSON
- Pump.fun create route present: yes
- Pump.fun verify route present: yes
- admin aggregate endpoint present: yes
- admin payment evidence endpoint present: yes

### Security headers

Present on checked API responses:

- strict-transport-security
- content-security-policy
- permissions-policy
- referrer-policy
- x-content-type-options
- x-frame-options

## Admin Aggregate Baseline Before New Attempt

Safety flags:

- raw_metadata_returned: false
- raw_payloads_returned: false
- db_url_printed: false
- secrets_printed: false
- read_only_mode: true

Aggregate counts before new attempt:

- payment_intents_count_by_status: completed=3, pending=22, unknown=2
- payments_count_by_status: completed=3
- access_grants_count_by_status: active=3
- active_access_grants_count: 3
- marketplace_entitlements_count: 3
- pending_payment_intents_expired_count: 22

Duplicate groups before new attempt:

- duplicate_payment_tx_signature_groups: 0
- duplicate_payment_intent_tx_signature_groups: 0
- duplicate_active_grant_groups: 0
- duplicate_listing_user_entitlement_groups: unavailable/null in aggregate output, not nonzero

## Owner Wallet / Frontend Evidence

Owner-provided sanitized observations:

- wallet popup opened: yes
- signed/sent: yes
- frontend payment status: payment confirmed / bought agent
- owned/unlocked visible: yes; bought agent shows owned
- Pump.fun Tokenized Agent revenue/accounting: owner reported correct revenue received and revenue split correct between buyback and creator

No screenshots, raw dashboard exports, cookies, tokens, raw request/response bodies, txBase64, signed transactions, private keys, seed phrases, DB URLs, or RPC URLs are archived here.

## Public Chain Evidence

Public transaction signature:

- 2ydGT5uPArgKx2WkiBZ9xNm17ap6WB4BVznJTNwThDThS8qia6zT5vq76CHgEDFwW4gj7FfMyTHJweobt9K5UhrR

Public Solscan summary:

- status: success / finalized
- timestamp UTC: 2026-05-03 04:19:27
- type: WSOL transfer workflow
- amount: 0.1 WSOL
- sender / fee payer: 6vREayFikfjLQWcswZ4Y8y9uqTZcaFFYrSJnDM6by2tv
- recipient owner: G3yF27myX5WdtAihoKEWtuSPxMBQYqxCMSsJaSEcBx2S
- total fee: 0.0000425 SOL
- version: legacy

## Backend/Admin Payment Evidence Lookup

Endpoint used safely:

- GET /admin/audits/payment-evidence/{tx_signature}

Safe lookup result summary:

- tx_signature_present: true
- payment_found: true
- payment_id_present: true
- payment_status: completed
- payment_intent_found: true
- payment_reference_present: true
- payment_reference: pumpfun:agentascendai:0967b710095e47bba1e12d4149639d9e
- payment_intent_status: completed
- verification_status: verified
- access_grant_present: true
- listing_scoped: true
- marketplace_entitlement_present: true
- duplicate_payment_tx_signature_group_count: 0
- duplicate_payment_intent_tx_signature_group_count: 0

Safety flags:

- raw_metadata_returned: false
- raw_payloads_returned: false
- db_url_printed: false
- secrets_printed: false
- read_only_mode: true

## Admin Aggregate Post-check

Aggregate counts after new attempt:

- payment_intents_count_by_status: completed=4, pending=22, unknown=2
- payments_count_by_status: completed=4
- access_grants_count_by_status: active=4
- active_access_grants_count: 4
- marketplace_entitlements_count: 4
- pending_payment_intents_expired_count: 22

Expected deltas vs precheck baseline:

- completed payment_intents: +1
- completed payments: +1
- active access_grants: +1
- marketplace_entitlements: +1
- pending expired intents: unchanged at 22

Duplicate groups after new attempt:

- duplicate_payment_tx_signature_groups: 0
- duplicate_payment_intent_tx_signature_groups: 0
- duplicate_active_grant_groups: 0
- duplicate_listing_user_entitlement_groups: unavailable/null in aggregate output, not nonzero

## Interpretation

The controlled regression succeeded:

1. One new real Pump.fun payment attempt was performed.
2. The owner signed/sent the wallet transaction.
3. The transaction succeeded publicly on Solana.
4. The deployed app/backend verified the payment through the intended normal flow.
5. Backend evidence shows completed payment, completed payment intent, payment_id present, verified status, access grant present, listing-scoped true, and marketplace entitlement present.
6. Aggregate counts increased exactly as expected for one successful listing-scoped canary.
7. Duplicate/replay aggregate counts remained clean.

Hermes did not issue an extra backend verify call after observing that the normal app flow had already verified successfully.

## Sensitive-data Exclusion Checklist

This archive intentionally excludes:

- private keys
- seed phrases
- auth tokens
- cookies
- DB URLs
- RPC URLs
- txBase64
- signed transactions
- raw request bodies
- raw response bodies
- raw DB rows
- raw metadata_json
- raw payload_json
- wallet private data

## Remaining Caveats

- The owner-provided Pump.fun revenue/accounting and owned/unlocked frontend observations are archived as owner-provided sanitized observations, not as screenshots or raw dashboard exports.
- duplicate_listing_user_entitlement_groups was unavailable/null in the aggregate output, so it is recorded as not nonzero rather than as a direct zero value.
- No replay/wrong-signature/expired-intent destructive or extra-payment probes were run in this phase.
