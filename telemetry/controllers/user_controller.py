"""Expose administrator user-management operations to QML."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from telemetry.data.auth import UserStore


class UserController(QObject):
    """Create, list, delete, and reset users for a local installation."""

    users_changed = Signal()
    message_changed = Signal()
    factory_reset_completed = Signal()
    current_user_email_changed = Signal(str)

    def __init__(self, user_store: UserStore) -> None:
        """Start without an authenticated user or management permissions."""
        super().__init__()
        self._user_store = user_store
        self._current_user_id: int | None = None
        self._is_admin = False
        self._users: list[dict] = []
        self._message = ""

    @Property("QVariantList", notify=users_changed)
    def users(self) -> list[dict]:
        """Expose non-sensitive local user details to QML."""
        return self._users

    @Property(str, notify=message_changed)
    def message(self) -> str:
        """Expose the latest user-management error to QML."""
        return self._message

    @Slot(int, bool)
    def load_for_user(self, user_id: int, is_admin: bool) -> None:
        """Load management state for the newly authenticated user."""
        self._current_user_id = user_id
        self._is_admin = is_admin
        self._reload()

    @Slot()
    def clear(self) -> None:
        """Remove all in-memory user information after logout."""
        self._current_user_id = None
        self._is_admin = False
        self._users = []
        self._set_message("")
        self.users_changed.emit()

    @Slot(str, str, result=bool)
    def createUser(self, username: str, password: str) -> bool:
        """Allow an administrator to create a standard local user."""
        if not self._is_admin:
            self._set_message("Administrator access is required.")
            return False
        try:
            self._user_store.create_user(
                username, password, must_change_password=True
            )
        except ValueError as error:
            self._set_message(str(error))
            return False
        self._set_message("")
        self._reload()
        return True

    @Slot(int, result=bool)
    def deleteUser(self, user_id: int) -> bool:
        """Allow an administrator to delete another local user."""
        if not self._is_admin:
            self._set_message("Administrator access is required.")
            return False
        if user_id == self._current_user_id:
            self._set_message("You cannot delete the user who is currently signed in.")
            return False
        self._user_store.delete_user(user_id)
        self._set_message("")
        self._reload()
        return True

    @Slot(int, str, result=bool)
    def updateUserEmail(self, user_id: int, email: str) -> bool:
        """Allow an administrator to update any local user's login email."""
        if not self._is_admin:
            self._set_message("Administrator access is required.")
            return False
        try:
            self._user_store.update_user_email(user_id, email)
        except ValueError as error:
            self._set_message(str(error))
            return False
        normalized_email = email.strip()
        self._set_message("")
        self._reload()
        if user_id == self._current_user_id:
            self.current_user_email_changed.emit(normalized_email)
        return True

    @Slot(result=bool)
    def factoryReset(self) -> bool:
        """Allow an administrator to erase every local user and account."""
        if not self._is_admin:
            self._set_message("Administrator access is required.")
            return False
        self._user_store.factory_reset()
        self.clear()
        self.factory_reset_completed.emit()
        return True

    def _reload(self) -> None:
        """Refresh QML-safe user records and mark the current user."""
        self._users = [
            {
                **user,
                "is_admin": bool(user["is_admin"]),
                "must_change_password": bool(user["must_change_password"]),
                "is_current": user["id"] == self._current_user_id,
            }
            for user in self._user_store.list_users()
        ]
        self.users_changed.emit()

    def _set_message(self, message: str) -> None:
        """Update the QML-visible message and notify the interface."""
        self._message = message
        self.message_changed.emit()
