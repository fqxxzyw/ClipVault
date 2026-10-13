"""Content-only quick picker sharing the paginated history model."""

from PySide6.QtCore import QEvent, QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QKeySequence, QPainter, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QListView,
    QMenu,
    QStyle,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from clipvault.ui.i18n import tr
from clipvault.ui.icons import icon, thumbnail_icon
from clipvault.ui.styles import PALETTES


class ContentDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = "dark"
        self.font_size = 13

    def sizeHint(self, option, index):
        return QSize(340, 92 + max(self.font_size - 13, 0) * 4)

    def paint(self, painter: QPainter, option, index):
        item = index.data(Qt.ItemDataRole.UserRole)
        if item is None:
            return
        c = PALETTES[self.theme]
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = QRectF(option.rect).adjusted(2, 3, -2, -3)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(
            QColor(c["selected"] if selected else c["hover"] if hovered else c["card"])
        )
        painter.setPen(QPen(QColor(c["accent"] if selected else c["border"]), 1))
        painter.drawRoundedRect(rect, 10, 10)
        font = option.font
        font.setPixelSize(self.font_size)
        painter.setFont(font)
        painter.setPen(QColor(c["text"]))
        metrics = painter.fontMetrics()
        # Fixed line budget: long clips never spill into another clickable row.
        lines = item.preview.replace("\r", "").splitlines() or [""]
        y = rect.top() + 15
        line_height = metrics.height() + 3
        budget = max(1, int((rect.height() - 26) / line_height))
        text_left = rect.left() + 13
        text_width = rect.width() - 26
        if item.content_type in {"image", "files"}:
            glyph = (
                thumbnail_icon(item.thumbnail)
                if item.thumbnail
                else icon("file" if item.content_type == "files" else "image")
            )
            glyph.paint(painter, int(text_left), int(rect.top() + 14), 58, 58)
            text_left += 70
            text_width -= 70
        for line in lines[:budget]:
            painter.drawText(
                QRectF(text_left, y, text_width, line_height),
                Qt.AlignmentFlag.AlignLeft,
                metrics.elidedText(line, Qt.TextElideMode.ElideRight, int(text_width)),
            )
            y += line_height
        painter.restore()


class MiniWindow(QWidget):
    copy_requested = Signal(int)
    markdown_copy_requested = Signal(int, str)
    full_requested = Signal()
    refresh_requested = Signal()
    more_requested = Signal()
    dismissed = Signal()

    def __init__(self, model, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("preview")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setWindowTitle("ClipVault")
        self.resize(420, 480)
        self.auto_hide = False
        self._drag_origin: QPoint | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        self.list_view = QListView()
        self.list_view.setModel(model)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setMouseTracking(True)
        self.list_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.delegate = ContentDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.clicked.connect(self._copy)
        self.list_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._menu)
        self.list_view.viewport().installEventFilter(self)
        self.list_view.installEventFilter(self)
        bar = self.list_view.verticalScrollBar()
        bar.valueChanged.connect(
            lambda value: self.more_requested.emit() if value == bar.maximum() else None
        )
        layout.addWidget(self.list_view)
        self.escape = QShortcut(QKeySequence("Esc"), self)
        self.escape.activated.connect(self.dismiss_panel)
        self.enter = QShortcut(QKeySequence("Return"), self)
        self.enter.activated.connect(lambda: self._copy(self.list_view.currentIndex()))
        self.keypad_enter = QShortcut(QKeySequence("Enter"), self)
        self.keypad_enter.activated.connect(lambda: self._copy(self.list_view.currentIndex()))
        self.full_shortcut = QShortcut(QKeySequence("Alt+F"), self)
        self.full_shortcut.activated.connect(self.full_requested)

    def apply_settings(self, settings):
        self.auto_hide = settings.auto_hide
        self.setWindowOpacity(settings.opacity / 100)
        self.delegate.theme = settings.theme
        self.delegate.font_size = settings.font_size
        self.list_view.setAccessibleName(tr("Mini window"))
        self.list_view.setToolTip(
            tr("Click a clip to copy · Enter to copy · Esc to hide · Alt+F to open full window")
        )
        self.list_view.setUniformItemSizes(False)
        self.list_view.setUniformItemSizes(True)
        self.list_view.viewport().update()

    def _copy(self, index):
        if index.isValid():
            self.copy_requested.emit(index.data(Qt.ItemDataRole.UserRole).id)

    def _menu(self, position):
        index = self.list_view.indexAt(position)
        if not index.isValid():
            return
        item = index.data(Qt.ItemDataRole.UserRole)
        if item.content_type != "markdown":
            return
        menu = QMenu(self)
        for label, mode in (("Copy Markdown", "markdown"), ("Copy plain text", "plain")):
            action = menu.addAction(tr(label))
            action.triggered.connect(
                lambda checked=False, m=mode: self.markdown_copy_requested.emit(item.id, m)
            )
        menu.exec(self.list_view.viewport().mapToGlobal(position))

    def show_panel(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            self.resize(min(420, available.width()), min(480, available.height()))
            self.move(available.center() - self.rect().center())
        self.show()
        self.raise_()
        self.activateWindow()
        if self.list_view.model().rowCount() and not self.list_view.currentIndex().isValid():
            self.list_view.setCurrentIndex(self.list_view.model().index(0, 0))
        self.list_view.setFocus()
        self.refresh_requested.emit()

    def closeEvent(self, event):
        event.ignore()
        self.dismiss_panel()

    def dismiss_panel(self):
        self.hide()
        self.dismissed.emit()

    def event(self, event):
        if event.type() == QEvent.Type.WindowDeactivate and self.auto_hide:
            QTimer.singleShot(150, self._hide_if_inactive)
        return super().event(event)

    def _hide_if_inactive(self):
        if not self.isActiveWindow() and QApplication.activePopupWidget() is None:
            self.dismiss_panel()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.dismiss_panel()
                return True
            if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                self._copy(self.list_view.currentIndex())
                return True
        # Alt-drag moves the borderless window without occupying content space.
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            self._drag_origin = event.globalPosition().toPoint() - self.pos()
            return True
        if event.type() == QEvent.Type.MouseMove and self._drag_origin is not None:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
            return True
        if event.type() == QEvent.Type.MouseButtonRelease and self._drag_origin is not None:
            self._drag_origin = None
            return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss_panel()
            event.accept()
        else:
            super().keyPressEvent(event)
