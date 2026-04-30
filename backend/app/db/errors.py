"""Database exception helpers for safe route-level error normalization."""

import sqlite3


def _is_psycopg_unique_violation(exc: BaseException) -> bool:
    try:
        import psycopg2
        import psycopg2.errors
    except ImportError:
        return False

    return isinstance(exc, (psycopg2.IntegrityError, psycopg2.errors.UniqueViolation)) and getattr(exc, "pgcode", None) == "23505"


def is_unique_violation(exc: BaseException) -> bool:
    """Return True for SQLite/Postgres unique constraint violations."""
    if isinstance(exc, sqlite3.IntegrityError):
        return True
    if getattr(exc, "pgcode", None) == "23505":
        return True
    if _is_psycopg_unique_violation(exc):
        return True
    return exc.__class__.__name__ == "UniqueViolation"
