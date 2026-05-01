# Held Scheduler Job Audit Plan

Related: [[Scheduler]], [[Cronjobs]], [[Execution Ledger]], [[Ops Runbook]]

## Status
Planning only. No jobs were enabled, disabled, modified, or run. `/jobs/run-due` was not called.

## Global prerequisites before enabling any held job
- Production `/health` and `/openapi.json` pass.
- Scheduler ledger and execution ledger state is clean by aggregate-only read-only audit.
- Job handler has tests and safe-mode behavior.
- Output is sanitized and does not print secrets, tokens, cookies, DB/RPC URLs, raw payloads, raw metadata, request/response bodies, or private wallet data.
- Owner approves one job class at a time.

## Per-job plan

### payment_route_audit
- Why held: touches payment route behavior and can create noisy/security-sensitive findings.
- Prerequisites: read-only route probes only; no create/verify with real or fake tx; no access mutation.
- Audit plan: inspect OpenAPI, auth-gate status, security headers, route schemas.
- Canary: enable only after dry-run report passes; first run read-only once.
- Risk: High.
- Approval prompt: `I approve a read-only payment_route_audit scheduler canary. Do not create payment intents, call verify, send payments, or mutate access.`

### failed_payment_replay_review
- Why held: payment replay review can expose sensitive payloads or accidentally probe real tx paths.
- Prerequisites: aggregate-only duplicate/replay data source; sanitized outputs.
- Audit plan: count failed/replay statuses only; no raw payloads.
- Canary: one read-only run, inspect summary.
- Risk: High.
- Approval prompt: `I approve a read-only failed_payment_replay_review scheduler canary with aggregate-only output and no verify calls or DB writes.`

### access_grant_integrity_check
- Why held: access control integrity is security-critical.
- Prerequisites: duplicate indexes/preflight clean, aggregate queries only, no grant create/revoke.
- Audit plan: count orphan/duplicate grants and inactive/expired anomalies.
- Canary: one read-only run.
- Risk: High.
- Approval prompt: `I approve a read-only access_grant_integrity_check scheduler canary. Do not create, revoke, or repair grants.`

### telegram_status_summary
- Why held: external messaging can spam or leak internal status.
- Prerequisites: delivery target verified, redaction, rate limits, no secrets.
- Audit plan: dry-run text to file first.
- Canary: one short sanitized Telegram message.
- Risk: Medium.
- Approval prompt: `I approve one sanitized telegram_status_summary canary message. Do not include secrets or raw logs.`

### task_queue_worker
- Why held: worker may execute mutable queued tasks.
- Prerequisites: queue schema audit, safe-mode denylist, per-task approval gates.
- Audit plan: read-only queue inventory and dry-run classification.
- Canary: no-op/dry-run only before any real task execution.
- Risk: High.
- Approval prompt: `I approve a dry-run task_queue_worker audit only. Do not execute queued tasks or mutate state.`

### git_status_summary
- Why held: may expose local paths/diffs/noisy repo state.
- Prerequisites: redact sensitive filenames/content, handle safe.directory issue.
- Audit plan: branch/ahead/dirty counts only.
- Canary: one read-only run.
- Risk: Low/Medium.
- Approval prompt: `I approve a read-only git_status_summary canary with sanitized output and no commits/pushes.`

### roadmap_review
- Why held: could rewrite roadmap or create strategy churn.
- Prerequisites: report-only mode, no auto-edits unless separately approved.
- Audit plan: summarize backlog and stale items.
- Canary: one report-only run.
- Risk: Medium.
- Approval prompt: `I approve one report-only roadmap_review canary. Do not edit files unless I separately approve a docs patch.`

## Recommended order
1. git_status_summary
2. roadmap_review
3. telegram_status_summary
4. access_grant_integrity_check
5. failed_payment_replay_review
6. payment_route_audit
7. task_queue_worker
