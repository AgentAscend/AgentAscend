# Skill: sqlite_schema_check

Purpose
- Verify SQLite schema compatibility and migration safety for backend runtime DB.

Scope
- `backend/app/db/session.py`
- `backend/app/db/agentascend.db`

Procedure
1) Fail-fast
- Compile db session file: `python3 -m py_compile backend/app/db/session.py`.
- Abort on compile error.

2) Schema checks
- Inspect table DDL: `sqlite3 backend/app/db/agentascend.db ".schema payments"`.
- Confirm required columns exist (including `tx_signature`).
- Confirm uniqueness/index protection for replay-sensitive fields.

3) Migration checks
- Run app init path once; ensure no migration crashes on existing DB.
- Re-run init path to confirm idempotence.

4) Output
- Emit explicit PASS/FAIL for each required schema guarantee.

Rollback
- If migration logic breaks schema, restore prior commit of `session.py` and recover DB from backup snapshot before reapplying fix.
