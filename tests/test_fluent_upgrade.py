from dataclasses import replace

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from clipvault.core.classifier import classify
from clipvault.core.languages import CODE_TYPES
from clipvault.database.models import SearchRequest, utc_now
from clipvault.services.html_preview import static_html
from clipvault.services.markdown import LocalDocument
from clipvault.services.preview import render_preview
from clipvault.ui.windows_frame import frame_attributes
from clipvault.utils.settings import Settings, SettingsError, SettingsStore


@pytest.mark.parametrize(
    "text,kind",
    [
        ("<!doctype html><html><body><h1>Local</h1></body></html>", "html"),
        ('<div style="color:red">Local</div>', "html"),
        ("body { display: flex; color: red; }", "css"),
        ("interface Clip { content: string; }", "typescript"),
        ('using System;\nConsole.WriteLine("hello");', "csharp"),
        ('public static void main(String[] args) { System.out.println("hello"); }', "java"),
        ('#include <stdio.h>\nint main() { printf("hello"); }', "c"),
        ('#include <iostream>\nint main() { std::cout << "hello"; }', "cpp"),
        ('package main\nfunc main() { fmt.Println("hello") }', "go"),
        ('fn main() { println!("hello"); }', "rust"),
        ("def greet(name)\n  puts name\nend", "ruby"),
        ('<?php echo "hello"; ?>', "php"),
        ("import SwiftUI\nstruct ContentView: View {}", "swift"),
        ('fun main() { println("hello") }', "kotlin"),
        ("import 'dart:core';\nvoid main() { print('hello'); }", "dart"),
        ("Get-ChildItem -Path .", "powershell"),
        ("name: ClipVault\noffline: true", "yaml"),
        ('[app]\nname = "ClipVault"\nenabled = true', "toml"),
        ("[app]\nname=ClipVault", "ini"),
        ('<?xml version="1.0"?><root><clip>local</clip></root>', "xml"),
    ],
)
def test_extended_code_recognition(text, kind):
    assert classify(text) == kind
    assert "<span" in render_preview(text, kind, "dark", 13)


@pytest.mark.parametrize(
    "text",
    [
        "this interface is pleasant",
        "a normal class discussion",
        "My CSS colors are nice",
        "function in mathematics",
        "a: b",
    ],
)
def test_new_recognizers_leave_ordinary_notes_alone(text):
    assert classify(text) == "text"


def test_all_supported_lexers_and_code_filter(repository):
    for kind in CODE_TYPES:
        assert "<html>" in render_preview("sample 123", kind, "light", 13)
    clip = repository.upsert("plain ambiguous content")
    repository.set_type(clip.id, "rust")
    assert repository.get(clip.id).content_type == "rust"
    assert repository.search(SearchRequest(content_type="code")).items[0].id == clip.id
    with pytest.raises(ValueError):
        repository.set_type(clip.id, "html'; DROP TABLE clipboard_history;")
    repository.upsert("plain ambiguous content")
    assert repository.get(clip.id).content_type == "rust"


def test_html_preview_strips_active_resources_and_keeps_visible_markup(qapp):
    raw = (
        '<h1>Hello</h1><p style="color:#123456">local <b>bold</b></p>'
        '<script>secret_script()</script><iframe src="https://example.org">secret_frame</iframe>'
        '<img src="file:///secret" alt="image">'
        '<a href="https://example.org" onclick="doStuff()">link</a>'
    )
    rendered = static_html(raw)
    assert "secret_script" not in rendered and "secret_frame" not in rendered
    assert "src=" not in rendered and "onclick=" not in rendered and "href=" not in rendered
    document = LocalDocument()
    document.setHtml(rendered)
    assert "Hello" in document.toPlainText() and "local bold" in document.toPlainText()
    assert "image" in document.toPlainText() and "link" in document.toPlainText()
    assert "font-weight:700" in document.toHtml().replace(" ", "")


def test_html_controls_and_manual_language(app, qtbot):
    raw = "<h1>Hello</h1><p>Offline preview</p><script>bad()</script>"
    app.database.submit("capture", (raw, utc_now()))
    qtbot.waitUntil(lambda: app.window.preview.clip is not None)
    preview = app.window.preview
    assert preview.clip.content_type == "html"
    assert "Hello" in preview.browser.toPlainText() and "bad()" not in preview.browser.toPlainText()
    preview.md_view.setCurrentIndex(1)
    assert preview.browser.toPlainText() == raw
    app.database.submit("set_type", (preview.clip.id, "xml"))
    qtbot.waitUntil(lambda: preview.clip is not None and preview.clip.content_type == "xml")
    assert preview.language.currentData() == "xml"


def _mouse(widget, kind, local, global_point, *, held=False):
    event = QMouseEvent(
        kind,
        QPointF(local),
        QPointF(global_point),
        Qt.MouseButton.LeftButton if kind != QEvent.Type.MouseMove else Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton
        if held or kind == QEvent.Type.MouseButtonPress
        else Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    from PySide6.QtWidgets import QApplication

    QApplication.sendEvent(widget, event)


def test_mini_normal_drag_does_not_copy_and_persists_geometry(app, qtbot):
    app.show_mini()
    qtbot.waitUntil(lambda: not app.window.search_busy)
    before = app.mini.pos()
    grip = app.mini.grip
    press = QPoint(15, 12)
    origin = grip.mapToGlobal(press)
    copied = []
    app.mini.copy_requested.connect(copied.append)
    _mouse(grip, QEvent.Type.MouseButtonPress, press, origin)
    _mouse(grip, QEvent.Type.MouseMove, press + QPoint(55, 35), origin + QPoint(55, 35), held=True)
    _mouse(grip, QEvent.Type.MouseButtonRelease, press, origin + QPoint(55, 35))
    assert app.mini.pos() != before and not copied
    qtbot.waitUntil(lambda: app.store.load().mini_geometry is not None)
    stored = app.store.load().mini_geometry
    app.mini.hide()
    app.show_mini()
    assert (app.mini.x(), app.mini.y(), app.mini.width(), app.mini.height()) == stored


def test_mini_edge_resize_pin_and_opacity(app, qtbot):
    app.show_mini()
    before = app.mini.size()
    point = QPoint(app.mini.width() - 3, app.mini.height() // 2)
    origin = app.mini.mapToGlobal(point)
    _mouse(app.mini, QEvent.Type.MouseButtonPress, point, origin)
    _mouse(
        app.mini, QEvent.Type.MouseMove, point + QPoint(90, 0), origin + QPoint(90, 0), held=True
    )
    _mouse(app.mini, QEvent.Type.MouseButtonRelease, point, origin + QPoint(90, 0))
    assert app.mini.width() > before.width()
    app._mini_preferences({"mini_topmost": True, "mini_opacity": 62, "mini_glass": True})
    assert app.mini.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert abs(app.mini.windowOpacity() - 0.62) < 0.01
    assert app.store.load().mini_topmost and app.store.load().mini_opacity == 62
    assert not app.mini.auto_hide
    app._mini_preferences({"mini_topmost": False, "mini_glass": False})
    assert not app.mini.windowFlags() & Qt.WindowType.WindowStaysOnTopHint
    assert not app.mini.delegate.glass


def test_mini_independent_opacity_and_restored_configuration(tmp_path):
    settings = replace(
        Settings(),
        opacity=100,
        mini_opacity=55,
        mini_topmost=True,
        mini_geometry=(-450, 60, 640, 420),
    )
    store = SettingsStore(tmp_path / "settings.json")
    store.save(settings)
    restored = store.load()
    assert restored == settings
    for values in (
        {"mini_opacity": 39},
        {"mini_geometry": (0, 0, 100, 100)},
        {"mini_topmost": "yes"},
    ):
        with pytest.raises(SettingsError):
            replace(Settings(), **values).validate()


def test_documented_dwm_attributes_guard_windows_version():
    assert frame_attributes(dark=True, glass=True, mini=True, build=19045) == [(20, 1)]
    assert (33, 2) in frame_attributes(dark=True, glass=True, mini=True, build=22000)
    assert (38, 3) in frame_attributes(dark=True, glass=True, mini=True, build=22621)
    assert (38, 2) in frame_attributes(dark=False, glass=True, mini=False, build=22621)
    assert (38, 1) in frame_attributes(dark=False, glass=False, mini=True, build=22621)


def test_page_slide_finishes_at_layout_position_and_reduced_motion_stops(app, qtbot):
    app.window.navigate("settings")
    qtbot.wait(40)
    page = app.window.stack.currentWidget()
    assert page.pos().y() >= 0
    qtbot.waitUntil(lambda: not app.window.motion.active)
    assert page.pos() == QPoint(0, 0)
    app.window.navigate("emoji")
    app.window.motion.configure(True)
    assert not app.window.motion.active and app.window.stack.currentWidget().pos() == QPoint(0, 0)


def test_pinned_mini_stays_open_after_copy(app, qtbot, qapp):
    app.database.submit("capture", ("pinned picker reuse", utc_now()))
    qtbot.waitUntil(lambda: bool(app.window.model.items))
    app._mini_preferences({"mini_topmost": True})
    app.show_mini()
    app._copy_id(app.window.model.items[0].id)
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "pinned picker reuse")
    assert app.mini.isVisible()
    app.mini.dismiss_panel()
    assert not app.mini.isVisible()


def test_auto_detect_existing_manually_labeled_clip(repository):
    clip = repository.upsert("<h1>Local</h1>")
    repository.set_type(clip.id, "text")
    assert repository.get(clip.id).content_type == "text"
    repository.set_type(clip.id, "auto")
    assert repository.get(clip.id).content_type == "html"
