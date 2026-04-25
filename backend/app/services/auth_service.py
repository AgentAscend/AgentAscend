import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header

from backend.app.db.session import get_connection
from backend.app.services.error_response import fail


_PASSWORD_SCHEME = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 150_000


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_email(email: str) -> str:
    normalized = (email or "").strip().lower()
    if not normalized:
        fail(400, "validation_error", "email is required")
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        fail(400, "validation_error", "Invalid email format")
    return normalized


def _sanitize_user_id_seed(seed: str) -> str:
    token = re.sub(r"[^a-z0-9_]+", "_", (seed or "").lower())
    token = token.strip("_")
    if not token:
        token = "user"
    return token[:24]


def _generate_unique_user_id(conn, seed: str) -> str:
    base = _sanitize_user_id_seed(seed)
    candidate = base
    i = 0
    while True:
        row = conn.execute("SELECT 1 FROM users WHERE user_id = ?", (candidate,)).fetchone()
        if not row:
            return candidate
        i += 1
        suffix = secrets.token_hex(2)
        candidate = f"{base}_{suffix}_{i}"


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS)
    return f"{_PASSWORD_SCHEME}${_PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        scheme, iterations_raw, salt_hex, digest_hex = stored_hash.split("$", 3)
        if scheme != _PASSWORD_SCHEME:
            return False
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except Exception:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return secrets.compare_digest(actual, expected)


def _session_ttl_seconds() -> int:
    raw = os.getenv("AUTH_SESSION_TTL_SECONDS", "2592000")
    try:
        ttl = int(raw)
    except ValueError:
        fail(500, "unknown", "AUTH_SESSION_TTL_SECONDS must be an integer")
    if ttl <= 0:
        fail(500, "unknown", "AUTH_SESSION_TTL_SECONDS must be greater than zero")
    return ttl


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _admin_user_set() -> set[str]:
    return {x.strip() for x in os.getenv("ADMIN_USER_IDS", "").split(",") if x.strip()}


def _user_payload(row) -> dict:
    user_id = row["user_id"]
    return {
        "user_id": user_id,
        "email": row["email"],
        "display_name": row["display_name"],
        "bio": row["bio"],
        "avatar_url": row["avatar_url"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "role": "admin" if user_id in _admin_user_set() else "user",
    }


def create_user_with_password(email: str, password: str, display_name: str | None = None) -> tuple[dict, str, str]:
    normalized_email = _normalize_email(email)

    with get_connection() as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if existing:
            fail(409, "validation_error", "Email already in use")

        seed = normalized_email.split("@", 1)[0]
        user_id = _generate_unique_user_id(conn, seed)
        password_hash = _password_hash(password)
        now_iso = _utcnow_iso()

        conn.execute(
            """
            INSERT INTO users (user_id, email, password_hash, display_name, bio, avatar_url, created_at, updated_at)
            VALUES (?, ?, ?, ?, '', '', ?, ?)
            """,
            (user_id, normalized_email, password_hash, display_name, now_iso, now_iso),
        )
        conn.commit()

    return create_session_for_user(user_id)


def authenticate_and_create_session(email: str, password: str) -> tuple[dict, str, str]:
    normalized_email = _normalize_email(email)

    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, email, password_hash FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()

    if not row or not _verify_password(password, row["password_hash"]):
        fail(401, "unauthorized", "Invalid email or password")

    return create_session_for_user(row["user_id"])


def create_session_for_user(user_id: str) -> tuple[dict, str, str]:
    session_token = secrets.token_urlsafe(32)
    session_hash = _token_hash(session_token)
    ttl = _session_ttl_seconds()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    expires_iso = expires_at.isoformat()

    with get_connection() as conn:
        user_row = conn.execute(
            """
            SELECT user_id, email, display_name, bio, avatar_url, created_at, updated_at
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        if not user_row:
            fail(404, "validation_error", "User not found")

        conn.execute(
            """
            INSERT INTO auth_sessions (session_token_hash, user_id, expires_at, created_at, last_seen_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (session_hash, user_id, expires_iso),
        )
        conn.commit()

    return _user_payload(user_row), session_token, expires_iso


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        fail(401, "unauthorized", "Missing Authorization header")

    prefix = "bearer "
    if not authorization.lower().startswith(prefix):
        fail(401, "unauthorized", "Authorization must use Bearer token")

    token = authorization[len(prefix) :].strip()
    if not token:
        fail(401, "unauthorized", "Bearer token missing")
    return token


def resolve_session(authorization: str | None = Header(default=None)) -> dict:
    token = _extract_bearer_token(authorization)
    session_hash = _token_hash(token)

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT s.session_token_hash, s.user_id, s.expires_at, s.revoked_at,
                   u.email, u.display_name, u.bio, u.avatar_url, u.created_at, u.updated_at
            FROM auth_sessions s
            JOIN users u ON u.user_id = s.user_id
            WHERE s.session_token_hash = ?
            """,
            (session_hash,),
        ).fetchone()

        if not row:
            fail(401, "unauthorized", "Invalid session token")

        if row["revoked_at"]:
            fail(401, "unauthorized", "Session revoked")

        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            fail(401, "unauthorized", "Session expired")

        conn.execute(
            "UPDATE auth_sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE session_token_hash = ?",
            (session_hash,),
        )
        conn.commit()

    return {
        "token_hash": row["session_token_hash"],
        "user": {
            "user_id": row["user_id"],
            "email": row["email"],
            "display_name": row["display_name"],
            "bio": row["bio"],
            "avatar_url": row["avatar_url"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "role": "admin" if row["user_id"] in _admin_user_set() else "user",
        },
    }


def require_user_access(target_user_id: str, authorization: str | None) -> dict:
    """Resolve a session and require the caller to own target_user_id or be admin."""
    auth = resolve_session(authorization)
    user = auth["user"]
    if user["user_id"] != target_user_id and user.get("role") != "admin":
        fail(403, "forbidden", "Authenticated user cannot access another user's data")
    return auth


def require_admin_session(authorization: str | None) -> dict:
    """Resolve a session and require an admin user."""
    auth = resolve_session(authorization)
    if auth["user"].get("role") != "admin":
        fail(403, "forbidden", "Admin role required")
    return auth


def revoke_session_by_token_hash(token_hash: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE auth_sessions SET revoked_at = CURRENT_TIMESTAMP WHERE session_token_hash = ?",
            (token_hash,),
        )
        conn.commit()


def update_profile(user_id: str, display_name: str | None, bio: str | None, avatar_url: str | None) -> dict:
    updates: list[str] = []
    params: list[object] = []

    if display_name is not None:
        updates.append("display_name = ?")
        params.append(display_name)
    if bio is not None:
        updates.append("bio = ?")
        params.append(bio)
    if avatar_url is not None:
        updates.append("avatar_url = ?")
        params.append(avatar_url)

    if not updates:
        fail(400, "validation_error", "At least one profile field is required")

    updates.append("updated_at = ?")
    params.append(_utcnow_iso())
    params.append(user_id)

    with get_connection() as conn:
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", tuple(params))
        row = conn.execute(
            """
            SELECT user_id, email, display_name, bio, avatar_url, created_at, updated_at
            FROM users WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        conn.commit()

    if not row:
        fail(404, "validation_error", "User not found")

    return _user_payload(row)
