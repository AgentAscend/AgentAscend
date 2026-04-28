import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_api_responses_include_security_headers(tmp_path, monkeypatch):
    import backend.app.db.session as session

    monkeypatch.setattr(session, "DB_PATH", tmp_path / "agentascend-security-headers-test.db")

    import backend.app.main as main

    importlib.reload(main)
    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-frame-options"] == "DENY"
    assert "geolocation=()" in response.headers["permissions-policy"]
    assert "default-src 'none'" in response.headers["content-security-policy"]
