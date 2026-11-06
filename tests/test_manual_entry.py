from dataclasses import replace

from PySide6.QtCore import Qt

from clipvault.database.models import MAX_TEXT_LENGTH, SearchRequest, utc_now
from clipvault.services.database import DatabaseWorker
from clipvault.utils.settings import Settings


def test_manual_entry_saves_exact_text_as_favorite_even_when_paused(app, qtbot, qapp):
    app.toggle_pause()
    app.save_settings(replace(app.settings, clean_copied_text=True))
    qapp.clipboard().setText("clipboard remains untouched")
    app.window.new_clip.click()
    dialog = app._manual_dialog
    assert dialog is not None and dialog.isVisible()
    assert not dialog.save.isEnabled()
    text = "常用内容\n  保留缩进\u200b以及空格  "
    dialog.editor.setPlainText(text)
    assert dialog.favorite.isChecked() and dialog.save.isEnabled()
    dialog.save.click()
    qtbot.waitUntil(lambda: app._manual_dialog is None)
    qtbot.waitUntil(lambda: bool(app.window.model.items) and not app.window.search_busy)
    qtbot.waitUntil(lambda: app.window.preview.clip is not None)
    clip = app.window.preview.clip
    assert clip.content == text and clip.is_favorite
    assert qapp.clipboard().text() == "clipboard remains untouched"
    app.database.submit("clear")
    qtbot.wait(180)
    assert any(item.id == clip.id for item in app.window.model.items)


def test_manual_save_and_copy_preserves_text(app, qtbot, qapp):
    app.window.new_clip.click()
    dialog = app._manual_dialog
    dialog.editor.setPlainText("第一行\n\n第二行")
    dialog.save_copy.click()
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "第一行\n\n第二行")
    qtbot.waitUntil(lambda: app._manual_dialog is None)
    qtbot.waitUntil(lambda: len(app.window.model.items) == 1)
    assert app.window.model.items[0].is_favorite


def test_manual_save_deduplicates_without_removing_favorite(qapp, tmp_path):
    worker = DatabaseWorker(tmp_path / "manual.sqlite3", Settings(paused=True))
    results = []
    worker.result.connect(lambda job, name, value: results.append(value))
    worker.execute(1, "manual_save", ("existing text", False))
    clip_id = results[-1]["clip_id"]
    assert not results[-1]["favorite"]
    worker.execute(2, "manual_save", ("existing text", True))
    assert results[-1]["clip_id"] == clip_id and results[-1]["favorite"]
    worker.execute(3, "manual_save", ("existing text", False))
    assert results[-1]["clip_id"] == clip_id and results[-1]["favorite"]
    assert worker._open().search(SearchRequest()).total == 1
    worker.close()


def test_manual_dialog_validates_and_preserves_unsaved_text_on_error(app, qtbot, monkeypatch):
    app.window.new_clip.click()
    dialog = app._manual_dialog
    dialog.editor.setPlainText(" ")
    assert not dialog.save.isEnabled()
    dialog.editor.setPlainText("a" * (MAX_TEXT_LENGTH + 1))
    assert not dialog.save.isEnabled() and dialog.error.isVisible()
    dialog.editor.setPlainText("Do not lose this text")
    original_submit = app.database.submit
    monkeypatch.setattr(
        app.database,
        "submit",
        lambda name, payload=None: (
            987654 if name == "manual_save" else original_submit(name, payload)
        ),
    )
    dialog.save.click()
    assert not dialog.save.isEnabled()
    dialog.reject()
    assert dialog.isVisible()
    app._error(987654, "manual_save", "storage failed")
    assert dialog.isVisible() and dialog.editor.toPlainText() == "Do not lose this text"
    assert dialog.save.isEnabled() and dialog.error.isVisible()
    dialog.reject()
    assert app._manual_dialog is None


def test_mini_window_can_open_manual_editor(app, qtbot):
    app.database.submit("capture", ("existing item", utc_now()))
    qtbot.waitUntil(lambda: len(app.window.model.items) == 1)
    app.show_mini()
    qtbot.waitUntil(lambda: app.mini.isVisible())
    qtbot.mouseClick(app.mini.new_clip, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: app._manual_dialog is not None and app._manual_dialog.isVisible())
    assert app.window.isVisible() and not app.mini.isVisible()
    app._manual_dialog.reject()
