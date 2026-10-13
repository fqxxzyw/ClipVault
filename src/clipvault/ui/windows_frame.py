"""Documented Windows 11 DWM corners, dark caption and Acrylic/Mica backdrops."""

import ctypes
import sys

from PySide6.QtGui import QGuiApplication


def frame_attributes(*, dark: bool, glass: bool, mini: bool, build: int):
    values = [(20, int(dark))]  # DWMWA_USE_IMMERSIVE_DARK_MODE
    if build >= 22000:
        values.append((33, 2))  # DWMWA_WINDOW_CORNER_PREFERENCE / DWMWCP_ROUND
    if build >= 22621:
        values.append((38, 3 if glass and mini else 2 if glass else 1))
    return values


def apply_windows_frame(widget, *, dark: bool, glass=False, mini=False) -> bool:
    if sys.platform != "win32" or QGuiApplication.platformName() != "windows":
        return False
    from ctypes import wintypes

    try:
        api = ctypes.WinDLL("dwmapi")
        setter = api.DwmSetWindowAttribute
        setter.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        setter.restype = ctypes.c_long
        hwnd = int(widget.winId())
        build = sys.getwindowsversion().build
        results = []
        for attribute, value in frame_attributes(dark=dark, glass=glass, mini=mini, build=build):
            data = ctypes.c_int(value)
            results.append(setter(hwnd, attribute, ctypes.byref(data), ctypes.sizeof(data)) == 0)
        if glass and build >= 22621:

            class Margins(ctypes.Structure):
                _fields_ = [(name, ctypes.c_int) for name in ("left", "right", "top", "bottom")]

            extend = api.DwmExtendFrameIntoClientArea
            extend.argtypes = [wintypes.HWND, ctypes.POINTER(Margins)]
            extend.restype = ctypes.c_long
            margins = Margins(-1, -1, -1, -1)
            extend(hwnd, ctypes.byref(margins))
        return all(results) and build >= 22621
    except (OSError, AttributeError):
        return False
