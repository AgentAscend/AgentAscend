# AgentAscend payment-critical env var readiness (2026-04-29)

## Required production backend env vars (fail-closed)

These are required in production (`AGENTASCEND_ENV`/`APP_ENV`/`ENVIRONMENT`/`RAILWAY_ENVIRONMENT` = `prod|production`):

1. `SOLANA_RECEIVER_WALLET`
2. `AGENT_TOKEN_MINT_ADDRESS`
3. `CURRENCY_MINT`
4. `PRICE_AMOUNT_SMALLEST_UNIT`
5. `SOL_PRICE_LAMPORTS`

## Expected behavior when missing/invalid

- On app startup in production:
  - `validate_payment_startup_env()` runs before DB init.
  - Missing/blank any required var => startup error (fail closed).
  - `PRICE_AMOUNT_SMALLEST_UNIT` and `SOL_PRICE_LAMPORTS` must be positive integers.
- On payment route usage:
  - Missing/invalid payment-critical config returns structured payment config error instead of silent fallback behavior.

## Platform placement

- Railway (backend): set all 5 vars above.
- Vercel (frontend): no secret payment verification fallback config should be used; frontend should rely on backend route responses and backend-configured pricing/messages.

## Notes

- Placeholder/default payment mint values are not allowed in production-critical flow.
- Pump.fun verification path remains backend source of truth for grant decisions.
