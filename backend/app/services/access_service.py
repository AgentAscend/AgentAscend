from backend.app.db.session import get_connection

FEATURE_RANDOM_NUMBER = "random_number"


def grant_access(user_id: str, feature_name: str):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO access_grants (user_id, feature_name, status)
            VALUES (?, ?, ?)
            """,
            (user_id, feature_name, "active"),
        )
        conn.commit()


def has_access(user_id: str, feature_name: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id
            FROM access_grants
            WHERE user_id = ? AND feature_name = ? AND status = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id, feature_name, "active"),
        ).fetchone()

    return row is not None
