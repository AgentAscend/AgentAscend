# Hermes Runtime Rules

## Scope
These runtime rules constrain autonomous repository operations in AgentAscend.
They complement AGENTS.md and are intended to be machine-auditable.

## Knowledge Boundaries (Mandatory)
- `/raw` is for unprocessed inputs only.
- `/wiki` is for structured schema-compliant pages only.
- `/system` is for system purpose/rules/schema only.
- Do not mix raw and structured content across these boundaries.

## Payment Enforcement (Mandatory)
- Backend payment verification is the source of truth.
- No bypass logic is allowed in Hermes/tool routes.
- Access grants are valid only after backend verification and successful payment insert.
- Replay protection via `tx_signature` uniqueness must remain enforced.

## File Write Policy
- Follow `agent_runtime/policies/write_allowlist.json`.
- Treat `agent_runtime/policies/protected_paths.json` as higher priority than allowlist.
- Any write/delete touching protected paths requires explicit user approval.

## Shell Command Policy
- Follow `agent_runtime/policies/shell_allowlist.json`.
- Prefer deterministic, non-destructive commands.
- Avoid privilege escalation and destructive filesystem operations.

## Verification Discipline
- One-file change loops are preferred.
- Verify after each file change (compile/test/schema checks as applicable).
- Keep docs/wiki commits separate from backend commits.
- Keep changes incremental; avoid broad redesign unless explicitly requested.
