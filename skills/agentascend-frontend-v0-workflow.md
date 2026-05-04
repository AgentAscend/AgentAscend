# AgentAscend Frontend v0 Workflow

## When to use
Use for v0 prompts, frontend ZIP audits, and live frontend/backend parity checks.

## Rules
- Preserve existing design unless the owner explicitly requests redesign.
- Use small patch-only prompts.
- Wire UI to backend truth; do not invent demo authority.
- No localStorage authority for paid access, payment verification, marketplace install/ownership, auth bypass, or production settings.
- Backend empty/error/auth-required states must render honestly.

## Checks
1. Fetch live OpenAPI and list required routes.
2. Audit the v0 ZIP from a fresh `/tmp` extraction.
3. Run compile/typecheck/build gates when available.
4. Verify pages consume live hooks/adapters in render paths, not just imports.
5. After deploy, scan live route chunks for expected backend markers and absence of legacy paid-unlock markers.

## Output
Return a concise PASS/PARTIAL/FAIL report and the next copy-paste v0 patch prompt.
