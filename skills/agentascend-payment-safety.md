# AgentAscend Payment Safety

## When to use
Use for any payment, Pump.fun, access grant, marketplace entitlement, Solana, ASND, replay, or payment-history work.

## Hard boundaries
- Do not create payment intents, call Pump.fun verify, run payments, sign/send transactions, create/revoke grants, mutate marketplace entitlements, claim revenue, run buybacks, or change payment env/config without explicit owner approval.
- Never print secrets, private RPC URLs, DB URLs, tokens, cookies, private keys, seed phrases, signed transactions, txBase64, raw DB rows, raw metadata/payload, or raw request/response bodies.
- Public tx signatures and public wallet addresses are allowed only when already part of launch evidence.

## Current facts
- Pump.fun create/verify routes are live and auth-gated.
- Controlled regression PASS evidence exists at [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass]].
- Exact tx_signature binding is deployed.
- Replay-index DDL is not needed now after preflight PASS.
- Runtime dependency advisories remain monitored; do not run `npm audit fix` blindly.

## Verification before claims
Use live `/health`, `/openapi.json`, sanitized admin aggregate/evidence summaries if explicitly allowed, and archived raw evidence. Do not use raw bodies or secrets.
