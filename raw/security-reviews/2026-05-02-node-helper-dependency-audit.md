---
type: security review
project: AgentAscend
date: 2026-05-02
status: superseded
tags:
  - agentascend
related:
  - "[[Pump.fun Tokenized Agent Payments]]"
  - "[[Payment Access Control]]"
  - "[[known-issues|Known Issues]]"
---

Status: Superseded for dev/runtime version state by commits `239fa79` and `a8ad3ba`; remaining runtime transitive advisories are accepted/monitored.
Related: [[Pump.fun Tokenized Agent Payments]], [[Payment Access Control]], [[known-issues|Known Issues]]

# 2026-05-02 Node Helper Dependency Audit

Unprocessed/source note for the AgentAscend Node helper dependency audit phase.

Scope: read-only dependency audit and documentation update only. No package files were changed. No install/update/audit-fix/dedupe command was run.

Baseline:
- branch main
- HEAD matched origin/main at 1d24285f25a771f8b5fb249669ba6b58059503d1
- node-payment-helper/node_modules absent
- node-payment-helper/dist absent
- package.json and package-lock.json tracked
- package-lock lockfileVersion 3

Production read-only checks:
- /health HTTP 200
- /openapi.json HTTP 200 valid JSON
- HSTS and standard security headers present
- Pump.fun create/verify routes present
- admin aggregate audit route present

Read-only commands run:
- npm audit --json
- npm outdated --json
- npm view / npm info for selected direct and transitive packages

Audit summary:
- total vulnerabilities: 16
- high: 4
- moderate: 12
- critical: 0

Main findings:
- Runtime chain: @pump-fun/agent-payments-sdk 3.0.2 pulls Anchor/SPL-token/Solana web3 dependencies with high/moderate audit findings. npm audit suggests a SemVer-major downgrade to 1.0.1, which is not safe to apply automatically.
- Runtime direct: @solana/web3.js is locked at latest stable 1.98.4 but still has moderate findings through jayson/rpc-websockets/uuid. npm audit suggests an incompatible downgrade, not a safe fix.
- Dev/test chain: vitest 1.6.1 pulls Vite/Vite-node/esbuild findings. Vitest 4.1.5 appears as a dev-only major update candidate.
- Pump.fun SDK latest observed: 3.0.3. It requires manual compatibility review before any runtime package change.

Recommendation:
Split phase. First consider an owner-approved dev-only Vitest/Vite cleanup. Keep runtime Pump.fun/Solana dependencies unchanged until a separate compatibility review proves safety. Do not run npm audit fix blindly.
