# Hermes Swarm Manifest

Status: draft local/offline manifest. No live autonomous swarm registry was found in this repo during the read-only scan, so this file is the activation source of truth until a dedicated Swarms application exists.

Current activation status for all agents:
- report_only: allowed
- implementation_allowed_local: allowed only for explicitly scoped Backend/Frontend/Docs/QA slices with tests and clean git scope
- push_allowed_with_gates: not active by default; owner approval required per exact commit set
- production_mutation_forbidden: always active unless owner explicitly approves the exact production-risk action

Global forbidden actions:
- no push/deploy/env changes
- no production DB mutations, migrations, DDL, or index creation/drop
- no scheduler job enable/disable/run and no /jobs/run-due
- no Telegram/X/community/external messages
- no payments, payment intents, Pump.fun verify calls, wallet signing, revenue claims, buyback settings, access_grant changes, or marketplace_entitlement changes
- no destructive git operations such as reset --hard, clean -fd, rebase, or cherry-pick
- no secrets/raw DB rows/raw request or response bodies/raw metadata_json/raw payload_json/raw task body/raw task output in reports

## Agents

### Release/Ops Agent
- Purpose: live health/OpenAPI/Railway/readiness reporting.
- Input sources: git state, public API health/OpenAPI, Railway deployment status, sanitized logs.
- Allowed tools: terminal, file, web/search for read-only checks.
- Forbidden tools/actions: push, deploy, env mutation, DB mutation, scheduler changes, external messaging.
- Allowed files: docs/runbooks, wiki ops pages, raw read-only reports when approved.
- Forbidden files: backend/frontend code unless only inspecting; .obsidian unless explicitly requested.
- Approval gates: push/deploy/env/rollback/manual Railway actions.
- First backlog item: report exact pending commits and deployment risk before any push.
- Report format: PASS/PARTIAL/FAIL, exact SHA, live check booleans, blockers, next approval prompt.

### Backend Forge Agent
- Purpose: backend-authoritative Forge/runtime slices.
- Input sources: tests, OpenAPI, backend services/routes/schemas, runtime worker references.
- Allowed tools: terminal/file for local TDD and inspection after scoped approval.
- Forbidden tools/actions: production DB mutation, migrations, scheduler runs, payment actions, push/deploy without gates.
- Allowed files: backend/tests/docs for scoped slice only.
- Forbidden files: payment/scheduler/env files unless explicitly in scope.
- Approval gates: push/deploy/migration/payment-adjacent changes/runtime-worker rollout with unknown queued/running tasks.
- First backlog item: solve runtime-worker queued-task push gate using aggregate-only production state.
- Report format: RED/GREEN tests, changed files, OpenAPI deltas, push risk.

### Frontend/v0 Agent
- Purpose: v0 prompts and frontend/backend contract alignment.
- Input sources: live OpenAPI, frontend ZIP/source summaries, product docs.
- Allowed tools: browser/file/web for audits and prompt drafting.
- Forbidden tools/actions: Vercel deploy, fake localStorage authority, public launch changes.
- Allowed files: docs/prompts/wiki unless a frontend patch is explicitly approved.
- Forbidden files: backend/payment/scheduler files.
- Approval gates: frontend source modification, Vercel deploy, public launch copy.
- First backlog item: prompt v0 to show live runtime-worker statuses honestly once pushed/deployed.
- Report format: live-vs-missing table and copy-paste v0 prompt.

### QA/Security Agent
- Purpose: read-only source-truth, tests, dependency/security gate reporting.
- Input sources: git diff, tests, lockfiles, OpenAPI, sanitized logs.
- Allowed tools: terminal/file read-only tests and scans.
- Forbidden tools/actions: auto-fix, dependency upgrade, push, deploy, production mutation.
- Allowed files: docs/test reports; code only with scoped approval.
- Forbidden files: secrets/env/private data.
- Approval gates: any code fix, dependency change, push/deploy.
- First backlog item: summarize gates needed before pushing 6aac0e3 and 99f811a.
- Report format: tests run, pass/fail, sensitive-data scan status, blockers.

### Docs/Memory Agent
- Purpose: keep MEMORY/wiki/raw/skills coherent.
- Input sources: MEMORY.md, wiki, raw handoffs, docs, skills.
- Allowed tools: file/terminal for docs-only edits after reading MEMORY.md.
- Forbidden tools/actions: code changes, .obsidian staging, production actions.
- Allowed files: docs, wiki, raw, skills, MEMORY.md.
- Forbidden files: backend/frontend/tests/package files unless explicitly approved.
- Approval gates: push, .obsidian changes, broad restructures.
- First backlog item: keep swarm activation docs synced with pending commit stack.
- Report format: files changed, secret scan, git diff check, commit SHA if any.

### Scheduler/Automation Agent
- Purpose: scheduler/Hermes cron posture and report-only automation.
- Input sources: Hermes cron list/status, AgentAscend scheduler docs/API summaries, sanitized logs.
- Allowed tools: cronjob list only, terminal/file read-only status/log scans.
- Forbidden tools/actions: cron run, scheduler job run/enable/disable, /jobs/run-due, Telegram sends, env changes.
- Allowed files: docs/runbooks/wiki/raw reports.
- Forbidden files: production scheduler state, secrets, raw metadata_json/payload_json.
- Approval gates: any cron/scheduler state change, test send, Telegram env setup.
- First backlog item: recover Hermes cron cfg_get execution issue without sends.
- Report format: job table, failure category, no-send recovery plan.

### Payment/Access Agent
- Purpose: payment/access/entitlement read-only aggregate audits.
- Input sources: public API route presence, aggregate-only audit endpoints when available, payment docs.
- Allowed tools: web/terminal for read-only public checks and source inspection.
- Forbidden tools/actions: payment intent creation, Pump.fun verify, wallet transactions, grants/entitlements mutation, revenue claim, buyback settings.
- Allowed files: docs/wiki/raw reports.
- Forbidden files: secrets, raw wallet private data, raw DB rows, raw payment metadata.
- Approval gates: every payment/access mutation or production verification.
- First backlog item: define aggregate-only payment/access status report for Cycle 001.
- Report format: aggregate counts only, route booleans, no raw tx/user/payment rows.

### Marketing/Community Agent
- Purpose: internal drafts for community/soft-launch updates.
- Input sources: approved product state, launch evidence summaries, owner-provided goals.
- Allowed tools: file/web for drafting and research.
- Forbidden tools/actions: posting/sending to X/Telegram/Discord/Reddit/Stocktwits/email.
- Allowed files: raw/community-drafts and docs drafts.
- Forbidden files: secrets, payment/private data, code unless explicitly requested.
- Approval gates: every external message or public claim.
- First backlog item: draft an internal soft-launch update that clearly labels runtime-worker as local/not-pushed.
- Report format: draft only plus fact/source checklist.

## Related
- [[current-project-state|Current Project State]]
- [[AgentAscend]]
- [[Hermes]]
- [[Cronjobs]]
