# Multi-Agent Architecture Plan

Related: [[Agent Architecture]], [[Hermes]], [[AgentAscend]], [[Ops Runbook]]

## Status
Planning only. No agents were created.

## Agent roles

### Payment/Access Agent
- Responsibilities: Pump.fun/SOL/ASND payment contracts, access grants, replay protection, admin evidence lookups.
- Allowed: backend payment/access docs, tests, route/service files only after approval.
- Forbidden: real payments, wallet signing, env vars, DB migrations, manual grants without explicit approval.
- Gates: Premium Strategic review for payment/security changes; full tests; live read-only auth gates.
- Owned checks: payment route tests, replay tests, aggregate duplicate checks.
- Handoff artifacts: audit report, migration prompt, regression evidence checklist.
- Risks: user funds, auth bypass, replay acceptance.
- First task: replay-index migration readiness review.

### Frontend/v0 Agent
- Responsibilities: v0 prompts, frontend contract parity, wallet UX, marketplace install flow.
- Allowed: v0 patch prompts, bundle audits, frontend docs.
- Forbidden: backend source-of-truth changes, production env changes, private wallet data.
- Gates: compile/parity PASS, live bundle marker audit.
- Owned checks: route/bundle markers, payment modal UX, ownership refresh.
- Handoff artifacts: copy-paste v0 prompt and verification checklist.
- Risks: frontend-only unlocks, stale deployments.
- First task: payment/access UI refresh after verify checklist.

### Ledger/Scheduler Agent
- Responsibilities: Execution Ledger, Scheduler Ledger, job safety, held-job audits.
- Allowed: scheduler docs/tests and read-only reports after approval.
- Forbidden: enabling jobs, `/jobs/run-due`, production scheduler flags without approval.
- Gates: one-job-at-a-time canary and owner prompt.
- Owned checks: job matrix, run history aggregates, artifact integrity.
- Handoff artifacts: per-job audit report.
- Risks: accidental mutations, notification spam.
- First task: git_status_summary read-only canary package.

### QA/Security Agent
- Responsibilities: release gates, secret scans, contract drift, dependency audits.
- Allowed: tests, docs, read-only scans.
- Forbidden: auto-fix dependency updates without approval, secret printing.
- Gates: independent review before commit/push.
- Owned checks: security headers, npm audit summary, diff secret scan.
- Handoff artifacts: PASS/FAIL release report.
- Risks: false confidence, leaked sensitive output.
- First task: node helper dependency cleanup matrix.

### Docs/Memory Agent
- Responsibilities: Obsidian graph, raw/wiki hygiene, MEMORY.md proposals, skills.
- Allowed: docs/wiki/raw/skills/learning markdown.
- Forbidden: code, `.obsidian` workspace/graph, secrets.
- Gates: graph report, secret scan, docs-only diff.
- Owned checks: orphan counts, hub links, runbooks.
- Handoff artifacts: latest graph orphan report and changed-file list.
- Risks: fabricated links/claims, noisy commits.
- First task: weekly graph maintenance batch.

### Release/Ops Agent
- Responsibilities: push/deploy readiness, Railway/Vercel/Namecheap click-by-click guidance, live API checks.
- Allowed: read-only deployment status and docs.
- Forbidden: deploys/env changes/pushes without explicit approval.
- Gates: exact commit scope, health/OpenAPI, Railway success.
- Owned checks: branch/head/origin, security headers, route presence.
- Handoff artifacts: deployment monitor report.
- Risks: unintended production deploy.
- First task: docs-only push/deploy monitor template.

### Marketplace/Product Agent
- Responsibilities: creator marketplace product requirements, listing UX, community/research synthesis.
- Allowed: roadmap/product docs and v0 prompts.
- Forbidden: tokenomics/buyback claims or settings changes without Premium Strategic review.
- Gates: claims safety review, backend contract check.
- Owned checks: marketplace entitlement proof, public claim safety.
- Handoff artifacts: product backlog and public-safe launch notes.
- Risks: overclaiming ASND utility/revenue.
- First task: marketplace entitlement/history user story backlog.

## Recommended creation order
1. Docs/Memory Agent
2. QA/Security Agent
3. Release/Ops Agent
4. Payment/Access Agent
5. Ledger/Scheduler Agent
6. Frontend/v0 Agent
7. Marketplace/Product Agent

## Exact next prompt
`Create the AgentAscend Docs/Memory Agent in planning/report-only mode. It may edit only docs/wiki/raw/skills/learning markdown, must never touch code or .obsidian workspace files, must run graph orphan counts and secret scans, and must produce a docs-only commit proposal before any commit or push.`
