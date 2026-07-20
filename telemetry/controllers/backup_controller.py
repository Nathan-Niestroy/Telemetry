"""Expose encrypted backup and validated restore workflows to QML."""

from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from telemetry.data.backup import BackupService


class BackupController(QObject):
    """Let administrators select backup files without exposing filesystem logic to QML."""

    state_changed = Signal()
    restore_completed = Signal()

    def __init__(self, service: BackupService) -> None:
        super().__init__()
        self._service = service
        self._is_admin = False
        self._message = ""

    @Property(str, notify=state_changed)
    def message(self) -> str:
        return self._message

    @Slot(int, bool)
    def load_for_user(self, _user_id: int, is_admin: bool) -> None:
        self._is_admin = is_admin
        self._set_message("")

    @Slot()
    def clear(self) -> None:
        self._is_admin = False
        self._set_message("")

    @Slot(str, result=bool)
    def createBackup(self, password: str) -> bool:
        if not self._is_admin:
            return self._error("Administrator access is required.")
        filename, _ = QFileDialog.getSaveFileName(
            None, "Save encrypted Telemetry backup", "Telemetry-backup.telemetry",
            "Telemetry backup (*.telemetry)"
        )
        if not filename:
            return False
        try:
            self._service.create(Path(filename), password)
        except (OSError, ValueError) as error:
            return self._error(f"Backup could not be created: {error}")
        self._set_message("Encrypted backup created successfully.")
        return True

    @Slot(str, result=bool)
    def restoreBackup(self, password: str) -> bool:
        if not self._is_admin:
            return self._error("Administrator access is required.")
        filename, _ = QFileDialog.getOpenFileName(
            None, "Restore encrypted Telemetry backup", "",
            "Telemetry backup (*.telemetry)"
        )
        if not filename:
            return False
        try:
            self._service.restore(Path(filename), password)
        except (OSError, ValueError) as error:
            return self._error(f"Backup could not be restored: {error}")
        self._set_message("Backup restored. Telemetry will now close; reopen it to continue.")
        self.restore_completed.emit()
        return True

    def _error(self, message: str) -> bool:
        self._set_message(message)
        return False

    def _set_message(self, message: str) -> None:
        self._message = message
        self.state_changed.emit()
