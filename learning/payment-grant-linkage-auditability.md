# Payment↔Grant Linkage Auditability

## Pattern
A system can have strong payment verification, auth gates, exact transaction binding, and replay protection while still losing auditability if completed payment rows are not durably linked to active access-grant and marketplace-entitlement rows.

## Why linkage matters
Payment-created access must be explainable after the fact. For every paid unlock, operators should be able to trace the chain across:
- `payment_intents`
- completed payment rows
- `access_grants`
- `marketplace_entitlements`
- `intent_reference`
- `payment_id`
- `tx_signature`

Without those links, later audits cannot easily prove which payment created which grant, whether a grant was duplicated, or whether a marketplace entitlement corresponds to the intended paid listing.

## Observed auditability problem
Read-only local reports flagged payment/access rows where linkage appeared incomplete or null-heavy. Treat that as a launch-risk investigation until scope is proven. Local findings do not automatically prove production state, and they do not authorize mutation.

## What must be avoided
- Do not treat this as an emergency production mutation.
- Do not backfill historical rows before forward invariants are tested and an owner-approved repair plan exists.
- Do not replay payments or call Pump.fun verify to “repair” state.
- Do not create/revoke production `access_grants` or change `marketplace_entitlements` without explicit approval.
- Do not print raw private DB rows, raw payloads, secrets, private wallet data, signed transactions, DB URLs, RPC URLs, cookies, or auth tokens.

## Future implementation should prove
- New legacy payment verification creates grants with durable `payment_id` linkage.
- New Pump.fun verification creates listing/tool grants with durable `payment_id` and `intent_reference` linkage.
- Payment insert, intent consumption, grant creation, and entitlement creation are atomic where they belong to the same flow.
- Duplicate/retry paths stay deterministic and do not create duplicate active grants.
- Historical repair remains a separate proposal with dry-run evidence and explicit owner approval before mutation.

## Safe workflow
1. Read `MEMORY.md` and confirm the exact scope.
2. Keep planning commits separate from backend/payment code commits.
3. Write RED tests for forward invariants before editing payment code.
4. Fix legacy and Pump.fun routes separately; do not assume one payment path covers the other.
5. Run focused payment/security regression tests.
6. Keep production backfill/data repair proposal-only until owner approves mutation.

## Related files
- `docs/plans/2026-05-12-payment-grant-linkage-hardening-plan.md`
- `skills/payment-grant-linkage-hardening.md`
