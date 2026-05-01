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

# Auth persistence issue factual log - 2026-04-25

Timestamp: 2026-04-25 21:20 PDT

Facts observed:
- User-reported issue queue includes tasks disappearing after sign out/sign in.
- Backend has auth routes and `tests/test_auth_persistence_config.py` in source.
- Live task persistence after signout/signin was not proven during this safe overnight cycle.

Open verification:
- Create throwaway user through live `/auth/signup` or app UI.
- Create a task while authenticated.
- Sign out, sign back in, and verify the task reappears from backend source of truth.
- Verify frontend never falls back to local demo/static task arrays after an empty successful API response.
