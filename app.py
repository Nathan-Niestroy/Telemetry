"""Configure and launch the Telemetry desktop application."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from account import AccountStore
from account_controller import AccountController
from auth import UserStore
from auth_controller import AuthController
from user_controller import UserController
from windows_theme import apply_telemetry_title_bar


# Set the control style before loading any QML files.
QQuickStyle.setStyle("Universal")

# Resolve every project file from app.py instead of the terminal's current folder.
project_path = Path(__file__).resolve().parent
icon_path = project_path / "assets" / "Telemetry_Icon.png"
qml_path = project_path / "qml" / "Main.qml"

# Create the database service and the controller exposed to the interface.
user_store = UserStore(project_path / "instance" / "telemetry.db")
auth_controller = AuthController(user_store)
account_store = AccountStore(project_path / "instance" / "telemetry.db")
account_controller = AccountController(account_store)
user_controller = UserController(user_store)
auth_controller.user_authenticated.connect(account_controller.load_for_user)
auth_controller.user_logged_out.connect(account_controller.clear)
auth_controller.user_authenticated.connect(user_controller.load_for_user)
auth_controller.user_logged_out.connect(user_controller.clear)
user_controller.factory_reset_completed.connect(
    auth_controller.reset_after_factory_reset
)

# Prevent Windows from grouping Telemetry under Python's taskbar identity.
if sys.platform == "win32":
    from ctypes import windll

    windll.shell32.SetCurrentProcessExplicitAppUserModelID("Telemetry.FamilyFinance")

# Create the application and apply its icon.
app = QGuiApplication(sys.argv)
app_icon = QIcon(str(icon_path))
app.setWindowIcon(app_icon)

# Let QML call the Python controller, then load the interface from disk.
engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("authController", auth_controller)
engine.rootContext().setContextProperty("accountController", account_controller)
engine.rootContext().setContextProperty("userController", user_controller)
engine.rootContext().setContextProperty(
    "telemetryIconUrl", QUrl.fromLocalFile(str(icon_path))
)
engine.load(QUrl.fromLocalFile(str(qml_path)))

# An empty root-object list means the QML interface failed to load.
if not engine.rootObjects():
    sys.exit(-1)

main_window = engine.rootObjects()[0]
main_window.setIcon(app_icon)
apply_telemetry_title_bar(main_window)
sys.exit(app.exec())
