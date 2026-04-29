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
- Production CSP includes browser RPC origins:
  - `https://rpc.solanatracker.io`
  - `wss://rpc.solanatracker.io`

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
