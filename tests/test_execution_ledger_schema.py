from backend.app.db import session


EXECUTION_LEDGER_TABLES = {
    "executions",
    "execution_steps",
    "execution_events",
    "execution_artifacts",
    "execution_costs",
    "execution_approvals",
}


EXPECTED_COLUMNS = {
    "executions": {
        "execution_id",
        "source_type",
        "source_id",
        "user_id",
        "agent_id",
        "status",
        "started_at",
        "finished_at",
        "metadata_json",
    },
    "execution_steps": {
        "step_id",
        "execution_id",
        "step_order",
        "step_type",
        "name",
        "status",
        "started_at",
        "finished_at",
        "metadata_json",
    },
    "execution_events": {
        "event_id",
        "execution_id",
        "step_id",
        "event_type",
        "level",
        "message",
        "payload_json",
        "created_at",
    },
    "execution_artifacts": {
        "artifact_id",
        "execution_id",
        "step_id",
        "artifact_type",
        "name",
        "uri",
        "content_text",
        "metadata_json",
        "created_at",
    },
    "execution_costs": {
        "cost_id",
        "execution_id",
        "step_id",
        "provider",
        "model",
        "input_tokens",
        "output_tokens",
        "cost_amount",
        "cost_currency",
        "metadata_json",
        "created_at",
    },
    "execution_approvals": {
        "approval_id",
        "execution_id",
        "step_id",
        "approval_type",
        "status",
        "requested_by",
        "approved_by",
        "requested_at",
        "decided_at",
        "reason",
        "metadata_json",
    },
}


EXPECTED_INDEXES = {
    "idx_executions_status_started",
    "idx_executions_user_started",
    "idx_execution_steps_execution_order",
    "idx_execution_events_execution_created",
    "idx_execution_artifacts_execution",
    "idx_execution_costs_execution",
    "idx_execution_approvals_execution_status",
}


def test_execution_ledger_tables_are_created_with_expected_columns(tmp_path):
    db_path = tmp_path / "agentascend-execution-ledger.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        with session.get_connection() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            assert EXECUTION_LEDGER_TABLES.issubset(tables)

            for table_name, expected_columns in EXPECTED_COLUMNS.items():
                columns = {
                    row[1]
                    for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                }
                assert expected_columns.issubset(columns)

                json_columns = [name for name in expected_columns if name.endswith("_json")]
                column_types = {
                    row[1]: row[2]
                    for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                }
                assert all(column_types[column] == "TEXT" for column in json_columns)
    finally:
        session.DB_PATH = original_db_path


def test_execution_ledger_indexes_are_created(tmp_path):
    db_path = tmp_path / "agentascend-execution-ledger-indexes.db"
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    try:
        session.init_db()
        with session.get_connection() as conn:
            indexes = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
            assert EXPECTED_INDEXES.issubset(indexes)
    finally:
        session.DB_PATH = original_db_path


def test_postgres_init_includes_execution_ledger_tables_and_indexes():
    postgres_table_ddl = "\n".join(session._POSTGRES_TABLE_DDL)
    postgres_index_ddl = "\n".join(session._POSTGRES_INDEX_DDL)

    for table_name in EXECUTION_LEDGER_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in postgres_table_ddl

    for index_name in EXPECTED_INDEXES:
        assert index_name in postgres_index_ddl

    assert "metadata_json TEXT" in postgres_table_ddl
    assert "payload_json TEXT" in postgres_table_ddl
