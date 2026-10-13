from datetime import datetime

from PySide6.QtCore import QAbstractListModel, QModelIndex, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from clipvault.database.models import TYPE_LABELS, ClipSummary
from clipvault.ui.i18n import tr
from clipvault.ui.icons import icon, thumbnail_icon
from clipvault.ui.styles import PALETTES, TYPE_COLORS


def relative_time(timestamp: str) -> str:
    try:
        date = datetime.fromisoformat(timestamp)
        age = max((datetime.now(date.tzinfo) - date).total_seconds(), 0)
        if age < 60:
            return tr("Just now")
        if age < 3600:
            return tr("{count}m ago", count=int(age // 60))
        if age < 86400:
            return tr("{count}h ago", count=int(age // 3600))
        return date.astimezone().strftime("%m/%d %H:%M")
    except ValueError:
        return ""


class ClipListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.items: list[ClipSummary] = []

    def rowCount(self, parent=None):
        parent = QModelIndex() if parent is None else parent
        return 0 if parent.isValid() else len(self.items)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.items):
            return None
        item = self.items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return item.preview
        if role == Qt.ItemDataRole.UserRole:
            return item
        if role == Qt.ItemDataRole.AccessibleTextRole:
            return f"{tr(TYPE_LABELS[item.content_type])}: {item.preview}"
        return None

    def replace(self, items):
        self.beginResetModel()
        self.items = list(items)
        self.endResetModel()

    def append(self, items):
        if not items:
            return
        start = len(self.items)
        self.beginInsertRows(QModelIndex(), start, start + len(items) - 1)
        self.items.extend(items)
        self.endInsertRows()


class ClipCardDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = "dark"
        self.font_size = 13

    def sizeHint(self, option, index):
        return QSize(280, 112 + (self.font_size - 13) * 3)

    def paint(self, painter: QPainter, option, index):
        item = index.data(Qt.ItemDataRole.UserRole)
        if not item:
            return
        colors = PALETTES[self.theme]
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        rect = QRectF(option.rect).adjusted(0, 3, -5, -5)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(
            QColor(
                colors["selected"] if selected else colors["hover"] if hovered else colors["card"]
            )
        )
        painter.setPen(QPen(QColor(colors["accent"] if selected else colors["border"]), 1))
        painter.drawRoundedRect(rect, 10, 10)
        left, top, width = rect.x() + 13, rect.y() + 12, rect.width() - 26
        font = QFont("Segoe UI", 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(TYPE_COLORS[item.content_type]))
        tag = tr(TYPE_LABELS[item.content_type]).upper()
        if item.is_pinned:
            tag += "  · " + tr("Pinned").upper()
        if item.is_favorite:
            tag += "  ★"
        painter.drawText(QRectF(left, top, width, 16), Qt.AlignmentFlag.AlignLeft, tag)
        font.setBold(False)
        font.setPixelSize(self.font_size)
        painter.setFont(font)
        painter.setPen(QColor(colors["text"]))
        if item.content_type in {"image", "files"}:
            glyph = (
                thumbnail_icon(item.thumbnail)
                if item.thumbnail
                else icon("file" if item.content_type == "files" else "image")
            )
            glyph.paint(painter, int(left), int(top + 23), 42, 42)
            left += 53
            width -= 53
        lines = item.preview.replace("\r", "").splitlines() or [""]
        first = lines[0].strip() or "…"
        second = next((line.strip() for line in lines[1:] if line.strip()), "")
        if not second and len(first) > 40:
            second = first[40:]
            first = first[:40]
        metrics = painter.fontMetrics()
        painter.drawText(
            QRectF(left, top + 25, width, 19),
            Qt.AlignmentFlag.AlignLeft,
            metrics.elidedText(first, Qt.TextElideMode.ElideRight, int(width)),
        )
        painter.setPen(QColor(colors["muted"]))
        painter.drawText(
            QRectF(left, top + 45, width, 19),
            Qt.AlignmentFlag.AlignLeft,
            metrics.elidedText(second, Qt.TextElideMode.ElideRight, int(width)),
        )
        font.setPixelSize(10)
        painter.setFont(font)
        footer = relative_time(item.updated_at)
        if item.content_type not in {"image", "files"}:
            footer += "  ·  " + tr("{count:,} characters", count=item.char_count)
        painter.drawText(
            QRectF(left, rect.bottom() - 22, width, 14),
            Qt.AlignmentFlag.AlignLeft,
            footer,
        )
        painter.restore()
