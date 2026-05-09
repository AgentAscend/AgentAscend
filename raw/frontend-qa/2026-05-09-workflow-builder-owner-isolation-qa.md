# Workflow Builder Owner-Isolation Live QA — 2026-05-09

## Verdict
PASS

## Scope
Controlled live product QA after deployed backend workflow auth/ownership commit `5299417d649c2d6c1e2acfd315741f175786998a`.

Frontend tested: `https://www.agentascend.ai/app/workflows`
API tested: `https://api.agentascend.ai`

Browser harness: Playwright Chromium from `/tmp/agentascend-browser-qa`, headless with `--no-sandbox --disable-setuid-sandbox`.

## Safety boundaries
- Throwaway QA accounts only.
- No owner credentials.
- No owner wallet.
- No payment endpoints called.
- No Pump.fun verify call.
- No wallet popups approved.
- No SOL sent.
- No scheduler jobs run.
- No `/jobs/run-due` call.
- No admin audit calls from the frontend session.
- No Railway/Vercel/env changes.
- No production DB manual mutation, migration, or manual index action.
- No secrets, cookies, auth tokens, DB URLs, RPC URLs, key material, recovery phrases, raw request/response bodies, raw DB rows, raw metadata/payload, transaction-base64 material, or signed transaction material recorded.

## Throwaway QA data
- User A: throwaway account created through normal auth flow.
- User B: throwaway account created through normal auth flow.
- User A workflow ID: `wf_03dbf75268`
- Workflow name: `Hermes Owner Isolation QA 4a1ea9`

No credentials, cookies, or tokens are stored in this note.

## User A workflow creation
PASS

Evidence:
- User A opened `/app/workflows` while authenticated.
- UI opened the Create Workflow modal.
- Modal copy was honest: “Create a draft workflow, then use the Nodes tab to build it from backend-saved graph nodes.”
- UI submitted `POST /workflows` with authenticated session.
- Sanitized request shape: keys `name`, `status`.
- Backend returned success.
- User A list included workflow `wf_03dbf75268`.
- UI list displayed the new workflow.

## User A graph edit/save/read
PASS

Evidence:
- User A opened the workflow editor.
- User A selected the Nodes tab.
- User A added one node through the UI.
- UI showed unsaved graph changes and one node.
- UI submitted `PUT /workflows/wf_03dbf75268/graph`.
- Sanitized request shape: `{ nodes: [...] }`.
- Node count sent: 1.
- Unsupported `edges` payload was not sent.
- Backend accepted the graph save.
- Follow-up graph read returned HTTP 200.
- Saved graph node count: 1.

## User A workflow run/history
PASS

Evidence:
- User A clicked Run Workflow once through the UI.
- UI called `POST /workflows/wf_03dbf75268/run`.
- Backend returned success.
- Follow-up `GET /workflows/wf_03dbf75268/runs` returned HTTP 200.
- Run history count after run: 1.
- UI Run History area rendered workflow/run-history content.

## User B owner isolation
PASS

Evidence:
- User B opened `/app/workflows` while authenticated as a separate throwaway account.
- User B UI list did not show User A workflow name or workflow ID.
- User B `GET /workflows` returned HTTP 200 with zero workflows for this throwaway account.
- User B API list did not include `wf_03dbf75268`.
- User B cross-user probes against User A workflow all failed closed:
  - `GET /workflows/wf_03dbf75268/graph` -> 403
  - `PUT /workflows/wf_03dbf75268/graph` -> 403
  - `POST /workflows/wf_03dbf75268/run` -> 403
  - `GET /workflows/wf_03dbf75268/runs` -> 403

## UI copy / product honesty
PASS

Observed:
- Workflow page says `PARTIALLY LIVE`.
- Copy says the backend runtime worker can run agents and create tasks, executions, and outputs.
- Copy says full visual workflow graph editing with triggers, branching, ordered steps, and output schemas is coming later.
- Copy says users can run agents directly today.
- Create modal no longer says “choose a template.”
- Static fake template cards were absent; template area says templates are not available yet and to create from scratch.
- Fake settings were absent during create and after detail/run-history inspection:
  - no `Auto-retry — Enabled`
  - no `Timeout — 5 minutes`
  - no `Notifications — Email`

## Sanitized network / console summary
- Console errors: 0
- Page errors: 0
- Failed requests: 0
- Workflow endpoint calls observed from frontend session:
  - `GET /workflows`
  - `POST /workflows`
  - `GET /workflows/{workflow_id}/graph`
  - `PUT /workflows/{workflow_id}/graph`
  - `POST /workflows/{workflow_id}/run`
  - `GET /workflows/{workflow_id}/runs`
- Payment endpoints called: 0
- Pump.fun verify called: 0
- `/jobs/run-due` called: 0
- Admin audit endpoints called from frontend: 0
- Admin token exposure observed: no

## Caveats
- This QA intentionally created controlled production workflow/run data through normal authenticated product flows.
- It did not test owner credentials, owner wallets, payments, payment intents, Pump.fun verify, or wallet interactions.
- It did not run scheduler jobs or call `/jobs/run-due`.
- It did not perform manual production DB cleanup.

## Recommended next step
Continue frontend workflow-builder polish from PASS baseline. Good next slices:
1. Improve node configuration editing and labels while preserving `{ nodes: [...] }` graph-save shape.
2. Add clearer run-history details if backend exposes richer run/execution linkage.
3. Keep unsupported graph features disabled or marked coming later until backend routes support them.
