# AgentAscend Replay-index Migration Preflight

Status: PREPARED ONLY. Do not run DDL without explicit owner approval.

## Current preflight summary
- Public `/health`: HTTP 200.
- Public `/openapi.json`: HTTP 200 and valid JSON.
- Pump.fun create/verify routes: present.
- Admin aggregate audit route: present and unauthenticated access fails closed.
- Security headers including HSTS: present.
- Admin aggregate safety flags from read-only endpoint: raw metadata not returned, raw payloads not returned, DB URL not printed, secrets not printed, read-only mode true.
- Duplicate aggregate counts from read-only endpoint: payment tx_signature groups 0; payment_intent tx_signature groups 0; active grant groups 0; listing/user entitlement groups 0.
- Existing index inspection: PARTIAL/BLOCKED in current tooling because safe DB index inspection could not be completed without a driver/in-service shell path. Treat index inspection as a required step in the owner-approved migration command/path before DDL.

## Owner approval prompt

I approve the AgentAscend Postgres replay-index migration DDL phase.

After approval, run a dedicated migration phase with the checks and DDL below. Do not run from FastAPI startup and do not run during deployment startup.

## Required pre-migration checks
1. `/health` returns HTTP 200.
2. `/openapi.json` returns valid JSON.
3. Admin aggregate endpoint is available.
4. Duplicate counts are all zero:
   - duplicate payment tx_signature groups: 0
   - duplicate payment_intent tx_signature groups: 0
   - duplicate active grant groups: 0
   - duplicate listing/user entitlements: 0
5. Existing index inspection is complete, or the owner explicitly accepts inspection as pending inside the migration command before any DDL.
6. No deploy is in progress.
7. Backup/rollback plan is known.

## Existing index guard
Before running DDL, inspect existing indexes on `payments`, `payment_intents`, `access_grants`, and `marketplace_entitlements`.

Report only table, index name, valid yes/no, unique yes/no, column/predicate summary, and recommended action.

Rules:
- Skip any equivalent existing unique/valid index.
- Avoid duplicate equivalent indexes.
- If an invalid candidate index exists, stop and report before trying anything.
- Leave non-unique helper indexes alone unless a separate owner-approved cleanup phase says otherwise.

## Candidate DDL
Run with `CONCURRENTLY`; do not wrap these statements in a normal transaction.

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

## Important CONCURRENTLY rules
- `CREATE INDEX CONCURRENTLY` cannot run inside a normal transaction.
- `DROP INDEX CONCURRENTLY` also cannot run inside a normal transaction.
- Do not run this from FastAPI startup.
- Do not run this during deployment startup.
- Run through a dedicated owner-approved migration command/path.

## Post-migration verification
1. Confirm index existence and validity.
2. Confirm admin aggregate duplicate counts are still zero.
3. Confirm `/health` still returns HTTP 200.
4. Confirm `/openapi.json` is valid.
5. Confirm Pump.fun routes are present.
6. Confirm schema-valid unauthenticated Pump.fun create still returns 401.
7. Confirm unauthenticated admin aggregate audit remains 403.
8. Confirm logs are clean of critical DB errors.

## Rollback/drop-index plan
Use only if owner-approved and needed; do not wrap in a normal transaction.

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_payments_tx_signature_unique_nonempty;
DROP INDEX CONCURRENTLY IF EXISTS idx_payment_intents_tx_signature_unique_nonempty;
DROP INDEX CONCURRENTLY IF EXISTS idx_access_grants_active_user_feature_intent_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_access_grants_active_user_feature_payment_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_marketplace_entitlements_listing_user_unique;
```

## Failure criteria
Stop and report if any of these happen:
- duplicate count is nonzero
- DDL fails
- invalid index is found
- health fails
- OpenAPI fails
- payment routes regress
- DB errors appear
- logs show critical errors
- migration command requires printing DB URL or secrets
