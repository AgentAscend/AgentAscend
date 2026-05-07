# AgentAscend Standing Post-Deploy QA Protocol

Status: active standing operating rule.
Scope: Railway backend/API deploys, Railway scheduler deploys, Vercel/frontend/v0 deploys, docs-only commits that trigger deploys, backend commits that trigger deploys, frontend ZIP/source deployments, and scheduler/runtime-worker related deployments.

## Standing rule

After every AgentAscend deploy, Hermes must run post-deploy QA before final PASS. The type of QA depends on deploy type. If QA is blocked, report PARTIAL, never PASS.

Hermes must not mark a deploy as PASS until the matching post-deploy QA checklist has run successfully. If a required check cannot be run, the deploy result is PARTIAL with the exact blocker and next safe step. If production health fails, route/auth/security regressions occur, or an unsafe payment/admin/scheduler surface is exposed, the deploy result is FAIL.

## Safety boundaries

Do not mutate production DB, run migrations, create/drop indexes, change Railway/Vercel variables, change scheduler job state, manually run scheduler jobs, call `/jobs/run-due`, run payments, create payment intents, call Pump.fun verify, create/revoke `access_grants`, change `marketplace_entitlements`, send Telegram/external messages, or print secrets/raw sensitive data.

Never print DB URLs, RPC URLs, auth tokens, cookies, private keys, seed phrases, txBase64, signed transactions, raw DB rows, raw metadata_json, raw payload_json, raw request/response bodies, raw task body, raw task output, wallet private data, or raw logs containing secrets.

## Universal post-deploy checks

Run for every deploy type:

1. Deployment status
   - Railway `AgentAscend` status if backend/scheduler/docs deploy affected Railway.
   - Railway `AgentAscend-Scheduler` status if backend/scheduler/docs deploy affected Railway.
   - Vercel/frontend status if frontend deploy.
   - Confirm no deployment remains BUILDING/DEPLOYING unexpectedly.

2. API health
   - `GET https://api.agentascend.ai/health` -> HTTP 200.
   - `GET https://api.agentascend.ai/openapi.json` -> HTTP 200 valid JSON.

3. API security headers
   - Strict-Transport-Security.
   - Content-Security-Policy.
   - Permissions-Policy.
   - Referrer-Policy.
   - X-Content-Type-Options.
   - X-Frame-Options.

4. Critical route presence in live OpenAPI
   - `POST /payments/pumpfun/create`.
   - `POST /payments/pumpfun/verify`.
   - `GET /agent-capabilities`.
   - `POST /agents`.
   - `GET /agents/{agent_id}`.
   - `PATCH /agents/{agent_id}/config`.
   - `POST /agents/{agent_id}/run`.
   - `POST /agents/{agent_id}/deploy`.
   - `GET /dashboard/command-center`.
   - `GET /tasks`.
   - `GET /tasks/{task_id}/execution`.
   - `GET /outputs`.
   - `GET /executions/me`.
   - `GET /executions/summary`.
   - `GET /executions/{execution_id}`.
   - `GET /admin/audits/task-runtime/aggregate` when expected.

5. Auth gates
   - Schema-valid unauthenticated Pump.fun create returns 401.
   - Unauthenticated admin launch-readiness audit returns 403.
   - Unauthenticated admin task-runtime aggregate returns 403 if the endpoint exists.
   - Do not call Pump.fun verify.

6. Sanitized logs
   - No Traceback.
   - No ERROR/CRITICAL startup blocker.
   - No ImportError.
   - No DB startup failure.
   - No secret-like values printed.
   - No unexpected Pump.fun verify marker.
   - No unexpected payment_intent creation marker.
   - No unexpected access_grant mutation marker.

## Backend/API deploy-specific checks

After backend/API deploys:

1. OpenAPI route diff sanity
   - Expected new routes present.
   - Existing critical routes still present.
   - Pump.fun routes not removed.
   - Jobs routes not unexpectedly exposed.
   - Admin routes remain auth-gated.

2. Runtime/task/worker changes
   - If touched, call `GET /admin/audits/task-runtime/aggregate` with `X-Agent-Runtime-Token` safely.
   - Do not print the token.
   - Report aggregate only: `tasks.total`, `queued`, `running`, `pending_approval`, `completed`, `failed`, `task_worker.enabled`, `task_worker.recent_status`, and safety flags.
   - Confirm safety flags: `raw_rows_returned=false`, `raw_task_body_returned=false`, `raw_task_output_returned=false`, `raw_metadata_returned=false`, `raw_payloads_returned=false`, `db_url_printed=false`, `secrets_printed=false`, `read_only_mode=true`.

3. Payment/access changes
   - Do not run real payments.
   - Do not call Pump.fun verify.
   - Run only read-only aggregate/admin checks.
   - Verify duplicate groups remain zero if a safe aggregate endpoint is available.

4. Scheduler-related backend changes
   - Do not run scheduler jobs.
   - Do not call `/jobs/run-due`.
   - Report natural scheduler activity separately if Railway restart causes it.
   - Distinguish “natural scheduler due job after restart” from “operator-triggered job run”.
   - Never hide natural due-job activity.

## Frontend/v0 deploy-specific checks

After any frontend/v0 deploy:

1. Live route smoke
   - `https://www.agentascend.ai`.
   - `/app`.
   - `/app/overview`.
   - `/app/agents`.
   - `/app/tasks`.
   - `/app/outputs`.
   - `/app/executions`.
   - `/app/workflows`.
   - `/app/deployments`.
   - `/app/marketplace`.
   - Expected: HTTP 200 and no render-blocking static failure.

2. Frontend security headers on at least `/app/overview`
   - HSTS, CSP, Permissions-Policy, Referrer-Policy, X-Content-Type-Options, X-Frame-Options.

3. Playwright harness smoke
   - Use `/tmp/agentascend-browser-qa/agentascend-browser-qa.js` when available.
   - Keep blocking `/payments/pumpfun/create`, `/payments/pumpfun/verify`, `/jobs/run-due`, and `/admin/audits`.
   - Do not click payment/install.
   - Do not click Run Agent unless owner explicitly approves authenticated QA.
   - Do not print cookies/tokens.
   - Do not approve wallet popups.
   - Do not sign transactions.
   - Report browser used, routes loaded, console errors, page errors, failed requests, blocked endpoint counts, and whether payment/admin/scheduler endpoints were avoided.
   - If Playwright is unavailable, report PARTIAL for browser QA, fall back to static route/bundle inspection, and do not claim full visual QA PASS.

4. Live bundle/source marker verification
   - Overview: command-center marker plus `Run Agent`, `Task Created`, `Execution Tracked`, `Output Generated`.
   - Agents: `Run Agent`, runAgent usage, `POST /agents/{agent_id}/run` marker, no generic active `Start`, and View Task/View Execution when expected.
   - Tasks: useTasks, getTaskExecution, `pending_approval`, `Pending Approval`, and no stale “Requires backend integration” blocker.
   - Outputs: `/outputs` backend route marker, “Run an agent to generate your first backend output” when empty state is expected, no stale “Requires backend /outputs endpoint” or “backend endpoint not connected yet” user-facing output copy.
   - Executions: useExecutions/useExecution markers, execution endpoint markers, no stale execution backend-required blocker.
   - Workflows: honest partially-live copy, visual workflow graph editing coming later, and copy must not imply agents cannot run without workflows.
   - Deployments: active actions limited to `pause`, `resume`, `restart`; no active payloads for `start`, `stop`, `redeploy`, `scale`, or `rollback`; unsupported features may remain disabled/coming-soon.
   - Marketplace/payment: `/payments/pumpfun/create`, `/payments/pumpfun/verify`, `payment_verified`; `PaymentRequiredModal`, `verifyResponse.success`, and legacy active `/payments/verify` absent.
   - Admin/scheduler: `X-Agent-Runtime-Token` absent, `/jobs/run-due` absent, `/admin/audits/task-runtime/aggregate` absent from frontend calls, no scheduler controls exposed.
   - Wallet/RPC: wallet provider unchanged unless intentionally touched, `NEXT_PUBLIC_SOLANA_RPC_URL` behavior safe, no private RPC hardcoded, RPC URL not logged.
   - localStorage authority: no localStorage authority for agents/tasks/outputs/executions runtime loop and no fake payment/access/ownership authority.

## Authenticated frontend QA rule

Authenticated QA is not required after every deploy, but Hermes must recommend it when a frontend deploy changes `/app/agents`, Run Agent behavior, `/app/tasks`, `/app/outputs`, `/app/executions`, or auth/session flow.

Authenticated QA may run only if the owner provides a safe test session or owner-assisted login, no passwords/cookies/tokens are printed, payment/admin/scheduler routes remain blocked, Run Agent click is explicitly approved, only one Run Agent click is performed, and no payment flow is tested unless separately approved.

Owner-assisted QA checklist:
1. Sign in.
2. Open `/app/overview`.
3. Open `/app/agents`.
4. Create/select a safe test agent.
5. Click Run Agent once.
6. Confirm no UI crash, task appears, execution appears, output appears or honest empty state appears, command center refreshes, no payment prompt, no admin/scheduler controls, and no `/jobs/run-due`.

## Docs-only deploy checks

If a docs-only commit triggers Railway deploy, still run universal post-deploy checks. Do not skip `/health` or `/openapi`. Report that no code change was expected. If route/API changes appear unexpectedly, report PARTIAL/FAIL.

## Final report format

Every deploy final report must include:

1. PASS / PARTIAL / FAIL.
2. Deploy type: backend, scheduler, frontend, docs-only, or mixed.
3. Commit/ZIP/source deployed.
4. Deployment IDs/statuses.
5. `/health` result.
6. `/openapi` result.
7. Route matrix result.
8. Auth gate result.
9. Security header result.
10. Browser/Playwright smoke result if frontend deploy.
11. Runtime-loop marker result if frontend deploy.
12. Payment/wallet regression result if frontend deploy.
13. Admin/scheduler exposure result.
14. Task-runtime aggregate result if backend/runtime deploy.
15. Sanitized log result.
16. Warnings.
17. Confirmation: no production DB mutation unless explicitly approved, no migrations unless explicitly approved, no scheduler jobs manually run, no `/jobs/run-due`, no payments, no Pump.fun verify, no secrets printed.
18. Next recommended action.

## PASS rules

- PASS only when all required post-deploy checks pass.
- If browser/Playwright check is unavailable for a frontend deploy, result is at most PASS FOR STATIC/SOURCE plus PARTIAL FOR VISUAL QA.
- If production health fails, result is FAIL.
- If route/auth/security regression occurs, result is FAIL.
- If deploy succeeds but logs are unavailable, result is PARTIAL unless other evidence is enough and the limitation is stated.
- If any payment/admin/scheduler unsafe route is exposed in frontend, result is FAIL.

## Related
- [[current-project-state|Current Project State]]
- [[AgentAscend]]
- [[Hermes]]
- [[Cronjobs]]
