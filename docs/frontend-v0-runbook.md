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
- Latest live Playwright QA PASS WITH CAVEATS: `raw/frontend-qa/2026-05-13-live-output-library-runtime-qa-pass-with-caveats.md`. It verified throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Output preview plus Output Library search/preview/disabled unsupported actions. Payment, wallet, and Pump.fun were intentionally not tested.


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

## Workflow builder owner-isolation gate
Workflow owner-isolation QA passed on 2026-05-09 and is archived at `raw/frontend-qa/2026-05-09-workflow-builder-owner-isolation-qa.md`. Future v0 workflow work must preserve the backend graph payload boundary `{ nodes: [...] }`; do not present `edges`, branching, ordered steps, output schemas, or full visual graph editing as live until backend OpenAPI supports those fields/features. Owner-isolation regression checks should verify User A create/save/read/run, User B list exclusion, and 403 on cross-user graph/save/run/runs probes.

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
- the configured browser RPC HTTPS origin
- the matching configured browser RPC WSS origin
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
    print(path, 'has_browser_rpc_https=', 'https://' in csp and 'rpc' in csp.lower(), 'has_browser_rpc_wss=', 'wss://' in csp and 'rpc' in csp.lower())
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

## Related
- [[current-project-state|Current Project State]]
- [[AgentAscend]]
- [[Hermes]]
- [[Cronjobs]]
