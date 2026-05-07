# AgentAscend Automation Governance

Status: active governance document.
Scope: scheduler jobs, Hermes cronjobs, subagents, report loops, and external notifications.

## Default posture

Automation is report-only by default. It may collect public or aggregate data, write docs/reports, and recommend action. It must not mutate production systems or communicate externally unless explicitly approved.

## Approval matrix

| Action | Default | Required approval |
| --- | --- | --- |
| Health/OpenAPI checks | allowed | none |
| Railway deployment status | allowed | none |
| Sanitized logs | allowed | none |
| Docs/wiki/skills edits | allowed when scoped | commit/push gate |
| Backend/frontend code edits | scoped only | implementation approval |
| Push | held | explicit push approval |
| Deploy | held | explicit deploy approval |
| DB migration/DDL | forbidden | explicit migration approval |
| Production DB write | forbidden | explicit owner approval |
| Scheduler enable/disable/run | forbidden | explicit scheduler approval |
| Telegram send/external message | forbidden | explicit message approval |
| Payment intent/create/verify | forbidden | explicit payment approval |
| access_grants/entitlements mutation | forbidden | explicit access approval |
| Public posts/community replies | forbidden | explicit post approval |

## Report-only automation cadence

### Daily
- API health and OpenAPI validity.
- Railway web/scheduler deployment status.
- Scheduler job summaries and failure counts, aggregate only.
- Wiki/orphan note scan.
- Git dirty summary.
- Payment/access aggregate counts, no raw rows.

### Weekly
- Dependency audit.
- Frontend/backend contract drift.
- Marketplace/payment smoke plan, no real payment.
- Obsidian graph maintenance.

### Manual approval only
- Deploys.
- Migrations.
- Payment canaries.
- Scheduler enablement or manual job runs.
- Telegram sends.
- Public posts.
- Access/entitlement cleanup.

## Stop conditions

Any automation must stop and report if it encounters:
- secrets or raw sensitive data in output;
- unexpected dirty code files;
- failing tests in a release gate;
- production mutation requirement;
- payment/access/scheduler side effects;
- unclear ownership or ambiguous scope;
- nonzero queued production tasks when task worker behavior is changing.

## Evidence handling

- Raw evidence goes under `raw/`.
- Structured stable knowledge goes under `wiki/`.
- Reusable checklists go under `skills/`.
- System policies and approved cronjob records go under `system/`.
- Do not delete raw evidence during cleanup.
- Do not stage `.obsidian` workspace or graph files unless explicitly requested.

## Standing post-deploy QA gate

After every deploy, Hermes must run post-deploy QA before final PASS. The type of QA depends on deploy type. If QA is blocked, report PARTIAL, never PASS. Use `docs/post-deploy-qa-protocol.md` as the standing runbook.

Minimum universal checks include deployment status, `/health`, `/openapi.json`, security headers, critical OpenAPI route presence, auth gates, and sanitized logs. Frontend deploys additionally require live route/header checks, Playwright route/render smoke when available, live bundle marker checks, payment/wallet regression checks, admin/scheduler exposure checks, and localStorage authority checks. Backend/runtime deploys additionally require task-runtime aggregate checks when relevant. Docs-only deploys still require universal post-deploy checks because they can trigger Railway deploys.
