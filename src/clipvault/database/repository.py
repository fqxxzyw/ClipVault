import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from clipvault.core.classifier import classify
from clipvault.database.migrations import migrate
from clipvault.database.models import (
    CONTENT_TYPES,
    MAX_TEXT_LENGTH,
    Clip,
    ClipSummary,
    SearchPage,
    SearchRequest,
    utc_now,
)
from clipvault.services.search import can_use_trigram, fts_expression, like_pattern, terms_for


class Repository:
    """One connection per owner thread. UI access is through DatabaseService only."""

    def __init__(self, path: Path | str, *, busy_timeout_ms: int = 2500):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), timeout=busy_timeout_ms / 1000)
        try:
            self.connection.row_factory = sqlite3.Row
            self.connection.execute(f"PRAGMA busy_timeout = {int(busy_timeout_ms)}")
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.execute("PRAGMA synchronous = NORMAL")
            self.connection.execute("PRAGMA secure_delete = ON")
            self.fts_available = migrate(self.connection)
        except Exception:
            self.connection.close()
            raise

    def upsert(self, content: str, captured_at: str | None = None) -> Clip:
        if not content.strip() or len(content) > MAX_TEXT_LENGTH:
            raise ValueError("Content is blank or exceeds the capture limit")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        timestamp = captured_at or utc_now()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO clipboard_history
                (content, content_hash, content_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    updated_at = MAX(updated_at, excluded.updated_at)
            """,
                (content, digest, classify(content), timestamp, timestamp),
            )
        row = self.connection.execute(
            "SELECT * FROM clipboard_history WHERE content_hash = ?", (digest,)
        ).fetchone()
        return Clip.from_row(row)

    def get(self, clip_id: int) -> Clip | None:
        row = self.connection.execute(
            "SELECT * FROM clipboard_history WHERE id = ?", (clip_id,)
        ).fetchone()
        return Clip.from_row(row) if row else None

    def set_flag(self, clip_id: int, flag: str, value: bool) -> Clip | None:
        if flag not in {"is_favorite", "is_pinned"}:
            raise ValueError("Unknown flag")
        with self.connection:
            self.connection.execute(
                f"UPDATE clipboard_history SET {flag} = ? WHERE id = ?", (int(value), clip_id)
            )
        return self.get(clip_id)

    def touch(self, clip_id: int) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE clipboard_history SET updated_at = ? WHERE id = ?", (utc_now(), clip_id)
            )

    def delete(self, clip_id: int) -> int:
        with self.connection:
            return self.connection.execute(
                "DELETE FROM clipboard_history WHERE id = ?", (clip_id,)
            ).rowcount

    def count(self) -> int:
        return self.connection.execute("SELECT COUNT(*) FROM clipboard_history").fetchone()[0]

    def search(self, request: SearchRequest) -> SearchPage:
        if request.content_type not in (*CONTENT_TYPES, "all"):
            raise ValueError("Unknown content type")
        if request.scope not in {"all", "favorites", "pinned"}:
            raise ValueError("Unknown scope")
        conditions, values = [], []
        if request.content_type != "all":
            conditions.append("content_type = ?")
            values.append(request.content_type)
        if request.scope != "all":
            conditions.append(
                "is_favorite = 1" if request.scope == "favorites" else "is_pinned = 1"
            )
        terms = terms_for(request.query)
        mode = "browse"
        if self.fts_available and can_use_trigram(terms):
            conditions.append("id IN (SELECT rowid FROM history_fts WHERE history_fts MATCH ?)")
            values.append(fts_expression(terms))
            mode = "fts5"
        if terms:
            # Also verify literal substrings so FTS and fallback have identical semantics.
            conditions.extend("content LIKE ? ESCAPE '\\'" for _ in terms)
            values.extend(like_pattern(term) for term in terms)
            if mode != "fts5":
                mode = "like"
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        order = "DESC" if request.newest_first else "ASC"
        limit = min(max(request.limit, 1), 200)
        rows = self.connection.execute(
            "SELECT id, substr(content, 1, 180) AS preview, content_type, updated_at, "
            "length(content) AS char_count, is_favorite, is_pinned FROM clipboard_history"
            + where
            + f" ORDER BY is_pinned DESC, updated_at {order}, id {order} LIMIT ? OFFSET ?",
            (*values, limit + 1, max(request.offset, 0)),
        ).fetchall()
        matching = self.connection.execute(
            "SELECT COUNT(*) FROM clipboard_history" + where, values
        ).fetchone()[0]
        items = [
            ClipSummary(
                **{
                    **dict(row),
                    "is_favorite": bool(row["is_favorite"]),
                    "is_pinned": bool(row["is_pinned"]),
                }
            )
            for row in rows[:limit]
        ]
        return SearchPage(items, len(rows) > limit, self.count(), matching, mode)

    def cleanup(self, retention_days: int, max_history: int, *, now: datetime | None = None) -> int:
        """Favorites AND pins survive age/quantity cleanup; quantity caps ordinary history."""
        removed = 0
        with self.connection:
            if retention_days:
                cutoff = ((now or datetime.now(UTC)) - timedelta(days=retention_days)).isoformat(
                    timespec="microseconds"
                )
                removed += self.connection.execute(
                    "DELETE FROM clipboard_history WHERE is_favorite = 0 AND is_pinned = 0 "
                    "AND updated_at < ?",
                    (cutoff,),
                ).rowcount
            removed += self.connection.execute(
                "DELETE FROM clipboard_history WHERE id IN (SELECT id FROM clipboard_history "
                "WHERE is_favorite = 0 AND is_pinned = 0 ORDER BY updated_at DESC, id DESC "
                "LIMIT -1 OFFSET ?)",
                (max(max_history, 1),),
            ).rowcount
        return removed

    def clear_ordinary(self) -> int:
        with self.connection:
            count = self.connection.execute(
                "DELETE FROM clipboard_history WHERE is_favorite = 0 AND is_pinned = 0"
            ).rowcount
        self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return count

    def close(self) -> None:
        self.connection.close()
