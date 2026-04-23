def telegram_user_to_user_id(telegram_user_id: int | str) -> str:
    raw = str(telegram_user_id).strip()
    if not raw or not raw.isdigit():
        raise ValueError("telegram_user_id must be numeric")
    return f"tg:{raw}"
