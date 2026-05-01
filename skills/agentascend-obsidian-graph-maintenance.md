# AgentAscend Obsidian Graph Maintenance

## Purpose
Keep AgentAscend Obsidian graph connected by linking raw evidence to wiki hubs while preserving raw evidence exactly.

## When to use
Use after major Hermes work sessions, after batches of generated raw notes, before release audits, and any time the Obsidian graph shows many floating isolated dots.

## Raw-to-hub mapping
- Pump.fun/payment notes -> [[Pump.fun Tokenized Agent Payments]], [[Payment Access Control]], [[Marketplace]], [[Launch Readiness]], [[AgentAscend]]
- Launch evidence notes -> [[Launch Readiness]], [[Pump.fun Tokenized Agent Payments]], [[Payment Access Control]], [[Marketplace]]
- Execution Ledger notes -> [[Execution Ledger]], [[Scheduler]], [[AgentAscend]], [[Ops Runbook]]
- Scheduler/cronjob notes -> [[Scheduler]], [[Cronjobs]], [[Execution Ledger]], [[Ops Runbook]]
- Frontend/v0 notes -> [[Frontend v0 Workflow]], [[Marketplace]], [[Pump.fun Tokenized Agent Payments]], [[Launch Readiness]]
- Hermes/tooling notes -> [[Hermes]], [[Agent Architecture]], [[Ops Runbook]], [[AgentAscend]]
- Security/payment hardening notes -> [[Payment Access Control]], [[Known Issues]], [[Launch Readiness]], [[Ops Runbook]]
- Roadmap/planning notes -> [[Roadmap]], [[Agent Architecture]], [[AgentAscend]]
- Backend health/deploy notes -> [[Ops Runbook]], [[Launch Readiness]], [[AgentAscend]]
- Git status notes -> [[Ops Runbook]], [[Hermes]], [[AgentAscend]]
- Community drafts -> [[Community]], [[Roadmap]], [[AgentAscend]]
- Research/trend notes -> [[Roadmap]], [[Community]], [[Marketplace]], [[AgentAscend]]

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

## Standard visible line
`Related: [[AgentAscend]], [[Launch Readiness]]`

## Rules
- Preserve raw evidence.
- Never delete public tx signatures.
- Never fabricate facts.
- Never add claims not supported by the note.
- Never add secrets.
- Never commit `.obsidian` graph/workspace files.
- Never touch code.
- Keep raw notes short-linked, not rewritten.
- Summarize concepts in wiki hubs instead of copying raw notes.

## Procedure
1. Scan `raw/`, `wiki/`, `docs/`, `skills/`, `learning/`, `MEMORY.md`, and `AGENTS.md`.
2. Count markdown files with zero outgoing wikilinks, no frontmatter, and no visible `Related:` line.
3. Group orphan notes by folder and topic.
4. Link up to 50 high-value raw evidence notes per batch by adding only frontmatter and a visible `Related:` line.
5. Update concise `Recent Evidence` bullets on relevant wiki hubs.
6. Write `raw/wiki-maintenance/latest-graph-orphan-report.md` with starting/ending counts, top orphan folders, duplicate candidates, touched files, and skipped files.
7. Run a secret/safety scan and `git diff --check` before committing.

## Verification
- Outgoing-zero count decreases or is explained.
- Touched raw notes have at least one wikilink.
- Hub pages link back to touched evidence clusters.
- No code, `.obsidian`, secrets, DB URLs, RPC URLs, tokens, cookies, private keys, seed phrases, raw request/response bodies, raw DB rows, raw metadata, `txBase64`, or signed transactions are staged.
