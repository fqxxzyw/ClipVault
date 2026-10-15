"""Conservative, local Unicode copy/paste cleanup; never executes or reformats code."""

import unicodedata

# Preserve ZWJ/ZWNJ, variation selectors, emoji tags and bidirectional text.
# Removing every Unicode format character would corrupt real languages and emoji.
_REMOVED = frozenset("\u200b\ufeff\u2060\u180e")


def clean_text(text: str) -> str:
    """Remove common invisible copy artifacts and normalize space widths only.

    Keep each space, tab, newline and all visible characters. Do not decode HTML,
    strip Markdown, infer indentation, strip line numbers or modify escape sequences.
    """
    return "".join(
        " " if unicodedata.category(char) == "Zs" else char
        for char in text
        if char not in _REMOVED
        and not (unicodedata.category(char) == "Cc" and char not in "\t\r\n")
    )
