from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    display_name: str | None = Field(default=None, min_length=1, max_length=80)


class AuthSigninRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class AuthSessionResponse(BaseModel):
    status: Literal["ok"] = "ok"
    session_token: str
    expires_at: str
    user: dict


class AuthSignoutResponse(BaseModel):
    status: Literal["ok"] = "ok"


class AuthMeResponse(BaseModel):
    status: Literal["ok"] = "ok"
    user: dict


class UserProfileResponse(BaseModel):
    status: Literal["ok"] = "ok"
    user: dict


class UserProfilePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=280)
    avatar_url: str | None = Field(default=None, max_length=500)
