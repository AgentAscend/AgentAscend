# Auth

## Summary
Authentication exists in the backend with signup/session support, frontend profile wiring, and backend ownership checks for private data/tool access. The remaining auth risk is live session persistence and per-user data reload after signout/signin.

## Components
- Backend auth routes and services:
  - `backend/app/routes/auth.py`
  - `backend/app/services/auth_service.py`
  - `backend/app/schemas/auth.py`
- Access-control surfaces:
  - private reads and deletes
  - tool access enforcement
  - legacy payment verification ownership checks
- Tests and frontend touchpoints:
  - `tests/test_auth_persistence_config.py`
  - frontend v0 auth guard and API client files from latest ZIP

## What is working
- Backend auth routes exist in source.
- Tests exist for auth persistence configuration.
- Live API health is up.
- Backend private reads, deletes, tool access, and legacy payment verification enforce owner/admin access in source.

## What is broken or unproven
- User-reported task disappearance after signout/signin is not yet resolved/proven.
- Need live verification of frontend token storage and reload behavior.
- Need release-gate checks to confirm private frontend calls consistently attach session tokens.

## Next actions
- Run auth persistence verification when live smoke testing is explicitly approved.
- Check latest v0 ZIP for `getSessionToken`/`requireSessionToken` on private API calls.
- Run live signout/signin task persistence smoke only with throwaway owned data.

## Relationships
- [[Database]]
- [[Marketplace]]
- [[Tasks Outputs]]
- [[Scheduler]]
- [[Frontend v0 Workflow]]
- [[Deployment]]
- [[Known Issues]]
- [[Roadmap]]

## Safety notes
- Never store tokens in docs.
- Private endpoints must require bearer auth and enforce owner access.
- Do not print auth headers, cookies, session tokens, or raw request/response bodies.

## Notes
This page was updated during the 2026-04-29 post-audit knowledge curation. Treat source-level facts separately from live-production verification.
