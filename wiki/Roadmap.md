# Roadmap

**Roadmap Date: 2026-04-26 (Weekly Reprioritization)**

## Summary
This roadmap reprioritizes AgentAscend toward one outcome: a trustworthy revenue loop (pay → verify → grant access → use tool) that works reliably on live infrastructure. Current evidence shows healthy API availability and improving execution-ledger/task pipeline maturity, but payment hardening, live auth/persistence proof, and frontend-contract validation remain the highest-risk gaps.

## Components
- Payment and access trust core: [[Payment System]], [[Payment Verification]], [[Token Gated Access]], [[Auth]], [[Solana Integration]], [[ASND Payment Integration]]
- Data durability and runtime: [[Database]], [[Scheduler]], [[Tasks Outputs]], [[agent-execution-system]]
- Product surfaces: [[Frontend v0 Workflow]], [[Marketplace]], [[Community]], [[Known Issues]], [[Deployment]]

## 1) Immediate priorities (next 24–72h)
1. **Close payment idempotency failure-path risk** and verify safe retry semantics end-to-end.
2. **Run authenticated live smoke matrix** for `/auth/me`, `/users/{id}/access`, `/users/{id}/payments`, `/tasks`, `/outputs` using throwaway users.
3. **Lock payment/tool auth binding in live behavior** (no caller-controlled user spoofing assumptions; backend ownership enforcement verified in deployed API behavior).

## 2) This week’s priorities
1. **Commit and ship clean backend hardening groups** (payments/tools/idempotency + tests) with reviewable scope.
2. **Prove Railway persistence durability**: create/read/signout-signin/restart/re-check matrix with evidence artifacts.
3. **Resolve frontend contract uncertainty** by validating latest v0 ZIP against current backend routes and known issue queue (outputs crash, task reload, workflow create wiring).
4. **Normalize payment status semantics** so UI/payment reporting cannot drift (`completed` vs `paid` mismatch removal).

## 3) This month’s priorities
1. **Productionize payment intent model** (`reference` + TTL + single-use + authenticated ownership binding).
2. **Complete execution ledger adoption** for task/workflow runs, events, artifacts, and user-facing execution history.
3. **Workflow runtime MVP** with honest run lifecycle/status/log/output behavior.
4. **Marketplace trust contract v1** (schema, verification state, permissions, telemetry, lifecycle) before aggressive creator monetization.

## 4) What to ignore for now
- Buyback/burn automation mechanics.
- Advanced staking mechanics and token-finance loops.
- Multi-chain expansion.
- Autonomous high-risk “agent economy” flows before core payment/access trust is proven.

## 5) Launch blockers
1. **Payment verification hardening not yet fully proven live** (especially failure-path idempotency and intent/auth binding guarantees).
2. **Auth + persistence reliability not proven through full live user matrix** (signout/signin + restart durability evidence still incomplete).
3. **Frontend integration verification gap** due to absent frontend workspace in this repo snapshot and unresolved known issues.
4. **Contract drift risk** between backend endpoints and frontend expectations until fresh bundle/source parity is confirmed.

## 6) Most likely revenue-first work
1. **Single reliable paid tool loop** (SOL first): create intent → verify tx → grant access → use tool → show access/payment history.
2. **Operational trust signals**: stable health, deterministic error handling, clear paid-state UX, no fake unlocks.
3. **Low-friction paid expansion**: add 1–2 adjacent paid tools only after baseline loop KPIs are stable.

## 7) ASND utility support
1. Keep **ASND as verified utility path**, not hype path: mirror SOL trust guarantees (receiver/mint/amount/finality/idempotency).
2. Add **clear ASND payment UX parity** after SOL loop reliability is proven.
3. Track usage metrics that can later justify deeper ASND utility (without price/return claims).

## 8) Unnecessary complexity
- Premature microservice split for payment/auth.
- Overbuilding orchestration abstractions before workflow runtime semantics are stable.
- Marketplace governance/payout complexity before listing trust and execution telemetry basics are complete.

## 9) Suggested milestone order
1. **Milestone 1 — Payment Trust Lock:** idempotency failure-path fix + auth/ownership enforcement + live smoke evidence.
2. **Milestone 2 — Persistence Proof:** Railway Postgres durability matrix passes with documented artifacts.
3. **Milestone 3 — Frontend Contract Parity:** outputs/task/workflow known issues resolved or honestly marked endpoint-needed.
4. **Milestone 4 — Revenue Loop Beta:** stable SOL-gated tool loop with observable metrics.
5. **Milestone 5 — ASND Utility Beta:** ASND path enabled with same safety guarantees as SOL.
6. **Milestone 6 — Marketplace Foundation:** creator listing/execution trust contract and monetization-safe lifecycle.

## Relationships
- [[Payment System]]
- [[Payment Verification]]
- [[Token Gated Access]]
- [[ASND Payment Integration]]
- [[ASND Token]]
- [[Auth]]
- [[Database]]
- [[Tasks Outputs]]
- [[Scheduler]]
- [[Frontend v0 Workflow]]
- [[Marketplace]]
- [[Community]]
- [[Known Issues]]
- [[Deployment]]

## Notes
- Reprioritized from current evidence in `raw/daily-status`, `raw/backend-health`, `raw/payment-audits`, `raw/frontend-integration`, and recent git history through 2026-04-26.
- This roadmap is execution guidance, not approval to deploy risky changes without review.

## 2026-04-30 Knowledge Graph Status Update
- Raw launch evidence, tokenized-agent, scheduler/cronjob, deploy-readiness, security, and Hermes runtime notes now link back to this hub graph.
- Exact Pump.fun `tx_signature` binding hardening is implemented and deployed at commit `453df65aec69f7aa95b20bb1752f7d3af97ad488`.
- Replay-index migration remains pending and must not be run without owner approval.
- Node dependency audit remains pending as a separate hardening phase.
