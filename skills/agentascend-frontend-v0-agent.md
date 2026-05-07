# Frontend V0 Agent

## Purpose
Operate the `agentascend-frontend-v0-agent` lane for AgentAscend with bounded, report-first work against the current live runtime/product state.

## Allowed scope
- Read `MEMORY.md` first and verify git/live production state before changes.
- Work only in the lane implied by this skill name.
- For documentation lanes: edit only `MEMORY.md`, `docs/`, `wiki/`, `raw/`, `learning/`, `skills/`, and `system/`.
- For implementation lanes: propose or implement only an explicitly approved smallest-safe slice, then stop at the required gate.

## Forbidden scope
- No backend/frontend code changes unless the owner explicitly requests that implementation slice.
- No production DB mutation, migrations, DDL, or indexes without explicit approval.
- No Railway/Vercel variable changes without explicit approval.
- No scheduler job enable/disable/run, and no `/jobs/run-due`.
- No payments, payment intents, Pump.fun verify, access_grants, marketplace_entitlements, Pump.fun claims, buyback settings, or wallet actions.
- No Telegram/external messages unless explicitly approved.
- No secrets or raw private data in output or files.
- Do not stage `.obsidian` workspace/graph files.

## Required checks
1. Read `MEMORY.md`.
2. Verify git branch, HEAD, origin/main, ahead/behind, staged files, and dirty summary.
3. Verify relevant live health/OpenAPI/security headers when production state matters.
4. Use the standing post-deploy QA protocol after any deploy-triggering push.
5. Run `git diff --check` and a focused secret/safety scan before staging docs or code.
6. Stage only the approved file scope.

## Stop conditions
Stop and report PARTIAL/FAIL if the task requires unapproved production mutation, scheduler state change/run, payment action, external message, secrets, raw private data, destructive git operation, or unclear source of truth. Stop if local `main` is diverged and use a clean worktree for any approved docs-only commit.

## Handoff format
Report PASS/PARTIAL/FAIL, files changed, checks run, live/prod evidence, blocked items, exact next owner approval prompt, and safety confirmations.

## Current relevant project state
- Runtime worker is live.
- Runtime-aware frontend loop is owner-verified: Agent → Run Agent → Task → Execution → Output.
- Payment flow works and controlled Pump.fun regression passed.
- Replay-index DDL is not needed because protections already exist.
- Post-deploy QA protocol is active.
- Playwright harness exists at `/tmp/agentascend-browser-qa/agentascend-browser-qa.js`.
- Hermes local/report-only swarm jobs and weekly hygiene job are active.
- Telegram sends remain not approved by default.
- Next product focus: frontend polish, workflow builder UX, output UX, task detail UX, execution detail UX, deployment events UX, and settings/community polish.

## Links to runbooks and hubs
- [[current-project-state|Current Project State]]
- [[AgentAscend]]
- [[Hermes]]
- [[Cronjobs]]
- [[scheduler|Scheduler]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- `docs/post-deploy-qa-protocol.md`
- `docs/automation-governance.md`
- `docs/hermes-agent-operating-model.md`
- `docs/hermes-swarm-cadence.md`
