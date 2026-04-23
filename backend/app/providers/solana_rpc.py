import json
import os
import urllib.error
import urllib.request

from fastapi import HTTPException


def rpc_post(method: str, params: list):
    rpc_url = os.getenv("SOLANA_RPC_URL")
    if not rpc_url:
        raise HTTPException(status_code=500, detail="SOLANA_RPC_URL is not set")

    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Solana RPC request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Invalid JSON returned by Solana RPC") from exc

    if data.get("error"):
        raise HTTPException(status_code=400, detail=f"Solana RPC error: {data['error']}")

    return data.get("result")


def fetch_transaction(tx_signature: str):
    return rpc_post(
        "getTransaction",
        [
            tx_signature,
            {
                "commitment": "confirmed",
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
            },
        ],
    )


def extract_account_keys(tx_result: dict) -> list[str]:
    message = tx_result.get("transaction", {}).get("message", {})
    account_keys = message.get("accountKeys", [])

    normalized_keys: list[str] = []
    for key in account_keys:
        if isinstance(key, str):
            normalized_keys.append(key)
        elif isinstance(key, dict) and "pubkey" in key:
            normalized_keys.append(key["pubkey"])

    loaded_addresses = (tx_result.get("meta") or {}).get("loadedAddresses") or {}
    normalized_keys.extend(loaded_addresses.get("writable", []) or [])
    normalized_keys.extend(loaded_addresses.get("readonly", []) or [])

    return normalized_keys


def received_lamports_for_wallet(tx_result: dict, wallet_address: str) -> int:
    meta = tx_result.get("meta") or {}
    pre_balances = meta.get("preBalances") or []
    post_balances = meta.get("postBalances") or []
    account_keys = extract_account_keys(tx_result)

    if wallet_address not in account_keys:
        raise HTTPException(status_code=400, detail="Receiver wallet not found in transaction")

    wallet_index = account_keys.index(wallet_address)

    if wallet_index >= len(pre_balances) or wallet_index >= len(post_balances):
        raise HTTPException(status_code=400, detail="Transaction balance arrays are malformed")

    return int(post_balances[wallet_index]) - int(pre_balances[wallet_index])
