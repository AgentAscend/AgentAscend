import json
import os
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
NODE_HELPER_DIR = REPO_ROOT / "node-payment-helper"
NODE_HELPER_CLI = NODE_HELPER_DIR / "dist" / "cli.js"
DEFAULT_TIMEOUT_SECONDS = 15
FORBIDDEN_INPUT_FIELDS = {"rpcUrl", "privateKey", "secretKey"}
SAFE_NODE_HELPER_ERROR_CODES = {
    "INVALID_USERWALLET",
    "INVALID_AGENTTOKENMINT",
    "INVALID_CURRENCYMINT",
    "INVALID_AMOUNT",
    "INVALID_MEMO",
    "INVALID_STARTTIME",
    "INVALID_ENDTIME",
    "INVALID_TIME_RANGE",
    "FORBIDDEN_FIELD",
    "MISSING_SOLANA_RPC_URL",
    "BUILD_PAYMENT_TRANSACTION_FAILED",
    "VALIDATE_INVOICE_PAYMENT_FAILED",
    "INVALID_JSON",
    "INVALID_REQUEST",
    "UNKNOWN_COMMAND",
    "NODE_HELPER_INVALID_RESPONSE",
    "NODE_HELPER_TIMEOUT",
    "NODE_HELPER_PROCESS_FAILED",
}


def _safe_error(error_code: str) -> dict[str, Any]:
    if error_code not in SAFE_NODE_HELPER_ERROR_CODES:
        return {"ok": False, "errorCode": "NODE_HELPER_PROCESS_FAILED"}
    return {"ok": False, "errorCode": error_code}


def _has_forbidden_input(input_payload: dict[str, Any]) -> bool:
    return any(field in input_payload for field in FORBIDDEN_INPUT_FIELDS)


def _node_command() -> list[str]:
    node_binary = os.getenv("NODE_BINARY", "node")
    return [node_binary, str(NODE_HELPER_CLI)]


def _sanitize_helper_result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return _safe_error("NODE_HELPER_INVALID_RESPONSE")

    if value.get("ok") is True:
        safe_result: dict[str, Any] = {"ok": True}
        if isinstance(value.get("txBase64"), str):
            safe_result["txBase64"] = value["txBase64"]
        if isinstance(value.get("invoiceId"), str):
            safe_result["invoiceId"] = value["invoiceId"]
        if isinstance(value.get("verified"), bool):
            safe_result["verified"] = value["verified"]
        return safe_result

    if value.get("ok") is False and isinstance(value.get("errorCode"), str):
        return _safe_error(value["errorCode"])

    return _safe_error("NODE_HELPER_INVALID_RESPONSE")


def _call_node_helper(command: str, input_payload: dict[str, Any]) -> dict[str, Any]:
    if _has_forbidden_input(input_payload):
        return _safe_error("FORBIDDEN_FIELD")

    request = {"command": command, "input": input_payload}

    try:
        completed = subprocess.run(
            _node_command(),
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            cwd=REPO_ROOT,
            env=os.environ.copy(),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _safe_error("NODE_HELPER_TIMEOUT")
    except OSError:
        return _safe_error("NODE_HELPER_PROCESS_FAILED")

    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return _safe_error("NODE_HELPER_INVALID_RESPONSE")

    return _sanitize_helper_result(parsed)


def build_payment_transaction(input_payload: dict[str, Any]) -> dict[str, Any]:
    return _call_node_helper("buildPaymentTransaction", input_payload)


def validate_invoice_payment(input_payload: dict[str, Any]) -> dict[str, Any]:
    return _call_node_helper("validateInvoicePayment", input_payload)
