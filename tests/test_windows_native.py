"""Opt-in tests that change the REAL Windows clipboard on an interactive desktop."""

import ctypes
import os
import subprocess
import sys

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtGui import QGuiApplication

from clipvault.app import ClipVaultApplication
from clipvault.core.hotkeys import HotkeyError, HotkeyManager, Win32HotkeyAPI, parse_hotkey

pytestmark = [
    pytest.mark.windows,
    pytest.mark.desktop,
    pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows"),
    pytest.mark.skipif(
        not os.environ.get("CLIPVAULT_DESKTOP_TESTS"),
        reason="Opt-in real Windows desktop tests are disabled",
    ),
]


@pytest.fixture
def real_desktop(qapp):
    assert QGuiApplication.platformName() == "windows", "Use QT_QPA_PLATFORM=windows"
    # Best-effort restoration of formats; clipboard content is never logged or stored on disk.
    original = QMimeData()
    current = qapp.clipboard().mimeData()
    if current is not None:
        for name in current.formats():
            original.setData(name, current.data(name))
    yield qapp
    qapp.clipboard().setMimeData(original)


def test_windows_external_process_capture(real_desktop, qtbot, tmp_path):
    c = ClipVaultApplication(real_desktop, tmp_path, no_tray=True, enable_hotkey=False)
    try:
        # Another process writes the OS clipboard. This does not use the app's backend.
        script = (
            "from PySide6.QtWidgets import QApplication; "
            "from PySide6.QtCore import QTimer; "
            "a=QApplication([]); "
            "a.clipboard().setText('ClipVault native Windows integration 中文\\nline 2'); "
            "QTimer.singleShot(350,a.quit); a.exec()"
        )
        environment = os.environ.copy()
        environment["QT_QPA_PLATFORM"] = "windows"
        process = subprocess.Popen(
            [sys.executable, "-c", script],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        qtbot.waitUntil(lambda: c.window.preview.clip is not None, timeout=6000)
        assert c.window.preview.clip.content == "ClipVault native Windows integration 中文\nline 2"
        assert process.wait(timeout=5) == 0
        with qtbot.waitSignal(c.clipboard.copied, timeout=3000):
            c._copy_id(c.window.preview.clip.id)
        assert real_desktop.clipboard().text() == c.window.preview.clip.content
    finally:
        c.shutdown()
        c.window.deleteLater()


def test_windows_real_hotkey_registration_conflict_and_release(real_desktop):
    api = Win32HotkeyAPI()
    first = HotkeyManager(real_desktop, api=api)
    second = HotkeyManager(real_desktop, api=api)
    # Distinct IDs: registration with the same HWND/id has special replacement semantics.
    second._next_id = 0x5000
    try:
        first.register("Ctrl+Alt+Shift+F11")
        with pytest.raises(HotkeyError):
            second.register("Ctrl+Alt+Shift+F11")
        first.close()
        second.register("Ctrl+Alt+Shift+F11")
    finally:
        first.close()
        second.close()


def test_windows_native_hotkey_message_delivery(real_desktop, qtbot):
    from ctypes import wintypes

    manager = HotkeyManager(real_desktop)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32.PostThreadMessageW.argtypes = [
        wintypes.DWORD,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.PostThreadMessageW.restype = wintypes.BOOL
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    try:
        binding = parse_hotkey("Ctrl+Alt+Shift+F10")
        manager.register(binding.display)
        # Checks Qt's dispatcher path; it does NOT claim to simulate physical key input.
        with qtbot.waitSignal(manager.activated, timeout=3000):
            assert user32.PostThreadMessageW(
                kernel32.GetCurrentThreadId(),
                0x0312,
                manager.identifier,
                binding.modifiers | (binding.key << 16),
            )
    finally:
        manager.close()
