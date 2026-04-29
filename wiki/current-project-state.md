# Current Project State

## Summary
AgentAscend is currently in a production-verification and consolidation phase. Execution Ledger and Scheduler Execution Ledger are production-enabled for the approved safe scheduler workload. Pump.fun/tokenized-agent marketplace payment flow has live evidence across purchase, ownership unlock, creator accounting, and creator claim payout. Held scheduler jobs and deeper payment/access architecture cleanup remain intentionally scoped for separate audits.

## Components
- Backend: FastAPI on Railway at `https://api.agentascend.ai`.
- Frontend: v0/Next.js on Vercel at `https://www.agentascend.ai`.
- Database: Railway Postgres for production persistence.
- Scheduler: Separate Railway `AgentAscend-Scheduler` worker.
- Execution Ledger: Backend execution tables and read APIs.
- Payment flow: Pump.fun SDK-aligned tokenized-agent payment routes and v0 wallet modal.
- Knowledge system: `MEMORY.md`, `raw/`, `wiki/`, `docs/`, `learning/`, `skills/`.

## Relationships
- [[Payment System]]
- [[Tokenized Agents]]
- [[Scheduler]]
- [[Agent Payment SDK]]
- [[Payment Verification]]
- [[Token Gated Access]]
- [[Frontend v0 Workflow]]
- [[Deployment]]
- [[Roadmap]]

## Current production state
- Backend `/health`: PASS, HTTP 200 with `{"status":"ok"}`.
- Backend `/openapi.json`: PASS, parses successfully.
- Pump.fun routes present:
  - `POST /payments/pumpfun/create`
  - `POST /payments/pumpfun/verify`
- Execution routes present:
  - `GET /executions/me`
  - `GET /executions/summary`
  - `GET /executions/{execution_id}`
  - `GET /tasks/{task_id}/execution`
- API security headers present on live backend: `nosniff`, `DENY`, `no-referrer`, restricted permissions policy, and API CSP.
- Frontend app routes load with HTTP 200:
  - `/`
  - `/app/overview`
  - `/app/marketplace`
  - `/app/executions`
- Live frontend CSP allows both SolanaTracker browser RPC origins:
  - `https://rpc.solanatracker.io`
  - `wss://rpc.solanatracker.io`
- Live frontend bundles for overview/marketplace include Pump.fun modal and endpoints, and do not contain the old active manual payment markers.

## Pump.fun/tokenized-agent state
- SDK model: use `@pump-fun/agent-payments-sdk` with `PumpAgent`, `buildAcceptPaymentInstructions`, and `validateInvoicePayment`.
- Agent token mint: `9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump`.
- Currency: SOL / wrapped SOL.
- Currency mint: `So11111111111111111111111111111111111111112`.
- Amount: `0.1 SOL` = `100000000` lamports/smallest unit.
- Pump.fun Agent Deposit/payment address: `G3yF27myX5WdtAihoKEWtuSPxMBQYqxCMSsJaSEcBx2S`.
- Creator/payment authority wallet: `DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D`.
- Buyback rate reported by owner: 50%.
- Buyback/burn is handled by Pump.fun, not AgentAscend code.
- Owner-reported live canary evidence: marketplace purchase completed, buyer owned/unlocked the bought agent, creator dashboard showed claimable funds and buyback accounting, and the creator claim payout was received.

## Scheduler/ledger state
Accurate release wording: Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved safe scheduler workload. Held scheduler jobs remain intentionally disabled and require separate scoped audits before enablement.

Approved safe scheduler jobs enabled in production:
- Backend health check
- Frontend/backend integration drift check
- Wiki/Obsidian consistency check
- TODO/FIXME scan

Held jobs disabled in production:
- Payment route audit
- Failed payment/replay protection review
- Access grant integrity check
- Telegram status summary
- Task queue worker
- Git status/change summary
- AgentAscend roadmap review

Read-only DB audit on 2026-04-29 found:
- 11 scheduler jobs total, 4 enabled.
- 0 due-now enabled jobs at audit time.
- Scheduler execution ledger rows exist for scheduled job runs.
- Scheduler execution artifacts count is 0.
- Scheduler artifacts with `content_text` count is 0.
- No orphan execution events/artifacts found.

## Started but not fully finished
- Archive owner-side payment canary evidence into a durable report with public tx signatures and screenshots or sanitized network evidence if desired.
- Continue payment/access atomicity and durable entitlement persistence review.
- Confirm or clean any remaining legacy payment modal code that is now inactive.
- Audit held scheduler jobs one-by-one before enabling any of them.
- Classify and isolate the dirty working tree before commit.
- Continue multi-agent architecture planning after payment/access core is stable.

## Safety notes
- Do not run real payments, wallet signing, claim revenue, mutate production DB rows, change Railway/Vercel variables, or enable/disable scheduler jobs during documentation/audit phases.
- Do not treat the Pump.fun payment address alone as invoice proof. Access must be granted only after backend-owned payment intent/invoice verification using exact SDK invoice parameters and `validateInvoicePayment`.
- Do not implement AgentAscend buyback/burn bots; Pump.fun handles tokenized-agent buyback/burn mechanics.

## Notes
This page was updated during the 2026-04-29 overnight audit/consolidation pass. Production claims here are based on read-only live checks plus owner-reported successful purchase/claim evidence from the same session.