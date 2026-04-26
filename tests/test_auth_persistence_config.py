import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_db_path_can_be_configured_for_persistent_railway_volume(tmp_path, monkeypatch):
    persistent_path = tmp_path / "railway-volume" / "agentascend.db"
    monkeypatch.setenv("AGENTASCEND_DB_PATH", str(persistent_path))

    import backend.app.db.session as session

    session = importlib.reload(session)

    assert session.DB_PATH == persistent_path
    session.init_db()
    assert persistent_path.exists()


def test_signup_user_can_signin_after_app_reload_with_same_db(tmp_path, monkeypatch):
    persistent_path = tmp_path / "persistent" / "agentascend.db"
    monkeypatch.setenv("AGENTASCEND_DB_PATH", str(persistent_path))

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
