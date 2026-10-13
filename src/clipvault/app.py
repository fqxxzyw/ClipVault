import sys
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from clipvault.core.classifier import is_web_url
from clipvault.core.clipboard import ClipboardMonitor, QtClipboardBackend
from clipvault.core.hotkeys import HotkeyError, HotkeyManager, parse_hotkey
from clipvault.services.database import DatabaseService
from clipvault.ui.i18n import tr, translate_widgets
from clipvault.ui.main_window import MainWindow
from clipvault.ui.mini_window import MiniWindow
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
        if sys.platform != "win32":
            self.application.setStyle("Fusion")
        apply_theme(application, self.settings.theme, self.settings.font_size)
        self.window = MainWindow(self.settings)
        self.window.setWindowIcon(QIcon(str(resource_path("clipvault.svg"))))
        self.mini = MiniWindow(self.window.model)
        self.mini.setWindowIcon(self.window.windowIcon())
        self.mini.apply_settings(self.settings)
        self.database = DatabaseService(directory / "history.sqlite3", self.settings, self)
        self.clipboard = ClipboardMonitor(
            QtClipboardBackend(application.clipboard()), application.clipboard(), self
        )
        self.hotkeys = HotkeyManager(application, enabled=enable_hotkey)
        self.startup = WindowsStartup()
        self._search_job: tuple[int, int] | None = None
        self._preview_job: int | None = None
        self._actions: dict[int, str] = {}
        self._stats_job = None
        self._emoji_text = ""
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
        self.window.mini_requested.connect(self.show_mini)
        self.mini.copy_requested.connect(self._copy_id)
        self.mini.markdown_copy_requested.connect(self._copy_markdown)
        self.mini.full_requested.connect(self._show_full)
        self.mini.refresh_requested.connect(self.window.refresh)
        self.mini.more_requested.connect(self.window._load_more)
        self.mini.dismissed.connect(self._mini_dismissed)
        self.mini.preferences_requested.connect(self._mini_preferences)
        self.mini.geometry_changed.connect(self._mini_geometry)
        self.hotkeys.activated.connect(self.toggle_window)
        self.clipboard.captured.connect(
            lambda text, timestamp: self.database.submit("capture", (text, timestamp))
        )
        self.clipboard.rich_captured.connect(
            lambda rich, timestamp: self.database.submit("capture_rich", (rich, timestamp))
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
        preview.language_requested.connect(
            lambda kind: self.database.submit("set_type", (self.window.current_id(), kind))
        )
        preview.markdown_copy_requested.connect(
            lambda mode: self._copy_markdown(self.window.current_id(), mode)
        )
        preview.markdown_requested.connect(
            lambda: self.database.submit("mark_markdown", self.window.current_id())
        )
        page = self.window.settings_page
        page.save_requested.connect(self.save_settings)
        page.clear_requested.connect(self.clear_history)
        page.open_data_requested.connect(self.open_data_folder)
        self.window.statistics_page.refresh_requested.connect(self._query_stats)
        self.window.statistics_page.reset_requested.connect(self._reset_stats)
        self.window.emoji_page.copy_requested.connect(self._copy_emoji)
        self.application.aboutToQuit.connect(self.shutdown)

    def _create_tray(self):
        self.tray = QSystemTrayIcon(self.window.windowIcon(), self)
        self.tray.setToolTip("ClipVault — Your Clipboard. Your Control.")
        menu = QMenu()
        show = QAction("打开 ClipVault", menu)
        show.triggered.connect(self._show_full)
        menu.addAction(show)
        self.tray_pause = QAction("暂停记录", menu)
        self.tray_pause.setCheckable(True)
        self.tray_pause.setChecked(self.settings.paused)
        self.tray_pause.triggered.connect(self.toggle_pause)
        menu.addAction(self.tray_pause)
        settings = QAction("设置", menu)
        settings.triggered.connect(self.show_settings)
        menu.addAction(settings)
        mini_action = QAction("Mini window", menu)
        mini_action.triggered.connect(self.show_mini)
        menu.addAction(mini_action)
        menu.addSeparator()
        quit_action = QAction("退出", menu)
        quit_action.triggered.connect(self.quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()
        self.tray_menu = menu
        translate_widgets(menu)

    def _tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_full()

    def _hotkey_status(self):
        if not self.hotkeys.available:
            self.window.hotkey_label.setText(tr("{key}  ·  Windows only", key=self.settings.hotkey))
        elif self.hotkeys.identifier is None:
            self.window.hotkey_label.setText(tr("Shortcut unavailable · change in Settings"))
        else:
            self.window.hotkey_label.setText(tr("{key}  to toggle", key=self.settings.hotkey))

    def toggle_window(self):
        if self.settings.shortcut_panel == "compact":
            if self.mini.isVisible() and self.mini.isActiveWindow():
                self.mini.hide()
            else:
                self.show_mini()
            return
        self.mini.hide()
        if (
            self.window.isVisible()
            and not self.window.isMinimized()
            and self.window.isActiveWindow()
        ):
            self.window.hide()
        else:
            self.window.show_panel(quick=True)

    def show_mini(self):
        self.window.hide()
        if self.window.scope not in {"all", "favorites", "pinned"}:
            self.window.navigate(self.window._last_clip_scope)
        self.mini.show_panel()

    def _show_full(self):
        self.mini.hide()
        self.window.show_panel()

    def _mini_dismissed(self):
        if self.tray is None:
            self.window.showMinimized()

    def _mini_preferences(self, values):
        allowed = {"mini_opacity", "mini_topmost", "mini_glass"}
        if not isinstance(values, dict) or set(values) - allowed:
            return
        candidate = replace(self.settings, **values)
        try:
            self.store.save(candidate)
        except SettingsError:
            self.window.notify(tr("Mini window preferences could not be saved."), persistent=True)
            self.mini.apply_settings(self.settings)
            return
        self.settings = candidate
        self.window.settings = candidate
        page = self.window.settings_page
        page.current = replace(page.current, **values)
        page.mini_opacity.setValue(candidate.mini_opacity)
        page.mini_topmost.setChecked(candidate.mini_topmost)
        page.mini_glass.setChecked(candidate.mini_glass)
        self.mini.apply_settings(candidate)

    def _mini_geometry(self, geometry):
        if self._stopping:
            return
        candidate = replace(self.settings, mini_geometry=tuple(geometry))
        if candidate.mini_geometry == self.settings.mini_geometry:
            return
        try:
            self.store.save(candidate)
        except SettingsError:
            return
        self.settings = candidate
        self.window.settings = candidate
        self.window.settings_page.current = replace(
            self.window.settings_page.current, mini_geometry=tuple(geometry)
        )

    def show_settings(self):
        self.mini.hide()
        self.window.show_panel()
        self.window.navigate("settings")

    def _search(self, request):
        self._search_job = (self.database.submit("search", request), request.offset)

    def _preview(self, clip_id):
        self._preview_job = self.database.submit("preview", clip_id)

    def _copy_id(self, clip_id):
        if clip_id is not None:
            self._actions[self.database.submit("get", clip_id)] = "copy"

    def _copy_markdown(self, clip_id, mode):
        if clip_id is not None:
            if mode == "plain":
                self.database.submit("markdown_plain", clip_id)
            elif mode == "markdown":
                self._copy_id(clip_id)

    def _copy_emoji(self, text):
        self._emoji_text = text
        self.clipboard.copy(text, 0)

    def _query_stats(self):
        days = self.window.statistics_page.period.currentData()
        end = datetime.now().date() + timedelta(days=1)
        bounds = ((end - timedelta(days=days)).isoformat(), end.isoformat()) if days else ("", "")
        self._stats_job = self.database.submit("stats", bounds)

    def _reset_stats(self):
        if (
            QMessageBox.question(
                self.window,
                tr("Reset statistics"),
                tr("Delete all aggregate counters? Clipboard history will be kept."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.database.submit("reset_stats")

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
        if clip_id:
            self.database.submit("touch", clip_id)
        elif not self.settings.paused and self._emoji_text:
            from clipvault.database.models import utc_now

            self.database.submit("capture", (self._emoji_text, utc_now()))
        self.window.notify("已复制到系统剪贴板。")
        if self.mini.isVisible() and not self.settings.mini_topmost:
            self.mini.dismiss_panel()
        if self.settings.copy_notification and self.tray is not None:
            self.tray.showMessage(
                "ClipVault", tr("已复制到剪贴板"), QSystemTrayIcon.MessageIcon.Information, 1400
            )
        if self.window.quick_mode:
            self.window.hide()

    def _clipboard_skipped(self, reason):
        messages = {
            "too_long": tr("Image or file selection exceeds the capture limit."),
            "copy_failed": "系统剪贴板暂时不可写，请重试复制。",
        }
        if reason in messages:
            self.window.notify(messages[reason])

    def _result(self, job_id, name, value):
        if name == "search":
            if self._search_job is not None and self._search_job[0] == job_id:
                current = self.mini.list_view.currentIndex()
                selected = current.data(Qt.ItemDataRole.UserRole).id if current.isValid() else None
                self.window.accept_page(value, append=self._search_job[1] != 0)
                if self.mini.isVisible() and self.window.model.items:
                    row = next(
                        (
                            i
                            for i, item in enumerate(self.window.model.items)
                            if item.id == selected
                        ),
                        0,
                    )
                    self.mini.list_view.setCurrentIndex(self.window.model.index(row, 0))
        elif name == "preview":
            if job_id == self._preview_job:
                clip, rendered, image = value
                if clip is None or clip.id == self.window.current_id():
                    self.window.preview.set_clip(clip, rendered, image)
        elif name == "get":
            action = self._actions.pop(job_id, None)
            if action == "copy" and value is not None:
                if value.content_type == "image":
                    self.database.submit("get_image", value.id)
                else:
                    self.clipboard.copy(value.content, value.id)
        elif name == "get_image" and value is not None:
            clip_id, image = value
            if not image.isNull():
                self.clipboard.copy_image(image, clip_id)
        elif name in {"format", "markdown_plain"} and value is not None:
            clip_id, text = value
            self.clipboard.copy(text, clip_id)
            # Formatting is explicitly copied, but does not overwrite or add a history entry.
        elif name in {"capture", "capture_rich"}:
            if value["clip_id"] is not None:
                self.refresh_timer.start()
            elif value["reason"] == "sensitive":
                self.window.notify("隐私过滤：疑似敏感内容未记录。")
            elif value["reason"] in {"too_long", "invalid_text"}:
                self.window.notify("内容过长或包含无效字符，未记录。")
            elif value["reason"] == "image_too_large":
                self.window.notify(tr("Image exceeds the 8 MiB storage limit and was not saved."))
        elif name == "stats" and job_id == self._stats_job:
            self.window.statistics_page.update_values(value)
        elif name == "reset_stats":
            self._query_stats()
        elif name in {
            "initialize",
            "flag",
            "delete",
            "touch",
            "clear",
            "cleanup",
            "mark_markdown",
            "set_type",
        }:
            self.refresh_timer.start()
            if name == "clear":
                self.window.notify(
                    tr(
                        "Cleared {count:,} ordinary clips. Favorites and pins were kept.",
                        count=value,
                    )
                )

    def _error(self, job_id, name, message):
        self._actions.pop(job_id, None)
        if name == "search" and self._search_job and job_id == self._search_job[0]:
            self.window.search_busy = False
            self.window.load_more.setEnabled(True)
        self.window.notify(message, persistent=True)
        self.window.listener_label.setText(tr("●  Storage error · retry available"))

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
        candidate = replace(candidate, paused=old.paused, mini_geometry=old.mini_geometry)
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
                message = tr("快捷键注册失败，可能与其他软件冲突；原快捷键仍然有效。")
            elif isinstance(error, (SettingsError, ValueError)):
                message = tr("设置无效或无法保存。请检查快捷键格式和数据目录权限。")
            else:
                message = tr("无法更新 Windows 开机启动项，请检查当前用户权限。")
            if rollback_failed:
                message += tr(" 部分系统设置无法恢复，请重新保存设置。")
            self.window.notify(message, persistent=True)
            self._hotkey_status()
            return
        self.settings = candidate
        self.database.submit("configure", candidate)
        self.database.submit("cleanup")
        apply_theme(self.application, candidate.theme, candidate.font_size)
        self.window.apply_settings(candidate)
        self.mini.apply_settings(candidate)
        if self.tray is not None:
            translate_widgets(self.tray_menu)
        self._hotkey_status()
        current = self.window.current_id()
        if current is not None:
            self._preview(current)
        self.window.notify("设置已保存并立即生效。")

    def clear_history(self):
        answer = QMessageBox.question(
            self.window,
            tr("清空普通历史记录"),
            tr("删除所有非收藏、非置顶记录？此操作无法撤销。"),
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
        self.window.motion.stop()
        self.mini.geometry_timer.stop()
        self.mini.glow_animation.stop()
        self.mini.hide()
        self.window.hide()
