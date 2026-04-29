import os
import sqlite3
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


PUMPFUN_AGENT_TOKEN_MINT = "9jwExoB9h42bNeUyCH8qBJAye3NJGrToiX62DQTEpump"
PUMPFUN_WSOL_MINT = "So11111111111111111111111111111111111111112"
PUMPFUN_CURRENCY_SYMBOL = "SOL"
PUMPFUN_AMOUNT_SMALLEST_UNIT = 100_000_000

PAYMENT_INTENT_REQUIRED_COLUMNS = {
    "reference",
    "user_id",
    "user_wallet",
    "agent_token_mint",
    "currency_mint",
    "currency_symbol",
    "amount_smallest_unit",
    "memo",
    "start_time",
    "end_time",
    "invoice_id",
    "status",
    "tx_signature",
    "verification_status",
    "created_at",
    "updated_at",
    "expires_at",
    "completed_at",
    "failure_reason",
    "metadata_json",
}
PAYMENT_INTENT_SCOPE_COLUMNS = {"plan_id", "product_id", "tool_id", "access_tier"}

PAYMENT_REQUIRED_COLUMNS = {
    "intent_reference",
    "user_id",
    "user_wallet",
    "agent_token_mint",
    "currency_mint",
    "currency_symbol",
    "amount_smallest_unit",
    "memo",
    "start_time",
    "end_time",
    "invoice_id",
    "tx_signature",
    "block_time",
    "slot",
    "verification_status",
    "created_at",
    "updated_at",
    "verified_at",
    "failure_reason",
}
PAYMENT_FINALITY_COLUMNS = {"confirmation_status", "finality"}

ACCESS_GRANT_REQUIRED_COLUMNS = {
    "payment_id",
    "grant_scope",
    "source",
    "plan_id",
    "product_id",
    "tool_id",
    "expires_at",
    "revoked_at",
    "updated_at",
    "metadata_json",
}
ACCESS_GRANT_INTENT_COLUMNS = {"intent_reference", "payment_intent_id"}
ACCESS_GRANT_ACTIVE_REPLAY_UNIQUE_INDEXES = {
    ("user_id", "feature_name", "intent_reference"),
    ("user_id", "feature_name", "payment_id"),
}

LEGACY_EXPECTED_COLUMNS = {
    "payment_intents": {"reference", "user_id", "token", "expires_at_epoch", "consumed_at", "created_at"},
    "payments": {"id", "user_id", "amount", "token", "status", "created_at", "tx_signature"},
    "access_grants": {"id", "user_id", "feature_name", "status", "created_at"},
}


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _indexes(conn: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return conn.execute(f"PRAGMA index_list({table})").fetchall()


def _unique_index_columns(conn: sqlite3.Connection, table: str) -> set[tuple[str, ...]]:
    unique_columns: set[tuple[str, ...]] = set()
    for index in _indexes(conn, table):
        if not index[2]:
            continue
        rows = conn.execute(f"PRAGMA index_info({index[1]})").fetchall()
        unique_columns.add(tuple(row[2] for row in rows))
    return unique_columns


def _build_legacy_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE payment_intents (
                reference TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token TEXT NOT NULL,
                expires_at_epoch INTEGER NOT NULL,
                consumed_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE payments (
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
        conn.execute(
            """
            CREATE TABLE access_grants (
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
            INSERT INTO payment_intents(reference, user_id, token, expires_at_epoch, consumed_at)
            VALUES ('legacy-ref-1', 'legacy-user', 'SOL', 4102444800, NULL)
            """
        )
        conn.execute(
            """
            INSERT INTO payments(user_id, amount, token, status, tx_signature)
            VALUES ('legacy-user', 0.1, 'SOL', 'completed', ?)
            """,
            ("4" * 88,),
        )
        conn.execute(
            """
            INSERT INTO access_grants(user_id, feature_name, status)
            VALUES ('legacy-user', 'random_number', 'active')
            """
        )
        conn.commit()


@pytest.fixture()
def migrated_legacy_db(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy-agentascend.db"
    _build_legacy_db(db_path)

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    session._init_sqlite_db()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        yield conn


@pytest.fixture()
def fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh-agentascend.db"

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    session._init_sqlite_db()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        yield conn


def test_fresh_payment_intents_schema_has_pumpfun_invoice_columns(fresh_db):
    columns = _columns(fresh_db, "payment_intents")

    assert PAYMENT_INTENT_REQUIRED_COLUMNS <= columns
    assert PAYMENT_INTENT_SCOPE_COLUMNS & columns


def test_fresh_payments_schema_has_pumpfun_invoice_payment_columns(fresh_db):
    columns = _columns(fresh_db, "payments")

    assert PAYMENT_REQUIRED_COLUMNS <= columns
    assert PAYMENT_FINALITY_COLUMNS & columns


def test_fresh_access_grants_schema_has_target_additive_columns(fresh_db):
    columns = _columns(fresh_db, "access_grants")

    assert ACCESS_GRANT_REQUIRED_COLUMNS <= columns
    assert ACCESS_GRANT_INTENT_COLUMNS & columns


def test_payments_tx_signature_unique_constraint_survives_migration(migrated_legacy_db):
    unique_columns = _unique_index_columns(migrated_legacy_db, "payments")

    assert ("tx_signature",) in unique_columns
    with pytest.raises(sqlite3.IntegrityError):
        migrated_legacy_db.execute(
            """
            INSERT INTO payments(user_id, amount, token, status, tx_signature)
            VALUES ('other-user', 0.2, 'SOL', 'completed', ?)
            """,
            ("4" * 88,),
        )


def test_additive_migration_preserves_legacy_rows_and_columns(migrated_legacy_db):
    for table, expected_columns in LEGACY_EXPECTED_COLUMNS.items():
        assert expected_columns <= _columns(migrated_legacy_db, table)

    assert migrated_legacy_db.execute("SELECT COUNT(*) FROM payment_intents").fetchone()[0] == 1
    assert migrated_legacy_db.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 1
    assert migrated_legacy_db.execute("SELECT COUNT(*) FROM access_grants").fetchone()[0] == 1

    payment_intent = migrated_legacy_db.execute(
        "SELECT reference, user_id, token, expires_at_epoch FROM payment_intents"
    ).fetchone()
    assert dict(payment_intent) == {
        "reference": "legacy-ref-1",
        "user_id": "legacy-user",
        "token": "SOL",
        "expires_at_epoch": 4102444800,
    }


def test_additive_migration_adds_pumpfun_invoice_columns_to_legacy_tables(migrated_legacy_db):
    intent_columns = _columns(migrated_legacy_db, "payment_intents")
    payment_columns = _columns(migrated_legacy_db, "payments")
    grant_columns = _columns(migrated_legacy_db, "access_grants")

    assert PAYMENT_INTENT_REQUIRED_COLUMNS <= intent_columns
    assert PAYMENT_INTENT_SCOPE_COLUMNS & intent_columns
    assert PAYMENT_REQUIRED_COLUMNS <= payment_columns
    assert PAYMENT_FINALITY_COLUMNS & payment_columns
    assert ACCESS_GRANT_REQUIRED_COLUMNS <= grant_columns
    assert ACCESS_GRANT_INTENT_COLUMNS & grant_columns


def test_access_grants_replay_unique_indexes_exist_when_no_duplicate_legacy_rows(migrated_legacy_db):
    unique_columns = _unique_index_columns(migrated_legacy_db, "access_grants")
    assert ACCESS_GRANT_ACTIVE_REPLAY_UNIQUE_INDEXES <= unique_columns


def test_additive_migration_is_idempotent_for_legacy_db(tmp_path, monkeypatch):
    db_path = tmp_path / "idempotent-agentascend.db"
    _build_legacy_db(db_path)

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    session._init_sqlite_db()
    session._init_sqlite_db()

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM payment_intents").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM access_grants").fetchone()[0] == 1
        assert PAYMENT_INTENT_REQUIRED_COLUMNS <= _columns(conn, "payment_intents")
        assert PAYMENT_REQUIRED_COLUMNS <= _columns(conn, "payments")
        assert ACCESS_GRANT_REQUIRED_COLUMNS <= _columns(conn, "access_grants")


def test_migration_skips_replay_unique_indexes_when_duplicate_active_grants_exist(tmp_path, monkeypatch):
    db_path = tmp_path / "duplicate-grants-agentascend.db"
    _build_legacy_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("ALTER TABLE access_grants ADD COLUMN intent_reference TEXT")
        conn.execute(
            "UPDATE access_grants SET intent_reference = 'duplicate-ref' WHERE user_id = 'legacy-user' AND feature_name = 'random_number'"
        )
        conn.execute(
            "INSERT INTO access_grants(user_id, feature_name, status, intent_reference) VALUES ('legacy-user', 'random_number', 'active', 'duplicate-ref')"
        )
        conn.commit()

    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", db_path)
    session._init_sqlite_db()

    with sqlite3.connect(db_path) as conn:
        unique_columns = _unique_index_columns(conn, "access_grants")
        assert ("user_id", "feature_name", "intent_reference") not in unique_columns
        assert ("user_id", "feature_name", "payment_id") not in unique_columns


def test_postgres_preflight_skips_replay_unique_indexes_when_duplicates_exist(monkeypatch):
    import backend.app.db.session as session

    executed_sql = []

    class FakeConn:
        def execute(self, sql, params=None):
            executed_sql.append(sql)
            class _Cursor:
                def fetchall(self_inner):
                    return []
            return _Cursor()

    monkeypatch.setattr(
        session,
        "_access_grant_duplicate_samples",
        lambda _conn: ([{"user_id": "u", "feature_name": "f", "intent_reference": "r", "duplicate_count": 2}], []),
    )

    session._create_access_grant_replay_unique_indexes_postgres(FakeConn())

    assert session.ACCESS_GRANTS_ACTIVE_INTENT_UNIQUE_INDEX_SQL not in executed_sql
    assert session.ACCESS_GRANTS_ACTIVE_PAYMENT_UNIQUE_INDEX_SQL not in executed_sql


def test_postgres_preflight_creates_replay_unique_indexes_when_no_duplicates(monkeypatch):
    import backend.app.db.session as session

    executed_sql = []

    class FakeConn:
        def execute(self, sql, params=None):
            executed_sql.append(sql)

            class _Cursor:
                def fetchall(self_inner):
                    return []

            return _Cursor()

    monkeypatch.setattr(session, "_access_grant_duplicate_samples", lambda _conn: ([], []))

    session._create_access_grant_replay_unique_indexes_postgres(FakeConn())

    assert session.ACCESS_GRANTS_ACTIVE_INTENT_UNIQUE_INDEX_SQL in executed_sql
    assert session.ACCESS_GRANTS_ACTIVE_PAYMENT_UNIQUE_INDEX_SQL in executed_sql


def test_replay_preflight_skip_log_is_structured_and_redacted(caplog, monkeypatch):
    import backend.app.db.session as session

    class FakeConn:
        def execute(self, sql, params=None):
            class _Cursor:
                def fetchall(self_inner):
                    return []

            return _Cursor()

    monkeypatch.setattr(
        session,
        "_access_grant_duplicate_samples",
        lambda _conn: (
            [{"user_id": "u1", "feature_name": "f1", "intent_reference": "intent_secret_123456", "duplicate_count": 2}],
            [{"user_id": "u1", "feature_name": "f1", "payment_id": "sig_secret_abcdef", "duplicate_count": 2}],
        ),
    )

    with caplog.at_level("WARNING"):
        session._create_access_grant_replay_unique_indexes_postgres(FakeConn())

    record = next(r for r in caplog.records if "Skipping replay index creation" in r.message)
    assert getattr(record, "db_type") == "postgres"
    assert getattr(record, "action") == "skip_replay_index_creation"
    assert getattr(record, "duplicate_category") == "active_access_grants_replay_keys"
    assert getattr(record, "duplicate_intent_rows")[0]["intent_reference"].startswith("***")
    assert getattr(record, "duplicate_payment_rows")[0]["payment_id"].startswith("***")
    assert "intent_secret_123456" not in str(getattr(record, "duplicate_intent_rows"))
    assert "sig_secret_abcdef" not in str(getattr(record, "duplicate_payment_rows"))


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_DSN"), reason="TEST_POSTGRES_DSN not set")
def test_postgres_integration_replay_index_preflight_paths():
    psycopg2 = pytest.importorskip("psycopg2")

    import backend.app.db.session as session

    dsn = os.environ["TEST_POSTGRES_DSN"]
    schema = f"agentascend_test_{uuid.uuid4().hex[:10]}"

    raw_conn = psycopg2.connect(dsn)
    raw_conn.autocommit = True
    adapter = session.PostgresConnectionAdapter(raw_conn)

    try:
        adapter.execute(f"CREATE SCHEMA {schema}")
        adapter.execute(f"SET search_path TO {schema}")
        adapter.execute(
            """
            CREATE TABLE access_grants (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                status TEXT NOT NULL,
                intent_reference TEXT,
                payment_id INTEGER
            )
            """
        )

        # Duplicate path: should skip both indexes
        adapter.execute(
            """
            INSERT INTO access_grants(user_id, feature_name, status, intent_reference, payment_id)
            VALUES
                ('u1', 'random_number', 'active', 'dup-ref', NULL),
                ('u1', 'random_number', 'active', 'dup-ref', NULL)
            """
        )
        session._create_access_grant_replay_unique_indexes_postgres(adapter)
        idx_rows = adapter.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = %s AND tablename = 'access_grants'",
            (schema,),
        ).fetchall()
        idx_names = {row["indexname"] for row in idx_rows}
        assert "idx_access_grants_active_user_feature_intent_unique" not in idx_names
        assert "idx_access_grants_active_user_feature_payment_unique" not in idx_names

        # Clean path: should create both indexes
        adapter.execute("TRUNCATE TABLE access_grants")
        session._create_access_grant_replay_unique_indexes_postgres(adapter)
        idx_rows = adapter.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = %s AND tablename = 'access_grants'",
            (schema,),
        ).fetchall()
        idx_names = {row["indexname"] for row in idx_rows}
        assert "idx_access_grants_active_user_feature_intent_unique" in idx_names
        assert "idx_access_grants_active_user_feature_payment_unique" in idx_names
    finally:
        try:
            adapter.execute("SET search_path TO public")
            adapter.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        finally:
            raw_conn.close()


def test_pumpfun_invoice_fields_can_store_official_constants_in_temp_db(fresh_db):
    fresh_db.execute(
        """
        INSERT INTO payment_intents(
            reference,
            user_id,
            token,
            expires_at_epoch,
            user_wallet,
            agent_token_mint,
            currency_mint,
            currency_symbol,
            amount_smallest_unit,
            memo,
            start_time,
            end_time,
            invoice_id,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "sdk-invoice-ref-1",
            "sdk-user",
            "SOL",
            4102444800,
            "11111111111111111111111111111111",
            PUMPFUN_AGENT_TOKEN_MINT,
            PUMPFUN_WSOL_MINT,
            PUMPFUN_CURRENCY_SYMBOL,
            PUMPFUN_AMOUNT_SMALLEST_UNIT,
            123456789,
            1_700_000_000,
            1_700_086_400,
            "invoice-pda-placeholder",
            "pending",
        ),
    )
    fresh_db.execute(
        """
        INSERT INTO payments(
            user_id,
            amount,
            token,
            status,
            tx_signature,
            intent_reference,
            user_wallet,
            agent_token_mint,
            currency_mint,
            currency_symbol,
            amount_smallest_unit,
            memo,
            start_time,
            end_time,
            invoice_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "sdk-user",
            0.1,
            "SOL",
            "completed",
            "5" * 88,
            "sdk-invoice-ref-1",
            "11111111111111111111111111111111",
            PUMPFUN_AGENT_TOKEN_MINT,
            PUMPFUN_WSOL_MINT,
            PUMPFUN_CURRENCY_SYMBOL,
            PUMPFUN_AMOUNT_SMALLEST_UNIT,
            123456789,
            1_700_000_000,
            1_700_086_400,
            "invoice-pda-placeholder",
        ),
    )

    intent_row = fresh_db.execute(
        """
        SELECT agent_token_mint, currency_mint, currency_symbol, amount_smallest_unit
        FROM payment_intents
        WHERE reference = 'sdk-invoice-ref-1'
        """
    ).fetchone()
    payment_row = fresh_db.execute(
        """
        SELECT agent_token_mint, currency_mint, currency_symbol, amount_smallest_unit
        FROM payments
        WHERE intent_reference = 'sdk-invoice-ref-1'
        """
    ).fetchone()

    expected = {
        "agent_token_mint": PUMPFUN_AGENT_TOKEN_MINT,
        "currency_mint": PUMPFUN_WSOL_MINT,
        "currency_symbol": PUMPFUN_CURRENCY_SYMBOL,
        "amount_smallest_unit": PUMPFUN_AMOUNT_SMALLEST_UNIT,
    }
    assert dict(intent_row) == expected
    assert dict(payment_row) == expected


def test_schema_migration_uses_only_temp_db_not_repo_db(tmp_path, monkeypatch):
    db_path = tmp_path / "isolated-agentascend.db"

    import backend.app.db.session as session

    repo_db_path = session.DB_PATH
    monkeypatch.setattr(session, "DB_PATH", db_path)
    session._init_sqlite_db()

    assert db_path.exists()
    assert session.DB_PATH == db_path
    assert repo_db_path != db_path
