import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

DB_PATH = Path("backend/app/db/agentascend.db")


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _next_interval_run(seconds: int) -> str:
    return (datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=seconds)).isoformat()


def _init_scheduler_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            job_type TEXT NOT NULL UNIQUE,
            schedule_type TEXT NOT NULL,
            cron_expression TEXT,
            interval_seconds INTEGER,
            enabled INTEGER NOT NULL DEFAULT 0,
            priority INTEGER NOT NULL DEFAULT 50,
            model_tier TEXT NOT NULL DEFAULT 'cheap',
            last_run_at TEXT,
            next_run_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'system',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_runs (
            id TEXT PRIMARY KEY,
            scheduled_job_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            output_summary TEXT,
            error_message TEXT,
            model_used TEXT,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(scheduled_job_id) REFERENCES scheduled_jobs(id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_findings (
            id TEXT PRIMARY KEY,
            source_job_id TEXT,
            finding_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(source_job_id) REFERENCES scheduled_jobs(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_enabled_next_run ON scheduled_jobs(enabled, next_run_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_runs_job_started ON job_runs(scheduled_job_id, started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_findings_source ON agent_findings(source_job_id)")


def _seed_default_scheduled_jobs(conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    defaults = [
        {
            "id": "default-backend-health-check",
            "name": "Backend health check",
            "description": "Check backend /health and record a short status summary.",
            "job_type": "backend_health_check",
            "schedule_type": "interval",
            "interval_seconds": 15 * 60,
            "priority": 30,
            "model_tier": "cheap",
        },
        {
            "id": "default-payment-route-audit",
            "name": "Payment route audit",
            "description": "Report-first scan of payment routes for replay/idempotency/security drift.",
            "job_type": "payment_route_audit",
            "schedule_type": "interval",
            "interval_seconds": 6 * 60 * 60,
            "priority": 80,
            "model_tier": "standard",
        },
        {
            "id": "default-access-grant-integrity-check",
            "name": "Access grant integrity check",
            "description": "Inspect access grant state for duplicates or suspicious records; no mutation.",
            "job_type": "access_grant_integrity_check",
            "schedule_type": "interval",
            "interval_seconds": 6 * 60 * 60,
            "priority": 75,
            "model_tier": "cheap",
        },
        {
            "id": "default-failed-payment-replay-review",
            "name": "Failed payment/replay protection review",
            "description": "Inspect failed payments and duplicate transaction signatures; no mutation.",
            "job_type": "failed_payment_replay_review",
            "schedule_type": "interval",
            "interval_seconds": 6 * 60 * 60,
            "priority": 80,
            "model_tier": "standard",
        },
        {
            "id": "default-wiki-consistency-check",
            "name": "Wiki/Obsidian consistency check",
            "description": "Check raw/wiki/system structure and schema headings.",
            "job_type": "wiki_consistency_check",
            "schedule_type": "interval",
            "interval_seconds": 12 * 60 * 60,
            "priority": 45,
            "model_tier": "cheap",
        },
        {
            "id": "default-integration-drift-check",
            "name": "Frontend/backend integration drift check",
            "description": "Daily report-first drift scan between frontend integration assumptions and backend routes.",
            "job_type": "integration_drift_check",
            "schedule_type": "cron",
            "cron_expression": "0 9 * * *",
            "priority": 65,
            "model_tier": "standard",
        },
        {
            "id": "default-git-status-summary",
            "name": "Git status/change summary",
            "description": "Summarize git branch and changed files without committing.",
            "job_type": "git_status_summary",
            "schedule_type": "interval",
            "interval_seconds": 4 * 60 * 60,
            "priority": 35,
            "model_tier": "cheap",
        },
        {
            "id": "default-todo-fixme-scan",
            "name": "TODO/FIXME scan",
            "description": "Scan source files for TODO/FIXME markers and summarize counts.",
            "job_type": "todo_fixme_scan",
            "schedule_type": "interval",
            "interval_seconds": 12 * 60 * 60,
            "priority": 35,
            "model_tier": "cheap",
        },
        {
            "id": "default-telegram-status-summary",
            "name": "Telegram status summary",
            "description": "Daily status summary with optional Telegram notification if configured.",
            "job_type": "telegram_status_summary",
            "schedule_type": "cron",
            "cron_expression": "0 8 * * *",
            "priority": 40,
            "model_tier": "cheap",
        },
        {
            "id": "default-roadmap-review",
            "name": "AgentAscend roadmap review",
            "description": "Report-first roadmap review; proposes next steps without editing strategy/payment decisions.",
            "job_type": "roadmap_review",
            "schedule_type": "interval",
            "interval_seconds": 2 * 24 * 60 * 60,
            "priority": 60,
            "model_tier": "premium",
            "enabled": 0,
            "metadata": {"requires_manual_approval": True, "reason": "premium strategic review is manual by default"},
        },
    ]
    for job in defaults:
        metadata = job.get("metadata", {}) | {"seeded_default": True, "risk_level": "low"}
        enabled = job.get("enabled", 1)
        next_run_at = _next_interval_run(int(job.get("interval_seconds") or 24 * 60 * 60)) if enabled else None
        conn.execute(
            """
            INSERT INTO scheduled_jobs(
                id, name, description, job_type, schedule_type, cron_expression, interval_seconds,
                enabled, priority, model_tier, last_run_at, next_run_at, created_at, updated_at,
                created_by, metadata_json
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, 'system', ?)
            ON CONFLICT(job_type) DO NOTHING
            """,
            (
                job["id"],
                job["name"],
                job["description"],
                job["job_type"],
                job["schedule_type"],
                job.get("cron_expression"),
                job.get("interval_seconds"),
                enabled,
                job["priority"],
                job["model_tier"],
                next_run_at,
                now,
                now,
                json.dumps(metadata, sort_keys=True),
            ),
        )


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                email TEXT,
                password_hash TEXT,
                display_name TEXT,
                bio TEXT,
                avatar_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "email" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        if "password_hash" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        if "display_name" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
        if "bio" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN bio TEXT")
        if "avatar_url" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
        if "updated_at" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN updated_at DATETIME")

        conn.execute(
            """
            UPDATE users
            SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            WHERE updated_at IS NULL
            """
        )

        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_token_hash TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)")

        _init_scheduler_tables(conn)
        _seed_default_scheduled_jobs(conn)

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                token TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                tx_signature TEXT UNIQUE
            )
            """
        )

        payment_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(payments)").fetchall()
        }
        if "tx_signature" not in payment_columns:
            conn.execute("ALTER TABLE payments ADD COLUMN tx_signature TEXT")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_tx_signature ON payments(tx_signature)"
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_scope TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                response_json TEXT,
                status_code INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(operation_scope, idempotency_key)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT UNIQUE NOT NULL,
                creator_user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                pricing_model TEXT NOT NULL,
                price_amount REAL NOT NULL,
                price_token TEXT NOT NULL,
                status TEXT NOT NULL,
                tags_json TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                published_at DATETIME
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS creator_earnings_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_user_id TEXT NOT NULL,
                listing_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                gross_amount REAL NOT NULL,
                fee_amount REAL NOT NULL,
                creator_amount REAL NOT NULL,
                token TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS creator_payout_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                creator_user_id TEXT NOT NULL,
                requested_amount REAL NOT NULL,
                token TEXT NOT NULL,
                destination_wallet TEXT NOT NULL,
                note TEXT,
                status TEXT NOT NULL,
                rejection_reason TEXT,
                tx_signature TEXT,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                approved_at DATETIME,
                rejected_at DATETIME,
                paid_at DATETIME
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT UNIQUE NOT NULL,
                owner_user_id TEXT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                tasks_completed INTEGER NOT NULL DEFAULT 0,
                success_rate REAL NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )

        agent_columns = {row[1] for row in conn.execute("PRAGMA table_info(agents)").fetchall()}
        if "owner_user_id" not in agent_columns:
            conn.execute("ALTER TABLE agents ADD COLUMN owner_user_id TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agents_owner_user_id ON agents(owner_user_id)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deployments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                environment TEXT NOT NULL,
                status TEXT NOT NULL,
                region TEXT NOT NULL,
                agents_count INTEGER NOT NULL DEFAULT 0,
                cpu_percent INTEGER NOT NULL DEFAULT 0,
                memory_percent INTEGER NOT NULL DEFAULT 0,
                requests_per_day INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                runs_total INTEGER NOT NULL DEFAULT 0,
                success_rate REAL NOT NULL DEFAULT 0,
                updated_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                workflow_id TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                started_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                assigned_to TEXT,
                updated_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                output_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                output_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                download_url TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS community_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE NOT NULL,
                author_user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                likes INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                notifications_email INTEGER NOT NULL DEFAULT 1,
                notifications_push INTEGER NOT NULL DEFAULT 1,
                notifications_marketing INTEGER NOT NULL DEFAULT 0,
                theme TEXT NOT NULL DEFAULT 'dark',
                updated_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_entitlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                installed_at DATETIME NOT NULL,
                UNIQUE(listing_id, user_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                action TEXT NOT NULL,
                occurred_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deployment_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL,
                cpu_percent REAL NOT NULL,
                memory_percent REAL NOT NULL,
                p95_latency_ms REAL NOT NULL DEFAULT 0,
                error_rate REAL NOT NULL DEFAULT 0,
                recorded_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workflow_nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                node_type TEXT NOT NULL,
                config_json TEXT NOT NULL,
                position_json TEXT NOT NULL,
                UNIQUE(workflow_id, node_id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile_extras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                timezone TEXT,
                language TEXT,
                website_url TEXT,
                location TEXT,
                updated_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                last_used_at DATETIME
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                config_json TEXT NOT NULL,
                updated_at DATETIME NOT NULL,
                UNIQUE(user_id, provider)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS staking_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                amount REAL NOT NULL,
                apy REAL NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rewards_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                amount REAL NOT NULL,
                source TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS marketplace_install_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                listing_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                actor_user_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ops_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observability_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                labels_json TEXT NOT NULL,
                recorded_at DATETIME NOT NULL
            )
            """
        )

        # Do not seed fake platform/community/operational records.
        # Authenticated frontend pages must render honest empty states until real
        # user-created backend data exists. Scheduler default jobs are seeded above
        # by _seed_default_scheduled_jobs because they are real system jobs, not UI
        # demo data.
        conn.commit()
