# Core Flow Test Runbook

## Scope
Validate critical auth → payment → access → gated-tool flow without exposing secrets.

## Preconditions
- Backend API reachable (`/health` returns ok)
- Test user credentials available (non-production throwaway account)
- Required payment env vars configured on backend

## 1) Fast regression suite (local)
```bash
cd /home/agentascend/projects/AgentAscend
PYTHONPATH=. .venv/bin/pytest -q
```

## 2) Focused security/payment checks
```bash
cd /home/agentascend/projects/AgentAscend
PYTHONPATH=. .venv/bin/pytest -q tests/test_tools_access_security.py tests/test_legacy_payment_verify_security.py tests/test_payment_schema_migration.py tests/test_pumpfun_payment_routes.py
```

Expected: all tests pass.

## 3) Task/output pipeline checks
```bash
cd /home/agentascend/projects/AgentAscend
PYTHONPATH=. .venv/bin/pytest -q tests/test_tasks_outputs_pipeline.py tests/test_execution_ledger_schema.py
```

## 4) Live API smoke sequence (manual)
1. Sign up/sign in test user.
2. Call payment create endpoint and capture `reference`.
3. Submit verify request with matching user/token/reference.
4. Confirm access-grant check returns granted.
5. Invoke gated tool route and confirm access is enforced.
6. Validate execution/task surfaces if task workflow is used.

Run this live sequence only in an explicitly approved smoke-test phase. Do not run real wallet payments, wallet signing, SOL transfers, Pump.fun claims, or production mutations from this runbook.

## Expected guardrail behavior
- Spoofed `user_id` requests are rejected.
- Verify calls without valid intent/reference binding are rejected.
- Failed verify attempts do not permanently lock idempotency keys.

## Failure triage checklist
- Confirm caller auth header is present where required.
- Confirm verify payload uses the same reference returned by create.
- Confirm Solana RPC connectivity and receiver/mint configuration.
- Re-check DB schema migration state for payment/access tables.

## Safety notes
- Use throwaway test users and mocked/sandboxed payment payloads unless a real-payment canary is explicitly approved.
- Never print private keys, bearer tokens, DB passwords, or seed phrases.
- Do not treat frontend state as payment truth; backend is authoritative.