---
type: evidence
project: AgentAscend
date: 2026-04-29
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

# Pump.fun Marketplace Buy Click Failure

## Status
FAIL / BLOCKED BEFORE PAYMENT INTENT

## User-observed behavior
Owner attempted to buy an agent from the live marketplace. Pressing the Buy button appeared to do nothing.

## Safe devtools evidence provided
Sanitized console/network signals:
- `SES Removing unpermitted intrinsics` warning.
- Phantom Standard Wallet duplicate-adapter warning.
- Deprecated `feature_collector.js` initialization warning.
- `POST https://api.agentascend.ai/tools/random-number?user_id=agentascendai` returned `401 Unauthorized` after the Buy click path.
- `PATCH https://api.agentascend.ai/users/me/integrations` returned `422 Unprocessable Content`, repeated.

No private keys, seed phrases, txBase64, signed transactions, cookies, auth tokens, DB URLs, RPC URLs, or raw response bodies were recorded.

## Live bundle follow-up findings
Read-only live bundle inspection after the report found:
- PumpfunPaymentModal is deployed in the marketplace route bundle.
- `/payments/pumpfun/create` and `/payments/pumpfun/verify` helpers are deployed.
- Marketplace route renders `PumpfunPaymentModal` with `actionLabel="Pay to Install"`.
- The shared API bundle also contains a `POST /tools/random-number?user_id=...` helper that does not pass a bearer token.
- The live devtools error proves the click path reached the random-number tool route instead of opening/completing the Pump.fun payment modal path.
- `/users/me/integrations` PATCH live OpenAPI requires request fields: `provider`, `status`, optional `config`; the frontend integration call returned 422, indicating payload shape drift or missing required fields.

## Revised diagnosis
User clarified that the random-number generator is an example paid/gated tool from the Pump.fun sample flow. Therefore, the presence of `/tools/random-number` is not automatically wrong by itself.

Primary canary blocker:
- The user-visible Buy click still did not open or complete the Pump.fun payment modal flow. No successful `/payments/pumpfun/create` intent creation was observed in the provided console evidence.
- If `/tools/random-number` is the selected agent's post-purchase example tool, it should still be blocked until payment/access is verified. A 401 before purchase can be expected, but the UI must route the user into the payment modal instead of appearing to do nothing.

Secondary issue:
- Wallet/integration persistence is sending a PATCH shape that the live backend rejects with 422. This can make wallet/connect state noisy or unstable and should be fixed, but it may be separate from the Buy button no-op.

## Safety result
No payment intent was confirmed created from this failed marketplace click.
No wallet signing occurred.
No SOL was sent.
No Pump.fun verify call was made.
No manual access grant was created.

## Required next action
Patch v0/frontend marketplace paid-action wiring before retrying any real payment:
- Buy/Install for paid marketplace agents must open PumpfunPaymentModal first.
- It must not call `/tools/random-number` before backend payment verification and confirmed access.
- The payment modal must create exactly one fresh `/payments/pumpfun/create` intent after the user intentionally starts payment.
- After `/payments/pumpfun/verify` returns `status === "payment_verified"` and matching `reference`, refresh backend entitlement/access state.
- Then, and only then, allow gated tool use.
- Fix `/users/me/integrations` PATCH payload to match live schema: `{ provider, status, config? }`.
