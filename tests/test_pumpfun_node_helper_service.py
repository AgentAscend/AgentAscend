import json
import subprocess

import pytest

from backend.app.services import pumpfun_node_helper


VALID_INPUT = {
    "userWallet": "11111111111111111111111111111111",
    "agentTokenMint": "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump",
    "currencyMint": "So11111111111111111111111111111111111111112",
    "amount": 100000000,
    "memo": 123456789,
    "startTime": 1_700_000_000,
    "endTime": 1_700_086_400,
}


def test_build_payment_transaction_calls_node_cli_with_sanitized_json(monkeypatch):
    calls = []

    def fake_run(command, *, input, text, capture_output, timeout, cwd, env, check):
        calls.append(
            {
                "command": command,
                "input": input,
                "text": text,
                "capture_output": capture_output,
                "timeout": timeout,
                "cwd": cwd,
                "env": env,
                "check": check,
            }
        )
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "ok": True,
                    "txBase64": "base64-unsigned-transaction",
                    "invoiceId": "invoice-id-safe-base58",
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(pumpfun_node_helper.subprocess, "run", fake_run)

    result = pumpfun_node_helper.build_payment_transaction(VALID_INPUT)

    assert result == {
        "ok": True,
        "txBase64": "base64-unsigned-transaction",
        "invoiceId": "invoice-id-safe-base58",
    }
    assert len(calls) == 1
    request = json.loads(calls[0]["input"])
    assert request == {"command": "buildPaymentTransaction", "input": VALID_INPUT}
    assert calls[0]["capture_output"] is True
    assert calls[0]["check"] is False
    assert "SOLANA_RPC_URL" not in json.dumps(result)


def test_validate_invoice_payment_preserves_safe_helper_error_without_stderr_leak(monkeypatch):
    def fake_run(command, *, input, text, capture_output, timeout, cwd, env, check):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=json.dumps({"ok": False, "errorCode": "VALIDATE_INVOICE_PAYMENT_FAILED"}),
            stderr="raw rpc failure https://quicknode.example.invalid/secret-token",
        )

    monkeypatch.setattr(pumpfun_node_helper.subprocess, "run", fake_run)

    result = pumpfun_node_helper.validate_invoice_payment(VALID_INPUT)

    assert result == {"ok": False, "errorCode": "VALIDATE_INVOICE_PAYMENT_FAILED"}
    assert "quicknode" not in json.dumps(result).lower()
    assert "raw rpc" not in json.dumps(result).lower()


def test_wrapper_rejects_forbidden_input_before_subprocess(monkeypatch):
    def fake_run(*args, **kwargs):
        raise AssertionError("subprocess must not run for forbidden input")

    monkeypatch.setattr(pumpfun_node_helper.subprocess, "run", fake_run)

    assert pumpfun_node_helper.build_payment_transaction({**VALID_INPUT, "rpcUrl": "https://attacker"}) == {
        "ok": False,
        "errorCode": "FORBIDDEN_FIELD",
    }
    assert pumpfun_node_helper.validate_invoice_payment({**VALID_INPUT, "privateKey": "secret"}) == {
        "ok": False,
        "errorCode": "FORBIDDEN_FIELD",
    }
    assert pumpfun_node_helper.validate_invoice_payment({**VALID_INPUT, "secretKey": "secret"}) == {
        "ok": False,
        "errorCode": "FORBIDDEN_FIELD",
    }


def test_wrapper_returns_safe_error_for_invalid_helper_stdout(monkeypatch):
    def fake_run(command, *, input, text, capture_output, timeout, cwd, env, check):
        return subprocess.CompletedProcess(
            command,
            1,
            stdout="not json https://quicknode.example.invalid/secret-token",
            stderr="raw error body",
        )

    monkeypatch.setattr(pumpfun_node_helper.subprocess, "run", fake_run)

    result = pumpfun_node_helper.build_payment_transaction(VALID_INPUT)

    assert result == {"ok": False, "errorCode": "NODE_HELPER_INVALID_RESPONSE"}
    assert "quicknode" not in json.dumps(result).lower()
    assert "raw error" not in json.dumps(result).lower()


def test_wrapper_returns_safe_error_for_timeout(monkeypatch):
    def fake_run(command, *, input, text, capture_output, timeout, cwd, env, check):
        raise subprocess.TimeoutExpired(command, timeout, output="raw output", stderr="raw stderr")

    monkeypatch.setattr(pumpfun_node_helper.subprocess, "run", fake_run)

    assert pumpfun_node_helper.validate_invoice_payment(VALID_INPUT) == {
        "ok": False,
        "errorCode": "NODE_HELPER_TIMEOUT",
    }
