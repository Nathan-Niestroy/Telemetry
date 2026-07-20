"""Best-effort operating-system protection for the live SQLite file."""

import sys
from pathlib import Path


def protect_with_windows_efs(database_path: Path) -> bool:
    """Ask Windows EFS to encrypt the database for the current user.

    Windows Home and some managed volumes do not provide EFS, so failure is
    intentionally non-fatal. Encrypted portable backups remain available.
    """
    if sys.platform != "win32" or not database_path.exists():
        return False
    try:
        from ctypes import WinDLL

        encrypt_file = WinDLL("advapi32", use_last_error=True).EncryptFileW
        encrypt_file.argtypes = [__import__("ctypes").c_wchar_p]
        encrypt_file.restype = __import__("ctypes").c_int
        return bool(encrypt_file(str(database_path)))
    except (AttributeError, OSError):
        return False
