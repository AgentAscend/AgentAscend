from __future__ import annotations

import json
import signal
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from backend.app.db.session import get_connection, init_db, utc_now_iso
from backend.app.services.job_runner import run_job_once
from backend.app.services.runtime_config import load_runtime_config


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _cron_field_matches(field: str, value: int) -> bool:
    field = field.strip()
    if field == "*":
        return True
    if field.startswith("*/"):
        return value % int(field[2:]) == 0
    for part in field.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(x) for x in part.split("-", 1)]
            if start <= value <= end:
                return True
        elif int(part) == value:
            return True
    return False


def cron_matches_now(expression: str, now: datetime | None = None) -> bool:
    """Minimal 5-field cron matcher: minute hour day-of-month month day-of-week."""
    current = now or datetime.now(UTC)
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"Unsupported cron expression: {expression}")
    minute, hour, day, month, dow = fields
    cron_dow = (current.weekday() + 1) % 7  # cron Sunday=0, Python Monday=0
    return all(
        [
            _cron_field_matches(minute, current.minute),
            _cron_field_matches(hour, current.hour),
            _cron_field_matches(day, current.day),
            _cron_field_matches(month, current.month),
            _cron_field_matches(dow, cron_dow),
        ]
    )


def compute_next_run(job: dict[str, Any], from_time: datetime | None = None) -> str | None:
    if not int(job.get("enabled") or 0):
        return None
    base = (from_time or datetime.now(UTC)).replace(microsecond=0)
    if job.get("schedule_type") == "interval":
        seconds = int(job.get("interval_seconds") or 3600)
        return (base + timedelta(seconds=seconds)).isoformat()
    if job.get("schedule_type") == "cron":
        expression = job.get("cron_expression") or "0 0 * * *"
        candidate = base + timedelta(minutes=1)
        for _ in range(0, 366 * 24 * 60):
            if cron_matches_now(expression, candidate):
                return candidate.isoformat()
            candidate += timedelta(minutes=1)
        raise ValueError(f"Could not compute next run for cron expression: {expression}")
    return None


def list_jobs(include_disabled: bool = True) -> list[dict[str, Any]]:
    query = "SELECT * FROM scheduled_jobs"
    params: tuple[Any, ...] = ()
    if not include_disabled:
        query += " WHERE enabled = 1"
    query += " ORDER BY priority DESC, name ASC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    jobs = []
    for row in rows:
        data = dict(row)
        data["metadata"] = json.loads(data.get("metadata_json") or "{}")
        jobs.append(data)
    return jobs


def set_job_enabled(job_id: str, enabled: bool) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise ValueError(f"Scheduled job not found: {job_id}")
        job = dict(row)
        job["enabled"] = 1 if enabled else 0
        next_run_at = compute_next_run(job) if enabled else None
        now = utc_now_iso()
        conn.execute(
            "UPDATE scheduled_jobs SET enabled = ?, next_run_at = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, next_run_at, now, job_id),
        )
        conn.commit()
    return get_job(job_id)


def get_job(job_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise ValueError(f"Scheduled job not found: {job_id}")
    data = dict(row)
    data["metadata"] = json.loads(data.get("metadata_json") or "{}")
    return data


def list_runs(limit: int = 20, failed_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM job_runs"
    params: tuple[Any, ...] = ()
    if failed_only:
        query += " WHERE status = 'failed'"
    query += " ORDER BY started_at DESC LIMIT ?"
    params = (limit,)
    with get_connection() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def due_jobs(now: datetime | None = None) -> list[dict[str, Any]]:
    current = (now or datetime.now(UTC)).replace(microsecond=0)
    jobs = list_jobs(include_disabled=False)
    due: list[dict[str, Any]] = []
    for job in jobs:
        next_run = _parse_dt(job.get("next_run_at"))
        if next_run and next_run <= current:
            due.append(job)
            continue
        if job.get("schedule_type") == "cron" and cron_matches_now(job.get("cron_expression") or "0 0 * * *", current):
            last_run = _parse_dt(job.get("last_run_at"))
            if not last_run or last_run.replace(second=0) < current.replace(second=0):
                due.append(job)
    return sorted(due, key=lambda item: int(item.get("priority") or 0), reverse=True)


def _runs_started_last_hour() -> int:
    since = (datetime.now(UTC) - timedelta(hours=1)).replace(microsecond=0).isoformat()
    with get_connection() as conn:
        return int(conn.execute("SELECT COUNT(*) FROM job_runs WHERE started_at >= ?", (since,)).fetchone()[0])


def run_due_jobs_once() -> list[dict[str, Any]]:
    config = load_runtime_config()
    if not config.get("scheduler_enabled"):
        return []
    max_runs = int(config.get("max_job_runs_per_hour") or 20)
    results = []
    for job in due_jobs():
        if _runs_started_last_hour() >= max_runs:
            break
        if job.get("model_tier") == "premium" and config.get("premium_model_requires_manual_approval"):
            continue
        result = run_job_once(job["id"])
        next_run_at = compute_next_run(job)
        now = utc_now_iso()
        with get_connection() as conn:
            conn.execute(
                "UPDATE scheduled_jobs SET next_run_at = ?, updated_at = ? WHERE id = ?",
                (next_run_at, now, job["id"]),
            )
            conn.commit()
        results.append(result)
    return results


def create_suggested_job(
    name: str,
    description: str,
    job_type: str,
    reason: str,
    source_job_id: str,
    priority: int = 50,
    risk_level: str = "medium",
    schedule_type: str = "interval",
    interval_seconds: int = 24 * 60 * 60,
    cron_expression: str | None = None,
    model_tier: str | None = None,
) -> dict[str, Any]:
    config = load_runtime_config()
    if not config.get("allow_auto_spawn_jobs"):
        raise ValueError("Auto-spawned jobs are disabled by runtime config")
    if risk_level in {"high", "critical"}:
        enabled = 0
    else:
        enabled = 1 if config.get("allow_auto_enable_spawned_jobs") else 0

    since = (datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat()
    with get_connection() as conn:
        spawned_today = int(
            conn.execute(
                "SELECT COUNT(*) FROM scheduled_jobs WHERE created_by = 'auto_spawn' AND created_at >= ?",
                (since,),
            ).fetchone()[0]
        )
        if spawned_today >= int(config.get("max_spawned_jobs_per_day") or 5):
            raise ValueError("Daily spawned job limit reached")

        existing = conn.execute("SELECT * FROM scheduled_jobs WHERE job_type = ?", (job_type,)).fetchone()
        if existing is not None:
            data = dict(existing)
            data["metadata"] = json.loads(data.get("metadata_json") or "{}")
            return data

        job_id = f"spawned-{uuid.uuid4().hex}"
        now = utc_now_iso()
        metadata = {
            "spawned": True,
            "reason": reason,
            "source_job_id": source_job_id,
            "risk_level": risk_level,
            "requires_manual_approval": risk_level in {"high", "critical"} or not enabled,
        }
        row = {
            "id": job_id,
            "name": name,
            "description": description,
            "job_type": job_type,
            "schedule_type": schedule_type,
            "cron_expression": cron_expression,
            "interval_seconds": interval_seconds,
            "enabled": enabled,
            "priority": priority,
            "model_tier": model_tier or str(config.get("default_model_tier") or "cheap"),
            "next_run_at": compute_next_run({"enabled": enabled, "schedule_type": schedule_type, "interval_seconds": interval_seconds, "cron_expression": cron_expression}) if enabled else None,
            "created_at": now,
            "updated_at": now,
            "metadata_json": json.dumps(metadata, sort_keys=True),
        }
        conn.execute(
            """
            INSERT INTO scheduled_jobs(id, name, description, job_type, schedule_type, cron_expression, interval_seconds,
                                       enabled, priority, model_tier, next_run_at, created_at, updated_at, created_by, metadata_json)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'auto_spawn', ?)
            """,
            (
                row["id"], row["name"], row["description"], row["job_type"], row["schedule_type"],
                row["cron_expression"], row["interval_seconds"], row["enabled"], row["priority"],
                row["model_tier"], row["next_run_at"], row["created_at"], row["updated_at"], row["metadata_json"],
            ),
        )
        conn.commit()
        row["metadata"] = metadata
        return row


def approve_spawned_job(job_id: str, enable: bool = True) -> dict[str, Any]:
    job = get_job(job_id)
    metadata = job.get("metadata", {})
    metadata["approved_at"] = utc_now_iso()
    metadata["approved_manually"] = True
    with get_connection() as conn:
        conn.execute(
            "UPDATE scheduled_jobs SET metadata_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(metadata, sort_keys=True), utc_now_iso(), job_id),
        )
        conn.commit()
    if enable:
        return set_job_enabled(job_id, True)
    return get_job(job_id)


class SchedulerService:
    def __init__(self, poll_seconds: int | None = None) -> None:
        config = load_runtime_config()
        self.poll_seconds = poll_seconds or int(config.get("scheduler_poll_seconds") or 30)
        self._stop = False

    def request_stop(self, *_args: object) -> None:
        self._stop = True

    def run_forever(self) -> None:
        init_db()
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)
        print(f"AgentAscend scheduler started; poll_seconds={self.poll_seconds}", flush=True)
        while not self._stop:
            try:
                results = run_due_jobs_once()
                if results:
                    print(f"Ran {len(results)} due job(s): {[r['job_id'] for r in results]}", flush=True)
            except Exception as exc:  # noqa: BLE001 - scheduler loop should survive individual cycle failure
                print(f"Scheduler cycle error: {exc}", flush=True)
            time.sleep(self.poll_seconds)
        print("AgentAscend scheduler stopped", flush=True)
