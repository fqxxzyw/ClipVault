"""Local aggregate statistics and an accessible, offline emoji picker."""

import unicodedata

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from clipvault.core.emoji import EMOJI
from clipvault.ui.i18n import tr, translate_widgets
from clipvault.ui.icons import icon


class StatisticsPage(QWidget):
    refresh_requested = Signal()
    reset_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.period = QComboBox()
        for title, days in (
            ("All dates", 0),
            ("Today", 1),
            ("Last 7 days", 7),
            ("Last 30 days", 30),
        ):
            self.period.addItem(title, days)
        self.period.currentIndexChanged.connect(self.refresh_requested)
        layout.addWidget(self.period)
        grid = QGridLayout()
        grid.setSpacing(12)
        self.values = {}
        for i, (key, title) in enumerate(
            (
                ("captures", "Captured copies"),
                ("reuses", "Copies from ClipVault"),
                ("characters", "Copied characters"),
                ("lines", "Copied lines"),
                ("emoji", "Copied emoji"),
                ("images", "Copied images"),
                ("files", "File selections"),
            )
        ):
            card = QFrame()
            card.setObjectName("privacyCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.addWidget(QLabel(title))
            value = QLabel("0")
            value.setObjectName("heading")
            value.setProperty("i18nSkip", True)
            self.values[key] = value
            card_layout.addWidget(value)
            grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(grid)
        self.note = QLabel(
            "Counts start with this version. Paused and filtered copies are excluded.\n"
            "Paste count: unavailable. The clipboard does not report paste events; "
            "reuse is not a paste.\n"
            "Emoji counts cover common Unicode sequences, not every possible grapheme."
        )
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.refresh = QPushButton("Refresh statistics")
        self.refresh.setIcon(icon("refresh"))
        self.refresh.clicked.connect(self.refresh_requested)
        layout.addWidget(self.refresh)
        self.reset = QPushButton("Reset statistics…")
        self.reset.setObjectName("danger")
        self.reset.clicked.connect(self.reset_requested)
        layout.addWidget(self.reset)
        layout.addStretch()
        # Large system fonts and short windows must not clip the bottom controls.
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        panel = QWidget()
        panel.setLayout(layout)
        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(panel)
        outer.addWidget(self.scroll)
        self.setLayout(outer)

    def update_values(self, values):
        for key, widget in self.values.items():
            widget.setText(f"{values.get(key, 0):,}")


def emoji_glyphs_available(text, family):
    # DejaVu has a few smileys, but symbol coverage does not imply emoji presentation.
    if family == "DejaVu Sans" and any(
        not (0x1F600 <= ord(char) <= 0x1F64F or char == "❤")
        for char in text
        if unicodedata.category(char) not in {"Cf", "Mn"}
    ):
        return False
    metrics = QFontMetrics(QFont(family, 18))
    return all(
        metrics.inFontUcs4(ord(char))
        for char in text
        if unicodedata.category(char) not in {"Cf", "Mn"}
    )


class EmojiPage(QWidget):
    copy_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Click an emoji to copy. It is saved in history when recording is active.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setSpacing(8)
        self.buttons = []
        families = set(QFontDatabase.families())
        self.emoji_font = next(
            (
                font
                for font in (
                    "Segoe UI Emoji",
                    "Noto Color Emoji",
                    "Noto Emoji",
                    "Apple Color Emoji",
                    "DejaVu Sans",
                )
                if font in families
            ),
            "Segoe UI",
        )
        for i, (emoji, name) in enumerate(EMOJI):
            button = QPushButton(emoji)
            button.setProperty("i18nSkip", True)
            button.setMinimumSize(48, 48)
            button._emoji = emoji
            button._emoji_supported = emoji_glyphs_available(emoji, self.emoji_font)
            display = emoji
            if self.emoji_font not in {"Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"}:
                display = display.replace("\ufe0f", "\ufe0e")
                if len(display) == 1:
                    display += "\ufe0e"
            button.setStyleSheet(
                f"font-family: '{self.emoji_font}'; font-size: 23px;"
                if button._emoji_supported
                else "font-size: 12px;"
            )
            button.setText(
                display
                if button._emoji_supported
                else QFontMetrics(QFont("Segoe UI", 10)).elidedText(
                    tr(name),
                    Qt.TextElideMode.ElideRight,
                    52,
                )
            )
            button.setToolTip(tr(name))
            button.setAccessibleName(tr(name))
            button.clicked.connect(lambda checked=False, text=emoji: self.copy_requested.emit(text))
            grid.addWidget(button, i // 8, i % 8)
            self.buttons.append((button, name))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        layout.addWidget(scroll, 1)

    def retranslate(self):
        translate_widgets(self)
        for button, name in self.buttons:
            if not button._emoji_supported:
                button.setText(
                    QFontMetrics(QFont("Segoe UI", 10)).elidedText(
                        tr(name), Qt.TextElideMode.ElideRight, 52
                    )
                )
            button.setToolTip(tr(name))
            button.setAccessibleName(tr(name))
