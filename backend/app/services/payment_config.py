import os
from decimal import Decimal

from fastapi import HTTPException

DEFAULT_SOL_PRICE_LAMPORTS = 100_000_000  # 0.1 SOL


def _required_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        raise HTTPException(status_code=500, detail=f"{name} is not set")
    return value


def _is_production_env() -> bool:
    candidates = [
        os.getenv("AGENTASCEND_ENV"),
        os.getenv("APP_ENV"),
        os.getenv("ENVIRONMENT"),
        os.getenv("RAILWAY_ENVIRONMENT"),
    ]
    normalized = {str(v or "").strip().lower() for v in candidates}
    return any(v in {"prod", "production"} for v in normalized)


def validate_payment_startup_env() -> None:
    if not _is_production_env():
        return

    required_names = [
        "SOLANA_RECEIVER_WALLET",
        "AGENT_TOKEN_MINT_ADDRESS",
        "CURRENCY_MINT",
        "PRICE_AMOUNT_SMALLEST_UNIT",
        "SOL_PRICE_LAMPORTS",
    ]
    for name in required_names:
        _required_env(name)

    required_positive_int_env("PRICE_AMOUNT_SMALLEST_UNIT")
    required_positive_int_env("SOL_PRICE_LAMPORTS")


def sol_price_lamports() -> int:
    raw = os.getenv("SOL_PRICE_LAMPORTS")
    if raw is None or raw.strip() == "":
        return DEFAULT_SOL_PRICE_LAMPORTS

    try:
        value = int(raw)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="SOL_PRICE_LAMPORTS must be an integer") from exc

    if value <= 0:
        raise HTTPException(status_code=500, detail="SOL_PRICE_LAMPORTS must be greater than zero")

    return value


def format_sol_amount(lamports: int) -> str:
    amount = Decimal(lamports) / Decimal(1_000_000_000)
    normalized = amount.normalize()
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def payment_required_tool_message() -> str:
    lamports = sol_price_lamports()
    return f"Please pay {format_sol_amount(lamports)} SOL to access this tool"


def required_pumpfun_mint(name: str) -> str:
    return _required_env(name)


def required_positive_int_env(name: str) -> int:
    raw = _required_env(name)
    try:
        value = int(raw)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"{name} must be an integer") from exc
    if value <= 0:
        raise HTTPException(status_code=500, detail=f"{name} must be greater than zero")
    return value
