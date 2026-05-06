from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.app.routes.jobs import _require_runtime_admin
from backend.app.services.launch_readiness_audit import run_launch_readiness_audit, run_payment_evidence_lookup
from backend.app.services.task_runtime_audit import run_task_runtime_audit

router = APIRouter(prefix="/admin/audits", tags=["admin-audits"])


@router.get("/launch-readiness/aggregate")
def get_launch_readiness_aggregate(_admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return run_launch_readiness_audit()


@router.get("/task-runtime/aggregate")
def get_task_runtime_aggregate(_admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return run_task_runtime_audit()


@router.get("/payment-evidence/{tx_signature}")
def get_payment_evidence(tx_signature: str, _admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return run_payment_evidence_lookup(tx_signature)
