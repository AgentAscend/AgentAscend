---
type: security review
project: AgentAscend
date: 2026-05-02
status: archived
tags:
  - agentascend
related:
  - "[[Payment Access Control]]"
  - "[[Launch Readiness]]"
  - "[[known-issues|Known Issues]]"
---

Related: [[Payment Access Control]], [[Launch Readiness]], [[known-issues|Known Issues]]

# 2026-05-02 Replay-index Migration Preflight

Unprocessed/source note for project state update.

Result: PASS.

DDL execution: not recommended and not needed now. No DDL was run and no production DB mutation occurred.

Aggregate duplicate counts were all zero:
- duplicate payment tx_signature groups: 0
- duplicate payment_intent tx_signature groups: 0
- duplicate active grant groups: 0
- duplicate listing/user entitlement groups: 0

Existing index inspection completed safely with sanitized output only. Existing valid replay protections already satisfy the target:
- payments(tx_signature): valid unique index/constraint already present
- payment_intents(tx_signature nonempty): valid unique partial index already present
- access_grants active user/feature/intent_reference: valid unique partial index already present
- access_grants active user/feature/payment_id: valid unique partial index already present
- marketplace_entitlements(listing_id, user_id): valid unique constraint/index already present

Recommendation: STOP; do not run replay-index DDL now. Candidate DDL would likely be redundant, especially for payments(tx_signature). Future DDL should inspect semantic equivalence first, not just IF NOT EXISTS by name. Do not drop existing production constraints/indexes unless separately inspected and approved. CREATE INDEX CONCURRENTLY and DROP INDEX CONCURRENTLY cannot run inside normal transactions.

Next hardening phase: Node dependency audit/cleanup.
