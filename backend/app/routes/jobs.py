from __future__ import annotations

import ipaddress
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from backend.app.services.runtime_config import load_runtime_config
from pydantic import BaseModel

from backend.app.services.job_runner import run_job_once
from backend.app.services.scheduler_service import (
    approve_spawned_job,
    get_job,
    list_jobs,
    list_runs,
    run_due_jobs_once,
    set_job_enabled,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobActionResponse(BaseModel):
    status: str
    job: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


def _is_production_runtime() -> bool:
    env_value = (os.getenv("ENV") or os.getenv("APP_ENV") or os.getenv("RAILWAY_ENVIRONMENT") or "").strip().lower()
    if env_value in {"prod", "production", "railway"}:
        return True
    return bool(os.getenv("RAILWAY_SERVICE_ID") or os.getenv("RAILWAY_PROJECT_ID") or os.getenv("RAILWAY_ENVIRONMENT_ID"))


def _is_local_or_private_host(host: str | None) -> bool:
    if not host:
        return False
    if host in {"testclient", "localhost"}:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


def _require_runtime_admin(request: Request, x_agent_runtime_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("AGENT_RUNTIME_ADMIN_TOKEN")
    if expected:
        if x_agent_runtime_token != expected:
            raise HTTPException(status_code=403, detail="Invalid agent runtime admin token")
        return

    if _is_production_runtime():
        raise HTTPException(
            status_code=503,
            detail="AGENT_RUNTIME_ADMIN_TOKEN must be configured before /jobs routes are available in production/Railway.",
        )

    config = load_runtime_config()
    client_host = request.client.host if request.client else None
    if config.get("safe_mode") and _is_local_or_private_host(client_host):
        return

    raise HTTPException(
        status_code=403,
        detail="/jobs routes require AGENT_RUNTIME_ADMIN_TOKEN unless safe local development mode is active.",
    )


@router.get("")
def api_list_jobs(include_disabled: bool = True, _admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return {"jobs": list_jobs(include_disabled=include_disabled)}


@router.get("/runs")
def api_list_runs(limit: int = 20, failed_only: bool = False, _admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return {"runs": list_runs(limit=limit, failed_only=failed_only)}


@router.get("/failed")
def api_failed_runs(limit: int = 20, _admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return {"runs": list_runs(limit=limit, failed_only=True)}


@router.post("/run-due")
def api_run_due(_admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return {"results": run_due_jobs_once()}


@router.get("/{job_id}")
def api_get_job(job_id: str, _admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    try:
        return {"job": get_job(job_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/enable", response_model=JobActionResponse)
def api_enable_job(job_id: str, _admin: None = Depends(_require_runtime_admin)) -> JobActionResponse:
    try:
        return JobActionResponse(status="ok", job=set_job_enabled(job_id, True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/disable", response_model=JobActionResponse)
def api_disable_job(job_id: str, _admin: None = Depends(_require_runtime_admin)) -> JobActionResponse:
    try:
        return JobActionResponse(status="ok", job=set_job_enabled(job_id, False))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/run", response_model=JobActionResponse)
def api_run_job(job_id: str, _admin: None = Depends(_require_runtime_admin)) -> JobActionResponse:
    try:
        return JobActionResponse(status="ok", result=run_job_once(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/approve", response_model=JobActionResponse)
def api_approve_spawned_job(job_id: str, enable: bool = True, _admin: None = Depends(_require_runtime_admin)) -> JobActionResponse:
    try:
        return JobActionResponse(status="ok", job=approve_spawned_job(job_id, enable=enable))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
