# AgentAscend Purpose

## Overview
AgentAscend is a monetized AI agent platform where tool execution is unlocked only after backend payment verification.

## Core Goals
- Build a self-improving AI agent system.
- Monetize agent usage via SOL and ASND.
- Provide real utility through tools and automation.
- Scale into a multi-agent ecosystem.

## Core Flow
User -> Interface (Telegram/Web) -> Backend Payment Check -> Access Grant -> Tool Execution -> Result

## Key Principles
- Payment before execution (backend-enforced).
- Replay-safe verification (`tx_signature` uniqueness).
- Structured knowledge over raw memory.
- Controlled tool access with auditable grants.
- Continuous improvement through incremental, verifiable changes.

## Notes
- SOL and ASND pricing are environment-driven (`SOL_PRICE_LAMPORTS`, `ASND_PRICE_TOKENS`).
- ASND verification uses receiver token-account delta checks on confirmed Solana transactions.
- Runtime rules and policy files in `agent_runtime/` constrain autonomous operations.
