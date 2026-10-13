from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QDate, QMimeData, Qt, QUrl
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QMessageBox

from clipvault.app import ClipVaultApplication
from clipvault.core.classifier import classify
from clipvault.core.emoji import emoji_count
from clipvault.database.models import SearchRequest, utc_now
from clipvault.services.markdown import MARKDOWN_FEATURES, LocalDocument, markdown_plain_text
from clipvault.ui import motion
from clipvault.ui.i18n import tr
from clipvault.utils.settings import Settings, SettingsError, SettingsStore


@pytest.fixture
def app(qapp, qtbot, tmp_path):
    controller = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    qtbot.addWidget(controller.window)
    qtbot.addWidget(controller.mini)
    qtbot.waitUntil(lambda: not controller.window.search_busy)
    yield controller
    controller.shutdown()
    qapp.clipboard().clear()


def capture(app, qtbot, text):
    app.database.submit("capture", (text, utc_now()))
    qtbot.waitUntil(
        lambda: app.window.preview.clip is not None and app.window.preview.clip.content == text
    )
    return app.window.preview.clip


@pytest.mark.parametrize(
    "text",
    [
        "# Heading\n\n**bold**",
        "```python\nprint(1)\n```",
        "- one\n- two",
        "| A | B |\n| --- | --- |\n| 1 | 2 |",
    ],
)
def test_markdown_classifier(text):
    assert classify(text) == "markdown"


@pytest.mark.parametrize("text", ["one * word", "1. just a note", "#hashtag", "a > b"])
def test_ambiguous_markdown_stays_text(text):
    assert classify(text) == "text"


def test_markdown_preview_copy_modes_and_no_recapture(app, qapp, qtbot):
    raw = "# 本地文档\n\n**重点**与[链接](https://example.org)\n\n- one\n- two"
    capture(app, qtbot, raw)
    assert "本地文档" in app.window.preview.browser.toPlainText()
    assert "# 本地文档" not in app.window.preview.browser.toPlainText()
    app.window.preview.md_view.setCurrentIndex(1)
    assert app.window.preview.browser.toPlainText() == raw
    app.window.preview.md_copy.setCurrentIndex(0)
    qtbot.mouseClick(app.window.preview.copy, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == raw)
    qtbot.wait(160)
    qtbot.waitUntil(lambda: app.window.preview.clip is not None)
    app.window.preview.md_copy.setCurrentIndex(1)
    qtbot.mouseClick(app.window.preview.copy, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: "重点与链接" in qapp.clipboard().text())
    assert "**" not in qapp.clipboard().text() and "https://" not in qapp.clipboard().text()
    qtbot.wait(180)
    assert len(app.window.model.items) == 1
    assert app.window.preview.clip.content == raw


def test_mark_text_as_markdown_persists(app, qtbot):
    capture(app, qtbot, "only **emphasis**")
    assert app.window.preview.clip.content_type == "text"
    qtbot.mouseClick(app.window.preview.special, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(
        lambda: (
            app.window.preview.clip is not None
            and app.window.preview.clip.content_type == "markdown"
        )
    )
    app.window.refresh()
    qtbot.waitUntil(lambda: not app.window.search_busy)
    assert app.window.model.items[0].content_type == "markdown"


def test_markdown_denies_all_resources(qapp, tmp_path):
    document = LocalDocument()
    secret = tmp_path / "secret.png"
    image = QImage(4, 4, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.red)
    image.save(str(secret))
    for url in (
        secret.as_uri(),
        "https://example.org/track.png",
        "data:image/png;base64,AAAA",
        "relative.png",
    ):
        assert document.loadResource(2, QUrl(url)) is None
    text = "# heading\n\n**bold** <script>alert(1)</script> ![image](file:///secret.png)"
    plain = markdown_plain_text(text)
    assert "heading" in plain and "**" not in plain and "alert(1)" in plain
    document.setMarkdown(
        text,
        MARKDOWN_FEATURES,
    )
    assert "&lt;script&gt;" in document.toHtml()


def test_language_switch_preserves_query_selection_and_source(app, qtbot):
    raw = "# Hello\n\nEnglish and 中文 stay unchanged."
    clip = capture(app, qtbot, raw)
    app.window.search.setText("中文")
    qtbot.waitUntil(lambda: not app.window.debounce.isActive() and not app.window.search_busy)
    app.save_settings(replace(app.settings, language="zh_CN"))
    qtbot.waitUntil(lambda: app.window.preview.clip is not None)
    assert app.window.heading.text() == "剪贴板"
    assert app.window.search.placeholderText() == "搜索记录…"
    assert app.window.preview.md_copy.itemText(1) == "复制纯文本"
    assert app.window.search.text() == "中文" and app.window.current_id() == clip.id
    assert app.window.preview.clip.content == raw
    assert app.store.load().language == "zh_CN"
    app.save_settings(replace(app.settings, language="en"))
    assert app.window.heading.text() == "Clipboard"
    assert app.window.settings_page.save.text() == "Save settings"
    assert app.window.search.text() == "中文" and app.window.current_id() == clip.id


@pytest.mark.parametrize(
    "field,value",
    [
        ("language", "invalid"),
        ("reduce_motion", 1),
        ("shortcut_panel", "invalid"),
        ("capture_images", "yes"),
    ],
)
def test_new_settings_validation(field, value):
    with pytest.raises(SettingsError):
        replace(Settings(), **{field: value}).validate()


def test_old_configuration_uses_new_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"theme":"light"}')
    settings = SettingsStore(path).load()
    assert settings.language == "system" and settings.capture_images
    assert settings.shortcut_panel == "full" and not settings.reduce_motion


def test_mini_single_click_enter_and_escape(app, qtbot, qapp):
    clip = capture(app, qtbot, "content-only mini window")
    app.show_mini()
    qtbot.waitUntil(lambda: not app.window.search_busy)
    assert app.mini.isVisible() and not app.window.isVisible()
    index = app.mini.list_view.model().index(0, 0)
    position = app.mini.list_view.visualRect(index).center()
    qtbot.mouseClick(app.mini.list_view.viewport(), Qt.MouseButton.LeftButton, pos=position)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == clip.content)
    qtbot.waitUntil(lambda: not app.mini.isVisible())
    app.show_mini()
    qtbot.waitUntil(lambda: not app.window.search_busy)
    assert app.mini.list_view.currentIndex().isValid()
    qtbot.keyClick(app.mini.list_view, Qt.Key.Key_Return)
    qtbot.waitUntil(lambda: not app.mini.isVisible())
    app.show_mini()
    qtbot.keyClick(app.mini, Qt.Key.Key_Escape)
    assert not app.mini.isVisible()


def test_motion_runs_finishes_and_can_be_disabled(app, qtbot, monkeypatch):
    monkeypatch.setattr(motion, "system_reduces_motion", lambda: False)
    app.window.navigate("settings")
    assert app.window.stack in app.window.motion.active
    qtbot.waitUntil(lambda: not app.window.motion.active, timeout=1000)
    app.window.navigate("all")
    assert app.window.motion.active
    app.window.motion.configure(True)
    assert not app.window.motion.active
    app.window.navigate("emoji")
    assert not app.window.motion.active and app.window.stack.currentIndex() == 3
    app.window.motion.configure(False)
    monkeypatch.setattr(motion, "system_reduces_motion", lambda: True)
    app.window.navigate("stats")
    assert not app.window.motion.active


def test_rapid_page_changes_and_resize_finish_consistently(app, qtbot, monkeypatch):
    monkeypatch.setattr(motion, "system_reduces_motion", lambda: False)
    for scope in ("settings", "all", "emoji", "stats", "pinned") * 4:
        app.window.navigate(scope)
    app.window.resize(820, 540)
    qtbot.waitUntil(lambda: not app.window.motion.active)
    assert app.window.scope == "pinned" and app.window.stack.currentIndex() == 0
    assert app.window.preview.geometry().right() <= app.window.stack.width()


def test_code_and_date_filters(repository):
    now = datetime.now(UTC)
    code = repository.upsert("def local():\n    return 1", now.isoformat())
    repository.upsert("# Markdown", (now - timedelta(days=10)).isoformat())
    repository.upsert("ordinary TXT", (now - timedelta(days=2)).isoformat())
    assert repository.search(SearchRequest(content_type="code")).items[0].id == code.id
    today = SearchRequest(
        date_from=(now - timedelta(hours=1)).isoformat(),
        date_to=(now + timedelta(hours=1)).isoformat(),
    )
    assert [item.id for item in repository.search(today).items] == [code.id]
    assert repository.search(SearchRequest(content_type="markdown")).matching == 1


def test_custom_date_filter_does_not_block_gui(app, qtbot):
    capture(app, qtbot, "today date filter")
    app.window.date_filter.setCurrentIndex(app.window.date_filter.findData(-1))
    app.window.date_from.setDate(QDate.currentDate().addDays(-1))
    app.window.date_to.setDate(QDate.currentDate())
    qtbot.waitUntil(lambda: not app.window.search_busy)
    assert len(app.window.model.items) == 1
    app.window.date_to.setDate(QDate.currentDate().addDays(-2))
    qtbot.waitUntil(lambda: not app.window.search_busy)
    assert not app.window.model.items


def test_image_capture_restore_and_asset_cleanup(app, qtbot, qapp):
    image = QImage(240, 160, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.blue)
    qapp.clipboard().setImage(image)
    qtbot.waitUntil(
        lambda: (
            app.window.preview.clip is not None and app.window.preview.clip.content_type == "image"
        )
    )
    clip_id = app.window.preview.clip.id
    assert app.window.preview.image == image
    assert app.window.model.items[0].thumbnail
    assert app.window.preview.image_view.isVisible()
    app._copy_id(clip_id)
    qtbot.waitUntil(lambda: qapp.clipboard().image() == image)
    qtbot.wait(250)
    assert len(app.window.model.items) == 1
    app.database.submit("delete", clip_id)
    qtbot.waitUntil(lambda: not app.window.model.items)
    import sqlite3

    with sqlite3.connect(app.directory / "history.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM clipboard_assets").fetchone()[0] == 0


def test_file_paths_icons_and_path_copy_without_reading_files(app, qtbot, qapp, tmp_path):
    paths = [tmp_path / "not-existing.md", tmp_path / "report.txt"]
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    qapp.clipboard().setMimeData(mime)
    qtbot.waitUntil(
        lambda: (
            app.window.preview.clip is not None and app.window.preview.clip.content_type == "files"
        )
    )
    clip = app.window.preview.clip
    assert [Path(path) for path in clip.content.splitlines()] == paths
    assert app.window.preview.files_view.count() == 2
    assert not app.window.preview.files_view.item(0).icon().isNull()
    app._copy_id(clip.id)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == clip.content)
    qtbot.wait(200)
    assert len(app.window.model.items) == 1


def test_rich_capture_respects_pause_and_image_setting(app, qtbot, qapp):
    app.toggle_pause()
    image = QImage(12, 12, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.green)
    qapp.clipboard().setImage(image)
    qtbot.wait(180)
    assert not app.window.model.items
    app.toggle_pause()
    app.save_settings(replace(app.settings, capture_images=False))
    qapp.clipboard().setImage(image)
    qtbot.wait(200)
    assert not app.window.model.items


def test_statistics_persist_and_exclude_paused_and_filtered_copies(app, qtbot, qapp, monkeypatch):
    raw = "first line 😀\nsecond line 👨‍💻 🇯🇵"
    clip = capture(app, qtbot, raw)
    app._copy_id(clip.id)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == raw)
    app.window.navigate("stats")
    qtbot.waitUntil(lambda: app.window.statistics_page.values["reuses"].text() == "1")
    values = app.window.statistics_page.values
    assert values["captures"].text() == "1" and values["characters"].text() == str(len(raw))
    assert values["lines"].text() == "2" and values["emoji"].text() == "3"
    app.toggle_pause()
    qapp.clipboard().setText("paused")
    qtbot.wait(130)
    app.toggle_pause()
    qapp.clipboard().setText("password=skip_me")
    qtbot.wait(130)
    app._query_stats()
    qtbot.wait(100)
    assert values["captures"].text() == "1"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)
    app._reset_stats()
    assert values["captures"].text() == "1"
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    app._reset_stats()
    qtbot.waitUntil(lambda: values["captures"].text() == "0")
    assert len(app.window.model.items) == 1


def test_emoji_button_copies_and_records_and_is_keyboard_accessible(app, qtbot, qapp):
    app.window.navigate("emoji")
    button, name = app.window.emoji_page.buttons[0]
    assert button.accessibleName() == tr(name)
    button.setFocus()
    qtbot.keyClick(button, Qt.Key.Key_Space)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "😀")
    app.window.navigate("all")
    qtbot.waitUntil(lambda: bool(app.window.model.items))
    assert app.window.model.items[0].preview == "😀"


def test_emoji_sequences_and_daily_statistics(repository):
    assert emoji_count("😀 👍🏽 👨‍💻 🇨🇳 1️⃣ plain") == 5
    repository.record_stat("x\ny😀", day="2026-10-01")
    repository.record_stat(reuse=True, day="2026-10-02")
    assert repository.statistics("2026-10-01", "2026-10-02")["lines"] == 2
    assert repository.statistics("2026-10-01", "2026-10-02")["reuses"] == 0
    assert repository.statistics()["reuses"] == 1


def test_v2_migration_retains_history_and_new_tables(tmp_path):
    import sqlite3

    from clipvault.database.repository import Repository

    path = tmp_path / "upgrade.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE clipboard_history (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "content TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE, "
            "content_type TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
            "is_favorite INTEGER NOT NULL DEFAULT 0, is_pinned INTEGER NOT NULL DEFAULT 0)"
        )
        stamp = utc_now()
        connection.execute(
            "INSERT INTO clipboard_history VALUES "
            "(1, 'saved before upgrade', 'hash', 'text', ?, ?, 1, 1)",
            (stamp, stamp),
        )
        connection.execute("PRAGMA user_version=2")
    repository = Repository(path)
    try:
        assert repository.get(1).is_favorite and repository.get(1).is_pinned
        assert repository.connection.execute("PRAGMA user_version").fetchone()[0] == 3
        assert repository.statistics()["captures"] == 0
    finally:
        repository.close()


def test_image_and_statistics_reopen_preserves_payload(repository):
    from clipvault.database.repository import Repository

    clip = repository.upsert_rich(
        "image", "2 × 2 · PNG", "test-image-digest", b"public-image-bytes", utc_now(), b"thumbnail"
    )
    repository.record_stat(kind="image")
    reopened = Repository(repository.path)
    try:
        assert reopened.image_data(clip.id) == b"public-image-bytes"
        assert reopened.search(SearchRequest()).items[0].thumbnail == b"thumbnail"
        assert reopened.statistics()["images"] == 1
    finally:
        reopened.close()


def test_image_dimension_limit_reports_skip_without_database_write(app, qapp, qtbot):
    image = QImage(8193, 1, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.red)
    skipped = []
    app.clipboard.skipped.connect(skipped.append)
    qapp.clipboard().setImage(image)
    qtbot.waitUntil(lambda: skipped == ["too_long"])
    assert not app.window.model.items


def test_full_shortcut_dismisses_mini_and_no_tray_escape_stays_recoverable(app, qtbot):
    app.show_mini()
    app.toggle_window()
    assert not app.mini.isVisible() and app.window.isVisible()
    app.show_mini()
    qtbot.keyClick(app.mini, Qt.Key.Key_Escape)
    qtbot.waitUntil(lambda: app.window.isMinimized())
    assert not app.mini.isVisible()
