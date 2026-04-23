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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

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

        conn.commit()
