"""Create and restore password-encrypted Telemetry database backups."""

import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from telemetry.data.schema import validate_database


MAGIC = b"TELEMETRY-BACKUP\x01"
SALT_SIZE = 16
NONCE_SIZE = 12


class BackupService:
    """Snapshot SQLite and protect the snapshot with a user password."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    @staticmethod
    def _key(password: str, salt: bytes) -> bytes:
        if len(password) < 12:
            raise ValueError("Backup password must be at least 12 characters.")
        return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(
            password.encode("utf-8")
        )

    def create(self, destination: Path, password: str) -> None:
        """Write a consistent, authenticated encrypted snapshot."""
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "telemetry.db"
            with closing(sqlite3.connect(self.database_path)) as source, closing(
                sqlite3.connect(snapshot)
            ) as target:
                source.backup(target)
            plaintext = snapshot.read_bytes()
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        ciphertext = AESGCM(self._key(password, salt)).encrypt(nonce, plaintext, MAGIC)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(MAGIC + salt + nonce + ciphertext)
        os.replace(temporary, destination)

    def restore(self, source: Path, password: str) -> None:
        """Authenticate and validate a backup before atomically replacing SQLite."""
        payload = source.read_bytes()
        minimum = len(MAGIC) + SALT_SIZE + NONCE_SIZE + 16
        if len(payload) < minimum or not payload.startswith(MAGIC):
            raise ValueError("This is not a supported Telemetry backup file.")
        offset = len(MAGIC)
        salt = payload[offset : offset + SALT_SIZE]
        offset += SALT_SIZE
        nonce = payload[offset : offset + NONCE_SIZE]
        ciphertext = payload[offset + NONCE_SIZE :]
        try:
            plaintext = AESGCM(self._key(password, salt)).decrypt(
                nonce, ciphertext, MAGIC
            )
        except Exception as error:
            raise ValueError("The backup password is incorrect or the file is damaged.") from error

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.database_path.with_suffix(".restore.tmp")
        temporary.write_bytes(plaintext)
        try:
            validate_database(temporary)
            os.replace(temporary, self.database_path)
        finally:
            temporary.unlink(missing_ok=True)
