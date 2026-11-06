"""Browse browser draft backups saved by the optional companion extension."""

from datetime import datetime
from urllib.parse import urlsplit

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from clipvault.ui.i18n import tr
from clipvault.ui.icons import icon


class BrowserDraftsPage(QWidget):
    refresh_requested = Signal()
    selected = Signal(str)
    copy_requested = Signal(str)
    delete_requested = Signal(str)
    clear_requested = Signal()
    toggle_requested = Signal(bool)
    pairing_requested = Signal()
    help_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_draft = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        description = QLabel(
            "The browser extension saves drafts locally even when ClipVault is closed. "
            "Connect it to see backups here."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)
        layout.addWidget(description)
        controls = QHBoxLayout()
        self.toggle = QPushButton()
        self.toggle.setProperty("i18nSkip", True)
        self.toggle.setCheckable(True)
        self.toggle.clicked.connect(self.toggle_requested)
        controls.addWidget(self.toggle)
        self.pair = QPushButton("Copy pairing code")
        self.pair.clicked.connect(self.pairing_requested)
        controls.addWidget(self.pair)
        self.help = QPushButton("Install browser extension")
        self.help.clicked.connect(self.help_requested)
        controls.addWidget(self.help)
        controls.addStretch()
        layout.addLayout(controls)
        self.status = QLabel()
        self.status.setProperty("i18nSkip", True)
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search drafts or websites…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaxLength(256)
        self.search.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        layout.addWidget(self.search)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(200)
        self.debounce.timeout.connect(self.refresh_requested)
        self.search.textChanged.connect(lambda: self.debounce.start())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setAccessibleName(tr("Browser drafts"))
        self.list.currentItemChanged.connect(self._selection_changed)
        list_layout.addWidget(self.list)
        self.empty = QLabel("No drafts yet. Type on an allowed website to save a backup.")
        self.empty.setObjectName("muted")
        self.empty.setWordWrap(True)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        list_layout.addWidget(self.empty, 1)
        self.list.hide()
        splitter.addWidget(list_panel)
        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(8, 0, 0, 0)
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName(tr("Draft text"))
        preview_layout.addWidget(self.preview, 1)
        actions = QHBoxLayout()
        self.copy = QPushButton("Copy draft")
        self.copy.setObjectName("primary")
        self.copy.clicked.connect(self._copy)
        actions.addWidget(self.copy)
        self.delete = QPushButton("Delete draft")
        self.delete.clicked.connect(self._delete)
        actions.addWidget(self.delete)
        preview_layout.addLayout(actions)
        splitter.addWidget(preview_panel)
        splitter.setSizes([270, 360])
        layout.addWidget(splitter, 1)
        footer = QHBoxLayout()
        self.note = QLabel(
            "Drafts are stored locally without encryption. Deleting here does not delete "
            "the browser's copy. Pause browser saving in the extension."
        )
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        footer.addWidget(self.note, 1)
        self.clear = QPushButton("Clear drafts…")
        self.clear.clicked.connect(self.clear_requested)
        footer.addWidget(self.clear)
        layout.addLayout(footer)
        self.set_bridge_status(False)
        self.set_preview(None)

    def set_bridge_status(self, active, message=""):
        self.toggle.blockSignals(True)
        self.toggle.setChecked(active)
        self.toggle.blockSignals(False)
        self.toggle.setText(tr("Stop browser sync" if active else "Start browser sync"))
        self.pair.setEnabled(active)
        self.status.setText(
            message
            or tr(
                "Sync is on. Pair the extension using the code."
                if active
                else "Sync is off. Browser-local backups still work independently."
            )
        )

    def set_drafts(self, drafts):
        self.empty.setVisible(not drafts)
        self.list.setVisible(bool(drafts))
        previous = self.current_id()
        self.list.blockSignals(True)
        self.list.clear()
        current_date = None
        selected_item = None
        for draft in drafts:
            try:
                stamp = datetime.fromisoformat(draft["updated_at"]).astimezone()
                day, clock = stamp.strftime("%Y-%m-%d"), stamp.strftime("%H:%M")
            except ValueError:
                day, clock = draft["updated_at"][:10], ""
            if day != current_date:
                header = QListWidgetItem(day)
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                self.list.addItem(header)
                current_date = day
            site = urlsplit(draft["origin"]).hostname or draft["origin"]
            snippet = " ".join(draft["preview"].split())[:110] or "…"
            item = QListWidgetItem(f"{clock}  ·  {site}\n{snippet}")
            item.setData(Qt.ItemDataRole.UserRole, draft["draft_id"])
            self.list.addItem(item)
            if draft["draft_id"] == previous:
                selected_item = item
        if selected_item is None and self.list.count() > 1:
            selected_item = self.list.item(1)
        if selected_item is not None:
            self.list.setCurrentItem(selected_item)
        self.list.blockSignals(False)
        self._selection_changed(self.list.currentItem(), None)

    def _selection_changed(self, current, _previous):
        draft_id = current.data(Qt.ItemDataRole.UserRole) if current is not None else None
        self.set_preview(None)
        if draft_id:
            self.selected.emit(draft_id)

    def current_id(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def set_preview(self, draft):
        self.current_draft = draft
        self.preview.setPlainText(draft["text"] if draft else "")
        self.copy.setEnabled(draft is not None)
        self.delete.setEnabled(draft is not None)

    def _copy(self):
        if self.current_draft:
            self.copy_requested.emit(self.current_draft["text"])

    def _delete(self):
        if self.current_draft:
            self.delete_requested.emit(self.current_draft["draft_id"])
