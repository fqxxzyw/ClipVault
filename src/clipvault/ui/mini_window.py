"""Content-only quick picker sharing the paginated history model."""

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListView,
    QMenu,
    QSlider,
    QStyle,
    QStyledItemDelegate,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from clipvault.ui.i18n import tr
from clipvault.ui.icons import icon, thumbnail_icon
from clipvault.ui.motion import system_reduces_motion
from clipvault.ui.styles import PALETTES
from clipvault.ui.windows_frame import apply_windows_frame


class ContentDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = "dark"
        self.font_size = 13
        self.glass = False

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
        fill = QColor(c["selected"] if selected else c["hover"] if hovered else c["card"])
        fill.setAlpha(195 if self.glass else 255)
        painter.setBrush(fill)
        painter.setPen(QPen(QColor(c["accent"] if selected else c["border"]), 1))
        painter.drawRoundedRect(rect, 14, 14)
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
    preferences_requested = Signal(object)
    geometry_changed = Signal(object)

    def __init__(self, model, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("miniWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setWindowTitle("ClipVault")
        self.setMinimumSize(240, 160)
        self.resize(420, 480)
        self.auto_hide = False
        self.settings = None
        self._positioned = False
        self._restoring = False
        self._press = None
        self._press_geometry = None
        self._edges = Qt.Edge(0)
        self._dragging = False
        self._native_gesture = False
        self._glow = QPointF(60, 40)
        self._glass_native = False
        self.geometry_timer = QTimer(self)
        self.geometry_timer.setInterval(400)
        self.geometry_timer.setSingleShot(True)
        self.geometry_timer.timeout.connect(self._remember)
        self.glow_animation = QVariantAnimation(self)
        self.glow_animation.setDuration(160)
        self.glow_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.glow_animation.valueChanged.connect(self._set_glow)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(5)
        self.header = QWidget()
        self.header.setObjectName("miniHeader")
        self.header.setMouseTracking(True)
        self.header.installEventFilter(self)
        row = QHBoxLayout(self.header)
        row.setContentsMargins(6, 0, 0, 0)
        self.grip = QLabel("⠿  ClipVault")
        self.grip.setObjectName("miniTitle")
        self.grip.setMouseTracking(True)
        self.grip.installEventFilter(self)
        row.addWidget(self.grip)
        row.addStretch()
        self.pin_button = self._tool("pin", "Always on top", row)
        self.pin_button.setCheckable(True)
        self.pin_button.clicked.connect(
            lambda checked: self.preferences_requested.emit({"mini_topmost": checked})
        )
        self.options_button = self._tool("settings", "Mini window appearance", row)
        self.options_button.clicked.connect(lambda: self._menu(None))
        self.full_button = self._tool("external", "Full window", row)
        self.full_button.clicked.connect(self.full_requested)
        self.close_button = self._tool("close", "Close", row)
        self.close_button.clicked.connect(self.dismiss_panel)
        layout.addWidget(self.header)
        self.list_view = QListView()
        self.list_view.setModel(model)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setMouseTracking(True)
        self.list_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.delegate = ContentDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
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
        self.full_shortcut = QShortcut(QKeySequence("Alt+F"), self)
        self.full_shortcut.activated.connect(self.full_requested)

    def _tool(self, glyph, label, layout):
        button = QToolButton()
        button.setIcon(icon(glyph))
        button.setProperty("miniLabel", label)
        button.setFixedSize(28, 28)
        button.setObjectName("miniTool")
        button.setToolTip(tr(label))
        button.setAccessibleName(tr(label))
        layout.addWidget(button)
        return button

    def apply_settings(self, settings):
        visible = self.isVisible()
        self._restoring = True
        self.settings = settings
        self.auto_hide = settings.auto_hide and not settings.mini_topmost
        if bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint) != settings.mini_topmost:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, settings.mini_topmost)
        self.pin_button.setChecked(settings.mini_topmost)
        self.setWindowOpacity(settings.mini_opacity / 100)
        self.delegate.theme = settings.theme
        self.delegate.font_size = settings.font_size
        self.delegate.glass = settings.mini_glass
        self.list_view.setAccessibleName(tr("Mini window"))
        self.list_view.setToolTip(
            tr("Drag to move · Drag edges to resize · Click to copy · Enter / Esc")
        )
        for button in (self.pin_button, self.options_button, self.full_button, self.close_button):
            button.setToolTip(tr(button.property("miniLabel")))
            button.setAccessibleName(button.toolTip())
        if settings.mini_geometry and not self._positioned:
            self.setGeometry(QRect(*settings.mini_geometry))
            self._positioned = True
        if settings.reduce_motion or system_reduces_motion():
            self.glow_animation.stop()
        self.list_view.setUniformItemSizes(False)
        self.list_view.setUniformItemSizes(True)
        self._glass_native = apply_windows_frame(
            self, dark=settings.theme == "dark", glass=settings.mini_glass, mini=True
        )
        self._restoring = False
        if visible:
            self.show()
        self.update()
        self.list_view.viewport().update()

    def paintEvent(self, event):
        dark = not self.settings or self.settings.theme == "dark"
        glass = self.settings is not None and self.settings.mini_glass
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 18, 18)
        painter.setClipPath(path)
        tint = QColor("#141d31" if dark else "#edf3fc")
        tint.setAlpha(180 if glass else 255)
        painter.fillPath(path, tint)
        if glass:
            sheen = QLinearGradient(0, 0, self.width(), self.height())
            sheen.setColorAt(0, QColor(210, 229, 255, 36 if dark else 110))
            sheen.setColorAt(0.45, QColor(128, 167, 255, 9))
            sheen.setColorAt(1, QColor(111, 215, 206, 26))
            painter.fillPath(path, sheen)
            halo = QRadialGradient(self._glow, 190)
            halo.setColorAt(0, QColor(174, 204, 255, 25 if dark else 38))
            halo.setColorAt(0.6, QColor(150, 190, 255, 8))
            halo.setColorAt(1, QColor(150, 190, 255, 0))
            painter.fillPath(path, halo)
        painter.setClipping(False)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor(215, 232, 255, 65 if dark else 185), 1))
        painter.drawRoundedRect(rect, 18, 18)
        painter.setPen(QPen(QColor(255, 255, 255, 42 if glass else 12), 1))
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 17, 17)

    def _set_glow(self, point):
        self._glow = point
        self.update()

    def _copy(self, index):
        if index.isValid():
            self.copy_requested.emit(index.data(Qt.ItemDataRole.UserRole).id)

    def _menu(self, position):
        menu = QMenu(self)
        index = (
            self.list_view.indexAt(position)
            if position is not None
            else self.list_view.currentIndex()
        )
        if index.isValid() and index.data(Qt.ItemDataRole.UserRole).content_type == "markdown":
            item = index.data(Qt.ItemDataRole.UserRole)
            for label, mode in (("Copy Markdown", "markdown"), ("Copy plain text", "plain")):
                action = menu.addAction(tr(label))
                action.triggered.connect(
                    lambda checked=False, m=mode: self.markdown_copy_requested.emit(item.id, m)
                )
            menu.addSeparator()
        pin = menu.addAction(tr("Always on top"))
        pin.setCheckable(True)
        pin.setChecked(self.settings.mini_topmost)
        pin.triggered.connect(
            lambda value: self.preferences_requested.emit({"mini_topmost": value})
        )
        glass = menu.addAction(tr("Liquid glass appearance"))
        glass.setCheckable(True)
        glass.setChecked(self.settings.mini_glass)
        glass.triggered.connect(
            lambda value: self.preferences_requested.emit({"mini_glass": value})
        )
        panel = QWidget()
        layout = QVBoxLayout(panel)
        label = QLabel(tr("Mini opacity") + f" · {self.settings.mini_opacity}%")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(40, 100)
        slider.setValue(self.settings.mini_opacity)
        slider.setAccessibleName(tr("Mini opacity"))
        slider.valueChanged.connect(
            lambda value: (
                label.setText(tr("Mini opacity") + f" · {value}%"),
                self.preferences_requested.emit({"mini_opacity": value}),
            )
        )
        layout.addWidget(label)
        layout.addWidget(slider)
        action = QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        menu.addSeparator()
        menu.addAction(tr("Reset size and position"), self.reset_geometry)
        menu.addAction(tr("Full window"), self.full_requested.emit)
        point = (
            self.list_view.viewport().mapToGlobal(position)
            if position is not None
            else self.options_button.mapToGlobal(self.options_button.rect().bottomLeft())
        )
        menu.exec(point)

    def reset_geometry(self):
        self._positioned = False
        self.resize(420, 480)
        self.show_panel()
        self._remember()

    def show_panel(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            if not self._positioned:
                self.resize(min(420, available.width()), min(480, available.height()))
                self.move(available.center() - self.rect().center())
                self._positioned = True
            elif not any(
                s.availableGeometry().intersects(self.geometry()) for s in QApplication.screens()
            ):
                self.move(available.center() - self.rect().center())
        self.show()
        self.raise_()
        self.activateWindow()
        if self.list_view.model().rowCount() and not self.list_view.currentIndex().isValid():
            self.list_view.setCurrentIndex(self.list_view.model().index(0, 0))
        self.list_view.setFocus()
        self.refresh_requested.emit()

    def showEvent(self, event):
        super().showEvent(event)
        if self.settings:
            self._glass_native = apply_windows_frame(
                self, dark=self.settings.theme == "dark", glass=self.settings.mini_glass, mini=True
            )

    def _remember(self):
        if self._positioned and not self._restoring:
            self.geometry_changed.emit((self.x(), self.y(), self.width(), self.height()))

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "geometry_timer") and not self._restoring:
            self.geometry_timer.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "geometry_timer") and not self._restoring:
            self.geometry_timer.start()

    def closeEvent(self, event):
        event.ignore()
        self.dismiss_panel()

    def dismiss_panel(self):
        self.glow_animation.stop()
        self._remember()
        self.hide()
        self.dismissed.emit()

    def event(self, event):
        if event.type() == QEvent.Type.WindowDeactivate and self.auto_hide:
            QTimer.singleShot(150, self._hide_if_inactive)
        return super().event(event)

    def _hide_if_inactive(self):
        if (
            self.auto_hide
            and not self.isActiveWindow()
            and QApplication.activePopupWidget() is None
        ):
            self.dismiss_panel()

    def _hit_edges(self, point):
        edges = Qt.Edge(0)
        if point.x() < 8:
            edges |= Qt.Edge.LeftEdge
        elif point.x() >= self.width() - 8:
            edges |= Qt.Edge.RightEdge
        if point.y() < 8:
            edges |= Qt.Edge.TopEdge
        elif point.y() >= self.height() - 8:
            edges |= Qt.Edge.BottomEdge
        return edges

    def _mouse(self, event, point, *, viewport=False):
        kind = event.type()
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self._press = event.globalPosition().toPoint()
            self._press_geometry = self.geometry()
            self._edges = self._hit_edges(point)
            self._dragging = bool(self._edges)
            self._native_gesture = False
            if viewport:
                index = self.list_view.indexAt(event.position().toPoint())
                if index.isValid():
                    self.list_view.setCurrentIndex(index)
            if self._edges and self.windowHandle():
                self._native_gesture = self.windowHandle().startSystemResize(self._edges)
            return True
        if kind == QEvent.Type.MouseMove:
            if self._press is not None:
                delta = event.globalPosition().toPoint() - self._press
                if (
                    not self._dragging
                    and delta.manhattanLength() >= QApplication.startDragDistance()
                ):
                    self._dragging = True
                    if self.windowHandle():
                        self._native_gesture = self.windowHandle().startSystemMove()
                if self._dragging and not self._native_gesture:
                    geometry = QRect(self._press_geometry)
                    if self._edges:
                        if self._edges & Qt.Edge.LeftEdge:
                            geometry.setLeft(
                                min(
                                    geometry.right() - self.minimumWidth() + 1,
                                    geometry.left() + delta.x(),
                                )
                            )
                        if self._edges & Qt.Edge.RightEdge:
                            geometry.setRight(
                                max(
                                    geometry.left() + self.minimumWidth() - 1,
                                    geometry.right() + delta.x(),
                                )
                            )
                        if self._edges & Qt.Edge.TopEdge:
                            geometry.setTop(
                                min(
                                    geometry.bottom() - self.minimumHeight() + 1,
                                    geometry.top() + delta.y(),
                                )
                            )
                        if self._edges & Qt.Edge.BottomEdge:
                            geometry.setBottom(
                                max(
                                    geometry.top() + self.minimumHeight() - 1,
                                    geometry.bottom() + delta.y(),
                                )
                            )
                        self.setGeometry(geometry)
                    else:
                        self.move(self._press_geometry.topLeft() + delta)
                return True
            edges = self._hit_edges(point)
            if edges in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif edges in (Qt.Edge.TopEdge, Qt.Edge.BottomEdge):
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif edges:
                self.setCursor(
                    Qt.CursorShape.SizeFDiagCursor
                    if edges
                    in (Qt.Edge.LeftEdge | Qt.Edge.TopEdge, Qt.Edge.RightEdge | Qt.Edge.BottomEdge)
                    else Qt.CursorShape.SizeBDiagCursor
                )
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            if (
                self.settings
                and self.settings.mini_glass
                and not self.settings.reduce_motion
                and not system_reduces_motion()
            ):
                self.glow_animation.stop()
                self.glow_animation.setStartValue(self._glow)
                self.glow_animation.setEndValue(QPointF(point))
                self.glow_animation.start()
            return False
        if (
            kind == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
            and self._press is not None
        ):
            click = not self._dragging
            self._press = None
            self._dragging = False
            self._native_gesture = False
            if click and viewport:
                self._copy(self.list_view.indexAt(event.position().toPoint()))
            else:
                self._remember()
            return True
        return False

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.dismiss_panel()
                return True
            if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                self._copy(self.list_view.currentIndex())
                return True
        if event.type() in {
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonRelease,
        }:
            point = watched.mapTo(self, event.position().toPoint())
            return self._mouse(event, point, viewport=watched is self.list_view.viewport())
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event):
        self._mouse(event, event.position().toPoint())

    def mouseMoveEvent(self, event):
        self._mouse(event, event.position().toPoint())

    def mouseReleaseEvent(self, event):
        self._mouse(event, event.position().toPoint())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss_panel()
            event.accept()
        else:
            super().keyPressEvent(event)
