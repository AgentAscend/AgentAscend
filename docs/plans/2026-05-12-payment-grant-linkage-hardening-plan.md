# Payment↔Grant Linkage Hardening Plan

> For Hermes: this is a planning document for a future TDD/local-first implementation. Do not use this plan as approval to push, deploy, mutate production data, run payments, call Pump.fun verify, create/revoke grants, or change scheduler state.

## Goal
Make future payment-created access grants durably link back to their payment and intent records so AgentAscend can audit paid access end-to-end.

## Risk posture
- This is a launch-risk and auditability hardening plan.
- This is not an emergency production mutation.
- No production DB writes are approved by this plan.
- No production backfill or cleanup is approved by this plan.
- No payment replay is approved by this plan.
- No Pump.fun verify call is approved by this plan.
- No access_grant or marketplace_entitlement mutation is approved by this plan.
- Any future production backfill, cleanup, replay, grant repair, entitlement repair, or verification run requires explicit owner approval.

## Architecture
Use TDD to prove forward invariants in local tests before any backend implementation. Future implementation must inspect whether completed payments have clean linkage to:
- `payment_intents`
- `access_grants`
- `marketplace_entitlements`
- `intent_reference`
- `payment_id`
- `tx_signature`

The implementation target is forward correctness first: new verified payment flows should write durable linkage at creation time. Historical repair must remain a separate proposal until owner-approved.

## Tech stack
- FastAPI backend
- Existing payment/access services
- SQLite test database
- pytest
- Local-only source review and tests

---

## Scope guard

### Allowed for this planning pack
- Preserve this plan.
- Preserve the related skill and learning note.
- Commit docs/skills/learning files only.

### Allowed only in a future explicitly approved local TDD implementation
- Read source and tests.
- Add/modify focused local tests.
- Modify backend payment/access code locally.
- Run local pytest and compile checks.
- Produce a proposal-only historical backfill document.

### Forbidden unless explicitly approved by the owner
- Production DB writes or backfills.
- Production cleanup scripts.
- Payment verification/replay with real transactions.
- Calling Pump.fun verify.
- Creating or revoking production `access_grants`.
- Changing production `marketplace_entitlements`.
- Scheduler/job state changes.
- `/jobs/run-due`.
- Deploys, pushes, migrations, index creation/drop, env edits, or package changes.
- Printing secrets, raw private rows, raw payloads, signed transactions, wallet private data, DB URLs, RPC URLs, cookies, or auth tokens.

---

## Future implementation sequence

### Task 1: Baseline payment/access tests

Objective: confirm local payment/security baseline before editing code.

Files to inspect in the future implementation:
- `backend/app/routes/payments.py`
- `backend/app/routes/pumpfun_payments.py`
- `backend/app/services/access_service.py`
- Existing payment/security tests

Command:
```bash
pytest -q tests/test_pumpfun_payment_routes.py tests/test_legacy_payment_verify_security.py tests/test_tools_access_security.py
```

Expected result: existing focused suite passes, or known unrelated failures are documented before changes.

Stop if unexpected payment/security failures appear.

---

### Task 2: RED test for legacy payment grant linkage

Objective: prove legacy payment verification creates an active grant linked to the inserted payment row.

Suggested file:
- Create or modify: `tests/test_payment_grant_linkage.py`

Test behavior:
- Arrange a successful legacy payment verification using existing test fakes.
- Query the local test DB for the inserted `payments` row.
- Query `access_grants` for the user/feature.
- Assert the active grant has:
  - `payment_id == payments.id`
  - non-empty `intent_reference` when an intent/reference exists
  - expected source/feature fields

Command:
```bash
pytest -q tests/test_payment_grant_linkage.py::test_legacy_verify_links_active_grant_to_payment -vv
```

Expected RED: fail because existing linkage is absent or incomplete.

---

### Task 3: GREEN minimal legacy linkage implementation

Objective: make the legacy RED test pass without broad refactor.

Likely files:
- `backend/app/routes/payments.py`
- `backend/app/services/access_service.py` if the grant creation API needs linkage parameters

Implementation guidance:
- Keep payment insert and grant insert in the same DB transaction/connection.
- Capture the inserted payment id.
- Pass `payment_id` and `intent_reference` into access grant creation.
- Preserve API response shape.
- Preserve replay/idempotency behavior.
- Do not add production backfill logic in this task.

Verification:
```bash
pytest -q tests/test_payment_grant_linkage.py::test_legacy_verify_links_active_grant_to_payment -vv
```

Expected GREEN: test passes.

---

### Task 4: RED test for Pump.fun grant linkage

Objective: prove Pump.fun verified payment creates active listing/tool grant with durable linkage.

Suggested file:
- `tests/test_payment_grant_linkage.py`

Test behavior:
- Use existing Pump.fun route test fixtures/fakes for successful local create + verify behavior.
- Query local test DB for payment, payment intent, grant, and entitlement records.
- Assert the grant includes:
  - `payment_id` matching inserted payment id
  - `intent_reference` matching immutable payment intent/reference
  - correct listing/product scope when listing-scoped
- Assert marketplace entitlement behavior remains unchanged except for intended linkage if later implemented.

Command:
```bash
pytest -q tests/test_payment_grant_linkage.py::test_pumpfun_verify_links_active_grant_to_payment_and_intent -vv
```

Expected RED: fail if linkage fields are absent or incomplete.

---

### Task 5: GREEN minimal Pump.fun linkage implementation

Objective: make the Pump.fun linkage test pass while preserving existing listing/tool behavior.

Likely files:
- `backend/app/routes/pumpfun_payments.py`
- `backend/app/services/access_service.py` if linkage parameters are centralized there

Implementation guidance:
- Capture payment id from the inserted/recorded payment row.
- Use the stored immutable intent/reference value for `intent_reference`.
- Pass linkage fields when creating access grants.
- Preserve marketplace entitlement behavior.
- Preserve exact tx signature binding behavior.
- Preserve safe error codes/statuses.
- Do not call live Pump.fun verify during local implementation.

Verification:
```bash
pytest -q tests/test_payment_grant_linkage.py::test_pumpfun_verify_links_active_grant_to_payment_and_intent -vv
```

Expected GREEN: test passes.

---

### Task 6: RED/GREEN rollback invariant test

Objective: prove payment insert, intent consumption, grant creation, and entitlement write are atomic where they are part of one payment flow.

Suggested file:
- `tests/test_payment_grant_linkage.py`

Test behavior:
- Force grant creation to raise during local verification.
- Use `TestClient(app, raise_server_exceptions=False)` if needed.
- Assert no completed payment row remains.
- Assert intent is not consumed.
- Assert no active grant exists.
- Assert no marketplace entitlement was created when the grant failed.

Command:
```bash
pytest -q tests/test_payment_grant_linkage.py::test_payment_verify_rolls_back_when_grant_insert_fails -vv
```

Expected: RED before transaction fix if non-atomic; GREEN after minimal transaction fix.

---

### Task 7: Regression suite

Objective: ensure linkage changes do not break existing payment/security behavior.

Command:
```bash
pytest -q tests/test_payment_grant_linkage.py tests/test_pumpfun_payment_routes.py tests/test_legacy_payment_verify_security.py tests/test_legacy_payment_atomicity.py tests/test_payment_replay_race.py tests/test_tools_access_security.py
python -m py_compile backend/app/routes/payments.py backend/app/routes/pumpfun_payments.py backend/app/services/access_service.py
```

Expected: pass.

---

### Task 8: Historical backfill proposal only

Objective: document how to repair historical rows without executing it.

Suggested future file:
- `raw/payment-audits/YYYY-MM-DD-payment-grant-backfill-proposal.md`

Proposal must include:
- scope distinction: local SQLite vs production Postgres
- read-only aggregate checks needed before mutation
- deterministic matching keys available
- rows that cannot be safely matched automatically
- transaction/rollback plan
- dry-run output shape
- owner approval gate before execution

Expected: report-only proposal; no data mutation.

---

## Completion criteria before requesting implementation commit/deploy approval
- New tests failed first and then pass.
- Existing payment/security regression tests pass.
- No production data touched.
- No payment replay or Pump.fun verify call occurred.
- No access grant or marketplace entitlement production mutation occurred.
- Backfill remains proposal-only.
- Git changes are limited to intended tests/code/docs for the approved implementation slice.
- Secret/safety scan over changed files passes without exposing secrets or raw private data.
