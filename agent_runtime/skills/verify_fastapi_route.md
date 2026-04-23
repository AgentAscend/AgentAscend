# Skill: verify_fastapi_route

Purpose
- Perform deterministic route-level checks without broad integration churn.

Inputs
- Target route file path.
- Expected status/error matrix.

Procedure
1) Fail-fast
- Stop if target file does not compile.
- Stop if request schema cannot be imported.

2) Local verification
- Run `python3 -m py_compile <route-file> <schema-file-if-any>`.
- Execute focused script/test hitting only the target route behaviors.

3) Required assertions
- Client errors map to 4xx with explicit messages.
- Server/config errors map to 5xx with explicit messages.
- Success payload follows response schema exactly.

4) Report format
- List each test case as PASS/FAIL with status code and message.
- Include any environment assumptions.

Rollback
- If checks fail after edits, revert only the edited file (`git checkout -- <file>`) and re-apply minimal fix.
