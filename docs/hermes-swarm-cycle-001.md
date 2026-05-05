# Hermes Swarm Cycle 001

Status: planned, report-only first cycle. Do not run as autonomous production mutation. This cycle can be started manually by the owner and each lane must stop at its safety boundary.

## Global cycle limits
- No push, deploy, env changes, production DB mutation, migrations, index changes, scheduler job changes/runs, /jobs/run-due, Telegram/external sends, payments, Pump.fun verify, wallet actions, access/entitlement mutation, or destructive git operations.
- Reports must avoid secrets, raw DB rows, raw metadata_json, raw payload_json, raw task body, and raw task output.

## 1. Release/Ops Agent
- Task: verify current branch/HEAD/origin/ahead count, live /health, live /openapi.json, Railway deployment status if CLI access is safe, and whether local commits are pending.
- Expected output: PASS/PARTIAL/FAIL deploy/readiness table and exact pending commit list.
- Safety limits: no push/deploy/env changes/log raw dumps.
- Stop condition: live deploy BUILDING/FAILED, git scope mismatch, or any secret exposure risk.

## 2. Backend Forge Agent
- Task: inspect backend backlog and recommend the next smallest runtime/Forge slice.
- Expected output: one proposed TDD slice with files/tests and explicit not-in-scope list.
- Safety limits: no implementation unless separately approved; no scheduler/payment production action.
- Stop condition: slice touches payment/security/runtime-worker push gate without owner approval.

## 3. Frontend/v0 Agent
- Task: generate/refine a v0 prompt based on live Forge backend and the local runtime-worker pending state.
- Expected output: copy-paste v0 prompt and live-vs-pending caveats.
- Safety limits: no Vercel deploy; no fake data/localStorage authority.
- Stop condition: OpenAPI/live backend cannot confirm required route support.

## 4. QA/Security Agent
- Task: summarize current test/dependency/security gates for pending commits.
- Expected output: required local test list, secret scan targets, production-readiness blockers.
- Safety limits: no code changes/dependency upgrades.
- Stop condition: tests require production credentials or payment verification.

## 5. Docs/Memory Agent
- Task: list stale/orphan notes and propose a small cleanup batch.
- Expected output: docs-only cleanup candidate list and MEMORY/wiki patch proposal.
- Safety limits: no .obsidian staging; no code changes.
- Stop condition: cleanup would mix unrelated untracked notes with committed docs.

## 6. Scheduler/Automation Agent
- Task: report current AgentAscend scheduler and Hermes cron posture.
- Expected output: enabled/held scheduler summary, Hermes cron failure category, no-send recovery plan.
- Safety limits: no job changes/runs, no Telegram send.
- Stop condition: recovery requires Hermes code/config/gateway restart or owner-approved canary.

## 7. Payment/Access Agent
- Task: read-only aggregate status if public/auth-safe endpoint is available; otherwise source/doc route check only.
- Expected output: route booleans and aggregate-only access/payment risk summary.
- Safety limits: no payment actions, no Pump.fun verify, no raw tx/user/payment rows.
- Stop condition: check would require auth secrets, fake transaction, real transaction, or DB mutation.

## 8. Marketing/Community Agent
- Task: draft an internal soft-launch update only.
- Expected output: draft text plus factual caveats: runtime-worker local/not-pushed unless owner later pushes.
- Safety limits: no external posting/sending.
- Stop condition: draft depends on unverified product or payment claims.
