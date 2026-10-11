from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from clipvault.database.models import TYPE_LABELS, Clip
from clipvault.ui.icons import icon


class PreviewPanel(QWidget):
    copy_requested = Signal()
    favorite_requested = Signal()
    pin_requested = Signal()
    delete_requested = Signal()
    format_requested = Signal()
    open_url_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("preview")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(4, 8, 18, 45))
        self.setGraphicsEffect(shadow)
        self.setMinimumWidth(275)
        self.clip: Clip | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 17, 18, 16)
        layout.setSpacing(12)
        title_row = QHBoxLayout()
        title = QLabel("Preview")
        title.setObjectName("sectionTitle")
        self.badge = QLabel("TEXT")
        self.badge.setObjectName("badge")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.badge)
        layout.addLayout(title_row)
        self.meta = QLabel("Select a clip to get started")
        self.meta.setObjectName("muted")
        self.meta.setWordWrap(True)
        layout.addWidget(self.meta)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        layout.addWidget(self.browser, 1)
        self.special = QPushButton()
        self.special.hide()
        layout.addWidget(self.special)
        self.special.clicked.connect(self._special_action)
        self.copy = QPushButton("Copy to clipboard")
        self.copy.setIcon(icon("copy", "#101522"))
        self.copy.setObjectName("primary")
        self.copy.clicked.connect(self.copy_requested)
        layout.addWidget(self.copy)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.favorite = QPushButton("Favorite")
        self.favorite.setCheckable(True)
        self.favorite.setIcon(icon("star"))
        self.favorite.clicked.connect(self.favorite_requested)
        self.pin = QPushButton("Pin")
        self.pin.setCheckable(True)
        self.pin.setIcon(icon("pin"))
        self.pin.clicked.connect(self.pin_requested)
        row.addWidget(self.favorite)
        row.addWidget(self.pin)
        layout.addLayout(row)
        row2 = QHBoxLayout()
        self.details = QPushButton("Details")
        self.details.setIcon(icon("info"))
        self.details.clicked.connect(self.show_details)
        self.delete = QPushButton("Delete")
        self.delete.setIcon(icon("trash", "#ff919e"))
        self.delete.setObjectName("danger")
        self.delete.clicked.connect(self.delete_requested)
        row2.addWidget(self.details)
        row2.addWidget(self.delete)
        layout.addLayout(row2)
        hint = QLabel("Enter to copy  ·  ↑↓ to browse")
        hint.setObjectName("muted")
        layout.addWidget(hint)
        self.set_clip(None, "")

    def set_clip(self, clip: Clip | None, rendered: str):
        self.clip = clip
        for button in (self.copy, self.favorite, self.pin, self.details, self.delete):
            button.setEnabled(clip is not None)
        self.special.hide()
        if clip is None:
            self.badge.setText("TEXT")
            self.meta.setText("Select a clip to get started")
            self.browser.setPlainText(
                "Your next great idea starts with a copy.\n\n"
                "Copy some text in any app. ClipVault keeps it here, on your device."
            )
            self.favorite.setChecked(False)
            self.pin.setChecked(False)
            return
        self.badge.setText(TYPE_LABELS[clip.content_type].upper())
        self.meta.setText(
            f"{len(clip.content):,} characters · "
            f"{datetime.fromisoformat(clip.updated_at).astimezone():%m/%d %H:%M}"
        )
        self.browser.setHtml(rendered)
        self.favorite.setChecked(clip.is_favorite)
        self.pin.setChecked(clip.is_pinned)
        self.favorite.setText("Favorited" if clip.is_favorite else "Favorite")
        self.pin.setText("Pinned" if clip.is_pinned else "Pin")
        if clip.content_type == "json":
            self.special.setText("Format JSON & copy")
            self.special.setIcon(icon("code"))
            self.special.show()
        elif clip.content_type == "url":
            self.special.setText("Open in browser")
            self.special.setIcon(icon("external"))
            self.special.show()

    def _special_action(self):
        if self.clip and self.clip.content_type == "json":
            self.format_requested.emit()
        elif self.clip and self.clip.content_type == "url":
            self.open_url_requested.emit()

    def show_details(self):
        if self.clip is None:
            return
        clip = self.clip
        dialog = QDialog(self)
        dialog.setWindowTitle("Clip details — ClipVault")
        dialog.resize(740, 540)
        layout = QVBoxLayout(dialog)
        details = QLabel(
            f"{TYPE_LABELS[clip.content_type]} · {len(clip.content):,} characters\n"
            f"Created: {datetime.fromisoformat(clip.created_at).astimezone():%Y-%m-%d %H:%M:%S}\n"
            f"Last copied: {datetime.fromisoformat(clip.updated_at).astimezone():%Y-%m-%d %H:%M:%S}"
        )
        details.setObjectName("muted")
        layout.addWidget(details)
        full_text = QPlainTextEdit()
        full_text.setReadOnly(True)
        full_text.setFont(QFont("Consolas", 11))
        full_text.setPlainText(clip.content)
        layout.addWidget(full_text)
        close = QPushButton("Close")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()
