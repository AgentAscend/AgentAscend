#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.session import init_db
from backend.app.services.job_runner import run_job_once
from backend.app.services.scheduler_service import approve_spawned_job, get_job, list_jobs, list_runs, set_job_enabled


def print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="AgentAscend persistent job admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List scheduled jobs")
    list_parser.add_argument("--enabled-only", action="store_true")

    enable_parser = sub.add_parser("enable", help="Enable a job")
    enable_parser.add_argument("job_id")

    disable_parser = sub.add_parser("disable", help="Disable a job")
    disable_parser.add_argument("job_id")

    run_parser = sub.add_parser("run", help="Run a job once now")
    run_parser.add_argument("job_id")

    show_parser = sub.add_parser("show", help="Show a job")
    show_parser.add_argument("job_id")

    runs_parser = sub.add_parser("runs", help="Show recent job runs")
    runs_parser.add_argument("--limit", type=int, default=20)
    runs_parser.add_argument("--failed", action="store_true")

    failed_parser = sub.add_parser("failed", help="Show failed job runs")
    failed_parser.add_argument("--limit", type=int, default=20)

    approve_parser = sub.add_parser("approve", help="Approve a spawned job")
    approve_parser.add_argument("job_id")
    approve_parser.add_argument("--no-enable", action="store_true")

    args = parser.parse_args()
    init_db()

    try:
        if args.command == "list":
            print_json(list_jobs(include_disabled=not args.enabled_only))
        elif args.command == "enable":
            print_json(set_job_enabled(args.job_id, True))
        elif args.command == "disable":
            print_json(set_job_enabled(args.job_id, False))
        elif args.command == "run":
            print_json(run_job_once(args.job_id))
        elif args.command == "show":
            print_json(get_job(args.job_id))
        elif args.command == "runs":
            print_json(list_runs(limit=args.limit, failed_only=args.failed))
        elif args.command == "failed":
            print_json(list_runs(limit=args.limit, failed_only=True))
        elif args.command == "approve":
            print_json(approve_spawned_job(args.job_id, enable=not args.no_enable))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
