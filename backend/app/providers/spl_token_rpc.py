from decimal import Decimal

from fastapi import HTTPException

from backend.app.providers.solana_rpc import extract_account_keys, rpc_post


def get_token_accounts_by_owner(owner_wallet: str, mint_address: str) -> list[dict]:
    result = rpc_post(
        "getTokenAccountsByOwner",
        [owner_wallet, {"mint": mint_address}, {"encoding": "jsonParsed"}],
    )

    if not result:
        return []

    return result.get("value", [])


def get_receiver_token_account(owner_wallet: str, mint_address: str) -> str:
    accounts = get_token_accounts_by_owner(owner_wallet, mint_address)

    if not accounts:
        raise HTTPException(status_code=400, detail="No token account found for receiver wallet and mint")

    if len(accounts) > 1:
        raise HTTPException(status_code=400, detail="Multiple token accounts found for receiver wallet and mint")

    pubkey = accounts[0].get("pubkey")
    if not pubkey:
        raise HTTPException(status_code=400, detail="Token account response missing pubkey")

    return pubkey


def token_balance_by_account_index(token_balances: list[dict], account_index: int, mint_address: str) -> Decimal:
    for entry in token_balances:
        if entry.get("accountIndex") == account_index and entry.get("mint") == mint_address:
            ui_amount_string = (
                entry.get("uiTokenAmount", {}).get("uiAmountString")
                or entry.get("uiTokenAmount", {}).get("amount")
                or "0"
            )
            return Decimal(str(ui_amount_string))
    return Decimal("0")


def received_token_amount_for_wallet(tx_result: dict, receiver_token_account: str, mint_address: str) -> Decimal:
    account_keys = extract_account_keys(tx_result)

    if receiver_token_account not in account_keys:
        raise HTTPException(status_code=400, detail="Receiver token account not found in transaction")

    account_index = account_keys.index(receiver_token_account)

    meta = tx_result.get("meta") or {}
    pre_token_balances = meta.get("preTokenBalances") or []
    post_token_balances = meta.get("postTokenBalances") or []

    pre_amount = token_balance_by_account_index(pre_token_balances, account_index, mint_address)
    post_amount = token_balance_by_account_index(post_token_balances, account_index, mint_address)

    return post_amount - pre_amount
