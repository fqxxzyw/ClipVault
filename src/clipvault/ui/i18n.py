"""Small offline bilingual catalogue. User clip content is never translated."""

from PySide6.QtCore import QLocale
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QLineEdit, QWidget

# Source messages are also the English fallback. Keep placeholders identical.
PAIRS = [
    (
        "Automatically clean copied text (zero-width artifacts and spaces)",
        "自动清理复制文本（零宽脏字符与特殊空格）",
    ),
    (
        "Cleans new history and text copied from history; keeps indentation and emoji. "
        "Does not rewrite the source clipboard or existing records.",
        "清理新入库及从历史复制的文本，保留缩进和 Emoji；不改写外部剪贴板或已有记录。",
    ),
    ("Your clipboard.\nUnder your control.", "你的剪贴板。\n由你掌控。"),
    ("WORKSPACE", "工作空间"),
    ("All Clips", "全部记录"),
    ("Favorites", "收藏"),
    ("Pinned", "置顶"),
    ("Settings", "设置"),
    ("Local by design", "本地存储，隐私优先"),
    ("No account. No cloud.\nJust your device.", "无需账号，无需云端。\n数据只在你的设备上。"),
    ("Clipboard", "剪贴板"),
    ("Capture once. Find it instantly.", "复制一次，随时找回。"),
    ("Keep the things you reach for.", "珍藏你经常使用的内容。"),
    ("Your essentials, always up front.", "常用内容，始终排在前面。"),
    ("Make ClipVault feel like yours.", "让 ClipVault 更适合你。"),
    ("Pause", "暂停"),
    ("Resume", "恢复"),
    ("Pause recording before copying sensitive information", "复制敏感信息前，请暂停记录"),
    ("Search clips…", "搜索记录…"),
    ("All types", "所有类型"),
    ("Text", "文本"),
    (
        "Newest first · click for oldest first (pins remain first)",
        "最新优先；点击切换为最早优先（置顶始终在前）",
    ),
    ("Refresh history", "刷新历史"),
    ("RECENT CLIPS", "最近记录"),
    ("No clips yet. Copy some text to begin.", "还没有记录，复制一段文字开始吧。"),
    ("No matches. Try another search or filter.", "没有匹配内容，试试其他关键词或筛选。"),
    ("No clips here yet. Copy text or save a favorite.", "这里还没有记录，复制文字或收藏内容吧。"),
    ("Load more", "加载更多"),
    ("Preview", "内容预览"),
    ("Select a clip to get started", "选择一条记录查看内容"),
    (
        "Your next great idea starts with a copy.\n"
        "\n"
        "Copy some text in any app. ClipVault keeps it here, on your device.",
        "好想法，从一次复制开始。\n\n在任何应用中复制文字，ClipVault 会在本地为你保存。",
    ),
    ("Copy to clipboard", "复制到剪贴板"),
    ("Favorite", "收藏"),
    ("Favorited", "已收藏"),
    ("Pin", "置顶"),
    ("Details", "详情"),
    ("Delete", "删除"),
    ("Enter to copy  ·  ↑↓ to browse", "Enter 复制  ·  ↑↓ 切换"),
    ("Format JSON & copy", "格式化 JSON 并复制"),
    ("Open in browser", "在浏览器中打开"),
    ("Clip details — ClipVault", "记录详情 — ClipVault"),
    ("Close", "关闭"),
    ("Appearance", "外观"),
    ("Theme", "主题"),
    ("Dark", "深色"),
    ("Light", "浅色"),
    ("Font size", "字体大小"),
    ("Window opacity", "窗口透明度"),
    ("Show a tray notification after copying", "复制后显示托盘通知"),
    ("Hide quick panel when it loses focus", "快捷面板失去焦点后自动隐藏"),
    ("Shortcuts & startup", "快捷键与启动"),
    ("Global shortcut", "全局快捷键"),
    (
        "Ctrl / Alt / Shift / Win + A–Z, 0–9, F1–F11 or navigation key",
        "Ctrl / Alt / Shift / Win + 字母、数字、F1–F11 或方向键",
    ),
    ("Start in the system tray when Windows starts", "Windows 启动时在托盘中运行"),
    ("Available on Windows only", "仅 Windows 可用"),
    ("Exit the app when the window is closed", "关闭窗口时退出程序"),
    ("Privacy & history", "隐私与历史"),
    ("Ordinary clip limit", "普通记录数量上限"),
    ("Auto cleanup", "自动清理"),
    ("Never", "永不"),
    (
        "Skip recognizable passwords, private keys and API tokens",
        "跳过可识别的密码、私钥和 API Token",
    ),
    (
        "Favorites and pinned clips survive cleanup and Clear history.\n"
        "Secret detection is a heuristic. Pause recording before copying secrets.\n"
        "Data stays on this device. SQLite storage is not encrypted.",
        "收藏和置顶内容不会被自动清理或清空历史删除。\n"
        "敏感检测无法识别所有秘密；复制敏感信息前请暂停记录。\n"
        "数据只存于此设备，SQLite 数据库未加密。",
    ),
    ("Open data folder", "打开数据目录"),
    ("Clear ordinary history…", "清空普通历史…"),
    ("Reset form", "重置表单"),
    ("Save settings", "保存设置"),
    ("Language", "界面语言"),
    ("Follow system", "跟随系统"),
    (
        "Reduce motion (also respects Windows animation settings)",
        "减少动态效果（同时遵循 Windows 动画设置）",
    ),
    ("Shortcut opens", "快捷键打开"),
    ("Full window", "完整窗口"),
    ("Mini window", "小窗"),
    ("Open mini window", "打开小窗"),
    (
        "Click a clip to copy · Enter to copy · Esc to hide · Alt+F to open full window",
        "单击复制 · Enter 复制 · Esc 隐藏 · Alt+F 打开完整窗口",
    ),
    ("Copy Markdown", "复制 Markdown"),
    ("Copy plain text", "复制纯文本"),
    ("Rendered", "渲染预览"),
    ("Source", "原始文本"),
    ("Preview as Markdown", "按 Markdown 预览"),
    (
        "Markdown preview does not load images or open links.",
        "Markdown 预览不加载图片，不打开链接。",
    ),
    ("●  Listening", "●  正在监听"),
    ("Ⅱ  Recording paused", "Ⅱ  已暂停记录"),
    ("●  Clipboard busy · retrying", "●  剪贴板忙碌，正在重试"),
    ("●  Clipboard unavailable", "●  剪贴板暂时不可用"),
    ("●  Starting…", "●  正在启动…"),
    ("●  Storage error · retry available", "●  存储错误，请重试"),
    ("Shortcut unavailable · change in Settings", "快捷键不可用，请在设置中更换"),
    ("Open ClipVault", "打开 ClipVault"),
    ("Pause recording", "暂停记录"),
    ("Quit", "退出"),
    (
        "Settings could not be read. Defaults are in use; the original file is retained.",
        "设置无法读取，已使用默认设置。原设置文件未删除。",
    ),
    (
        "The global shortcut is unavailable. Choose another combination in Settings.",
        "全局快捷键注册失败，可能被其他应用占用。请在设置中更换组合。",
    ),
    (
        "Global shortcuts and startup integration are available on Windows only.",
        "当前为非 Windows 环境；全局快捷键和开机启动仅在 Windows 提供。",
    ),
    ("Could not open the default browser.", "无法打开默认浏览器。"),
    ("Copied to the system clipboard.", "已复制到系统剪贴板。"),
    ("Copied to clipboard", "已复制到剪贴板"),
    ("Content exceeds 100,000 characters and was not saved.", "内容超过 100,000 字符，未记录。"),
    (
        "Clipboard is temporarily not writable. Please try copying again.",
        "系统剪贴板暂时不可写，请重试复制。",
    ),
    (
        "Privacy filter: potentially sensitive content was not saved.",
        "隐私过滤：疑似敏感内容未记录。",
    ),
    (
        "Content is too long or contains invalid characters and was not saved.",
        "内容过长或包含无效字符，未记录。",
    ),
    (
        "The pause setting could not be saved. Check data folder permissions.",
        "暂停状态无法保存。请检查数据目录权限。",
    ),
    ("Recording paused.", "已暂停记录。"),
    (
        "Recording resumed. Content copied while paused is not imported.",
        "已恢复记录；暂停期间的内容不会补录。",
    ),
    (
        "Shortcut conflict. The previous shortcut remains active.",
        "快捷键注册失败，可能与其他软件冲突；原快捷键仍然有效。",
    ),
    (
        "Invalid settings or write failure. Check the shortcut and data folder permissions.",
        "设置无效或无法保存。请检查快捷键格式和数据目录权限。",
    ),
    (
        "Could not update Windows startup. Check current-user permissions.",
        "无法更新 Windows 开机启动项，请检查当前用户权限。",
    ),
    (
        " Some system settings could not be restored. Save settings again.",
        " 部分系统设置无法恢复，请重新保存设置。",
    ),
    ("Settings saved and applied.", "设置已保存并立即生效。"),
    ("Clear ordinary history", "清空普通历史记录"),
    (
        "Delete all clips that are neither favorite nor pinned? This cannot be undone.",
        "删除所有非收藏、非置顶记录？此操作无法撤销。",
    ),
    ("Could not open the local data folder.", "无法打开本地数据目录。"),
    (
        "Database temporarily unavailable. Try again; the operation has not completed.",
        "数据库暂时不可用。请稍后重试；本次操作尚未完成。",
    ),
    (
        "Could not access the local database. Check permissions and database version.",
        "无法读写本地数据库。请检查磁盘权限或数据库版本。",
    ),
    (
        "Content or settings could not be processed. Operation cancelled.",
        "内容或设置无法处理，本次操作已取消。",
    ),
    (
        "Operation did not complete. Try again or restart ClipVault.",
        "本次操作未完成，请重试或重启 ClipVault。",
    ),
    ("{count:,} characters", "{count:,} 字符"),
    ("{total:,} clips  ·  {matching:,} matching", "{total:,} 条记录  ·  {matching:,} 条匹配"),
    ("{matching:,} CLIPS  ·  {loaded:,} LOADED", "{matching:,} 条匹配  ·  已加载 {loaded:,} 条"),
    ("Just now", "刚刚"),
    ("{count}m ago", "{count} 分钟前"),
    ("{count}h ago", "{count} 小时前"),
    ("{days} days", "{days} 天"),
    ("{key}  ·  Windows only", "{key}  ·  仅 Windows"),
    ("{key}  to toggle", "{key}  打开 / 隐藏"),
    (
        "Cleared {count:,} ordinary clips. Favorites and pins were kept.",
        "已清空 {count:,} 条普通记录。收藏和置顶已保留。",
    ),
    ("Created: {date}", "创建时间：{date}"),
    ("Last copied: {date}", "最近复制：{date}"),
]
PAIRS += [
    ("Statistics", "统计"),
    ("Emoji", "表情"),
    ("Image", "图片"),
    ("Files", "文件"),
    ("Code", "Code · 代码"),
    ("All dates", "所有日期"),
    ("Today", "今天"),
    ("Last 7 days", "最近 7 天"),
    ("Last 30 days", "最近 30 天"),
    ("Custom range", "自定义日期"),
    ("From", "从"),
    ("Through", "至"),
    ("Captured copies", "新复制次数"),
    ("Copies from ClipVault", "ClipVault 复用次数"),
    ("Copied characters", "复制字符数"),
    ("Copied lines", "复制行数"),
    ("Copied emoji", "复制表情数"),
    ("Copied images", "复制图片数"),
    ("File selections", "文件选择次数"),
    ("Refresh statistics", "刷新统计"),
    ("Reset statistics…", "重置统计…"),
    ("Reset statistics", "重置统计"),
    (
        "Delete all aggregate counters? Clipboard history will be kept.",
        "删除全部统计计数？剪贴板历史将保留。",
    ),
    (
        "Counts start with this version. Paused and filtered copies are excluded.\n"
        "Paste count: unavailable. The clipboard does not report paste events; "
        "reuse is not a paste.\n"
        "Emoji counts cover common Unicode sequences, not every possible grapheme.",
        "计数从此版本开始。暂停及隐私过滤的复制不计入统计。\n"
        "粘贴次数：不可观测。系统剪贴板不提供粘贴事件，复用次数不等于粘贴次数。\n"
        "表情统计覆盖常见 Unicode 序列，并非全部字素。",
    ),
    (
        "Click an emoji to copy. It is saved in history when recording is active.",
        "点击表情即可复制；记录开启时也会保存到历史。",
    ),
    ("Copy paths", "复制路径"),
    (
        "Save copied images locally (no sensitive-image detection)",
        "将复制的图片保存在本地（图片无敏感检测）",
    ),
    (
        "Record copied file paths only; never read file contents",
        "仅记录复制的文件路径，不读取文件内容",
    ),
    (
        "Image exceeds the 8 MiB storage limit and was not saved.",
        "图片超过 8 MiB 存储限制，未记录。",
    ),
    ("Image or file selection exceeds the capture limit.", "图片或文件选择超过记录限制，未记录。"),
    ("Saved settings apply immediately.", "保存后立即生效。"),
    ("Statistics of your local clipboard activity.", "查看本地剪贴板使用情况。"),
    ("A little expression, ready to copy.", "一点表情，即点即用。"),
    ("Markdown preview mode", "Markdown 预览模式"),
    ("Markdown copy format", "Markdown 复制格式"),
    ("Yes", "是"),
    ("No", "否"),
    ("History list", "历史记录列表"),
    ("7 days", "7 天"),
    ("30 days", "30 天"),
    ("90 days", "90 天"),
    ("Grinning face", "笑脸"),
    ("Smiling face", "微笑"),
    ("Laughing", "大笑"),
    ("Love", "爱意"),
    ("Cool", "酷"),
    ("Thinking", "思考"),
    ("Party", "派对"),
    ("Crying", "哭泣"),
    ("Thumbs up", "赞"),
    ("Applause", "鼓掌"),
    ("Thanks", "感谢"),
    ("Strength", "力量"),
    ("Heart", "爱心"),
    ("Sparkles", "闪光"),
    ("Fire", "火焰"),
    ("Celebration", "庆祝"),
    ("Rocket", "火箭"),
    ("Done", "完成"),
    ("No", "否"),
    ("Warning", "警告"),
    ("Idea", "想法"),
    ("Pin", "置顶"),
    ("Clipboard", "剪贴板"),
    ("Computer", "电脑"),
    ("Python", "Python"),
    ("Coffee", "咖啡"),
    ("Rainbow", "彩虹"),
    ("Target", "目标"),
    ("Developer", "开发者"),
    ("China", "中国"),
    ("Japan", "日本"),
    ("Rainbow flag", "彩虹旗"),
]
PAIRS += [("Offline. On your device.", "完全离线，数据在本地。"), ("TXT", "TXT · 文本")]
PAIRS += [
    ("Always on top", "窗口置顶"),
    ("Mini window appearance", "小窗外观"),
    ("Mini opacity", "小窗透明度"),
    ("Liquid glass appearance", "液态玻璃外观"),
    ("Keep the mini window above other windows", "小窗始终保持在其他窗口上方"),
    ("Reset size and position", "重置大小和位置"),
    (
        "Drag to move · Drag edges to resize · Click to copy · Enter / Esc",
        "拖动移动 · 边缘缩放 · 单击复制 · Enter / Esc",
    ),
    ("Mini window preferences could not be saved.", "小窗设置无法保存。"),
    ("Content language", "内容语言"),
    (
        "Static HTML: scripts and external resources are disabled. "
        "CSS support is Qt rich text, not a web browser.",
        "静态 HTML：禁用脚本和外部资源。CSS 使用 Qt 富文本支持范围，不是完整网页浏览器。",
    ),
    (
        "Drag anywhere to move; drag edges to resize. Windows 11 Acrylic blur is used "
        "when supported; other systems use translucent glass styling.",
        "普通拖动即可移动，拖动边缘调整大小。支持时请求 Windows 11 Acrylic 模糊，"
        "其他系统显示半透明玻璃外观。",
    ),
]
PAIRS += [("Auto detect", "自动识别")]
ZH = dict(PAIRS)
EN = {zh: en for en, zh in PAIRS}
_language = "en"


def set_language(language: str):
    global _language
    if language == "system":
        language = "zh_CN" if QLocale.system().language() == QLocale.Language.Chinese else "en"
    _language = language


def tr(source: str, **values) -> str:
    english = EN.get(source, source)
    translated = ZH.get(english, english) if _language == "zh_CN" else english
    return translated.format(**values) if values else translated


def translate_widgets(root):
    """Translate registered UI strings, preserving source text and combo item data."""
    for widget in [root, *root.findChildren(QWidget), *root.findChildren(QAction)]:
        if widget.property("i18nSkip"):
            continue
        if isinstance(widget, (QLabel, QAbstractButton, QAction)):
            if not hasattr(widget, "_source_text"):
                widget._source_text = widget.text()
            widget.setText(tr(widget._source_text))
            if isinstance(widget, QAbstractButton):
                widget.setAccessibleName(widget.text())
        if isinstance(widget, QComboBox):
            if not hasattr(widget, "_source_items"):
                widget._source_items = [widget.itemText(i) for i in range(widget.count())]
            for i, source in enumerate(widget._source_items):
                widget.setItemText(i, tr(source))
        if isinstance(widget, QLineEdit):
            if not hasattr(widget, "_source_placeholder"):
                widget._source_placeholder = widget.placeholderText()
            widget.setPlaceholderText(tr(widget._source_placeholder))
            widget.setAccessibleName(widget.placeholderText())
        if isinstance(widget, QWidget):
            if not hasattr(widget, "_source_tooltip"):
                widget._source_tooltip = widget.toolTip()
            widget.setToolTip(tr(widget._source_tooltip))
