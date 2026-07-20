"""Version and validate Telemetry's SQLite schema."""

import sqlite3
from contextlib import closing
from pathlib import Path


SCHEMA_VERSION = 3
REQUIRED_TABLES = {
    "users",
    "accounts",
    "holdings",
    "income_sources",
    "income_allocations",
    "monthly_budget_items",
}


def finalize_schema(database_path: Path) -> None:
    """Record the current schema version after every store has initialized."""
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def validate_database(database_path: Path) -> None:
    """Raise ValueError unless *database_path* is a healthy Telemetry database."""
    try:
        with closing(
            sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)
        ) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
    except sqlite3.Error as error:
        raise ValueError("The backup does not contain a readable SQLite database.") from error
    if integrity != "ok":
        raise ValueError(f"The backup database failed its integrity check: {integrity}")
    missing = REQUIRED_TABLES - tables
    if missing:
        raise ValueError(
            "The backup is not a complete Telemetry database (missing: "
            + ", ".join(sorted(missing))
            + ")."
        )
