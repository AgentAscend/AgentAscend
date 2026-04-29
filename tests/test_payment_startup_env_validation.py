import importlib
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_payment_startup_env_validation_skips_non_production(monkeypatch):
    monkeypatch.delenv("AGENTASCEND_ENV", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)

    from backend.app.services import payment_config

    importlib.reload(payment_config)
    payment_config.validate_payment_startup_env()


def test_payment_startup_env_validation_fails_closed_in_production(monkeypatch):
    monkeypatch.setenv("AGENTASCEND_ENV", "production")
    for key in [
        "SOLANA_RECEIVER_WALLET",
        "AGENT_TOKEN_MINT_ADDRESS",
        "CURRENCY_MINT",
        "PRICE_AMOUNT_SMALLEST_UNIT",
        "SOL_PRICE_LAMPORTS",
    ]:
        monkeypatch.delenv(key, raising=False)

    from backend.app.services import payment_config

    importlib.reload(payment_config)
    with pytest.raises(HTTPException) as exc_info:
        payment_config.validate_payment_startup_env()
    assert exc_info.value.status_code == 500
    assert "is not set" in str(exc_info.value.detail)


def test_lifespan_startup_runs_validation_before_db_init(monkeypatch):
    call_order = []

    import backend.app.services.payment_config as payment_config
    import backend.app.db.session as session

    monkeypatch.setattr(payment_config, "validate_payment_startup_env", lambda: call_order.append("validate"))
    monkeypatch.setattr(session, "init_db", lambda: call_order.append("init_db"))

    import backend.app.main as main

    importlib.reload(main)

    from fastapi.testclient import TestClient

    with TestClient(main.app):
        pass

    assert call_order == ["validate", "init_db"]
