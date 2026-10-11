"""Windows RegisterHotKey, delivered by Qt's native event loop; no keyboard hook."""

import ctypes
import sys
from dataclasses import dataclass

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

MODIFIERS = {"ctrl": 0x0002, "alt": 0x0001, "shift": 0x0004, "win": 0x0008}
KEYS = {"space": 0x20, "insert": 0x2D, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22}
KEYS.update({f"f{number}": 0x6F + number for number in range(1, 12)})


@dataclass(frozen=True)
class Hotkey:
    modifiers: int
    key: int
    display: str


def parse_hotkey(value: str) -> Hotkey:
    pieces = [piece.strip().lower() for piece in value.split("+")]
    if len(pieces) < 2 or not all(pieces) or len(set(pieces)) != len(pieces):
        raise ValueError("Use a shortcut such as Ctrl+Shift+V")
    if any(piece not in MODIFIERS for piece in pieces[:-1]):
        raise ValueError("Supported modifiers: Ctrl, Alt, Shift, Win")
    # A Shift-only binding would steal normal typing. Require Ctrl/Alt/Win.
    if not any(piece in {"ctrl", "alt", "win"} for piece in pieces[:-1]):
        raise ValueError("Include Ctrl, Alt or Win to avoid intercepting normal typing")
    key_name = pieces[-1]
    if len(key_name) == 1 and key_name.isascii() and key_name.isalnum():
        key = ord(key_name.upper())
        label = key_name.upper()
    elif key_name in KEYS:
        key = KEYS[key_name]
        label = {"pageup": "PageUp", "pagedown": "PageDown"}.get(key_name, key_name.title())
    else:
        raise ValueError("Use A–Z, 0–9, F1–F11, Space, Insert, Home, End, PageUp or PageDown")
    mods = sum(MODIFIERS[piece] for piece in pieces[:-1])
    labels = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "win": "Win"}
    display = "+".join([labels[name] for name in MODIFIERS if name in pieces[:-1]] + [label])
    return Hotkey(mods, key, display)


class HotkeyError(Exception):
    pass


class Win32HotkeyAPI:
    def __init__(self):
        from ctypes import wintypes

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.user32.RegisterHotKey.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.RegisterHotKey.restype = wintypes.BOOL
        self.user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.UnregisterHotKey.restype = wintypes.BOOL

    def register(self, identifier: int, hotkey: Hotkey) -> bool:
        return bool(
            self.user32.RegisterHotKey(None, identifier, hotkey.modifiers | 0x4000, hotkey.key)
        )

    def unregister(self, identifier: int) -> None:
        self.user32.UnregisterHotKey(None, identifier)


class NativeHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def nativeEventFilter(self, event_type, message):
        if sys.platform == "win32" and event_type in (
            b"windows_generic_MSG",
            b"windows_dispatcher_MSG",
        ):
            from ctypes import wintypes

            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0312 and msg.wParam == self.manager.identifier:
                self.manager.activated.emit()
                return True, 0
        return False, 0


class HotkeyManager(QObject):
    activated = Signal()

    def __init__(self, application, *, api=None, enabled=True):
        super().__init__()
        self.application = application
        self.api = (
            api
            if api is not None
            else (Win32HotkeyAPI() if enabled and sys.platform == "win32" else None)
        )
        if not enabled:
            self.api = None
        self.identifier: int | None = None
        self.binding: Hotkey | None = None
        self._next_id = 0x4C00
        self.filter = NativeHotkeyFilter(self)
        if self.api is not None:
            self.application.installNativeEventFilter(self.filter)

    @property
    def available(self) -> bool:
        return self.api is not None

    def register(self, value: str) -> Hotkey:
        binding = parse_hotkey(value)
        if self.binding == binding and self.identifier is not None:
            return binding
        if not self.available:
            self.binding = binding
            return binding
        # Register a replacement before releasing the old binding. Conflicts leave it intact.
        identifier = self._next_id
        self._next_id = 0x4C00 if identifier >= 0x4FFF else identifier + 1
        if not self.api.register(identifier, binding):
            raise HotkeyError("Shortcut could not be registered; it may be in use by another app")
        old_id = self.identifier
        self.identifier, self.binding = identifier, binding
        if old_id is not None:
            self.api.unregister(old_id)
        return binding

    def close(self) -> None:
        if self.api is not None:
            if self.identifier is not None:
                self.api.unregister(self.identifier)
            self.application.removeNativeEventFilter(self.filter)
        self.identifier = None
