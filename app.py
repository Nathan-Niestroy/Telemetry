"""Configure and launch the Telemetry desktop application."""

import os
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QTimer, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from telemetry.controllers.account_controller import AccountController
from telemetry.controllers.auth_controller import AuthController
from telemetry.controllers.budget_controller import BudgetController
from telemetry.controllers.backup_controller import BackupController
from telemetry.controllers.report_controller import ReportController
from telemetry.controllers.user_controller import UserController
from telemetry.data.account import AccountStore
from telemetry.data.backup import BackupService
from telemetry.data.auth import UserStore
from telemetry.data.budget import BudgetStore
from telemetry.data.holding import HoldingStore
from telemetry.data.schema import finalize_schema
from telemetry.platform.windows_theme import apply_telemetry_title_bar
from telemetry.platform.data_protection import protect_with_windows_efs


QQuickStyle.setStyle("Universal")

project_path = Path(__file__).resolve().parent
default_data_path = (
    Path(os.environ.get("LOCALAPPDATA", project_path)) / "Telemetry"
    if getattr(sys, "frozen", False)
    else project_path / "instance"
)
data_path = Path(os.environ.get("TELEMETRY_DATA_DIR", default_data_path))
icon_path = project_path / "assets" / "Telemetry_Icon.png"
qml_path = project_path / "qml" / "Main.qml"

database_path = data_path / "telemetry.db"
user_store = UserStore(database_path)
auth_controller = AuthController(user_store)
account_store = AccountStore(database_path)
holding_store = HoldingStore(database_path)
account_controller = AccountController(account_store, holding_store)
user_controller = UserController(user_store)
budget_store = BudgetStore(database_path)
finalize_schema(database_path)
protect_with_windows_efs(database_path)
budget_controller = BudgetController(budget_store)
report_controller = ReportController(user_store, account_store, budget_controller)
backup_controller = BackupController(
    BackupService(database_path)
)
auth_controller.user_authenticated.connect(account_controller.load_for_user)
auth_controller.user_logged_out.connect(account_controller.clear)
auth_controller.user_authenticated.connect(user_controller.load_for_user)
auth_controller.user_logged_out.connect(user_controller.clear)
auth_controller.user_authenticated.connect(report_controller.load_for_user)
auth_controller.user_logged_out.connect(report_controller.clear)
auth_controller.user_authenticated.connect(budget_controller.load_for_user)
auth_controller.user_logged_out.connect(budget_controller.clear)
auth_controller.user_authenticated.connect(backup_controller.load_for_user)
auth_controller.user_logged_out.connect(backup_controller.clear)
user_controller.factory_reset_completed.connect(
    auth_controller.reset_after_factory_reset
)
user_controller.current_user_email_changed.connect(
    auth_controller.update_current_email
)
user_controller.factory_reset_completed.connect(budget_store.factory_reset)
user_controller.factory_reset_completed.connect(report_controller.clearCredentials)

# Give Telemetry its own Windows taskbar identity instead of grouping it under Python.
if sys.platform == "win32":
    from ctypes import windll

    windll.shell32.SetCurrentProcessExplicitAppUserModelID("Telemetry.FamilyFinance")

app = QApplication(sys.argv)
app_icon = QIcon(str(icon_path))
app.setWindowIcon(app_icon)

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("authController", auth_controller)
engine.rootContext().setContextProperty("accountController", account_controller)
engine.rootContext().setContextProperty("userController", user_controller)
engine.rootContext().setContextProperty("reportController", report_controller)
engine.rootContext().setContextProperty("budgetController", budget_controller)
engine.rootContext().setContextProperty("backupController", backup_controller)
backup_controller.restore_completed.connect(app.quit)
engine.rootContext().setContextProperty(
    "telemetryIconUrl", QUrl.fromLocalFile(str(icon_path))
)
engine.load(QUrl.fromLocalFile(str(qml_path)))

if not engine.rootObjects():
    sys.exit(-1)

main_window = engine.rootObjects()[0]
main_window.setIcon(app_icon)
apply_telemetry_title_bar(main_window)

if os.environ.get("TELEMETRY_SMOKE_TEST") == "1":
    QTimer.singleShot(250, app.quit)

# Tear down QML before Python releases any context-property controller. Without
# this explicit order, bindings can briefly observe null controllers while the
# interpreter is shutting down and print misleading TypeError messages.
exit_code = app.exec()
for root_object in engine.rootObjects():
    root_object.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
engine.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
sys.exit(exit_code)
