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

# Pump.fun Live Payment Canary Evidence

## Status
PARTIAL / PENDING OWNER WALLET ACTION

P8A readiness passed. P8B owner-side payment action was not completed in this session because no owner response with public payment metadata was received after the canary instructions were issued.

## Date/time
- Archive created: 2026-04-30T02:12:24Z
- Intended canary date label: 2026-04-29

## Environment
- Frontend: https://www.agentascend.ai
- Backend: https://api.agentascend.ai
- Git branch: main
- Backend/frontend-integrated commit: c724b7d7d1c7c1e0c0a778a208364722f3ae3f2c
- origin/main: c724b7d7d1c7c1e0c0a778a208364722f3ae3f2c
- Railway AgentAscend web deployment: 59d2a265-35fe-4363-8b18-0a5638acdfbb, status SUCCESS
- AgentAscend-Scheduler deployment: 781459be-a9f0-44cf-9b95-9280b50ebdfa, status SUCCESS

## Payment constants
- Amount: 0.1 SOL / 100000000 lamports
- Agent token mint: 9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump
- Currency mint: So11111111111111111111111111111111111111112
- Pump.fun Agent Deposit/payment address: G3yF27myX5WdtAihoKEWtuSPxMBQYqxCMSsJaSEcBx2S
- Creator/payment authority wallet: DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D

## P8A readiness result
PASS

Verified safe/read-only readiness:
- Backend /health returned HTTP 200.
- Backend /openapi.json returned HTTP 200 and valid JSON.
- POST /payments/pumpfun/create route present.
- POST /payments/pumpfun/verify route present.
- Schema-valid unauthenticated create probe returned HTTP 401.
- Pump.fun verify probe was skipped; no fake or real tx was submitted.
- API security headers present: Content-Security-Policy, Permissions-Policy, Referrer-Policy, X-Content-Type-Options, X-Frame-Options.
- API Strict-Transport-Security absent; launch-hardening warning only.
- Frontend routes returned HTTP 200: /, /app/overview, /app/marketplace, /app/executions.
- Frontend CSP present and allows backend API plus browser Solana RPC HTTPS/WSS origins.
- 26 live frontend assets found and fetched with 0 asset fetch errors.
- Live bundle includes PumpfunPaymentModal.
- Live bundle includes /payments/pumpfun/create.
- Live bundle includes /payments/pumpfun/verify.
- Live bundle includes payment_verified.
- Live bundle includes reference-match evidence around payment_verified.
- Live bundle does not include PaymentRequiredModal.
- Live bundle does not include legacy /payments/verify.
- Live bundle does not include verifyResponse.success.
- No private QuickNode marker found.
- localStorage keys found: agentascend_user_id only; no paid/access/unlock localStorage key found.

## P8B owner-side live payment action
PENDING

No payment reference was received.
No public tx_signature was received.
No owner wallet signing result was received.
No Pump.fun UI/revenue observation was received.

## P8C backend verification
NOT RUN

Reason: P8B was not completed and no public tx_signature/payment reference was provided.

## P8D DB/access verification
NOT RUN

Reason: P8C was not run. Also, production DB aggregate verification remains blocked by safe DB access limitations.

## P8E Pump.fun/revenue observation
NOT PROVIDED

## Sensitive data exclusion confirmation
This archive intentionally does not include:
- auth tokens
- cookies
- DB URLs
- RPC URLs
- QuickNode URLs
- txBase64
- signed transaction payloads
- private wallet data
- seed phrases
- raw request bodies
- raw response bodies

## Remaining risks
- P8 payment canary itself remains unproven until one owner-side wallet transaction is completed and verified.
- Scheduler DB aggregate verification remains blocked by safe DB access limitations and was explicitly accepted as unrelated to canary readiness.
- API HSTS remains absent and should be handled as launch-hardening.
- Replay unique indexes are intentionally not created by default and need separate migration planning.
- validateInvoicePayment exact tx_signature binding remains future hardening.

## Next required safe input
Owner must provide only safe public/sanitized metadata after exactly one canary attempt:
- reference
- public tx_signature if a transaction was sent
- amount/currency confirmation
- invoiceId present true/false
- txBase64 present true/false
- verify status shown by frontend
- payment_id present true/false
- access_unlocked true/false
- creator_accounting_observed true/false/unknown
- pumpfun_revenue_observed true/false/unknown
