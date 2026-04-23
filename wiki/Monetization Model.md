## Summary
AgentAscend monetizes tool execution through backend-enforced, per-request payments in SOL or ASND before access is granted.

## Components
- Backend payment gate (`/payments/create`, `/payments/verify`) is the only source of truth.
- SOL pricing is env-driven through `SOL_PRICE_LAMPORTS` (default `100000000` = 0.1 SOL).
- ASND pricing is env-driven through `ASND_PRICE_TOKENS` (default `100`).
- Replay protection uses unique `tx_signature` in the payments table.
- Access grants are issued only after successful payment insert.

## Relationships
- Uses [[Payment System]]
- Uses [[ASND Payment Integration]]
- Supports [[Tool System]]
- Supports [[Knowledge System]]

## Notes
- Initial ASND policy: minimum accepted payment is `ASND_PRICE_TOKENS` (default 100) and must be validated on-chain against receiver token-account balance delta.
- Runtime config errors (invalid env values) fail closed with server errors.
- Revenue can be directed to growth, liquidity, or token utility mechanisms based on future treasury policy.
