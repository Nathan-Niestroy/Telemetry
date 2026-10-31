"""Release-hardening tests for backups, migrations, and permissions."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from telemetry.controllers.user_controller import UserController
from telemetry.controllers.report_controller import ReportController
from telemetry.data.account import AccountStore
from telemetry.data.auth import UserStore
from telemetry.data.backup import BackupService
from telemetry.data.budget import BudgetStore
from telemetry.data.holding import HoldingStore
from telemetry.data.schema import SCHEMA_VERSION, finalize_schema, validate_database


class ReleaseHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.database = Path(self.temporary.name) / "telemetry.db"
        self.users = UserStore(self.database)
        self.accounts = AccountStore(self.database)
        self.holdings = HoldingStore(self.database)
        self.budgets = BudgetStore(self.database)
        finalize_schema(self.database)

    def test_schema_is_versioned_and_validated(self) -> None:
        validate_database(self.database)
        with closing(sqlite3.connect(self.database)) as connection:
            self.assertEqual(
                connection.execute("PRAGMA user_version").fetchone()[0],
                SCHEMA_VERSION,
            )

    def test_legacy_private_accounts_are_upgraded(self) -> None:
        legacy = Path(self.temporary.name) / "legacy.db"
        users = UserStore(legacy)
        user_id = users.create_user("admin@example.com", "admin-password")
        with closing(sqlite3.connect(legacy)) as connection, connection:
            connection.execute(
                "CREATE TABLE accounts (id INTEGER PRIMARY KEY, user_id INTEGER, "
                "name TEXT, owner TEXT, account_type TEXT, balance_cents INTEGER, "
                "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "INSERT INTO accounts (user_id,name,owner,account_type,balance_cents) "
                "VALUES (?, 'Savings', 'Family', 'Asset', 100)", (user_id,)
            )
        upgraded = AccountStore(legacy)
        self.assertEqual(upgraded.list_accounts()[0]["account_type"], "Other Asset")

    def test_encrypted_backup_round_trip(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Savings", "Family", "Bank", 12345)
        backup = Path(self.temporary.name) / "snapshot.telemetry"
        service = BackupService(self.database)
        service.create(backup, "correct horse battery staple")
        self.accounts.delete_account(self.accounts.list_accounts()[0]["id"])
        service.restore(backup, "correct horse battery staple")
        self.assertEqual(AccountStore(self.database).list_accounts()[0]["balance_cents"], 12345)

    def test_encrypted_backup_rejects_wrong_password_and_tampering(self) -> None:
        backup = Path(self.temporary.name) / "snapshot.telemetry"
        service = BackupService(self.database)
        service.create(backup, "correct horse battery staple")
        with self.assertRaisesRegex(ValueError, "incorrect or the file is damaged"):
            service.restore(backup, "this password is incorrect")
        payload = bytearray(backup.read_bytes())
        payload[-1] ^= 1
        backup.write_bytes(payload)
        with self.assertRaisesRegex(ValueError, "incorrect or the file is damaged"):
            service.restore(backup, "correct horse battery staple")

    def test_non_admin_cannot_manage_users(self) -> None:
        admin_id = self.users.create_user("admin@example.com", "admin-password")
        member_id = self.users.create_user("member@example.com", "member-password")
        controller = UserController(self.users)
        controller.load_for_user(member_id, False)
        self.assertFalse(controller.createUser("new@example.com", "member-password"))
        self.assertFalse(controller.deleteUser(admin_id))
        self.assertFalse(controller.updateUserEmail(admin_id, "changed@example.com"))
        self.assertFalse(controller.factoryReset())
        self.assertEqual(len(self.users.list_users()), 2)

    def test_admin_cannot_delete_current_login(self) -> None:
        admin_id = self.users.create_user("admin@example.com", "admin-password")
        controller = UserController(self.users)
        controller.load_for_user(admin_id, True)
        self.assertFalse(controller.deleteUser(admin_id))
        self.assertTrue(self.users.has_users())

    @patch("telemetry.controllers.report_controller.QSettings")
    @patch("telemetry.controllers.report_controller.keyring.delete_password")
    def test_factory_reset_cleanup_removes_gmail_credential(
        self, delete_password, settings_class
    ) -> None:
        settings = settings_class.return_value
        settings.value.return_value = "sender@example.com"
        controller = ReportController(self.users, self.accounts)
        controller.clearCredentials()
        delete_password.assert_called_once_with(
            "Telemetry.FamilyFinance.Gmail", "sender@example.com"
        )
        settings.remove.assert_called_once_with("report/sender_email")


if __name__ == "__main__":
    unittest.main()
