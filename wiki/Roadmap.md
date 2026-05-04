---
type: wiki
project: AgentAscend
aliases:
  - Roadmap
---

# Roadmap

## Summary
AgentAscend's near-term roadmap should move from backend-hardening phases into frontend/product integration against live backend truth. Payment/access proof and Forge backend foundations are live; the bottleneck is now making the logged-in product feel real, honest, and useful.

## Immediate priorities
1. Frontend/v0 implementation against live backend routes:
   - Forge agent create/read/config.
   - capability registry/templates.
   - run/deploy/workflow bridge actions with honest queued/running copy.
   - Command Center aggregate.
   - deployment events timeline.
2. Remove fake/localStorage authority from logged-in app pages.
3. Patch placeholder-heavy pages: overview, agents, deployments, workflows, tasks, outputs, executions, token, community, settings.
4. Add backend slices one at a time only when a frontend contract requires them.

## Hardening watch items
- Monitor Pump.fun/Solana transitive dependency advisories; do not blindly run audit fixes.
- Keep replay-index DDL on hold unless schema drift appears; current preflight says DDL not needed.
- Keep held scheduler jobs disabled unless owner approves enablement under documented conditions.
- Keep payment/security/tokenomics/public launch decisions under owner/Premium Strategic review.

## Later phases
- Multi-agent role setup after frontend/backend product contracts stabilize.
- Marketplace creator product polish and clearer install/use lifecycle.
- ASND utility expansion grounded in actual platform usage.

## Recent Evidence
- [[raw/launch-evidence/2026-05-03-pumpfun-controlled-payment-regression-pass|2026-05-03 controlled Pump.fun payment regression PASS]]
- [[raw/security-reviews/2026-05-02-replay-index-preflight|2026-05-02 replay-index preflight PASS / DDL not needed]]
- [[raw/scheduler-runtime-audits/2026-05-02-final-scheduler-posture|2026-05-02 final scheduler posture]]
- [[raw/security-reviews/2026-05-02-node-helper-dependency-audit|2026-05-02 Node helper dependency audit baseline]]
- Commits: `239fa79` dev dependency cleanup, `a8ad3ba` Pump.fun SDK 3.0.3, `2d00a31` controlled regression evidence, `5ac6d06` Forge definitions, `34a8c21` Command Center, `{prod_short}` deployment events.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Agent Architecture]]
- [[Payment Access Control]]
- [[scheduler|Scheduler]]
