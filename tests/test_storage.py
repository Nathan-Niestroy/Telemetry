"""Integration tests for Telemetry's SQLite storage classes."""

import tempfile
import unittest
from pathlib import Path

from account import AccountStore
from auth import UserStore


class StorageTests(unittest.TestCase):
    """Verify authentication, isolation, deletion, and reset behavior."""

    def setUp(self) -> None:
        """Create an isolated SQLite database for each test."""
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "telemetry-test.db"
        self.users = UserStore(database_path)
        self.accounts = AccountStore(database_path)

    def tearDown(self) -> None:
        """Remove the temporary database after every test."""
        self.temporary_directory.cleanup()

    def test_first_user_is_admin_and_password_is_verified(self) -> None:
        user_id = self.users.create_user("admin", "correct-password")

        self.assertEqual(
            self.users.authenticate("ADMIN", "correct-password"), (user_id, True)
        )
        self.assertIsNone(self.users.authenticate("admin", "wrong-password"))

    def test_accounts_are_isolated_by_user(self) -> None:
        first_user = self.users.create_user("first", "first-password")
        second_user = self.users.create_user("second", "second-password")
        self.accounts.create_account(
            first_user, "TSP", "First", "Retirement", 2_500_000
        )

        self.assertEqual(len(self.accounts.list_accounts(first_user)), 1)
        self.assertEqual(self.accounts.list_accounts(second_user), [])

    def test_deleting_a_user_cascades_to_their_accounts(self) -> None:
        user_id = self.users.create_user("member", "member-password")
        self.accounts.create_account(user_id, "Bank", "Member", "Bank", 10_000)

        self.users.delete_user(user_id)

        self.assertEqual(self.accounts.list_accounts(user_id), [])

    def test_factory_reset_removes_all_local_data(self) -> None:
        user_id = self.users.create_user("admin", "admin-password")
        self.accounts.create_account(user_id, "TSP", "Admin", "Retirement", 10_000)

        self.users.factory_reset()

        self.assertFalse(self.users.has_users())
        self.assertEqual(self.accounts.list_accounts(user_id), [])


if __name__ == "__main__":
    unittest.main()

