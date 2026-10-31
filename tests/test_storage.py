"""Integration tests for Telemetry's SQLite storage classes."""

import tempfile
import unittest
import sqlite3
from decimal import Decimal
from pathlib import Path

from telemetry.controllers.account_controller import AccountController
from telemetry.controllers.budget_controller import BudgetController
from telemetry.controllers.report_controller import ReportController
from telemetry.data.account import AccountStore
from telemetry.data.auth import UserStore
from telemetry.data.budget import BudgetStore
from telemetry.data.holding import HoldingStore, MarketPriceService


class StorageTests(unittest.TestCase):
    """Verify authentication, isolation, deletion, and reset behavior."""

    def setUp(self) -> None:
        """Create an isolated SQLite database for each test."""
        self.temporary_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temporary_directory.name) / "telemetry-test.db"
        self.users = UserStore(database_path)
        self.accounts = AccountStore(database_path)
        self.holdings = HoldingStore(database_path)
        self.budgets = BudgetStore(database_path)

    def tearDown(self) -> None:
        """Remove the temporary database after every test."""
        self.temporary_directory.cleanup()

    def test_first_user_is_admin_and_password_is_verified(self) -> None:
        user_id = self.users.create_user("admin@example.com", "correct-password")

        self.assertEqual(
            self.users.authenticate("ADMIN@EXAMPLE.COM", "correct-password"),
            (user_id, True, False),
        )
        self.assertIsNone(
            self.users.authenticate("admin@example.com", "wrong-password")
        )

    def test_temporary_password_must_be_changed_on_first_login(self) -> None:
        self.users.create_user("admin@example.com", "admin-password")
        user_id = self.users.create_user(
            "member@example.com", "temporary-password", must_change_password=True
        )

        self.assertEqual(
            self.users.authenticate("member@example.com", "temporary-password"),
            (user_id, False, True),
        )
        with self.assertRaisesRegex(ValueError, "different"):
            self.users.change_required_password(user_id, "temporary-password")

        self.users.change_required_password(user_id, "new-secure-password")

        self.assertIsNone(
            self.users.authenticate("member@example.com", "temporary-password")
        )
        self.assertEqual(
            self.users.authenticate("member@example.com", "new-secure-password"),
            (user_id, False, False),
        )

    def test_login_email_can_be_updated(self) -> None:
        user_id = self.users.create_user("old@example.com", "secure-password")

        self.users.update_user_email(user_id, "new@example.com")

        self.assertIsNone(self.users.authenticate("old@example.com", "secure-password"))
        self.assertEqual(
            self.users.authenticate("new@example.com", "secure-password"),
            (user_id, True, False),
        )
        with self.assertRaisesRegex(ValueError, "valid email"):
            self.users.update_user_email(user_id, "not-an-email")

    def test_family_report_contains_dashboard_totals_and_accounts(self) -> None:
        accounts = [
            {"name": "Savings", "owner": "Family", "account_type": "Bank", "balance_cents": 100_000},
            {"name": "Loan", "owner": "Family", "account_type": "Debt", "balance_cents": 25_000},
        ]

        message = ReportController._build_message(
            "sender@example.com", ["family@example.com"], accounts
        )
        plain = message.get_body(preferencelist=("plain",)).get_content()

        self.assertIn("Net worth: $750.00", plain)
        self.assertIn("Total debt: $250.00", plain)
        self.assertIn("Savings", plain)

    def test_family_report_contains_selected_month_budget(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        budget = BudgetController(self.budgets)
        budget.load_for_user(user_id, True)
        self.assertTrue(budget.saveIncomeSource("Job", "Salary", "120000"))
        self.assertTrue(budget.saveAllocation("Taxes", "Tax", "2500"))
        self.assertTrue(
            budget.saveMonthlyItem(
                "Groceries", "Spending", "600", "575", "Includes household goods"
            )
        )
        self.assertTrue(
            budget.saveMonthlyItem("Emergency fund", "Saving", "500", "450", "")
        )

        message = ReportController._build_message(
            "sender@example.com", [], [], budget.report_snapshot()
        )
        plain = message.get_body(preferencelist=("plain",)).get_content()
        html_body = message.get_body(preferencelist=("html",)).get_content()

        self.assertIn(f"Monthly spending & saving — {budget.currentMonthLabel}", plain)
        self.assertIn("Planned spending: $600.00", plain)
        self.assertIn("Actual saving: $450.00", plain)
        self.assertIn("Groceries (Spending): planned $600.00, actual $575.00", plain)
        self.assertIn("Includes household goods", html_body)

    def test_family_report_can_be_previewed_before_sending(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Savings", "Family", "Bank", 100_000)
        budget = BudgetController(self.budgets)
        budget.load_for_user(user_id, True)
        self.assertTrue(
            budget.saveMonthlyItem("Groceries", "Spending", "600", "575", "")
        )
        report = ReportController(self.users, self.accounts, budget)
        report.load_for_user(user_id, True)

        self.assertTrue(report.preparePreview())
        self.assertEqual(report.previewRecipients, "admin@example.com")
        self.assertIn("Savings", report.previewText)
        self.assertIn("Groceries", report.previewText)
        self.assertIn("Family financial breakdown", report.previewHtml)
        self.assertIn("Budget summary", report.previewHtml)
        self.assertIn("role='presentation'", report.previewHtml)

    def test_income_allocations_and_monthly_budget_are_calculated(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        controller = BudgetController(self.budgets)
        controller.load_for_user(user_id, True)

        self.assertTrue(controller.saveIncomeSource("Job", "Salary", "120000"))
        self.assertTrue(controller.saveAllocation("Taxes", "Tax", "2500"))
        self.assertTrue(
            controller.saveMonthlyItem("Rent", "Spending", "2000", "1950", "")
        )
        self.assertTrue(
            controller.saveMonthlyItem("Emergency fund", "Saving", "500", "500", "")
        )

        self.assertEqual(controller.monthlyGross, "$10,000.00")
        self.assertEqual(controller.monthlyNet, "$7,500.00")
        self.assertEqual(controller.plannedSpending, "$2,000.00")
        self.assertEqual(controller.plannedSaving, "$500.00")
        self.assertEqual(controller.plannedRemaining, "$5,000.00")
        self.assertEqual(controller.actualRemaining, "$5,050.00")

        source = controller.incomeSources[0]
        self.assertTrue(
            controller.updateIncomeSource(
                source["id"], "Primary job", "Salary", "120600"
            )
        )
        self.assertEqual(controller.monthlyGross, "$10,050.00")

        rent = next(item for item in controller.monthlyItems if item["name"] == "Rent")
        self.assertTrue(
            controller.updateMonthlyItem(
                rent["id"], "Housing", "Spending", "2050", "2000", "Updated"
            )
        )
        self.assertEqual(
            next(item for item in controller.monthlyItems if item["name"] == "Housing")["actual"],
            "$2,000.00",
        )

    def test_previous_month_plan_copies_without_actual_spending(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        controller = BudgetController(self.budgets)
        controller.load_for_user(user_id, True)
        controller.changeMonth(-1)
        self.assertTrue(
            controller.saveMonthlyItem("Groceries", "Spending", "500", "475", "")
        )
        controller.changeMonth(1)

        self.assertTrue(controller.copyPreviousMonth())

        self.assertEqual(controller.monthlyItems[0]["planned"], "$500.00")
        self.assertEqual(controller.monthlyItems[0]["actual"], "$0.00")

    def test_accounts_are_shared_with_the_family(self) -> None:
        first_user = self.users.create_user("first@example.com", "first-password")
        second_user = self.users.create_user("second@example.com", "second-password")
        self.accounts.create_account(
            first_user, "TSP", "First", "Retirement", 2_500_000
        )

        self.assertEqual(len(self.accounts.list_accounts(first_user)), 1)
        self.assertEqual(len(self.accounts.list_accounts(second_user)), 1)

    def test_family_account_can_be_updated(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Savings", "Family", "Bank", 10_000)
        account_id = self.accounts.list_accounts()[0]["id"]

        self.assertTrue(
            self.accounts.update_account(
                account_id, "Emergency fund", "Family", "Bank", 25_000
            )
        )
        self.assertEqual(self.accounts.list_accounts()[0]["balance_cents"], 25_000)

    def test_legacy_account_types_are_normalized(self) -> None:
        connection = sqlite3.connect(self.accounts.database_path)
        try:
            connection.execute(
                """
                INSERT INTO accounts (name, owner, account_type, balance_cents)
                VALUES ('Legacy asset', 'Family', 'Asset', 10000),
                       ('Legacy other', 'Family', 'Other', 20000)
                """
            )
            connection.commit()
        finally:
            connection.close()

        migrated_store = AccountStore(self.accounts.database_path)

        self.assertEqual(
            {account["account_type"] for account in migrated_store.list_accounts()},
            {"Other Asset"},
        )

    def test_unknown_account_type_is_rejected(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        controller = AccountController(self.accounts, self.holdings)
        controller.load_for_user(user_id, True)

        self.assertFalse(controller.addAccount("Wallet", "Family", "Cash", "10"))
        self.assertEqual(controller.message, "Choose a valid account type.")
        self.assertEqual(self.accounts.list_accounts(), [])

    def test_family_account_and_its_holdings_can_be_deleted(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Brokerage", "Family", "Investment", 0)
        account_id = self.accounts.list_accounts()[0]["id"]
        self.holdings.save_holding(account_id, "yahoo", "VTI", "1")

        self.assertTrue(self.accounts.delete_account(account_id))
        self.assertEqual(self.accounts.list_accounts(), [])
        self.assertEqual(self.holdings.list_holdings(), [])

    def test_only_an_admin_can_delete_a_family_account(self) -> None:
        admin_id = self.users.create_user("admin@example.com", "admin-password")
        member_id = self.users.create_user("member@example.com", "member-password")
        self.accounts.create_account(admin_id, "Savings", "Family", "Bank", 10_000)
        account_id = self.accounts.list_accounts()[0]["id"]
        controller = AccountController(self.accounts, self.holdings)

        controller.load_for_user(member_id, False)
        self.assertFalse(controller.deleteAccount(account_id))
        self.assertEqual(len(self.accounts.list_accounts()), 1)

        controller.load_for_user(admin_id, True)
        self.assertTrue(controller.deleteAccount(account_id))
        self.assertEqual(self.accounts.list_accounts(), [])

    def test_debt_is_subtracted_from_family_net_worth(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Savings", "Family", "Bank", 100_000)
        self.accounts.create_account(user_id, "Credit card", "Family", "Debt", 25_000)
        controller = AccountController(self.accounts)

        controller.load_for_user(user_id, True)

        self.assertEqual(controller.totalNetWorth, "$750.00")
        self.assertEqual(controller.totalAssets, "$1,000.00")
        self.assertEqual(controller.totalDebt, "$250.00")
        debt = next(account for account in controller.accounts if account["is_debt"])
        self.assertEqual(debt["balance"], "-$250.00")

    def test_fractional_holdings_recalculate_the_linked_account(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Brokerage", "Family", "Investment", 0)
        account_id = self.accounts.list_accounts()[0]["id"]
        self.holdings.save_holding(account_id, "yahoo", "VTI", "2.5")
        holding_id = self.holdings.list_holdings()[0]["id"]

        self.holdings.update_price(holding_id, Decimal("100.25"), "2026-07-17")
        self.holdings.recalculate_accounts()

        self.assertEqual(self.accounts.list_accounts()[0]["balance_cents"], 25_063)
        controller = AccountController(self.accounts, self.holdings)
        controller.load_for_user(user_id, True)
        self.assertEqual(controller.holdings[0]["shares_display"], "2.5")
        self.assertEqual(controller._format_quantity("100"), "100")

    def test_tsp_close_can_be_entered_without_a_third_party_api(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "TSP", "Family", "Retirement", 0)
        account_id = self.accounts.list_accounts()[0]["id"]
        controller = AccountController(self.accounts, self.holdings)
        controller.load_for_user(user_id, True)

        self.assertTrue(
            controller.saveHolding(
                account_id, "tsp", "C Fund", "10", "100.25", "2026-07-17"
            )
        )

        self.assertEqual(self.accounts.list_accounts()[0]["balance_cents"], 100_250)
        self.assertEqual(controller.holdings[0]["provider_name"], "Official TSP close")

    def test_holding_cannot_be_attached_to_a_debt_account(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Loan", "Family", "Debt", 10_000)
        account_id = self.accounts.list_accounts()[0]["id"]
        controller = AccountController(self.accounts, self.holdings)
        controller.load_for_user(user_id, True)

        self.assertFalse(
            controller.saveHolding(account_id, "yahoo", "VTI", "1", "", "")
        )
        self.assertEqual(self.holdings.list_holdings(), [])

    def test_holding_cannot_be_attached_to_a_bank_account(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Checking", "Family", "Bank", 10_000)
        account_id = self.accounts.list_accounts()[0]["id"]
        controller = AccountController(self.accounts, self.holdings)
        controller.load_for_user(user_id, True)

        self.assertFalse(
            controller.saveHolding(account_id, "cash", "", "100", "", "")
        )
        self.assertEqual(self.holdings.list_holdings(), [])

    def test_cash_holding_is_included_at_face_value(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "Brokerage", "Family", "Investment", 0)
        account_id = self.accounts.list_accounts()[0]["id"]
        controller = AccountController(self.accounts, self.holdings)
        controller.load_for_user(user_id, True)

        self.assertTrue(
            controller.saveHolding(account_id, "cash", "", "725.50", "", "")
        )

        self.assertEqual(self.accounts.list_accounts()[0]["balance_cents"], 72_550)
        self.assertEqual(controller.holdings[0]["provider_name"], "Cash")

    def test_official_tsp_csv_returns_latest_fund_closes(self) -> None:
        content = (
            "Date,G Fund,F Fund,C Fund,S Fund,I Fund,L 2050\n"
            "2026-07-16,19.1,20.2,100.3,90.4,50.5,40.6\n"
            "2026-07-17,19.2,20.3,101.4,91.5,51.6,41.7\n"
        ).encode()

        prices, as_of = MarketPriceService._parse_tsp_csv(content)

        self.assertEqual(as_of, "2026-07-17")
        self.assertEqual(prices["C FUND"], Decimal("101.4"))
        self.assertEqual(prices["L 2050"], Decimal("41.7"))

    def test_deleting_a_user_preserves_family_accounts(self) -> None:
        user_id = self.users.create_user("member@example.com", "member-password")
        self.accounts.create_account(user_id, "Bank", "Member", "Bank", 10_000)

        self.users.delete_user(user_id)

        self.assertEqual(len(self.accounts.list_accounts()), 1)

    def test_factory_reset_removes_all_local_data(self) -> None:
        user_id = self.users.create_user("admin@example.com", "admin-password")
        self.accounts.create_account(user_id, "TSP", "Admin", "Retirement", 10_000)

        self.users.factory_reset()

        self.assertFalse(self.users.has_users())
        self.assertEqual(self.accounts.list_accounts(user_id), [])


if __name__ == "__main__":
    unittest.main()
