"""Apply Telemetry's colors to the native Windows title bar."""

import sys


def apply_telemetry_title_bar(window) -> None:
    """Use Windows DWM attributes while doing nothing on other platforms."""
    if sys.platform != "win32":
        return

    from ctypes import byref, c_int, c_uint, c_void_p, sizeof, windll

    # DWM uses BGR COLORREF values rather than the RGB values used by QML.
    dark_mode = c_int(1)
    caption_color = c_uint(0x00261306)  # QML #061326
    text_color = c_uint(0x00FFF7E8)  # QML #e8f7ff
    border_color = c_uint(0x006A4617)  # QML #17466a
    window_handle = c_void_p(int(window.winId()))

    # Official DWMWINDOWATTRIBUTE values from the Windows SDK.
    attributes = (
        (20, dark_mode),  # DWMWA_USE_IMMERSIVE_DARK_MODE
        (34, border_color),  # DWMWA_BORDER_COLOR
        (35, caption_color),  # DWMWA_CAPTION_COLOR
        (36, text_color),  # DWMWA_TEXT_COLOR
    )
    for attribute, value in attributes:
        windll.dwmapi.DwmSetWindowAttribute(
            window_handle, attribute, byref(value), sizeof(value)
        )

