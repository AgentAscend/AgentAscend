from backend.app.db.session import get_connection

FEATURE_RANDOM_NUMBER = "random_number"


def grant_access(
    user_id: str,
    feature_name: str,
    *,
    conn=None,
    payment_id: int | None = None,
    intent_reference: str | None = None,
    source: str | None = None,
):
    def _insert(connection):
        connection.execute(
            """
            INSERT INTO access_grants (user_id, feature_name, status, payment_id, intent_reference, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, feature_name, "active", payment_id, intent_reference, source),
        )

    if conn is not None:
        _insert(conn)
        return

    with get_connection() as local_conn:
        _insert(local_conn)
        local_conn.commit()


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
