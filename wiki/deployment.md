# Deployment

## Summary
Backend deploys GitHub to Railway; frontend deploys through Vercel/v0. Live backend health is `https://api.agentascend.ai/health`. Local `main` may be ahead of `origin/main`; pushing and deployment require explicit approval.

## Components
- Backend deployment:
  - Railway backend service
  - Railway Postgres
  - GitHub `main` as backend source
- Frontend deployment:
  - Vercel frontend
  - v0 ZIP/file-level source review workflow
  - Namecheap DNS
- Verification surfaces:
  - `https://api.agentascend.ai/health`
  - `/openapi.json`
  - live frontend `/_next/static` chunks
  - CSP headers

## What is working
- Live backend health returned ok during recent checks.
- OpenAPI was reachable during recent checks.
- Latest live CSP verification included both SolanaTracker HTTPS and WSS RPC origins for browser wallet connectivity.
- Railway services were visible in read-only checks with successful latest statuses.

## What is broken or unproven
- Need verify latest local backend commits are deployed to Railway after any approved push/deploy.
- Need verify Vercel deployment includes latest v0 patch content after any approved v0 deploy.
- Browser automation can have sandbox limitations; HTTP/header/bundle/WebSocket checks remain useful independent evidence.

## Next actions
- Push local commits only after owner approval.
- Poll `/health` and `/openapi.json` after approved deploys.
- Use live bundle marker scan after Vercel deploy.
- Check env presence without exposing values.

## Relationships
- [[Auth]]
- [[Database]]
- [[Marketplace]]
- [[Scheduler]]
- [[Frontend v0 Workflow]]
- [[Known Issues]]
- [[Roadmap]]

## Safety notes
- No deploys without explicit instruction.
- Never paste secrets or env values into reports.
- Do not print credentialed RPC URLs, DB URLs, Railway/Vercel secrets, auth tokens, cookies, or private keys.

## Notes
This page was updated during the 2026-04-29 post-audit knowledge curation. Treat source-level facts separately from live-production verification.
