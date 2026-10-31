# Telemetry security notes

Telemetry is deprecated as of October 31, 2026 and is no longer maintained.
No security updates are planned. The notes below describe the existing design,
not an ongoing support commitment. See [README.md](README.md) for retirement
and backup guidance.

Telemetry is a local family net-worth application intended for a trusted Windows
computer. It has not been designed as an internet-facing service.

## Protected information

- Telemetry passwords are hashed with PBKDF2-SHA256, a random salt, and 600,000
  iterations. Plaintext login passwords are not stored.
- Gmail reporting uses a dedicated Google App Password. The credential is stored
  through the Windows Credential Manager backend and is not written to SQLite,
  the repository, or QML settings.
- SQL operations use bound parameters for user-provided values.
- A temporary-password user cannot load financial data until replacing the
  administrator-issued password.

## Information stored locally

`instance/telemetry.db` (or `%LOCALAPPDATA%\Telemetry\telemetry.db` in a packaged
build) contains login emails, password hashes and salts, family
accounts, balances, owners, holdings, cached closing prices, income, payroll
allocations, monthly spending and saving plans, actual category totals, and price
dates. Telemetry requests Windows EFS protection for the live file, but EFS is
unavailable on some Windows editions, filesystems, and managed devices. Treat the
database as unencrypted unless Windows Advanced Attributes shows it as encrypted.

The TSP price cache contains public market information only. The Gmail App
Password is stored separately in Windows Credential Manager under the service
name `Telemetry.FamilyFinance.Gmail`.

## Permissions

- The first registered user is the administrator.
- Only administrators can create users, create or remove financial accounts,
  edit login emails, delete users, configure Gmail, send reports, or
  factory-reset data.
- Every authenticated family user can view all shared accounts and edit existing
  balances, eligible holdings, income, allocations, and monthly budgets.
- Deleting a user does not delete shared financial accounts.

These permissions protect against accidental in-app actions. They do not protect
the database from another Windows user or program that already has filesystem
access.

## Sensitive data guidance

Do not store account numbers, bank credentials, access tokens, Social Security
numbers, tax documents, or other secrets in account names or owner labels. Use
descriptive labels such as `House brokerage` or `Family savings`.

Family report emails contain financial totals, account-level balances, and
monthly budget details. Verify the recipients in the preview before sending and
treat received reports as sensitive.

## Credential rotation

If the Gmail App Password may have been exposed:

1. Revoke it from the Google Account security settings.
2. Create a new App Password dedicated to Telemetry.
3. Replace it through **Manage family > Email report settings**.

Changing the normal Google password can also revoke existing App Passwords.

## Backup and reset behavior

Prefer Telemetry's password-encrypted `.telemetry` backups. They use scrypt and
AES-256-GCM, and restore validates authentication and SQLite integrity before
replacement. Protect the backup password separately.

Factory reset deletes local users, accounts, budgets, and holdings from SQLite
and removes Telemetry's Gmail credential and sender setting. Revoke the App
Password through the Google Account as well if it may have been exposed.

## Before publishing or sharing the repository

Inspect the entire Git history and untracked files for financial data and
credentials. Confirm that `instance/`, database files, virtual environments, and
environment files remain excluded. Never commit a Gmail App Password.
