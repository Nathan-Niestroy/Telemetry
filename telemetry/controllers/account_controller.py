"""Expose account data and actions to the QML interface."""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from threading import Thread

from PySide6.QtCore import Property, QObject, Signal, Slot

from telemetry.data.account import ACCOUNT_TYPES, AccountStore
from telemetry.data.holding import HoldingStore, MarketPriceService


class AccountController(QObject):
    """Manage the current user's financial accounts for the interface."""

    accounts_changed = Signal()
    message_changed = Signal()
    total_changed = Signal()
    holdings_changed = Signal()
    refresh_state_changed = Signal()
    _refresh_completed = Signal(int, "QVariantList")

    def __init__(
        self, account_store: AccountStore, holding_store: HoldingStore | None = None
    ) -> None:
        """Start without a selected user or any account data in memory."""
        super().__init__()
        self._account_store = account_store
        self._holding_store = holding_store or HoldingStore(account_store.database_path)
        self._market_service = MarketPriceService(self._holding_store)
        self._user_id: int | None = None
        self._is_admin = False
        self._accounts: list[dict] = []
        self._message = ""
        self._holdings: list[dict] = []
        self._refreshing = False
        self._refresh_completed.connect(self._finish_refresh)

    @Property("QVariantList", notify=accounts_changed)
    def accounts(self) -> list[dict]:
        """Expose QML-ready account dictionaries for the signed-in user."""
        return self._accounts

    @Property("QVariantList", notify=accounts_changed)
    def assetAccounts(self) -> list[dict]:
        """Expose only accounts that can contain market-priced holdings."""
        return [
            account for account in self._accounts
            if not account["is_debt"] and account["account_type"] != "Bank"
        ]

    @Property(str, notify=message_changed)
    def message(self) -> str:
        """Expose the latest account validation error to QML."""
        return self._message

    @Property(str, notify=total_changed)
    def totalNetWorth(self) -> str:
        """Expose the family total as display-ready currency."""
        total = sum(account["net_cents"] for account in self._accounts)
        return f"${Decimal(total) / Decimal(100):,.2f}"

    @Property(str, notify=total_changed)
    def totalAssets(self) -> str:
        """Expose the combined value of non-debt accounts."""
        total = sum(
            account["balance_cents"]
            for account in self._accounts
            if not account["is_debt"]
        )
        return f"${Decimal(total) / Decimal(100):,.2f}"

    @Property(str, notify=total_changed)
    def totalDebt(self) -> str:
        """Expose the combined amount owed across debt accounts."""
        total = sum(
            account["balance_cents"]
            for account in self._accounts
            if account["is_debt"]
        )
        return f"${Decimal(total) / Decimal(100):,.2f}"

    @Property("QVariantList", notify=holdings_changed)
    def holdings(self) -> list[dict]:
        """Expose the family's market-priced position breakdown."""
        return self._holdings

    @Property(bool, notify=refresh_state_changed)
    def refreshingPrices(self) -> bool:
        return self._refreshing

    @Property(bool, notify=holdings_changed)
    def hasYahooHoldings(self) -> bool:
        return any(holding["provider"] == "yahoo" for holding in self._holdings)

    @Slot(int, bool)
    def load_for_user(self, user_id: int, is_admin: bool) -> None:
        """Select the signed-in user and load the shared family accounts."""
        self._user_id = user_id
        self._is_admin = is_admin
        self._reload()

    @Slot()
    def clear(self) -> None:
        """Remove account data from memory when the user signs out."""
        self._user_id = None
        self._is_admin = False
        self._accounts = []
        self._holdings = []
        self._set_message("")
        self.accounts_changed.emit()
        self.holdings_changed.emit()
        self.total_changed.emit()

    @Slot(str, str, str, str, result=bool)
    def addAccount(
        self, name: str, owner: str, account_type: str, balance: str
    ) -> bool:
        """Validate QML form values and save the balance as integer cents."""
        if self._user_id is None:
            self._set_message("Sign in before adding an account.")
            return False
        if not self._is_admin:
            self._set_message("Only an administrator can create a new account.")
            return False

        name = name.strip()
        owner = owner.strip()
        account_type = account_type.strip()
        if not name or not owner or not account_type:
            self._set_message("Complete every account field.")
            return False
        if account_type not in ACCOUNT_TYPES:
            self._set_message("Choose a valid account type.")
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

    @Slot(int, str, str, str, str, result=bool)
    def updateAccount(
        self, account_id: int, name: str, owner: str, account_type: str, balance: str
    ) -> bool:
        """Allow any signed-in family member to update a shared account."""
        if self._user_id is None:
            self._set_message("Sign in before editing an account.")
            return False
        validated = self._validate_fields(name, owner, account_type, balance)
        if validated is None:
            return False
        clean_name, clean_owner, clean_type, cents = validated
        if not self._account_store.update_account(
            account_id, clean_name, clean_owner, clean_type, cents
        ):
            self._set_message("That account no longer exists.")
            return False
        self._set_message("")
        self._reload()
        return True

    @Slot(int, result=bool)
    def deleteAccount(self, account_id: int) -> bool:
        """Allow an administrator to remove a shared family account."""
        if self._user_id is None:
            self._set_message("Sign in before removing an account.")
            return False
        if not self._is_admin:
            self._set_message("Only an administrator can remove an account.")
            return False
        if not self._account_store.delete_account(account_id):
            self._set_message("That account no longer exists.")
            return False
        self._set_message("")
        self._reload()
        return True

    @Slot(int, str, str, str, str, str, result=bool)
    def saveHolding(
        self, account_id: int, provider: str, symbol: str, shares: str,
        closing_price: str, price_as_of: str
    ) -> bool:
        """Add or update a Yahoo ticker, official TSP fund, or cash position."""
        if self._user_id is None:
            self._set_message("Sign in before editing holdings.")
            return False
        valid_account_ids = {
            account["id"] for account in self._accounts
            if not account["is_debt"] and account["account_type"] != "Bank"
        }
        if account_id not in valid_account_ids:
            self._set_message("Choose a valid asset account for this holding.")
            return False
        provider = provider.strip().lower()
        symbol = symbol.strip().upper()
        if provider == "cash":
            symbol = "CASH"
        if provider not in {"yahoo", "tsp", "cash"} or not symbol:
            self._set_message("Choose a provider and enter a symbol.")
            return False
        try:
            quantity = Decimal(shares.strip().replace(",", ""))
        except InvalidOperation:
            self._set_message("Enter a valid number of shares.")
            return False
        if not quantity.is_finite() or quantity <= 0:
            self._set_message("Shares must be greater than zero.")
            return False
        price: Decimal | None = None
        if provider == "tsp" and closing_price.strip():
            try:
                price = Decimal(closing_price.strip().replace("$", "").replace(",", ""))
            except InvalidOperation:
                self._set_message("Enter the official TSP closing share price.")
                return False
            if not price.is_finite() or price <= 0 or not price_as_of.strip():
                self._set_message("Enter a positive TSP closing price and its date.")
                return False
        holding_id = self._holding_store.save_holding(
            account_id, provider, symbol, format(quantity.normalize(), "f")
        )
        if provider == "cash":
            self._holding_store.update_price(holding_id, Decimal("1"), "Manual cash")
            self._holding_store.recalculate_accounts()
            self._reload()
        if provider == "tsp" and price is not None:
            self._holding_store.update_price(holding_id, price, price_as_of.strip())
            self._holding_store.recalculate_accounts()
            self._reload()
        self._set_message("")
        self._reload_holdings()
        return True

    @Slot(int)
    def deleteHolding(self, holding_id: int) -> None:
        if self._user_id is None:
            return
        self._holding_store.delete_holding(holding_id)
        self._reload_holdings()

    @Slot()
    def refreshMarketPrices(self) -> None:
        """Refresh providers off the UI thread and retain cached prices on errors."""
        if self._user_id is None or self._refreshing:
            return
        if not self._holdings:
            self._set_message("Add at least one holding before refreshing prices.")
            return
        self._refreshing = True
        self._set_message("Refreshing after-close prices…")
        self.refresh_state_changed.emit()

        def run() -> None:
            updated, errors = self._market_service.refresh()
            self._refresh_completed.emit(updated, errors)

        Thread(target=run, daemon=True).start()

    @Slot(int, "QVariantList")
    def _finish_refresh(self, updated: int, errors: list[str]) -> None:
        self._refreshing = False
        self.refresh_state_changed.emit()
        self._reload()
        if errors:
            self._set_message(
                f"Updated {updated} holding(s). " + " | ".join(errors[:3])
            )
        else:
            self._set_message(f"Updated {updated} holding(s) from closing prices.")

    def _validate_fields(
        self, name: str, owner: str, account_type: str, balance: str
    ) -> tuple[str, str, str, int] | None:
        """Validate editable account fields and return normalized values."""
        name, owner, account_type = name.strip(), owner.strip(), account_type.strip()
        if not name or not owner or not account_type:
            self._set_message("Complete every account field.")
            return None
        if account_type not in ACCOUNT_TYPES:
            self._set_message("Choose a valid account type.")
            return None
        try:
            amount = Decimal(balance.strip().replace(",", "").replace("$", ""))
        except InvalidOperation:
            self._set_message("Enter a valid balance.")
            return None
        if not amount.is_finite() or amount < 0:
            self._set_message("Balance cannot be negative.")
            return None
        cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return name, owner, account_type, cents

    def _reload(self) -> None:
        """Reload database records and format cents for display."""
        records = self._account_store.list_accounts(self._user_id)
        self._accounts = [
            {
                **record,
                "is_debt": record["account_type"] == "Debt",
                "net_cents": (
                    -record["balance_cents"]
                    if record["account_type"] == "Debt"
                    else record["balance_cents"]
                ),
                "balance": (
                    "-$" if record["account_type"] == "Debt" else "$"
                ) + f"{Decimal(record['balance_cents']) / Decimal(100):,.2f}",
            }
            for record in records
        ]
        self.accounts_changed.emit()
        self.total_changed.emit()
        self._reload_holdings()

    def _reload_holdings(self) -> None:
        records = self._holding_store.list_holdings() if self._user_id else []
        self._holdings = [
            {
                **record,
                "provider_name": (
                    "Yahoo Finance" if record["provider"] == "yahoo"
                    else "Official TSP close" if record["provider"] == "tsp"
                    else "Cash"
                ),
                "shares_display": self._format_quantity(record["shares"]),
                "price": "—" if record["last_price_cents"] is None else
                         f"${Decimal(record['last_price_cents']) / Decimal(100):,.2f}",
                "market_value": "—" if record["last_price_cents"] is None else
                                f"${Decimal(record['shares']) * Decimal(record['last_price_cents']) / Decimal(100):,.2f}",
            }
            for record in records
        ]
        self.holdings_changed.emit()

    @staticmethod
    def _format_quantity(shares: str) -> str:
        formatted = f"{Decimal(shares):,f}"
        return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted

    def _set_message(self, message: str) -> None:
        """Update the QML-visible message and notify the interface."""
        self._message = message
        self.message_changed.emit()
