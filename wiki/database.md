# Database

## Summary
Backend supports local SQLite for isolated tests and Railway Postgres for production. Production DB aggregate checks have been run read-only; persistence-changing checks still require explicit approval.

## Components
- Database/session source:
  - `backend/app/db/session.py`
- Runtime dependencies:
  - `requirements.txt`
  - Railway `DATABASE_URL` environment variable
- Test/runtime stores:
  - local SQLite DB for development and isolated tests
  - Railway Postgres for production
  - tests using temp DB fixtures

## What is working
- Local scheduler and backend DB tables are active.
- psycopg2-binary is installed locally.
- Live health endpoint is ok.
- Read-only production aggregate checks reported scheduler jobs/events/artifacts without DB writes.

## What is broken or unproven
- Full live create/update/delete persistence smokes were not run in this docs cycle.
- Production cleanup of historical demo rows is separate from source cleanup.
- Any schema or migration change requires a separate approved migration phase.

## Next actions
- Confirm Railway `DATABASE_URL` is present without printing it when deployment checks are in scope.
- Run live create/read/redeploy persistence smoke only in an explicitly approved production-smoke phase.
- Keep local SQLite tests isolated.
- Keep read-only audits separate from mutation tests.

## Relationships
- [[Auth]]
- [[Deployment]]
- [[Marketplace]]
- [[Scheduler]]
- [[Tasks Outputs]]
- [[Known Issues]]
- [[Roadmap]]

## Safety notes
- Do not print connection strings.
- Do not mutate production data without backup/approval.
- Do not run migrations without explicit migration approval.

## Notes
This page was updated during the 2026-04-29 post-audit knowledge curation. Treat source-level facts separately from live-production verification.
