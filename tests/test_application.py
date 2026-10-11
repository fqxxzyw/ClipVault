import sqlite3
from dataclasses import replace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from clipvault.app import ClipVaultApplication
from clipvault.database.models import utc_now
from clipvault.utils.settings import SettingsError


@pytest.fixture
def controller(qapp, qtbot, tmp_path):
    c = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    qtbot.addWidget(c.window)
    qtbot.waitUntil(
        lambda: not c.window.search_busy and c.window.count_label.text().startswith("0")
    )
    yield c
    c.shutdown()
    qapp.clipboard().clear()


def test_real_qt_event_to_database_list_and_internal_copy(controller, qtbot, qapp):
    c = controller
    qapp.clipboard().setText("ClipVault Qt integration 中文记录")
    qtbot.waitUntil(lambda: len(c.window.model.items) == 1)
    qtbot.waitUntil(lambda: c.window.preview.clip is not None)
    clip = c.window.preview.clip
    assert clip.content == "ClipVault Qt integration 中文记录"
    qtbot.mouseClick(c.window.preview.copy, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == clip.content)
    qtbot.wait(200)
    assert len(c.window.model.items) == 1
    qtbot.mouseClick(c.window.preview.favorite, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: c.window.preview.clip is not None and c.window.preview.clip.is_favorite)
    qtbot.mouseClick(c.window.preview.pin, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: c.window.preview.clip is not None and c.window.preview.clip.is_pinned)
    c.window.navigate("favorites")
    qtbot.waitUntil(lambda: not c.window.search_busy)
    assert len(c.window.model.items) == 1
    c.window.navigate("pinned")
    qtbot.waitUntil(lambda: not c.window.search_busy)
    assert len(c.window.model.items) == 1


def test_pause_privacy_and_duplicate_capture(controller, qtbot, qapp):
    c = controller
    qapp.clipboard().setText("unique ordinary clip")
    qtbot.waitUntil(lambda: len(c.window.model.items) == 1)
    qapp.clipboard().setText("unique ordinary clip")
    qtbot.wait(220)
    assert len(c.window.model.items) == 1
    c.toggle_pause()
    assert c.settings.paused
    qapp.clipboard().setText("copied while paused")
    qtbot.wait(220)
    assert len(c.window.model.items) == 1
    c.toggle_pause()
    qtbot.wait(220)
    assert len(c.window.model.items) == 1
    qapp.clipboard().setText("password=never_store_this")
    qtbot.waitUntil(lambda: "敏感" in c.window.notice.text())
    assert len(c.window.model.items) == 1


def test_json_action_search_delete_and_settings(controller, qtbot, qapp):
    c = controller
    qapp.clipboard().setText('{"离线":true,"value":42}')
    qtbot.waitUntil(lambda: c.window.preview.clip is not None)
    assert c.window.preview.clip.content_type == "json"
    qtbot.mouseClick(c.window.preview.special, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "\n" in qapp.clipboard().text())
    assert '"离线": true' in qapp.clipboard().text()
    c.window.search.setText("离线")
    qtbot.waitUntil(lambda: not c.window.debounce.isActive() and not c.window.search_busy)
    assert len(c.window.model.items) == 1
    c.save_settings(replace(c.settings, theme="light", hotkey="Ctrl+Alt+K", font_size=16))
    assert c.settings.theme == "light" and c.store.load().font_size == 16
    qtbot.waitUntil(lambda: c.window.preview.clip is not None)
    qtbot.mouseClick(c.window.preview.delete, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not c.window.model.items)


def test_restart_restores_flags_and_configuration(qapp, qtbot, tmp_path):
    c = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    c.database.submit("capture", ("restart persistence", utc_now()))
    qtbot.waitUntil(lambda: c.window.preview.clip is not None)
    clip_id = c.window.preview.clip.id
    c.database.submit("flag", (clip_id, "is_favorite", True))
    c.database.submit("flag", (clip_id, "is_pinned", True))
    c.save_settings(replace(c.settings, theme="light", retention_days=7))
    c.shutdown()
    c.window.deleteLater()
    restarted = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    try:
        qtbot.waitUntil(lambda: restarted.window.preview.clip is not None)
        assert restarted.window.preview.clip.is_favorite and restarted.window.preview.clip.is_pinned
        assert restarted.settings.theme == "light" and restarted.settings.retention_days == 7
    finally:
        restarted.shutdown()
        restarted.window.deleteLater()
        qapp.clipboard().clear()


def test_clear_confirmation_required(controller, qtbot, qapp, monkeypatch):
    c = controller
    qapp.clipboard().setText("will clear only with confirmation")
    qtbot.waitUntil(lambda: len(c.window.model.items) == 1)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    c.clear_history()
    qtbot.wait(140)
    assert len(c.window.model.items) == 1
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    c.clear_history()
    qtbot.waitUntil(lambda: not c.window.model.items)


def test_failed_pause_save_does_not_silently_change_state(controller, monkeypatch):
    def fail(*args):
        raise SettingsError("write failure")

    monkeypatch.setattr(controller.store, "save", fail)
    controller.toggle_pause()
    assert not controller.settings.paused and not controller.clipboard.paused


def test_async_busy_database_does_not_block_gui(controller, qtbot):
    c = controller
    other = sqlite3.connect(c.directory / "history.sqlite3")
    other.execute("BEGIN IMMEDIATE")
    c.database.submit("capture", ("queued write after contention", utc_now()))
    c.window.search.setText("queued")
    qtbot.wait(90)
    assert c.window.search.text() == "queued"
    other.rollback()
    other.close()
    qtbot.waitUntil(lambda: bool(c.window.model.items), timeout=5000)
    assert c.window.model.items[0].preview == "queued write after contention"


def test_keyboard_selection_and_enter_copy(controller, qtbot, qapp):
    c = controller
    for text in ("first", "second", "third"):
        c.database.submit("capture", (text, utc_now()))
    qtbot.waitUntil(lambda: len(c.window.model.items) == 3)
    c.window.search.setFocus()
    qtbot.keyClick(c.window.search, Qt.Key.Key_Down)
    selected = c.window.current_id()
    assert selected == c.window.model.items[1].id
    qtbot.keyClick(c.window.search, Qt.Key.Key_Return)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "second")


def test_url_action_uses_http_only(controller, qtbot, qapp, monkeypatch):
    from clipvault.app import QDesktopServices

    opened = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", lambda url: opened.append(url.toString()) or True
    )
    qapp.clipboard().setText("https://example.org/docs")
    qtbot.waitUntil(lambda: controller.window.preview.clip is not None)
    controller._open_url()
    assert opened == ["https://example.org/docs"]


def test_capture_does_not_write_clipboard_text_to_errors(controller, qtbot):
    c = controller
    errors = []
    c.database.error.connect(lambda job, name, message: errors.append(message))
    c.database.submit("capture", ("INVALID\ud800PRIVATE", utc_now()))
    qtbot.waitUntil(lambda: "无效" in c.window.notice.text())
    assert not errors
    assert not c.window.model.items
