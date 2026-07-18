# Telemetry

![Telemetry application icon](assets/Telemetry_Icon.png)

Telemetry is a private desktop application for monitoring family financial
accounts in one place. It tracks current balances for accounts such as bank
accounts, TSP accounts, Roth IRAs, and other retirement or investment accounts.
Telemetry is currently an account and net-worth tracker, not a transaction or
budgeting application.

This repository contains an early development version. Financial institutions
are not connected automatically, so balances are entered manually.

## Current features

- First-launch administrator registration
- Local sign-in with salted PBKDF2-SHA256 password hashes
- Administrator-managed local users
- Per-user financial account isolation
- Account name, owner, type, and current balance tracking
- Exact balance storage using integer cents
- User deletion with associated-account cleanup
- Confirmed factory reset for all local users and accounts
- Dark Universal-style desktop interface matching the Telemetry icon
- SQLite persistence with no separate database server

## Requirements

- Windows 11 is the primary development platform
- Python 3.14 is recommended
- PySide6 6.11.1

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

Activate the environment and install the dependency:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Launch Telemetry:

```powershell
python app.py
```

On first launch, create the administrator account. Passwords must contain at
least 10 characters. After signing in, accounts can be added from the main
screen and additional local users can be created under **Manage users**.

## Project structure

```text
Telemetry/
|-- app.py                         Application startup and dependency wiring
|-- auth.py                        User persistence and password verification
|-- auth_controller.py             Authentication state exposed to QML
|-- account.py                     Financial-account persistence
|-- account_controller.py          Account state exposed to QML
|-- user_controller.py             Administrator user-management actions
|-- windows_theme.py               Native Windows title-bar integration
|-- assets/
|   `-- Telemetry_Icon.png         Application icon
|-- qml/
|   |-- Main.qml                   Main window and account list
|   |-- AddAccountDialog.qml       Account-entry form
|   `-- UserManagementDialog.qml   User and reset controls
|-- tests/
|   `-- test_storage.py            SQLite behavior tests
`-- instance/
    `-- telemetry.db               Private local data; excluded from Git
```

The interface calls Python through controllers:

```text
QML interface -> controllers -> SQLite stores -> instance/telemetry.db
```

## Data and security

Telemetry is currently designed for local use on a trusted computer.

- Passwords are salted and hashed; plaintext passwords are never stored.
- SQL statements use parameters for user-supplied values.
- Each financial account belongs to one authenticated user.
- The first registered user is the administrator.
- Standard users cannot create users, delete users, or factory-reset the app.
- The signed-in administrator cannot delete their own active account.
- The local database and virtual environment are excluded by `.gitignore`.

The SQLite database itself is **not encrypted**. Anyone with access to the
computer and database file may be able to read financial account information.
Do not enter account numbers, banking passwords, access tokens, Social Security
numbers, or other banking credentials. Authentication must be redesigned before
Telemetry supports remote access or synchronization between computers.

Before making the repository public, inspect the full Git history for secrets
and personal financial data, not only the latest files.

## Factory reset

An administrator can choose **Manage users > Factory reset Telemetry**. After
confirmation, this permanently deletes all local users and financial accounts
and returns Telemetry to first-launch registration. This action cannot be
undone unless the database was backed up separately.

## Tests

Run the standard-library test suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

## Roadmap

Likely next milestones include editing and deleting financial accounts,
calculating total net worth, recording balance history, and displaying account
growth over time.
