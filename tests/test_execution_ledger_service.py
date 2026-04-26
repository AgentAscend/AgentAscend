import json

from backend.app.db import session
from backend.app.services import execution_ledger


def _use_temp_db(db_path):
    original_db_path = session.DB_PATH
    session.DB_PATH = db_path
    session.init_db()
    return original_db_path


def test_create_execution_creates_row_and_serializes_metadata(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-service.db")
    try:
        created = execution_ledger.create_execution(
            user_id="user_1",
            source_type="task",
            source_id="task_1",
            agent_id="agent_1",
            metadata={"purpose": "unit-test"},
        )

        assert created["execution_id"].startswith("exec_")
        assert created["user_id"] == "user_1"
        assert created["source_type"] == "task"
        assert created["source_id"] == "task_1"
        assert created["agent_id"] == "agent_1"
        assert created["status"] == "pending"
        assert created["metadata"] == {"purpose": "unit-test"}

        with session.get_connection() as conn:
            row = conn.execute(
                "SELECT metadata_json FROM executions WHERE execution_id = ?",
                (created["execution_id"],),
            ).fetchone()
        assert json.loads(row["metadata_json"]) == {"purpose": "unit-test"}
    finally:
        session.DB_PATH = original_db_path


def test_create_execution_step_creates_row(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-step.db")
    try:
        execution = execution_ledger.create_execution(user_id="user_1")

        step = execution_ledger.create_execution_step(
            execution_id=execution["execution_id"],
            step_order=2,
            step_type="tool_call",
            name="Run tool",
            metadata={"tool": "search"},
        )

        assert step["step_id"].startswith("step_")
        assert step["execution_id"] == execution["execution_id"]
        assert step["step_order"] == 2
        assert step["step_type"] == "tool_call"
        assert step["name"] == "Run tool"
        assert step["status"] == "pending"
        assert step["metadata"] == {"tool": "search"}
    finally:
        session.DB_PATH = original_db_path


def test_append_execution_event_creates_event_and_serializes_payload(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-event.db")
    try:
        execution = execution_ledger.create_execution(user_id="user_1")
        step = execution_ledger.create_execution_step(
            execution_id=execution["execution_id"],
            step_order=1,
            step_type="planning",
            name="Plan",
        )

        event = execution_ledger.append_execution_event(
            execution_id=execution["execution_id"],
            event_type="step_started",
            step_id=step["step_id"],
            level="warning",
            message="Step started",
            payload={"attempt": 1},
        )

        assert event["event_id"].startswith("evt_")
        assert event["execution_id"] == execution["execution_id"]
        assert event["step_id"] == step["step_id"]
        assert event["event_type"] == "step_started"
        assert event["level"] == "warning"
        assert event["message"] == "Step started"
        assert event["payload"] == {"attempt": 1}

        with session.get_connection() as conn:
            row = conn.execute(
                "SELECT payload_json FROM execution_events WHERE event_id = ?",
                (event["event_id"],),
            ).fetchone()
        assert json.loads(row["payload_json"]) == {"attempt": 1}
    finally:
        session.DB_PATH = original_db_path


def test_attach_execution_artifact_creates_artifact(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-artifact.db")
    try:
        execution = execution_ledger.create_execution(user_id="user_1")

        artifact = execution_ledger.attach_execution_artifact(
            execution_id=execution["execution_id"],
            artifact_type="output_ref",
            name="Task output",
            uri="output://out_1",
            metadata={"source_type": "output", "source_id": "out_1"},
        )

        assert artifact["artifact_id"].startswith("art_")
        assert artifact["execution_id"] == execution["execution_id"]
        assert artifact["artifact_type"] == "output_ref"
        assert artifact["name"] == "Task output"
        assert artifact["uri"] == "output://out_1"
        assert artifact["metadata"] == {"source_type": "output", "source_id": "out_1"}
    finally:
        session.DB_PATH = original_db_path


def test_attach_execution_artifact_uses_caller_owned_db_without_committing(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-artifact-db.db")
    try:
        execution = execution_ledger.create_execution(user_id="user_1")

        with session.get_connection() as conn:
            artifact = execution_ledger.attach_execution_artifact(
                execution_id=execution["execution_id"],
                artifact_type="output",
                name="Task output",
                uri="output://out_db",
                metadata={"task_id": "tsk_db", "output_id": "out_db", "output_type": "text", "status": "completed"},
                source_type="output",
                source_id="out_db",
                db=conn,
            )
            assert artifact["artifact_id"].startswith("art_")
            assert artifact["metadata"] == {
                "output_id": "out_db",
                "output_type": "text",
                "source_id": "out_db",
                "source_type": "output",
                "status": "completed",
                "task_id": "tsk_db",
            }
            visible_inside_transaction = conn.execute(
                "SELECT COUNT(*) AS count FROM execution_artifacts WHERE artifact_id=?",
                (artifact["artifact_id"],),
            ).fetchone()["count"]
            assert visible_inside_transaction == 1
            conn.rollback()

        assert execution_ledger.list_execution_artifacts(execution["execution_id"]) == []
    finally:
        session.DB_PATH = original_db_path


def test_record_execution_cost_creates_cost(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-cost.db")
    try:
        execution = execution_ledger.create_execution(user_id="user_1")

        cost = execution_ledger.record_execution_cost(
            execution_id=execution["execution_id"],
            provider="openai",
            model="example-model",
            input_tokens=10,
            output_tokens=5,
            cost_amount=0.02,
            cost_currency="USD",
            metadata={"cost_type": "model"},
        )

        assert cost["cost_id"].startswith("cost_")
        assert cost["execution_id"] == execution["execution_id"]
        assert cost["provider"] == "openai"
        assert cost["model"] == "example-model"
        assert cost["input_tokens"] == 10
        assert cost["output_tokens"] == 5
        assert cost["cost_amount"] == 0.02
        assert cost["cost_currency"] == "USD"
        assert cost["metadata"] == {"cost_type": "model"}
    finally:
        session.DB_PATH = original_db_path


def test_request_execution_approval_creates_approval(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-approval.db")
    try:
        execution = execution_ledger.create_execution(user_id="user_1")

        approval = execution_ledger.request_execution_approval(
            execution_id=execution["execution_id"],
            approval_type="human_review",
            requested_by="user_1",
            reason="Needs review",
            metadata={"risk": "medium"},
        )

        assert approval["approval_id"].startswith("appr_")
        assert approval["execution_id"] == execution["execution_id"]
        assert approval["approval_type"] == "human_review"
        assert approval["status"] == "pending"
        assert approval["requested_by"] == "user_1"
        assert approval["reason"] == "Needs review"
        assert approval["metadata"] == {"risk": "medium"}
    finally:
        session.DB_PATH = original_db_path


def test_list_helpers_scope_rows_to_execution_or_user(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-list.db")
    try:
        user_execution = execution_ledger.create_execution(user_id="user_1", source_type="task", source_id="task_1")
        other_execution = execution_ledger.create_execution(user_id="user_2", source_type="task", source_id="task_2")
        step = execution_ledger.create_execution_step(
            execution_id=user_execution["execution_id"],
            step_order=1,
            step_type="tool_call",
            name="Run tool",
        )
        execution_ledger.append_execution_event(
            execution_id=user_execution["execution_id"],
            event_type="step_started",
            step_id=step["step_id"],
        )
        execution_ledger.append_execution_event(
            execution_id=other_execution["execution_id"],
            event_type="other_event",
        )
        execution_ledger.attach_execution_artifact(
            execution_id=user_execution["execution_id"],
            artifact_type="output_ref",
            name="Output",
        )
        execution_ledger.record_execution_cost(
            execution_id=user_execution["execution_id"],
            cost_amount=0.01,
        )
        execution_ledger.request_execution_approval(
            execution_id=user_execution["execution_id"],
            approval_type="human_review",
        )

        user_executions = execution_ledger.list_executions_for_user("user_1")
        assert [item["execution_id"] for item in user_executions] == [user_execution["execution_id"]]
        assert execution_ledger.get_execution(user_execution["execution_id"])["user_id"] == "user_1"
        assert execution_ledger.get_execution_by_source(user_execution["source_type"], user_execution["source_id"])["execution_id"] == user_execution["execution_id"]
        with session.get_connection() as conn:
            assert execution_ledger.get_execution_by_source("task", "task_1", db=conn)["execution_id"] == user_execution["execution_id"]
        assert execution_ledger.get_execution_by_source("task", "missing") is None
        assert execution_ledger.get_execution("missing") is None
        assert [item["step_id"] for item in execution_ledger.list_execution_steps(user_execution["execution_id"])] == [step["step_id"]]
        assert [item["event_type"] for item in execution_ledger.list_execution_events(user_execution["execution_id"])] == ["step_started"]
        assert len(execution_ledger.list_execution_artifacts(user_execution["execution_id"])) == 1
        assert len(execution_ledger.list_execution_costs(user_execution["execution_id"])) == 1
        assert len(execution_ledger.list_execution_approvals(user_execution["execution_id"])) == 1
    finally:
        session.DB_PATH = original_db_path


def test_mark_execution_and_step_status_helpers_update_rows(tmp_path):
    original_db_path = _use_temp_db(tmp_path / "execution-ledger-status.db")
    try:
        execution = execution_ledger.create_execution(user_id="user_1")
        step = execution_ledger.create_execution_step(
            execution_id=execution["execution_id"],
            step_order=1,
            step_type="tool_call",
            name="Run tool",
        )

        running = execution_ledger.mark_execution_running(execution["execution_id"])
        assert running["status"] == "running"
        assert running["finished_at"] is None

        completed_step = execution_ledger.mark_execution_step_completed(step["step_id"])
        assert completed_step["status"] == "completed"
        assert completed_step["finished_at"] is not None

        completed = execution_ledger.mark_execution_completed(execution["execution_id"])
        assert completed["status"] == "completed"
        assert completed["finished_at"] is not None
    finally:
        session.DB_PATH = original_db_path


def test_is_execution_ledger_enabled_defaults_false_and_accepts_truthy(monkeypatch):
    monkeypatch.delenv("EXECUTION_LEDGER_ENABLED", raising=False)
    assert execution_ledger.is_execution_ledger_enabled() is False

    for value in ["1", "true", "TRUE", "yes", "on"]:
        monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", value)
        assert execution_ledger.is_execution_ledger_enabled() is True

    monkeypatch.setenv("EXECUTION_LEDGER_ENABLED", "0")
    assert execution_ledger.is_execution_ledger_enabled() is False
