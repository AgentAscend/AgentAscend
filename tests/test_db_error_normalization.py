import sqlite3

from backend.app.db.errors import is_unique_violation


class FakePostgresUniqueViolation(Exception):
    pgcode = "23505"


class FakeNamedUniqueViolation(Exception):
    pass


FakeNamedUniqueViolation.__name__ = "UniqueViolation"


def test_is_unique_violation_detects_sqlite_integrity_error():
    assert is_unique_violation(sqlite3.IntegrityError("UNIQUE constraint failed: payments.tx_signature"))


def test_is_unique_violation_detects_postgres_sqlstate_23505():
    assert is_unique_violation(FakePostgresUniqueViolation("duplicate key value violates unique constraint"))


def test_is_unique_violation_detects_named_unique_violation_fallback():
    assert is_unique_violation(FakeNamedUniqueViolation("duplicate key value violates unique constraint"))


def test_is_unique_violation_rejects_non_unique_errors():
    assert not is_unique_violation(RuntimeError("connection failed"))
