import importlib
import sqlite3
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_sqlite_db_path_can_be_configured_for_local_dev(tmp_path, monkeypatch):
    persistent_path = tmp_path / "local-dev" / "agentascend.db"
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_PATH", str(persistent_path))

    import backend.app.db.session as session

    session = importlib.reload(session)

    assert session.DB_PATH == persistent_path
    assert session._using_postgres() is False
    session.init_db()
    assert persistent_path.exists()


def test_database_url_selects_postgres_connection_over_sqlite_path(tmp_path, monkeypatch):
    persistent_path = tmp_path / "ignored-sqlite" / "agentascend.db"
    monkeypatch.setenv("DATABASE_PATH", str(persistent_path))
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.invalid:5432/agentascend")

    import backend.app.db.session as session

    session = importlib.reload(session)
    sentinel = object()
    monkeypatch.setattr(session, "_connect_postgres", lambda: sentinel)

    assert session._using_postgres() is True
    assert session.get_connection() is sentinel
    assert not persistent_path.exists()


def test_signup_me_and_signin_work_when_database_url_branch_is_selected(tmp_path, monkeypatch):
    db_path = tmp_path / "database-url-branch.db"
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.invalid:5432/agentascend")

    import backend.app.db.session as session
    session = importlib.reload(session)

    def sqlite_backed_database_url_connection():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(session, "_using_postgres", lambda: True)
    monkeypatch.setattr(session, "_connect_postgres", sqlite_backed_database_url_connection)
    monkeypatch.setattr(session, "_init_postgres_db", session._init_sqlite_db)

    import backend.app.main as main
    main = importlib.reload(main)

    email = "database-url-branch@example.com"
    password = "TestPass123!"

    with TestClient(main.app) as client:
        signup = client.post(
            "/auth/signup",
            json={"email": email, "password": password, "display_name": "Database URL Branch"},
        )
        assert signup.status_code == 200, signup.text
        token = signup.json()["session_token"]
        user_id = signup.json()["user"]["user_id"]

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200, me.text
        assert me.json()["user"]["user_id"] == user_id

        signin = client.post("/auth/signin", json={"email": email, "password": password})
        assert signin.status_code == 200, signin.text
        assert signin.json()["user"]["user_id"] == user_id

def test_signup_user_can_signin_after_app_reload_with_same_db(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    persistent_path = tmp_path / "persistent" / "agentascend.db"
    monkeypatch.setenv("DATABASE_PATH", str(persistent_path))

    import backend.app.db.session as session
    session = importlib.reload(session)

    import backend.app.main as main
    main = importlib.reload(main)

    email = "auth-persistence@example.com"
    password = "TestPass123!"

    with TestClient(main.app) as client:
        signup = client.post(
            "/auth/signup",
            json={"email": email, "password": password, "display_name": "Auth Persistence"},
        )
        assert signup.status_code == 200, signup.text
        user_id = signup.json()["user"]["user_id"]

    # Simulate a fresh app process using the same configured DB path.
    session = importlib.reload(session)
    main = importlib.reload(main)

    with TestClient(main.app) as client:
        signin = client.post("/auth/signin", json={"email": email, "password": password})
        assert signin.status_code == 200, signin.text
        body = signin.json()
        assert body["status"] == "ok"
        assert body["session_token"]
        assert body["user"]["user_id"] == user_id
        assert body["user"]["email"] == email

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['session_token']}"})
        assert me.status_code == 200, me.text
        assert me.json()["user"]["user_id"] == user_id
