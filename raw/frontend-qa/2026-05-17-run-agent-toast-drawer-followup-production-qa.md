---
type: evidence
project: AgentAscend
date: 2026-05-17
status: archived
related:
  - [[AgentAscend]]
  - [[Launch Readiness]]
  - [[Frontend v0 Workflow]]
  - [[Execution Ledger]]
tags:
  - frontend-qa
  - production-qa
  - run-agent
  - pr-13
  - followup
---

Related: [[AgentAscend]], [[Launch Readiness]], [[Frontend v0 Workflow]], [[Execution Ledger]]

# Run Agent Toast / Latest Run Drawer Follow-up Production QA — PR #13

## Verdict

PASS WITH POLISH CAVEAT

The focused no-reload production QA confirmed the successful Run Agent browser path and the immediate Latest Run drawer task link behavior. The browser observed `POST /agents/{agent_id}/run` returning HTTP 200, no false failure message appeared, the agent card showed honest Pending/Running state, the Latest Run drawer/panel was inspected before any reload, and `Open Task` was visible with the expected `/app/tasks?task_id=...` href shape.

The exact `Agent run queued` toast and `View Task` / `View Execution` toast actions were still not observed within the first 5 seconds after the successful POST. This is a polish caveat rather than a runtime failure because backend truth and runtime propagation passed.

## Deployment under test

- PR: https://github.com/AgentAscend/agentascend-web/pull/13
- PR head commit: `d1438196557855e3c7961796a6218df56b108555`
- Production main commit: `e7c904a31893518469d26a4e72172a4a278b1937`

## Baseline health

- `https://agentascend.ai`: HTTP 200
- `https://api.agentascend.ai/health`: HTTP 200, valid JSON
- `https://api.agentascend.ai/openapi.json`: HTTP 200, valid JSON

No payment routes or admin endpoints were called during baseline checks.

## Throwaway production QA flow

- Throwaway account used: yes
- Safe private test agent created: yes
- Agent name: `QA Run Agent Toast Drawer 20260517232636`
- Agent ID captured: yes, redacted as `agt_6452…9d15`
- Run Agent clicked exactly once: yes
- Browser-observed run request: yes
- Run request: `POST /agents/{agent_id}/run`
- Run request status: HTTP 200
- Response contained `task_id`: yes, redacted as `tsk_9685…9962`
- Response contained `execution_id`: no
- False `Failed to run agent` text after HTTP 200: no
- Page reloaded before immediate drawer inspection: no

## Toast result

- Visible text captured within first 5 seconds: Pending / Running state only
- Exact `Agent run queued` observed: no
- `View Task` toast action observed: no
- `View Execution` toast action observed: no
- False failure observed: no

## Latest Run drawer / panel result

- Current page inspected without reload after POST: yes
- Agent card status: honest Pending/Running state visible immediately after click
- Latest Run panel observed before reload: yes
- `Open Task` link observed: yes
- `Open Task` href shape: `/app/tasks?task_id=...`
- `Open Task` clicked: yes
- `Open Task` navigation loaded: yes
- `Open Execution` link observed: no
- `Open Execution` href shape: not applicable; run response did not contain `execution_id`

## Runtime page result

### Tasks

- `/app/tasks?task_id=...` loaded successfully.
- Linked task context was applied.
- The linked task detail opened honestly.
- Task progressed to completed state.
- Related execution context appeared in task detail.
- No fake task row was created.

### Executions

- `/app/executions` loaded successfully.
- A related task-linked execution appeared for the run.
- The execution state was shown honestly.

### Outputs

- `/app/outputs` loaded successfully.
- The page showed a backend output/artifact or honest backend-loaded state for the run.
- Raw output content was not recorded in this evidence file.

### Overview

- `/app/overview` loaded successfully.
- Overview showed honest runtime activity and completed-task state.

## Browser/network safety summary

- Console errors: 0
- Page errors: 0
- Failed requests: 1 benign aborted Next.js chunk request observed during navigation
- Payment endpoints called: no
- Pump.fun verify called: no
- `/jobs/run-due` called: no
- Admin audit endpoints called: no
- Wallet popup appeared: no
- Wallet signing occurred: no
- Forbidden endpoint blocks triggered: 0

## Local QA artifacts

Sanitized screenshots and result JSON were saved under `/tmp/agentascend-browser-qa/`:

- `20260517232636-followup-agent-created.png`
- `20260517232636-followup-immediate-after-run-no-reload.png`
- `20260517232636-followup-drawer-no-reload.png`
- `20260517232636-followup-open-task-clicked.png`
- `20260517232636-run-agent-toast-drawer-followup-result.json`

These artifacts are local QA artifacts only and were not embedded here.

## Safety confirmations

No prohibited actions were performed:

- No payments run.
- No payment intents created.
- No Pump.fun verify call.
- No marketplace install/pay action.
- No wallet popup approved.
- No wallet transaction signed.
- No scheduler jobs run.
- No `/jobs/run-due` call.
- No admin audit endpoint call.
- No manual production DB mutation.
- No migrations.
- No Railway/Vercel variable changes.
- No code push.
- No manual deploy.
- No secrets, cookies, auth tokens, passwords, DB URLs, RPC URLs, private keys, seed phrases, raw request/response bodies, raw DB rows, metadata_json values, payload_json values, raw task/output content, or wallet-private data were included in this evidence file.

## Recommendation

Archive this evidence as a PASS WITH POLISH CAVEAT for PR #13 follow-up QA. Runtime and Latest Run `Open Task` navigation are working. Optional frontend polish remains: make the success toast/action more persistent or easier to observe after a successful Run Agent POST, and consider adding an `Open Execution` drawer link only when the run response or safe backend relation provides an execution ID.
