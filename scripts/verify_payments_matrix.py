#!/usr/bin/env python3
"""Quick payment-route verification matrix for AgentAscend.

Runs non-destructive checks for validation and config guardrails.
Optional: set TEST_ASND_SUCCESS_SIG to validate a real ASND signature path.
"""

import os
import sys
import types
import importlib.util


def _install_fastapi_stub():
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

    fastapi.HTTPException = HTTPException
    fastapi.APIRouter = APIRouter
    sys.modules["fastapi"] = fastapi
    return HTTPException


def _load_payments_module():
    spec = importlib.util.spec_from_file_location("payments_mod", "backend/app/routes/payments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    HTTPException = _install_fastapi_stub()

    sys.path.insert(0, ".")
    from backend.app.db.session import init_db

    init_db()
    mod = _load_payments_module()

    # Baseline env for checks
    os.environ["SOLANA_RPC_URL"] = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    os.environ["SOLANA_RECEIVER_WALLET"] = os.getenv(
        "SOLANA_RECEIVER_WALLET", "DTC729KJNSuCqGgFUYyYEPQAaiajFMvSerrAmyn84K6D"
    )
    os.environ["ASND_MINT_ADDRESS"] = os.getenv(
        "ASND_MINT_ADDRESS", "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump"
    )

    checks = []

    # 1) Unsupported token
    try:
        mod.create_payment(types.SimpleNamespace(user_id="matrix_user", token="BAD"))
        checks.append(("unsupported_token", False, "expected HTTP 400"))
    except HTTPException as e:
        checks.append(("unsupported_token", e.status_code == 400, f"{e.status_code} {e.detail}"))

    # 2) Invalid signature format
    try:
        mod.verify_payment(mod.PaymentVerifyRequest(user_id="matrix_user", tx_signature="not-a-real-signature", token="SOL"))
        checks.append(("invalid_signature", False, "expected HTTP 400"))
    except HTTPException as e:
        checks.append(("invalid_signature", e.status_code == 400, f"{e.status_code} {e.detail}"))

    # 3) Missing ASND_MINT_ADDRESS guardrail
    # Use a known chain-valid signature so execution reaches ASND env checks.
    chain_valid_sig = os.getenv(
        "TEST_CHAIN_VALID_SIG",
        "5R3UuHFYw2beVSYKaff87w93is2Rd84N2egqAT4eaS5ZJW2EHQuPr3e4jhSLo7EGyVqG3XCE635rNnxVjUMHpyoa",
    )
    old_mint = os.environ.pop("ASND_MINT_ADDRESS", None)
    try:
        mod.verify_payment(mod.PaymentVerifyRequest(user_id="matrix_user", tx_signature=chain_valid_sig, token="ASND"))
        checks.append(("missing_asnd_mint", False, "expected HTTP 500"))
    except HTTPException as e:
        checks.append(("missing_asnd_mint", e.status_code == 500, f"{e.status_code} {e.detail}"))
    finally:
        if old_mint is not None:
            os.environ["ASND_MINT_ADDRESS"] = old_mint

    # 4) Chain path with fake format-valid signature should fail cleanly
    try:
        mod.verify_payment(mod.PaymentVerifyRequest(user_id="matrix_user", tx_signature="4" * 88, token="ASND"))
        checks.append(("fake_sig_chain_path", False, "expected HTTP 400"))
    except HTTPException as e:
        checks.append(("fake_sig_chain_path", e.status_code == 400, f"{e.status_code} {e.detail}"))

    # 5) Optional: real ASND success signature
    success_sig = os.getenv("TEST_ASND_SUCCESS_SIG", "").strip()
    if success_sig:
        try:
            result = mod.verify_payment(
                mod.PaymentVerifyRequest(user_id="matrix_success_user", tx_signature=success_sig, token="ASND")
            )
            ok = result.get("status") == "payment_verified"
            checks.append(("real_asnd_success_sig", ok, str(result)))
        except HTTPException as e:
            checks.append(("real_asnd_success_sig", False, f"{e.status_code} {e.detail}"))

    failed = [c for c in checks if not c[1]]

    print("Payment verification matrix results:")
    for name, ok, detail in checks:
        status = "PASS" if ok else "FAIL"
        print(f"- {status}: {name} -> {detail}")

    if failed:
        print(f"\nFAILED checks: {len(failed)}")
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
