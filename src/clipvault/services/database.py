"""Serialized database work in a QThread; all UI callbacks are queued signals."""

import hashlib
import json
import sqlite3
from pathlib import Path

from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QObject,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QImage

from clipvault.core.classifier import format_json
from clipvault.core.privacy import validate_capture
from clipvault.core.text_cleanup import clean_text
from clipvault.database.repository import Repository
from clipvault.services.cleanup import cleanup_history
from clipvault.services.markdown import markdown_plain_text
from clipvault.services.preview import render_preview
from clipvault.utils.settings import Settings


class DatabaseWorker(QObject):
    result = Signal(int, str, object)
    error = Signal(int, str, str)
    closed = Signal()

    def __init__(self, path: Path, settings: Settings):
        super().__init__()
        self.path = path
        self.settings = settings
        self.repository: Repository | None = None
        self.stopped = False

    def _open(self) -> Repository:
        if self.repository is None:
            self.repository = Repository(self.path)
        return self.repository

    @Slot(int, str, object)
    def execute(self, job_id: int, name: str, payload, attempt: int = 0):
        if self.stopped:
            return
        try:
            if name == "configure":
                self.settings = payload
                value = None
            else:
                repo = self._open()
                if name == "initialize":
                    cleanup_history(repo, self.settings)
                    repo.cleanup_browser_drafts(self.settings.retention_days)
                    value = {"fts": repo.fts_available}
                elif name == "capture":
                    text, timestamp = payload
                    decision = validate_capture(
                        text,
                        paused=self.settings.paused,
                        filter_sensitive=self.settings.sensitive_filter,
                    )
                    # Enforce original length/pause/privacy limits before allocating cleaned text.
                    # Invalid controls may be repaired; surrogates still fail the second check.
                    if self.settings.clean_copied_text and (
                        decision.allowed or decision.reason == "invalid_text"
                    ):
                        text = clean_text(text)
                        decision = validate_capture(
                            text,
                            paused=self.settings.paused,
                            filter_sensitive=self.settings.sensitive_filter,
                        )
                    if decision.allowed:
                        clip = repo.upsert(text, timestamp)
                        repo.record_stat(text)
                        cleanup_history(repo, self.settings)
                        value = {"clip_id": clip.id, "reason": ""}
                    else:
                        value = {"clip_id": None, "reason": decision.reason}
                elif name == "manual_save":
                    text, favorite = payload
                    if (
                        type(favorite) is not bool
                        or not validate_capture(text, filter_sensitive=False).allowed
                    ):
                        raise ValueError("Invalid manually created text")
                    clip = repo.upsert(text, favorite=favorite)
                    cleanup_history(repo, self.settings)
                    value = {"clip_id": clip.id, "favorite": clip.is_favorite}
                elif name == "capture_rich":
                    rich, timestamp = payload
                    if (
                        self.settings.paused
                        or (rich.kind == "image" and not self.settings.capture_images)
                        or (rich.kind == "files" and not self.settings.capture_files)
                    ):
                        value = {"clip_id": None, "reason": "paused"}
                    else:
                        png = None
                        thumbnail = b""
                        if rich.kind == "image":
                            if (
                                rich.image is None
                                or rich.image.isNull()
                                or rich.image.width() * rich.image.height() > 16_000_000
                                or max(rich.image.width(), rich.image.height()) > 8192
                            ):
                                raise ValueError("Image dimensions exceed limit")
                            data = QByteArray()
                            buffer = QBuffer(data)
                            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                            if not rich.image.save(buffer, "PNG"):
                                raise ValueError("Image encoding failed")
                            png = bytes(data)
                            buffer.close()
                            if len(png) > 8 * 1024 * 1024:
                                value = {"clip_id": None, "reason": "image_too_large"}
                                self.result.emit(job_id, name, value)
                                return
                            content = f"{rich.image.width()} × {rich.image.height()} · PNG"
                            digest = hashlib.sha256(b"image\0" + png).hexdigest()
                            thumb = rich.image.scaled(
                                96,
                                96,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                            small = QByteArray()
                            buf = QBuffer(small)
                            buf.open(QIODevice.OpenModeFlag.WriteOnly)
                            thumb.save(buf, "PNG")
                            buf.close()
                            thumbnail = bytes(small)
                        else:
                            if not rich.files or len(rich.files) > 100:
                                raise ValueError("Invalid file list")
                            content = "\n".join(rich.files)
                            if not validate_capture(
                                content, filter_sensitive=self.settings.sensitive_filter
                            ).allowed:
                                value = {"clip_id": None, "reason": "sensitive"}
                                self.result.emit(job_id, name, value)
                                return
                            digest = hashlib.sha256(
                                b"files\0" + json.dumps(rich.files).encode()
                            ).hexdigest()
                        clip = repo.upsert_rich(
                            rich.kind, content, digest, png, timestamp, thumbnail
                        )
                        repo.record_stat(kind=rich.kind)
                        cleanup_history(repo, self.settings)
                        value = {"clip_id": clip.id, "reason": ""}
                elif name == "search":
                    value = repo.search(payload)
                elif name == "browser_draft_save":
                    repo.save_browser_draft(payload, retention_days=self.settings.retention_days)
                    value = None
                elif name == "browser_draft_list":
                    value = repo.browser_drafts(payload or "")
                elif name == "browser_draft_get":
                    value = repo.browser_draft(payload)
                elif name == "browser_draft_delete":
                    value = repo.delete_browser_draft(payload)
                elif name == "browser_draft_clear":
                    value = repo.clear_browser_drafts()
                elif name in {"get", "preview"}:
                    clip = repo.get(payload)
                    if name == "get":
                        value = clip
                    else:
                        value = (
                            (
                                clip,
                                render_preview(
                                    clip.content,
                                    clip.content_type,
                                    self.settings.theme,
                                    self.settings.font_size,
                                ),
                                QImage.fromData(repo.image_data(clip.id) or b"", "PNG")
                                if clip.content_type == "image"
                                else None,
                            )
                            if clip
                            else (None, "", None)
                        )
                elif name == "flag":
                    value = repo.set_flag(*payload)
                elif name == "delete":
                    value = repo.delete(payload)
                elif name == "touch":
                    value = repo.touch(payload)
                    repo.record_stat(reuse=True)
                elif name == "touch_many":
                    for clip_id, timestamp in payload:
                        if repo.get(clip_id) is not None:
                            repo.touch(clip_id, timestamp)
                    value = None
                elif name == "record_reuse":
                    for _ in range(payload):
                        repo.record_stat(reuse=True)
                    value = None
                elif name == "get_batch":
                    if not payload or len(payload) > 100 or len(set(payload)) != len(payload):
                        raise ValueError("Invalid batch")
                    value = []
                    total_bytes = 0
                    for clip_id in payload:
                        clip = repo.get(clip_id)
                        if clip is None:
                            raise ValueError("A selected clip no longer exists")
                        png = repo.image_data(clip_id) if clip.content_type == "image" else None
                        if clip.content_type == "image" and not png:
                            raise ValueError("A selected image is unavailable")
                        total_bytes += len(png or b"")
                        if total_bytes > 40 * 1024 * 1024:
                            raise ValueError("Selected images exceed the batch limit")
                        value.append((clip, png))
                elif name == "cleanup":
                    value = cleanup_history(repo, self.settings)
                    repo.cleanup_browser_drafts(self.settings.retention_days)
                elif name == "clear":
                    value = repo.clear_ordinary()
                elif name == "format":
                    clip = repo.get(payload)
                    value = (clip.id, format_json(clip.content)) if clip else None
                elif name == "markdown_plain":
                    clip = repo.get(payload)
                    value = (
                        (clip.id, markdown_plain_text(clip.content))
                        if clip and clip.content_type == "markdown"
                        else None
                    )
                elif name == "set_type":
                    value = repo.set_type(*payload)
                elif name == "mark_markdown":
                    value = repo.mark_markdown(payload)
                elif name == "get_image":
                    value = (payload, QImage.fromData(repo.image_data(payload) or b"", "PNG"))
                elif name == "stats":
                    value = repo.statistics(*payload)
                elif name == "reset_stats":
                    value = repo.reset_statistics()
                else:
                    raise ValueError("Unknown operation")
            self.result.emit(job_id, name, value)
        except sqlite3.OperationalError as error:
            if ("locked" in str(error) or "busy" in str(error)) and attempt < 2:
                QTimer.singleShot(
                    150 * (attempt + 1), lambda: self.execute(job_id, name, payload, attempt + 1)
                )
                return
            self.error.emit(job_id, name, "数据库暂时不可用。请稍后重试；本次操作尚未完成。")
        except (sqlite3.DatabaseError, OSError):
            self.error.emit(job_id, name, "无法读写本地数据库。请检查磁盘权限或数据库版本。")
        except (ValueError, TypeError, UnicodeError, RecursionError):
            self.error.emit(job_id, name, "内容或设置无法处理，本次操作已取消。")
        except Exception:
            # Never attach payloads, SQL, or clipboard text to error dialogs/logs.
            self.error.emit(job_id, name, "本次操作未完成，请重试或重启 ClipVault。")

    @Slot()
    def close(self):
        self.stopped = True
        if self.repository is not None:
            self.repository.close()
        self.closed.emit()


class DatabaseService(QObject):
    command = Signal(int, str, object)
    stop_requested = Signal()
    result = Signal(int, str, object)
    error = Signal(int, str, str)

    def __init__(self, path: Path, settings: Settings, parent=None):
        super().__init__(parent)
        self.thread = QThread(self)
        self.worker = DatabaseWorker(path, settings)
        self.worker.moveToThread(self.thread)
        self.command.connect(self.worker.execute, Qt.ConnectionType.QueuedConnection)
        self.stop_requested.connect(self.worker.close, Qt.ConnectionType.QueuedConnection)
        self.worker.result.connect(self.result)
        self.worker.error.connect(self.error)
        self.worker.closed.connect(self.thread.quit, Qt.ConnectionType.DirectConnection)
        self.thread.finished.connect(self.worker.deleteLater)
        self._counter = 0
        self._closed = False
        self.thread.start()

    def submit(self, name: str, payload=None) -> int:
        self._counter += 1
        if not self._closed:
            self.command.emit(self._counter, name, payload)
        return self._counter

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.stop_requested.emit()
        # Drain submitted operations before releasing the connection. No thread termination.
        self.thread.wait()
