from datetime import datetime

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from clipvault.database.models import TYPE_LABELS, Clip
from clipvault.services.markdown import MARKDOWN_FEATURES, LocalDocument
from clipvault.services.preview import PREVIEW_LIMIT
from clipvault.ui.i18n import tr
from clipvault.ui.icons import icon


class PreviewPanel(QWidget):
    copy_requested = Signal()
    favorite_requested = Signal()
    pin_requested = Signal()
    delete_requested = Signal()
    format_requested = Signal()
    open_url_requested = Signal()
    markdown_requested = Signal()
    markdown_copy_requested = Signal(str)

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
        self.rendered = ""
        self.image = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 17, 18, 16)
        layout.setSpacing(8)
        title_row = QHBoxLayout()
        title = QLabel("Preview")
        title.setObjectName("sectionTitle")
        self.badge = QLabel("TEXT")
        self.badge.setObjectName("badge")
        self.badge.setProperty("i18nSkip", True)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.badge)
        layout.addLayout(title_row)
        self.meta = QLabel("Select a clip to get started")
        self.meta.setObjectName("muted")
        self.meta.setWordWrap(True)
        self.meta.setProperty("i18nSkip", True)
        layout.addWidget(self.meta)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        self.browser.setDocument(LocalDocument(self.browser))
        self.browser.setAccessibleName(tr("Preview"))
        layout.addWidget(self.browser, 1)
        self.image_view = QLabel()
        self.image_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_view.setMinimumSize(0, 0)
        self.image_view.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.image_view.installEventFilter(self)
        layout.addWidget(self.image_view, 1)
        self.files_view = QListWidget()
        self.files_view.setWordWrap(True)
        layout.addWidget(self.files_view, 1)
        self.md_controls = QWidget()
        md_row = QHBoxLayout(self.md_controls)
        md_row.setContentsMargins(0, 0, 0, 0)
        self.md_view = QComboBox()
        self.md_view.addItem("Rendered", "rendered")
        self.md_view.addItem("Source", "source")
        self.md_view.setAccessibleName("Markdown preview mode")
        self.md_view.currentIndexChanged.connect(self._render)
        self.md_copy = QComboBox()
        self.md_copy.addItem("Copy Markdown", "markdown")
        self.md_copy.addItem("Copy plain text", "plain")
        self.md_copy.setAccessibleName("Markdown copy format")
        md_row.addWidget(self.md_view)
        md_row.addWidget(self.md_copy)
        layout.addWidget(self.md_controls)
        self.special = QPushButton()
        self.special.hide()
        layout.addWidget(self.special)
        self.special.clicked.connect(self._special_action)
        self.copy = QPushButton("Copy to clipboard")
        self.copy.setIcon(icon("copy", "#101522"))
        self.copy.setObjectName("primary")
        self.copy.clicked.connect(self._copy)
        layout.addWidget(self.copy)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.favorite = QPushButton("Favorite")
        self.favorite.setCheckable(True)
        self.favorite.setProperty("i18nSkip", True)
        self.favorite.setIcon(icon("star"))
        self.favorite.clicked.connect(self.favorite_requested)
        self.pin = QPushButton("Pin")
        self.pin.setCheckable(True)
        self.pin.setProperty("i18nSkip", True)
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

    def set_clip(self, clip: Clip | None, rendered: str, image=None):
        self.clip = clip
        self.rendered = rendered
        self.image = image
        self.image_view.setVisible(clip is not None and clip.content_type == "image")
        self.files_view.setVisible(clip is not None and clip.content_type == "files")
        self.browser.setVisible(clip is None or clip.content_type not in {"image", "files"})
        self._update_image()
        self.files_view.clear()
        if clip and clip.content_type == "files":
            for path in clip.content.splitlines():
                item = QListWidgetItem(icon("file"), path)
                item.setToolTip(path)
                self.files_view.addItem(item)
        for button in (self.copy, self.favorite, self.pin, self.details, self.delete):
            button.setEnabled(clip is not None)
        self.special.hide()
        self.copy.setText(
            tr("Copy paths" if clip and clip.content_type == "files" else "Copy to clipboard")
        )
        self.copy.setAccessibleName(self.copy.text())
        self.md_controls.setVisible(clip is not None and clip.content_type == "markdown")
        if clip is None:
            self.badge.setText("TEXT")
            self.meta.setText(tr("Select a clip to get started"))
            self.browser.setPlainText(
                tr(
                    "Your next great idea starts with a copy.\n\n"
                    "Copy some text in any app. ClipVault keeps it here, on your device."
                )
            )
            self.favorite.setChecked(False)
            self.pin.setChecked(False)
            self.favorite.setText(tr("Favorite"))
            self.pin.setText(tr("Pin"))
            return
        self.badge.setText(tr(TYPE_LABELS[clip.content_type]).upper())
        self.meta.setText(
            tr("{count:,} characters", count=len(clip.content))
            + " · "
            + f"{datetime.fromisoformat(clip.updated_at).astimezone():%m/%d %H:%M}"
        )
        if clip.content_type == "image":
            self.meta.setText(clip.content)
        self._render()
        self.favorite.setChecked(clip.is_favorite)
        self.pin.setChecked(clip.is_pinned)
        self.favorite.setText(tr("Favorited" if clip.is_favorite else "Favorite"))
        self.pin.setText(tr("Pinned" if clip.is_pinned else "Pin"))
        self.favorite.setAccessibleName(self.favorite.text())
        self.pin.setAccessibleName(self.pin.text())
        if clip.content_type == "json":
            self.special.setText(tr("Format JSON & copy"))
            self.special.setIcon(icon("code"))
            self.special.show()
        elif clip.content_type == "url":
            self.special.setText(tr("Open in browser"))
            self.special.setIcon(icon("external"))
            self.special.show()
        elif clip.content_type == "text":
            self.special.setText(tr("Preview as Markdown"))
            self.special.setIcon(icon("code"))
            self.special.show()
        self.special.setAccessibleName(self.special.text())

    def _render(self):
        if self.clip is None:
            return
        if self.clip.content_type == "markdown" and self.md_view.currentData() == "rendered":
            self.browser.document().setDefaultStyleSheet(
                "h1 {font-size:23px;} h2 {font-size:19px;} "
                "pre, code {font-family:Consolas,monospace;} "
                "table {border-collapse:collapse;} td, th {padding:6px;}"
            )
            self.browser.document().setMarkdown(
                self.clip.content[:PREVIEW_LIMIT], MARKDOWN_FEATURES
            )
            self.browser.setToolTip(tr("Markdown preview does not load images or open links."))
        else:
            self.browser.setHtml(self.rendered)
            self.browser.setToolTip("")
        if len(self.clip.content) > PREVIEW_LIMIT:
            self.meta.setText(
                tr("{count:,} characters", count=len(self.clip.content))
                + f" · {PREVIEW_LIMIT:,} / {len(self.clip.content):,}"
            )

    def _update_image(self):
        if self.image is not None and not self.image.isNull():
            from PySide6.QtGui import QPixmap

            self.image_view.setPixmap(
                QPixmap.fromImage(self.image).scaled(
                    self.image_view.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.image_view.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_image()

    def eventFilter(self, watched, event):
        if watched is self.image_view and event.type() == QEvent.Type.Resize:
            self._update_image()
        return super().eventFilter(watched, event)

    def _copy(self):
        if self.clip and self.clip.content_type == "markdown":
            self.markdown_copy_requested.emit(self.md_copy.currentData())
        else:
            self.copy_requested.emit()

    def _special_action(self):
        if self.clip and self.clip.content_type == "json":
            self.format_requested.emit()
        elif self.clip and self.clip.content_type == "url":
            self.open_url_requested.emit()
        elif self.clip and self.clip.content_type == "text":
            self.markdown_requested.emit()

    def show_details(self):
        if self.clip is None:
            return
        clip = self.clip
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Clip details — ClipVault"))
        dialog.resize(740, 540)
        layout = QVBoxLayout(dialog)
        details = QLabel(
            tr(TYPE_LABELS[clip.content_type])
            + " · "
            + tr("{count:,} characters", count=len(clip.content))
            + "\n"
            + tr(
                "Created: {date}",
                date=f"{datetime.fromisoformat(clip.created_at).astimezone():%Y-%m-%d %H:%M:%S}",
            )
            + "\n"
            + tr(
                "Last copied: {date}",
                date=f"{datetime.fromisoformat(clip.updated_at).astimezone():%Y-%m-%d %H:%M:%S}",
            )
        )
        details.setObjectName("muted")
        layout.addWidget(details)
        full_text = QPlainTextEdit()
        full_text.setReadOnly(True)
        full_text.setFont(QFont("Consolas", 11))
        full_text.setPlainText(clip.content)
        layout.addWidget(full_text)
        close = QPushButton(tr("Close"))
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()
