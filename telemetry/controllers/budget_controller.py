"""Expose shared income and monthly budget calculations to QML."""

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from PySide6.QtCore import Property, QObject, Signal, Slot

from telemetry.data.budget import BudgetStore


class BudgetController(QObject):
    changed = Signal()

    def __init__(self, store: BudgetStore) -> None:
        super().__init__()
        self._store = store
        self._authenticated = False
        self._month = date.today().strftime("%Y-%m")
        self._sources: list[dict] = []
        self._allocations: list[dict] = []
        self._items: list[dict] = []
        self._message = ""

    @Property("QVariantList", notify=changed)
    def incomeSources(self) -> list[dict]:
        return self._sources

    @Property("QVariantList", notify=changed)
    def allocations(self) -> list[dict]:
        return self._allocations

    @Property("QVariantList", notify=changed)
    def monthlyItems(self) -> list[dict]:
        return self._items

    @Property(str, notify=changed)
    def currentMonth(self) -> str:
        return self._month

    @Property(str, notify=changed)
    def currentMonthLabel(self) -> str:
        year, month = map(int, self._month.split("-"))
        return date(year, month, 1).strftime("%B %Y")

    @Property(str, notify=changed)
    def message(self) -> str:
        return self._message

    @Property(str, notify=changed)
    def monthlyGross(self) -> str:
        return self._money(self._monthly_gross_cents())

    @Property(str, notify=changed)
    def monthlyAllocations(self) -> str:
        return self._money(sum(item["monthly_cents"] for item in self._allocations))

    @Property(str, notify=changed)
    def monthlyNet(self) -> str:
        return self._money(self._monthly_net_cents())

    @Property(str, notify=changed)
    def plannedSpending(self) -> str:
        return self._money(self._sum_items("Spending", "planned_cents"))

    @Property(str, notify=changed)
    def plannedSaving(self) -> str:
        return self._money(self._sum_items("Saving", "planned_cents"))

    @Property(str, notify=changed)
    def plannedRemaining(self) -> str:
        planned = sum(item["planned_cents"] for item in self._items)
        return self._money(self._monthly_net_cents() - planned)

    @Property(str, notify=changed)
    def actualSpending(self) -> str:
        return self._money(self._sum_items("Spending", "actual_cents"))

    @Property(str, notify=changed)
    def actualSaving(self) -> str:
        return self._money(self._sum_items("Saving", "actual_cents"))

    @Property(str, notify=changed)
    def actualRemaining(self) -> str:
        actual = sum(item["actual_cents"] for item in self._items)
        return self._money(self._monthly_net_cents() - actual)

    @Slot(int, bool)
    def load_for_user(self, _user_id: int, _is_admin: bool) -> None:
        self._authenticated = True
        self._reload()

    @Slot()
    def clear(self) -> None:
        self._authenticated = False
        self._sources = []
        self._allocations = []
        self._items = []
        self._message = ""
        self.changed.emit()

    @Slot(str, str, str, result=bool)
    def saveIncomeSource(self, name: str, income_type: str, annual: str) -> bool:
        cents = self._validate_amount(name, annual)
        if cents is None:
            return False
        self._store.save_income_source(name.strip(), income_type.strip(), cents)
        self._message = ""
        self._reload()
        return True

    @Slot(int)
    def deleteIncomeSource(self, source_id: int) -> None:
        self._store.delete_income_source(source_id)
        self._reload()

    @Slot(int, str, str, str, result=bool)
    def updateIncomeSource(
        self, source_id: int, name: str, income_type: str, annual: str
    ) -> bool:
        cents = self._validate_amount(name, annual)
        if cents is None:
            return False
        try:
            updated = self._store.update_income_source(
                source_id, name.strip(), income_type.strip(), cents
            )
        except ValueError as error:
            return self._set_error(str(error))
        if not updated:
            return self._set_error("That income source no longer exists.")
        self._message = ""
        self._reload()
        return True

    @Slot(str, str, str, result=bool)
    def saveAllocation(self, name: str, group: str, monthly: str) -> bool:
        cents = self._validate_amount(name, monthly)
        if cents is None:
            return False
        self._store.save_allocation(name.strip(), group.strip(), cents)
        self._message = ""
        self._reload()
        return True

    @Slot(int)
    def deleteAllocation(self, allocation_id: int) -> None:
        self._store.delete_allocation(allocation_id)
        self._reload()

    @Slot(int, str, str, str, result=bool)
    def updateAllocation(
        self, allocation_id: int, name: str, group: str, monthly: str
    ) -> bool:
        cents = self._validate_amount(name, monthly)
        if cents is None:
            return False
        try:
            updated = self._store.update_allocation(
                allocation_id, name.strip(), group.strip(), cents
            )
        except ValueError as error:
            return self._set_error(str(error))
        if not updated:
            return self._set_error("That allocation no longer exists.")
        self._message = ""
        self._reload()
        return True

    @Slot(str, str, str, str, str, result=bool)
    def saveMonthlyItem(
        self, name: str, item_type: str, planned: str, actual: str, notes: str
    ) -> bool:
        planned_cents = self._validate_amount(name, planned)
        if planned_cents is None:
            return False
        actual_cents = self._parse_cents(actual or "0")
        if actual_cents is None:
            self._message = "Enter a valid non-negative actual amount."
            self.changed.emit()
            return False
        self._store.save_month_item(
            self._month, name.strip(), item_type, planned_cents, actual_cents,
            notes.strip()
        )
        self._message = ""
        self._reload()
        return True

    @Slot(int)
    def deleteMonthlyItem(self, item_id: int) -> None:
        self._store.delete_month_item(item_id)
        self._reload()

    @Slot(int, str, str, str, str, str, result=bool)
    def updateMonthlyItem(
        self, item_id: int, name: str, item_type: str, planned: str,
        actual: str, notes: str
    ) -> bool:
        planned_cents = self._validate_amount(name, planned)
        if planned_cents is None:
            return False
        actual_cents = self._parse_cents(actual or "0")
        if actual_cents is None:
            return self._set_error("Enter a valid non-negative actual amount.")
        try:
            updated = self._store.update_month_item(
                item_id, name.strip(), item_type, planned_cents, actual_cents,
                notes.strip()
            )
        except ValueError as error:
            return self._set_error(str(error))
        if not updated:
            return self._set_error("That monthly category no longer exists.")
        self._message = ""
        self._reload()
        return True

    @Slot(int)
    def changeMonth(self, offset: int) -> None:
        year, month = map(int, self._month.split("-"))
        month += offset
        year += (month - 1) // 12
        month = (month - 1) % 12 + 1
        self._month = f"{year:04d}-{month:02d}"
        self._items = self._format_items(self._store.list_month_items(self._month))
        self._message = ""
        self.changed.emit()

    @Slot(result=bool)
    def copyPreviousMonth(self) -> bool:
        if self._items:
            self._message = "This month already has budget items."
            self.changed.emit()
            return False
        year, month = map(int, self._month.split("-"))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
        self._store.copy_month(f"{year:04d}-{month:02d}", self._month)
        self._reload()
        return True

    def _reload(self) -> None:
        if not self._authenticated:
            return
        self._sources = [
            {**item, "annual": self._money(item["annual_cents"]),
             "monthly": self._money(self._annual_to_monthly(item["annual_cents"]))}
            for item in self._store.list_income_sources()
        ]
        self._allocations = [
            {**item, "monthly": self._money(item["monthly_cents"])}
            for item in self._store.list_allocations()
        ]
        self._items = self._format_items(self._store.list_month_items(self._month))
        self.changed.emit()

    def _format_items(self, items: list[dict]) -> list[dict]:
        return [
            {**item, "planned": self._money(item["planned_cents"]),
             "actual": self._money(item["actual_cents"])}
            for item in items
        ]

    def _monthly_gross_cents(self) -> int:
        return self._annual_to_monthly(
            sum(item["annual_cents"] for item in self._sources)
        )

    def _monthly_net_cents(self) -> int:
        return self._monthly_gross_cents() - sum(
            item["monthly_cents"] for item in self._allocations
        )

    def _sum_items(self, item_type: str, field: str) -> int:
        return sum(item[field] for item in self._items if item["item_type"] == item_type)

    def report_snapshot(self) -> dict:
        """Return the active month's raw budget values for the family email."""
        planned_total = sum(item["planned_cents"] for item in self._items)
        actual_total = sum(item["actual_cents"] for item in self._items)
        return {
            "month": self.currentMonthLabel,
            "monthly_net_cents": self._monthly_net_cents(),
            "planned_spending_cents": self._sum_items("Spending", "planned_cents"),
            "planned_saving_cents": self._sum_items("Saving", "planned_cents"),
            "planned_remaining_cents": self._monthly_net_cents() - planned_total,
            "actual_spending_cents": self._sum_items("Spending", "actual_cents"),
            "actual_saving_cents": self._sum_items("Saving", "actual_cents"),
            "actual_remaining_cents": self._monthly_net_cents() - actual_total,
            "items": [dict(item) for item in self._items],
        }

    def _validate_amount(self, name: str, amount: str) -> int | None:
        if not self._authenticated:
            self._message = "Sign in before editing the family budget."
            self.changed.emit()
            return None
        if not name.strip():
            self._message = "Enter a name or category."
            self.changed.emit()
            return None
        cents = self._parse_cents(amount)
        if cents is None:
            self._message = "Enter a valid non-negative amount."
            self.changed.emit()
        return cents

    def _set_error(self, message: str) -> bool:
        self._message = message
        self.changed.emit()
        return False

    @staticmethod
    def _annual_to_monthly(annual_cents: int) -> int:
        return int(
            (Decimal(annual_cents) / Decimal(12)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )

    @staticmethod
    def _parse_cents(amount: str) -> int | None:
        try:
            value = Decimal(amount.replace(",", "").replace("$", "").strip())
        except InvalidOperation:
            return None
        if not value.is_finite() or value < 0:
            return None
        return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    @staticmethod
    def _money(cents: int) -> str:
        sign = "-" if cents < 0 else ""
        return f"{sign}${abs(cents) / 100:,.2f}"
