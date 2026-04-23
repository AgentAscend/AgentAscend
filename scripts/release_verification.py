#!/usr/bin/env python3
"""Release verification for AgentAscend.

Covers:
1) Payment matrix regression checks
2) Telegram unpaid/paid command flow
3) Replay protection assertion on reused tx_signature
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
import time
import types
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "backend/app/db/agentascend.db"


class CheckResult:
    def __init__(self, name: str, ok: bool, detail: str):
        self.name = name
        self.ok = ok
        self.detail = detail


def install_fastapi_stub():
    fastapi = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class APIRouter:
        def post(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def get(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

    class FastAPI:
        def on_event(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

        def include_router(self, *_args, **_kwargs):
            return None

    fastapi.HTTPException = HTTPException
    fastapi.APIRouter = APIRouter
    fastapi.FastAPI = FastAPI
    sys.modules["fastapi"] = fastapi
    return HTTPException


def load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, str(BASE_DIR / rel_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_payment_matrix(max_attempts: int = 3) -> CheckResult:
    cmd = [sys.executable, "scripts/verify_payments_matrix.py"]
    for attempt in range(1, max_attempts + 1):
        proc = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
        out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        if proc.returncode == 0:
            return CheckResult("payment_matrix", True, "matrix passed")

        if "429" in out and attempt < max_attempts:
            time.sleep(attempt * 2)
            continue

        return CheckResult("payment_matrix", False, out.strip()[-5000:])

    return CheckResult("payment_matrix", False, "matrix failed after retries")


def telegram_flow_check() -> CheckResult:
    sys.path.insert(0, str(BASE_DIR))
    from backend.app.db.session import init_db
    from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, grant_access

    init_db()
    telegram_mod = load_module("telegram_mod", "backend/app/routes/telegram.py")

    os.environ["SOLANA_RECEIVER_WALLET"] = os.getenv(
        "SOLANA_RECEIVER_WALLET", "DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D"
    )

    user_num = int(time.time())

    unpaid = telegram_mod.telegram_command(
        telegram_mod.TelegramCommandRequest(telegram_user_id=user_num, chat_id=999, command="/random")
    )
    if unpaid.get("status") != "payment_required" or not unpaid.get("payment"):
        return CheckResult("telegram_unpaid", False, f"unexpected unpaid response: {unpaid}")

    user_id = unpaid.get("user_id")
    grant_access(user_id, FEATURE_RANDOM_NUMBER)

    paid = telegram_mod.telegram_command(
        telegram_mod.TelegramCommandRequest(telegram_user_id=user_num, chat_id=999, command="/random")
    )
    if paid.get("status") != "success" or not isinstance(paid.get("result"), int):
        return CheckResult("telegram_paid", False, f"unexpected paid response: {paid}")

    return CheckResult("telegram_flow", True, f"user={user_id}")


def replay_assertion(HTTPException) -> CheckResult:
    sys.path.insert(0, str(BASE_DIR))
    from backend.app.db.session import init_db

    init_db()

    replay_sig = os.getenv("TEST_REPLAY_SIG", "").strip()
    token = os.getenv("TEST_REPLAY_TOKEN", "").strip().upper()

    if not replay_sig:
        if not DB_PATH.exists():
            return CheckResult("replay_assertion", False, f"DB not found: {DB_PATH}")
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                """
                SELECT tx_signature, token
                FROM payments
                WHERE tx_signature IS NOT NULL AND tx_signature != ''
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if not row:
            return CheckResult(
                "replay_assertion",
                False,
                "No payment tx_signature found. Set TEST_REPLAY_SIG and TEST_REPLAY_TOKEN to run replay check.",
            )
        replay_sig, token = row[0], (row[1] or "").upper()

    if token not in {"SOL", "ASND"}:
        return CheckResult("replay_assertion", False, f"Unsupported replay token: {token}")

    payments_mod = load_module("payments_mod", "backend/app/routes/payments.py")

    # Stub chain-facing helpers so this replay check is deterministic and offline.
    payments_mod.fetch_transaction = lambda _sig: {"meta": {"err": None}}
    os.environ["SOLANA_RECEIVER_WALLET"] = os.getenv(
        "SOLANA_RECEIVER_WALLET", "DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D"
    )

    if token == "SOL":
        os.environ["SOL_PRICE_LAMPORTS"] = os.getenv("SOL_PRICE_LAMPORTS", "100000000")
        payments_mod.received_lamports_for_wallet = lambda _tx, _wallet: int(os.getenv("SOL_PRICE_LAMPORTS", "100000000"))
    else:
        os.environ["ASND_MINT_ADDRESS"] = os.getenv(
            "ASND_MINT_ADDRESS", "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump"
        )
        os.environ["ASND_PRICE_TOKENS"] = os.getenv("ASND_PRICE_TOKENS", "100")
        payments_mod.get_receiver_token_account = lambda _wallet, _mint: os.getenv(
            "ASND_RECEIVER_TOKEN_ACCOUNT", "2QNQhJRTcERXwwUs8jVqTGt5wJXYNHPfTw1wGEhuHW4g"
        )
        payments_mod.received_token_amount_for_wallet = lambda _tx, _acct, _mint: 999999

    try:
        payments_mod.verify_payment(
            payments_mod.PaymentVerifyRequest(user_id="release_replay_user", tx_signature=replay_sig, token=token)
        )
        return CheckResult("replay_assertion", False, "verify_payment unexpectedly succeeded on reused signature")
    except HTTPException as exc:
        if exc.status_code == 400 and "already used" in str(exc.detail).lower():
            return CheckResult("replay_assertion", True, f"{exc.status_code} {exc.detail}")
        return CheckResult("replay_assertion", False, f"unexpected error: {exc.status_code} {exc.detail}")


def main() -> int:
    HTTPException = install_fastapi_stub()

    checks = [
        run_payment_matrix(),
        telegram_flow_check(),
        replay_assertion(HTTPException),
    ]

    print("Release verification results:")
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"- {status}: {check.name} -> {check.detail}")

    failed = [c for c in checks if not c.ok]
    if failed:
        print(f"\nFAILED checks: {len(failed)}")
        return 1

    print("\nAll release verification checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
