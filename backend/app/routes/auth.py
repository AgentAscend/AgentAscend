from fastapi import APIRouter, Header

from backend.app.schemas.auth import (
    AuthMeResponse,
    AuthSessionResponse,
    AuthSigninRequest,
    AuthSignoutResponse,
    AuthSignupRequest,
    UserProfilePatchRequest,
    UserProfileResponse,
)
from backend.app.services.auth_service import (
    authenticate_and_create_session,
    create_user_with_password,
    resolve_session,
    revoke_session_by_token_hash,
    update_profile,
)
from backend.app.services.rate_limit import enforce_rate_limit

router = APIRouter()


@router.post("/auth/signup", response_model=AuthSessionResponse)
def auth_signup(payload: AuthSignupRequest):
    enforce_rate_limit("auth.signup", payload.email.lower(), limit=10, window_seconds=300)
    user, session_token, expires_at = create_user_with_password(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    return {
        "status": "ok",
        "session_token": session_token,
        "expires_at": expires_at,
        "user": user,
    }


@router.post("/auth/signin", response_model=AuthSessionResponse)
def auth_signin(payload: AuthSigninRequest):
    enforce_rate_limit("auth.signin", payload.email.lower(), limit=20, window_seconds=300)
    user, session_token, expires_at = authenticate_and_create_session(
        email=payload.email,
        password=payload.password,
    )
    return {
        "status": "ok",
        "session_token": session_token,
        "expires_at": expires_at,
        "user": user,
    }


@router.post("/auth/signout", response_model=AuthSignoutResponse)
def auth_signout(authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    revoke_session_by_token_hash(auth["token_hash"])
    return {"status": "ok"}


@router.get("/auth/me", response_model=AuthMeResponse)
def auth_me(authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    return {
        "status": "ok",
        "user": auth["user"],
    }


@router.get("/users/me/profile", response_model=UserProfileResponse)
def users_me_profile(authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    return {
        "status": "ok",
        "user": auth["user"],
    }


@router.patch("/users/me/profile", response_model=UserProfileResponse)
def users_patch_profile(payload: UserProfilePatchRequest, authorization: str | None = Header(default=None)):
    auth = resolve_session(authorization)
    user = update_profile(
        user_id=auth["user"]["user_id"],
        display_name=payload.display_name,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
    )
    return {
        "status": "ok",
        "user": user,
    }
