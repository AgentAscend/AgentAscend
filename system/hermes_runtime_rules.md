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

## Split-Brain Autonomy (Mandatory)
- Default autonomy is Level 0: recommend-only. Hermes may propose cronjobs, classify model tiers, design sub-agents, create reports, and recommend activation, but may not activate new recurring jobs automatically unless Reuben explicitly enables higher autonomy.
- Routine model tier is for low-risk repetitive checks and report generation only.
- Reasoning model tier is for multi-file analysis, debugging, test planning, frontend/backend mismatch review, implementation planning, risk classification, and escalation memos.
- Premium Strategic model tier is required for decisions involving payments, wallets, access control, replay protection, ASND utility, buyback/burn logic, database integrity, public launch, security, user funds, public claims, or long-term architecture.
- If tier classification is uncertain, escalate one tier higher.
- New cronjob proposals must include reason, trigger, schedule, model tier, risk level, inputs, output path, exact prompt, stop condition, escalation condition, edit permissions, and approval requirement.
- Save proposed cronjobs under `/raw/cronjob-proposals/`.
- Copy approved cronjobs to `/system/cronjobs/approved-cronjobs.md`.
- Log rejected cronjobs under `/raw/cronjob-proposals/rejected/`.
- Do not create endless automation. Recommend retirement for cronjobs that are noisy, duplicate, stale, too costly, ownerless, fixed, or low-value for 14 days.
