from PySide6.QtGui import QColor, QPalette

PALETTES = {
    "dark": {
        "bg": "#101522",
        "sidebar": "#0c101b",
        "panel": "#161c29",
        "card": "#192130",
        "border": "#273247",
        "text": "#e6edf8",
        "muted": "#899ab4",
        "accent": "#89a5ff",
        "selected": "#273652",
        "hover": "#202c42",
        "input": "#141c2b",
        "danger": "#ff919e",
    },
    "light": {
        "bg": "#f4f6fa",
        "sidebar": "#ebeff7",
        "panel": "#ffffff",
        "card": "#ffffff",
        "border": "#dbe2ee",
        "text": "#26324a",
        "muted": "#697993",
        "accent": "#476de2",
        "selected": "#e5edff",
        "hover": "#eef2fb",
        "input": "#ffffff",
        "danger": "#ce4059",
    },
}
TYPE_COLORS = {
    "text": "#8d9fbd",
    "url": "#59c7bf",
    "python": "#f1c16d",
    "javascript": "#d9be62",
    "json": "#a899ff",
    "shell": "#7cc795",
    "sql": "#75b8f0",
    "markdown": "#87b8ff",
    "image": "#e4a4e6",
    "files": "#8ec8ad",
}


def apply_theme(application, theme: str, font_size: int):
    c = PALETTES[theme]
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, c["bg"]),
        (QPalette.ColorRole.WindowText, c["text"]),
        (QPalette.ColorRole.Base, c["panel"]),
        (QPalette.ColorRole.Text, c["text"]),
        (QPalette.ColorRole.Button, c["card"]),
        (QPalette.ColorRole.ButtonText, c["text"]),
        (QPalette.ColorRole.Highlight, c["selected"]),
        (QPalette.ColorRole.HighlightedText, c["text"]),
        (QPalette.ColorRole.PlaceholderText, c["muted"]),
        (QPalette.ColorRole.ToolTipBase, c["card"]),
        (QPalette.ColorRole.ToolTipText, c["text"]),
    ):
        palette.setColor(role, QColor(color))
    application.setPalette(palette)
    application.setStyleSheet(f"""
        QWidget {{ font-family: 'Segoe UI', 'Microsoft YaHei UI', 'Noto Sans CJK SC', 'Noto Sans', sans-serif; font-size: {font_size}px;
                   color: {c["text"]}; }}
        QMainWindow, QDialog {{ background: {c["bg"]}; }}
        QWidget#root, QWidget#workspace {{ background: {c["bg"]}; }}
        QWidget#sidebar {{ background: {c["sidebar"]}; border-right: 1px solid {c["border"]}; }}
        QLabel#brand {{ font-size: 20px; font-weight: 700; }}
        QLabel#heading {{ font-size: 25px; font-weight: 700; }}
        QLabel#sectionTitle {{ font-size: 16px; font-weight: 600; }}
        QLabel#muted, QLabel#subtitle {{ color: {c["muted"]}; }}
        QLabel#subtitle {{ font-size: {font_size}px; }}
        QLabel#eyebrow {{ color: {c["muted"]}; font-size: 10px; font-weight: 600; }}
        QLabel#badge {{ background: {c["selected"]}; color: {c["accent"]}; border-radius: 5px;
                        padding: 4px 7px; font-size: 11px; }}
        QFrame#privacyCard {{ background: {c["panel"]}; border: 1px solid {c["border"]};
                             border-radius: 12px; }}
        QToolButton#nav {{ background: transparent; text-align: left; border: 0; border-radius: 8px;
                         padding: 11px 13px; color: {c["muted"]}; }}
        QToolButton#nav:hover {{ background: {c["hover"]}; color: {c["text"]}; }}
        QToolButton#nav:checked {{ background: {c["selected"]}; color: {c["accent"]}; }}
        QPushButton, QToolButton {{ background: {c["card"]}; border: 1px solid {c["border"]};
                                  border-radius: 7px; padding: 7px 10px; min-height: 18px; }}
        QPushButton:hover, QToolButton:hover {{ background: {c["hover"]}; border-color: {c["muted"]}; }}
        QPushButton:pressed, QToolButton:pressed {{ background: {c["selected"]}; border-color: {c["accent"]}; }}
        QPushButton:focus, QToolButton:focus, QComboBox:focus, QSpinBox:focus {{ border: 1px solid {c["accent"]}; }}
        QToolButton#nav:focus {{ border: 1px solid {c["accent"]}; padding: 10px 12px; }}
        QPushButton#primary:focus, QPushButton#primary:pressed {{ border: 2px solid {c["text"]}; padding: 8px; }}
        QPushButton:checked {{ background: {c["selected"]}; color: {c["accent"]}; }}
        QPushButton:disabled, QToolButton:disabled {{ color: {c["muted"]}; }}
        QPushButton#primary {{ background: {c["accent"]}; border: 0; color: {"#101522" if theme == "dark" else "#ffffff"};
                               font-weight: 600; padding: 10px; }}
        QPushButton#primary:hover {{ background: {"#a6bbff" if theme == "dark" else "#355ac5"}; }}
        QPushButton#danger {{ color: {c["danger"]}; }}
        QLineEdit, QComboBox, QSpinBox, QKeySequenceEdit {{ background: {c["input"]};
            border: 1px solid {c["border"]}; border-radius: 7px; padding: 8px; selection-background-color: {c["selected"]}; }}
        QLineEdit:focus, QKeySequenceEdit:focus {{ border-color: {c["accent"]}; }}
        QComboBox::drop-down {{ border: 0; width: 24px; }}
        QComboBox QAbstractItemView {{ background: {c["card"]}; selection-background-color: {c["selected"]}; }}
        QListView, QListWidget {{ background: transparent; border: 0; outline: 0; }}
        QWidget#preview {{ background: {c["panel"]}; border: 1px solid {c["border"]}; border-radius: 12px; }}
        QTextBrowser, QPlainTextEdit {{ background: {c["panel"]}; border: 0; padding: 4px; }}
        QSplitter::handle {{ background: transparent; width: 14px; }}
        QStatusBar {{ background: {c["sidebar"]}; border-top: 1px solid {c["border"]};
                     color: {c["muted"]}; font-size: 11px; padding: 4px 14px; }}
        QStatusBar::item {{ border: 0; }}
        QLabel#status {{ color: {c["muted"]}; font-size: 11px; }}
        QLabel#notice {{ background: {c["selected"]}; color: {c["accent"]}; border-radius: 7px;
                         padding: 8px 12px; }}
        QScrollBar:vertical {{ background: transparent; width: 6px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {c["border"]}; border-radius: 3px; min-height: 25px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
        QScrollBar:horizontal {{ height: 6px; background: transparent; }}
        QScrollBar::handle:horizontal {{ background: {c["border"]}; border-radius: 3px; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        QCheckBox {{ spacing: 9px; }}
        QCheckBox:focus {{ color: {c["accent"]}; }}
        QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {c["muted"]}; }}
        QCheckBox::indicator:checked {{ background: {c["accent"]}; border: 1px solid {c["accent"]}; }}
        QSlider::groove:horizontal {{ height: 4px; background: {c["border"]}; border-radius: 2px; }}
        QSlider::sub-page:horizontal {{ background: {c["accent"]}; border-radius: 2px; }}
        QSlider::handle:horizontal {{ background: {c["accent"]}; width: 14px; margin: -5px 0; border-radius: 7px; }}
        QScrollArea {{ border: 0; background: transparent; }}
        QMenu {{ background: {c["panel"]}; border: 1px solid {c["border"]}; padding: 5px; }}
        QMenu::item {{ padding: 7px 20px; border-radius: 4px; }}
        QMenu::item:selected {{ background: {c["selected"]}; }}
        QToolTip {{ background: {c["card"]}; border: 1px solid {c["border"]}; padding: 5px; }}
    """)
