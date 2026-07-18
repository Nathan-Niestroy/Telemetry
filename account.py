"""Store financial accounts in Telemetry's SQLite database."""

import sqlite3
from contextlib import closing
from pathlib import Path


class AccountStore:
    """Provide SQLite operations for financial accounts."""

    def __init__(self, database_path: Path) -> None:
        """Remember the shared database path and ensure the account table exists."""
        self.database_path = database_path
        self._create_table()

    def _connect(self) -> sqlite3.Connection:
        """Open a named-row connection with foreign-key enforcement enabled."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_table(self) -> None:
        """Create the account table without changing an existing installation."""
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )

    def create_account(
        self,
        user_id: int,
        name: str,
        owner: str,
        account_type: str,
        balance_cents: int,
    ) -> None:
        """Save one account for the authenticated user."""
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO accounts (user_id, name, owner, account_type, balance_cents)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, owner, account_type, balance_cents),
            )

    def list_accounts(self, user_id: int) -> list[dict]:
        """Return only the accounts belonging to the authenticated user."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, name, owner, account_type, balance_cents
                FROM accounts
                WHERE user_id = ?
                ORDER BY name COLLATE NOCASE
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]
