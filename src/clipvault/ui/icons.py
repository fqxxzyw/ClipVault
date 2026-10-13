from functools import lru_cache

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

PATHS = {
    "file": '<path d="M6 2h8l4 4v16H6ZM14 2v5h4M9 12h6M9 16h6"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="2"/><path d="m3 18 6-6 4 4 4-6 4 7"/>',
    "stats": '<path d="M4 20h17M7 20V10h3v10M13 20V4h3v16M19 20v-7"/>',
    "emoji": '<circle cx="12" cy="12" r="9"/><path d="M7 14c3 4 7 4 10 0M8 8v2m8-2v2"/>',
    "mini": '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M3 9h18M13 13h5v4h-5Z"/>',
    "clipboard": '<rect x="5" y="5" width="14" height="16" rx="3"/><rect x="8" y="3" width="8" height="4" rx="2"/><path d="M9 11h6m-6 4h4"/>',
    "star": '<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',
    "pin": '<path d="m9 3 6 0-1 6 4 4v2H6v-2l4-4ZM12 15v7"/>',
    "settings": '<path d="m9 3 1-1h4l1 3 3 1 3 3-2 3 1 3-3 3-3-1-2 3H9l-1-3-3-1-3-3 2-3-1-3 3-3Z"/><circle cx="12" cy="11" r="3"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "play": '<path d="m8 4 12 8-12 8Z"/>',
    "copy": '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
    "trash": '<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
    "external": '<path d="M14 3h7v7m0-7L10 14M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
    "code": '<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-15-2 18"/>',
    "shield": '<path d="M12 2 3 6v6c0 5 9 10 9 10s9-5 9-10V6ZM8 12l3 3 5-6"/>',
    "text": '<path d="M4 5h16M12 5v15m-5 0h10"/>',
    "link": '<path d="m10 8 3-3a5 5 0 0 1 7 7l-3 3m-3 1-3 3a5 5 0 0 1-7-7l3-3m1 6 8-8"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
    "check": '<path d="m4 12 5 5L20 6"/>',
    "folder": '<path d="M3 6h6l2 3h10v11H3Z"/>',
    "close": '<path d="m6 6 12 12M6 18 18 6"/>',
    "sort": '<path d="M5 4v16m-3-3 3 3 3-3M12 5h9m-9 5h7m-7 5h5"/>',
    "refresh": '<path d="M20 7a9 9 0 1 0 1 7M20 2v6h-6"/>',
}


@lru_cache(maxsize=128)
def icon(name: str, color: str = "#aab8ce", size: int = 24) -> QIcon:
    drawing = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
        f'<g fill="none" stroke="{color}" stroke-width="1.65" '
        f'stroke-linecap="round" stroke-linejoin="round">{PATHS[name]}</g></svg>'
    )
    image = QImage(size * 2, size * 2, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    QSvgRenderer(QByteArray(drawing.encode())).render(painter)
    painter.end()
    pixmap = QPixmap.fromImage(image)
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


@lru_cache(maxsize=128)
def thumbnail_icon(data: bytes) -> QIcon:
    return QIcon(QPixmap.fromImage(QImage.fromData(data, "PNG")))
