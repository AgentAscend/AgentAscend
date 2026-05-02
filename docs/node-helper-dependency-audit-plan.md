# Node Helper Dependency Audit Cleanup Plan

Related: [[Payment Access Control]], [[Pump.fun Tokenized Agent Payments]], [[Ops Runbook]], [[Known Issues]]

## Status
2026-05-02 read-only dependency audit completed. No package changes were made.

`npm audit --json`, `npm outdated --json`, and targeted `npm view`/`npm info` checks were run without installing, updating, deduping, or rewriting any lockfile. Do not run `npm audit fix` automatically.

## Package manager and lock status
- Package manager: npm.
- Helper package: `node-payment-helper`.
- Committed lockfile: `node-payment-helper/package-lock.json`, lockfileVersion 3.
- `node-payment-helper/package.json` and `node-payment-helper/package-lock.json` are tracked and expected.
- `node-payment-helper/node_modules` was absent during baseline.
- `node-payment-helper/dist` was absent during baseline.
- No tracked `dist` or `node_modules` files exist.

## Current direct dependencies
Runtime:
- `@pump-fun/agent-payments-sdk`: pinned at `3.0.2`; npm latest observed: `3.0.3`.
- `@solana/web3.js`: declared as `^1.98.0`; lock resolves to `1.98.4`; npm latest stable observed: `1.98.4`.

Dev:
- `@types/node`: declared as `^20.12.12`; lock resolves to `20.19.39`.
- `typescript`: declared as `^5.4.5`; lock resolves to `5.9.3`.
- `vitest`: declared as `^1.6.0`; lock resolves to `1.6.1`; npm latest observed: `4.1.5`.

Important transitive runtime packages in lock:
- `@coral-xyz/anchor`: `0.31.1` via Pump.fun SDK; npm latest observed: `0.32.1`.
- `@solana/spl-token`: `0.4.14` via Pump.fun SDK; latest observed: `0.4.14`.
- `@solana/buffer-layout-utils`: `0.2.0` via SPL-token.
- `bigint-buffer`: `1.1.5` via SPL-token path.
- `jayson`: `4.3.0`, `rpc-websockets`: `9.3.8`, and `uuid`: `8.3.2` via Solana web3 path.

## Audit summary — 2026-05-02
`npm audit --json` reported the same high-level count as the prior signal:

- total: 16
- high: 4
- moderate: 12
- critical: 0
- low: 0

No serious new production-specific exploit path was proven during this docs-first audit, but runtime dependency risk remains because the helper imports Pump.fun SDK and Solana web3 in production code.

## Dependency exposure
Runtime helper source imports:
- `@solana/web3.js` directly in `src/pumpfun-helper.ts` for `Connection`, `PublicKey`, `Transaction`, invoice PDA checks, transaction lookup, and transaction construction.
- `@pump-fun/agent-payments-sdk` through `src/sdk-loader.ts` for `PumpAgent`, `buildAcceptPaymentInstructions`, `validateInvoicePayment`, and `getInvoiceIdPDA`.

Test-only/dev usage:
- `vitest` is used by test files and `vitest.config.ts`.
- Vite/Vite-node/esbuild findings are dev/test-runner-path findings, not production helper runtime imports.

Compatibility-sensitive surfaces:
- transaction building
- signature binding
- invoice PDA derivation
- Pump.fun `validateInvoicePayment`
- Solana `Connection.getSignaturesForAddress`
- Solana `Connection.getTransaction`
- `PublicKey` parsing/comparison

## Upgrade matrix

| package | direct/transitive | runtime/dev | severity | current version | patched/latest version if known | fix type | risk | Pump.fun/Solana compatibility risk | recommendation |
|---|---|---:|---|---|---|---|---|---|---|
| `@pump-fun/agent-payments-sdk` | direct | runtime | high via transitive chain | `3.0.2` | latest `3.0.3`; audit suggests `1.0.1` | audit force only / unsafe downgrade; possible patch candidate `3.0.3` needs review | high | high: SDK owns `PumpAgent`, invoice PDA helper, transaction instructions, and validation semantics | needs manual review; do not auto-fix; inspect 3.0.3 changelog/API before any update |
| `@solana/web3.js` | direct | runtime | moderate via `jayson`/`rpc-websockets`/`uuid` | `1.98.4` locked | latest stable `1.98.4`; audit suggests `0.0.3` | no safe fix from current stable; audit suggestion is incompatible downgrade | high | high: direct runtime dependency for transaction building, signature lookup, and transaction fetching | accept/monitor temporarily; do not downgrade |
| `@solana/spl-token` | transitive via Pump.fun SDK | runtime | high via subchain | `0.4.14` | latest `0.4.14` | no direct safe patch available | medium/high | medium/high because Pump.fun SDK depends on SPL-token tree | accept/monitor unless Pump.fun SDK releases safer dependency tree |
| `@solana/buffer-layout-utils` | transitive via SPL-token | runtime | high via `bigint-buffer`/web3 chain | `0.2.0` | no safe direct fix identified | no direct safe fix | medium | medium: transitive encoding/layout utility under SPL-token | accept/monitor; avoid overrides without compatibility tests |
| `bigint-buffer` | transitive via SPL-token path | runtime | high | `1.1.5` | no safe direct fix identified by audit except Pump.fun SDK downgrade | audit force only / unsafe downgrade | medium | medium: low-level conversion package under Solana token path | accept/monitor; do not override blindly |
| `@coral-xyz/anchor` | transitive via Pump.fun SDK | runtime | moderate via borsh/web3 chain | `0.31.1` | latest `0.32.1` | possible minor via upstream only | medium | medium/high: Pump.fun SDK pins range and may expect Anchor 0.31 behavior | needs manual review; prefer Pump.fun SDK-managed update |
| `@coral-xyz/borsh` | transitive via Anchor | runtime | moderate via web3 chain | `0.31.1` | tied to Anchor | upstream-managed | medium | medium: serialization compatibility risk | accept/monitor; do not force override |
| `jayson` | transitive via web3 | runtime | moderate via `uuid` | `4.3.0` | no safe direct fix through current web3 stable | no safe fix | medium | medium: RPC client path under web3 | accept/monitor pending Solana web3 fix |
| `rpc-websockets` | transitive via web3 | runtime | moderate via `uuid` | `9.3.8` | no safe direct fix through current web3 stable | no safe fix | medium | medium: websocket/RPC path under web3 | accept/monitor pending Solana web3 fix |
| `uuid` | transitive via jayson/rpc-websockets | runtime | moderate | `8.3.2` | advisory fixed at newer major, but constrained transitively | no safe direct fix | medium | low/medium: transitive RPC package path; exploit requires vulnerable buffer use path | accept/monitor; no direct override without tests |
| `vitest` | direct | dev | moderate via Vite/Vite-node/esbuild | `1.6.1` | latest `4.1.5` | major | medium | low: test runner only, but may require test/config changes | dev-only update candidate in separate approved phase |
| `vite` | transitive via Vitest | dev | moderate | `5.4.21` | latest `8.0.10`; Vitest 4 uses Vite 6/7/8 range | major through Vitest | low/medium | low for Pump.fun runtime; possible test tooling breakage | dev-only update candidate with tests |
| `vite-node` | transitive via Vitest | dev | moderate | `1.6.1` | tied to Vitest 4.1.5 | major through Vitest | low/medium | low for Pump.fun runtime | dev-only update candidate with tests |
| `esbuild` | transitive via Vite | dev | moderate | `0.21.5` | newer via Vite/Vitest major | major through Vitest | low | none for production helper runtime | dev-only update candidate with tests |
| `typescript` | direct | dev/build | none from audit | `5.9.3` locked | latest observed `6.0.3` | major | medium | low direct runtime risk; could affect type/build output | do not include in first cleanup unless needed |
| `@types/node` | direct | dev/types | none from audit | `20.19.39` locked | latest observed `25.6.0` | major runtime-target mismatch risk | medium | low direct runtime risk; may conflict with Node target expectations | do not include in first cleanup unless needed |

## Recommended cleanup sequence
Recommended option: split phase.

1. Dev-only cleanup first, after explicit owner approval.
   - Candidate: update only Vitest/Vite test-runner stack if a compatibility-safe version plan is accepted.
   - Do not touch runtime dependencies in the same commit.
   - Required verification: `npm test`, `npm run typecheck`, `npm run build`, focused Python backend helper tests, and full pytest if practical.

2. Runtime dependency review later.
   - Investigate Pump.fun SDK `3.0.3` before changing from `3.0.2`.
   - Confirm whether API exports and semantics remain compatible for `PumpAgent`, `getInvoiceIdPDA`, `buildAcceptPaymentInstructions`, and `validateInvoicePayment`.
   - Do not apply npm audit's suggested Pump.fun SDK downgrade to `1.0.1`.
   - Do not downgrade Solana web3 to `0.0.3` or any audit-forced incompatible version.
   - Avoid dependency overrides unless a targeted compatibility test proves safety.

3. Accepted/compensated risk until runtime fix exists.
   - Keep the helper isolated and server-side.
   - Keep payment verification fail-closed.
   - Never expose unsigned/signed transaction payloads or raw RPC/private data in logs.
   - Continue monitoring Pump.fun SDK and Solana web3 releases for a safe runtime fix.

## Required tests for any future approved package update
Run from `node-payment-helper` after the approved package change:

```bash
npm test
npm run typecheck
npm run build
```

Run from repo root:

```bash
.venv/bin/python -m pytest tests/test_pumpfun_payment_routes.py tests/test_pumpfun_node_helper_service.py -q
.venv/bin/python -m pytest -q
```

If the change is pushed/deployed after approval, run production smoke checks only:
- `/health` HTTP 200
- `/openapi.json` valid JSON
- Pump.fun routes present
- no payment actions and no Pump.fun verify calls unless separately approved

## Future owner approval sentence before package changes
`I approve a dev-only Node helper dependency cleanup now: update only the Vitest/Vite test-runner dependency stack in node-payment-helper package.json/package-lock.json, do not touch Pump.fun SDK or Solana runtime dependencies, do not run npm audit fix, then run npm test, npm run typecheck, npm run build, tests/test_pumpfun_payment_routes.py, tests/test_pumpfun_node_helper_service.py, and full pytest if practical.`

A separate approval is required for any runtime dependency change:

`I approve a runtime Node helper dependency compatibility spike now: inspect and update only the explicitly named Pump.fun/Solana runtime package versions after confirming API compatibility, do not run npm audit fix, do not call Pump.fun verify, do not create payment intents, and run the full helper and backend payment regression suite before any push.`

## Scope guard
- Do not run `npm audit fix` automatically.
- Do not install, update, dedupe, or rewrite lockfiles without explicit owner approval.
- Do not call Pump.fun verify.
- Do not create payment intents.
- Do not run payments or sign/send transactions.
- Do not mutate production DB or scheduler state.
- Do not change backend payment verification semantics while auditing dependencies.
