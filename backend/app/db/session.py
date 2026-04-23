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

        conn.commit()
