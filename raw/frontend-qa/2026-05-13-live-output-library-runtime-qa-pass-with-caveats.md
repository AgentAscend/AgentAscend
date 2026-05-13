# Live Output Library UX and signed-in runtime QA PASS WITH CAVEATS — 2026-05-13

## Summary
Live Playwright QA completed against `https://www.agentascend.ai` using a local no-sandbox Playwright harness. Verdict: **PASS WITH CAVEATS**.

This QA verified the deployed Output Library UX patch and the core signed-in runtime loop:

Throwaway signup → Ascend Forge create → Run Agent → Task → Execution → Output → Output preview.

## Scope covered
- Public marketing, legal, and auth routes.
- Signed-in app routes.
- Throwaway account signup.
- Ascend Forge agent creation.
- Agent options menu → Run Agent.
- Backend task, execution, and output verification.
- Output Library search/export/bulk/preview behavior.
- Safe clicking across settings, workflows, marketplace, token, tasks, and executions where appropriate.

## QA artifacts
Local artifacts from the QA run:

- Main result JSON: `/tmp/agentascend-browser-qa/live-full-qa-result.json`
- Focused runtime run result: `/tmp/agentascend-browser-qa/focused-run-result.json`
- Output preview result: `/tmp/agentascend-browser-qa/output-preview-result.json`
- Screenshots directory: `/tmp/agentascend-browser-qa/screenshots`

These artifacts are local QA evidence only and were not copied into this note because raw private bodies, cookies, session values, and generated output content must not be archived.

## Public route smoke
The following routes returned HTTP 200 and rendered:

- `/`
- `/platform`
- `/token`
- `/community`
- `/vision`
- `/privacy`
- `/terms`
- `/auth/signin`
- `/auth/signup`

## Signed-in app route smoke
The following routes returned HTTP 200 and rendered the authenticated app shell:

- `/app/overview`
- `/app/agents`
- `/app/tasks`
- `/app/outputs`
- `/app/executions`
- `/app/workflows`
- `/app/marketplace`
- `/app/settings`
- `/app/token`

## Ascend Forge creation
The throwaway-account QA flow:

1. Opened `/app/agents`.
2. Clicked **Open Ascend Forge**.
3. Filled agent name and mission.
4. Selected the Research category.
5. Clicked **Create Basic Agent**.
6. Confirmed `POST /agents` returned HTTP 200.
7. Confirmed backend `/agents` listed the created throwaway agent.

## Run Agent and backend source-of-truth verification
The focused runtime flow:

1. Opened the created agent card menu via the vertical ellipsis.
2. Clicked **Run Agent**.
3. Confirmed `POST /agents/{agent_id}/run` returned HTTP 200.
4. Confirmed backend source-of-truth after run:
   - `/agents`: HTTP 200, count 1
   - `/tasks?user_id=<throwaway>`: HTTP 200, count 1
   - `/executions/me?limit=20`: HTTP 200, count 1
   - `/outputs?user_id=<throwaway>`: HTTP 200, count 1
   - `/executions/summary`: HTTP 200
   - `/dashboard/command-center`: HTTP 200

## Post-run UI evidence
After Run Agent:

- `/app/tasks` showed task queue data backed by the run.
- `/app/executions` showed Total Executions 1 and Completed 1.
- `/app/outputs` showed an output card for the manual run.
- `/app/agents` showed the created QA agent.

## Output Library UX verification
The live Output Library patch passed browser QA:

- “Outputs are live” info card was visible.
- “Search filters loaded backend outputs locally” was visible.
- Total Outputs showed 1 for the throwaway account.
- The output card rendered backend output metadata.
- The task link was visible.
- **Export All** was disabled.
- **Load More Outputs** was disabled.
- Search input worked for local loaded-list filtering.
- **Preview** opened the output modal.
- “Backend output preview” was visible.
- No output-page console errors were observed.
- No output-page runtime/page errors were observed.

## Safety result
No dangerous production actions were performed during this QA:

- No payment routes called.
- No Pump.fun create/verify called.
- No wallet transaction attempted.
- No scheduler jobs run.
- No `/jobs/run-due` call.
- No admin audit endpoints called.
- No Telegram or external messages sent.
- No cookies, session values, passwords, raw private responses, raw database rows, raw task body/output, raw metadata/payload JSON, private wallet data, or signing payloads were archived.

## Caveats
- Three throwaway QA accounts were created.
- Three throwaway agents were created.
- Two agents were run successfully.
- Two task/execution/output sets were generated.
- Throwaway QA resources remain in production and must not be deleted without a separate owner-approved cleanup plan.
- The initial broad script had a selector miss for **Run Agent**; a focused rerun confirmed **Run Agent** works from the vertical ellipsis menu.
- Payment, wallet, and Pump.fun flows were intentionally not tested in this QA.

## Relationships
- [[current-project-state|Current Project State]]
- [[frontend-v0-workflow|Frontend v0 Workflow]]
- [[Execution Ledger]]
- [[known-issues|Known Issues]]
