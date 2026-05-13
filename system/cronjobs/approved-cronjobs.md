# Approved AgentAscend Cronjobs

This file records AgentAscend cronjobs explicitly approved by Reuben or activated from direct user instruction.

## Active Hermes cronjobs — reviewed 2026-05-12

Safety baseline for all active Hermes jobs:
- Report-first by default.
- Workdir: `/home/agentascend/projects/AgentAscend`.
- No production DB mutation, payment action, scheduler state change, deploy, commit, push, social post, email, or external account action unless explicitly approved in a later instruction.
- Redact secrets and private raw responses.

| Job | ID | Schedule | Delivery | Status at review | Purpose |
|---|---|---:|---|---|---|
| AgentAscend daily morning operator cycle | `4472b9af1cce` | `0 8 * * *` | Telegram DM (target redacted in docs) | OK | Morning project/health/git/status report |
| AgentAscend backend health monitor | `9600858f2a1d` | `0 */4 * * *` | Telegram DM (target redacted in docs) | OK | Safe live backend health/header checks |
| AgentAscend daily evening audit cycle | `3c6b73c24cf9` | `0 18 * * *` | Telegram DM (target redacted in docs) | OK | Payment/wiki/db/git evening audit reports |
| AgentAscend integration quality and test planning | `88c926f33ab3` | `30 10 */2 * *` | Telegram DM (target redacted in docs) | OK | Frontend/backend integration and tests planning |
| AgentAscend MVP readiness and local dev check | `0402b231934b` | `0 12 * * 2,5` | Telegram DM (target redacted in docs) | OK | Twice-weekly readiness/local checks |
| AgentAscend MEMORY.md maintenance | `7fede4bb3eb4` | `30 19 * * *` | Telegram DM (target redacted in docs) | OK | Report-only MEMORY accuracy review |
| AgentAscend Swarm Daily Operator Report | `77986833403e` | `0 */12 * * *` | local | OK | Local report-only operator synthesis |
| AgentAscend Swarm Daily Knowledge Hygiene Report | `0d6d5816aee6` | `30 9 * * *` | local | OK | Local report-only knowledge hygiene |
| AgentAscend Swarm Backend Frontend Contract Report | `df768cdc7c99` | `15 10 */2 * *` | local | OK | Local report-only contract drift review |
| AgentAscend Swarm Weekly Security Dependency Report | `afd8fa8cc7b9` | `0 9 * * 1` | local | OK | Local report-only security/dependency review |
| AgentAscend Weekly System Hygiene and Cronjob Audit | `5cf95fc08134` | `30 9 * * 0` | local | OK | Local weekly system/cronjob hygiene audit |

## Retired Hermes cronjobs — 2026-05-12

Recorded in [[raw/cronjob-retirement/2026-05-12-hermes-paused-job-cleanup]].

| Job | ID | Prior state | Reason |
|---|---|---|---|
| AgentAscend documentation gap scan | `3e2c67fffbfe` | paused/error | Superseded by knowledge hygiene + weekly system hygiene jobs |
| AgentAscend weekly strategy security and ecosystem scan | `af4423ba979c` | paused/error | Overbroad; strategy remains manual/Premium Strategic gated; security covered by weekly security report |
| AgentAscend weekly roadmap reprioritizer | `c778a3e0a264` | paused/error | Roadmap changes should stay manual/report-first after evidence review |

## AgentAscend DB scheduler jobs — observed 2026-05-12

Enabled/audited local scheduler jobs:
- `default-backend-health-check`
- `default-integration-drift-check`
- `default-wiki-consistency-check`
- `default-todo-fixme-scan`
- `default-payment-route-audit`
- `default-failed-payment-replay-review`
- `default-access-grant-integrity-check`
- `default-task-queue-worker`
- `default-telegram-status-summary`
- `default-git-status-summary`

Disabled/manual by design:
- `default-roadmap-review` — Premium Strategic/manual review gated.

## Historical entry — 2026-04-25 MEMORY.md Maintenance

- Job name: AgentAscend MEMORY.md maintenance
- Job ID: `7fede4bb3eb4`
- Schedule: `30 19 * * *` daily at 7:30 PM
- Delivery: Telegram DM (target redacted in docs)
- Workdir: `/home/agentascend/projects/AgentAscend`
- Output path: `raw/memory-maintenance/YYYY-MM-DD.md`
- Risk level: Low to Medium
- Allowed actions: read files, inspect git status/diffs, create one markdown report, propose MEMORY.md patch in report
- Forbidden actions: edit MEMORY.md automatically from the cronjob, expose secrets, add raw logs, add temporary debugging noise, modify payment/wallet/access/database/deployment code, commit, push, deploy, post externally, send emails, or send appeals
- Escalation condition: payment verification, wallets, access control, replay protection, ASND utility, database integrity, public launch, security, user funds, public claims, or conflicting autonomy rules
- Source proposal: `raw/cronjob-proposals/2026-04-25-0002.md`
