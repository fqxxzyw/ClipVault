from datetime import UTC, datetime, time, timedelta

from PySide6.QtCore import QDate, QEvent, QItemSelectionModel, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from clipvault import __version__
from clipvault.database.models import CONTENT_TYPES, TYPE_LABELS, SearchPage, SearchRequest
from clipvault.ui.clip_card import ClipCardDelegate, ClipListModel
from clipvault.ui.history_view import HistoryView
from clipvault.ui.i18n import set_language, tr, translate_widgets
from clipvault.ui.icons import icon
from clipvault.ui.motion import Motion, system_reduces_motion
from clipvault.ui.preview_panel import PreviewPanel
from clipvault.ui.settings_page import SettingsPage
from clipvault.ui.tools_pages import EmojiPage, StatisticsPage
from clipvault.ui.windows_frame import apply_windows_frame
from clipvault.utils.settings import Settings


class MainWindow(QMainWindow):
    search_requested = Signal(object)
    selected = Signal(int)
    copy_requested = Signal(int)
    batch_copy_requested = Signal(object)
    panel_hidden = Signal()
    pause_requested = Signal()
    quit_requested = Signal()
    mini_requested = Signal()

    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.scope = "all"
        self.quick_mode = False
        self.tray_available = False
        self.search_busy = False
        self._has_more = False
        self._selected_id: int | None = None
        self._mutating_list = False
        self._counts = (0, 0)
        self._listener_status = "listening"
        self._last_clip_scope = "all"
        self.motion = Motion(self)
        self.setWindowTitle("ClipVault — Your Clipboard. Your Control.")
        self.resize(900, 620)
        self.setMinimumSize(820, 540)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(173)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(13, 23, 13, 20)
        side.setSpacing(6)
        brand_row = QHBoxLayout()
        logo = QLabel()
        logo.setFixedSize(28, 28)
        logo.setPixmap(icon("clipboard", "#89a5ff", 28).pixmap(QSize(28, 28)))
        brand = QLabel("ClipVault")
        brand.setObjectName("brand")
        brand_row.addWidget(logo)
        brand_row.addWidget(brand)
        side.addLayout(brand_row)
        tagline = QLabel("Your clipboard.\nUnder your control.")
        tagline.setObjectName("muted")
        tagline.setContentsMargins(5, 7, 0, 25)
        side.addWidget(tagline)
        label = QLabel("WORKSPACE")
        label.setObjectName("eyebrow")
        label.setContentsMargins(12, 0, 0, 4)
        side.addWidget(label)
        self.nav_group = QButtonGroup(self)
        self.nav_buttons = {}
        for scope, title, glyph in (
            ("all", "All Clips", "clipboard"),
            ("favorites", "Favorites", "star"),
            ("pinned", "Pinned", "pin"),
            ("stats", "Statistics", "stats"),
            ("emoji", "Emoji", "emoji"),
            ("settings", "Settings", "settings"),
        ):
            button = QToolButton()
            button.setText(title)
            button.setIcon(icon(glyph))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setObjectName("nav")
            button.setCheckable(True)
            button.setMinimumWidth(143)
            button.clicked.connect(lambda checked=False, value=scope: self.navigate(value))
            self.nav_group.addButton(button)
            self.nav_buttons[scope] = button
            side.addWidget(button)
        self.nav_buttons["all"].setChecked(True)
        side.addStretch()
        privacy = QFrame()
        privacy.setObjectName("privacyCard")
        privacy_layout = QVBoxLayout(privacy)
        privacy_layout.setContentsMargins(12, 13, 12, 12)
        shield = QLabel()
        shield.setPixmap(icon("shield", "#79c8aa", 22).pixmap(QSize(22, 22)))
        privacy_layout.addWidget(shield)
        privacy_layout.addWidget(QLabel("Local by design"))
        small = QLabel("Offline. On your device.")
        small.setWordWrap(True)
        small.setObjectName("muted")
        privacy_layout.addWidget(small)
        side.addWidget(privacy)
        version = QLabel(f"CLIPVAULT  /  {__version__}")
        version.setObjectName("eyebrow")
        version.setContentsMargins(8, 14, 0, 0)
        side.addWidget(version)
        main_layout.addWidget(sidebar)

        workspace = QWidget()
        workspace.setObjectName("workspace")
        body = QVBoxLayout(workspace)
        body.setContentsMargins(23, 22, 23, 14)
        body.setSpacing(15)
        top = QHBoxLayout()
        headings = QVBoxLayout()
        headings.setSpacing(4)
        self.heading = QLabel("Clipboard")
        self.heading.setObjectName("heading")
        self.subtitle = QLabel("Capture once. Find it instantly.")
        self.subtitle.setObjectName("subtitle")
        headings.addWidget(self.heading)
        headings.addWidget(self.subtitle)
        top.addLayout(headings)
        top.addStretch()
        self.pause = QPushButton("Pause")
        self.pause.setIcon(icon("pause"))
        self.pause.setToolTip("Pause recording before copying sensitive information")
        self.pause.clicked.connect(self.pause_requested)
        self.mini = QPushButton("Mini window")
        self.mini.setIcon(icon("mini"))
        self.mini.setToolTip("Open mini window")
        self.mini.clicked.connect(self.mini_requested)
        top.addWidget(self.mini)
        top.addWidget(self.pause)
        body.addLayout(top)
        self.notice = QLabel()
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        self.notice.hide()
        body.addWidget(self.notice)
        self.notice_timer = QTimer(self)
        self.notice_timer.setSingleShot(True)
        self.notice_timer.timeout.connect(self.notice.hide)

        self.stack = QStackedWidget()
        clips_page = QWidget()
        clips_layout = QVBoxLayout(clips_page)
        clips_layout.setContentsMargins(0, 0, 0, 0)
        clips_layout.setSpacing(13)
        tools = QHBoxLayout()
        tools.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search clips…")
        self.search.setMaxLength(512)
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        self.search.installEventFilter(self)
        tools.addWidget(self.search, 1)
        self.type_filter = QComboBox()
        self.type_filter.addItem("All types", "all")
        self.type_filter.addItem("Code", "code")
        for content_type in CONTENT_TYPES:
            self.type_filter.addItem(TYPE_LABELS[content_type], content_type)
        self.type_filter.setMinimumWidth(104)
        tools.addWidget(self.type_filter)
        self.sort = QPushButton()
        self.sort.setIcon(icon("sort"))
        self.sort.setCheckable(True)
        self.sort.setToolTip("Newest first · click for oldest first (pins remain first)")
        tools.addWidget(self.sort)
        self.retry = QPushButton()
        self.retry.setIcon(icon("refresh"))
        self.retry.setToolTip("Refresh history")
        self.retry.clicked.connect(self.refresh)
        tools.addWidget(self.retry)
        clips_layout.addLayout(tools)
        self.date_range_widget = QWidget()
        self.date_range_widget.hide()
        dates = QHBoxLayout(self.date_range_widget)
        dates.setContentsMargins(0, 0, 0, 0)
        dates.setSpacing(8)
        self.date_filter = QComboBox()
        for title, value in (
            ("All dates", 0),
            ("Today", 1),
            ("Last 7 days", 7),
            ("Last 30 days", 30),
            ("Custom range", -1),
        ):
            self.date_filter.addItem(title, value)
        tools.insertWidget(2, self.date_filter)
        self.date_from = QDateEdit(QDate.currentDate().addDays(-6))
        self.date_to = QDateEdit(QDate.currentDate())
        for edit in (self.date_from, self.date_to):
            edit.setCalendarPopup(True)
            edit.setDisplayFormat("yyyy-MM-dd")
            edit.setMaximumDate(QDate.currentDate().addYears(1))
            edit.setMinimumDate(QDate(2000, 1, 1))
            edit.hide()
            dates.addWidget(edit)
        self.date_from.setAccessibleName(tr("From"))
        self.date_to.setAccessibleName(tr("Through"))
        dates.addStretch()
        clips_layout.addWidget(self.date_range_widget)
        self.date_filter.currentIndexChanged.connect(self._dates_changed)
        self.date_from.dateChanged.connect(lambda: self.refresh())
        self.date_to.dateChanged.connect(lambda: self.refresh())
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(7)
        self.results_label = QLabel("RECENT CLIPS")
        self.results_label.setObjectName("eyebrow")
        left_layout.addWidget(self.results_label)
        self.model = ClipListModel(self)
        self.list_view = HistoryView()
        self.list_view.setModel(self.model)
        self.list_view.setAccessibleName(tr("History list"))
        self.list_view.setMouseTracking(True)
        self.list_view.setUniformItemSizes(True)
        self.list_view.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_view.setMinimumWidth(255)
        self.delegate = ClipCardDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.selectionModel().currentChanged.connect(self._select)
        self.list_view.doubleClicked.connect(self._double_click)
        self.list_view.installEventFilter(self)
        left_layout.addWidget(self.list_view, 1)
        self.empty = QLabel("No clips yet. Copy some text to begin.")
        self.empty.setWordWrap(True)
        self.empty.setObjectName("muted")
        left_layout.addWidget(self.empty)
        self.load_more = QPushButton("Load more")
        self.load_more.clicked.connect(self._load_more)
        self.load_more.hide()
        left_layout.addWidget(self.load_more)
        splitter.addWidget(left)
        self.preview = PreviewPanel()
        splitter.addWidget(self.preview)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([310, 335])
        view_tools = QHBoxLayout()
        view_tools.setSpacing(6)
        self.list_mode = QPushButton("List")
        self.grid_mode = QPushButton("Grid")
        self.list_mode.setIcon(icon("list"))
        self.grid_mode.setIcon(icon("grid"))
        for button in (self.list_mode, self.grid_mode):
            button.setCheckable(True)
            view_tools.addWidget(button)
        self.view_group = QButtonGroup(self)
        self.view_group.addButton(self.list_mode)
        self.view_group.addButton(self.grid_mode)
        self.list_mode.setChecked(True)
        self.list_mode.clicked.connect(lambda: self.list_view.set_grid_mode(False))
        self.grid_mode.clicked.connect(lambda: self.list_view.set_grid_mode(True))
        view_tools.addStretch()
        self.batch_select = QPushButton("Select")
        self.batch_select.setProperty("i18nSkip", True)
        self.batch_select.setIcon(icon("select"))
        self.batch_select.setCheckable(True)
        self.batch_select.toggled.connect(self._set_batch_mode)
        view_tools.addWidget(self.batch_select)
        self.select_all = QPushButton("Select loaded")
        self.select_all.clicked.connect(self.list_view.selectAll)
        self.select_all.hide()
        view_tools.addWidget(self.select_all)
        self.batch_copy = QPushButton()
        self.batch_copy.setProperty("i18nSkip", True)
        self.batch_copy.setObjectName("primary")
        self.batch_copy.clicked.connect(self._copy_selection)
        self.batch_copy.hide()
        view_tools.addWidget(self.batch_copy)
        self.list_view.selection_count_changed.connect(self._selection_count_changed)
        self._selection_count_changed(0)
        clips_layout.addLayout(view_tools)
        clips_layout.addWidget(splitter, 1)
        self.stack.addWidget(clips_page)
        self.settings_page = SettingsPage(settings)
        self.stack.addWidget(self.settings_page)
        self.statistics_page = StatisticsPage()
        self.stack.addWidget(self.statistics_page)
        self.emoji_page = EmojiPage()
        self.stack.addWidget(self.emoji_page)
        body.addWidget(self.stack, 1)
        main_layout.addWidget(workspace, 1)
        self.count_label = QLabel("0 clips")
        self.count_label.setObjectName("status")
        self.listener_label = QLabel("●  Starting…")
        self.listener_label.setObjectName("status")
        self.hotkey_label = QLabel()
        self.hotkey_label.setObjectName("status")
        self.statusBar().setSizeGripEnabled(False)
        self.statusBar().addWidget(self.count_label)
        self.statusBar().addWidget(self.listener_label)
        self.statusBar().addPermanentWidget(self.hotkey_label)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(180)
        self.debounce.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.debounce.start())
        self.type_filter.currentIndexChanged.connect(lambda: self.refresh())
        self.sort.toggled.connect(lambda: self.refresh())
        self.escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.escape.activated.connect(self.dismiss_panel)
        self.apply_settings(settings)

    def apply_settings(self, settings: Settings):
        self.settings = settings
        apply_windows_frame(self, dark=settings.theme == "dark", glass=True)
        set_language(settings.language)
        self.motion.configure(settings.reduce_motion)
        for effect in (
            Qt.UIEffect.UI_FadeMenu,
            Qt.UIEffect.UI_AnimateCombo,
            Qt.UIEffect.UI_FadeTooltip,
            Qt.UIEffect.UI_AnimateToolBox,
        ):
            QApplication.setEffectEnabled(
                effect, not settings.reduce_motion and not system_reduces_motion()
            )
        for widget in (
            self.heading,
            self.subtitle,
            self.pause,
            self.count_label,
            self.listener_label,
            self.hotkey_label,
            self.results_label,
            self.empty,
            self.notice,
            self.preview.special,
        ):
            widget.setProperty("i18nSkip", True)
        self.type_filter.blockSignals(True)
        translate_widgets(self)
        self.type_filter.blockSignals(False)
        self._translate_dynamic()
        self.list_view.setAccessibleName(tr("History list"))
        self.preview.browser.setAccessibleName(tr("Preview"))
        self.preview.copy.setIcon(
            icon("copy", "#101522" if settings.theme == "dark" else "#ffffff")
        )
        self.preview.language.setAccessibleName(tr("Content language"))
        self.preview.md_view.setAccessibleName(tr("Markdown preview mode"))
        self.preview.md_copy.setAccessibleName(tr("Markdown copy format"))
        self.date_from.setAccessibleName(tr("From"))
        self.date_to.setAccessibleName(tr("Through"))
        self.emoji_page.retranslate()
        self.preview.set_clip(self.preview.clip, self.preview.rendered, self.preview.image)
        self.setWindowOpacity(settings.opacity / 100)
        self.delegate.theme = settings.theme
        self.delegate.font_size = settings.font_size
        self.list_view.setUniformItemSizes(False)
        self.list_view.setUniformItemSizes(True)
        self.list_view.viewport().update()
        self.setMinimumSize(
            820 + max(settings.font_size - 13, 0) * 28, 540 + max(settings.font_size - 13, 0) * 14
        )
        self.settings_page.populate(settings)
        self.pause.setText(tr("Resume" if settings.paused else "Pause"))
        self.pause.setAccessibleName(self.pause.text())
        self.pause.setIcon(icon("play" if settings.paused else "pause"))
        self.listener_status("paused" if settings.paused else "listening")
        self.batch_select.setText(tr("Done" if self.list_view.batch_mode else "Select"))
        self._selection_count_changed(len(self.list_view.selected_ids()))

    def _set_batch_mode(self, enabled):
        self.list_view.set_batch_mode(enabled)
        self.select_all.setVisible(enabled)
        self.batch_copy.setVisible(enabled)
        self.batch_select.setText(tr("Done" if enabled else "Select"))
        if not enabled and self.list_view.currentIndex().isValid():
            self.list_view.selectionModel().select(
                self.list_view.currentIndex(), QItemSelectionModel.SelectionFlag.ClearAndSelect
            )

    def _selection_count_changed(self, count):
        self.batch_copy.setText(tr("Copy selected ({count})", count=count))
        self.batch_copy.setEnabled(count > 0)

    def _copy_selection(self):
        ids = self.list_view.selected_ids()
        if len(ids) > 100:
            self.notify(tr("Select at most 100 clips at a time."))
        elif ids:
            self.batch_copy_requested.emit(ids)

    def _double_click(self, index):
        if index.isValid() and not self.list_view.batch_mode:
            self.copy_requested.emit(self.model.items[index.row()].id)

    def _translate_dynamic(self):
        self.heading.setText(
            tr(
                {
                    "all": "Clipboard",
                    "favorites": "Favorites",
                    "pinned": "Pinned",
                    "settings": "Settings",
                    "stats": "Statistics",
                    "emoji": "Emoji",
                }[self.scope]
            )
        )
        self.subtitle.setText(
            tr(
                {
                    "all": "Capture once. Find it instantly.",
                    "favorites": "Keep the things you reach for.",
                    "pinned": "Your essentials, always up front.",
                    "settings": "Make ClipVault feel like yours.",
                    "stats": "Statistics of your local clipboard activity.",
                    "emoji": "A little expression, ready to copy.",
                }[self.scope]
            )
        )
        self.count_label.setText(
            tr(
                "{total:,} clips  ·  {matching:,} matching",
                total=self._counts[0],
                matching=self._counts[1],
            )
        )
        self.results_label.setText(
            tr(
                "{matching:,} CLIPS  ·  {loaded:,} LOADED",
                matching=self._counts[1],
                loaded=len(self.model.items),
            )
        )
        self.empty.setText(
            tr(
                "No matches. Try another search or filter."
                if self.search.text()
                else "No clips here yet. Copy text or save a favorite."
            )
        )

    def listener_status(self, status: str):
        self._listener_status = status
        labels = {
            "listening": "●  Listening",
            "paused": "Ⅱ  Recording paused",
            "retrying": "●  Clipboard busy · retrying",
            "unavailable": "●  Clipboard unavailable",
        }
        self.listener_label.setText(tr(labels.get(status, status)))

    def notify(self, text: str, *, persistent: bool = False):
        self.notice.setText(tr(text))
        self.notice.show()
        self.notice_timer.stop()
        if not persistent:
            self.notice_timer.start(4500)

    def navigate(self, scope: str):
        self.debounce.stop()
        self.scope = scope
        if scope in {"all", "favorites", "pinned"}:
            self._last_clip_scope = scope
        self.quick_mode = False
        self.nav_buttons[scope].setChecked(True)
        self.heading.setText(
            tr(
                {
                    "all": "Clipboard",
                    "favorites": "Favorites",
                    "pinned": "Pinned",
                    "settings": "Settings",
                    "stats": "Statistics",
                    "emoji": "Emoji",
                }[scope]
            )
        )
        self.subtitle.setText(
            tr(
                {
                    "all": "Capture once. Find it instantly.",
                    "favorites": "Keep the things you reach for.",
                    "pinned": "Your essentials, always up front.",
                    "settings": "Make ClipVault feel like yours.",
                    "stats": "Statistics of your local clipboard activity.",
                    "emoji": "A little expression, ready to copy.",
                }[scope]
            )
        )
        self.motion.transition(
            self.stack,
            lambda: self.stack.setCurrentIndex(
                {"settings": 1, "stats": 2, "emoji": 3}.get(scope, 0)
            ),
        )
        if scope in {"all", "favorites", "pinned"}:
            self.refresh()
        elif scope == "stats":
            self.statistics_page.refresh_requested.emit()

    def _dates_changed(self):
        custom = self.date_filter.currentData() == -1
        self.date_range_widget.setVisible(custom)
        self.date_from.setVisible(custom)
        self.date_to.setVisible(custom)
        self.refresh()

    def date_range(self, *, utc=True):
        days = self.date_filter.currentData()
        if days == 0:
            return "", ""
        if days == -1:
            start = self.date_from.date().toPython()
            end = self.date_to.date().toPython() + timedelta(days=1)
        else:
            end = datetime.now().date() + timedelta(days=1)
            start = end - timedelta(days=days)
        if not utc:
            return start.isoformat(), end.isoformat()
        return tuple(
            datetime.combine(day, time.min)
            .astimezone()
            .astimezone(UTC)
            .isoformat(timespec="microseconds")
            for day in (start, end)
        )

    def request(self, offset=0) -> SearchRequest:
        return SearchRequest(
            self.search.text(),
            self.type_filter.currentData(),
            self._last_clip_scope,
            not self.sort.isChecked(),
            offset,
            date_from=self.date_range()[0],
            date_to=self.date_range()[1],
        )

    def refresh(self):
        if self.scope not in {"all", "favorites", "pinned"}:
            return
        self.search_busy = True
        self.load_more.setEnabled(False)
        self.search_requested.emit(self.request())

    def _load_more(self):
        if not self.search_busy and self._has_more:
            self.search_busy = True
            self.load_more.setEnabled(False)
            self.search_requested.emit(self.request(len(self.model.items)))

    def accept_page(self, page: SearchPage, *, append: bool = False):
        changed = append or page.items != self.model.items
        if changed:
            self.motion.transition(
                self.list_view.viewport(), lambda: self._accept_page(page, append=append)
            )
        else:
            self._accept_page(page, append=append)

    def _accept_page(self, page: SearchPage, *, append: bool = False):
        self.search_busy = False
        self._has_more = page.has_more
        self.load_more.setVisible(page.has_more)
        self.load_more.setEnabled(True)
        self._counts = (page.total, page.matching)
        self.count_label.setText(
            tr(
                "{total:,} clips  ·  {matching:,} matching",
                total=page.total,
                matching=page.matching,
            )
        )
        self.results_label.setText(
            f"{page.matching:,} CLIPS  /  {len(self.model.items) if append else 0}"
        )
        self._mutating_list = True
        if append:
            self.model.append(page.items)
        else:
            self.model.replace(page.items)
        self._mutating_list = False
        self.results_label.setText(
            tr(
                "{matching:,} CLIPS  ·  {loaded:,} LOADED",
                matching=page.matching,
                loaded=len(self.model.items),
            )
        )
        self.empty.setVisible(not self.model.items)
        self.empty.setText(
            tr(
                "No matches. Try another search or filter."
                if self.search.text()
                else "No clips here yet. Copy text or save a favorite."
            )
        )
        if not append:
            row = next(
                (i for i, clip in enumerate(self.model.items) if clip.id == self._selected_id), 0
            )
            if self.model.items:
                index = self.model.index(row, 0)
                if self.list_view.batch_mode:
                    self.list_view.selectionModel().setCurrentIndex(
                        index, QItemSelectionModel.SelectionFlag.NoUpdate
                    )
                else:
                    self.list_view.setCurrentIndex(index)
            else:
                self._selected_id = None
                self.preview.set_clip(None, "")

    def _select(self, current, previous):
        if self._mutating_list or not current.isValid():
            return
        self._selected_id = self.model.items[current.row()].id
        self.preview.set_clip(None, "")
        self.selected.emit(self._selected_id)

    def current_id(self) -> int | None:
        index = self.list_view.currentIndex()
        return self.model.items[index.row()].id if index.isValid() else None

    def show_panel(self, *, quick: bool = False):
        self.quick_mode = quick
        if quick:
            if self.scope not in {"all", "favorites", "pinned"}:
                self.navigate("all")
                self.quick_mode = True
            screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
            if screen:
                available = screen.availableGeometry()
                if self.width() > available.width() or self.height() > available.height():
                    self.resize(min(900, available.width()), min(620, available.height()))
                x = available.x() + (available.width() - self.width()) // 2
                y = available.y() + max(20, (available.height() - self.height()) // 3)
                self.move(
                    max(available.x(), min(x, available.right() - self.width() + 1)),
                    max(available.y(), min(y, available.bottom() - self.height() + 1)),
                )
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.search.setFocus()
        self.search.selectAll()
        self.refresh()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.KeyPress and watched in {self.search, self.list_view}:
            if event.key() == Qt.Key.Key_Escape:
                self.dismiss_panel()
                return True
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if self.list_view.batch_mode:
                    self._copy_selection()
                    return True
                clip_id = self.current_id()
                if clip_id is not None:
                    self.copy_requested.emit(clip_id)
                return True
            if watched is self.search and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
                count = len(self.model.items)
                if count:
                    row = self.list_view.currentIndex().row()
                    row = min(
                        max(row + (1 if event.key() == Qt.Key.Key_Down else -1), 0), count - 1
                    )
                    self.list_view.setCurrentIndex(self.model.index(row, 0))
                    self.list_view.scrollTo(self.model.index(row, 0))
                return True
        return super().eventFilter(watched, event)

    def dismiss_panel(self):
        if self.tray_available:
            self.hide()
        else:
            self.showMinimized()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss_panel()
            event.accept()
        else:
            super().keyPressEvent(event)

    def event(self, event):
        if event.type() == QEvent.Type.WindowDeactivate:
            if self.quick_mode and self.settings.auto_hide:
                QTimer.singleShot(150, self._hide_if_inactive)
        return super().event(event)

    def _hide_if_inactive(self):
        if (
            self.quick_mode
            and not self.isActiveWindow()
            and QApplication.activeModalWidget() is None
        ):
            self.hide()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self.panel_hidden.emit()
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
            and self.tray_available
        ):
            QTimer.singleShot(0, self.hide)
        super().changeEvent(event)

    def closeEvent(self, event):
        event.ignore()
        if self.settings.quit_on_close or not self.tray_available:
            self.quit_requested.emit()
        else:
            self.hide()

    def showEvent(self, event):
        super().showEvent(event)
        apply_windows_frame(self, dark=self.settings.theme == "dark", glass=True)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.panel_hidden.emit()
