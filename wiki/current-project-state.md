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
Accurate release wording: Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved scheduler workload. The final scheduler posture is report-first: approved low-risk jobs are enabled, while remaining held jobs stay disabled unless separately approved for enablement.

Enabled and audited scheduler jobs in production:
- `default-backend-health-check`
- `default-integration-drift-check`
- `default-wiki-consistency-check`
- `default-todo-fixme-scan`
- `default-payment-route-audit`
- `default-failed-payment-replay-review`
- `default-access-grant-integrity-check`
- `default-task-queue-worker`

Still disabled / held jobs in production:
- `default-telegram-status-summary`
- `default-git-status-summary`
- `default-roadmap-review`

Held-job posture, 2026-05-02:
- `default-telegram-status-summary` is patched and deployed as report-only by default at commit `31642a0ed52d8172759561eb5fe2788fe16745dc`. Its no-send canary passed with `mode=report_only`, `external_message_sent=false`, `send_enabled=false`, no `agent_findings` delta, and no payment/access/marketplace deltas. Outbound Telegram sends require `AGENT_RUNTIME_TELEGRAM_STATUS_SEND_ENABLED=true` and separate owner approval.
- `default-roadmap-review` passed a scoped canary as a placeholder/report-first job. It does not call a model or mutate files and is safe to enable later if owner-approved.
- `default-git-status-summary` is patched to fail closed safely when git is unavailable. Production currently lacks git, so keep it disabled unless the owner accepts sanitized failed/unavailable reports.

Task worker enablement note, 2026-05-02:
- Owner-approved canary for `default-task-queue-worker` processed 0 tasks.
- Task worker scheduler metadata is aggregate-only: `processed`, `completed`, `failed`, and `output_count`.
- `output_ids` is removed from job metadata.
- No payment/access/marketplace mutation occurred during enablement; protected aggregates stayed unchanged.
- `AGENT_RUNTIME_TASK_WORKER_BACKGROUND_ENABLED` controls `create_task` background triggering separately from scheduled job enabled state.
- Scheduled enablement of `default-task-queue-worker` can process real queued production tasks in future natural scheduler runs.

Read-only DB audit on 2026-04-29 found:
- 11 scheduler jobs total, 4 enabled at that time before later audited enablements.
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
This page was updated after the 2026-05-02 task worker scheduler enablement canary. Production claims here are based on read-only live checks, scoped canaries, and owner-reported successful purchase/claim evidence where noted.