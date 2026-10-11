from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QClipboard

from clipvault.core.clipboard import (
    ClipboardMonitor,
    ClipboardRead,
    ClipboardUnavailable,
    QtClipboardBackend,
)


class FakeClipboard:
    def __init__(self):
        self.text = None
        self.internal = False
        self.fail_reads = 0
        self.writes = []

    def read_text(self):
        if self.fail_reads:
            self.fail_reads -= 1
            raise ClipboardUnavailable
        return ClipboardRead(self.text, self.internal)

    def write_text(self, text):
        self.text = text
        self.internal = True
        self.writes.append(text)


def test_rapid_event_capture_pause_and_resume(qtbot):
    backend = FakeClipboard()
    monitor = ClipboardMonitor(backend)
    events = []
    monitor.captured.connect(lambda text, timestamp: events.append(text))
    for text in ["one", "two", "three", "three"]:
        backend.text = text
        monitor.on_change()
    assert events == ["one", "two", "three", "three"]
    monitor.set_paused(True)
    backend.text = "paused secret"
    monitor.on_change()
    assert len(events) == 4
    monitor.set_paused(False)
    assert len(events) == 4  # No backfill.
    backend.text = "resumed"
    monitor.on_change()
    assert events[-1] == "resumed"
    monitor.close()


def test_internal_copy_does_not_capture_and_external_copy_does(qtbot):
    backend = FakeClipboard()
    monitor = ClipboardMonitor(backend)
    events, copied = [], []
    monitor.captured.connect(lambda text, stamp: events.append(text))
    monitor.copied.connect(copied.append)
    monitor.copy("same content", 42)
    monitor.on_change()
    assert not events
    assert copied == [42]
    backend.internal = False
    monitor.on_change()
    assert events == ["same content"]
    monitor.close()


def test_busy_clipboard_retry_recovers(qtbot):
    backend = FakeClipboard()
    backend.text = "after retry"
    backend.fail_reads = 2
    monitor = ClipboardMonitor(backend)
    with qtbot.waitSignal(monitor.captured, timeout=1500) as blocker:
        monitor.on_change()
    assert blocker.args[0] == "after retry"
    monitor.close()


def test_newer_event_supersedes_pending_retry(qtbot):
    backend = FakeClipboard()
    monitor = ClipboardMonitor(backend)
    events = []
    monitor.captured.connect(lambda text, stamp: events.append(text))
    backend.fail_reads = 1
    backend.text = "obsolete"
    monitor.on_change()
    backend.text = "newest"
    monitor.on_change()
    qtbot.wait(90)
    assert events == ["newest"]
    monitor.close()


def test_pause_cancels_pending_clipboard_retry(qtbot):
    backend = FakeClipboard()
    backend.fail_reads = 1
    backend.text = "before pause"
    monitor = ClipboardMonitor(backend)
    events = []
    monitor.captured.connect(lambda text, stamp: events.append(text))
    monitor.on_change()
    monitor.set_paused(True)
    qtbot.wait(90)
    assert not events
    monitor.close()
    monitor.close()


def test_qt_backend_mime_and_text_events(qapp, qtbot):
    clipboard = qapp.clipboard()
    backend = QtClipboardBackend(clipboard)
    monitor = ClipboardMonitor(backend, clipboard)
    events = []
    monitor.captured.connect(lambda text, stamp: events.append(text))
    clipboard.setText("Qt text event", QClipboard.Mode.Clipboard)
    qtbot.waitUntil(lambda: "Qt text event" in events)
    backend.write_text("internal clip")
    qtbot.wait(30)
    assert "internal clip" not in events
    monitor.close()
    clipboard.clear()


def test_file_clipboard_excluded_and_web_urls_allowed(qapp):
    backend = QtClipboardBackend(qapp.clipboard())
    # Use Qt-only path on CI's offscreen platform; native coverage is opt-in on Windows.
    backend.windows_reader = None
    mime = QMimeData()
    mime.setText("/tmp/example.txt")
    mime.setUrls([QUrl.fromLocalFile("/tmp/example.txt")])
    qapp.clipboard().setMimeData(mime)
    assert backend.read_text().text is None
    mime = QMimeData()
    mime.setText("https://example.org")
    mime.setUrls([QUrl("https://example.org")])
    qapp.clipboard().setMimeData(mime)
    assert backend.read_text().text == "https://example.org"
    qapp.clipboard().clear()
