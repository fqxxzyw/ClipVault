"""Serialized database work in a QThread; all UI callbacks are queued signals."""

import sqlite3
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot

from clipvault.core.classifier import format_json
from clipvault.core.privacy import validate_capture
from clipvault.database.repository import Repository
from clipvault.services.cleanup import cleanup_history
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
                    value = {"fts": repo.fts_available}
                elif name == "capture":
                    text, timestamp = payload
                    decision = validate_capture(
                        text,
                        paused=self.settings.paused,
                        filter_sensitive=self.settings.sensitive_filter,
                    )
                    if decision.allowed:
                        clip = repo.upsert(text, timestamp)
                        cleanup_history(repo, self.settings)
                        value = {"clip_id": clip.id, "reason": ""}
                    else:
                        value = {"clip_id": None, "reason": decision.reason}
                elif name == "search":
                    value = repo.search(payload)
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
                            )
                            if clip
                            else (None, "")
                        )
                elif name == "flag":
                    value = repo.set_flag(*payload)
                elif name == "delete":
                    value = repo.delete(payload)
                elif name == "touch":
                    value = repo.touch(payload)
                elif name == "cleanup":
                    value = cleanup_history(repo, self.settings)
                elif name == "clear":
                    value = repo.clear_ordinary()
                elif name == "format":
                    clip = repo.get(payload)
                    value = (clip.id, format_json(clip.content)) if clip else None
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
