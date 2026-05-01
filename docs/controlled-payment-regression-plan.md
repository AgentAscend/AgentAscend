# Controlled Pump.fun Payment Regression Plan

Related: [[Pump.fun Tokenized Agent Payments]], [[Payment Access Control]], [[Launch Readiness]], [[Marketplace]]

## Status
Planning only. No payment was run, no wallet signing was requested, no SOL was sent, no payment intent was created, no verify call was made, and no access grant was created or revoked.

## Future canary cases
1. Valid real Pump.fun payment accepted.
2. Replay rejected.
3. Wrong-signature rejected.
4. Expired intent rejected.
5. Wrong user/wallet rejected where applicable.
6. Duplicate tx rejected.

## Safety rules
- Owner manually signs/sends in their wallet only after explicit approval.
- One real payment maximum per canary.
- No private keys, seed phrases, auth tokens, cookies, DB URLs, RPC URLs, raw request/response bodies, `txBase64`, signed transactions, private wallet data, raw DB rows, raw metadata, or raw payloads in chat or docs.
- No manual access grant creation.
- No production DB mutation outside normal backend payment flow triggered by the owner-approved real canary.

## Evidence to archive
- Public tx signature.
- Payment reference or sanitized reference-present evidence.
- Sanitized create/verify result summary: status, `payment_id` present, `payment_verified`, reference match, listing-scoped yes/no.
- Sanitized frontend owner/unlock proof.
- Sanitized creator accounting/revenue proof if available.
- Admin aggregate duplicate counts and payment-evidence lookup summary only.

## Rollback/failure handling
If valid payment fails, do not manually grant access. Archive the sanitized failure summary, preserve public tx signature, run read-only admin evidence lookup if approved, and prepare a code/debug plan. If replay/wrong-signature is accepted, treat as P0 and stop further canaries.

## Exact future prompt
`I approve one controlled AgentAscend Pump.fun payment regression canary. Run health/OpenAPI/auth/security prechecks first. Create at most one owner-approved real payment intent through the normal authenticated frontend/API flow, have the owner manually sign/send exactly one payment in their wallet, then verify only that payment. Archive sanitized evidence only. Then test replay of the same tx, wrong-signature, expired intent, wrong user/wallet where applicable, and duplicate tx rejection without sending more SOL. Do not ask for private keys/seed phrases/tokens/cookies, do not print raw request/response bodies or signed transactions, do not manually create access grants, do not run migrations, and stop immediately on any unsafe acceptance.`
