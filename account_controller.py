"""Expose account data and actions to the QML interface."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from PySide6.QtCore import Property, QObject, Signal, Slot

from account import AccountStore


class AccountController(QObject):
    """Manage the current user's financial accounts for the interface."""

    accounts_changed = Signal()
    message_changed = Signal()

    def __init__(self, account_store: AccountStore) -> None:
        """Start without a selected user or any account data in memory."""
        super().__init__()
        self._account_store = account_store
        self._user_id: int | None = None
        self._accounts: list[dict] = []
        self._message = ""

    @Property("QVariantList", notify=accounts_changed)
    def accounts(self) -> list[dict]:
        """Expose QML-ready account dictionaries for the signed-in user."""
        return self._accounts

    @Property(str, notify=message_changed)
    def message(self) -> str:
        """Expose the latest account validation error to QML."""
        return self._message

    @Slot(int, bool)
    def load_for_user(self, user_id: int, _is_admin: bool) -> None:
        """Select the signed-in user and load only their accounts."""
        self._user_id = user_id
        self._reload()

    @Slot()
    def clear(self) -> None:
        """Remove account data from memory when the user signs out."""
        self._user_id = None
        self._accounts = []
        self._set_message("")
        self.accounts_changed.emit()

    @Slot(str, str, str, str, result=bool)
    def addAccount(
        self, name: str, owner: str, account_type: str, balance: str
    ) -> bool:
        """Validate QML form values and save the balance as integer cents."""
        if self._user_id is None:
            self._set_message("Sign in before adding an account.")
            return False

        name = name.strip()
        owner = owner.strip()
        account_type = account_type.strip()
        if not name or not owner or not account_type:
            self._set_message("Complete every account field.")
            return False

        try:
            amount = Decimal(balance.strip())
        except InvalidOperation:
            self._set_message("Enter a valid balance.")
            return False
        if not amount.is_finite() or amount < 0:
            self._set_message("Balance cannot be negative.")
            return False

        cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        self._account_store.create_account(
            self._user_id, name, owner, account_type, cents
        )
        self._set_message("")
        self._reload()
        return True

    def _reload(self) -> None:
        """Reload database records and format cents for display."""
        records = self._account_store.list_accounts(self._user_id)
        self._accounts = [
            {
                **record,
                "balance": f"${Decimal(record['balance_cents']) / Decimal(100):,.2f}",
            }
            for record in records
        ]
        self.accounts_changed.emit()

    def _set_message(self, message: str) -> None:
        """Update the QML-visible message and notify the interface."""
        self._message = message
        self.message_changed.emit()
