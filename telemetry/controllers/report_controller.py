"""Create and send family dashboard summaries through Gmail SMTP."""

import html
import smtplib
from email.message import EmailMessage
from threading import Thread
from typing import Callable

import keyring
from PySide6.QtCore import QObject, Property, QSettings, Signal, Slot

from telemetry.controllers.budget_controller import BudgetController
from telemetry.data.account import AccountStore
from telemetry.data.auth import EMAIL_PATTERN, UserStore


class ReportController(QObject):
    """Store email credentials securely and send administrator-approved reports."""

    state_changed = Signal()
    _send_completed = Signal(bool, str)
    _credential_service = "Telemetry.FamilyFinance.Gmail"

    def __init__(
        self,
        user_store: UserStore,
        account_store: AccountStore,
        budget_controller: BudgetController | None = None,
    ) -> None:
        super().__init__()
        self._user_store = user_store
        self._account_store = account_store
        self._budget_controller = budget_controller
        self._settings = QSettings("Telemetry", "FamilyFinance")
        self._sender_email = self._settings.value("report/sender_email", "", str)
        self._is_admin = False
        self._sending = False
        self._message = ""
        self._preview_text = ""
        self._preview_html = ""
        self._preview_recipients = ""
        self._prepared_message: EmailMessage | None = None
        self._send_completed.connect(self._finish_send)

    @Property(str, notify=state_changed)
    def senderEmail(self) -> str:
        return self._sender_email

    @Property(bool, notify=state_changed)
    def configured(self) -> bool:
        if not self._sender_email:
            return False
        try:
            return bool(
                keyring.get_password(self._credential_service, self._sender_email)
            )
        except keyring.errors.KeyringError:
            return False

    @Property(bool, notify=state_changed)
    def sending(self) -> bool:
        return self._sending

    @Property(str, notify=state_changed)
    def message(self) -> str:
        return self._message

    @Property(str, notify=state_changed)
    def previewText(self) -> str:
        return self._preview_text

    @Property(str, notify=state_changed)
    def previewHtml(self) -> str:
        return self._preview_html

    @Property(str, notify=state_changed)
    def previewRecipients(self) -> str:
        return self._preview_recipients

    @Slot(int, bool)
    def load_for_user(self, _user_id: int, is_admin: bool) -> None:
        self._is_admin = is_admin
        self._message = ""
        self.state_changed.emit()

    @Slot()
    def clear(self) -> None:
        self._is_admin = False
        self._message = ""
        self._preview_text = ""
        self._preview_html = ""
        self._preview_recipients = ""
        self._prepared_message = None
        self.state_changed.emit()

    @Slot()
    def clearCredentials(self) -> None:
        """Remove Gmail configuration as part of a complete factory reset."""
        if self._sender_email:
            try:
                keyring.delete_password(self._credential_service, self._sender_email)
            except (keyring.errors.KeyringError, keyring.errors.PasswordDeleteError):
                pass
        self._settings.remove("report/sender_email")
        self._sender_email = ""
        self.clear()

    @Slot(result=bool)
    def preparePreview(self) -> bool:
        """Build and retain the exact snapshot that will be sent after confirmation."""
        if not self._is_admin:
            return self._set_error("Administrator access is required.")
        recipients = self._recipients()
        if not recipients:
            return self._set_error("No family email addresses are available.")
        self._prepared_message = self._current_message(recipients)
        plain_part = self._prepared_message.get_body(preferencelist=("plain",))
        html_part = self._prepared_message.get_body(preferencelist=("html",))
        self._preview_text = plain_part.get_content() if plain_part else ""
        self._preview_html = html_part.get_content() if html_part else ""
        self._preview_recipients = ", ".join(recipients)
        self._message = ""
        self.state_changed.emit()
        return True

    @Slot(str, str, result=bool)
    def saveSettings(self, sender_email: str, app_password: str) -> bool:
        """Save a Gmail address and its dedicated App Password."""
        if not self._is_admin:
            return self._set_error("Administrator access is required.")
        sender_email = sender_email.strip()
        app_password = app_password.replace(" ", "").strip()
        if not EMAIL_PATTERN.fullmatch(sender_email):
            return self._set_error("Enter a valid Gmail address.")
        if not sender_email.lower().endswith("@gmail.com"):
            return self._set_error("The automatic sender must be a Gmail address.")
        if not app_password:
            return self._set_error("Enter the Google App Password.")

        old_sender = self._sender_email
        try:
            keyring.set_password(self._credential_service, sender_email, app_password)
            if old_sender and old_sender.lower() != sender_email.lower():
                keyring.delete_password(self._credential_service, old_sender)
        except keyring.errors.KeyringError as error:
            return self._set_error(f"Windows could not save the credential: {error}")

        self._sender_email = sender_email
        self._settings.setValue("report/sender_email", sender_email)
        self._message = "Email sending is configured."
        self.state_changed.emit()
        return True

    @Slot(result=bool)
    def sendBreakdown(self) -> bool:
        """Send the current dashboard snapshot without blocking the interface."""
        if not self._is_admin:
            return self._set_error("Administrator access is required.")
        if self._sending:
            return False
        try:
            password = keyring.get_password(
                self._credential_service, self._sender_email
            )
        except keyring.errors.KeyringError as error:
            return self._set_error(f"Windows could not read the credential: {error}")
        if not self._sender_email or not password:
            return self._set_error("Configure Gmail before sending a breakdown.")

        message = self._prepared_message
        if message is None:
            recipients = self._recipients()
            if not recipients:
                return self._set_error("No family email addresses are available.")
            message = self._current_message(recipients)
        self._prepared_message = None
        self._sending = True
        self._message = "Sending family breakdown…"
        self.state_changed.emit()
        Thread(
            target=self._send_worker,
            args=(self._sender_email, password, message),
            daemon=True,
        ).start()
        return True

    def _recipients(self) -> list[str]:
        return sorted(
            {
                user["username"].strip()
                for user in self._user_store.list_users()
                if EMAIL_PATTERN.fullmatch(user["username"].strip())
            },
            key=str.lower,
        )

    def _current_message(self, recipients: list[str]) -> EmailMessage:
        return self._build_message(
            self._sender_email,
            recipients,
            self._account_store.list_accounts(),
            self._budget_controller.report_snapshot()
            if self._budget_controller else None,
        )

    def _send_worker(self, sender: str, password: str, message: EmailMessage) -> None:
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
                smtp.login(sender, password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as error:
            self._send_completed.emit(False, f"Email could not be sent: {error}")
        else:
            self._send_completed.emit(True, "Family breakdown sent successfully.")

    @Slot(bool, str)
    def _finish_send(self, _success: bool, message: str) -> None:
        self._sending = False
        self._message = message
        self.state_changed.emit()

    def _set_error(self, message: str) -> bool:
        self._message = message
        self.state_changed.emit()
        return False

    @staticmethod
    def _build_message(
        sender: str,
        recipients: list[str],
        accounts: list[dict],
        budget: dict | None = None,
    ) -> EmailMessage:
        assets = sum(
            account["balance_cents"]
            for account in accounts
            if account["account_type"].casefold() != "debt"
        )
        debt = sum(
            account["balance_cents"]
            for account in accounts
            if account["account_type"].casefold() == "debt"
        )
        net_worth = assets - debt

        def money(cents: int) -> str:
            return f"${cents / 100:,.2f}"

        plain_accounts = "\n".join(
            f"- {account['name']} ({account['owner']}, {account['account_type']}): "
            f"{money(account['balance_cents'])}"
            for account in accounts
        ) or "- No accounts are currently tracked."

        plain_budget = ""
        if budget is not None:
            plain_items = "\n".join(
                f"- {item['name']} ({item['item_type']}): "
                f"planned {money(item['planned_cents'])}, "
                f"actual {money(item['actual_cents'])}"
                + (f" — {item['notes']}" if item.get("notes") else "")
                for item in budget["items"]
            ) or "- No spending or saving categories are planned for this month."
            plain_budget = (
                f"\n\nMonthly spending & saving — {budget['month']}\n"
                f"Monthly net income: {money(budget['monthly_net_cents'])}\n"
                f"Planned spending: {money(budget['planned_spending_cents'])}\n"
                f"Planned saving: {money(budget['planned_saving_cents'])}\n"
                f"Planned remaining: {money(budget['planned_remaining_cents'])}\n"
                f"Actual spending: {money(budget['actual_spending_cents'])}\n"
                f"Actual saving: {money(budget['actual_saving_cents'])}\n"
                f"Actual remaining: {money(budget['actual_remaining_cents'])}\n\n"
                f"Categories\n{plain_items}"
            )

        email = EmailMessage()
        email["Subject"] = "Telemetry family financial breakdown"
        email["From"] = sender
        email["To"] = ", ".join(recipients)
        email.set_content(
            "TELEMETRY\n"
            "Family financial breakdown\n"
            "========================================\n\n"
            "SUMMARY\n"
            "----------------------------------------\n"
            f"Net worth: {money(net_worth)}\n"
            f"Total assets: {money(assets)}\n"
            f"Total debt: {money(debt)}\n\n"
            "ACCOUNTS\n"
            "----------------------------------------\n"
            f"{plain_accounts}{plain_budget}\n\n"
            "----------------------------------------\n"
            "This snapshot was sent from the Telemetry family dashboard."
        )
        email.add_alternative(
            ReportController._build_html_report(
                accounts, budget, assets, debt, net_worth, money
            ),
            subtype="html",
        )
        return email

    @staticmethod
    def _build_html_report(
        accounts: list[dict],
        budget: dict | None,
        assets: int,
        debt: int,
        net_worth: int,
        money: Callable[[int], str],
    ) -> str:
        """Render an email-client-friendly report using inline table styles."""
        cell = "padding:10px 12px;border-bottom:1px solid #17466a;color:#e8f7ff;"
        account_rows = "".join(
            "<tr>"
            f"<td style='{cell}'><strong>{html.escape(item['name'])}</strong></td>"
            f"<td style='{cell}'>{html.escape(item['owner'])}</td>"
            f"<td style='{cell}'>{html.escape(item['account_type'])}</td>"
            f"<td style='{cell}text-align:right;white-space:nowrap'>"
            f"{money(item['balance_cents'])}</td></tr>"
            for item in accounts
        ) or (
            f"<tr><td colspan='4' style='{cell}color:#91adbf'>"
            "No accounts are currently tracked.</td></tr>"
        )

        budget_section = ""
        if budget is not None:
            budget_rows = "".join(
                "<tr>"
                f"<td style='{cell}'><strong>{html.escape(item['name'])}</strong></td>"
                f"<td style='{cell}'>{html.escape(item['item_type'])}</td>"
                f"<td style='{cell}text-align:right'>{money(item['planned_cents'])}</td>"
                f"<td style='{cell}text-align:right'>{money(item['actual_cents'])}</td>"
                f"<td style='{cell}'>{html.escape(item.get('notes', ''))}</td></tr>"
                for item in budget["items"]
            ) or (
                f"<tr><td colspan='5' style='{cell}color:#91adbf'>"
                "No categories are planned for this month.</td></tr>"
            )
            budget_section = (
                "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
                "bgcolor='#0a1d33'><tr><td style='padding:0 24px 24px'>"
                f"<h2 style='margin:24px 0 12px;color:#55dff4;font-size:20px'>"
                f"Monthly spending &amp; saving — {html.escape(budget['month'])}</h2>"
                "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
                "style='margin-bottom:16px;background:#102943;border-radius:8px'><tr>"
                f"<td style='padding:14px'><span style='color:#91adbf'>Monthly net</span><br>"
                f"<strong>{money(budget['monthly_net_cents'])}</strong></td>"
                f"<td style='padding:14px'><span style='color:#91adbf'>Planned remaining</span><br>"
                f"<strong>{money(budget['planned_remaining_cents'])}</strong></td>"
                f"<td style='padding:14px'><span style='color:#91adbf'>Actual remaining</span><br>"
                f"<strong>{money(budget['actual_remaining_cents'])}</strong></td>"
                "</tr></table>"
                "<table width='100%' cellpadding='0' cellspacing='0' "
                "style='margin-bottom:18px;border:1px solid #17466a'>"
                "<tr style='background:#102943;color:#55dff4'><th style='padding:10px;text-align:left'>"
                "Budget summary</th><th style='padding:10px;text-align:right'>Planned</th>"
                "<th style='padding:10px;text-align:right'>Actual</th></tr>"
                f"<tr><td style='{cell}'><strong>Spending</strong></td>"
                f"<td style='{cell}text-align:right'>{money(budget['planned_spending_cents'])}</td>"
                f"<td style='{cell}text-align:right'>{money(budget['actual_spending_cents'])}</td></tr>"
                f"<tr><td style='{cell}'><strong>Saving</strong></td>"
                f"<td style='{cell}text-align:right'>{money(budget['planned_saving_cents'])}</td>"
                f"<td style='{cell}text-align:right'>{money(budget['actual_saving_cents'])}</td></tr>"
                "</table><h3 style='color:#55dff4'>Categories</h3>"
                "<table width='100%' cellpadding='0' cellspacing='0' "
                "style='border:1px solid #17466a'><tr style='background:#102943;color:#55dff4'>"
                "<th style='padding:10px;text-align:left'>Category</th>"
                "<th style='padding:10px;text-align:left'>Type</th>"
                "<th style='padding:10px;text-align:right'>Planned</th>"
                "<th style='padding:10px;text-align:right'>Actual</th>"
                "<th style='padding:10px;text-align:left'>Notes</th></tr>"
                f"{budget_rows}</table></td></tr></table>"
            )

        return (
            "<!doctype html><html><body bgcolor='#061326' style='margin:0;padding:0;"
            "font-family:Segoe UI,Arial,sans-serif;color:#e8f7ff'>"
            "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
            "bgcolor='#061326'><tr><td align='center' style='padding:20px'>"
            "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
            "bgcolor='#0a1d33' style='max-width:760px;border:1px solid #17466a'>"
            "<tr><td bgcolor='#08192c' style='padding:24px;color:#e8f7ff;"
            "border-bottom:1px solid #17466a'>"
            "<div style='font-size:12px;color:#91adbf'>TELEMETRY</div>"
            "<h1 style='margin:5px 0 0;font-size:25px'>Family financial breakdown</h1>"
            "</td></tr><tr><td style='padding:24px'>"
            "<table role='presentation' width='100%' cellpadding='0' cellspacing='0' "
            "style='background:#102943;border-radius:8px'><tr>"
            f"<td style='padding:16px'><span style='color:#91adbf'>Net worth</span><br>"
            f"<strong style='font-size:22px'>{money(net_worth)}</strong></td>"
            f"<td style='padding:16px'><span style='color:#91adbf'>Assets</span><br>"
            f"<strong style='color:#55e879'>{money(assets)}</strong></td>"
            f"<td style='padding:16px'><span style='color:#91adbf'>Debt</span><br>"
            f"<strong style='color:#ff647c'>{money(debt)}</strong></td></tr></table>"
            "<h2 style='margin:24px 0 12px;color:#55dff4;font-size:20px'>Accounts</h2>"
            "<table width='100%' cellpadding='0' cellspacing='0' "
            "style='border:1px solid #17466a'><tr style='background:#102943;color:#55dff4'>"
            "<th style='padding:10px;text-align:left'>Account</th>"
            "<th style='padding:10px;text-align:left'>Owner</th>"
            "<th style='padding:10px;text-align:left'>Type</th>"
            "<th style='padding:10px;text-align:right'>Balance</th></tr>"
            f"{account_rows}</table></td></tr><tr><td>{budget_section}</td></tr>"
            "<tr><td bgcolor='#08192c' style='padding:18px 24px;color:#91adbf;"
            "font-size:12px;border-top:1px solid #17466a'>"
            "Snapshot sent from the Telemetry family dashboard.</td></tr>"
            "</table></td></tr></table></body></html>"
        )
