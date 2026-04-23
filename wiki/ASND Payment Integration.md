## Summary
ASND payment integration verifies confirmed SPL-token transfers on Solana and grants tool access only when the backend confirms receiver token-account delta meets configured minimums.

## Components
- ASND mint address: `9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump`
- Receiver wallet: `DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D`
- Receiver ASND token account: `2QNQhJRTcERXwwUs8jVqTGt5wJXYNHPfTw1wGEhuHW4g`
- Backend verifier in `backend/app/routes/payments.py`
- SPL provider module: `backend/app/providers/spl_token_rpc.py`

## Relationships
- Extends [[Monetization Model]]
- Uses [[Payment System]]
- Uses [[Solana Integration]]
- Supports [[Tokenized Agents]]

## Notes
- Required env configuration includes `SOLANA_RPC_URL`, `SOLANA_RECEIVER_WALLET`, and `ASND_MINT_ADDRESS`.
- ASND threshold is controlled by `ASND_PRICE_TOKENS` (default `100`).
- Reused transaction signatures are rejected (`Transaction signature already used`).
- The payment gate is backend-enforced; tool routes do not bypass payment verification.
