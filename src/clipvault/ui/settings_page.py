import sys
from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from clipvault.ui.icons import icon
from clipvault.utils.settings import Settings


class SettingsPage(QWidget):
    save_requested = Signal(object)
    clear_requested = Signal()
    open_data_requested = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.current = settings
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 12, 0)
        layout.setSpacing(18)

        self.theme = QComboBox()
        self.theme.addItem("Dark", "dark")
        self.theme.addItem("Light", "light")
        self.language = QComboBox()
        self.language.addItem("Follow system", "system")
        self.language.addItem("简体中文", "zh_CN")
        self.language.addItem("English", "en")
        self.reduce_motion = QCheckBox("Reduce motion (also respects Windows animation settings)")
        self.shortcut_panel = QComboBox()
        self.shortcut_panel.addItem("Full window", "full")
        self.shortcut_panel.addItem("Mini window", "compact")
        self.font_size = QSpinBox()
        self.font_size.setRange(11, 20)
        self.font_size.setSuffix(" px")
        self.opacity = QSpinBox()
        self.opacity.setRange(65, 100)
        self.opacity.setSuffix(" %")
        self.notifications = QCheckBox("Show a tray notification after copying")
        self.auto_hide = QCheckBox("Hide quick panel when it loses focus")
        appearance = self._section(
            "Appearance",
            [
                ("Theme", self.theme),
                ("Language", self.language),
                ("Font size", self.font_size),
                ("Window opacity", self.opacity),
                ("", self.notifications),
                ("", self.auto_hide),
                ("", self.reduce_motion),
            ],
        )
        layout.addWidget(appearance)

        self.mini_opacity = QSpinBox()
        self.mini_opacity.setRange(40, 100)
        self.mini_opacity.setSuffix(" %")
        self.mini_topmost = QCheckBox("Keep the mini window above other windows")
        self.mini_glass = QCheckBox("Liquid glass appearance")
        mini_hint = QLabel(
            "Drag anywhere to move; drag edges to resize. Windows 11 Acrylic blur is used "
            "when supported; other systems use translucent glass styling."
        )
        mini_hint.setWordWrap(True)
        mini_hint.setObjectName("muted")
        layout.addWidget(
            self._section(
                "Mini window",
                [
                    ("Mini opacity", self.mini_opacity),
                    ("", self.mini_topmost),
                    ("", self.mini_glass),
                    ("", mini_hint),
                ],
            )
        )

        self.hotkey = QLineEdit()
        self.hotkey.setPlaceholderText("Ctrl+Shift+V")
        self.hotkey.setMaxLength(80)
        self.hotkey.setToolTip("Ctrl / Alt / Shift / Win + A–Z, 0–9, F1–F11 or navigation key")
        self.startup = QCheckBox("Start in the system tray when Windows starts")
        if sys.platform != "win32":
            self.startup.setEnabled(False)
            self.startup.setToolTip("Available on Windows only")
        self.quit_on_close = QCheckBox("Exit the app when the window is closed")
        layout.addWidget(
            self._section(
                "Shortcuts & startup",
                [
                    ("Global shortcut", self.hotkey),
                    ("Shortcut opens", self.shortcut_panel),
                    ("", self.startup),
                    ("", self.quit_on_close),
                ],
            )
        )

        self.max_history = QSpinBox()
        self.max_history.setRange(100, 100_000)
        self.max_history.setSingleStep(100)
        self.retention = QComboBox()
        for days in (0, 7, 30, 90):
            self.retention.addItem("Never" if days == 0 else f"{days} days", days)
        self.sensitive = QCheckBox("Skip recognizable passwords, private keys and API tokens")
        self.clean_text = QCheckBox(
            "Automatically clean copied text (zero-width artifacts and spaces)"
        )
        self.clean_hint = QLabel(
            "Cleans new history and text copied from history; keeps indentation and emoji. "
            "Does not rewrite the source clipboard or existing records."
        )
        self.clean_hint.setWordWrap(True)
        self.clean_hint.setObjectName("muted")
        self.capture_images = QCheckBox("Save copied images locally (no sensitive-image detection)")
        self.capture_files = QCheckBox("Record copied file paths only; never read file contents")
        layout.addWidget(
            self._section(
                "Privacy & history",
                [
                    ("Ordinary clip limit", self.max_history),
                    ("Auto cleanup", self.retention),
                    ("", self.sensitive),
                    ("", self.clean_text),
                    ("", self.clean_hint),
                    ("", self.capture_images),
                    ("", self.capture_files),
                ],
            )
        )
        hint = QLabel(
            "Favorites and pinned clips survive cleanup and Clear history.\n"
            "Secret detection is a heuristic. Pause recording before copying secrets.\n"
            "Data stays on this device. SQLite storage is not encrypted."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        actions = QHBoxLayout()
        folder = QPushButton("Open data folder")
        folder.setIcon(icon("folder"))
        folder.clicked.connect(self.open_data_requested)
        self.clear = QPushButton("Clear ordinary history…")
        self.clear.setObjectName("danger")
        self.clear.setIcon(icon("trash", "#ff919e"))
        self.clear.clicked.connect(self.clear_requested)
        actions.addWidget(folder)
        actions.addWidget(self.clear)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        scroll.setWidget(panel)
        outer.addWidget(scroll)
        footer = QHBoxLayout()
        reset = QPushButton("Reset form")
        reset.clicked.connect(
            lambda: self.populate(replace(Settings(), paused=self.current.paused))
        )
        self.save = QPushButton("Save settings")
        self.save.setObjectName("primary")
        self.save.setIcon(icon("check", "#101522"))
        self.save.clicked.connect(self._save)
        footer.addWidget(reset)
        footer.addStretch()
        footer.addWidget(self.save)
        outer.addLayout(footer)
        self.populate(settings)

    def _section(self, title: str, rows: list) -> QFrame:
        frame = QFrame()
        frame.setObjectName("privacyCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(17, 15, 17, 16)
        label = QLabel(title)
        label.setObjectName("sectionTitle")
        layout.addWidget(label)
        form = QFormLayout()
        form.setHorizontalSpacing(25)
        form.setVerticalSpacing(12)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        for text, widget in rows:
            if text:
                form.addRow(text, widget)
            else:
                form.addRow(widget)
        layout.addLayout(form)
        return frame

    def populate(self, settings: Settings):
        self.current = settings
        self.theme.setCurrentIndex(self.theme.findData(settings.theme))
        self.language.setCurrentIndex(self.language.findData(settings.language))
        self.shortcut_panel.setCurrentIndex(self.shortcut_panel.findData(settings.shortcut_panel))
        self.reduce_motion.setChecked(settings.reduce_motion)
        self.font_size.setValue(settings.font_size)
        self.opacity.setValue(settings.opacity)
        self.mini_opacity.setValue(settings.mini_opacity)
        self.mini_topmost.setChecked(settings.mini_topmost)
        self.mini_glass.setChecked(settings.mini_glass)
        self.hotkey.setText(settings.hotkey)
        self.max_history.setValue(settings.max_history)
        self.retention.setCurrentIndex(self.retention.findData(settings.retention_days))
        for checkbox, value in (
            (self.notifications, settings.copy_notification),
            (self.auto_hide, settings.auto_hide),
            (self.startup, settings.start_at_login),
            (self.quit_on_close, settings.quit_on_close),
            (self.sensitive, settings.sensitive_filter),
            (self.clean_text, settings.clean_copied_text),
            (self.capture_images, settings.capture_images),
            (self.capture_files, settings.capture_files),
        ):
            checkbox.setChecked(value)

    def _save(self):
        self.save_requested.emit(
            replace(
                self.current,
                theme=self.theme.currentData(),
                language=self.language.currentData(),
                reduce_motion=self.reduce_motion.isChecked(),
                shortcut_panel=self.shortcut_panel.currentData(),
                font_size=self.font_size.value(),
                opacity=self.opacity.value(),
                mini_opacity=self.mini_opacity.value(),
                mini_topmost=self.mini_topmost.isChecked(),
                mini_glass=self.mini_glass.isChecked(),
                hotkey=self.hotkey.text().strip(),
                max_history=self.max_history.value(),
                retention_days=self.retention.currentData(),
                sensitive_filter=self.sensitive.isChecked(),
                clean_copied_text=self.clean_text.isChecked(),
                capture_images=self.capture_images.isChecked(),
                capture_files=self.capture_files.isChecked(),
                copy_notification=self.notifications.isChecked(),
                auto_hide=self.auto_hide.isChecked(),
                start_at_login=self.startup.isChecked(),
                quit_on_close=self.quit_on_close.isChecked(),
            )
        )
