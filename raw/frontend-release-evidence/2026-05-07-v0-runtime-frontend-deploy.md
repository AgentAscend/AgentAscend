# v0 Runtime Frontend Deploy Evidence

## Summary
Sanitized archive note for the deployed/audited AgentAscend v0 runtime frontend ZIP/source candidate.

Status: PASS for documentation/evidence archival.

This note records the v0 ZIP/source artifact and links it to the latest live/static/Playwright frontend QA evidence. The ZIP binary itself is intentionally not committed.

## Artifact
- ZIP path: `/home/agentascend/Downloads/b_ANz9e3XMJhO.zip`
- ZIP name: `b_ANz9e3XMJhO.zip`
- SHA256: `11cf476426d453aadaa228ea8e24a0c1af1a74ca569337b22d69b68756aac644`
- ZIP size: 1,329,201 bytes
- ZIP file count: 146
- Deployed frontend: `https://www.agentascend.ai`
- API base: `https://api.agentascend.ai`
- Evidence note created: 2026-05-07 01:30 UTC

## Source/audit match
- The ZIP exists at the recorded path.
- The SHA256 matches the previously audited v0 source candidate hash: `11cf476426d453aadaa228ea8e24a0c1af1a74ca569337b22d69b68756aac644`.
- Fresh audit directory checked: `/tmp/agentascend-v0-cycle003-reaudit-20260506-173416`.
- ZIP-to-audit-dir comparison matched the audited source except for one generated file: `tsconfig.tsbuildinfo`.
- Interpretation: this is the same audited v0 source candidate for release/evidence purposes; the generated TypeScript build-info delta is not product source.

## Deploy/live status
- Live frontend route `https://www.agentascend.ai` returned HTTP 200 during evidence archival.
- Live frontend app routes listed below returned HTTP 200 during evidence archival.
- Exact Vercel deployment ID/URL was not available from local credentials in this session, so this note records live production URL/status rather than a Vercel deployment object.

## Post-deploy QA protocol used
- Standing protocol: `docs/post-deploy-qa-protocol.md`.
- Protocol class: frontend/v0 deploy evidence plus live frontend route/header smoke and existing Playwright QA artifact link.
- Related current status: `MEMORY.md`, especially the standing post-deploy QA rule and current frontend/product state sections.

## Live frontend routes checked
All returned HTTP 200 in the evidence archival smoke:
- `https://www.agentascend.ai`
- `https://www.agentascend.ai/app`
- `https://www.agentascend.ai/app/overview`
- `https://www.agentascend.ai/app/agents`
- `https://www.agentascend.ai/app/tasks`
- `https://www.agentascend.ai/app/outputs`
- `https://www.agentascend.ai/app/executions`
- `https://www.agentascend.ai/app/workflows`
- `https://www.agentascend.ai/app/deployments`
- `https://www.agentascend.ai/app/marketplace`

## Frontend security headers
Checked on `https://www.agentascend.ai/app/overview` during evidence archival:
- Strict-Transport-Security: present
- Content-Security-Policy: present
- Permissions-Policy: present
- Referrer-Policy: present
- X-Content-Type-Options: present
- X-Frame-Options: present

## API smoke
Checked during evidence archival:
- `GET https://api.agentascend.ai/health` -> HTTP 200
- `GET https://api.agentascend.ai/openapi.json` -> HTTP 200 valid JSON

## Playwright/static/live QA evidence
Latest local Playwright QA evidence files:
- Safe unauthenticated harness: `/tmp/agentascend-browser-qa/agentascend-browser-qa.js`
- Full authenticated QA result: `/tmp/agentascend-browser-qa/full-auth-qa-output/result.json`
- Full authenticated screenshots directory: `/tmp/agentascend-browser-qa/full-auth-qa-output/`

Latest full authenticated QA summary from sanitized result:
- Browser: Playwright Chromium
- Authenticated session used: yes
- Sandbox args: `--no-sandbox`, `--disable-setuid-sandbox`
- Routes checked: 8 authenticated app routes
- Render-blocking errors: 0
- Console/page/failed request issues in route results: none recorded
- Forbidden endpoint attempts:
  - `/payments/pumpfun/create`: 0
  - `/payments/pumpfun/verify`: 0
  - `/jobs/run-due`: 0
  - `/admin/audits`: 0
- Login POSTs allowed: 1
- Run Agent POSTs allowed during this automated run: 0
- The account already had runtime-loop evidence visible after login; no extra Run Agent click was performed by this run.

## Runtime loop status
Runtime loop tracked in latest QA evidence:
Agent -> Run Agent -> Task -> Execution -> Output

Evidence from authenticated QA result:
- Overview rendered `AgentAscend Command Center`.
- Agents rendered with a test agent present.
- Tasks rendered `Manual run: test` entries.
- Executions rendered `Execution Ledger` and execution signals.
- Outputs rendered `Output Library` plus output entries for manual runs.
- Overview signals showed command center, task status, execution, and output indicators.

Interpretation:
- Runtime loop evidence is present and linked.
- The full automated Playwright run did not create a new task because no visible Run Agent button was available in that session/account state; existing owner-assisted/runtime evidence still links the deployed frontend to the Agent -> Run Agent -> Task -> Execution -> Output loop.

## Pump.fun/payment/wallet/API regression notes
- Pump.fun payment flow preservation was part of the audited source and live bundle/marker checks from the post-deploy QA cycle.
- No Pump.fun payment was tested during this evidence archival.
- No payment intent was created during this evidence archival.
- Pump.fun verify was not called during this evidence archival.
- Wallet provider behavior was preserved by scope; no wallet popup was approved and no transaction was signed.
- API base URL behavior was preserved by scope; no frontend or Vercel variables were changed.

## Admin/scheduler exposure notes
- No admin token exposure was recorded.
- `/jobs/run-due` was not called.
- Scheduler job state was not changed.
- No scheduler controls were exercised.

## Safety confirmations
- ZIP binary committed: no.
- Backend code changed: no.
- Frontend code changed: no.
- Deployment performed: no.
- Production DB mutated: no.
- Migrations run: no.
- Payment action performed: no.
- Pump.fun verify called: no.
- Scheduler job state changed: no.
- `/jobs/run-due` called: no.
- Secrets/cookies/auth tokens/raw request bodies/raw response bodies/raw DB rows/raw metadata/raw payloads/raw task body/output/wallet private data printed: no.

## Related links
- Standing post-deploy protocol: `docs/post-deploy-qa-protocol.md`
- Current operating memory/status: `MEMORY.md`
- Frontend workflow wiki: `wiki/frontend-v0-workflow.md`
- Current project state wiki: `wiki/current-project-state.md`
- Prior owner-assisted runtime QA evidence: `raw/frontend-qa/2026-05-05-owner-assisted-runtime-frontend-qa-pass.md`
