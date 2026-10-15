from dataclasses import replace

import pytest

from clipvault.core.clipboard import ClipboardMonitor
from clipvault.core.text_cleanup import clean_text
from clipvault.database.models import MAX_TEXT_LENGTH, SearchRequest, utc_now
from clipvault.services.database import DatabaseWorker
from clipvault.utils.settings import Settings, SettingsError, SettingsStore


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("import\u200b pandas\ufeff as pd\u2060", "import pandas as pd"),
        ("a\x00\x01\x08\x7f\x85b", "ab"),
        ("a\u00a0\u2002\u202fb", "a   b"),
        ('if True:\r\n\tprint("你好")  \n', 'if True:\r\n\tprint("你好")  \n'),
        ("👨‍👩‍👧‍👦 👩🏽‍💻 ❤️ می\u200cروم", "👨‍👩‍👧‍👦 👩🏽‍💻 ❤️ می\u200cروم"),
        ('```python\nprint("&nbsp; * ZWSP")\n```', '```python\nprint("&nbsp; * ZWSP")\n```'),
        ("1: x = a * b\ntext  \n", "1: x = a * b\ntext  \n"),
    ],
)
def test_conservative_cleanup(raw, expected):
    assert clean_text(raw) == expected
    assert clean_text(expected) == expected


def test_worker_cleanup_dedup_privacy_and_limits(qapp, tmp_path):
    worker = DatabaseWorker(tmp_path / "test.sqlite3", Settings(clean_copied_text=True))
    results = []
    worker.result.connect(lambda job, name, value: results.append(value))
    for i, text in enumerate(["im\u200bport os", "import os"]):
        worker.execute(i, "capture", (text, utc_now()))
    assert results[0]["clip_id"] == results[1]["clip_id"]
    repo = worker._open()
    page = repo.search(SearchRequest())
    assert page.total == 1
    assert repo.get(results[0]["clip_id"]).content == "import os"
    for text, reason in [
        ("\u200b\ufeff\x00", "blank"),
        ('pass\u200bword = "private"', "sensitive"),
        ("\ud800", "invalid_text"),
        ("\u200b" * (MAX_TEXT_LENGTH + 1), "too_long"),
    ]:
        worker.execute(5, "capture", (text, utc_now()))
        assert results[-1]["reason"] == reason
    worker.execute(6, "configure", Settings(clean_copied_text=True, paused=True))
    worker.execute(7, "capture", ("do not store", utc_now()))
    assert results[-1]["reason"] == "paused"
    worker.close()


def test_disabled_capture_is_exact(qapp, tmp_path):
    worker = DatabaseWorker(tmp_path / "test.sqlite3", Settings())
    worker.execute(1, "capture", ("keep\u200b\u00a0me", utc_now()))
    page = worker._open().search(SearchRequest())
    assert worker._open().get(page.items[0].id).content == "keep\u200b\u00a0me"
    worker.close()


def test_copy_switch_and_file_path_bypass(qapp):
    class Backend:
        def write_text(self, text):
            self.text = text

    backend = Backend()
    monitor = ClipboardMonitor(backend)
    monitor.copy("a\u200bb", 1)
    assert backend.text == "a\u200bb"
    monitor.clean_copied_text = True
    monitor.copy("a\u200bb", 1)
    assert backend.text == "ab"
    monitor.copy("C:/a\u200bb", 1, clean=False)
    assert backend.text == "C:/a\u200bb"
    monitor.close()


def test_cleanup_setting_persistence_and_validation(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    assert not store.load().clean_copied_text
    store.save(Settings(clean_copied_text=True))
    assert store.load().clean_copied_text
    with pytest.raises(SettingsError):
        replace(Settings(), clean_copied_text=1).validate()


def test_settings_checkbox_and_immediate_application(app, qtbot, monkeypatch):
    monkeypatch.setattr(app.hotkeys, "register", lambda value: None)
    page = app.window.settings_page
    page.clean_text.setChecked(True)
    page._save()
    assert app.settings.clean_copied_text
    assert app.clipboard.clean_copied_text
    qtbot.waitUntil(lambda: app.database.worker.settings.clean_copied_text)
    assert app.store.load().clean_copied_text
