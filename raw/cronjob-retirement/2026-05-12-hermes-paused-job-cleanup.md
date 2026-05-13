---
type: raw
project: AgentAscend
date: 2026-05-12
---

# Hermes Cronjob Retirement — 2026-05-12 Paused Job Cleanup

## Decision
Retire/remove three disabled Hermes cronjobs that were paused after errors and are now superseded by safer enabled report-only jobs.

## Jobs to retire
1. `3e2c67fffbfe` — AgentAscend documentation gap scan
   - State before action: paused/disabled, last status error.
   - Reason: covered by `AgentAscend Swarm Daily Knowledge Hygiene Report` and `AgentAscend Weekly System Hygiene and Cronjob Audit`.

2. `af4423ba979c` — AgentAscend weekly strategy security and ecosystem scan
   - State before action: paused/disabled, last status error.
   - Reason: broad scope overlaps with weekly security/dependency report; strategy decisions remain owner/Premium Strategic review gated.

3. `c778a3e0a264` — AgentAscend weekly roadmap reprioritizer
   - State before action: paused/disabled, last status error.
   - Reason: auto-reprioritization of roadmap is risky; roadmap updates should remain manual/report-first after evidence review.

## Safety
- No active healthy cronjobs were removed.
- No Telegram canary was sent.
- No production scheduler/DB/payment state was touched.
- Remaining enabled Hermes jobs are report-first and either Telegram-delivered status/audit cycles or local-only swarm reports.

## Expected result
Hermes cronjob list should drop from 14 to 11 jobs. Active coverage remains:
- morning operator cycle
- backend health monitor
- evening audit cycle
- integration/test planning
- MVP/local readiness
- MEMORY maintenance
- swarm daily operator report
- swarm daily knowledge hygiene
- swarm backend/frontend contract report
- swarm weekly security/dependency report
- weekly system hygiene/cronjob audit
