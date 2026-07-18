"""Expose Telemetry authentication state and actions to the QML interface."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from auth import UserStore


class AuthController(QObject):
    """Connect the QML login interface to the SQLite user store."""

    state_changed = Signal()
    user_authenticated = Signal(int, bool)
    user_logged_out = Signal()

    def __init__(self, user_store: UserStore) -> None:
        """Start logged out and determine whether registration is required."""
        super().__init__()
        self._user_store = user_store
        self._has_user = user_store.has_users()
        self._logged_in = False
        self._username = ""
        self._is_admin = False
        self._message = ""

    @Property(bool, notify=state_changed)
    def hasUser(self) -> bool:
        """Tell QML whether it should show registration or login."""
        return self._has_user

    @Property(bool, notify=state_changed)
    def loggedIn(self) -> bool:
        """Tell QML whether it should show the protected home screen."""
        return self._logged_in

    @Property(str, notify=state_changed)
    def username(self) -> str:
        """Expose the signed-in username for the welcome message."""
        return self._username

    @Property(bool, notify=state_changed)
    def isAdmin(self) -> bool:
        """Tell QML whether the current user may manage local users."""
        return self._is_admin

    @Property(str, notify=state_changed)
    def message(self) -> str:
        """Expose validation and login errors to the interface."""
        return self._message

    @Slot(str, str)
    def register(self, username: str, password: str) -> None:
        """Create the first user and sign them in when creation succeeds."""
        try:
            user_id = self._user_store.create_user(username, password)
        except ValueError as error:
            self._message = str(error)
        else:
            self._has_user = True
            self._logged_in = True
            self._username = username.strip()
            self._is_admin = True
            self._message = ""
            self.user_authenticated.emit(user_id, True)
        self.state_changed.emit()

    @Slot(str, str)
    def login(self, username: str, password: str) -> None:
        """Sign in when the supplied credentials match the database."""
        authentication = self._user_store.authenticate(username, password)
        if authentication is not None:
            user_id, is_admin = authentication
            self._logged_in = True
            self._username = username.strip()
            self._is_admin = is_admin
            self._message = ""
            self.user_authenticated.emit(user_id, is_admin)
        else:
            self._message = "Incorrect username or password."
        self.state_changed.emit()

    @Slot()
    def logout(self) -> None:
        """Clear the current in-memory login session."""
        self._logged_in = False
        self._username = ""
        self._is_admin = False
        self._message = ""
        self.state_changed.emit()
        self.user_logged_out.emit()

    @Slot()
    def reset_after_factory_reset(self) -> None:
        """Return the interface to first-launch registration after a reset."""
        self._has_user = False
        self.logout()
