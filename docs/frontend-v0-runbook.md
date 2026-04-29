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
