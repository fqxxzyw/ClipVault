import sqlite3

SCHEMA_VERSION = 4


def migrate(connection: sqlite3.Connection) -> bool:
    """Apply transactional migrations; future versions must never be downgraded."""
    version = connection.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise sqlite3.DatabaseError("Database version is newer than this application")
    try:
        connection.execute("BEGIN IMMEDIATE")
        if version < 1:
            connection.execute("""
                CREATE TABLE clipboard_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    content_hash TEXT NOT NULL UNIQUE,
                    content_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_favorite INTEGER NOT NULL DEFAULT 0 CHECK(is_favorite IN (0, 1))
                )
            """)
            connection.execute("PRAGMA user_version = 1")
        if version < 2:
            connection.execute(
                "ALTER TABLE clipboard_history ADD COLUMN is_pinned INTEGER NOT NULL "
                "DEFAULT 0 CHECK(is_pinned IN (0, 1))"
            )
            connection.execute("PRAGMA user_version = 2")
        if version < 3:
            connection.execute("""
                CREATE TABLE clipboard_assets (
                    clip_id INTEGER PRIMARY KEY REFERENCES clipboard_history(id) ON DELETE CASCADE,
                    png BLOB NOT NULL,
                    thumbnail BLOB NOT NULL
                )
            """)
            connection.execute("""
                CREATE TABLE daily_stats (
                    day TEXT PRIMARY KEY,
                    captures INTEGER NOT NULL DEFAULT 0,
                    reuses INTEGER NOT NULL DEFAULT 0,
                    characters INTEGER NOT NULL DEFAULT 0,
                    lines INTEGER NOT NULL DEFAULT 0,
                    emoji INTEGER NOT NULL DEFAULT 0,
                    images INTEGER NOT NULL DEFAULT 0,
                    files INTEGER NOT NULL DEFAULT 0
                )
            """)
            connection.execute("PRAGMA user_version = 3")
        if version < 4:
            # v4 records may carry additional code-language identifiers unknown to v3 apps.
            connection.execute("PRAGMA user_version = 4")
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_time ON "
            "clipboard_history(is_pinned DESC, updated_at DESC, id DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_favorite ON "
            "clipboard_history(is_favorite, updated_at DESC)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_type ON "
            "clipboard_history(content_type, updated_at DESC)"
        )
        connection.commit()
    except sqlite3.Error:
        connection.rollback()
        raise
    # FTS is optional. Trigram is supported by SQLite >= 3.34; LIKE works without it.
    try:
        with connection:
            existed = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'history_fts'"
            ).fetchone()
            connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS history_fts USING "
                "fts5(content, content='clipboard_history', content_rowid='id', "
                "tokenize='trigram')"
            )
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS history_fts_insert AFTER INSERT ON clipboard_history
                BEGIN INSERT INTO history_fts(rowid, content) VALUES (new.id, new.content); END
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS history_fts_delete AFTER DELETE ON clipboard_history
                BEGIN INSERT INTO history_fts(history_fts, rowid, content)
                VALUES ('delete', old.id, old.content); END
            """)
            connection.execute("""
                CREATE TRIGGER IF NOT EXISTS history_fts_update
                AFTER UPDATE OF content ON clipboard_history
                BEGIN
                    INSERT INTO history_fts(history_fts, rowid, content)
                    VALUES ('delete', old.id, old.content);
                    INSERT INTO history_fts(rowid, content) VALUES (new.id, new.content);
                END
            """)
            if not existed:
                connection.execute("INSERT INTO history_fts(history_fts) VALUES ('rebuild')")
        return True
    except sqlite3.OperationalError as error:
        # Only absence of FTS/trigram is optional; corruption/I/O errors must surface.
        if "no such module" not in str(error) and "no such tokenizer" not in str(error):
            raise
        return False
