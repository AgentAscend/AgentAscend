# Replay Index Migration Preflight Result

Related: [[Payment Access Control]], [[Pump.fun Tokenized Agent Payments]], [[Launch Readiness]], [[Ops Runbook]]

## Status
PASS / DDL NOT RECOMMENDED / DDL NOT NEEDED NOW.

No DDL was run, no migration was run, no index was created, no index was dropped, and no production DB mutation was performed.

## Preflight result — 2026-05-02
- Replay-index migration preflight: PASS.
- DDL execution: not recommended and not needed now.
- Admin aggregate audit endpoint was used safely with aggregate-only reporting.
- Existing Postgres index inspection completed safely with sanitized output only.

## Admin aggregate duplicate counts
All target duplicate counts were zero:

- duplicate payment `tx_signature` groups: 0
- duplicate payment_intent `tx_signature` groups: 0
- duplicate active grant groups: 0
- duplicate listing/user entitlement groups: 0

Safety flags confirmed by aggregate audit:

- `raw_metadata_returned: false`
- `raw_payloads_returned: false`
- `db_url_printed: false`
- `secrets_printed: false`
- `read_only_mode: true`

## Existing valid replay protections
Existing valid production indexes/constraints already satisfy the replay hardening target:

- `payments(tx_signature)`: valid unique index/constraint already present.
- `payment_intents(tx_signature)` for nonempty signatures: valid unique partial index already present.
- active `access_grants(user_id, feature_name, intent_reference)`: valid unique partial index already present.
- active `access_grants(user_id, feature_name, payment_id)`: valid unique partial index already present.
- `marketplace_entitlements(listing_id, user_id)`: valid unique constraint/index already present.

## Recommendation
STOP; do not run replay-index DDL now.

The candidate DDL would likely be redundant, especially for `payments(tx_signature)`, because equivalent or stronger valid uniqueness already exists.

## Future DDL rules
If schema drift or duplicate-risk evidence appears later:

1. Repeat read-only health/OpenAPI/security prechecks.
2. Repeat the admin aggregate duplicate preflight and stop if any duplicate count is nonzero.
3. Inspect existing indexes for semantic equivalence before running DDL. Do not rely only on `IF NOT EXISTS` by index name.
4. Do not drop existing production constraints/indexes unless separately inspected and approved.
5. Run `CREATE INDEX CONCURRENTLY` / `DROP INDEX CONCURRENTLY` only through a dedicated owner-approved migration command/path, never from FastAPI startup and never during deployment startup.
6. Remember that `CREATE INDEX CONCURRENTLY` and `DROP INDEX CONCURRENTLY` cannot run inside normal transactions.

## Candidate DDL retained for reference only
Do not run this unless future preflight proves it is needed and the owner explicitly approves.

```sql
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_payments_tx_signature_unique_nonempty
ON payments(tx_signature)
WHERE tx_signature IS NOT NULL AND tx_signature <> '';

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_payment_intents_tx_signature_unique_nonempty
ON payment_intents(tx_signature)
WHERE tx_signature IS NOT NULL AND tx_signature <> '';

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_access_grants_active_user_feature_intent_unique
ON access_grants(user_id, feature_name, intent_reference)
WHERE status = 'active'
  AND intent_reference IS NOT NULL
  AND intent_reference <> '';

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_access_grants_active_user_feature_payment_unique
ON access_grants(user_id, feature_name, payment_id)
WHERE status = 'active'
  AND payment_id IS NOT NULL;

CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_marketplace_entitlements_listing_user_unique
ON marketplace_entitlements(listing_id, user_id);
```

## Rollback reference
Only use for indexes that were actually created by a future approved migration. Do not drop existing production constraints/indexes unless separately inspected and approved.

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_marketplace_entitlements_listing_user_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_access_grants_active_user_feature_payment_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_access_grants_active_user_feature_intent_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_payment_intents_tx_signature_unique_nonempty;
DROP INDEX CONCURRENTLY IF EXISTS idx_payments_tx_signature_unique_nonempty;
```

## Next hardening phase
Proceed to Node dependency audit/cleanup as a separate docs-first, code-reviewed phase. Do not run `npm audit fix` automatically and do not change payment verification semantics during dependency cleanup.
