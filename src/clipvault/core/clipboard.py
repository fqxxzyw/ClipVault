"""Event-driven Qt clipboard with a bounded Windows Unicode-text reader."""

import ctypes
import sys
import uuid
from dataclasses import dataclass
from typing import Protocol

from PySide6.QtCore import QMimeData, QObject, QTimer, Signal
from PySide6.QtGui import QClipboard, QGuiApplication, QImage

from clipvault.database.models import MAX_TEXT_LENGTH, utc_now

INTERNAL_MIME = "application/x-clipvault-source"


class ClipboardUnavailable(Exception):
    pass


class ClipboardTooLong(Exception):
    pass


@dataclass(frozen=True)
class ClipboardRead:
    text: str | None
    internal: bool = False
    kind: str = "text"
    image: QImage | None = None
    files: tuple[str, ...] = ()


class ClipboardBackend(Protocol):
    def read_text(self) -> ClipboardRead: ...
    def write_text(self, text: str) -> None: ...


class WindowsTextReader:
    def __init__(self):
        from ctypes import wintypes

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        for name in ("OpenClipboard", "CloseClipboard", "IsClipboardFormatAvailable"):
            function = getattr(self.user32, name)
            function.restype = wintypes.BOOL
        self.user32.OpenClipboard.argtypes = [wintypes.HWND]
        self.user32.CloseClipboard.argtypes = []
        self.user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        self.user32.GetClipboardData.argtypes = [wintypes.UINT]
        self.user32.GetClipboardData.restype = wintypes.HANDLE
        self.kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalSize.restype = ctypes.c_size_t
        self.kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalLock.restype = ctypes.c_void_p
        self.kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalUnlock.restype = wintypes.BOOL

    def read(self) -> str | None:
        if not self.user32.OpenClipboard(None):
            raise ClipboardUnavailable
        try:
            if self.user32.IsClipboardFormatAvailable(15):  # CF_HDROP: copied files, not text
                return None
            if not self.user32.IsClipboardFormatAvailable(13):  # CF_UNICODETEXT
                return None
            handle = self.user32.GetClipboardData(13)
            if not handle:
                raise ClipboardUnavailable
            size = self.kernel32.GlobalSize(handle)
            pointer = self.kernel32.GlobalLock(handle)
            if not pointer:
                raise ClipboardUnavailable
            try:
                # Read at most two UTF-16 units per allowed character, plus NUL.
                # Global allocations can be padded, so allocation size alone is not a text limit.
                byte_limit = (MAX_TEXT_LENGTH * 2 + 1) * 2
                raw = ctypes.string_at(pointer, min(size, byte_limit))
                terminator = next(
                    (
                        index
                        for index in range(0, len(raw) - 1, 2)
                        if raw[index : index + 2] == b"\0\0"
                    ),
                    None,
                )
                if terminator is None:
                    if size >= byte_limit:
                        raise ClipboardTooLong
                    raise ClipboardUnavailable
                try:
                    text = raw[:terminator].decode("utf-16-le", errors="strict")
                except UnicodeDecodeError:
                    raise ClipboardUnavailable from None
                if len(text) > MAX_TEXT_LENGTH:
                    raise ClipboardTooLong
                return text.replace("\r\n", "\n")
            finally:
                self.kernel32.GlobalUnlock(handle)
        finally:
            self.user32.CloseClipboard()


class QtClipboardBackend:
    def __init__(self, clipboard: QClipboard):
        self.clipboard = clipboard
        self.source = uuid.uuid4().hex.encode("ascii")
        self.windows_reader = (
            WindowsTextReader()
            if sys.platform == "win32" and QGuiApplication.platformName() == "windows"
            else None
        )

    def read_text(self) -> ClipboardRead:
        # On Windows this read also detects an inaccessible/locked clipboard.
        if self.windows_reader:
            text = self.windows_reader.read()
        else:
            mime = self.clipboard.mimeData(QClipboard.Mode.Clipboard)
            is_file = mime is not None and any(url.isLocalFile() for url in mime.urls())
            text = mime.text() if mime is not None and mime.hasText() and not is_file else None
        if text is None:
            return ClipboardRead(None)
        mime = self.clipboard.mimeData(QClipboard.Mode.Clipboard)
        internal = mime is not None and bytes(mime.data(INTERNAL_MIME)) == self.source
        return ClipboardRead(text, internal)

    def write_text(self, text: str) -> None:
        mime = QMimeData()
        mime.setText(text)
        mime.setData(INTERNAL_MIME, self.source)
        self.clipboard.setMimeData(mime, QClipboard.Mode.Clipboard)
        # Verify that ownership/write succeeded. A busy Windows clipboard can reject it.
        result = self.read_text()
        if result.text != text.replace("\r\n", "\n"):
            raise ClipboardUnavailable

    def read_payload(self) -> ClipboardRead:
        # Native read checks locks even when Qt exposes stale clipboard MIME data.
        text_result = self.read_text()
        mime = self.clipboard.mimeData(QClipboard.Mode.Clipboard)
        if mime is None:
            return text_result
        if bytes(mime.data(INTERNAL_MIME)) == self.source:
            return ClipboardRead(None, True)
        paths = tuple(url.toLocalFile() for url in mime.urls() if url.isLocalFile())
        if paths:
            if len(paths) > 100 or sum(map(len, paths)) > MAX_TEXT_LENGTH:
                raise ClipboardTooLong
            return ClipboardRead(None, kind="files", files=paths)
        if mime.hasImage():
            image = self.clipboard.image(QClipboard.Mode.Clipboard)
            if not image.isNull():
                if (
                    image.width() * image.height() > 16_000_000
                    or max(image.width(), image.height()) > 8192
                ):
                    raise ClipboardTooLong
                return ClipboardRead(None, kind="image", image=image.copy())
        return text_result

    def write_image(self, image: QImage):
        mime = QMimeData()
        mime.setImageData(image)
        mime.setData(INTERNAL_MIME, self.source)
        self.clipboard.setMimeData(mime, QClipboard.Mode.Clipboard)
        if self.clipboard.image(QClipboard.Mode.Clipboard) != image:
            raise ClipboardUnavailable


class ClipboardMonitor(QObject):
    captured = Signal(str, str)
    status_changed = Signal(str)
    skipped = Signal(str)
    copied = Signal(int)
    rich_captured = Signal(object, str)

    def __init__(self, backend: ClipboardBackend, clipboard: QClipboard | None = None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.clipboard = clipboard
        self.paused = False
        self._generation = 0
        self._write_generation = 0
        self._stopped = False
        if clipboard is not None:
            clipboard.dataChanged.connect(self.on_change)

    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        self._generation += 1  # Cancel pending retry from before a pause/resume transition.
        self.status_changed.emit("paused" if paused else "listening")

    def on_change(self) -> None:
        self._generation += 1
        if not self.paused and not self._stopped:
            self._read(self._generation, 0, utc_now())

    def _read(self, generation: int, attempt: int, timestamp: str) -> None:
        if self._stopped or self.paused or generation != self._generation:
            return
        try:
            reader = getattr(self.backend, "read_payload", self.backend.read_text)
            result = reader()
        except ClipboardTooLong:
            self.skipped.emit("too_long")
            return
        except (ClipboardUnavailable, RuntimeError, OSError):
            if attempt < 5:
                self.status_changed.emit("retrying")
                QTimer.singleShot(
                    35 * 2**attempt, lambda: self._read(generation, attempt + 1, timestamp)
                )
            else:
                self.status_changed.emit("unavailable")
            return
        self.status_changed.emit("listening")
        if not result.internal:
            if result.kind in {"image", "files"}:
                self.rich_captured.emit(result, timestamp)
            elif result.text is not None:
                self.captured.emit(result.text, timestamp)

    def copy(self, text: str, clip_id: int) -> None:
        self._write_generation += 1
        self._write(text, clip_id, self._write_generation, 0)

    def copy_image(self, image: QImage, clip_id: int):
        self._write_generation += 1
        self._write(image, clip_id, self._write_generation, 0)

    def _write(self, text: str, clip_id: int, generation: int, attempt: int) -> None:
        if self._stopped or generation != self._write_generation:
            return
        try:
            if isinstance(text, QImage):
                self.backend.write_image(text)
            else:
                self.backend.write_text(text)
        except (ClipboardUnavailable, RuntimeError, OSError):
            if attempt < 5:
                QTimer.singleShot(
                    35 * 2**attempt, lambda: self._write(text, clip_id, generation, attempt + 1)
                )
            else:
                self.skipped.emit("copy_failed")
            return
        self.copied.emit(clip_id)

    def close(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._generation += 1
        self._write_generation += 1
        if self.clipboard is not None:
            self.clipboard.dataChanged.disconnect(self.on_change)
