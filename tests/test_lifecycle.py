from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QSystemTrayIcon

from clipvault.app import ClipVaultApplication
from clipvault.core.clipboard import ClipboardMonitor, ClipboardRead, ClipboardUnavailable
from clipvault.utils.settings import SettingsError


class UnavailableClipboard:
    def read_text(self):
        raise ClipboardUnavailable

    def write_text(self, text):
        raise ClipboardUnavailable


def test_bounded_read_failure_reports_unavailable_and_next_event_recovers(qtbot):
    backend = UnavailableClipboard()
    monitor = ClipboardMonitor(backend)
    states, captures = [], []
    monitor.status_changed.connect(states.append)
    monitor.captured.connect(lambda text, stamp: captures.append(text))
    monitor.on_change()
    qtbot.waitUntil(lambda: "unavailable" in states, timeout=2000)
    assert not captures
    backend.read_text = lambda: ClipboardRead("recovered without restarting")
    monitor.on_change()
    assert captures == ["recovered without restarting"] and states[-1] == "listening"
    monitor.close()


def test_bounded_copy_failure_never_reports_success(qtbot):
    monitor = ClipboardMonitor(UnavailableClipboard())
    copied, skipped = [], []
    monitor.copied.connect(copied.append)
    monitor.skipped.connect(skipped.append)
    monitor.copy("test text", 1)
    qtbot.waitUntil(lambda: bool(skipped), timeout=2000)
    assert skipped == ["copy_failed"] and not copied
    monitor.close()


def test_tray_menu_pause_restore_and_quit(qapp, qtbot, tmp_path, monkeypatch):
    # Real Qt actions/widgets with platform availability mocked; not an OS tray verification.
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda: True)
    c = ClipVaultApplication(qapp, tmp_path, enable_hotkey=False)
    try:
        assert c.tray is not None and c.window.tray_available
        c.window.hide()
        c._tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        assert c.window.isVisible()
        c.tray_pause.trigger()
        assert c.settings.paused and c.clipboard.paused
        c.tray_menu.actions()[2].trigger()
        assert c.window.scope == "settings"
        c.window.close()
        assert not c.window.isVisible() and not c._stopping
        c.window.show_panel()
        assert c.window.isVisible()
    finally:
        c.shutdown()
        c.window.deleteLater()
        qapp.clipboard().clear()


def test_repeated_panel_show_hide_and_no_tray_escape(qapp, qtbot, tmp_path):
    c = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    try:
        for _ in range(25):
            c.window.show_panel(quick=True)
            assert c.window.isVisible()
            c.window.hide()
            assert not c.window.isVisible()
        c.window.show_panel()
        qtbot.keyClick(c.window, Qt.Key.Key_Escape)
        qtbot.waitUntil(lambda: c.window.isMinimized())
        c.window.show_panel()
        assert c.window.isVisible() and not c.window.isMinimized()
    finally:
        c.shutdown()
        c.window.deleteLater()


def test_settings_save_failure_keeps_previous_settings(qapp, qtbot, tmp_path, monkeypatch):
    c = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    old = c.settings

    def fail(settings):
        raise SettingsError("Simulated disk error")

    try:
        monkeypatch.setattr(c.store, "save", fail)
        c.save_settings(replace(old, theme="light", hotkey="Ctrl+Alt+J"))
        assert c.settings == old
        assert c.hotkeys.binding.display == old.hotkey
    finally:
        c.shutdown()
        c.window.deleteLater()


def test_open_data_folder_action_is_local(qapp, qtbot, tmp_path, monkeypatch):
    c = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    urls = []
    try:
        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: urls.append(url) or True)
        c.open_data_folder()
        assert len(urls) == 1 and urls[0].isLocalFile()
        assert Path(urls[0].toLocalFile()) == tmp_path
    finally:
        c.shutdown()
        c.window.deleteLater()
