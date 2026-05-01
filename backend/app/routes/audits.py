from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from backend.app.routes.jobs import _require_runtime_admin
from backend.app.services.launch_readiness_audit import run_launch_readiness_audit, run_payment_evidence_lookup

router = APIRouter(prefix="/admin/audits", tags=["admin-audits"])


@router.get("/launch-readiness/aggregate")
def get_launch_readiness_aggregate(_admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return run_launch_readiness_audit()


@router.get("/payment-evidence/{tx_signature}")
def get_payment_evidence(tx_signature: str, _admin: None = Depends(_require_runtime_admin)) -> dict[str, Any]:
    return run_payment_evidence_lookup(tx_signature)
