"""Store recurring income, payroll allocations, and monthly family budgets."""

import sqlite3
from contextlib import closing
from pathlib import Path


class BudgetStore:
    """Persist the shared family budget alongside net-worth data."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._create_tables()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_tables(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS income_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    income_type TEXT NOT NULL,
                    annual_cents INTEGER NOT NULL CHECK (annual_cents >= 0)
                );

                CREATE TABLE IF NOT EXISTS income_allocations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    allocation_group TEXT NOT NULL,
                    monthly_cents INTEGER NOT NULL CHECK (monthly_cents >= 0)
                );

                CREATE TABLE IF NOT EXISTS monthly_budget_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    budget_month TEXT NOT NULL,
                    name TEXT NOT NULL COLLATE NOCASE,
                    item_type TEXT NOT NULL CHECK (item_type IN ('Spending', 'Saving')),
                    planned_cents INTEGER NOT NULL CHECK (planned_cents >= 0),
                    actual_cents INTEGER NOT NULL DEFAULT 0 CHECK (actual_cents >= 0),
                    notes TEXT NOT NULL DEFAULT '',
                    UNIQUE (budget_month, name)
                );
                """
            )

    def list_income_sources(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT id, name, income_type, annual_cents FROM income_sources "
                "ORDER BY annual_cents DESC, name COLLATE NOCASE"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_income_source(self, name: str, income_type: str, annual_cents: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO income_sources (name, income_type, annual_cents)
                   VALUES (?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       income_type = excluded.income_type,
                       annual_cents = excluded.annual_cents""",
                (name, income_type, annual_cents),
            )

    def update_income_source(
        self, source_id: int, name: str, income_type: str, annual_cents: int
    ) -> bool:
        try:
            with closing(self._connect()) as connection, connection:
                cursor = connection.execute(
                    """UPDATE income_sources
                       SET name = ?, income_type = ?, annual_cents = ?
                       WHERE id = ?""",
                    (name, income_type, annual_cents, source_id),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("That income source name is already in use.") from error
        return cursor.rowcount == 1

    def delete_income_source(self, source_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM income_sources WHERE id = ?", (source_id,))

    def list_allocations(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT id, name, allocation_group, monthly_cents
                   FROM income_allocations
                   ORDER BY allocation_group, monthly_cents DESC, name COLLATE NOCASE"""
            ).fetchall()
        return [dict(row) for row in rows]

    def save_allocation(self, name: str, group: str, monthly_cents: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO income_allocations (name, allocation_group, monthly_cents)
                   VALUES (?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       allocation_group = excluded.allocation_group,
                       monthly_cents = excluded.monthly_cents""",
                (name, group, monthly_cents),
            )

    def update_allocation(
        self, allocation_id: int, name: str, group: str, monthly_cents: int
    ) -> bool:
        try:
            with closing(self._connect()) as connection, connection:
                cursor = connection.execute(
                    """UPDATE income_allocations
                       SET name = ?, allocation_group = ?, monthly_cents = ?
                       WHERE id = ?""",
                    (name, group, monthly_cents, allocation_id),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("That allocation name is already in use.") from error
        return cursor.rowcount == 1

    def delete_allocation(self, allocation_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "DELETE FROM income_allocations WHERE id = ?", (allocation_id,)
            )

    def list_month_items(self, month: str) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """SELECT id, budget_month, name, item_type, planned_cents,
                          actual_cents, notes
                   FROM monthly_budget_items WHERE budget_month = ?
                   ORDER BY item_type, planned_cents DESC, name COLLATE NOCASE""",
                (month,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_month_item(
        self, month: str, name: str, item_type: str, planned_cents: int,
        actual_cents: int, notes: str
    ) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT INTO monthly_budget_items
                       (budget_month, name, item_type, planned_cents, actual_cents, notes)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(budget_month, name) DO UPDATE SET
                       item_type = excluded.item_type,
                       planned_cents = excluded.planned_cents,
                       actual_cents = excluded.actual_cents,
                       notes = excluded.notes""",
                (month, name, item_type, planned_cents, actual_cents, notes),
            )

    def update_month_item(
        self, item_id: int, name: str, item_type: str, planned_cents: int,
        actual_cents: int, notes: str
    ) -> bool:
        try:
            with closing(self._connect()) as connection, connection:
                cursor = connection.execute(
                    """UPDATE monthly_budget_items
                       SET name = ?, item_type = ?, planned_cents = ?,
                           actual_cents = ?, notes = ?
                       WHERE id = ?""",
                    (name, item_type, planned_cents, actual_cents, notes, item_id),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("That category name is already used this month.") from error
        return cursor.rowcount == 1

    def delete_month_item(self, item_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM monthly_budget_items WHERE id = ?", (item_id,))

    def copy_month(self, source_month: str, target_month: str) -> None:
        """Copy planned categories into an empty month with zero actual amounts."""
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """INSERT OR IGNORE INTO monthly_budget_items
                       (budget_month, name, item_type, planned_cents, actual_cents, notes)
                   SELECT ?, name, item_type, planned_cents, 0, notes
                   FROM monthly_budget_items WHERE budget_month = ?""",
                (target_month, source_month),
            )

    def factory_reset(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM monthly_budget_items")
            connection.execute("DELETE FROM income_allocations")
            connection.execute("DELETE FROM income_sources")
