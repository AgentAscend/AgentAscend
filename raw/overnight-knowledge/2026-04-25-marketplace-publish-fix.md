---
type: evidence
project: AgentAscend
date: 2026-04-25
status: archived
tags:
  - agentascend
  - overnight-knowledge
related:
  - "[[AgentAscend]]"
  - "[[Roadmap]]"
  - "[[Ops Runbook]]"
---

Related: [[AgentAscend]], [[Roadmap]], [[Ops Runbook]]

# Marketplace publish fix factual log - 2026-04-25

Timestamp: 2026-04-25 21:20 PDT

Facts observed:
- Backend source contains `backend/app/routes/marketplace.py` and `tests/test_marketplace_publish_e2e.py`.
- Test names indicate queued publish create should become immediately discoverable, while explicit drafts remain private to discover.
- Known release-gate lesson: marketplace publish must map frontend local statuses to backend-supported publish behavior and must not leave local pseudo-published drafts as source of truth.

Open verification:
- Run local test: `.venv/bin/python -m pytest tests/test_marketplace_publish_e2e.py -q`.
- Probe live create/list/discover with a throwaway user and delete/cleanup only if endpoint supports safe ownership deletion.
