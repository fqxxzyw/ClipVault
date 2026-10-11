from dataclasses import dataclass
from datetime import UTC, datetime

CONTENT_TYPES = ("text", "url", "python", "javascript", "json", "shell", "sql")
TYPE_LABELS = {
    "text": "Text",
    "url": "URL",
    "python": "Python",
    "javascript": "JavaScript",
    "json": "JSON",
    "shell": "Shell",
    "sql": "SQL",
}
MAX_TEXT_LENGTH = 100_000
PAGE_SIZE = 50


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True, slots=True)
class Clip:
    id: int
    content: str
    content_hash: str
    content_type: str
    created_at: str
    updated_at: str
    is_favorite: bool
    is_pinned: bool

    @classmethod
    def from_row(cls, row) -> "Clip":
        data = dict(row)
        data["is_favorite"] = bool(data["is_favorite"])
        data["is_pinned"] = bool(data["is_pinned"])
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ClipSummary:
    id: int
    preview: str
    content_type: str
    updated_at: str
    char_count: int
    is_favorite: bool
    is_pinned: bool


@dataclass(frozen=True, slots=True)
class SearchRequest:
    query: str = ""
    content_type: str = "all"
    scope: str = "all"
    newest_first: bool = True
    offset: int = 0
    limit: int = PAGE_SIZE


@dataclass(frozen=True, slots=True)
class SearchPage:
    items: list[ClipSummary]
    has_more: bool
    total: int
    matching: int
    search_mode: str
