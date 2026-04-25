## Summary
AgentAscend uses a split-brain autonomy model where Hermes coordinates routine, reasoning, and premium strategic work without allowing automation chaos. The default mode is Level 0, which permits recommendations and reports but does not permit automatic activation of new recurring jobs or risky edits.

## Components
- Routine model tier for low-risk repetitive checks, file scans, git summaries, basic health checks, documentation gaps, broken links, TODO extraction, changelog generation, dependency collection, and log summaries.
- Reasoning model tier for multi-file analysis, debugging, test design, frontend/backend mismatch review, implementation planning, risk classification, and escalation memos.
- Premium strategic model tier for payment verification architecture, security, replay protection, SOL/ASND logic, access control, revenue flywheel, tokenized-agent strategy, marketplace architecture, launch roadmap, public-trust decisions, and final approvals.
- Autonomous task spawning rules requiring a clear reason, trigger, schedule, model tier, risk level, inputs, output path, exact prompt, stop condition, escalation condition, edit permissions, and approval requirement.
- Automation levels from Level 0 recommend-only through Level 4 premium-approval-required.
- Escalation rules for money, wallets, payment verification, access control, replay protection, ASND utility, buyback/burn logic, database integrity, public launch, security, user funds, and public claims.
- Cronjob retirement rules to prune noisy, duplicate, stale, or low-value automation.

## Relationships
- Coordinates [[Hermes Agent]]
- Extends [[Automation Engine]]
- Protects [[Payment System]]
- Protects [[Payment Verification]]
- Protects [[Token Gated Access]]
- Supports [[Knowledge System]]
- Supports [[Telegram Interface]]
- Supports [[Strategy Engine]]

## Notes
- Default autonomy is Level 0: Hermes may propose cronjobs, design sub-agents, classify model tiers, create reports, and recommend activation, but may not activate new recurring jobs automatically unless Reuben explicitly enables higher autonomy.
- Level 1 allows safe reporting autonomy only if explicitly enabled.
- Level 2 allows safe maintenance edits only if explicitly enabled.
- Level 3 allows controlled small build work only if explicitly enabled and verified.
- Level 4 requires Premium Strategic review and Reuben approval for payment, wallet, access-control, tokenomics, database, launch, production, social-posting, user-funds, or reputation-sensitive actions.
- New cronjob proposals belong in raw/cronjob-proposals/YYYY-MM-DD-HHMM.md.
- Approved cronjobs belong in system/cronjobs/approved-cronjobs.md.
- Rejected cronjobs belong in raw/cronjob-proposals/rejected/YYYY-MM-DD-HHMM.md.
- Retirement proposals belong in raw/cronjob-retirement/YYYY-MM-DD-HHMM.md.
- Daily/major cron cycles should include an Autonomous Task Spawning Review section so AgentAscend gains compounding automation without creating noise.
