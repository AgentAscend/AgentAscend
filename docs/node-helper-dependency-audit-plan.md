# Node Helper Dependency Audit Cleanup Plan

Related: [[Payment Access Control]], [[Pump.fun Tokenized Agent Payments]], [[Ops Runbook]], [[Known Issues]]

## Status
Next hardening phase after replay-index preflight PASS. Planning only. Prior `npm audit --json` was read-only. No `npm audit fix`, package upgrade, lockfile rewrite, or helper code change has been approved by this document.

## Current direct dependencies
- `@pump-fun/agent-payments-sdk` pinned at `3.0.2`.
- `@solana/web3.js` declared as `^1.98.0`.
- Dev stack includes TypeScript and Vitest.

## Vulnerability summary
`npm audit --json` reported 16 vulnerabilities: 12 moderate and 4 high.

High-risk chain:
- `@pump-fun/agent-payments-sdk` is direct and reported high because it pulls vulnerable Solana/Anchor dependencies. Audit suggests `@pump-fun/agent-payments-sdk@1.0.1` as a SemVer-major downgrade from 3.0.2, so this is not safe to apply automatically and may break Pump.fun SDK compatibility.
- `@solana/spl-token`, `@solana/buffer-layout-utils`, and `bigint-buffer` are transitive high findings under the Pump.fun SDK/SPL-token tree.

Moderate chain:
- `@solana/web3.js` is direct and moderate through `jayson`, `rpc-websockets`, and `uuid`. Audit suggests `@solana/web3.js@0.9.2` as SemVer-major and likely incompatible with current SDK usage.
- `vitest` is direct dev dependency and moderate through `vite`, `vite-node`, and `esbuild`. Audit suggests `vitest@4.1.5`, SemVer-major, likely manageable but should be tested separately.
- Anchor/Borsh packages inherit Solana web3 findings transitively.

## Cleanup strategy
1. Split runtime vs dev dependency remediation.
2. First test whether updating Vitest/Vite dev dependencies alone removes the dev-server findings without touching Pump.fun runtime behavior.
3. For runtime findings, check Pump.fun SDK release notes and available versions above 3.0.2. Do not downgrade to 1.0.1 without explicit SDK compatibility review.
4. If no safe Pump.fun SDK upgrade exists, document accepted risk and compensate by keeping the helper isolated, minimal, and server-side only.
5. After any dependency change, run helper build/typecheck/tests and a focused backend helper-service test suite.

## Future owner-approved cleanup prompt
`I approve a docs-first and then code-reviewed dependency cleanup slice for node-payment-helper. Do not run npm audit fix automatically. First inspect available @pump-fun/agent-payments-sdk, @solana/web3.js, vitest, and vite versions and propose a compatibility-safe upgrade matrix. Then, if a low-risk dev-only update is available, update only package.json/package-lock.json, run npm ci, npm audit --json, npm run typecheck, npm run build, npm test, and relevant backend helper tests. Do not change payment verification semantics, do not call Pump.fun verify, do not create payment intents, and do not touch production.`


## Scope guard for next phase
- Do not run `npm audit fix` automatically.
- Do not call Pump.fun verify.
- Do not create payment intents.
- Do not run payments or sign/send transactions.
- Do not mutate production DB or scheduler state.
- Do not change backend payment verification semantics while auditing dependencies.
- Prefer docs-first compatibility matrix, then a minimal dev-only dependency update if low risk.
