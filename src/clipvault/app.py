import sys
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from clipvault.core.classifier import is_web_url
from clipvault.core.clipboard import ClipboardMonitor, QtClipboardBackend
from clipvault.core.hotkeys import HotkeyError, HotkeyManager, parse_hotkey
from clipvault.services.database import DatabaseService
from clipvault.ui.main_window import MainWindow
from clipvault.ui.styles import apply_theme
from clipvault.utils.paths import resource_path
from clipvault.utils.settings import Settings, SettingsError, SettingsStore
from clipvault.utils.startup import WindowsStartup


class ClipVaultApplication(QObject):
    def __init__(
        self,
        application: QApplication,
        directory: Path,
        *,
        background=False,
        no_tray=False,
        enable_hotkey=True,
    ):
        super().__init__()
        self.application = application
        self.directory = directory
        self.store = SettingsStore(directory / "settings.json")
        settings_warning = None
        try:
            self.settings = self.store.load()
        except SettingsError:
            self.settings = Settings()
            settings_warning = "设置无法读取，已使用默认设置。原设置文件未删除。"
        self.application.setQuitOnLastWindowClosed(False)
        self.application.setStyle("Fusion")
        apply_theme(application, self.settings.theme, self.settings.font_size)
        self.window = MainWindow(self.settings)
        self.window.setWindowIcon(QIcon(str(resource_path("clipvault.svg"))))
        self.database = DatabaseService(directory / "history.sqlite3", self.settings, self)
        self.clipboard = ClipboardMonitor(
            QtClipboardBackend(application.clipboard()), application.clipboard(), self
        )
        self.hotkeys = HotkeyManager(application, enabled=enable_hotkey)
        self.startup = WindowsStartup()
        self._search_job: tuple[int, int] | None = None
        self._preview_job: int | None = None
        self._actions: dict[int, str] = {}
        self._stopping = False
        self.tray: QSystemTrayIcon | None = None
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(100)
        self.refresh_timer.timeout.connect(self.window.refresh)
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.setInterval(60 * 60 * 1000)
        self.cleanup_timer.timeout.connect(lambda: self.database.submit("cleanup"))
        self.cleanup_timer.start()
        self._connect()
        if not no_tray and QSystemTrayIcon.isSystemTrayAvailable():
            self._create_tray()
        self.window.tray_available = self.tray is not None
        self.clipboard.set_paused(self.settings.paused)
        if enable_hotkey:
            try:
                self.hotkeys.register(self.settings.hotkey)
            except (HotkeyError, ValueError):
                settings_warning = "全局快捷键注册失败，可能被其他应用占用。请在设置中更换组合。"
        self._hotkey_status()
        self.database.submit("initialize")
        if not background or self.tray is None:
            self.window.show()
            self.window.search.setFocus()
        if settings_warning:
            self.window.notify(settings_warning, persistent=True)
        elif sys.platform != "win32":
            self.window.notify("当前为非 Windows 环境；全局快捷键和开机启动仅在 Windows 提供。")

    def _connect(self):
        self.window.search_requested.connect(self._search)
        self.window.selected.connect(self._preview)
        self.window.copy_requested.connect(self._copy_id)
        self.window.pause_requested.connect(self.toggle_pause)
        self.window.quit_requested.connect(self.quit)
        self.hotkeys.activated.connect(self.toggle_window)
        self.clipboard.captured.connect(
            lambda text, timestamp: self.database.submit("capture", (text, timestamp))
        )
        self.clipboard.status_changed.connect(self.window.listener_status)
        self.clipboard.skipped.connect(self._clipboard_skipped)
        self.clipboard.copied.connect(self._copied)
        self.database.result.connect(self._result)
        self.database.error.connect(self._error)
        preview = self.window.preview
        preview.copy_requested.connect(lambda: self._copy_id(self.window.current_id()))
        preview.favorite_requested.connect(lambda: self._flag("is_favorite"))
        preview.pin_requested.connect(lambda: self._flag("is_pinned"))
        preview.delete_requested.connect(self._delete)
        preview.format_requested.connect(self._format)
        preview.open_url_requested.connect(self._open_url)
        page = self.window.settings_page
        page.save_requested.connect(self.save_settings)
        page.clear_requested.connect(self.clear_history)
        page.open_data_requested.connect(self.open_data_folder)
        self.application.aboutToQuit.connect(self.shutdown)

    def _create_tray(self):
        self.tray = QSystemTrayIcon(self.window.windowIcon(), self)
        self.tray.setToolTip("ClipVault — Your Clipboard. Your Control.")
        menu = QMenu()
        show = QAction("打开 ClipVault", menu)
        show.triggered.connect(lambda: self.window.show_panel())
        menu.addAction(show)
        self.tray_pause = QAction("暂停记录", menu)
        self.tray_pause.setCheckable(True)
        self.tray_pause.setChecked(self.settings.paused)
        self.tray_pause.triggered.connect(self.toggle_pause)
        menu.addAction(self.tray_pause)
        settings = QAction("设置", menu)
        settings.triggered.connect(self.show_settings)
        menu.addAction(settings)
        menu.addSeparator()
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        self.tray_menu = menu

    def _tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.window.show_panel()

    def _hotkey_status(self):
        if not self.hotkeys.available:
            self.window.hotkey_label.setText(f"{self.settings.hotkey}  ·  Windows only")
        elif self.hotkeys.identifier is None:
            self.window.hotkey_label.setText("Shortcut unavailable · change in Settings")
        else:
            self.window.hotkey_label.setText(f"{self.settings.hotkey}  to toggle")

    def toggle_window(self):
        if (
            self.window.isVisible()
            and not self.window.isMinimized()
            and self.window.isActiveWindow()
        ):
            self.window.hide()
        else:
            self.window.show_panel(quick=True)

    def show_settings(self):
        self.window.show_panel()
        self.window.navigate("settings")

    def _search(self, request):
        self._search_job = (self.database.submit("search", request), request.offset)

    def _preview(self, clip_id):
        self._preview_job = self.database.submit("preview", clip_id)

    def _copy_id(self, clip_id):
        if clip_id is not None:
            self._actions[self.database.submit("get", clip_id)] = "copy"

    def _flag(self, flag):
        clip = self.window.preview.clip
        if clip is not None and clip.id == self.window.current_id():
            self.database.submit("flag", (clip.id, flag, not getattr(clip, flag)))

    def _delete(self):
        clip_id = self.window.current_id()
        if clip_id is not None:
            self.database.submit("delete", clip_id)

    def _format(self):
        clip = self.window.preview.clip
        if clip and clip.content_type == "json":
            self.database.submit("format", clip.id)

    def _open_url(self):
        clip = self.window.preview.clip
        if clip and clip.content_type == "url" and is_web_url(clip.content.strip()):
            if not QDesktopServices.openUrl(QUrl(clip.content.strip())):
                self.window.notify("无法打开默认浏览器。")

    def _copied(self, clip_id):
        self.database.submit("touch", clip_id)
        self.window.notify("已复制到系统剪贴板。")
        if self.settings.copy_notification and self.tray is not None:
            self.tray.showMessage(
                "ClipVault", "已复制到剪贴板", QSystemTrayIcon.MessageIcon.Information, 1400
            )
        if self.window.quick_mode:
            self.window.hide()

    def _clipboard_skipped(self, reason):
        messages = {
            "too_long": "内容超过 100,000 字符，未记录。",
            "copy_failed": "系统剪贴板暂时不可写，请重试复制。",
        }
        if reason in messages:
            self.window.notify(messages[reason])

    def _result(self, job_id, name, value):
        if name == "search":
            if self._search_job is not None and self._search_job[0] == job_id:
                self.window.accept_page(value, append=self._search_job[1] != 0)
        elif name == "preview":
            if job_id == self._preview_job:
                clip, rendered = value
                if clip is None or clip.id == self.window.current_id():
                    self.window.preview.set_clip(clip, rendered)
        elif name == "get":
            action = self._actions.pop(job_id, None)
            if action == "copy" and value is not None:
                self.clipboard.copy(value.content, value.id)
        elif name == "format" and value is not None:
            clip_id, text = value
            self.clipboard.copy(text, clip_id)
            # Formatting is explicitly copied, but does not overwrite or add a history entry.
        elif name == "capture":
            if value["clip_id"] is not None:
                self.refresh_timer.start()
            elif value["reason"] == "sensitive":
                self.window.notify("隐私过滤：疑似敏感内容未记录。")
            elif value["reason"] in {"too_long", "invalid_text"}:
                self.window.notify("内容过长或包含无效字符，未记录。")
        elif name in {"initialize", "flag", "delete", "touch", "clear", "cleanup"}:
            self.refresh_timer.start()
            if name == "clear":
                self.window.notify(f"已清空 {value:,} 条普通记录。收藏和置顶已保留。")

    def _error(self, job_id, name, message):
        self._actions.pop(job_id, None)
        if name == "search" and self._search_job and job_id == self._search_job[0]:
            self.window.search_busy = False
            self.window.load_more.setEnabled(True)
        self.window.notify(message, persistent=True)
        self.window.listener_label.setText("●  Storage error · retry available")

    def toggle_pause(self):
        settings = replace(self.settings, paused=not self.settings.paused)
        try:
            self.store.save(settings)
        except SettingsError:
            self.window.notify("暂停状态无法保存。请检查数据目录权限。", persistent=True)
            if self.tray is not None:
                self.tray_pause.setChecked(self.settings.paused)
            return
        self.settings = settings
        self.clipboard.set_paused(settings.paused)
        self.database.submit("configure", settings)
        self.window.apply_settings(settings)
        if self.tray is not None:
            self.tray_pause.setChecked(settings.paused)
        self.window.notify(
            "已暂停记录。" if settings.paused else "已恢复记录；暂停期间的内容不会补录。"
        )

    def save_settings(self, candidate: Settings):
        old = self.settings
        candidate = replace(candidate, paused=old.paused)
        startup_snapshot = None
        changed_hotkey = False
        try:
            candidate.validate()
            candidate = replace(candidate, hotkey=parse_hotkey(candidate.hotkey).display)
            self.hotkeys.register(candidate.hotkey)
            changed_hotkey = candidate.hotkey != old.hotkey
            if candidate.start_at_login != old.start_at_login:
                startup_snapshot = self.startup.snapshot()
                self.startup.set_enabled(candidate.start_at_login)
            self.store.save(candidate)
        except (SettingsError, ValueError, HotkeyError, OSError) as error:
            rollback_failed = False
            try:
                if startup_snapshot is not None:
                    self.startup.restore(startup_snapshot)
                if changed_hotkey:
                    self.hotkeys.register(old.hotkey)
            except (HotkeyError, OSError):
                rollback_failed = True
            if isinstance(error, HotkeyError):
                message = "快捷键注册失败，可能与其他软件冲突；原快捷键仍然有效。"
            elif isinstance(error, (SettingsError, ValueError)):
                message = "设置无效或无法保存。请检查快捷键格式和数据目录权限。"
            else:
                message = "无法更新 Windows 开机启动项，请检查当前用户权限。"
            if rollback_failed:
                message += " 部分系统设置无法恢复，请重新保存设置。"
            self.window.notify(message, persistent=True)
            self._hotkey_status()
            return
        self.settings = candidate
        self.database.submit("configure", candidate)
        self.database.submit("cleanup")
        apply_theme(self.application, candidate.theme, candidate.font_size)
        self.window.apply_settings(candidate)
        self._hotkey_status()
        current = self.window.current_id()
        if current is not None:
            self._preview(current)
        self.window.notify("设置已保存并立即生效。")

    def clear_history(self):
        answer = QMessageBox.question(
            self.window,
            "清空普通历史记录",
            "删除所有非收藏、非置顶记录？此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.database.submit("clear")

    def open_data_folder(self):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.directory))):
            self.window.notify("无法打开本地数据目录。")

    def quit(self):
        self.shutdown()
        self.application.quit()

    def shutdown(self):
        if self._stopping:
            return
        self._stopping = True
        self.refresh_timer.stop()
        self.cleanup_timer.stop()
        self.clipboard.close()
        self.hotkeys.close()
        if self.tray is not None:
            self.tray.hide()
        self.database.close()
        self.window.hide()
