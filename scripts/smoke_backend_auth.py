#!/usr/bin/env python3
"""Safe AgentAscend backend auth smoke script.

This script performs non-mutating checks against the live or local backend.
It never prints bearer tokens or other secrets. Authenticated checks run only
when both AUTH_TOKEN and AUTH_USER_ID are present, or equivalent env names are
provided with CLI flags.

Examples:
  python scripts/smoke_backend_auth.py
  AGENTASCEND_API_BASE=https://api.agentascend.ai python scripts/smoke_backend_auth.py
  AUTH_TOKEN='...' AUTH_USER_ID='user_...' python scripts/smoke_backend_auth.py
  python scripts/smoke_backend_auth.py --output raw/backend-health/smoke.md
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any

DEFAULT_BASE_URL = "https://api.agentascend.ai"
SECRET_KEYS = {
    "authorization",
    "access_token",
    "auth_token",
    "bearer",
    "password",
    "private_key",
    "secret",
    "seed",
    "seed_phrase",
    "session",
    "session_token",
    "token",
}


def redact(value: Any) -> Any:
    """Recursively redact likely secrets from a JSON-like value."""
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            if key_lower == "authorization" and isinstance(item, str):
                if item.lower().startswith("bearer "):
                    redacted[key_text] = "Bearer [REDACTED]"
                else:
                    redacted[key_text] = "[REDACTED]"
            elif any(secret_key in key_lower for secret_key in SECRET_KEYS):
                redacted[key_text] = "[REDACTED]"
            else:
                redacted[key_text] = redact(item)
        return redacted
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact(item) for item in value)
    return value


def parse_json_bytes(raw: bytes) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text[:1000]}


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    body: Mapping[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int | None, Any, str | None]:
    """Return (status, body, transport_error). HTTP errors are returned as bodies."""
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, parse_json_bytes(response.read()), None
    except urllib.error.HTTPError as exc:
        return exc.code, parse_json_bytes(exc.read()), None
    except urllib.error.URLError as exc:
        return None, None, str(exc.reason)
    except TimeoutError as exc:
        return None, None, str(exc)


def build_checks(base_url: str, token: str | None, user_id: str | None) -> list[dict[str, Any]]:
    base = base_url.rstrip("/")
    checks: list[dict[str, Any]] = [
        {"name": "health", "method": "GET", "path": "/health", "requires_auth": False, "expected": {200}},
        {"name": "marketplace_live", "method": "GET", "path": "/marketplace/live", "requires_auth": False, "expected": {200}},
        {"name": "openapi", "method": "GET", "path": "/openapi.json", "requires_auth": False, "expected": {200}},
    ]

    if token and user_id:
        encoded_user = urllib.parse.quote(user_id, safe="")
        checks.extend(
            [
                {"name": "auth_me", "method": "GET", "path": "/auth/me", "requires_auth": True, "expected": {200}},
                {
                    "name": "user_access",
                    "method": "GET",
                    "path": f"/users/{encoded_user}/access",
                    "requires_auth": True,
                    "expected": {200},
                },
                {
                    "name": "user_payments",
                    "method": "GET",
                    "path": f"/users/{encoded_user}/payments",
                    "requires_auth": True,
                    "expected": {200},
                },
                {
                    "name": "marketplace_entitlements",
                    "method": "GET",
                    "path": f"/marketplace/entitlements?user_id={encoded_user}",
                    "requires_auth": True,
                    "expected": {200},
                },
                {
                    "name": "marketplace_creator_listings",
                    "method": "GET",
                    "path": f"/marketplace/listings?creator_user_id={encoded_user}",
                    "requires_auth": True,
                    "expected": {200},
                },
            ]
        )
    return checks


def run_checks(base_url: str, token: str | None, user_id: str | None, timeout: int) -> list[dict[str, Any]]:
    base = base_url.rstrip("/")
    results: list[dict[str, Any]] = []
    for check in build_checks(base, token, user_id):
        url = f"{base}{check['path']}"
        status, body, error = request_json(
            check["method"],
            url,
            token=token if check["requires_auth"] else None,
            timeout=timeout,
        )
        passed = status in check["expected"] and error is None
        results.append(
            {
                "name": check["name"],
                "method": check["method"],
                "path": check["path"],
                "requires_auth": check["requires_auth"],
                "expected": sorted(check["expected"]),
                "status": status,
                "passed": passed,
                "error": error,
                "body": redact(body),
            }
        )
    return results


def render_markdown(base_url: str, results: Sequence[Mapping[str, Any]], auth_enabled: bool) -> str:
    now = dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    failed = [result for result in results if not result["passed"]]
    lines = [
        "# AgentAscend Backend Auth Smoke Report",
        "",
        f"Generated: {now}",
        f"Base URL: {base_url.rstrip('/')}",
        f"Authenticated checks: {'enabled' if auth_enabled else 'skipped; AUTH_TOKEN and AUTH_USER_ID not both set'}",
        f"Overall: {'PASS' if not failed else 'FAIL'}",
        "",
        "## Checks",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"### {'PASS' if result['passed'] else 'FAIL'} {result['name']}",
                f"- Request: {result['method']} {result['path']}",
                f"- Requires auth: {result['requires_auth']}",
                f"- Expected status: {result['expected']}",
                f"- Actual status: {result['status']}",
            ]
        )
        if result.get("error"):
            lines.append(f"- Transport error: {result['error']}")
        body = result.get("body")
        if body is not None:
            body_json = json.dumps(body, indent=2, sort_keys=True)
            lines.extend(["- Response body:", "```json", body_json[:4000], "```"])
        lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- This script is non-mutating by default; it uses GET-only checks.",
            "- Bearer tokens, session tokens, passwords, keys, and secrets are redacted before output.",
            "- For deeper payment verification, use a separate approved staged smoke script with known test credentials and safe test transactions.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safe AgentAscend backend auth smoke checks")
    parser.add_argument("--base-url", default=os.environ.get("AGENTASCEND_API_BASE", DEFAULT_BASE_URL))
    parser.add_argument("--token-env", default="AUTH_TOKEN", help="Environment variable containing bearer token")
    parser.add_argument("--user-id-env", default="AUTH_USER_ID", help="Environment variable containing expected user id")
    parser.add_argument("--output", help="Optional markdown report path")
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    token = os.environ.get(args.token_env)
    user_id = os.environ.get(args.user_id_env)
    auth_enabled = bool(token and user_id)

    results = run_checks(args.base_url, token, user_id, args.timeout)
    report = render_markdown(args.base_url, results, auth_enabled)

    if args.output:
        output_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(report)
            handle.write("\n")
        print(f"Wrote smoke report: {output_path}")
    else:
        print(report)

    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
