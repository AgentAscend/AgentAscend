import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "smoke_backend_auth.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("smoke_backend_auth", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status: int, body: dict):
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body

    def close(self):
        return None


def test_redact_removes_bearer_token_and_password():
    script = _load_script()

    payload = {
        "Authorization": "Bearer secret-token-value",
        "password": "secret-password",
        "session_token": "secret-session",
        "nested": {"token": "nested-token"},
    }

    redacted = script.redact(payload)

    assert redacted["Authorization"] == "Bearer [REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["session_token"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"


def test_request_json_reports_http_errors_without_raising(monkeypatch):
    script = _load_script()

    def fake_urlopen(_request, timeout=0):
        raise HTTPError(
            url="https://api.example.test/private",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=FakeResponse(401, {"error": {"code": "unauthorized", "message": "Missing Authorization header"}}),
        )

    monkeypatch.setattr(script.urllib.request, "urlopen", fake_urlopen)

    status, body, error = script.request_json("GET", "https://api.example.test/private")

    assert status == 401
    assert body["error"]["code"] == "unauthorized"
    assert error is None


def test_build_checks_uses_authenticated_endpoints_only_when_token_and_user_present():
    script = _load_script()

    anonymous = script.build_checks("https://api.example.test", None, None)
    authenticated = script.build_checks("https://api.example.test", "token", "user_123")

    assert all(check["requires_auth"] is False for check in anonymous)
    assert any(check["path"] == "/auth/me" for check in authenticated)
    assert any(check["path"] == "/users/user_123/access" for check in authenticated)
    assert any(check["path"] == "/users/user_123/payments" for check in authenticated)
