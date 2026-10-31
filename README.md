# Telemetry (deprecated)

> **Deprecated as of October 31, 2026.** Active development has ended. The
> maintainer is moving their finance workflow to ChatGPT with a finance plugin.
> No further features, bug fixes, or security updates are planned.

The source and instructions below are retained for existing users and reference.
Existing installations can still open local data and create encrypted backups.
Before retiring your installation, use **Manage family > Create encrypted backup**
and keep the backup password separately. Telemetry backups are for restoring in
Telemetry; this project does not provide an automatic migration to ChatGPT.
If you used Gmail reports, revoke the dedicated Gmail App Password when you
stop using Telemetry.

![Telemetry application icon](assets/Telemetry_Icon.png)

Telemetry is a private Windows desktop application for monitoring a family's
assets, debts, and net worth in one shared dashboard. It tracks bank accounts,
brokerage and retirement accounts, TSP funds, cash investment positions, loans,
vehicles, and other manually entered assets or liabilities. It also provides
shared income, allocation, monthly spending, and saving plans. Telemetry does
not import bank transactions.

This repository contains the final, unmaintained development version. Telemetry does not use
Plaid or connect to financial institutions. Bank balances and debts are entered
manually; supported investment and TSP positions can be recalculated from their
latest available closing prices.

## Existing features

- First-launch administrator registration using an email address
- Local sign-in with salted PBKDF2-SHA256 password hashes
- Administrator-managed family users and editable login emails
- Mandatory first-login password replacement for administrator-created users
- Shared family dashboard containing every financial account
- Asset, debt, and net-worth totals
- Interactive account-composition chart with hover details
- Account editing for every signed-in family member
- Administrator-only account creation and removal with confirmation
- Account name, owner, type, and current balance tracking
- Debt tracking with liabilities subtracted from family net worth
- Account-linked asset breakdowns using ticker symbols or TSP fund quantities
- Read-only combined holdings overview and fund-position search
- Cash positions within investment-account breakdowns
- After-close Yahoo Finance and official TSP refreshes with last-known-good caching
- Automatic recalculation of a tracked investment account from its holdings
- Holdings disabled for bank and debt accounts
- Exact balance storage using integer cents
- User deletion without deleting shared family financial accounts
- Confirmed factory reset for all local users and accounts
- Dark Universal-style desktop interface matching the Telemetry icon
- SQLite persistence with no separate database server
- Password-encrypted, tamper-detecting backup and validated restore
- Best-effort Windows EFS protection for the live database when available
- Previewed, administrator-triggered Gmail family breakdown emails
- Shared income and payroll-allocation dashboard
- Month-by-month planned and actual spending and saving
- Previous-month plan copying with actual amounts reset to zero

## Requirements

- Windows 11 is the primary development platform
- Python 3.14 is recommended
- Internet access for market refreshes and Gmail reports
- A Gmail account with 2-Step Verification for automatic family reports

Python dependencies are pinned or bounded in `requirements.txt`:

- PySide6 provides the QML desktop interface.
- yfinance retrieves recent Yahoo Finance closing prices.
- keyring stores the Gmail App Password in Windows Credential Manager.

SQLite support is included with Python through the standard-library `sqlite3`
module; it does not need to be installed separately.

## Setup

From PowerShell in the repository directory, create a virtual environment:

```powershell
py -3.14 -m venv .venv
```

If PowerShell blocks activation scripts, allow them for only the current
terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Activate the environment and install the dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Launch Telemetry from the activated environment:

```powershell
python app.py
```

## First-time setup

On first launch, create the administrator account with an email address and a
password containing at least 10 characters. The first user is always the local
administrator.

Administrators create other family users from **Manage family**. Each new user
receives a temporary password and must replace it before Telemetry loads the
dashboard or financial data. Administrators can also edit login emails, delete
users, configure family email reports, and factory-reset the application.

Every authenticated family member sees the same financial dashboard and can
update existing accounts. Only administrators can create or remove accounts.
Signing out clears both login fields.

## Accounts and net worth

Each account has a name, owner, type, and non-negative balance. Supported types
are Bank, Investment, Retirement, Real Estate, Other Asset, and Debt. Older
Asset and Other records are automatically normalized to Other Asset.

- Asset-like accounts increase net worth.
- Debt accounts represent the current amount owed and reduce net worth.
- Owner is a descriptive family label; it does not control access.
- All accounts are visible to every authenticated family user.
- Bank and debt accounts use manually entered balances and cannot have holdings.
- Investment, retirement, real-estate, and other-asset accounts can hold
  positions and calculate their balances from those holdings.

The dashboard shows total assets, total debt, and net worth. Its composition
chart is interactive: hover over a segment or legend entry to identify an
account and its share of the tracked finances.

## Income, allocation, spending, and saving

Use the **Net worth / Budget** switcher below the application header to move
between the two full dashboards. The selected dashboard is highlighted and the
content cross-fades without opening another window. The budget dashboard contains
two shared family views.

**Income & allocation** tracks recurring income sources as annual amounts and
shows their combined monthly gross value. Payroll deductions and allocations are
entered as monthly amounts and grouped as Tax, Benefit, Retirement, or Other.
Telemetry subtracts those allocations from monthly gross income to estimate the
monthly net amount available for the family budget.

**Monthly spending & saving** keeps a separate plan for each calendar month. Each
category is classified as Spending or Saving and stores planned, actual, and
optional note values. The dashboard shows planned spending, planned saving,
remaining income, actual spending, and actual saving. Use the same category name
to update it, or select **Edit** to prefill and rename an existing entry. The
actual-remaining total uses actual spending and saving values instead of the plan.
An empty month can copy the previous month's categories and planned amounts while
resetting every actual amount to zero.

The current 2026 tax planning estimate assumes married filing jointly, one
household income, the federal and Virginia standard deductions, two Virginia
personal exemptions, no dependent or other tax credits, and pre-tax medical and
dental premiums. It estimates annual liability for planning rather than trying to
reproduce payroll withholding. Replace these estimates with actual paystub or
year-to-date amounts when available.

## Holdings and closing prices

Open **Holdings** on an eligible account to manage only that account's positions.
Open **… > Asset breakdown** on the Net Worth dashboard for a read-only,
searchable overview of positions across all accounts.

Telemetry supports:

- Yahoo Finance ticker symbols and fractional share quantities
- Official TSP G, F, C, S, I, L Income, and lifecycle fund quantities
- Cash positions stored at their entered face value

Yahoo Finance tickers do not require an API key. TSP prices come from the
official `tsp.gov` fund-price-history CSV, using the request and cache approach
validated from the MIT-licensed `srichs/tsp-analytics` project. Telemetry does
not depend on Max TSP or another hosted TSP API. A manual TSP close and date can
be entered when needed.

**Refresh closing prices** retrieves the latest available market close rather
than an intraday quote. The last valid TSP download is cached locally. After all
positions in an account have prices, Telemetry replaces that account's raw
balance with the sum of its holding values. A provider failure retains the last
successfully stored price and reports the error in the interface.

## Project structure

```text
Telemetry/
|-- app.py                         Application startup and dependency wiring
|-- telemetry/                     Python application package
|   |-- controllers/               State and actions exposed to QML
|   |   |-- account_controller.py
|   |   |-- auth_controller.py
|   |   |-- budget_controller.py
|   |   |-- report_controller.py
|   |   `-- user_controller.py
|   |-- data/                      Persistence and financial-data services
|   |   |-- account.py
|   |   |-- auth.py
|   |   |-- budget.py
|   |   `-- holding.py
|   `-- platform/
|       `-- windows_theme.py       Native Windows title-bar integration
|-- assets/
|   `-- Telemetry_Icon.png         Application icon
|-- qml/
|   |-- Main.qml                   Shared net-worth dashboard and account list
|   |-- components/
|   |   `-- DashboardHeader.qml    Responsive header and compact actions menu
|   |-- AddAccountDialog.qml       Account-entry form
|   |-- dashboards/
|   |   `-- BudgetDashboard.qml    Full income, spending, and saving dashboard
|   |-- EditAccountDialog.qml      Shared account editing form
|   |-- AssetBreakdownDialog.qml   Ticker/TSP holdings and price refresh
|   |-- EmailPreviewDialog.qml     Review a report before sending
|   |-- EmailSettingsDialog.qml    Secure Gmail report configuration
|   `-- UserManagementDialog.qml   Email-user management and reset controls
|-- tests/
|   `-- test_storage.py            SQLite behavior tests
`-- instance/
    `-- telemetry.db               Private local data; excluded from Git
```

The interface calls Python through controllers:

```text
QML interface -> controllers -> SQLite stores -> instance/telemetry.db
                              -> market closing-price providers
                              -> Gmail SMTP / Windows Credential Manager
```

QML is organized by responsibility: `Main.qml` owns page-level state and
dashboard composition, reusable dashboard pieces live in `qml/components/`, and
focused dialogs handle individual editing workflows. The `telemetry` package
separates persistence and external data services from QML-facing controllers and
platform integration. `app.py` wires those layers together and starts the UI.

## Data and security

Telemetry is currently designed for local use on a trusted computer.

- Passwords are salted and hashed; plaintext passwords are never stored.
- Email addresses are used as case-insensitive login identifiers.
- Temporary-password users cannot load dashboard data until changing passwords.
- SQL statements use parameters for user-supplied values.
- Financial accounts are shared by all authenticated family users.
- Only administrators can create or remove financial accounts; all users can
  edit them.
- The first registered user is the administrator.
- Standard users cannot create users, delete users, or factory-reset the app.
- The signed-in administrator cannot delete their own active account.
- Deleting a user preserves the shared family accounts and holdings.
- The local database and virtual environment are excluded by `.gitignore`.
- The Gmail App Password is stored by Windows Credential Manager, not SQLite.
- Email reports are sent only after an administrator presses **Send breakdown**.
- Reports are sent to every valid email currently listed under **Manage family**.

Telemetry asks Windows EFS to encrypt the live database for the current Windows
user when the filesystem and Windows edition support it. This is best-effort:
when EFS is unavailable, the SQLite database itself is **not encrypted**. Anyone
with access to the computer and database file may be able to read financial
account information.
Do not enter account numbers, banking passwords, access tokens, Social Security
numbers, or other banking credentials. Authentication must be redesigned before
Telemetry supports remote access or synchronization between computers.

Email reports contain sensitive totals and account balances. Verify every family
email address before sending. Before making the repository public, inspect the
full Git history for secrets and personal financial data, not only the latest
files. See [SECURITY.md](SECURITY.md) for the full local-security model.

## Local data and encrypted backup

Source runs store application data in `instance/telemetry.db`. Packaged builds
store it under `%LOCALAPPDATA%\Telemetry`. The official TSP cache is stored next
to the database. These paths are excluded from Git.

Administrators can open **Manage family**, choose **Create encrypted backup**,
and enter a backup password containing at least 12 characters when prompted. The resulting
`.telemetry` file uses scrypt key derivation and authenticated AES-256-GCM
encryption. Restore authenticates the file, runs SQLite integrity and schema
checks, and only then replaces the live database. Reopen Telemetry after restore.

To make an additional manual backup:

1. Close Telemetry so SQLite has no active writes.
2. Copy `instance/telemetry.db` to an encrypted or otherwise trusted location.
3. Protect the backup as carefully as the computer because the database is not
   encrypted.

Restoring a backup replaces the current database. Keep a separate copy of the
current database before restoring an older one. Gmail credentials are managed
separately by Windows Credential Manager and are not included in database copies.

## Factory reset

An administrator can choose **Manage family > Factory reset Telemetry**. After
confirmation, this permanently deletes all local users and financial accounts
and returns Telemetry to first-launch registration. Holdings are removed through
their account relationships. This action cannot be undone unless the database
was backed up separately. The Gmail credential remains in Windows Credential
Manager and can be replaced from Email report settings after registering again.

## Tests

Run the standard-library test suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

## Gmail family report

An administrator can use **Email settings** to configure a Gmail sending address
and a dedicated Google App Password. The App Password is stored by Windows
Credential Manager and is never written to Telemetry's database or source code.
The normal Google password is never requested.

**Send breakdown** previews the current asset, debt, net-worth, account, and
monthly budget summary before emailing it to every valid family login email.
Sending runs in the background. Gmail requires
2-Step Verification before an App Password can be created. The report contains
financial information, so administrators should verify every family email before
sending. The report is sent as both plain text and formatted HTML and includes:

- Net worth, total assets, and total debt
- Every account's name, owner, type, and current balance
- The selected month's planned and actual spending, saving, remaining income,
  categories, and notes
- A note identifying Telemetry as the source of the snapshot

### Gmail setup

1. Enable 2-Step Verification on the sending Google account.
2. Create a dedicated Google App Password named `Telemetry`.
3. In Telemetry, open **Manage family > Email report settings**.
4. Enter the Gmail address and App Password, then select **Save securely**.
5. Select **… > Send breakdown** from either dashboard, review the preview, and
   select **Send email**.

Do not enter the normal Google password. Spaces in the displayed 16-character
App Password are removed automatically. Changing the Google account password may
revoke App Passwords; create and save a new one if Gmail authentication fails.

## Windows packaging

Install development requirements and create the standalone executable:

```powershell
python -m pip install -r requirements-dev.txt
pyinstaller --clean --noconfirm Telemetry.spec
```

The executable is written to `dist/Telemetry.exe`. If Inno Setup 6 is installed,
compile `installer/Telemetry.iss` to create a conventional Windows installer.
GitHub Actions runs the tests, performs an offscreen QML startup test, and uploads
the packaged executable on every push and pull request.

## License

Telemetry is available under the MIT License. See [LICENSE](LICENSE).

## Acknowledgments

Telemetry was made possible by open-source maintainers, data providers, platform
teams, testers, and development tools. Please see [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md)
for the full thank-you list, including the `srichs/tsp-analytics` contributors,
Python, SQLite, Qt for Python, yfinance, keyring, cryptography, PyInstaller,
Pillow, Inno Setup, Microsoft, Google, GitHub, and OpenAI Codex.

## Troubleshooting

- **Incorrect email address or password:** Use the user's family login email and
  Telemetry password, not the Gmail App Password.
- **Password change required:** Sign in with the administrator-issued temporary
  password, then choose a different password containing at least 10 characters.
- **No market close available:** Verify the ticker and internet connection. New
  or delisted symbols may not have usable Yahoo Finance history.
- **Official TSP refresh failed:** Retry later. Telemetry uses its last valid TSP
  cache when one exists, or accepts a manual close and `YYYY-MM-DD` date.
- **Gmail authentication failed:** Confirm 2-Step Verification is enabled and use
  a Google App Password rather than the normal account password.
- **Report has the wrong recipients:** Correct family emails in **Manage family**
  before sending again.
- **Report totals look stale:** Refresh market closing prices or update manual
  bank and debt balances before sending.

## Current limitations

- The database is local to one Windows computer; EFS protection is best-effort.
- There is no bank synchronization, Plaid integration, or transaction import.
- Market values use closing prices, not live intraday quotes.
- Reports contain the current snapshot only and are not scheduled automatically.
- Monthly spending is entered as category totals; Telemetry does not import bank
  transactions or automatically derive actual spending.
