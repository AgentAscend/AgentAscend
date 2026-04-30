import json
import os
import re
import time
import uuid
from typing import Literal

from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.errors import is_unique_violation
from backend.app.db.session import get_connection
from backend.app.services import pumpfun_node_helper
from backend.app.services.access_service import FEATURE_RANDOM_NUMBER
from backend.app.services.auth_service import require_user_access
from backend.app.services.error_response import fail
from backend.app.services.payment_config import required_positive_int_env
from backend.app.services.payment_error_codes import (
    PAYMENT_CONFIG_ERROR,
    PAYMENT_HELPER_ERROR,
    PAYMENT_INTENT_CONSUMED,
    PAYMENT_INTENT_EXPIRED,
    PAYMENT_INTENT_INVALID,
    PAYMENT_NOT_VERIFIED,
    PAYMENT_RECORD_ERROR,
    TRANSACTION_SIGNATURE_USED,
    VALIDATION_ERROR,
)
from backend.app.services.rate_limit import enforce_rate_limit

router = APIRouter()

DEFAULT_CURRENCY_MINT = "So11111111111111111111111111111111111111112"
DEFAULT_PAYMENT_TTL_SECONDS = 900
_SIGNATURE_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{80,100}$")


class PumpfunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    user_wallet: str = Field(min_length=1)
    access_tier: str = Field(default="mvp", min_length=1)


class PumpfunCreateResponse(BaseModel):
    status: Literal["payment_transaction_built"]
    payment_required: Literal[True] = True
    user_id: str
    reference: str
    txBase64: str
    invoiceId: str | None = None
    agentTokenMint: str
    currencyMint: str
    currencySymbol: Literal["SOL"] = "SOL"
    amount: int
    memo: int
    startTime: int
    endTime: int
    ttl_seconds: int


class PumpfunVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    tx_signature: str = Field(min_length=1)


class PumpfunVerifyResponse(BaseModel):
    status: Literal["payment_verified"]
    user_id: str
    reference: str
    payment_id: int
    tx_signature: str
    token: Literal["SOL"] = "SOL"
    invoiceId: str | None = None


def _optional_positive_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        fail(500, PAYMENT_CONFIG_ERROR, f"{name} must be an integer")
    if value <= 0:
        fail(500, PAYMENT_CONFIG_ERROR, f"{name} must be greater than zero")
    return value


def _config_value(name: str, default: str) -> str:
    value = (os.getenv(name) or default).strip()
    if not value:
        fail(500, "payment_config_error", f"{name} is not configured")
    return value


def _payment_ttl_seconds() -> int:
    return _optional_positive_int_env("PAYMENT_TTL_SECONDS", DEFAULT_PAYMENT_TTL_SECONDS)


def _amount_smallest_unit() -> int:
    try:
        return required_positive_int_env("PRICE_AMOUNT_SMALLEST_UNIT")
    except Exception as exc:
        fail(500, PAYMENT_CONFIG_ERROR, str(getattr(exc, "detail", "PRICE_AMOUNT_SMALLEST_UNIT is not configured")))


def _agent_token_mint() -> str:
    value = (os.getenv("AGENT_TOKEN_MINT_ADDRESS") or "").strip()
    if not value:
        fail(500, PAYMENT_CONFIG_ERROR, "AGENT_TOKEN_MINT_ADDRESS is not configured")
    return value


def _currency_mint() -> str:
    value = (os.getenv("CURRENCY_MINT") or "").strip()
    if not value:
        fail(500, PAYMENT_CONFIG_ERROR, "CURRENCY_MINT is not configured")
    return value


def _new_reference(user_id: str) -> str:
    safe_user = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", user_id).strip("_")[:48] or "user"
    return f"pumpfun:{safe_user}:{uuid.uuid4().hex}"


def _new_memo() -> int:
    return int.from_bytes(os.urandom(4), "big") or 1


def _validate_signature_format(tx_signature: str) -> None:
    if not _SIGNATURE_PATTERN.match((tx_signature or "").strip()):
        fail(400, VALIDATION_ERROR, "Invalid transaction signature format")


def _require_unused_tx_signature(tx_signature: str) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM payments WHERE tx_signature = ? LIMIT 1",
            (tx_signature,),
        ).fetchone()
    if row is not None:
        fail(400, TRANSACTION_SIGNATURE_USED, "Transaction signature already used")


def _safe_helper_error(status_code: int = 400) -> None:
    fail(status_code, PAYMENT_HELPER_ERROR, "Payment helper failed")


def _build_helper_payload(*, user_wallet: str, agent_token_mint: str, currency_mint: str, amount: int, memo: int, start_time: int, end_time: int) -> dict:
    return {
        "userWallet": user_wallet,
        "agentTokenMint": agent_token_mint,
        "currencyMint": currency_mint,
        "amount": amount,
        "memo": memo,
        "startTime": start_time,
        "endTime": end_time,
    }


def _store_pending_intent(
    *,
    reference: str,
    payload: PumpfunCreateRequest,
    helper_payload: dict,
    invoice_id: str | None,
    ttl_seconds: int,
) -> None:
    expires_at_epoch = int(helper_payload["endTime"])
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO payment_intents(
                reference, user_id, token, expires_at_epoch, user_wallet,
                agent_token_mint, currency_mint, currency_symbol, amount_smallest_unit,
                memo, start_time, end_time, invoice_id, tool_id, access_tier,
                status, verification_status, expires_at, metadata_json, currency, chain
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?, ?, ?)
            """,
            (
                reference,
                payload.user_id,
                "SOL",
                expires_at_epoch,
                helper_payload["userWallet"],
                helper_payload["agentTokenMint"],
                helper_payload["currencyMint"],
                "SOL",
                helper_payload["amount"],
                helper_payload["memo"],
                helper_payload["startTime"],
                helper_payload["endTime"],
                invoice_id,
                FEATURE_RANDOM_NUMBER,
                payload.access_tier,
                "pending",
                "unverified",
                json.dumps({"source": "pumpfun_sdk"}, sort_keys=True),
                "SOL",
                "solana-mainnet",
            ),
        )
        conn.commit()


def _load_pending_intent(reference: str, user_id: str):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM payment_intents
            WHERE reference = ? AND user_id = ? AND token = ?
            """,
            (reference, user_id, "SOL"),
        ).fetchone()
    if row is None:
        fail(400, PAYMENT_INTENT_INVALID, "Invalid payment reference")
    if row["status"] == "completed":
        fail(400, PAYMENT_INTENT_CONSUMED, "Payment reference already completed")
    if row["status"] != "pending":
        fail(400, PAYMENT_INTENT_INVALID, "Payment reference is not pending")
    if int(row["end_time"] or row["expires_at_epoch"] or 0) < int(time.time()):
        fail(400, PAYMENT_INTENT_EXPIRED, "Payment reference expired")
    return row


def _validate_exact_invoice_columns(row) -> None:
    required = [
        "user_wallet",
        "agent_token_mint",
        "currency_mint",
        "amount_smallest_unit",
        "memo",
        "start_time",
        "end_time",
    ]
    for column in required:
        if row[column] is None or row[column] == "":
            fail(400, "payment_intent_invalid", "Payment reference is missing invoice terms")


def _record_verified_payment_and_access(*, row, tx_signature: str, invoice_id: str | None) -> int:
    with get_connection() as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO payments(
                    user_id, amount, token, status, tx_signature, intent_reference,
                    user_wallet, agent_token_mint, currency_mint, currency_symbol,
                    amount_smallest_unit, memo, start_time, end_time, invoice_id,
                    payer_wallet, chain, amount_expected, amount_received,
                    verification_status, updated_at, verified_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                (
                    row["user_id"],
                    int(row["amount_smallest_unit"]) / 1_000_000_000,
                    "SOL",
                    "completed",
                    tx_signature,
                    row["reference"],
                    row["user_wallet"],
                    row["agent_token_mint"],
                    row["currency_mint"],
                    "SOL",
                    int(row["amount_smallest_unit"]),
                    int(row["memo"]),
                    int(row["start_time"]),
                    int(row["end_time"]),
                    invoice_id or row["invoice_id"],
                    row["user_wallet"],
                    "solana-mainnet",
                    int(row["amount_smallest_unit"]) / 1_000_000_000,
                    int(row["amount_smallest_unit"]) / 1_000_000_000,
                    "verified",
                ),
            )
        except Exception as exc:
            if is_unique_violation(exc):
                fail(400, TRANSACTION_SIGNATURE_USED, "Transaction signature already used")
            raise
        payment_id = getattr(cursor, "lastrowid", None)
        if payment_id is None:
            payment_row = conn.execute(
                "SELECT id FROM payments WHERE tx_signature = ? LIMIT 1",
                (tx_signature,),
            ).fetchone()
            if payment_row is None:
                fail(500, PAYMENT_RECORD_ERROR, "Payment record could not be confirmed")
            payment_id = payment_row["id"]
        conn.execute(
            """
            UPDATE payment_intents
            SET status = ?, verification_status = ?, tx_signature = ?, completed_at = datetime('now'), updated_at = datetime('now')
            WHERE reference = ?
            """,
            ("completed", "verified", tx_signature, row["reference"]),
        )
        try:
            conn.execute(
                """
                INSERT INTO access_grants(
                    user_id, feature_name, status, payment_id, intent_reference,
                    grant_scope, source, tool_id, updated_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
                """,
                (
                    row["user_id"],
                    FEATURE_RANDOM_NUMBER,
                    "active",
                    payment_id,
                    row["reference"],
                    FEATURE_RANDOM_NUMBER,
                    "pumpfun_sdk",
                    FEATURE_RANDOM_NUMBER,
                    json.dumps({"invoice_id": invoice_id or row["invoice_id"]}, sort_keys=True),
                ),
            )
        except Exception as exc:
            if is_unique_violation(exc):
                fail(400, TRANSACTION_SIGNATURE_USED, "Transaction signature already used")
            raise
        conn.commit()
    return payment_id


@router.post("/payments/pumpfun/create", response_model=PumpfunCreateResponse)
def create_pumpfun_payment(payload: PumpfunCreateRequest, authorization: str | None = Header(default=None)):
    require_user_access(payload.user_id, authorization)
    enforce_rate_limit("payments.pumpfun.create", payload.user_id, limit=30, window_seconds=300)

    ttl_seconds = _payment_ttl_seconds()
    start_time = int(time.time())
    end_time = start_time + ttl_seconds
    amount = _amount_smallest_unit()
    helper_payload = _build_helper_payload(
        user_wallet=payload.user_wallet,
        agent_token_mint=_agent_token_mint(),
        currency_mint=_currency_mint(),
        amount=amount,
        memo=_new_memo(),
        start_time=start_time,
        end_time=end_time,
    )

    helper_result = pumpfun_node_helper.build_payment_transaction(helper_payload)
    if not helper_result.get("ok") or not helper_result.get("txBase64"):
        _safe_helper_error()

    reference = _new_reference(payload.user_id)
    invoice_id = helper_result.get("invoiceId")
    _store_pending_intent(
        reference=reference,
        payload=payload,
        helper_payload=helper_payload,
        invoice_id=invoice_id,
        ttl_seconds=ttl_seconds,
    )

    return {
        "status": "payment_transaction_built",
        "payment_required": True,
        "user_id": payload.user_id,
        "reference": reference,
        "txBase64": helper_result["txBase64"],
        "invoiceId": invoice_id,
        "agentTokenMint": helper_payload["agentTokenMint"],
        "currencyMint": helper_payload["currencyMint"],
        "currencySymbol": "SOL",
        "amount": amount,
        "memo": helper_payload["memo"],
        "startTime": start_time,
        "endTime": end_time,
        "ttl_seconds": ttl_seconds,
    }


@router.post("/payments/pumpfun/verify", response_model=PumpfunVerifyResponse)
def verify_pumpfun_payment(payload: PumpfunVerifyRequest, authorization: str | None = Header(default=None)):
    require_user_access(payload.user_id, authorization)
    enforce_rate_limit("payments.pumpfun.verify", payload.user_id, limit=30, window_seconds=300)
    _validate_signature_format(payload.tx_signature)
    _require_unused_tx_signature(payload.tx_signature)

    row = _load_pending_intent(payload.reference, payload.user_id)
    _validate_exact_invoice_columns(row)
    helper_payload = _build_helper_payload(
        user_wallet=row["user_wallet"],
        agent_token_mint=row["agent_token_mint"],
        currency_mint=row["currency_mint"],
        amount=int(row["amount_smallest_unit"]),
        memo=int(row["memo"]),
        start_time=int(row["start_time"]),
        end_time=int(row["end_time"]),
    )

    # Current Pump.fun helper semantics validate the immutable invoice terms.
    # The submitted tx_signature is still recorded for local replay/accounting;
    # add an exact signature-to-invoice cross-check later if the SDK exposes it.
    helper_result = pumpfun_node_helper.validate_invoice_payment(helper_payload)
    if not helper_result.get("ok"):
        _safe_helper_error()
    if not helper_result.get("verified"):
        fail(400, PAYMENT_NOT_VERIFIED, "Payment was not verified")

    invoice_id = helper_result.get("invoiceId") or row["invoice_id"]
    payment_id = _record_verified_payment_and_access(
        row=row,
        tx_signature=payload.tx_signature,
        invoice_id=invoice_id,
    )

    return {
        "status": "payment_verified",
        "user_id": payload.user_id,
        "reference": payload.reference,
        "payment_id": payment_id,
        "tx_signature": payload.tx_signature,
        "token": "SOL",
        "invoiceId": invoice_id,
    }
