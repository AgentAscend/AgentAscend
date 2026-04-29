# AgentAscend MEMORY.md


## 1. Purpose

AgentAscend is an AI x Web3 ecosystem and command center for intelligent agents.

The long-term vision is to let users deploy, use, and eventually monetize AI agents that can operate across crypto, automation, social platforms, Telegram/Discord, dashboards, and payment-gated tools.

AgentAscend is not just a chatbot website. It is intended to become an infrastructure layer for:

- AI agents
- Agent tools
- Payment-gated access
- Tokenized agents
- Telegram/Discord bots
- ASND/SOL utility
- Automated workflows
- Future agent marketplace features

---

## 2. Current Project Direction

### Current production snapshot — 2026-04-29

- Execution Ledger/Scheduler Ledger is production-enabled and audited for the approved safe scheduler workload. Held scheduler jobs remain intentionally disabled and require separate scoped audits before enablement.
- Approved safe scheduler jobs enabled in production: backend health check, integration drift check, wiki consistency check, and TODO/FIXME scan.
- Held scheduler jobs disabled in production: payment route audit, failed payment/replay review, access grant integrity check, Telegram status summary, task queue worker, git status summary, and roadmap review.
- Pump.fun/tokenized-agent payment routes are live and auth-gated: `POST /payments/pumpfun/create` and `POST /payments/pumpfun/verify`.
- Live v0 frontend paid routes use the Pump.fun modal flow and production CSP allows SolanaTracker browser RPC over both `https://rpc.solanatracker.io` and `wss://rpc.solanatracker.io`.
- Owner-reported canary: marketplace purchase completed, buyer ownership/unlock worked, creator dashboard accounting updated, and creator claim payout was received. Archive public transaction/sanitized evidence before using this as final launch proof.
- Pump.fun roles: Agent Deposit/payment address is `G3yF27myX5WdtAihoKEWtuSPxMBQYqxCMSsJaSEcBx2S`; creator/payment authority wallet is `DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D`; buyback/burn is handled by Pump.fun, not AgentAscend code.
- Critical rule: the Pump.fun payment address alone is not invoice proof; AgentAscend access must require backend-owned invoice/payment-intent verification with exact SDK params and `validateInvoicePayment`.

The current priority is to build a working MVP that proves the core access/payment loop.

The MVP should prove:

1. User connects wallet.
2. User initiates payment.
3. User pays in SOL first, with ASND support planned.
4. Backend verifies the payment.
5. Backend records the payment.
6. Backend grants access.
7. User can use a gated tool.
8. Payment/access state can be checked later.
9. System logs and reports the flow clearly.

The first gated tool can be simple. The purpose is not the tool itself. The purpose is proving that AgentAscend can gate AI/agent features behind verified blockchain payment.

---

## 3. Core Architecture (Current)

Current local architecture:

AgentAscend/
- AGENTS.md
- MEMORY.md
- backend/
- docs/
- raw/
- wiki/
- system/

Frontend note:
- `frontend/` is not present in this workspace snapshot; treat frontend integration as contract-based with the deployed v0 app until a repo path is added.

Backend:

backend/
- app/
  - main.py
  - routes/
    - health.py
    - payments.py
    - tools.py
    - users.py
  - services/
    - access_service.py
  - db/
    - session.py

Known backend stack:

- FastAPI
- Uvicorn
- SQLite for local development/test fixtures
- Railway Postgres direction for deployed persistence
- Python backend routes
- Backend source of truth for payments, access, marketplace data, community data, tasks, and outputs
- DB-backed scheduler tables for scheduled jobs, job runs, and findings

Known frontend direction:

- Next.js / v0 / Vercel direction
- Wallet connection flow
- Payment request flow
- Backend verification flow
- Gated tool unlock flow
- Auth/profile wiring
- Backend-first marketplace, community, tasks, and outputs pages

Local backend:

http://127.0.0.1:8000

Health endpoint:

GET /health

Expected health response:

{"status":"ok"}

---

## 4. Source of Truth Rules

The backend is the source of truth for:

- Payment status
- Verified transactions
- User access
- Feature unlocks
- Access grants
- Payment history
- Gated tool permissions

The frontend should never be the source of truth for access.

The frontend may display access state, but the backend decides whether a user has access.

Never unlock paid features from frontend-only state.

Never trust a client-provided “paid” flag.

Never grant access unless the backend verifies the payment or confirms an existing valid access grant.

---

## 5. Payment System

Current payment direction:

- SOL verification first
- ASND verification planned
- Pump.fun/tokenized-agent payment flow has been explored
- Backend verification must remain authoritative
- Access grants are created only after valid payment verification

Payment verification must check:

1. Valid transaction signature
2. Correct receiver wallet
3. Correct token type
4. Correct token mint when applicable
5. Correct amount
6. Correct user/payment intent when applicable
7. Confirmation/finality status
8. Duplicate transaction signature prevention
9. Replay protection
10. Existing access grant/idempotent behavior
11. No fake client-side unlocks

Payment records should include:

- User ID
- Amount
- Token
- Status
- Created timestamp
- Transaction signature when available

Access grant records should include:

- User ID
- Feature name
- Payment reference
- Status
- Created timestamp

Known local test example:

GET /users/real3/access
GET /users/real3/payments

Example result previously seen:

User access example:
{
  "user_id": "real3",
  "access_grants": [
    {
      "feature_name": "random_number",
      "status": "active",
      "payment_id": 1,
      "created_at": "2026-04-23 05:48:54"
    }
  ]
}

User payments example:
{
  "user_id": "real3",
  "payments": [
    {
      "id": 1,
      "amount": 0.1,
      "token": "SOL",
      "status": "completed",
      "created_at": "2026-04-23 05:48:54"
    }
  ]
}

These examples are useful for local development memory, but production logic must not rely on dummy data.

---

## 6. Payment Security Rules

Never replace real payment verification with dummy verification logic in production paths.

Never mark payments completed unless verification succeeds.

Never create access grants unless a payment is verified or a valid existing grant already exists.

Never allow the same transaction signature to create multiple access grants.

Never ignore receiver wallet mismatch.

Never ignore amount mismatch.

Never ignore token/mint mismatch.

Never expose private keys, seed phrases, API keys, wallet credentials, or RPC secrets.

Use environment variables for sensitive or deployment-specific values.

Known important environment variables:

- SOLANA_RPC_URL
- SOLANA_RECEIVER_WALLET

Potential future environment variables:

- ASND_TOKEN_MINT
- ASND_RECEIVER_WALLET
- PAYMENT_REQUIRED_CONFIRMATIONS
- FEATURE_RANDOM_NUMBER_PRICE_SOL
- FEATURE_RANDOM_NUMBER_PRICE_ASND

---

## 7. ASND Token Context

AgentAscend has an ASND token associated with the project.

Known token mint:

9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump

ASND should gain utility from actual platform usage, not empty hype.

Potential utility ideas:

- Access to paid tools
- Agent usage
- Agent creation
- Premium bot access
- Marketplace features
- Tokenized agent workflows
- Holding or staking requirements later
- Buyback/burn mechanics from real platform revenue

Important rule:

Do not make public claims that imply guaranteed price action, guaranteed returns, or guaranteed revenue.

Keep public claims focused on building, utility, access, and platform progress.

---

## 8. Revenue Flywheel Direction

The long-term revenue flywheel idea:

1. Users pay for tools, agents, or access.
2. Payment may be in SOL, ASND, or later fiat-to-crypto paths.
3. Backend verifies payment.
4. User receives access.
5. A portion of platform revenue may later support ASND buyback/burn or ecosystem mechanics.
6. AgentAscend becomes more useful as more tools/agents are added.

Simple MVP version:

User pays SOL → backend verifies → backend grants access → user uses gated tool

Later version:

User pays SOL/ASND → backend verifies → backend grants access → revenue logic records amount → optional buyback/burn or treasury logic handled separately

Do not overcomplicate the MVP with staking, buybacks, automatic burns, tokenized marketplace logic, and multi-agent flows until the core payment/access loop works.

---

## 9. Hermes Role

Hermes is the autonomous project operator for AgentAscend.

Hermes helps with:

- Reading project state
- Reviewing code
- Generating reports
- Maintaining project knowledge (`raw/`, `wiki/`, `system/`)
- Suggesting next steps
- Running cronjob-style checks
- Auditing payment/access logic
- Proposing safe improvements
- Helping build toward MVP

Hermes should act like a project foreman, not a random chatbot.

Hermes should:

1. Read before writing.
2. Prefer small, testable changes.
3. Preserve project structure.
4. Keep the backend as source of truth.
5. Avoid risky edits without approval.
6. Report findings clearly.
7. Update knowledge when architecture changes.
8. Escalate security/payment/token decisions.
9. Avoid deleting files unless explicitly approved.
10. Avoid overwriting important docs without preserving history.

---

## 10. Hermes Safety Rules

Hermes must not:

- Expose secrets
- Store private keys
- Store seed phrases
- Commit secrets
- Delete files without approval
- Rewrite payment logic casually
- Replace verification with dummy logic
- Grant access without verified payment
- Post publicly without approval
- Send appeals/messages without approval
- Make financial promises
- Make token price promises
- Modify production/deployment settings without approval
- Run destructive shell commands without explicit approval

Hermes may:

- Read files
- Summarize project state
- Create reports
- Propose changes
- Draft docs
- Draft community updates
- Suggest tests
- Create safe plans
- Recommend cronjobs
- Perform safe edits only when explicitly allowed

---

## 11. Split-Brain Architecture

AgentAscend should use a split-brain AI architecture.

The concept:

Cheap/routine models = scouts and checkers
Reasoning models = planners and debuggers
Premium models = architects and final reviewers
Hermes = coordinator/operator
Reuben = final approval for high-impact actions

Routine/cheap models should handle:

- Git summaries
- File scans
- TODO extraction
- Broken link checks
- Basic docs checks
- Basic endpoint health reports
- Log summaries
- Draft variations

Reasoning models should handle:

- Multi-file debugging
- Code review
- Test planning
- Frontend/backend mismatch analysis
- Cronjob proposal review
- Medium-risk architecture planning

Premium strategic models should handle:

- Payment verification architecture
- Replay protection decisions
- Wallet/payment rules
- Access-control decisions
- ASND utility design
- Buyback/burn logic
- Launch readiness
- Security reviews
- Public claims with reputation risk
- Major roadmap decisions

If a finding affects money, wallets, security, access control, ASND utility, public launch, or user trust, escalate it to premium review and Reuben approval.

---

## 12. Cronjob System Direction

Hermes should use cronjobs as scheduled operating loops.

Core cronjob categories:

- Daily project status
- Daily build command report
- Backend health check
- Payment system audit
- Git status and commit suggestion
- Frontend integration check
- LLM wiki cleanup
- Obsidian sync
- Hermes runtime audit
- Code quality review
- Test plan generation
- Security review
- Tool opportunity scan
- Marketplace planning
- Revenue flywheel review
- Community update drafts
- X account recovery tracker
- Competitor/trend scan
- Dependency update check
- Database integrity check
- Build roadmap reprioritizer
- MVP launch readiness check
- Telegram/Discord bot planning
- Tokenized agent flow review
- Local dev environment check
- Documentation gap scan
- MEMORY.md maintenance

Default autonomy level:

Level 0 — Recommend only

This means Hermes may propose cronjobs and improvements, but should not activate recurring jobs or edit scheduler configs unless Reuben explicitly enables it.

Persistent scheduler foundation:

- Scheduled jobs are stored in the backend SQLite database, not only in Hermes/chat memory.
- `scheduled_jobs` is the source of truth for job definitions, schedules, model tier, enabled state, and metadata.
- `job_runs` records every scheduler execution with status, summary, error details, model tier, and metadata.
- `agent_findings` stores report-first findings created by scheduler checks.
- The scheduler clock runs separately through `scripts/run_scheduler.py`.
- Operator CLI controls are available through `scripts/job_admin.py`.
- FastAPI `/jobs` API routes exist for job controls, but they must be protected with `AGENT_RUNTIME_ADMIN_TOKEN` outside explicit safe local development.
- In production/Railway, missing `AGENT_RUNTIME_ADMIN_TOKEN` must fail closed.
- Railway should run the scheduler as a separate worker process, not inside the web process: web = FastAPI, worker = `python3 scripts/run_scheduler.py`.
- Spawned jobs are disabled by default unless explicitly approved or a safe config enables them.
- High-risk and premium jobs require manual approval.
- Future Hermes execution remains report-first: jobs may create findings, summaries, and suggested jobs, but must not directly run destructive Hermes CLI actions.
- Scheduler Telegram summaries may send only when both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are configured as environment variables.
- Backend health checks use `AGENTASCEND_HEALTH_URL` when set; otherwise they fall back to the local/backend health URL.

---

## 13. Autonomous Task Spawning

Hermes may recommend new cronjobs or sub-agents when it finds repeated issues or repeated opportunities.

New cronjobs should only be proposed when the task is:

- Repeated
- Useful
- Measurable
- Safe to automate
- Connected to MVP, revenue, security, growth, documentation, or launch readiness
- Clear enough to define
- Has a stop condition

Every proposed cronjob should include:

1. Name
2. Reason
3. Trigger condition
4. Schedule
5. Model tier
6. Risk level
7. Inputs
8. Outputs
9. Exact prompt
10. Allowed actions
11. Forbidden actions
12. Escalation condition
13. Stop condition
14. Approval requirement

Cronjob proposals should be saved to:

raw/cronjob-proposals/YYYY-MM-DD-HHMM.md

Approved cronjobs should be copied to:

system/cronjobs/approved-cronjobs.md

Rejected cronjobs should be logged to:

raw/cronjob-proposals/rejected/YYYY-MM-DD-HHMM.md

---

## 14. Spawnable Agent Concepts

Potential specialized spawned agents:

### Payment Sentinel Agent

Purpose:

- Monitor payment verification
- Detect duplicate signatures
- Detect receiver wallet mismatch
- Detect suspicious access grants
- Watch for replay attempts

Escalate when:

- Duplicate transaction signatures appear
- Access grant exists without valid payment
- Payment completed without verification
- Receiver wallet mismatch appears

### Access Control Watcher

Purpose:

- Confirm backend remains source of truth
- Detect frontend-only unlock logic
- Detect paid tools accessible without backend verification

### Git Hygiene Agent

Purpose:

- Monitor uncommitted changes
- Detect secrets or generated junk
- Suggest commit groups

### Documentation Gardener Agent

Purpose:

- Find stale docs
- Find missing docs
- Find broken links
- Convert raw notes into structured docs

### Test Architect Agent

Purpose:

- Convert repeated bugs into test plans
- Recommend test skeletons
- Watch for missing payment/access tests

### Frontend Flow Inspector

Purpose:

- Inspect wallet connect → payment → verification → unlock user journey

### Community Signal Agent

Purpose:

- Draft community updates from real project progress
- Avoid hype-only claims

### Trend Scout Agent

Purpose:

- Track AI agents, crypto x AI, Solana, robotics, and tokenized agent narratives

### Revenue Flywheel Analyst

Purpose:

- Review platform revenue, ASND utility, and buyback/burn plans

### Launch Readiness Commander

Purpose:

- Determine MVP launch blockers and public demo readiness

---

## 15. Knowledge Structure Rules

The project knowledge base is organized as top-level `raw/`, `wiki/`, and `system/`.

Use raw/ for:

- Daily reports
- Audits
- Logs
- Scratch notes
- Findings
- Cronjob outputs
- Raw research
- Temporary reports

Use wiki/ for:

- Structured durable knowledge
- Architecture pages
- Payment system docs
- Tool system docs
- User system docs
- Roadmap
- Tokenized agent docs
- ASND utility docs

Use system/ for:

- Rules
- Schemas
- Hermes runtime instructions
- Cronjob definitions
- Operating procedures
- Agent permissions
- Project policies

Do not dump everything into wiki pages.

Raw findings should start in /raw.

Only distilled, durable knowledge should move to /wiki.

Rules and operating procedures should go in /system.

---

## 16. Obsidian Rules

Obsidian is used as human-readable project memory.

Use Obsidian for:

- High-level concepts
- Project vision
- Architecture explanations
- Founder-readable planning
- Strategy notes
- Connected idea maps
- Human navigation

Use project knowledge folders for:

- Agent-readable structured knowledge
- Reports
- Schemas
- Cronjob outputs
- System instructions
- Durable machine-readable docs

Obsidian and project knowledge folders should stay aligned, but they do not need to duplicate everything.

---

## 17. Current Build Priorities (High Signal)

Immediate priorities:

1. Keep authenticated ownership enforcement on gated tools and prevent regression.
2. Keep `/payments/verify` bound to create-side payment intent (`reference` + TTL + user binding).
3. Keep idempotency failure lifecycle safe (release in-progress keys on failed verify paths).
4. Normalize payment status semantics across modules (`completed` vs `paid`) and docs.
5. Add/maintain payment-to-access auditability (`payment_id` linkage for grants where applicable).
6. Keep backend as source of truth for access control.
7. Confirm users/access endpoints work.
8. Confirm payments history endpoint works.
9. Continue ASND verification hardening.
10. Wire frontend payment flow to backend cleanly.
11. Keep payment/access regression tests green.
12. Keep documentation updated.

Near-term priorities:

1. Create reliable MVP demo.
2. Make the gated tool flow work end-to-end.
3. Add better frontend payment/access states.
4. Add Telegram/Discord planning.
5. Improve Hermes runtime rules.
6. Improve cronjob system.
7. Create tool marketplace plan.
8. Create safer revenue flywheel plan.
9. Draft community updates from real progress.
10. Prepare launch readiness checklist.

Long-term priorities:

1. Agent marketplace.
2. User-created agents.
3. Tokenized agent workflows.
4. ASND-gated features.
5. Revenue-backed ASND utility.
6. Buyback/burn system only after real revenue flow exists.
7. Telegram/Discord bot integration.
8. AI workflow automation.
9. More advanced Hermes self-improvement loops.
10. Multi-agent orchestration.

---

## 18. Important Files (Current)

Important root files:

- AGENTS.md
- MEMORY.md

Important backend files:

- backend/app/main.py
- backend/app/routes/health.py
- backend/app/routes/payments.py
- backend/app/routes/users.py
- backend/app/routes/tools.py
- backend/app/routes/jobs.py
- backend/app/routes/platform.py
- backend/app/services/access_service.py
- backend/app/services/idempotency.py
- backend/app/services/scheduler_service.py
- backend/app/services/job_runner.py
- backend/app/services/runtime_config.py
- backend/app/db/session.py

Important scheduler/runtime files:

- scripts/run_scheduler.py
- scripts/job_admin.py
- docs/scheduler-runtime.md

Important knowledge folders:

- raw/
- wiki/
- system/
- learning/
- skills/

Important future/current docs:

- wiki/Payment-System.md or wiki/payment-system.md
- wiki/Access-Control.md or wiki/auth.md
- wiki/ASND-Token.md
- wiki/Revenue-Flywheel.md
- wiki/Tokenized-Agents.md
- wiki/Tool-System.md
- wiki/User-System.md
- wiki/roadmap.md
- system/Hermes-Runtime-Rules.md
- system/cronjobs/approved-cronjobs.md
- learning/*.md
- skills/*.md

---

## 19. Local Development Commands

Known backend direction:

cd ~/projects/AgentAscend
source .venv/bin/activate
uvicorn backend.app.main:app --reload

Health check:

curl http://127.0.0.1:8000/health

Example user/access checks:

curl "http://127.0.0.1:8000/users/real3/access"
curl "http://127.0.0.1:8000/users/real3/payments"

Git status:

git status

Do not run destructive commands unless explicitly approved.

---

## 20. Public Communication Rules

AgentAscend public messaging should be:

- Serious
- Builder-focused
- Transparent
- Confident
- Not hype-only
- Not scammy
- Not overpromising
- Honest about current progress

Good messaging themes:

- Building daily
- AI x Web3 infrastructure
- Intelligent agents
- Payment-gated tools
- Autonomous workflows
- Backend and frontend progress
- Long-term positioning for AI/crypto/agents/robotics
- Community being early to the build

Avoid:

- Guaranteed returns
- Guaranteed price increases
- “This will 100x”
- Fake partnership claims
- Claims that features are live before they are
- Overstating X/Twitter account status
- Sounding desperate about account appeals

---

## 21. X / Social Account Context

AgentAscend X account has had suspension/lock issues.

Known situation:

- Appeal process has been ongoing.
- X response said to follow prompts after signing in.
- No prompts appeared.
- Another appeal process may be needed.
- Project has not stopped.
- Other channels exist or are being built:
  - GitHub
  - Discord
  - Reddit
  - TikTok
  - Stocktwits
  - Telegram

Hermes may draft professional appeal language and community updates.

Hermes must not send appeals or external messages automatically.

---

## 22. GitHub / Community Direction

AgentAscend has or is building presence across:

- GitHub
- Telegram
- Discord
- Reddit
- TikTok
- Stocktwits
- X/Twitter when restored

Community updates should emphasize:

- The project is still moving forward.
- Backend and frontend are being built.
- The system is robust and will take time.
- AI/crypto/agents/robotics may become a major future growth area.
- AgentAscend wants to be positioned before the wave becomes obvious.

Do not overpromise timelines.

---

## 23. MVP Launch Readiness Criteria

AgentAscend is closer to MVP when:

1. Backend starts reliably.
2. /health works.
3. Payment create endpoint works.
4. Payment verification endpoint works with real verification.
5. Payment records are stored.
6. Duplicate transaction signatures are blocked.
7. Access grants are created only after verified payment.
8. User access endpoint shows correct access.
9. Gated tool checks backend access before running.
10. Frontend can connect wallet.
11. Frontend can trigger payment.
12. Frontend can request backend verification.
13. Frontend can unlock gated tool after backend confirms access.
14. Docs explain how to run and test the system.
15. Security risks are documented.
16. Public demo claims are accurate.

---

## 24. Launch Blockers (Current)

Current or likely launch blockers:

- Payment verification hardening must stay enforced and regression-tested.
- ASND verification not yet fully implemented.
- Frontend/backend payment flow may not be fully wired.
- Payment/access regression test coverage should keep expanding.
- Database schema may need tightening (`access_grants` audit linkage).
- Error handling/observability may need improvement.
- MVP demo flow may need cleanup.
- Docs may need updating.
- Public messaging must stay accurate.

---

## 25. MEMORY.md Maintenance Rules

Before making important project changes, Hermes should read this MEMORY.md.

When important project facts change, Hermes should propose an update to MEMORY.md.

Do not add:

- Secrets
- Private keys
- Seed phrases
- API keys
- Raw logs
- Huge transcripts
- Temporary debugging noise
- Unverified assumptions as facts

Keep this file concise enough to read quickly (target ~250 lines; move detailed procedures to wiki/system docs).

If a section grows too long, move details into /wiki and link or reference the wiki page from here.

MEMORY.md should answer:

1. What is AgentAscend?
2. What is being built now?
3. What is the architecture?
4. What are the rules?
5. What are the risks?
6. What should Hermes remember before acting?

---

## 26. Current Operating Bias

The project should prioritize:

1. Working MVP over endless planning.
2. Real payment/access flow over fancy UI.
3. Backend truth over frontend assumptions.
4. Security over speed when money/access is involved.
5. Simple launchable version over overbuilt marketplace.
6. Honest community updates over hype.
7. Durable documentation over scattered chat memory.
8. Cronjob discipline over random autonomous activity.
9. Small safe changes over large risky rewrites.
10. Reuben approval for money/security/public-launch decisions.

---

## 27. Best Next Action Pattern

When Hermes finishes any major review, it should end with:

Best next coding task:
Best next documentation task:
Best next community task:
Biggest current risk:
Recommended command for Reuben to approve:

This keeps AgentAscend moving forward without losing control.

---

## 28. Final Reminder

AgentAscend is being built as a real AI x Web3 project.

The immediate goal is not to build every future feature at once.

The immediate goal is to prove the core loop:

wallet connection → payment → backend verification → access grant → gated tool use

Once that loop works reliably, AgentAscend can expand into:

- AI tools
- Telegram bots
- Discord bots
- Agent marketplace
- Tokenized agents
- ASND utility
- Revenue flywheel
- Autonomous workflows
- Larger AI x Web3 infrastructure

Hermes should keep the project focused, safe, documented, and moving forward daily.
