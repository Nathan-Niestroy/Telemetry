"""Store and refresh market-priced holdings for family accounts."""

import csv
import io
import sqlite3
from contextlib import closing
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


class HoldingStore:
    """Persist ticker, TSP fund, and cash positions in the shared database."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    provider TEXT NOT NULL CHECK (provider IN ('yahoo', 'tsp', 'cash')),
                    symbol TEXT NOT NULL,
                    shares TEXT NOT NULL,
                    last_price_cents INTEGER,
                    price_as_of TEXT,
                    updated_at TEXT,
                    UNIQUE(account_id, provider, symbol),
                    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                )
                """
            )
            schema = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'holdings'"
            ).fetchone()[0]
            if "max_tsp" in schema or "'cash'" not in schema:
                connection.execute("ALTER TABLE holdings RENAME TO holdings_legacy")
                connection.execute(
                    """
                    CREATE TABLE holdings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        provider TEXT NOT NULL CHECK (provider IN ('yahoo', 'tsp', 'cash')),
                        symbol TEXT NOT NULL, shares TEXT NOT NULL,
                        last_price_cents INTEGER, price_as_of TEXT, updated_at TEXT,
                        UNIQUE(account_id, provider, symbol),
                        FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO holdings SELECT id, account_id,
                        CASE provider WHEN 'max_tsp' THEN 'tsp' ELSE provider END,
                        symbol, shares, last_price_cents, price_as_of, updated_at
                    FROM holdings_legacy
                    """
                )
                connection.execute("DROP TABLE holdings_legacy")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_holdings(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT h.id, h.account_id, a.name AS account_name, h.provider,
                       h.symbol, h.shares, h.last_price_cents, h.price_as_of
                FROM holdings h JOIN accounts a ON a.id = h.account_id
                ORDER BY a.name COLLATE NOCASE, h.symbol COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def save_holding(self, account_id: int, provider: str, symbol: str, shares: str) -> int:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO holdings (account_id, provider, symbol, shares)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(account_id, provider, symbol)
                DO UPDATE SET shares = excluded.shares
                """,
                (account_id, provider, symbol, shares),
            )
            row = connection.execute(
                "SELECT id FROM holdings WHERE account_id = ? AND provider = ? AND symbol = ?",
                (account_id, provider, symbol),
            ).fetchone()
        return row[0]

    def delete_holding(self, holding_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))

    def update_price(self, holding_id: int, price: Decimal, as_of: str) -> None:
        cents = int((price * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                UPDATE holdings SET last_price_cents = ?, price_as_of = ?,
                    updated_at = CURRENT_TIMESTAMP WHERE id = ?
                """,
                (cents, as_of, holding_id),
            )

    def recalculate_accounts(self) -> None:
        """Set linked account balances to the sum of priced positions."""
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                UPDATE accounts
                SET balance_cents = (
                    SELECT COALESCE(SUM(
                        CAST(ROUND(CAST(h.shares AS REAL) * h.last_price_cents) AS INTEGER)
                    ), 0)
                    FROM holdings h WHERE h.account_id = accounts.id
                )
                WHERE EXISTS (SELECT 1 FROM holdings h WHERE h.account_id = accounts.id)
                  AND NOT EXISTS (
                      SELECT 1 FROM holdings h
                      WHERE h.account_id = accounts.id AND h.last_price_cents IS NULL
                  )
                """
            )


class MarketPriceService:
    """Retrieve after-close prices without accessing financial credentials."""

    def __init__(self, store: HoldingStore) -> None:
        self.store = store
        self.tsp_cache_path = store.database_path.parent / "tsp-fund-price-history.csv"

    def refresh(self) -> tuple[int, list[str]]:
        holdings = self.store.list_holdings()
        errors: list[str] = []
        updated = 0
        yahoo = [holding for holding in holdings if holding["provider"] == "yahoo"]
        tsp = [holding for holding in holdings if holding["provider"] == "tsp"]

        for holding in yahoo:
            try:
                price, as_of = self._yahoo_close(holding["symbol"])
                self.store.update_price(holding["id"], price, as_of)
                updated += 1
            except Exception as error:  # provider failures should not discard cached prices
                errors.append(f"{holding['symbol']}: {error}")

        if tsp:
            try:
                prices, as_of = self._official_tsp_closes()
                for holding in tsp:
                    price = prices.get(holding["symbol"].upper())
                    if price is None:
                        errors.append(f"{holding['symbol']}: not found in official TSP data")
                        continue
                    self.store.update_price(holding["id"], price, as_of)
                    updated += 1
            except Exception as error:
                errors.append(f"Official TSP: {error}")

        self.store.recalculate_accounts()
        return updated, errors

    @staticmethod
    def _yahoo_close(symbol: str) -> tuple[Decimal, str]:
        import yfinance as yf

        history = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False)
        if history.empty:
            raise ValueError("no market close available")
        row = history.iloc[-1]
        return Decimal(str(row["Close"])), history.index[-1].date().isoformat()

    def _official_tsp_closes(self) -> tuple[dict[str, Decimal], str]:
        """Download the official TSP CSV, falling back to the last valid cache."""
        import requests

        content: bytes | None = None
        fetch_error: Exception | None = None
        try:
            response = requests.get(
                "https://www.tsp.gov/data/fund-price-history.csv",
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; rv:128.0) "
                        "Gecko/20100101 Firefox/128.0"
                    ),
                    "Accept": "text/csv,application/csv,text/plain;q=0.9,*/*;q=0.1",
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.content
            self._parse_tsp_csv(content)  # validate before replacing a good cache
            self.tsp_cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.tsp_cache_path.with_suffix(".csv.tmp")
            temporary_path.write_bytes(content)
            temporary_path.replace(self.tsp_cache_path)
        except Exception as error:
            fetch_error = error

        if content is None:
            if not self.tsp_cache_path.exists():
                raise ValueError(f"download failed and no cached prices exist: {fetch_error}")
            content = self.tsp_cache_path.read_bytes()
        return self._parse_tsp_csv(content)

    @staticmethod
    def _parse_tsp_csv(content: bytes) -> tuple[dict[str, Decimal], str]:
        """Validate official price history and return its newest complete row."""
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {"Date", "G Fund", "F Fund", "C Fund", "S Fund", "I Fund"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("downloaded content is not a valid TSP price CSV")
        latest: dict[str, str] | None = None
        for row in reader:
            if row.get("Date") and (
                latest is None or row["Date"] > latest["Date"]
            ):
                latest = row
        if latest is None:
            raise ValueError("official TSP price CSV contains no price rows")
        prices = {
            fund.upper(): Decimal(value)
            for fund, value in latest.items()
            if fund != "Date" and value not in (None, "")
        }
        return prices, latest["Date"]
