import logging
import os
import re
import sqlite3
import uuid
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException

from backend.app.db.session import get_connection
from backend.app.providers.solana_rpc import fetch_transaction, received_lamports_for_wallet
from backend.app.providers.spl_token_rpc import (
    get_receiver_token_account,
    received_token_amount_for_wallet,
)
from backend.app.schemas.payments import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentVerifyRequest,
    PaymentVerifyResponse,
)
from backend.app.services.access_service import FEATURE_RANDOM_NUMBER, grant_access
from backend.app.services.idempotency import check_or_begin, finalize
from backend.app.services.rate_limit import enforce_rate_limit

router = APIRouter()
logger = logging.getLogger(__name__)

DEFAULT_SOL_PRICE_LAMPORTS = 100_000_000  # 0.1 SOL
DEFAULT_ASND_PRICE_TOKENS = Decimal("100")
SUPPORTED_TOKENS = {"SOL", "ASND"}
_SIGNATURE_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{80,100}$")



def _normalize_token(token: str) -> str:
    normalized = (token or "").strip().upper()
    if normalized not in SUPPORTED_TOKENS:
        raise HTTPException(status_code=400, detail="Unsupported token. Use SOL or ASND")
    return normalized


def _validate_signature_format(tx_signature: str) -> None:
    if not _SIGNATURE_PATTERN.match((tx_signature or "").strip()):
        raise HTTPException(status_code=400, detail="Invalid transaction signature format")


def _sol_price_lamports() -> int:
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


def _asnd_price_tokens() -> Decimal:
    raw = os.getenv("ASND_PRICE_TOKENS")
    if raw is None or raw.strip() == "":
        return DEFAULT_ASND_PRICE_TOKENS

    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=500, detail="ASND_PRICE_TOKENS must be a valid decimal number") from exc

    if value <= 0:
        raise HTTPException(status_code=500, detail="ASND_PRICE_TOKENS must be greater than zero")

    return value


def _payment_ttl_seconds() -> int:
    raw = os.getenv("PAYMENT_TTL_SECONDS")
    if raw is None or raw.strip() == "":
        return 900

    try:
        value = int(raw)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="PAYMENT_TTL_SECONDS must be an integer") from exc

    if value <= 0:
        raise HTTPException(status_code=500, detail="PAYMENT_TTL_SECONDS must be greater than zero")

    return value


def _payment_reference(user_id: str, token: str) -> str:
    return f"{user_id}:{token}:{os.urandom(8).hex()}"


@router.post("/payments/create", response_model=PaymentCreateResponse)
def create_payment(payload: PaymentCreateRequest):
    enforce_rate_limit("payments.create", payload.user_id, limit=60, window_seconds=300)
    selected_token = _normalize_token(payload.token)

    receiver_wallet = os.getenv("SOLANA_RECEIVER_WALLET")
    if not receiver_wallet:
        raise HTTPException(status_code=500, detail="SOLANA_RECEIVER_WALLET is not set")

    ttl_seconds = _payment_ttl_seconds()
    reference = _payment_reference(payload.user_id, selected_token)

    if selected_token == "SOL":
        sol_price_lamports = _sol_price_lamports()
        return {
            "status": "payment_required",
            "payment_required": True,
            "user_id": payload.user_id,
            "amount": sol_price_lamports / 1_000_000_000,
            "amount_lamports": sol_price_lamports,
            "token": "SOL",
            "receiver": receiver_wallet,
            "receiver_wallet": receiver_wallet,
            "receiver_token_account": None,
            "reference": reference,
            "ttl_seconds": ttl_seconds,
        }

    asnd_price_tokens = _asnd_price_tokens()
    receiver_token_account = os.getenv("ASND_RECEIVER_TOKEN_ACCOUNT")
    return {
        "status": "payment_required",
        "payment_required": True,
        "user_id": payload.user_id,
        "amount": str(asnd_price_tokens),
        "token": "ASND",
        "receiver": receiver_token_account or receiver_wallet,
        "receiver_wallet": receiver_wallet,
        "receiver_token_account": receiver_token_account,
        "reference": reference,
        "ttl_seconds": ttl_seconds,
    }


@router.post("/payments/verify", response_model=PaymentVerifyResponse)
def verify_payment(payload: PaymentVerifyRequest):
    enforce_rate_limit("payments.verify", payload.user_id, limit=60, window_seconds=300)
    selected_token = _normalize_token(payload.token)
    _validate_signature_format(payload.tx_signature)

    idempotency_key = payload.idempotency_key or f"pay_{uuid.uuid4().hex}"
    scope = f"payment_verify:{payload.user_id}"
    replay = check_or_begin(
        scope,
        idempotency_key,
        {
            "user_id": payload.user_id,
            "tx_signature": payload.tx_signature,
            "token": selected_token,
        },
    )
    if replay:
        return replay["payload"]

    tx_result = fetch_transaction(payload.tx_signature)
    if not tx_result:
        raise HTTPException(status_code=400, detail="Transaction not found or not confirmed")

    meta = tx_result.get("meta")
    if not meta:
        raise HTTPException(status_code=400, detail="Transaction metadata missing")

    if meta.get("err") is not None:
        raise HTTPException(status_code=400, detail="Transaction failed on-chain")

    payment_details = {}

    if selected_token == "SOL":
        receiver_wallet = os.getenv("SOLANA_RECEIVER_WALLET")
        if not receiver_wallet:
            raise HTTPException(status_code=500, detail="SOLANA_RECEIVER_WALLET is not set")

        sol_price_lamports = _sol_price_lamports()
        received_lamports = received_lamports_for_wallet(tx_result, receiver_wallet)
        if received_lamports < sol_price_lamports:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient payment: expected at least {sol_price_lamports} lamports, "
                    f"received {received_lamports}"
                ),
            )

        amount = sol_price_lamports / 1_000_000_000
        payment_details["received_lamports"] = received_lamports
    else:
        receiver_wallet = os.getenv("SOLANA_RECEIVER_WALLET")
        if not receiver_wallet:
            raise HTTPException(status_code=500, detail="SOLANA_RECEIVER_WALLET is not set")

        mint_address = os.getenv("ASND_MINT_ADDRESS")
        if not mint_address:
            raise HTTPException(status_code=500, detail="ASND_MINT_ADDRESS is not set")

        asnd_price_tokens = _asnd_price_tokens()
        receiver_token_account = get_receiver_token_account(receiver_wallet, mint_address)
        received_amount = received_token_amount_for_wallet(
            tx_result,
            receiver_token_account,
            mint_address,
        )

        if received_amount < asnd_price_tokens:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient ASND payment: expected at least {asnd_price_tokens}, "
                    f"received {received_amount}"
                ),
            )

        amount = float(received_amount)
        payment_details["received_amount"] = str(received_amount)
        payment_details["receiver_token_account"] = receiver_token_account

    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (payload.user_id,),
        )

        try:
            cursor = conn.execute(
                """
                INSERT INTO payments (user_id, amount, token, status, tx_signature)
                VALUES (?, ?, ?, ?, ?)
                """,
                (payload.user_id, amount, selected_token, "completed", payload.tx_signature),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail="Transaction signature already used") from exc

        payment_id = cursor.lastrowid
        conn.commit()

    grant_access(payload.user_id, FEATURE_RANDOM_NUMBER)

    response_payload = {
        "status": "payment_verified",
        "user_id": payload.user_id,
        "payment_id": payment_id,
        "tx_signature": payload.tx_signature,
        "token": selected_token,
        **payment_details,
    }
    finalize(scope, idempotency_key, response_payload)
    logger.info("payment_verified_success user_id=%s token=%s", payload.user_id, selected_token)
    return response_payload
