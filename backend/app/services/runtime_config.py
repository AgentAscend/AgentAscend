from __future__ import annotations

import os
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "agent_runtime.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "scheduler_enabled": True,
    "allow_auto_spawn_jobs": True,
    "allow_auto_enable_spawned_jobs": False,
    "max_job_runs_per_hour": 20,
    "max_spawned_jobs_per_day": 5,
    "default_model_tier": "cheap",
    "premium_model_requires_manual_approval": True,
    "telegram_notifications_enabled": True,
    "safe_mode": True,
    "scheduler_poll_seconds": 30,
    "backend_base_url": "http://127.0.0.1:8000",
}


def _parse_scalar(value: str) -> Any:
    cleaned = value.strip().strip('"').strip("'")
    lowered = cleaned.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(cleaned)
    except ValueError:
        return cleaned


def load_runtime_config(path: Path | None = None) -> dict[str, Any]:
    """Load the flat AgentAscend runtime YAML without adding a PyYAML dependency."""
    config = dict(DEFAULT_CONFIG)
    source = path or CONFIG_PATH
    if source.exists():
        for line in source.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            config[key.strip()] = _parse_scalar(value)

    # Environment overrides for deployment without editing the YAML.
    bool_envs = {
        "AGENT_RUNTIME_SCHEDULER_ENABLED": "scheduler_enabled",
        "AGENT_RUNTIME_ALLOW_AUTO_SPAWN_JOBS": "allow_auto_spawn_jobs",
        "AGENT_RUNTIME_ALLOW_AUTO_ENABLE_SPAWNED_JOBS": "allow_auto_enable_spawned_jobs",
        "AGENT_RUNTIME_PREMIUM_REQUIRES_APPROVAL": "premium_model_requires_manual_approval",
        "AGENT_RUNTIME_TELEGRAM_NOTIFICATIONS_ENABLED": "telegram_notifications_enabled",
        "AGENT_RUNTIME_SAFE_MODE": "safe_mode",
    }
    for env_name, key in bool_envs.items():
        if env_name in os.environ:
            config[key] = os.environ[env_name].strip().lower() == "true"

    int_envs = {
        "AGENT_RUNTIME_MAX_JOB_RUNS_PER_HOUR": "max_job_runs_per_hour",
        "AGENT_RUNTIME_MAX_SPAWNED_JOBS_PER_DAY": "max_spawned_jobs_per_day",
        "AGENT_RUNTIME_POLL_SECONDS": "scheduler_poll_seconds",
    }
    for env_name, key in int_envs.items():
        if env_name in os.environ:
            config[key] = int(os.environ[env_name])

    if os.getenv("AGENTASCEND_BACKEND_BASE_URL"):
        config["backend_base_url"] = os.environ["AGENTASCEND_BACKEND_BASE_URL"]
    if os.getenv("AGENT_RUNTIME_DEFAULT_MODEL_TIER"):
        config["default_model_tier"] = os.environ["AGENT_RUNTIME_DEFAULT_MODEL_TIER"]

    return config
