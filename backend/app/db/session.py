import sqlite3
from pathlib import Path

DB_PATH = Path("backend/app/db/agentascend.db")


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

        agents_count = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        if agents_count == 0:
            conn.executemany(
                """
                INSERT INTO agents(agent_id, name, category, description, status, tasks_completed, success_rate, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                [
                    ("agt_research_alpha", "Research Alpha", "Research", "Analyzing market trends", "active", 156, 98.5),
                    ("agt_builder_bot", "Builder Bot", "Builder", "Deploying smart contracts", "active", 89, 97.2),
                    ("agt_social_sentinel", "Social Sentinel", "Marketing", "Scheduling community campaigns", "idle", 234, 99.1),
                    ("agt_strat_mind", "Strat Mind", "Strategy", "Optimizing portfolio", "active", 67, 94.3),
                ],
            )

        deployments_count = conn.execute("SELECT COUNT(*) FROM deployments").fetchone()[0]
        if deployments_count == 0:
            conn.executemany(
                """
                INSERT INTO deployments(deployment_id, name, environment, status, region, agents_count, cpu_percent, memory_percent, requests_per_day, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                [
                    ("dep_prod", "Production Cluster", "production", "running", "US East", 12, 45, 62, 2400000),
                    ("dep_stage", "Staging Environment", "staging", "running", "US West", 5, 28, 41, 156000),
                    ("dep_dev", "Development Sandbox", "development", "running", "EU Central", 3, 15, 23, 12000),
                ],
            )

        workflows_count = conn.execute("SELECT COUNT(*) FROM workflows").fetchone()[0]
        if workflows_count == 0:
            conn.executemany(
                """
                INSERT INTO workflows(workflow_id, name, status, runs_total, success_rate, updated_at)
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                """,
                [
                    ("wf_market_scan", "Market Scan", "active", 120, 98.0),
                    ("wf_deploy_check", "Deployment Health Check", "active", 220, 99.2),
                    ("wf_content_loop", "Content Loop", "paused", 83, 96.1),
                ],
            )

        workflow_runs_count = conn.execute("SELECT COUNT(*) FROM workflow_runs").fetchone()[0]
        if workflow_runs_count == 0:
            conn.executemany(
                """
                INSERT INTO workflow_runs(run_id, workflow_id, status, duration_ms, started_at)
                VALUES(?, ?, ?, ?, datetime('now'))
                """,
                [
                    ("run_001", "wf_market_scan", "success", 4200),
                    ("run_002", "wf_deploy_check", "success", 1900),
                    ("run_003", "wf_content_loop", "failed", 3100),
                ],
            )

        tasks_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if tasks_count == 0:
            conn.executemany(
                """
                INSERT INTO tasks(task_id, title, status, priority, assigned_to, updated_at)
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                """,
                [
                    ("tsk_001", "Analyze token velocity", "queued", "high", "agt_research_alpha"),
                    ("tsk_002", "Generate campaign copy", "running", "medium", "agt_social_sentinel"),
                    ("tsk_003", "Backfill payout exports", "completed", "low", "agt_builder_bot"),
                ],
            )

        outputs_count = conn.execute("SELECT COUNT(*) FROM outputs").fetchone()[0]
        if outputs_count == 0:
            conn.executemany(
                """
                INSERT INTO outputs(output_id, title, output_type, size_bytes, download_url, created_at)
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                """,
                [
                    ("out_001", "Weekly market report", "report", 184320, "/downloads/out_001"),
                    ("out_002", "Deployment diagnostics", "log", 12048, "/downloads/out_002"),
                ],
            )

        posts_count = conn.execute("SELECT COUNT(*) FROM community_posts").fetchone()[0]
        if posts_count == 0:
            conn.executemany(
                """
                INSERT INTO community_posts(post_id, author_user_id, title, body, likes, created_at)
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                """,
                [
                    ("post_001", "creator_alpha", "How I scaled my agent", "Playbook for scaling automation.", 32),
                    ("post_002", "creator_beta", "Prompt QA checklist", "Checklist for stable outputs.", 21),
                ],
            )

        activity_count = conn.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
        if activity_count == 0:
            conn.executemany(
                """
                INSERT INTO activity_log(source, action, occurred_at)
                VALUES(?, ?, datetime('now'))
                """,
                [
                    ("system", "Initial platform dataset seeded"),
                    ("deployment", "Production cluster health check passed"),
                ],
            )

        metrics_count = conn.execute("SELECT COUNT(*) FROM deployment_metrics").fetchone()[0]
        if metrics_count == 0:
            conn.executemany(
                """
                INSERT INTO deployment_metrics(deployment_id, cpu_percent, memory_percent, p95_latency_ms, error_rate, recorded_at)
                VALUES(?, ?, ?, ?, ?, datetime('now'))
                """,
                [
                    ("dep_prod", 42, 61, 188, 0.3),
                    ("dep_stage", 27, 40, 215, 0.5),
                ],
            )

        alerts_count = conn.execute("SELECT COUNT(*) FROM ops_alerts").fetchone()[0]
        if alerts_count == 0:
            conn.executemany(
                """
                INSERT INTO ops_alerts(alert_id, severity, title, message, status, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                [
                    ("alert_001", "warning", "Elevated retry rate", "Payments verify retries above baseline", "open"),
                    ("alert_002", "info", "Daily backup complete", "SQLite snapshot completed", "resolved"),
                ],
            )

        observability_count = conn.execute("SELECT COUNT(*) FROM observability_metrics").fetchone()[0]
        if observability_count == 0:
            conn.executemany(
                """
                INSERT INTO observability_metrics(metric_name, metric_value, labels_json, recorded_at)
                VALUES(?, ?, ?, datetime('now'))
                """,
                [
                    ("api_requests_per_min", 72, '{"service":"api"}'),
                    ("api_error_rate", 0.4, '{"service":"api"}'),
                ],
            )

        conn.commit()
