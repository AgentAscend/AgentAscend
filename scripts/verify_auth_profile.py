#!/usr/bin/env python3
"""Verification script for auth/session/profile flows.

Checks:
- signup creates user + session
- duplicate signup blocked
- signin works
- /auth/me resolves bearer token
- /users/me/profile patch persists
- signout revokes token
"""

import importlib.util
import sys
import types


def _install_fastapi_stub():
    fastapi = types.ModuleType("fastapi")

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail):
            super().__init__(str(detail))
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

        def patch(self, *_args, **_kwargs):
            def deco(fn):
                return fn

            return deco

    def Header(default=None):  # noqa: N802 - match FastAPI API
        return default

    fastapi.HTTPException = HTTPException
    fastapi.APIRouter = APIRouter
    fastapi.Header = Header
    sys.modules["fastapi"] = fastapi

    return HTTPException


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bearer(token: str) -> str:
    return f"Bearer {token}"


def main() -> None:
    HTTPException = _install_fastapi_stub()

    sys.path.insert(0, ".")
    from backend.app.db.session import get_connection, init_db

    init_db()

    auth = _load_module("backend/app/routes/auth.py", "auth_mod")
    auth_schemas = _load_module("backend/app/schemas/auth.py", "auth_schemas_mod")

    checks: list[tuple[str, bool, str]] = []

    with get_connection() as conn:
        conn.execute("DELETE FROM auth_sessions")
        conn.execute("DELETE FROM users WHERE email LIKE 'verify_auth_%@example.com'")
        conn.commit()

    signup = auth.auth_signup(
        auth_schemas.AuthSignupRequest(
            email="verify_auth_user@example.com",
            password="verysecure123",
            display_name="Verify User",
        )
    )
    checks.append(("signup_ok", signup.get("status") == "ok" and bool(signup.get("session_token")), str(signup)))

    try:
        auth.auth_signup(
            auth_schemas.AuthSignupRequest(
                email="verify_auth_user@example.com",
                password="verysecure123",
                display_name="Duplicate",
            )
        )
        checks.append(("signup_duplicate_blocked", False, "expected HTTP 409"))
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "", "message": str(exc.detail)}
        checks.append(("signup_duplicate_blocked", exc.status_code == 409 and detail.get("code") == "validation_error", f"{exc.status_code} {detail}"))

    signin = auth.auth_signin(
        auth_schemas.AuthSigninRequest(
            email="verify_auth_user@example.com",
            password="verysecure123",
        )
    )
    checks.append(("signin_ok", signin.get("status") == "ok" and bool(signin.get("session_token")), str(signin)))

    token = signin["session_token"]

    me = auth.auth_me(_bearer(token))
    checks.append(("auth_me_ok", me.get("status") == "ok" and me.get("user", {}).get("email") == "verify_auth_user@example.com", str(me)))

    patched = auth.users_patch_profile(
        auth_schemas.UserProfilePatchRequest(display_name="Verify Updated", bio="bio text", avatar_url="https://example.com/a.png"),
        _bearer(token),
    )
    user = patched.get("user", {})
    checks.append(
        (
            "profile_patch_ok",
            patched.get("status") == "ok"
            and user.get("display_name") == "Verify Updated"
            and user.get("bio") == "bio text"
            and user.get("avatar_url") == "https://example.com/a.png",
            str(patched),
        )
    )

    signout = auth.auth_signout(_bearer(token))
    checks.append(("signout_ok", signout.get("status") == "ok", str(signout)))

    try:
        auth.auth_me(_bearer(token))
        checks.append(("revoked_token_blocked", False, "expected HTTP 401"))
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "", "message": str(exc.detail)}
        checks.append(("revoked_token_blocked", exc.status_code == 401 and detail.get("code") == "unauthorized", f"{exc.status_code} {detail}"))

    failed = [c for c in checks if not c[1]]

    print("Auth/profile verification results:")
    for name, ok, detail in checks:
        print(f"- {'PASS' if ok else 'FAIL'}: {name} -> {detail}")

    if failed:
        print(f"\nFAILED checks: {len(failed)}")
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
