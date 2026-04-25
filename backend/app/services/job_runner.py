from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from backend.app.db.session import get_connection, utc_now_iso
from backend.app.services.runtime_config import load_runtime_config

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    try:
        data["metadata"] = json.loads(data.get("metadata_json") or "{}")
    except json.JSONDecodeError:
        data["metadata"] = {}
    return data


def _run_readonly_command(args: list[str], timeout: int = 20) -> tuple[int, str]:
    completed = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    return completed.returncode, output[:4000]


def _count_rows(table: str, where: str = "1=1", params: tuple[Any, ...] = ()) -> int:
    with get_connection() as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0])


def _record_finding(
    source_job_id: str,
    finding_type: str,
    severity: str,
    title: str,
    summary: str,
    recommendation: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO agent_findings(id, source_job_id, finding_type, severity, title, summary, recommendation, created_at, metadata_json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"finding-{uuid.uuid4().hex}",
                source_job_id,
                finding_type,
                severity,
                title,
                summary,
                recommendation,
                utc_now_iso(),
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
        conn.commit()


def _backend_health_url(config: dict[str, Any]) -> tuple[str, str]:
    explicit = os.getenv("AGENTASCEND_HEALTH_URL")
    if explicit:
        return explicit.strip(), "AGENTASCEND_HEALTH_URL"
    base_url = str(config.get("backend_base_url") or "http://127.0.0.1:8000").rstrip("/")
    return f"{base_url}/health", "backend_base_url"


def _backend_health_check(job: dict[str, Any]) -> dict[str, Any]:
    config = load_runtime_config()
    url, url_source = _backend_health_url(config)
    metadata = {"url": url, "active_url": url, "url_source": url_source}
    try:
        with urlopen(url, timeout=10) as response:  # noqa: S310 - configured local/backend health URL
            body = response.read(1000).decode("utf-8", errors="replace")
            if response.status >= 400:
                raise RuntimeError(f"HTTP {response.status}: {body}")
            return {"status": "success", "summary": f"Backend health OK at {url}: {body[:200]}", "metadata": metadata}
    except (URLError, TimeoutError, RuntimeError) as exc:
        _record_finding(
            job["id"],
            "backend_health",
            "warning",
            "Backend health check failed",
            f"Health endpoint {url} was not reachable or returned an error: {exc}",
            "Check whether the FastAPI backend is running locally/Railway and verify /health before release.",
            metadata,
        )
        return {"status": "failed", "summary": f"Backend health failed at {url}", "error": str(exc), "metadata": metadata}


def _payment_route_audit(job: dict[str, Any]) -> dict[str, Any]:
    payments_path = PROJECT_ROOT / "backend/app/routes/payments.py"
    text = payments_path.read_text(encoding="utf-8") if payments_path.exists() else ""
    checks = {
        "tx_signature_unique": "tx_signature" in text and "IntegrityError" in text,
        "receiver_check": "receiver" in text.lower() or "SOLANA_RECEIVER_WALLET" in text,
        "amount_check": "amount" in text.lower(),
        "access_grant": "access" in text.lower(),
    }
    missing = [name for name, ok in checks.items() if not ok]
    if missing:
        _record_finding(
            job["id"],
            "payment_audit",
            "warning",
            "Payment route audit found missing static checks",
            f"Static scan did not find: {', '.join(missing)}.",
            "Review payment verification manually before release; do not auto-edit payment logic from scheduler jobs.",
            {"missing": missing},
        )
    status = "success"
    return {"status": status, "summary": f"Payment route audit complete. Missing static signals: {missing or 'none'}", "metadata": {"checks": checks}}


def _access_grant_integrity_check(_job: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        duplicate_rows = conn.execute(
            """
            SELECT user_id, feature_name, COUNT(*) AS count
            FROM access_grants
            WHERE status = 'active'
            GROUP BY user_id, feature_name
            HAVING COUNT(*) > 1
            """
        ).fetchall()
    return {
        "status": "success",
        "summary": f"Access grant integrity check complete. Duplicate active grants: {len(duplicate_rows)}",
        "metadata": {"duplicate_active_grants": [dict(row) for row in duplicate_rows[:20]]},
    }


def _failed_payment_replay_review(_job: dict[str, Any]) -> dict[str, Any]:
    with get_connection() as conn:
        failed_count = conn.execute("SELECT COUNT(*) FROM payments WHERE status != 'completed'").fetchone()[0]
        duplicate_tx = conn.execute(
            """
            SELECT tx_signature, COUNT(*) AS count
            FROM payments
            WHERE tx_signature IS NOT NULL AND tx_signature != ''
            GROUP BY tx_signature
            HAVING COUNT(*) > 1
            """
        ).fetchall()
    return {
        "status": "success",
        "summary": f"Payment replay review complete. Failed/non-completed payments: {failed_count}; duplicate tx signatures: {len(duplicate_tx)}",
        "metadata": {"failed_payment_count": failed_count, "duplicate_tx_signatures": [dict(row) for row in duplicate_tx[:20]]},
    }


def _wiki_consistency_check(_job: dict[str, Any]) -> dict[str, Any]:
    required_dirs = ["raw", "wiki", "system"]
    missing_dirs = [name for name in required_dirs if not (PROJECT_ROOT / name).exists()]
    wiki_pages = list((PROJECT_ROOT / "wiki").glob("*.md")) if (PROJECT_ROOT / "wiki").exists() else []
    pages_missing_summary = []
    for page in wiki_pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        if "## Summary" not in text:
            pages_missing_summary.append(page.name)
    return {
        "status": "success",
        "summary": f"Wiki consistency check complete. Missing dirs: {missing_dirs or 'none'}; pages missing Summary: {len(pages_missing_summary)}",
        "metadata": {"missing_dirs": missing_dirs, "pages_missing_summary": pages_missing_summary[:50]},
    }


def _integration_drift_check(_job: dict[str, Any]) -> dict[str, Any]:
    backend_routes = sorted(str(path.relative_to(PROJECT_ROOT)) for path in (PROJECT_ROOT / "backend/app/routes").glob("*.py"))
    frontend_exists = (PROJECT_ROOT / "frontend").exists()
    return {
        "status": "success",
        "summary": f"Integration drift scan complete. Backend route modules: {len(backend_routes)}; frontend dir present: {frontend_exists}.",
        "metadata": {"backend_routes": backend_routes, "frontend_dir_present": frontend_exists},
    }


def _git_status_summary(_job: dict[str, Any]) -> dict[str, Any]:
    code, output = _run_readonly_command(["git", "status", "--short"], timeout=15)
    branch_code, branch = _run_readonly_command(["git", "branch", "--show-current"], timeout=15)
    changed = [line for line in output.splitlines() if line.strip()]
    status = "success" if code == 0 and branch_code == 0 else "failed"
    return {"status": status, "summary": f"Git branch={branch.strip() or 'unknown'}; changed files={len(changed)}", "metadata": {"changed": changed[:100]}}


def _todo_fixme_scan(_job: dict[str, Any]) -> dict[str, Any]:
    matches: list[str] = []
    for root in ["backend", "scripts", "tests", "wiki", "system"]:
        base = PROJECT_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".md", ".txt"} and "__pycache__" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="replace")
                for idx, line in enumerate(text.splitlines(), 1):
                    if re.search(r"\b(TODO|FIXME)\b", line, flags=re.IGNORECASE):
                        matches.append(f"{path.relative_to(PROJECT_ROOT)}:{idx}: {line.strip()[:160]}")
    return {"status": "success", "summary": f"TODO/FIXME scan complete. Matches: {len(matches)}", "metadata": {"matches": matches[:100]}}


def _telegram_status_summary(job: dict[str, Any]) -> dict[str, Any]:
    recent_runs = _count_rows("job_runs", "started_at >= ?", ((datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat(),))
    summary = f"AgentAscend scheduler daily summary: {recent_runs} job runs recorded in the last 24h."
    notification = _send_telegram_notification(summary)
    metadata = {"telegram_notification": notification}
    if notification.get("enabled") and not notification.get("sent"):
        _record_finding(
            job["id"],
            "telegram_notification",
            "info",
            "Telegram status summary could not be sent",
            notification.get("error") or "Telegram credentials/chat id not configured.",
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID if scheduler-originated Telegram delivery is desired.",
            notification,
        )
    return {"status": "success", "summary": summary, "metadata": metadata}


def _roadmap_review(_job: dict[str, Any]) -> dict[str, Any]:
    memory = PROJECT_ROOT / "MEMORY.md"
    size = memory.stat().st_size if memory.exists() else 0
    return {
        "status": "success",
        "summary": f"Roadmap review placeholder complete. MEMORY.md size={size} bytes. Premium strategic recommendations remain manual/report-first.",
        "metadata": {"manual_review_required": True},
    }


def _send_telegram_notification(message: str) -> dict[str, Any]:
    config = load_runtime_config()
    if not config.get("telegram_notifications_enabled"):
        return {"enabled": False, "sent": False, "reason": "disabled_by_config"}
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"enabled": True, "sent": False, "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is not configured"}
    try:
        from urllib.parse import urlencode

        payload = urlencode({"chat_id": chat_id, "text": message}).encode("utf-8")
        with urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, timeout=10) as response:  # noqa: S310
            return {"enabled": True, "sent": response.status < 400, "status_code": response.status}
    except Exception as exc:  # noqa: BLE001 - notifier must not crash scheduler
        return {"enabled": True, "sent": False, "error": str(exc)}


def _send_failed_job_alert(job: dict[str, Any], run_id: str, summary: str, error: str | None) -> dict[str, Any]:
    message = "\n".join(
        [
            "AgentAscend scheduler job failed",
            f"Job: {job['name']}",
            f"Job ID: {job['id']}",
            f"Job type: {job['job_type']}",
            f"Run ID: {run_id}",
            f"Summary: {summary[:1200] or 'No summary recorded'}",
            f"Error: {(error or 'None')[:1200]}",
        ]
    )
    return _send_telegram_notification(message)


JOB_HANDLERS = {
    "backend_health_check": _backend_health_check,
    "payment_route_audit": _payment_route_audit,
    "access_grant_integrity_check": _access_grant_integrity_check,
    "failed_payment_replay_review": _failed_payment_replay_review,
    "wiki_consistency_check": _wiki_consistency_check,
    "integration_drift_check": _integration_drift_check,
    "git_status_summary": _git_status_summary,
    "todo_fixme_scan": _todo_fixme_scan,
    "telegram_status_summary": _telegram_status_summary,
    "roadmap_review": _roadmap_review,
}


def get_job(job_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise ValueError(f"Scheduled job not found: {job_id}")
    return _row_to_dict(row)


def run_job_once(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    run_id = f"run-{uuid.uuid4().hex}"
    started_at = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO job_runs(id, scheduled_job_id, started_at, status, model_used, metadata_json)
            VALUES(?, ?, ?, 'running', ?, ?)
            """,
            (run_id, job_id, started_at, job["model_tier"], json.dumps({"job_type": job["job_type"]}, sort_keys=True)),
        )
        conn.commit()

    try:
        handler = JOB_HANDLERS.get(job["job_type"], lambda j: {"status": "success", "summary": f"No-op suggested job recorded: {j['name']}", "metadata": {"suggested": True}})
        result = handler(job)
        status = result.get("status") or "success"
        summary = str(result.get("summary") or "")[:4000]
        error = result.get("error")
        metadata = result.get("metadata") or {}
    except Exception as exc:  # noqa: BLE001 - individual job failure must not crash scheduler
        status = "failed"
        summary = f"Job failed: {exc}"
        error = str(exc)
        metadata = {"exception_type": type(exc).__name__}

    if status != "success":
        metadata = dict(metadata)
        metadata["telegram_failure_alert"] = _send_failed_job_alert(job, run_id, summary, error)

    finished_at = utc_now_iso()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE job_runs
            SET finished_at = ?, status = ?, output_summary = ?, error_message = ?, metadata_json = ?
            WHERE id = ?
            """,
            (finished_at, status, summary, error, json.dumps(metadata, sort_keys=True), run_id),
        )
        conn.execute(
            """
            UPDATE scheduled_jobs
            SET last_run_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (finished_at, finished_at, job_id),
        )
        conn.commit()

    return {"run_id": run_id, "job_id": job_id, "status": status, "summary": summary, "error": error}
