# AgentAscend Obsidian Graph Maintenance

## Purpose
Keep the AgentAscend Obsidian graph connected without deleting or rewriting raw evidence.

## When to use
Use after major Hermes sessions, after batches of raw notes, before release audits, and whenever the graph has floating raw/archive clusters.

## Rules
- Preserve raw evidence; do not delete notes.
- Add frontmatter and `Related:` links instead of rewriting raw reports.
- Mark stale notes as `Status: Superseded by [[...]]` when appropriate.
- Do not fabricate facts or upgrade owner-reported observations into Hermes-verified evidence.
- Never add secrets.

## Raw-to-hub mapping
- Pump.fun/payment notes -> [[Pump.fun Tokenized Agent Payments]], [[Payment Access Control]], [[marketplace|Marketplace]], [[Launch Readiness]], [[AgentAscend]]
- Launch evidence -> [[Launch Readiness]], [[Pump.fun Tokenized Agent Payments]], [[Payment Access Control]], [[marketplace|Marketplace]]
- Scheduler/cronjob -> [[scheduler|Scheduler]], [[Cronjobs]], [[Execution Ledger]], [[Ops Runbook]]
- Execution Ledger -> [[Execution Ledger]], [[scheduler|Scheduler]], [[AgentAscend]], [[Ops Runbook]]
- Frontend/v0 -> [[frontend-v0-workflow|Frontend v0 Workflow]], [[marketplace|Marketplace]], [[Launch Readiness]]
- Hermes/tooling -> [[Hermes]], [[Agent Architecture]], [[Ops Runbook]], [[AgentAscend]]
- Security/payment hardening -> [[Payment Access Control]], [[known-issues|Known Issues]], [[Launch Readiness]], [[Ops Runbook]]
- Roadmap/planning -> [[Roadmap]], [[Agent Architecture]], [[AgentAscend]]

## Standard frontmatter
```yaml
---
type: evidence
project: AgentAscend
date: YYYY-MM-DD
status: archived
tags:
  - agentascend
related:
  - "[[AgentAscend]]"
---
```

## Graph scan
Count outgoing `[[wikilinks]]` per markdown file. Prioritize high-signal orphans in `raw/launch-evidence`, `raw/security-reviews`, `raw/scheduler-runtime-audits`, `raw/deploy-readiness`, `raw/post-deploy-audits`, `raw/wiki-maintenance`, `raw/tokenized-agent-flow`, and `skills/`.
