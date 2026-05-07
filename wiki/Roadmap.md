---
type: wiki
project: AgentAscend
aliases:
  - Roadmap
---

# Roadmap

## Summary
AgentAscend's near-term roadmap has moved from backend hardening into frontend/product polish against live backend truth. Payment/access proof, Forge backend foundations, runtime worker, and the core runtime loop are live.

## Immediate priorities
1. Frontend polish for the verified runtime loop:
   - Overview/Command Center clarity.
   - Agent run feedback and next-step guidance.
   - Task detail UX.
   - Execution detail UX.
   - Output search/export/share/delete honest UX.
   - Deployment events/timeline UX.
2. Workflow builder UX:
   - Honest partial-live state.
   - Visual graph builder as a future/backend slice.
   - Workflow run/history details where live contracts exist.
3. Settings/community/token polish without fake authority.
4. Add backend slices one at a time only when frontend polish proves a real missing endpoint.

## Hardening watch items
- Monitor Pump.fun/Solana transitive dependency advisories; do not blindly run audit fixes.
- Keep replay-index DDL on hold unless schema drift appears; current preflight says DDL not needed.
- Keep held scheduler jobs disabled unless owner approves enablement under documented conditions.
- Convert/pause/remove legacy Telegram Hermes cronjobs only with owner approval.
- Keep payment/security/tokenomics/public launch decisions under owner/Premium Strategic review.

## Later phases
- Full visual workflow graph builder.
- Richer deployment scale/rollback/log streaming.
- Marketplace creator product polish and clearer install/use lifecycle.
- Token/community UX grounded in actual platform usage.
- Multi-agent role setup after frontend/backend product contracts stabilize.

## Relationships
- [[current-project-state|Current Project State]]
- [[Launch Readiness]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Agent Architecture]]
- [[Payment Access Control]]
- [[Cronjobs]]
- [[scheduler|Scheduler]]
