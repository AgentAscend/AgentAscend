# Replay Index Migration Approval Package

Related: [[Payment Access Control]], [[Pump.fun Tokenized Agent Payments]], [[Launch Readiness]], [[Ops Runbook]]

## Status
PARTIAL / OWNER APPROVAL PACKAGE READY FOR FUTURE DDL PHASE.

This document is planning-only. No DDL was run, no migration was run, no index was created, and no production DB mutation was performed.

## Required prechecks
1. `GET https://api.agentascend.ai/health` returns 200.
2. `GET https://api.agentascend.ai/openapi.json` returns 200 and valid JSON.
3. OpenAPI contains `/payments/pumpfun/create`, `/payments/pumpfun/verify`, `/admin/audits/launch-readiness/aggregate`, and `/admin/audits/payment-evidence/{tx_signature}`.
4. Schema-valid unauthenticated Pump.fun create returns 401.
5. Unauthenticated aggregate audit returns 403.
6. HSTS and standard security headers are present.

## Duplicate aggregate preflight
Run `GET /admin/audits/launch-readiness/aggregate` with `X-Agent-Runtime-Token` from the private owner/runtime environment. Summarize only aggregate values.

Required safety flags:
- `raw_metadata_returned: false`
- `raw_payloads_returned: false`
- `db_url_printed: false`
- `secrets_printed: false`
- `read_only_mode: true`

Required duplicate counts before DDL:
- duplicate payment `tx_signature` groups: 0
- duplicate payment_intent `tx_signature` groups: 0
- duplicate active grant groups: 0
- duplicate listing/user entitlement groups: 0

If any duplicate count is nonzero, stop and prepare a cleanup plan instead of running DDL.

## Existing index inspection before DDL
Inspect Postgres indexes read-only and report only table, index name, valid yes/no, unique yes/no, column/predicate summary, and action. If direct inspection is blocked, the owner-approved migration phase must run this query from a safe DB/admin shell before DDL:

```sql
SELECT
  c.relname AS index_name,
  t.relname AS table_name,
  i.indisvalid AS is_valid,
  i.indisunique AS is_unique,
  pg_get_indexdef(i.indexrelid) AS index_definition
FROM pg_index i
JOIN pg_class c ON c.oid = i.indexrelid
JOIN pg_class t ON t.oid = i.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'public'
  AND t.relname IN ('payments', 'payment_intents', 'access_grants', 'marketplace_entitlements')
ORDER BY t.relname, c.relname;
```

Skip equivalent valid indexes. Leave non-unique helper indexes alone unless separately approved.

## Candidate DDL
Important: `CREATE INDEX CONCURRENTLY` cannot run inside a transaction. Do not run from FastAPI startup. Do not run during deployment startup.

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

## Rollback plan
Important: `DROP INDEX CONCURRENTLY` cannot run inside a transaction.

```sql
DROP INDEX CONCURRENTLY IF EXISTS idx_marketplace_entitlements_listing_user_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_access_grants_active_user_feature_payment_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_access_grants_active_user_feature_intent_unique;
DROP INDEX CONCURRENTLY IF EXISTS idx_payment_intents_tx_signature_unique_nonempty;
DROP INDEX CONCURRENTLY IF EXISTS idx_payments_tx_signature_unique_nonempty;
```

## Failure criteria
Stop if production health fails, OpenAPI fails, admin aggregate endpoint fails closed unexpectedly, safety flags are missing/unsafe, duplicate counts are nonzero, existing equivalent indexes are invalid/confusing, DDL reports lock/duplicate errors, or post-migration verification fails.

## Post-migration verification
Re-run health/OpenAPI/auth gates, aggregate duplicate preflight, and index inspection. Confirm all intended indexes exist, are valid, unique, and partial where expected.

## Exact owner approval prompt
`I approve the AgentAscend Postgres replay-index migration DDL phase. Run the health/OpenAPI/auth prechecks, admin aggregate duplicate preflight, read-only existing index inspection, then run only the safe concurrent unique index DDL if duplicate counts are zero and equivalent valid indexes do not already exist. Do not run DDL inside a transaction, do not run from FastAPI startup, do not mutate any rows, and stop on any blocker.`
