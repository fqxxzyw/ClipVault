"""Dialog for deliberately creating reusable text without touching the clipboard."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from clipvault.core.privacy import validate_capture
from clipvault.database.models import MAX_TEXT_LENGTH
from clipvault.ui.i18n import tr


class ManualEntryDialog(QDialog):
    save_requested = Signal(str, bool, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("New clip"))
        self.setMinimumSize(440, 340)
        self.resize(580, 430)
        self._busy = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        title = QLabel(tr("Create a reusable clip"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        description = QLabel(tr("Write or paste text to save and reuse later."))
        description.setObjectName("muted")
        description.setWordWrap(True)
        layout.addWidget(description)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("manualEditor")
        self.editor.setPlaceholderText(tr("Enter text here…"))
        self.editor.setAccessibleName(tr("Clip text"))
        self.editor.textChanged.connect(self._validate)
        layout.addWidget(self.editor, 1)
        self.counter = QLabel()
        self.counter.setObjectName("muted")
        layout.addWidget(self.counter)

        self.favorite = QCheckBox(tr("Add to Favorites and protect from automatic cleanup"))
        self.favorite.setChecked(True)
        layout.addWidget(self.favorite)
        hint = QLabel(tr("Saved locally without encryption. Avoid storing passwords or secrets."))
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.error = QLabel()
        self.error.setObjectName("manualError")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel = QPushButton(tr("Cancel"))
        self.cancel.clicked.connect(self.reject)
        buttons.addWidget(self.cancel)
        self.save = QPushButton(tr("Save"))
        self.save.clicked.connect(lambda: self._submit(False))
        buttons.addWidget(self.save)
        self.save_copy = QPushButton(tr("Save and copy"))
        self.save_copy.setObjectName("primary")
        self.save_copy.clicked.connect(lambda: self._submit(True))
        buttons.addWidget(self.save_copy)
        layout.addLayout(buttons)
        self._validate()
        self.editor.setFocus()

    def _validate(self):
        text = self.editor.toPlainText()
        decision = validate_capture(text, filter_sensitive=False)
        self.counter.setText(
            tr("{count:,} / {limit:,} characters", count=len(text), limit=MAX_TEXT_LENGTH)
        )
        if decision.reason == "too_long":
            self.show_error(tr("Text exceeds the 100,000 character limit."))
        elif decision.reason == "invalid_text":
            self.show_error(tr("Text contains invalid characters."))
        else:
            self.error.hide()
        self.save.setEnabled(decision.allowed and not self._busy)
        self.save_copy.setEnabled(decision.allowed and not self._busy)

    def _submit(self, copy_after):
        text = self.editor.toPlainText()
        if self._busy or not validate_capture(text, filter_sensitive=False).allowed:
            return
        self.set_busy(True)
        self.save_requested.emit(text, self.favorite.isChecked(), copy_after)

    def set_busy(self, busy):
        self._busy = busy
        self.editor.setEnabled(not busy)
        self.favorite.setEnabled(not busy)
        self.cancel.setEnabled(not busy)
        self._validate()

    def show_error(self, message):
        self.error.setText(message)
        self.error.show()

    def reject(self):
        if not self._busy:
            super().reject()
