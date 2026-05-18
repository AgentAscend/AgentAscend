# AgentAscend Frontend v0 Runbook

## Purpose
Keep v0/Vercel frontend work aligned with the live backend contract and prevent source-of-truth regressions.

## Current deployment
- Public frontend: `https://www.agentascend.ai`.
- Key app routes checked during the 2026-04-29 audit:
  - `/`
  - `/app/overview`
  - `/app/marketplace`
  - `/app/executions`
- Live routes returned HTTP 200 during read-only audit.
- Latest Workflow Run-History / Execution Trace UX production QA PASS: `raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass.md`. It verified PR #5 merged/live at `a010a7aff8ec2358c21fe088ac87d5ede3144f2a`, Vercel production success, `/app/workflows` HTTP 200, `/app/executions` HTTP 200, backend `/health` HTTP 200, backend `/openapi.json` HTTP 200 valid JSON, execution trace preview/link markers, and no raw metadata/payload rendering or forbidden scheduler/admin/payment calls. PR #4 Deployment Events UX is separately merged/live at `ec4b59e68d7f26edeb43e8a48b122cfeff539fac`; prior stale/mixed PR #4 references are resolved.
- Latest production Run Agent toast/drawer follow-up QA PASS WITH POLISH CAVEAT: `raw/frontend-qa/2026-05-17-run-agent-toast-drawer-followup-production-qa.md`. It verified throwaway signup → Ascend Forge create → exactly one visible Run Agent click → `POST /agents/{id}/run` HTTP 200 → task_id returned → no false failure → Pending/Running state → Latest Run drawer without reload → `Open Task` link to `/app/tasks?task_id=...` → Tasks/Executions/Outputs/Overview runtime state. Exact `Agent run queued` / toast action visibility remains optional polish, not a blocker; `Open Execution` was not applicable because the run response did not contain execution_id. Payment, wallet, admin, scheduler, `/jobs/run-due`, and Pump.fun were intentionally not tested/called.
- Previous live Playwright QA PASS WITH CAVEATS: `raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats.md`. It verified throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Output preview plus Output Library search/preview/disabled unsupported actions. Payment, wallet, and Pump.fun were intentionally not tested.


## Workflow Run-History / Execution Trace UX release gate
A workflow run-history source or live deployment passes this gate when:
- `/app/workflows` and `/app/executions` return HTTP 200 in production.
- Backend `/health` returns HTTP 200.
- Backend `/openapi.json` returns HTTP 200 and valid JSON.
- Run-history renders execution trace preview and links to execution, task, and output where backend data exists.
- Empty/missing linked data uses honest copy such as “Execution details are not linked for this run yet.” and “No output linked yet.”
- Status rendering covers queued, running, completed, failed, pending approval, and an unknown neutral fallback without inventing backend state.
- Raw `metadata_json`, raw `payload_json`, raw task/output content, cookies, tokens, wallet/private data, and credentials are not rendered or archived.
- Scheduler/admin/payment safety markers remain absent: no `/jobs/run-due`, no frontend runtime-token/admin audit calls, no payment route calls added unless the slice explicitly covers payments.

Latest archived PASS: `raw/frontend-qa/2026-05-17-workflow-run-history-execution-trace-ux-live-pass.md`.

## Run Agent UI click-path release gate
A Run Agent source or live deployment passes this gate when:
- A throwaway account can sign up/sign in.
- `/app/agents` opens and one safe test agent can be created.
- The visible agent action/menu Run Agent path is clicked exactly once.
- Browser network observes `POST /agents/{id}/run` returning HTTP 200.
- UI does not show false `Failed to run agent` copy after the successful run.
- UI shows an honest queued/running/pending state, or a clear success/refresh warning.
- When a Run Agent slice changes success navigation, inspect the immediate no-reload drawer/panel state and verify safe links such as `Open Task` to `/app/tasks?task_id=...` where backend IDs exist.
- `/app/tasks`, `/app/executions`, `/app/outputs`, and `/app/overview` show runtime state or honest pending/empty state.
- Payment, Pump.fun verify, scheduler, `/jobs/run-due`, wallet signing, and frontend admin endpoints are not called during QA.

Latest archived PASS WITH POLISH CAVEAT: `raw/frontend-qa/2026-05-17-run-agent-toast-drawer-followup-production-qa.md`. Runtime path and Latest Run `Open Task` navigation are verified; exact `Agent run queued` / toast action visibility remains optional polish, not a current blocker.

## Output Library release gate
An Output Library source or live deployment passes this gate only when:
- `/app/outputs` renders backend outputs from `GET /outputs` and never falls back to fake/demo/localStorage output authority.
- Search is clearly local over loaded backend outputs unless the live OpenAPI adds server-side search. Required copy: “Search filters loaded backend outputs locally.”
- Unsupported bulk export, share, delete, and pagination/load-more controls are disabled or clearly coming later unless backend endpoints are added.
- Top-level Export All must be disabled while backend bulk export is absent.
- Preview uses backend detail data from `GET /outputs/{output_id}`.
- Download URL is requested on demand from `GET /outputs/{output_id}/download-url`; no fake download URL is generated.
- Payment, Pump.fun verify, scheduler, `/jobs/run-due`, and frontend admin endpoints are not called during Output Library QA.

Latest archived PASS WITH CAVEATS: `raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats.md`. Throwaway QA resources remain in production and require a separate owner-approved cleanup plan before deletion.

## Workflow builder owner-isolation release gate
A workflow-builder source or live deployment passes the ownership gate only when:
- User A can create a workflow through `/app/workflows`, save/read a graph, run it once, and read run history.
- Graph save sends the backend-supported shape `{ nodes: [...] }` and does not send unsupported `edges` unless OpenAPI later supports them.
- User B's workflow list excludes User A's workflow.
- User B direct probes against User A workflow graph, graph save, run, and runs history return 403.
- Workflow copy remains honest: `PARTIALLY LIVE` is acceptable; unsupported templates, full visual graph editing, branching, output schemas, and fake settings must be disabled or marked coming later.
- Payment, Pump.fun verify, scheduler, `/jobs/run-due`, and frontend admin endpoints are not called during workflow QA.

Latest archived PASS: `raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa.md`.

## Pump.fun wallet/payment release gate
A v0 source or live deployment passes the wallet/payment gate only when:
- Active paid pages import/render `PumpfunPaymentModal`.
- Active paid pages call `/payments/pumpfun/create` and `/payments/pumpfun/verify`.
- Verification uses `status === "payment_verified"` and exact reference matching.
- Legacy `PaymentRequiredModal` is not active in overview/marketplace paid flows.
- Old `verifyResponse.success`, active `/payments/verify`, and localStorage paid flags are absent from active paid route bundles.
- Wallet provider uses an explicit public browser RPC env where configured.
- CSP allows the browser RPC over both HTTPS and WSS.

## Current live CSP requirement
Production `connect-src` should include:
- `https://api.agentascend.ai`
- `https://rpc.solanatracker.io`
- `wss://rpc.solanatracker.io`
- existing allowed Solana/RPC/analytics origins as configured

Google Fonts must remain allowed if used:
- `https://fonts.googleapis.com`
- `https://fonts.gstatic.com`

## Read-only live verification script
```bash
python3 - <<'PY'
import urllib.request, re, urllib.parse
base='https://www.agentascend.ai'
for path in ['/app/overview','/app/marketplace','/app/executions']:
    req=urllib.request.Request(base+path, headers={'User-Agent':'AgentAscend-audit'})
    with urllib.request.urlopen(req, timeout=25) as r:
        csp=r.headers.get('content-security-policy','')
        html=r.read().decode('utf-8','ignore')
    print(path, 'https_rpc=', 'https://rpc.solanatracker.io' in csp, 'wss_rpc=', 'wss://rpc.solanatracker.io' in csp)
    assets=sorted(set(re.findall(r'(?:src|href)="([^"]*_next/static/[^"]+\.js[^"]*)"', html)))
    bundle=''
    for src in assets:
        with urllib.request.urlopen(urllib.parse.urljoin(base+path, src), timeout=25) as a:
            bundle += a.read().decode('utf-8','ignore')[:2000000]
    for marker in ['PumpfunPaymentModal','/payments/pumpfun/create','/payments/pumpfun/verify','payment_verified','PaymentRequiredModal','verifyResponse.success']:
        print(' ', marker, marker in bundle)
PY
```

## v0 patch discipline
- Treat each new ZIP/export as source of truth.
- Extract fresh and run mechanical gates before approving.
- Use patch-only prompts; do not redesign unless asked.
- Keep backend endpoint names and response contracts aligned to OpenAPI.
- Never introduce frontend-only access authority.
- Separate source PASS from live deployment PASS.

## Mechanical gates for v0 candidates
Run the package-manager path used by the project, commonly:
```bash
pnpm exec tsc --noEmit
pnpm run build
node scripts/source-truth-check.mjs
pnpm audit --audit-level=moderate
```
Add lint when configured and reliable.

## Browser limitations
If browser automation is blocked in the audit container by Chromium sandbox/user namespace errors, use live HTTP headers, bundle inspection, backend OpenAPI, and direct WSS connectivity as the no-payment deployment gate. State the limitation explicitly.
