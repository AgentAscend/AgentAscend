# Marketplace

## Summary
Marketplace backend routes and E2E tests exist. Pump.fun/tokenized-agent purchase, unlock, creator accounting, and claim flow have passed a live owner-reported canary; archive sanitized evidence before public launch claims.

## Components
- Marketplace source:
  - `backend/app/routes/marketplace.py`
  - `backend/app/schemas/marketplace.py`
  - `tests/test_marketplace_publish_e2e.py`
  - v0 marketplace page/API adapter
- Payment/access surfaces:
  - Pump.fun create/verify endpoints
  - backend-verified access grants
  - creator accounting/claim flow

## What is working
- Backend marketplace route file exists.
- E2E test file covers publish/discover and private draft behavior.
- Active Pump.fun payment flow uses backend create/verify endpoints and backend-verified access.
- Live canary reportedly completed purchase, ownership unlock, dashboard accounting, and creator claim payout.

## What is broken or unproven
- Live frontend publish wiring and Vercel bundle status need verification after each v0 deploy.
- LocalStorage ghost drafts and stale publish flows remain a known risk.
- Public launch claims still need archived public transaction IDs and sanitized UI/network evidence.

## Next actions
- Run marketplace publish E2E test locally when marketplace work is in scope.
- Run live throwaway publish/list/discover smoke only in an explicitly approved production-smoke phase.
- Scan v0 bundle for `deleteDraftListing(draft.id)` and absence of `markListingPublished(draft.id...)` success path.
- Preserve payment/claim evidence without secrets, signed transactions, cookies, or wallet-private data.

## Relationships
- [[Auth]]
- [[Database]]
- [[Deployment]]
- [[Scheduler]]
- [[Frontend v0 Workflow]]
- [[Known Issues]]
- [[Roadmap]]

## Safety notes
- No marketplace financial/tokenomics decisions without approval.
- Destructive delete tests must use throwaway owned data only.
- Do not run real payments, wallet signing, SOL transfers, Pump.fun claims, buyback, or burn actions without explicit approval.

## Notes
This page was updated during the 2026-04-29 post-audit knowledge curation. Treat source-level facts separately from live-production verification.
