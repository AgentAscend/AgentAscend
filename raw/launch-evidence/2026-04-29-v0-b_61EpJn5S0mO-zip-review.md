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

# v0 ZIP Review — b_61EpJn5S0mO.zip

## Status
PARTIAL / DO NOT RETRY LIVE PAYMENT YET

## ZIP
- Path reviewed: `/home/agentascend/Downloads/b_61EpJn5S0mO.zip`
- SHA256: `cefc5903208ce84cb7e4c93b208cf00dc08bb593761d57d211df156d1594399d`
- Fresh extraction: `/tmp/agentascend-v0-audit-20260429192953`

## Mechanical gates
- Dependency install: PASS using `npx --yes pnpm@10.24.0 install --frozen-lockfile`
- TypeScript: PASS
- Lint: PASS with warnings only
- Build: PASS
- source-truth-check: PASS

## Backend no-payment probes
- `/health`: HTTP 200
- `/openapi.json`: HTTP 200 valid JSON
- unauthenticated schema-valid `/payments/pumpfun/create`: HTTP 401
- `/payments/pumpfun/verify`: not called

## Pump.fun marketplace flow source audit
PASS with caveat.

`app/app/marketplace/page.tsx` now opens `PumpfunPaymentModal` directly for paid marketplace agents. It does not call the random-number gated tool before payment in the marketplace install path.

Important source lines reviewed:
- `handleInstall` detects paid agents via `pricing_model !== 'free' && price_amount > 0`.
- Paid agents call `setPendingAgentId(agent.id)` and `setIsPaymentModalOpen(true)`.
- `PumpfunPaymentModal` is rendered with `actionLabel="Pay to Install"`.
- Free agents still install immediately.

## Pump.fun hook audit
PARTIAL.

The hook uses:
- `/payments/pumpfun/create`
- wallet adapter signing
- browser `sendRawTransaction`
- `/payments/pumpfun/verify`
- success only when `status === 'payment_verified'` and reference matches

Caveat:
The P8 canary requirement also asked to require `payment_id` present. Current source type includes `payment_id`, but runtime success check does not explicitly assert it is present before setting `payment_verified`.

## Legacy payment flow audit
PASS.

Built bundle scan:
- `PaymentRequiredModal`: absent from build bundle
- `/payments/verify`: absent from build bundle
- `verifyResponse.success`: absent from build bundle

Legacy component file still exists but is not imported/active.

## Random-number button exposure
FAIL / PRODUCT BLOCKER.

`app/app/overview/page.tsx` still renders a visible `Random Number Tool` card with a `Run Tool` button. Built bundle also contains `Random Number Tool` and `/tools/random-number` markers.

This may be acceptable as a demo, but user stated they do not think a live random number generator button should be there. For launch polish, hide it behind an explicit dev/demo flag or remove it from production navigation/pages.

## Integrations payload audit
PASS.

`PATCH /users/me/integrations` now uses backend-compatible shape:
- `provider`
- `status`
- optional `config.wallet_address`

Live OpenAPI confirms `IntegrationPatchInput` requires `provider` and `status`, optional `config`.

## CSP/RPC source audit
PASS with warning.

CSP allows backend API and SolanaTracker HTTPS/WSS. No private QuickNode URL found. Source includes a broad QuikNode provider domain in CSP, not a secret URL/key.

## Recommendation
Do not retry live canary until the Random Number Tool production visibility is fixed and the verify success check explicitly requires `payment_id`.

## Secrets/private data
No auth tokens, cookies, DB URLs, RPC URLs, txBase64 values, signed transactions, private keys, seed phrases, or raw private wallet data were recorded.
