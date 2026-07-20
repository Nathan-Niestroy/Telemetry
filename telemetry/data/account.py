"""Store financial accounts in Telemetry's SQLite database."""

import sqlite3
from contextlib import closing
from pathlib import Path


ACCOUNT_TYPES = (
    "Bank",
    "Investment",
    "Retirement",
    "Real Estate",
    "Other Asset",
    "Debt",
)


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
        """Create the shared-family account table and migrate older databases."""
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_by INTEGER,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
            }
            if "user_id" in columns:
                connection.execute("ALTER TABLE accounts RENAME TO accounts_private")
                connection.execute(
                    """
                    CREATE TABLE accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_by INTEGER,
                        name TEXT NOT NULL,
                        owner TEXT NOT NULL,
                        account_type TEXT NOT NULL,
                        balance_cents INTEGER NOT NULL CHECK (balance_cents >= 0),
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO accounts
                        (id, created_by, name, owner, account_type, balance_cents, created_at)
                    SELECT id, user_id, name, owner, account_type, balance_cents, created_at
                    FROM accounts_private
                    """
                )
                connection.execute("DROP TABLE accounts_private")
            connection.execute(
                "UPDATE accounts SET account_type = 'Other Asset' "
                "WHERE account_type IN ('Asset', 'Other')"
            )

    def create_account(
        self,
        user_id: int,
        name: str,
        owner: str,
        account_type: str,
        balance_cents: int,
    ) -> None:
        """Save a shared family account and record which user created it."""
        self._validate_account_type(account_type)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO accounts (created_by, name, owner, account_type, balance_cents)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, owner, account_type, balance_cents),
            )

    def list_accounts(self, _user_id: int | None = None) -> list[dict]:
        """Return every account in the shared family ledger."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, name, owner, account_type, balance_cents
                FROM accounts
                ORDER BY balance_cents DESC, name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def update_account(
        self, account_id: int, name: str, owner: str, account_type: str, balance_cents: int
    ) -> bool:
        """Update one shared account and report whether it existed."""
        self._validate_account_type(account_type)
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                UPDATE accounts
                SET name = ?, owner = ?, account_type = ?, balance_cents = ?
                WHERE id = ?
                """,
                (name, owner, account_type, balance_cents, account_id),
            )
        return cursor.rowcount == 1

    @staticmethod
    def _validate_account_type(account_type: str) -> None:
        if account_type not in ACCOUNT_TYPES:
            raise ValueError("Choose a valid account type.")

    def delete_account(self, account_id: int) -> bool:
        """Delete one shared account and report whether it existed."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "DELETE FROM accounts WHERE id = ?", (account_id,)
            )
        return cursor.rowcount == 1
