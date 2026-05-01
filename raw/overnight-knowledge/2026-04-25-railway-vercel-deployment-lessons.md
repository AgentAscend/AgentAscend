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

# Railway and Vercel deployment lessons factual log - 2026-04-25

Timestamp: 2026-04-25 21:20 PDT

Facts observed:
- Live backend health at `https://api.agentascend.ai/health` returned ok.
- Past parity issues often happened when source changes existed locally but were not deployed to Railway/Vercel.
- Vercel live route checks are not enough; bundle markers must prove the actual patch is deployed.

Open verification:
- Railway: confirm latest GitHub commit deployed and production env vars are present without printing values.
- Vercel: compare live JS chunks against source patch markers and stale bug markers.
- Never mark source PASS as production PASS without live verification.
