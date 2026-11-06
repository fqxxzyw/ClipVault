import base64
import re
from pathlib import Path

import pytest
from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtGui import QColor, QImage

from clipvault.app import ClipVaultApplication
from clipvault.core.clipboard import ClipboardRead
from clipvault.database.models import utc_now


@pytest.fixture
def controller(qapp, qtbot, tmp_path):
    c = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    qtbot.addWidget(c.window)
    qtbot.addWidget(c.mini)
    qtbot.waitUntil(lambda: not c.window.search_busy)
    yield c
    c.shutdown()
    qapp.clipboard().clear()


def add_texts(c, qtbot, *texts):
    for text in texts:
        c.database.submit("capture", (text, utc_now()))
    qtbot.waitUntil(lambda: len(c.window.model.items) == len(texts))
    qtbot.waitUntil(lambda: not c.window.search_busy and not c.refresh_timer.isActive())


def select_rows(view, rows):
    for row in rows:
        index = view.model().index(row, 0)
        view.selectionModel().select(index, QItemSelectionModel.SelectionFlag.Select)


def test_copy_keeps_order_until_window_hidden(controller, qtbot, qapp):
    c = controller
    add_texts(c, qtbot, "first item", "second item", "third item")
    initial = [item.id for item in c.window.model.items]
    c._copy_id(initial[-1])
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "first item")
    c.window.refresh()
    qtbot.waitUntil(lambda: not c.window.search_busy)
    assert [item.id for item in c.window.model.items] == initial
    c.window.hide()
    qtbot.waitUntil(lambda: not c._pending_reuse)
    qtbot.waitUntil(lambda: c.window.model.items[0].id == initial[-1])
    assert len(c.window.model.items) == 3


def test_new_capture_after_reuse_remains_newer_when_panel_closes(controller, qtbot, qapp):
    c = controller
    add_texts(c, qtbot, "older item", "recent item")
    older = c.window.model.items[-1].id
    c._copy_id(older)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "older item")
    # An external copy after the reuse must remain newer than the deferred update.
    qapp.clipboard().setText("copied later elsewhere")
    qtbot.waitUntil(lambda: len(c.window.model.items) == 3)
    c.window.hide()
    qtbot.waitUntil(lambda: not c._pending_reuse)
    qtbot.waitUntil(lambda: c.window.model.items[1].id == older)
    assert c.window.model.items[0].preview == "copied later elsewhere"
    assert c.window.model.items[1].id == older


def test_main_multi_select_grid_copies_text_in_visible_order(controller, qtbot, qapp):
    c = controller
    add_texts(c, qtbot, "first item", "second item", "third item")
    c.window.grid_mode.click()
    c.window.batch_select.click()
    assert c.window.list_view.grid_mode and c.window.list_view.batch_mode
    # One click toggles a row without requiring Ctrl, including in grid mode.
    for row in (2, 0):
        index = c.window.model.index(row, 0)
        qtbot.mouseClick(
            c.window.list_view.viewport(),
            Qt.MouseButton.LeftButton,
            pos=c.window.list_view.visualRect(index).center(),
        )
    assert c.window.list_view.selected_ids() == [
        c.window.model.items[0].id,
        c.window.model.items[2].id,
    ]
    # Refresh and filter-related reloads do not discard checked items.
    c.window.refresh()
    qtbot.waitUntil(lambda: not c.window.search_busy)
    assert len(c.window.list_view.selected_ids()) == 2
    c.window.batch_copy.click()
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "third item\n\nfirst item")
    qtbot.wait(100)
    assert len(c.window.model.items) == 3  # Internal batch must not be recaptured.


def test_mini_multi_select_does_not_copy_until_confirmed(controller, qtbot, qapp):
    c = controller
    add_texts(c, qtbot, "alpha item", "beta item")
    c.show_mini()
    qtbot.waitUntil(lambda: not c.window.search_busy)
    c.mini.batch_select.click()
    c.mini.grid_mode.click()
    for row in (0, 1):
        index = c.window.model.index(row, 0)
        qtbot.mouseClick(
            c.mini.list_view.viewport(),
            Qt.MouseButton.LeftButton,
            pos=c.mini.list_view.visualRect(index).center(),
        )
    assert len(c.mini.list_view.selected_ids()) == 2
    assert c.mini.isVisible()
    c.mini.batch_copy.click()
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "beta item\n\nalpha item")
    qtbot.waitUntil(lambda: not c.mini.isVisible())


def test_batch_images_and_mixed_content_keep_pixels(controller, qtbot, qapp):
    c = controller
    for color in ("#f00000", "#0000f0"):
        image = QImage(5, 3, QImage.Format.Format_ARGB32)
        image.fill(QColor(color))
        c.database.submit(
            "capture_rich", (ClipboardRead(None, kind="image", image=image), utc_now())
        )
    qtbot.waitUntil(lambda: len(c.window.model.items) == 2)
    c.window.batch_select.click()
    select_rows(c.window.list_view, (0, 1))
    c.window.batch_copy.click()
    qtbot.waitUntil(
        lambda: (
            qapp.clipboard().mimeData() is not None and len(qapp.clipboard().mimeData().urls()) == 2
        )
    )
    mime = qapp.clipboard().mimeData()
    files = [Path(url.toLocalFile()) for url in mime.urls()]
    assert all(path.is_file() for path in files)
    colors = [QImage(str(path)).pixelColor(0, 0).name() for path in files]
    assert colors == ["#0000f0", "#f00000"]
    assert all(
        QImage(str(path)).size() == QImage(5, 3, QImage.Format.Format_ARGB32).size()
        for path in files
    )
    assert len(re.findall("data:image/png;base64,", mime.html())) == 2
    assert all(
        base64.b64decode(data) == path.read_bytes()
        for data, path in zip(
            re.findall(r'data:image/png;base64,([^" ]+)', mime.html()), files, strict=True
        )
    )
    # Text and images are also represented together as rich HTML, with a plain-text fallback.
    c.database.submit("capture", ("mixed text <hello>", utc_now()))
    qtbot.waitUntil(lambda: len(c.window.model.items) == 3)
    c.window.list_view.clearSelection()
    select_rows(c.window.list_view, (0, 1, 2))
    c.window.batch_copy.click()
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "mixed text <hello>")
    mime = qapp.clipboard().mimeData()
    assert "mixed text &lt;hello&gt;" in mime.html()
    assert mime.html().count("data:image/png;base64,") == 2
    assert not mime.urls()
    qtbot.wait(100)
    assert len(c.window.model.items) == 3
