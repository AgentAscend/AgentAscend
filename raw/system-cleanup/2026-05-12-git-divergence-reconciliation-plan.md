---
type: raw
project: AgentAscend
date: 2026-05-12
---

# Git Divergence Reconciliation Plan — 2026-05-12

## Scope
Read-only reconciliation analysis for local `main` divergence from `origin/main`, plus clean commit group proposal for current dirty/untracked knowledge work.

## Baseline
- Branch: `main`
- Local HEAD: `c076ff65bfdf7334b746d40923c0c0c36eb9bfac`
- `origin/main`: `74bd6e92d2129500dc92261eda9f9b09ea2a5ae5`
- Merge base: `1bb536aad9bf93f02e9f79199e7f9f48e6cd325a`
- Divergence: `origin/main...HEAD = 8 left / 8 right`
- Staged files: none
- No push, deploy, reset, merge, rebase, stash, commit, production DB mutation, scheduler mutation, payment action, or env change performed.

## Key finding
Do **not** push local `main` as-is. It is an older diverged line that contains duplicate/superseded versions of backend commits already present on `origin/main`, while `origin/main` also has remote-only production-relevant commits not present locally.

The safest reconciliation path is:
1. Keep local `main` as a reference/backup only.
2. Use `origin/main` as the canonical base.
3. Port only intentionally selected docs/evidence/current-cleanup files into a clean worktree or clean branch based on `origin/main`.
4. Commit in small docs/knowledge batches.
5. Do not push until explicit owner approval and standing post-deploy QA plan is ready.

## Ahead commits on local main

### Drop / do not replay directly
- `6aac0e3` — `backend: add agent runtime worker execution`
  - Patch-equivalent to remote `5e7afb1` per `git cherry`.
  - Do not replay; keep remote canonical commit.
- `6815807` — `Harden workflow auth ownership`
  - Patch-equivalent to remote `5299417` per `git cherry`.
  - Do not replay; keep remote canonical commit.

### Port selectively as docs/evidence only if still useful
- `99f811a` — `Define Hermes multi-agent operating model`
  - Local docs/skills/wiki swarm operating model.
  - Remote has newer/canonical `2d34357` and later `dc49e5b`; do not replay wholesale.
- `37397b6` — `Refine Hermes swarm activation and cron recovery plan`
  - Local docs/skills/wiki refinements.
  - Likely superseded by remote `dc49e5b` and current 2026-05-12 cronjob cleanup.
- `f3d3a7f` — `Record owner-assisted runtime frontend QA pass`
  - Potentially useful historical frontend QA evidence; port only sanitized raw/wiki deltas if absent on origin.
- `c8f0246` — `Add standing post-deploy QA protocol`
  - Remote has similar canonical `29a07f1`; do not replay wholesale.
- `cf938b8` — `Record logged-in runtime QA pass with caveats`
  - Potentially useful historical QA evidence; port sanitized raw/wiki deltas if absent on origin.
- `c076ff6` — `Record workflow owner isolation QA pass`
  - Remote has current canonical `74bd6e9`; do not replay wholesale.

## Behind commits on origin/main that must be preserved
- `2d34357` — Publish Hermes swarm operating model
- `2f7eb59` — Add admin task runtime aggregate audit endpoint
- `5e7afb1` — backend: add agent runtime worker execution
- `29a07f1` — Add standing post-deploy QA protocol
- `712c05e` — Archive v0 frontend deploy evidence
- `dc49e5b` — Run system hygiene and cronjob audit
- `5299417` — backend: harden workflow auth ownership
- `74bd6e9` — Record workflow owner isolation QA pass

These remote commits are the production/canonical line. Any clean reconciliation branch should start from `origin/main`.

## Merge conflict expectation
A direct merge of local `main` and `origin/main` is not recommended. `git merge-tree --write-tree --name-only --messages HEAD origin/main` reports conflicts in:
- `MEMORY.md`
- `docs/automation-governance.md`
- `docs/frontend-v0-runbook.md`
- `docs/hermes-swarm-cadence.md`
- `docs/hermes-swarm-manifest.md`
- `docs/post-deploy-qa-protocol.md`
- all eight `skills/agentascend-*-agent.md` swarm skill files
- `wiki/Agent Architecture.md`
- `wiki/AgentAscend.md`
- `wiki/Cronjobs.md`
- `wiki/Execution Ledger.md`
- `wiki/Hermes.md`
- `wiki/current-project-state.md`
- `wiki/frontend-v0-workflow.md`
- `wiki/known-issues.md`

A normal merge would mix old local docs with newer remote docs and create large conflict resolution risk.

## Current dirty tracked files
- `.gitignore`
- `.obsidian/graph.json`
- `.obsidian/workspace.json`
- `MEMORY.md`
- `system/cronjobs/approved-cronjobs.md`
- `wiki/Cronjobs.md`
- `wiki/Launch Readiness.md`
- `wiki/Roadmap.md`
- `wiki/current-project-state.md`
- `wiki/known-issues.md`

Recommendation: do not commit `.obsidian/*` in the first reconciliation batch. Treat them as local editor state unless owner explicitly wants Obsidian workspace layout committed.

## Current untracked summary
- `docs`: 1 file
- `learning`: 11 files
- `raw`: 48 files
- `skills`: 13 files
- `wiki`: 5 files
- `wikilinks.md`: 1 file

Total untracked files: 79.

## Proposed clean commit groups

### Group 0 — Safety baseline / no commit
Purpose: preserve state before any operation.
Actions:
- Create backup branch/tag if approved: `backup/local-main-diverged-2026-05-12` at current local HEAD.
- Do not push it by default.
- Work from a clean worktree based on `origin/main` for actual publishable commits.

### Group 1 — 2026-05-12 system cleanup + cronjob state docs
Risk: docs/knowledge only, but GitHub push may trigger Railway deploy; requires standing docs-only post-deploy QA if pushed.
Files to port/commit from current dirty tree:
- `.gitignore`
- `MEMORY.md`
- `system/cronjobs/approved-cronjobs.md`
- `wiki/current-project-state.md`
- `wiki/Cronjobs.md`
- `wiki/known-issues.md`
- `wiki/Launch Readiness.md`
- `wiki/Roadmap.md`
- `raw/system-cleanup/2026-05-12-project-cleanup-cronjob-review.md`
- `raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup.md`
- `raw/system-cleanup/2026-05-12-git-hygiene-secret-scan.md`
- `raw/system-cleanup/2026-05-12-git-divergence-reconciliation-plan.md`

Commit message suggestion:
- `docs: refresh project state and cronjob cleanup evidence`

Checks before commit:
- `git diff --check -- <files>`
- scoped secret scan over only these files
- wiki schema check for the touched wiki pages

### Group 2 — Payment↔grant linkage planning pack
Risk: docs/skill/plan only; no code/data mutation.
Files:
- `docs/plans/2026-05-12-payment-grant-linkage-hardening-plan.md`
- `skills/payment-grant-linkage-hardening.md`
- `learning/payment-grant-linkage-auditability.md`

Commit message suggestion:
- `docs: plan payment grant linkage hardening`

Checks:
- `git diff --check -- <files>`
- scoped secret scan over these files

### Group 3 — Recent frontend QA evidence pack
Risk: docs/raw evidence only.
Files:
- `raw/frontend-qa/2026-05-11-full-signed-in-functional-ux-qa-pass.md`

Optional after review:
- port any still-missing older local QA evidence from `f3d3a7f` and `cf938b8` if absent on origin.

Commit message suggestion:
- `docs: archive full signed-in frontend QA evidence`

### Group 4 — Curated historical knowledge archive
Risk: broad knowledge-base noise; review in batches before commit.
Candidate folders/files:
- `learning/*.md` other than `payment-grant-linkage-auditability.md`
- `skills/*.md` new task skills other than `payment-grant-linkage-hardening.md`
- `wiki/agent-execution-system.md`
- `wiki/community.md`
- `wiki/postgres-scaling.md`
- `wiki/tasks-outputs.md`
- `wiki/workflow-orchestration.md`
- `wikilinks.md`

Recommendation: split into smaller batches by theme:
- execution/runtime knowledge,
- frontend/v0 QA skills,
- marketplace/community knowledge,
- persistence/Postgres knowledge.

### Group 5 — Raw historical notes archive
Risk: large volume/noise; may not belong in git.
Candidate folders:
- `raw/account-recovery/`
- `raw/community-drafts/`
- `raw/research/`
- `raw/roadmap-history/`
- other older raw planning/research directories.

Recommendation: do not commit until owner confirms these should be source-controlled. Consider `.gitignore` rules or Obsidian-only local storage for recurring personal/raw daily notes.

### Group 6 — Obsidian local UI state hold
Files:
- `.obsidian/graph.json`
- `.obsidian/workspace.json`

Recommendation: hold out of commit unless the owner explicitly wants workspace/graph UI settings shared in the repo. These are editor-state changes, not project state.

## Recommended implementation path
1. Create a clean worktree from `origin/main`.
2. Port Group 1 files manually/currently from dirty tree, resolving against remote canonical docs.
3. Run docs-scoped checks and secret scan.
4. Commit Group 1 locally only.
5. Repeat for Group 2 and Group 3.
6. Leave Groups 4–6 uncommitted until separately approved.
7. If push is approved later, run standing post-deploy QA after Railway/Vercel deploys or report PARTIAL if blocked.

## Current safety check status
Earlier same-session checks passed:
- `git diff --check`: PASS
- Targeted high-confidence secret scan over 85 changed/untracked text files: PASS
- Updated wiki schema quick checks: PASS

Repeat scoped checks inside the clean worktree before any commit because the final ported diffs may differ from this dirty local tree.
