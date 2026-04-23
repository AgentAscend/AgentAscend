# Skill: payment_guardrail

Purpose
- Ensure payment-gated backend behavior remains authoritative and non-bypassable.

Scope
- `backend/app/routes/payments.py`
- `backend/app/services/access_service.py`
- `backend/app/routes/tools.py`
- `backend/app/db/session.py`

Procedure
1) Fail-fast prechecks
- Confirm `tx_signature` uniqueness exists in payments schema.
- Confirm tools route checks backend grant state.

2) Validation checks
- Unsupported token must return 400.
- Invalid signature format must return 400 before RPC lookup.
- Missing payment env vars must return explicit 500.
- Duplicate `tx_signature` must return 400 `Transaction signature already used`.

3) Access sequencing
- Verify access grant is triggered only after successful payment insert/commit.
- Verify replay attempt does not create additional rows.

4) Runtime checks
- Unpaid user on `/tools/random-number` -> `payment_required`.
- Paid user -> `success` with result.

Rollback
- If guardrail regression appears, revert the latest payment-related commit and re-run verification matrix.
