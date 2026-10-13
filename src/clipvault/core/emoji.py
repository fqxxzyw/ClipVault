"""A small offline picker and conservative emoji sequence counter."""

import re

# Counts regional flag pairs, keycaps and common ZWJ/skin-tone sequences as one.
_BASE = r"[\U0001F300-\U0001FAFF\u2600-\u27BF]"
_UNIT = _BASE + r"[\uFE0E\uFE0F]?[\U0001F3FB-\U0001F3FF]?"
_PATTERN = re.compile(
    r"[\U0001F1E6-\U0001F1FF]{2}|[0-9#*]\uFE0F?\u20E3|" + _UNIT + r"(?:\u200D" + _UNIT + r")*"
)
EMOJI = (
    ("😀", "Grinning face"),
    ("😊", "Smiling face"),
    ("😂", "Laughing"),
    ("🥰", "Love"),
    ("😎", "Cool"),
    ("🤔", "Thinking"),
    ("🥳", "Party"),
    ("😭", "Crying"),
    ("👍", "Thumbs up"),
    ("👏", "Applause"),
    ("🙏", "Thanks"),
    ("💪", "Strength"),
    ("❤️", "Heart"),
    ("✨", "Sparkles"),
    ("🔥", "Fire"),
    ("🎉", "Celebration"),
    ("🚀", "Rocket"),
    ("✅", "Done"),
    ("❌", "No"),
    ("⚠️", "Warning"),
    ("💡", "Idea"),
    ("📌", "Pin"),
    ("📋", "Clipboard"),
    ("💻", "Computer"),
    ("🐍", "Python"),
    ("☕", "Coffee"),
    ("🌈", "Rainbow"),
    ("🎯", "Target"),
    ("👨‍💻", "Developer"),
    ("🇨🇳", "China"),
    ("🇯🇵", "Japan"),
    ("🏳️‍🌈", "Rainbow flag"),
)


def emoji_count(text: str) -> int:
    return sum(1 for _ in _PATTERN.finditer(text))
