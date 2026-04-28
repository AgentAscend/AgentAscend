#!/usr/bin/env python3
"""Verify the Pump.fun Node payment helper CLI is built for runtime.

This script is intentionally secret-safe: it checks paths and package metadata only.
It does not read or print environment variables, RPC URLs, database URLs, request
payloads, subprocess output, or other secret-bearing runtime data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER_DIR = ROOT / "node-payment-helper"
PACKAGE_JSON = HELPER_DIR / "package.json"
PACKAGE_LOCK = HELPER_DIR / "package-lock.json"
DIST_CLI = HELPER_DIR / "dist" / "cli.js"


def _fail(message: str) -> int:
    print(f"node_payment_helper_runtime=FAIL {message}")
    return 1


def main() -> int:
    if not HELPER_DIR.is_dir():
        return _fail("helper_dir_missing")
    if not PACKAGE_JSON.is_file():
        return _fail("package_json_missing")
    if not PACKAGE_LOCK.is_file():
        return _fail("package_lock_missing")

    try:
        package = json.loads(PACKAGE_JSON.read_text())
    except json.JSONDecodeError:
        return _fail("package_json_invalid")

    bin_mapping = package.get("bin")
    expected_bin = "dist/cli.js"
    if not isinstance(bin_mapping, dict) or bin_mapping.get("agentascend-payment-helper") != expected_bin:
        return _fail("cli_bin_mapping_missing")

    if not DIST_CLI.is_file():
        return _fail("dist_cli_missing")

    content = DIST_CLI.read_text(errors="ignore")
    if "buildPaymentTransaction" not in content or "validateInvoicePayment" not in content:
        return _fail("dist_cli_unexpected_content")

    print("node_payment_helper_runtime=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
