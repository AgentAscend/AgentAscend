---
type: launch evidence
project: AgentAscend
date: 2026-05-03
status: superseded
tags:
  - agentascend
related:
  - "[[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]]"
  - "[[Launch Readiness]]"
  - "[[Pump.fun Tokenized Agent Payments]]"
---

Status: Superseded by [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]].
Related: [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]], [[Launch Readiness]], [[Pump.fun Tokenized Agent Payments]]

# Pump.fun Controlled Payment Regression Canary — Partial

Timestamp UTC: 2026-05-03T03:53:13Z

## Result

PARTIAL / BLOCKED before payment.

The approved preflight passed, but no owner wallet-action response was received before timeout. No payment intent was intentionally created by the agent, no wallet signing was requested beyond the safe owner-side prompt, and no verify/replay/payment mutation steps were run.

## Commit Under Test

- AgentAscend production commit: a8ad3ba4b6412538267798ed4951a427370c96ee
- Runtime helper update under test: @pump-fun/agent-payments-sdk 3.0.2 -> 3.0.3

## Read-only Preflight Summary

### Git / local scope

- branch: main
- HEAD equals origin/main: yes
- scoped backend/tests/node-helper/package state: clean
- node-payment-helper/node_modules: absent
- node-payment-helper/dist: absent

### Production API

- /health: HTTP 200, valid JSON
- /openapi.json: HTTP 200, valid JSON
- POST /payments/pumpfun/create route present: yes
- POST /payments/pumpfun/verify route present: yes
- /admin/audits/launch-readiness/aggregate present: yes
- /admin/audits/payment-evidence/{tx_signature} present: yes
- unauthenticated Pump.fun create probe: HTTP 401
- unauthenticated Pump.fun verify probe: HTTP 401

### Security headers

Present on checked API responses:

- strict-transport-security
- content-security-policy
- permissions-policy
- referrer-policy
- x-content-type-options
- x-frame-options

### Railway deployments

- AgentAscend: SUCCESS at a8ad3ba4b6412538267798ed4951a427370c96ee
- AgentAscend-Scheduler: SUCCESS at a8ad3ba4b6412538267798ed4951a427370c96ee

### Frontend static checks

- /app/marketplace: HTTP 200
- /app/overview: HTTP 200
- active frontend assets fetched: 19
- /payments/pumpfun/create marker present: yes
- /payments/pumpfun/verify marker present: yes
- payment_verified marker present: yes
- legacy /payments/verify marker present: no
- verifyResponse.success marker present: no
- PaymentRequiredModal marker present: no

Browser automation was blocked by local Chromium sandbox restrictions, so frontend evidence is HTTP/static asset based.

## Admin Aggregate Baseline

Safety flags:

- raw_metadata_returned: false
- raw_payloads_returned: false
- db_url_printed: false
- secrets_printed: false
- read_only_mode: true

Aggregate counts:

- payment_intents_count_by_status: completed=3, pending=21, unknown=2
- payments_count_by_status: completed=3
- access_grants_count_by_status: active=3
- active_access_grants_count: 3
- marketplace_entitlements_count: 3

Duplicate groups:

- duplicate_payment_tx_signature_groups: 0
- duplicate_payment_intent_tx_signature_groups: 0
- duplicate_active_grant_groups: 0
- duplicate_listing_user_entitlement_groups: 0

Additional aggregate integrity observations:

- pending_payment_intents_expired_count: 21
- completed_payments_missing_intent_link: 0
- active_grants_without_payment_link: 0
- active_grants_without_intent_reference: 0
- entitlements_without_payment_reference: unavailable/null in aggregate

## Owner Wallet-action Gate

Status: BLOCKED / NO RESPONSE BEFORE TIMEOUT

Requested owner-side safe metadata only:

- wallet popup opened yes/no
- signed/sent yes/no
- public payment reference if shown
- public tx signature only if sent
- amount/currency
- frontend final status text or sanitized screenshot statement
- payment_id present yes/no/unknown
- access unlocked yes/no/unknown
- marketplace entitlement/install visible yes/no/unknown

No owner metadata was received in this run.

## Tests Not Run

Because the owner wallet-action gate did not complete:

- valid real payment accepted: NOT RUN
- replay rejected/idempotent: NOT RUN
- wrong-signature production test: NOT RUN
- expired-intent production test: NOT RUN
- post-payment aggregate delta check: NOT RUN
- payment evidence endpoint lookup: NOT RUN

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

## Safe Resume Prompt

Resume with:

I am ready to resume the AgentAscend controlled Pump.fun payment regression canary from the 2026-05-03 preflight PASS / owner-action timeout state. Do not rerun duplicate payment attempts. First rerun read-only prechecks and admin aggregate duplicate counts. If still zero, guide me through exactly one owner-side wallet attempt and accept only public/sanitized metadata: public reference, public tx signature if sent, amount/currency, frontend status, payment_id present boolean, access unlocked boolean, and entitlement/install visible boolean. Do not request or print txBase64, signed transactions, auth tokens, cookies, raw request/response bodies, DB/RPC URLs, private keys, seed phrase, raw DB rows, raw metadata_json, raw payload_json, or wallet private data.
