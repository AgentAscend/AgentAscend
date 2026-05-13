# Payment↔Grant Linkage Hardening

## When to use
Use when investigating or fixing payment/access auditability gaps where completed payments may not be durably linked to active access grants and marketplace entitlements by `payment_id`, `intent_reference`, and `tx_signature`.

## Allowed scope
For planning-only work:
- Read and update the approved plan/skill/learning files.
- Do not touch backend, frontend, tests, package files, scheduler config, or production systems.

For a future explicitly approved local TDD implementation:
- Read `MEMORY.md` and verify git state.
- Read source and tests locally.
- Add focused local tests first.
- Modify backend payment/access code locally only after RED tests exist.
- Run targeted local pytest and compile checks.
- Draft report-only backfill proposals.

## Forbidden scope without explicit owner approval
- Push or deploy.
- Production DB writes, backfills, cleanup scripts, migrations, or index changes.
- Payment replay or live payment verification.
- Pump.fun verify calls.
- Creating/revoking production `access_grants`.
- Changing production `marketplace_entitlements`.
- Scheduler job changes, scheduler job runs, or `/jobs/run-due`.
- Railway/Vercel variable changes.
- Telegram/external messages.
- Printing secrets, DB URLs, RPC URLs, auth tokens, cookies, private keys, seed phrases, signed transactions, raw request/response bodies, raw DB rows, raw `metadata_json`, raw `payload_json`, raw task body/output, or wallet private data.

## Inputs needed
- Current `MEMORY.md`.
- Latest approved plan: `docs/plans/2026-05-12-payment-grant-linkage-hardening-plan.md`.
- Latest sanitized payment/access audit notes, if any.
- Exact scope: local SQLite, staging Postgres, or production Postgres.
- Explicit owner approval before any production read beyond sanitized aggregates or any production mutation.

## Procedure
1. Confirm the work mode: planning-only, local TDD implementation, or owner-approved production remediation.
2. Verify git state and stop if the branch/scope is unclear.
3. For local TDD implementation, establish baseline focused tests before edits.
4. Write RED tests for forward invariants:
   - legacy verified payment creates a grant with `payment_id` and intent/reference metadata when applicable;
   - Pump.fun verified payment creates listing/tool grant with `payment_id` and `intent_reference`;
   - grant failure rolls back payment/intent consumption and entitlement creation where applicable;
   - duplicate/retry path remains deterministic and creates no duplicate grant.
5. Implement minimal local code changes to pass tests.
6. Run targeted payment/security regressions.
7. Draft a separate historical backfill proposal; do not execute it without owner approval.
8. Run scoped secret/safety scan and git diff review before any commit request.

## Required tests for future implementation
- `tests/test_payment_grant_linkage.py::test_legacy_verify_links_active_grant_to_payment`
- `tests/test_payment_grant_linkage.py::test_pumpfun_verify_links_active_grant_to_payment_and_intent`
- `tests/test_payment_grant_linkage.py::test_payment_verify_rolls_back_when_grant_insert_fails`
- Existing Pump.fun payment route tests.
- Existing legacy payment verification/security tests.
- Existing replay/idempotency tests.
- Existing tools/access security tests.

## Stop conditions
Stop and report PARTIAL/FAIL if:
- Production-vs-local scope is unclear.
- A test requires broad unrelated refactors.
- The implementation would change API contracts unexpectedly.
- The fix requires production mutation, payment replay, Pump.fun verify, grant repair, entitlement repair, deploy, scheduler run, or env change without explicit owner approval.
- Any scanner finds actual secret material or raw private data.
- Any forbidden path is dirty/staged in a planning-only phase.

## Evidence/report format
Report:
1. PASS / PARTIAL / FAIL.
2. Scope used: planning-only, local TDD, or owner-approved remediation.
3. Git branch, HEAD, origin/main, and changed files.
4. Tests run and result, including RED then GREEN evidence for new tests when implementing.
5. Linkage invariants proven or not proven.
6. Production actions taken: should be `none` unless explicitly approved.
7. Safety scan result, with findings by file/line/category only and no matched values.
8. Remaining risks and next owner approval needed.

## Expected pass/fail
PASS:
- Planning phase changes only approved docs/skills/learning files, or implementation phase proves all new payment-created active grants carry linkage fields.
- Existing replay/idempotency tests still pass.
- Historical data repair remains separate and owner-approved.

FAIL/PARTIAL:
- Cannot confirm production-vs-local scope.
- Tests require broad unrelated refactors.
- A necessary next step would mutate production data or require deploy without owner approval.

## Common failure modes
- Confusing local SQLite report findings with production Postgres state.
- Backfilling before tests prove forward invariants.
- Printing raw private DB rows while debugging.
- Fixing Pump.fun and forgetting legacy `/payments/verify`, or vice versa.
- Treating `intent_reference` as optional for new payment-created grants when auditability requires it.
- Committing planning notes together with backend/payment code.
