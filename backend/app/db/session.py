import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _default_db_path() -> Path:
    configured = os.getenv("DATABASE_PATH") or os.getenv("SQLITE_PATH")
    if configured:
        return Path(configured)
    return Path("backend/app/db/agentascend.db")


DB_PATH = _default_db_path()


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _next_interval_run(seconds: int) -> str:
    return (datetime.now(UTC).replace(microsecond=0) + timedelta(seconds=seconds)).isoformat()


DATABASE_URL = os.getenv("DATABASE_URL")


def _using_postgres() -> bool:
    url = os.getenv("DATABASE_URL", "").strip()
    return url.startswith(("postgres://", "postgresql://"))


class DbRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _translate_sql(sql: str) -> str:
    translated = sql.replace("datetime('now')", "CURRENT_TIMESTAMP")
    had_insert_or_ignore = "INSERT OR IGNORE INTO" in translated
    translated = translated.replace("INSERT OR IGNORE INTO", "INSERT INTO")
    translated = translated.replace("?", "%s")
    if had_insert_or_ignore and "ON CONFLICT" not in translated.upper():
        translated = f"{translated} ON CONFLICT DO NOTHING"
    return translated


class PostgresCursorAdapter:
    def __init__(self, cursor):
        self._cursor = cursor
        self.rowcount = cursor.rowcount

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return DbRow(row)

    def fetchall(self):
        return [DbRow(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield DbRow(row)


class PostgresConnectionAdapter:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=()):
        if params is None:
            params = ()
        translated = _translate_sql(sql)
        cur = self._conn.cursor()
        try:
            cur.execute(translated, params)
        except Exception:
            cur.close()
            raise
        return PostgresCursorAdapter(cur)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()
        return False


def _connect_postgres():
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError as exc:
        raise RuntimeError("DATABASE_URL is configured for Postgres, but psycopg2-binary is not installed") from exc
    conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)
    return PostgresConnectionAdapter(conn)


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


def _init_execution_ledger_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id TEXT UNIQUE NOT NULL,
            source_type TEXT,
            source_id TEXT,
            user_id TEXT,
            agent_id TEXT,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            step_id TEXT UNIQUE NOT NULL,
            execution_id TEXT NOT NULL,
            step_order INTEGER NOT NULL DEFAULT 0,
            step_type TEXT NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT,
            finished_at TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(execution_id) REFERENCES executions(execution_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            execution_id TEXT NOT NULL,
            step_id TEXT,
            event_type TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'info',
            message TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(execution_id) REFERENCES executions(execution_id),
            FOREIGN KEY(step_id) REFERENCES execution_steps(step_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_artifacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artifact_id TEXT UNIQUE NOT NULL,
            execution_id TEXT NOT NULL,
            step_id TEXT,
            artifact_type TEXT NOT NULL,
            name TEXT NOT NULL,
            uri TEXT,
            content_text TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(execution_id) REFERENCES executions(execution_id),
            FOREIGN KEY(step_id) REFERENCES execution_steps(step_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cost_id TEXT UNIQUE NOT NULL,
            execution_id TEXT NOT NULL,
            step_id TEXT,
            provider TEXT,
            model TEXT,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_amount REAL NOT NULL DEFAULT 0,
            cost_currency TEXT NOT NULL DEFAULT 'USD',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(execution_id) REFERENCES executions(execution_id),
            FOREIGN KEY(step_id) REFERENCES execution_steps(step_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS execution_approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_id TEXT UNIQUE NOT NULL,
            execution_id TEXT NOT NULL,
            step_id TEXT,
            approval_type TEXT NOT NULL,
            status TEXT NOT NULL,
            requested_by TEXT,
            approved_by TEXT,
            requested_at TEXT NOT NULL,
            decided_at TEXT,
            reason TEXT,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(execution_id) REFERENCES executions(execution_id),
            FOREIGN KEY(step_id) REFERENCES execution_steps(step_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_executions_status_started ON executions(status, started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_executions_user_started ON executions(user_id, started_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_steps_execution_order ON execution_steps(execution_id, step_order)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_events_execution_created ON execution_events(execution_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_artifacts_execution ON execution_artifacts(execution_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_costs_execution ON execution_costs(execution_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_execution_approvals_execution_status ON execution_approvals(execution_id, status)")


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
            "id": "default-task-queue-worker",
            "name": "Task queue worker",
            "description": "Process queued user tasks and persist outputs from completed work.",
            "job_type": "task_queue_worker",
            "schedule_type": "interval",
            "interval_seconds": 60,
            "priority": 70,
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
    if _using_postgres():
        return _connect_postgres()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_sqlite_db():
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
        _init_execution_ledger_tables(conn)
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
                tx_signature TEXT UNIQUE,
                intent_reference TEXT,
                user_wallet TEXT,
                agent_token_mint TEXT,
                currency_mint TEXT,
                currency_symbol TEXT,
                amount_smallest_unit INTEGER,
                memo INTEGER,
                start_time INTEGER,
                end_time INTEGER,
                invoice_id TEXT,
                recipient_address TEXT,
                payer_wallet TEXT,
                chain TEXT,
                mint_address TEXT,
                amount_expected REAL,
                amount_received REAL,
                confirmation_status TEXT,
                block_time INTEGER,
                slot INTEGER,
                verification_status TEXT,
                failure_reason TEXT,
                updated_at DATETIME,
                verified_at DATETIME
            )
            """
        )

        payment_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(payments)").fetchall()
        }
        payment_column_migrations = {
            "tx_signature": "TEXT",
            "intent_reference": "TEXT",
            "user_wallet": "TEXT",
            "agent_token_mint": "TEXT",
            "currency_mint": "TEXT",
            "currency_symbol": "TEXT",
            "amount_smallest_unit": "INTEGER",
            "memo": "INTEGER",
            "start_time": "INTEGER",
            "end_time": "INTEGER",
            "invoice_id": "TEXT",
            "recipient_address": "TEXT",
            "payer_wallet": "TEXT",
            "chain": "TEXT",
            "mint_address": "TEXT",
            "amount_expected": "REAL",
            "amount_received": "REAL",
            "confirmation_status": "TEXT",
            "block_time": "INTEGER",
            "slot": "INTEGER",
            "verification_status": "TEXT",
            "failure_reason": "TEXT",
            "updated_at": "DATETIME",
            "verified_at": "DATETIME",
        }
        for column, column_type in payment_column_migrations.items():
            if column not in payment_columns:
                conn.execute(f"ALTER TABLE payments ADD COLUMN {column} {column_type}")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_tx_signature ON payments(tx_signature)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_intent_reference ON payments(intent_reference)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_status_created ON payments(user_id, status, created_at)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS access_grants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                payment_id INTEGER,
                intent_reference TEXT,
                grant_scope TEXT,
                source TEXT,
                plan_id TEXT,
                product_id TEXT,
                tool_id TEXT,
                expires_at DATETIME,
                revoked_at DATETIME,
                updated_at DATETIME,
                metadata_json TEXT
            )
            """
        )

        access_grant_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(access_grants)").fetchall()
        }
        access_grant_column_migrations = {
            "payment_id": "INTEGER",
            "intent_reference": "TEXT",
            "grant_scope": "TEXT",
            "source": "TEXT",
            "plan_id": "TEXT",
            "product_id": "TEXT",
            "tool_id": "TEXT",
            "expires_at": "DATETIME",
            "revoked_at": "DATETIME",
            "updated_at": "DATETIME",
            "metadata_json": "TEXT",
        }
        for column, column_type in access_grant_column_migrations.items():
            if column not in access_grant_columns:
                conn.execute(f"ALTER TABLE access_grants ADD COLUMN {column} {column_type}")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_access_grants_user_feature_status ON access_grants(user_id, feature_name, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_access_grants_user_scope_status ON access_grants(user_id, grant_scope, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_access_grants_payment_id ON access_grants(payment_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_access_grants_intent_reference ON access_grants(intent_reference)")

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
            CREATE TABLE IF NOT EXISTS payment_intents (
                reference TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                expires_at_epoch INTEGER NOT NULL,
                consumed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_wallet TEXT,
                agent_token_mint TEXT,
                currency_mint TEXT,
                currency_symbol TEXT,
                amount_smallest_unit INTEGER,
                memo INTEGER,
                start_time INTEGER,
                end_time INTEGER,
                invoice_id TEXT,
                plan_id TEXT,
                product_id TEXT,
                tool_id TEXT,
                access_tier TEXT,
                amount_expected REAL,
                recipient_address TEXT,
                expected_wallet TEXT,
                status TEXT,
                tx_signature TEXT,
                verification_status TEXT,
                updated_at DATETIME,
                expires_at DATETIME,
                completed_at DATETIME,
                failed_at DATETIME,
                canceled_at DATETIME,
                failure_reason TEXT,
                metadata_json TEXT,
                mint_address TEXT,
                currency TEXT,
                chain TEXT
            )
            """
        )

        payment_intent_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(payment_intents)").fetchall()
        }
        payment_intent_column_migrations = {
            "user_wallet": "TEXT",
            "agent_token_mint": "TEXT",
            "currency_mint": "TEXT",
            "currency_symbol": "TEXT",
            "amount_smallest_unit": "INTEGER",
            "memo": "INTEGER",
            "start_time": "INTEGER",
            "end_time": "INTEGER",
            "invoice_id": "TEXT",
            "plan_id": "TEXT",
            "product_id": "TEXT",
            "tool_id": "TEXT",
            "access_tier": "TEXT",
            "amount_expected": "REAL",
            "recipient_address": "TEXT",
            "expected_wallet": "TEXT",
            "status": "TEXT",
            "tx_signature": "TEXT",
            "verification_status": "TEXT",
            "updated_at": "DATETIME",
            "expires_at": "DATETIME",
            "completed_at": "DATETIME",
            "failed_at": "DATETIME",
            "canceled_at": "DATETIME",
            "failure_reason": "TEXT",
            "metadata_json": "TEXT",
            "mint_address": "TEXT",
            "currency": "TEXT",
            "chain": "TEXT",
        }
        for column, column_type in payment_intent_column_migrations.items():
            if column not in payment_intent_columns:
                conn.execute(f"ALTER TABLE payment_intents ADD COLUMN {column} {column_type}")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_intents_user_status_created ON payment_intents(user_id, status, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_intents_status_expires ON payment_intents(status, expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_intents_invoice_id ON payment_intents(invoice_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_intents_memo_time ON payment_intents(memo, start_time, end_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_payment_intents_tx_signature ON payment_intents(tx_signature)")

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
                user_id TEXT,
                agent_id TEXT,
                type TEXT NOT NULL DEFAULT 'general',
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                assigned_to TEXT,
                error_message TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL
            )
            """
        )
        task_columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        if "user_id" not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN user_id TEXT")
        if "agent_id" not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN agent_id TEXT")
        if "type" not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN type TEXT NOT NULL DEFAULT 'general'")
        if "error_message" not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN error_message TEXT")
        if "created_at" not in task_columns:
            conn.execute("ALTER TABLE tasks ADD COLUMN created_at DATETIME")
        conn.execute(
            """
            UPDATE tasks
            SET created_at = COALESCE(created_at, updated_at, CURRENT_TIMESTAMP)
            WHERE created_at IS NULL
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                output_id TEXT UNIQUE NOT NULL,
                task_id TEXT,
                user_id TEXT,
                title TEXT NOT NULL,
                output_type TEXT NOT NULL,
                content TEXT,
                text TEXT,
                file_url TEXT,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                download_url TEXT NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL
            )
            """
        )
        output_columns = {row[1] for row in conn.execute("PRAGMA table_info(outputs)").fetchall()}
        if "task_id" not in output_columns:
            conn.execute("ALTER TABLE outputs ADD COLUMN task_id TEXT")
        if "user_id" not in output_columns:
            conn.execute("ALTER TABLE outputs ADD COLUMN user_id TEXT")
        if "content" not in output_columns:
            conn.execute("ALTER TABLE outputs ADD COLUMN content TEXT")
        if "text" not in output_columns:
            conn.execute("ALTER TABLE outputs ADD COLUMN text TEXT")
        if "file_url" not in output_columns:
            conn.execute("ALTER TABLE outputs ADD COLUMN file_url TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_updated ON tasks(status, updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_outputs_task_user ON outputs(task_id, user_id)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS community_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE NOT NULL,
                author_user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                likes INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        community_post_columns = {row[1] for row in conn.execute("PRAGMA table_info(community_posts)").fetchall()}
        if "updated_at" not in community_post_columns:
            conn.execute("ALTER TABLE community_posts ADD COLUMN updated_at DATETIME")
        conn.execute(
            """
            UPDATE community_posts
            SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            WHERE updated_at IS NULL
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
        # Remove legacy demo rows from deployments that already ran the old seed
        # block; delete by exact known fixture IDs only so real user-created data
        # is not affected.
        conn.execute("DELETE FROM agents WHERE agent_id IN ('agt_research_alpha', 'agt_builder_bot', 'agt_social_sentinel', 'agt_strat_mind')")
        conn.execute("DELETE FROM deployments WHERE deployment_id IN ('dep_prod', 'dep_stage', 'dep_dev')")
        conn.execute("DELETE FROM workflows WHERE workflow_id IN ('wf_market_scan', 'wf_deploy_check', 'wf_content_loop')")
        conn.execute("DELETE FROM workflow_runs WHERE run_id IN ('run_001', 'run_002', 'run_003')")
        conn.execute("DELETE FROM tasks WHERE task_id IN ('tsk_001', 'tsk_002', 'tsk_003')")
        conn.execute("DELETE FROM outputs WHERE output_id IN ('out_001', 'out_002')")
        conn.execute("DELETE FROM community_posts WHERE post_id IN ('post_001', 'post_002')")
        conn.execute("DELETE FROM activity_log WHERE source='system' AND action='Initial platform dataset seeded'")
        conn.execute("DELETE FROM activity_log WHERE source='deployment' AND action='Production cluster health check passed'")
        conn.execute("DELETE FROM deployment_metrics WHERE deployment_id IN ('dep_prod', 'dep_stage')")
        conn.execute("DELETE FROM ops_alerts WHERE alert_id IN ('alert_001', 'alert_002')")
        conn.execute("DELETE FROM observability_metrics WHERE metric_name IN ('api_requests_per_min', 'api_error_rate') AND labels_json = '{\"service\":\"api\"}'")
        conn.commit()


_POSTGRES_TABLE_DDL = [
    """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        email TEXT,
        password_hash TEXT,
        display_name TEXT,
        bio TEXT,
        avatar_url TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS auth_sessions (
        id SERIAL PRIMARY KEY,
        session_token_hash TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL,
        token TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        tx_signature TEXT UNIQUE,
        intent_reference TEXT,
        user_wallet TEXT,
        agent_token_mint TEXT,
        currency_mint TEXT,
        currency_symbol TEXT,
        amount_smallest_unit BIGINT,
        memo BIGINT,
        start_time BIGINT,
        end_time BIGINT,
        invoice_id TEXT,
        recipient_address TEXT,
        payer_wallet TEXT,
        chain TEXT,
        mint_address TEXT,
        amount_expected NUMERIC,
        amount_received NUMERIC,
        confirmation_status TEXT,
        block_time BIGINT,
        slot BIGINT,
        verification_status TEXT,
        failure_reason TEXT,
        updated_at TIMESTAMPTZ,
        verified_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS access_grants (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        feature_name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        payment_id INTEGER,
        intent_reference TEXT,
        grant_scope TEXT,
        source TEXT,
        plan_id TEXT,
        product_id TEXT,
        tool_id TEXT,
        expires_at TIMESTAMPTZ,
        revoked_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ,
        metadata_json TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS idempotency_records (
        id SERIAL PRIMARY KEY,
        operation_scope TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        payload_hash TEXT NOT NULL,
        response_json TEXT,
        status_code INTEGER,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(operation_scope, idempotency_key)
    )""",
    """CREATE TABLE IF NOT EXISTS payment_intents (
        reference TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        token TEXT NOT NULL,
        expires_at_epoch INTEGER NOT NULL,
        consumed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        user_wallet TEXT,
        agent_token_mint TEXT,
        currency_mint TEXT,
        currency_symbol TEXT,
        amount_smallest_unit BIGINT,
        memo BIGINT,
        start_time BIGINT,
        end_time BIGINT,
        invoice_id TEXT,
        plan_id TEXT,
        product_id TEXT,
        tool_id TEXT,
        access_tier TEXT,
        amount_expected NUMERIC,
        recipient_address TEXT,
        expected_wallet TEXT,
        status TEXT,
        tx_signature TEXT,
        verification_status TEXT,
        updated_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        failed_at TIMESTAMPTZ,
        canceled_at TIMESTAMPTZ,
        failure_reason TEXT,
        metadata_json TEXT,
        mint_address TEXT,
        currency TEXT,
        chain TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS scheduled_jobs (
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
    )""",
    """CREATE TABLE IF NOT EXISTS job_runs (
        id TEXT PRIMARY KEY,
        scheduled_job_id TEXT NOT NULL REFERENCES scheduled_jobs(id),
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        output_summary TEXT,
        error_message TEXT,
        model_used TEXT,
        tokens_used INTEGER NOT NULL DEFAULT 0,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS agent_findings (
        id TEXT PRIMARY KEY,
        source_job_id TEXT REFERENCES scheduled_jobs(id),
        finding_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        summary TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        created_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS executions (
        id SERIAL PRIMARY KEY,
        execution_id TEXT UNIQUE NOT NULL,
        source_type TEXT,
        source_id TEXT,
        user_id TEXT,
        agent_id TEXT,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS execution_steps (
        id SERIAL PRIMARY KEY,
        step_id TEXT UNIQUE NOT NULL,
        execution_id TEXT NOT NULL REFERENCES executions(execution_id),
        step_order INTEGER NOT NULL DEFAULT 0,
        step_type TEXT NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS execution_events (
        id SERIAL PRIMARY KEY,
        event_id TEXT UNIQUE NOT NULL,
        execution_id TEXT NOT NULL REFERENCES executions(execution_id),
        step_id TEXT REFERENCES execution_steps(step_id),
        event_type TEXT NOT NULL,
        level TEXT NOT NULL DEFAULT 'info',
        message TEXT,
        payload_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS execution_artifacts (
        id SERIAL PRIMARY KEY,
        artifact_id TEXT UNIQUE NOT NULL,
        execution_id TEXT NOT NULL REFERENCES executions(execution_id),
        step_id TEXT REFERENCES execution_steps(step_id),
        artifact_type TEXT NOT NULL,
        name TEXT NOT NULL,
        uri TEXT,
        content_text TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS execution_costs (
        id SERIAL PRIMARY KEY,
        cost_id TEXT UNIQUE NOT NULL,
        execution_id TEXT NOT NULL REFERENCES executions(execution_id),
        step_id TEXT REFERENCES execution_steps(step_id),
        provider TEXT,
        model TEXT,
        input_tokens INTEGER NOT NULL DEFAULT 0,
        output_tokens INTEGER NOT NULL DEFAULT 0,
        cost_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
        cost_currency TEXT NOT NULL DEFAULT 'USD',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS execution_approvals (
        id SERIAL PRIMARY KEY,
        approval_id TEXT UNIQUE NOT NULL,
        execution_id TEXT NOT NULL REFERENCES executions(execution_id),
        step_id TEXT REFERENCES execution_steps(step_id),
        approval_type TEXT NOT NULL,
        status TEXT NOT NULL,
        requested_by TEXT,
        approved_by TEXT,
        requested_at TEXT NOT NULL,
        decided_at TEXT,
        reason TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS marketplace_listings (
        id SERIAL PRIMARY KEY,
        listing_id TEXT UNIQUE NOT NULL,
        creator_user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        pricing_model TEXT NOT NULL,
        price_amount DOUBLE PRECISION NOT NULL,
        price_token TEXT NOT NULL,
        status TEXT NOT NULL,
        tags_json TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        published_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS creator_earnings_events (
        id SERIAL PRIMARY KEY,
        creator_user_id TEXT NOT NULL,
        listing_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        gross_amount DOUBLE PRECISION NOT NULL,
        fee_amount DOUBLE PRECISION NOT NULL,
        creator_amount DOUBLE PRECISION NOT NULL,
        token TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS creator_payout_requests (
        id SERIAL PRIMARY KEY,
        request_id TEXT UNIQUE NOT NULL,
        creator_user_id TEXT NOT NULL,
        requested_amount DOUBLE PRECISION NOT NULL,
        token TEXT NOT NULL,
        destination_wallet TEXT NOT NULL,
        note TEXT,
        status TEXT NOT NULL,
        rejection_reason TEXT,
        tx_signature TEXT,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        approved_at TIMESTAMPTZ,
        rejected_at TIMESTAMPTZ,
        paid_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS agents (
        id SERIAL PRIMARY KEY,
        agent_id TEXT UNIQUE NOT NULL,
        owner_user_id TEXT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        tasks_completed INTEGER NOT NULL DEFAULT 0,
        success_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS deployments (
        id SERIAL PRIMARY KEY,
        deployment_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        environment TEXT NOT NULL,
        status TEXT NOT NULL,
        region TEXT NOT NULL,
        agents_count INTEGER NOT NULL DEFAULT 0,
        cpu_percent INTEGER NOT NULL DEFAULT 0,
        memory_percent INTEGER NOT NULL DEFAULT 0,
        requests_per_day INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS workflows (
        id SERIAL PRIMARY KEY,
        workflow_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        runs_total INTEGER NOT NULL DEFAULT 0,
        success_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS workflow_runs (
        id SERIAL PRIMARY KEY,
        run_id TEXT UNIQUE NOT NULL,
        workflow_id TEXT NOT NULL,
        status TEXT NOT NULL,
        duration_ms INTEGER NOT NULL DEFAULT 0,
        started_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        task_id TEXT UNIQUE NOT NULL,
        user_id TEXT,
        agent_id TEXT,
        type TEXT NOT NULL DEFAULT 'general',
        title TEXT NOT NULL,
        status TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'medium',
        assigned_to TEXT,
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS outputs (
        id SERIAL PRIMARY KEY,
        output_id TEXT UNIQUE NOT NULL,
        task_id TEXT,
        user_id TEXT,
        title TEXT NOT NULL,
        output_type TEXT NOT NULL,
        content TEXT,
        text TEXT,
        file_url TEXT,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        download_url TEXT NOT NULL DEFAULT '',
        created_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS community_posts (
        id SERIAL PRIMARY KEY,
        post_id TEXT UNIQUE NOT NULL,
        author_user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        likes INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        notification_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS user_preferences (
        id SERIAL PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        notifications_email INTEGER NOT NULL DEFAULT 1,
        notifications_push INTEGER NOT NULL DEFAULT 1,
        notifications_marketing INTEGER NOT NULL DEFAULT 0,
        theme TEXT NOT NULL DEFAULT 'dark',
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS marketplace_entitlements (
        id SERIAL PRIMARY KEY,
        listing_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        installed_at TIMESTAMPTZ NOT NULL,
        UNIQUE(listing_id, user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS activity_log (id SERIAL PRIMARY KEY, source TEXT NOT NULL, action TEXT NOT NULL, occurred_at TIMESTAMPTZ NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS deployment_metrics (
        id SERIAL PRIMARY KEY,
        deployment_id TEXT NOT NULL,
        cpu_percent DOUBLE PRECISION NOT NULL,
        memory_percent DOUBLE PRECISION NOT NULL,
        p95_latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0,
        error_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
        recorded_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS workflow_nodes (
        id SERIAL PRIMARY KEY,
        workflow_id TEXT NOT NULL,
        node_id TEXT NOT NULL,
        node_type TEXT NOT NULL,
        config_json TEXT NOT NULL,
        position_json TEXT NOT NULL,
        UNIQUE(workflow_id, node_id)
    )""",
    """CREATE TABLE IF NOT EXISTS task_logs (id SERIAL PRIMARY KEY, task_id TEXT NOT NULL, level TEXT NOT NULL, message TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS user_profile_extras (
        id SERIAL PRIMARY KEY,
        user_id TEXT UNIQUE NOT NULL,
        timezone TEXT,
        language TEXT,
        website_url TEXT,
        location TEXT,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS api_keys (
        id SERIAL PRIMARY KEY,
        key_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        key_hash TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        last_used_at TIMESTAMPTZ
    )""",
    """CREATE TABLE IF NOT EXISTS user_integrations (
        id SERIAL PRIMARY KEY,
        user_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        status TEXT NOT NULL,
        config_json TEXT NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        UNIQUE(user_id, provider)
    )""",
    """CREATE TABLE IF NOT EXISTS staking_positions (
        id SERIAL PRIMARY KEY,
        position_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        token TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL,
        apy DOUBLE PRECISION NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS rewards_ledger (
        id SERIAL PRIMARY KEY,
        entry_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        token TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL,
        source TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS marketplace_install_events (
        id SERIAL PRIMARY KEY,
        event_id TEXT UNIQUE NOT NULL,
        listing_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS audit_events (
        id SERIAL PRIMARY KEY,
        event_id TEXT UNIQUE NOT NULL,
        actor_user_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_id TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS ops_alerts (
        id SERIAL PRIMARY KEY,
        alert_id TEXT UNIQUE NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS observability_metrics (
        id SERIAL PRIMARY KEY,
        metric_name TEXT NOT NULL,
        metric_value DOUBLE PRECISION NOT NULL,
        labels_json TEXT NOT NULL,
        recorded_at TIMESTAMPTZ NOT NULL
    )""",
]

_POSTGRES_INDEX_DDL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    "CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_tx_signature ON payments(tx_signature)",
    "CREATE INDEX IF NOT EXISTS idx_payments_intent_reference ON payments(intent_reference)",
    "CREATE INDEX IF NOT EXISTS idx_payments_invoice_id ON payments(invoice_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_user_status_created ON payments(user_id, status, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_payment_intents_user_status_created ON payment_intents(user_id, status, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_payment_intents_status_expires ON payment_intents(status, expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_payment_intents_invoice_id ON payment_intents(invoice_id)",
    "CREATE INDEX IF NOT EXISTS idx_payment_intents_memo_time ON payment_intents(memo, start_time, end_time)",
    "CREATE INDEX IF NOT EXISTS idx_payment_intents_tx_signature ON payment_intents(tx_signature)",
    "CREATE INDEX IF NOT EXISTS idx_access_grants_user_feature_status ON access_grants(user_id, feature_name, status)",
    "CREATE INDEX IF NOT EXISTS idx_access_grants_user_scope_status ON access_grants(user_id, grant_scope, status)",
    "CREATE INDEX IF NOT EXISTS idx_access_grants_payment_id ON access_grants(payment_id)",
    "CREATE INDEX IF NOT EXISTS idx_access_grants_intent_reference ON access_grants(intent_reference)",
    "CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_enabled_next_run ON scheduled_jobs(enabled, next_run_at)",
    "CREATE INDEX IF NOT EXISTS idx_job_runs_job_started ON job_runs(scheduled_job_id, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_agent_findings_source ON agent_findings(source_job_id)",
    "CREATE INDEX IF NOT EXISTS idx_executions_status_started ON executions(status, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_executions_user_started ON executions(user_id, started_at)",
    "CREATE INDEX IF NOT EXISTS idx_execution_steps_execution_order ON execution_steps(execution_id, step_order)",
    "CREATE INDEX IF NOT EXISTS idx_execution_events_execution_created ON execution_events(execution_id, created_at)",
    "CREATE INDEX IF NOT EXISTS idx_execution_artifacts_execution ON execution_artifacts(execution_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_costs_execution ON execution_costs(execution_id)",
    "CREATE INDEX IF NOT EXISTS idx_execution_approvals_execution_status ON execution_approvals(execution_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_agents_owner_user_id ON agents(owner_user_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_status_updated ON tasks(status, updated_at)",
    "CREATE INDEX IF NOT EXISTS idx_outputs_task_user ON outputs(task_id, user_id)",
]

_POSTGRES_COLUMN_MIGRATIONS = {
    "users": [
        ("email", "TEXT"), ("password_hash", "TEXT"), ("display_name", "TEXT"),
        ("bio", "TEXT"), ("avatar_url", "TEXT"), ("updated_at", "TIMESTAMPTZ"),
    ],
    "payments": [
        ("tx_signature", "TEXT"),
        ("intent_reference", "TEXT"),
        ("user_wallet", "TEXT"),
        ("agent_token_mint", "TEXT"),
        ("currency_mint", "TEXT"),
        ("currency_symbol", "TEXT"),
        ("amount_smallest_unit", "BIGINT"),
        ("memo", "BIGINT"),
        ("start_time", "BIGINT"),
        ("end_time", "BIGINT"),
        ("invoice_id", "TEXT"),
        ("recipient_address", "TEXT"),
        ("payer_wallet", "TEXT"),
        ("chain", "TEXT"),
        ("mint_address", "TEXT"),
        ("amount_expected", "NUMERIC"),
        ("amount_received", "NUMERIC"),
        ("confirmation_status", "TEXT"),
        ("block_time", "BIGINT"),
        ("slot", "BIGINT"),
        ("verification_status", "TEXT"),
        ("failure_reason", "TEXT"),
        ("updated_at", "TIMESTAMPTZ"),
        ("verified_at", "TIMESTAMPTZ"),
    ],
    "access_grants": [
        ("payment_id", "INTEGER"),
        ("intent_reference", "TEXT"),
        ("grant_scope", "TEXT"),
        ("source", "TEXT"),
        ("plan_id", "TEXT"),
        ("product_id", "TEXT"),
        ("tool_id", "TEXT"),
        ("expires_at", "TIMESTAMPTZ"),
        ("revoked_at", "TIMESTAMPTZ"),
        ("updated_at", "TIMESTAMPTZ"),
        ("metadata_json", "TEXT"),
    ],
    "payment_intents": [
        ("user_wallet", "TEXT"),
        ("agent_token_mint", "TEXT"),
        ("currency_mint", "TEXT"),
        ("currency_symbol", "TEXT"),
        ("amount_smallest_unit", "BIGINT"),
        ("memo", "BIGINT"),
        ("start_time", "BIGINT"),
        ("end_time", "BIGINT"),
        ("invoice_id", "TEXT"),
        ("plan_id", "TEXT"),
        ("product_id", "TEXT"),
        ("tool_id", "TEXT"),
        ("access_tier", "TEXT"),
        ("amount_expected", "NUMERIC"),
        ("recipient_address", "TEXT"),
        ("expected_wallet", "TEXT"),
        ("status", "TEXT"),
        ("tx_signature", "TEXT"),
        ("verification_status", "TEXT"),
        ("updated_at", "TIMESTAMPTZ"),
        ("expires_at", "TIMESTAMPTZ"),
        ("completed_at", "TIMESTAMPTZ"),
        ("failed_at", "TIMESTAMPTZ"),
        ("canceled_at", "TIMESTAMPTZ"),
        ("failure_reason", "TEXT"),
        ("metadata_json", "TEXT"),
        ("mint_address", "TEXT"),
        ("currency", "TEXT"),
        ("chain", "TEXT"),
    ],
    "agents": [("owner_user_id", "TEXT")],
    "tasks": [
        ("user_id", "TEXT"), ("agent_id", "TEXT"), ("type", "TEXT NOT NULL DEFAULT 'general'"),
        ("error_message", "TEXT"), ("created_at", "TIMESTAMPTZ"),
    ],
    "outputs": [("task_id", "TEXT"), ("user_id", "TEXT"), ("content", "TEXT"), ("text", "TEXT"), ("file_url", "TEXT")],
    "community_posts": [("updated_at", "TIMESTAMPTZ")],
}


def _postgres_column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
        """,
        (table, column),
    ).fetchone()
    return row is not None


def _init_postgres_db():
    with get_connection() as conn:
        for ddl in _POSTGRES_TABLE_DDL:
            conn.execute(ddl)
        for table, columns in _POSTGRES_COLUMN_MIGRATIONS.items():
            for column, column_type in columns:
                if not _postgres_column_exists(conn, table, column):
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
        conn.execute("UPDATE users SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL")
        conn.execute("UPDATE tasks SET created_at = COALESCE(created_at, updated_at, CURRENT_TIMESTAMP) WHERE created_at IS NULL")
        conn.execute("UPDATE community_posts SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) WHERE updated_at IS NULL")
        for ddl in _POSTGRES_INDEX_DDL:
            conn.execute(ddl)
        _seed_default_scheduled_jobs(conn)
        _remove_legacy_demo_rows(conn)
        conn.commit()


def _remove_legacy_demo_rows(conn) -> None:
    conn.execute("DELETE FROM agents WHERE agent_id IN ('agt_research_alpha', 'agt_builder_bot', 'agt_social_sentinel', 'agt_strat_mind')")
    conn.execute("DELETE FROM deployments WHERE deployment_id IN ('dep_prod', 'dep_stage', 'dep_dev')")
    conn.execute("DELETE FROM workflows WHERE workflow_id IN ('wf_market_scan', 'wf_deploy_check', 'wf_content_loop')")
    conn.execute("DELETE FROM workflow_runs WHERE run_id IN ('run_001', 'run_002', 'run_003')")
    conn.execute("DELETE FROM tasks WHERE task_id IN ('tsk_001', 'tsk_002', 'tsk_003')")
    conn.execute("DELETE FROM outputs WHERE output_id IN ('out_001', 'out_002')")
    conn.execute("DELETE FROM community_posts WHERE post_id IN ('post_001', 'post_002')")
    conn.execute("DELETE FROM activity_log WHERE source='system' AND action='Initial platform dataset seeded'")
    conn.execute("DELETE FROM activity_log WHERE source='deployment' AND action='Production cluster health check passed'")
    conn.execute("DELETE FROM deployment_metrics WHERE deployment_id IN ('dep_prod', 'dep_stage')")
    conn.execute("DELETE FROM ops_alerts WHERE alert_id IN ('alert_001', 'alert_002')")
    conn.execute("DELETE FROM observability_metrics WHERE metric_name IN ('api_requests_per_min', 'api_error_rate') AND labels_json = '{\"service\":\"api\"}'")


def init_db():
    if _using_postgres():
        _init_postgres_db()
    else:
        _init_sqlite_db()
