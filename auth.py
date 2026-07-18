"""Store Telemetry users and verify their passwords with SQLite."""

import hashlib
import hmac
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path


# Repeating the hash makes password guessing intentionally expensive.
PBKDF2_ITERATIONS = 600_000


class UserStore:
    """Provide the database operations needed by the login screen."""

    def __init__(self, database_path: Path) -> None:
        """Prepare the database directory and users table."""
        # SQLite cannot create missing parent folders itself.
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = database_path
        self._create_tables()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection that returns rows accessible by column name."""
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_tables(self) -> None:
        """Create the users table the first time Telemetry is launched."""
        # `closing` releases the file handle; `connection` commits the transaction.
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(users)").fetchall()
            }
            if "is_admin" not in columns:
                connection.execute(
                    "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0"
                )
            # Existing installations need one administrator after the migration.
            connection.execute(
                """
                UPDATE users SET is_admin = 1
                WHERE id = (SELECT MIN(id) FROM users)
                  AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin = 1)
                """
            )

    def has_users(self) -> bool:
        """Return whether at least one login has already been created."""
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT EXISTS(SELECT 1 FROM users)").fetchone()
        return bool(row[0])

    def create_user(self, username: str, password: str) -> int:
        """Validate a new user, store a salted password hash, and return its ID."""
        # Whitespace around a username should not create a different account.
        username = username.strip()
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if len(password) < 10:
            raise ValueError("Password must be at least 10 characters.")

        # Each password gets a random salt so equal passwords have different hashes.
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)

        try:
            with closing(self._connect()) as connection, connection:
                is_first_user = not bool(
                    connection.execute("SELECT EXISTS(SELECT 1 FROM users)").fetchone()[0]
                )
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, salt, is_admin)
                    VALUES (?, ?, ?, ?)
                    """,
                    # Hex strings are easy to store safely in SQLite TEXT columns.
                    (username, password_hash.hex(), salt.hex(), int(is_first_user)),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("That username already exists.") from error
        return cursor.lastrowid

    def authenticate(self, username: str, password: str) -> tuple[int, bool] | None:
        """Return the user's ID and admin status when credentials match."""
        with closing(self._connect()) as connection:
            user = connection.execute(
                "SELECT id, password_hash, salt, is_admin FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()

        if user is None:
            return None

        # Recreate the hash using the stored salt instead of decrypting a password.
        expected_hash = bytes.fromhex(user["password_hash"])
        salt = bytes.fromhex(user["salt"])
        supplied_hash = self._hash_password(password, salt)
        # Constant-time comparison avoids leaking information through timing differences.
        if hmac.compare_digest(supplied_hash, expected_hash):
            return user["id"], bool(user["is_admin"])
        return None

    def verify_user(self, username: str, password: str) -> bool:
        """Return True only when the supplied credentials are valid."""
        return self.authenticate(username, password) is not None

    def list_users(self) -> list[dict]:
        """Return non-sensitive user details for the management screen."""
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, username, is_admin, created_at FROM users ORDER BY username"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_user(self, user_id: int) -> None:
        """Delete a user; their accounts are removed by the foreign key cascade."""
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def factory_reset(self) -> None:
        """Remove all local accounts and users while retaining the table schema."""
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM accounts")
            connection.execute("DELETE FROM users")
            connection.execute(
                "DELETE FROM sqlite_sequence WHERE name IN ('accounts', 'users')"
            )

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        """Turn a password into a one-way PBKDF2-SHA256 hash."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
