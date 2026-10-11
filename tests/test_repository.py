import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from clipvault.database.migrations import SCHEMA_VERSION, migrate
from clipvault.database.models import SearchRequest
from clipvault.database.repository import Repository


def test_write_read_and_persistence(tmp_path):
    path = tmp_path / "test.sqlite3"
    first = Repository(path)
    item = first.upsert("你好，ClipVault\nsecond line")
    first.close()
    second = Repository(path)
    assert second.get(item.id).content == "你好，ClipVault\nsecond line"
    assert second.count() == 1
    second.close()


def test_deduplicate_keeps_flags_and_creation_time(repository):
    first = repository.upsert("same", "2026-01-01T00:00:00.000000+00:00")
    repository.set_flag(first.id, "is_favorite", True)
    repository.set_flag(first.id, "is_pinned", True)
    second = repository.upsert("same", "2026-03-01T00:00:00.000000+00:00")
    assert first.id == second.id
    assert second.created_at == first.created_at
    assert second.updated_at > first.updated_at
    assert second.is_favorite and second.is_pinned
    assert repository.count() == 1
    # A retried older capture must not move the item backwards in time.
    assert repository.upsert("same", first.created_at).updated_at == second.updated_at


def test_flags_delete_and_pinned_sort(repository):
    first = repository.upsert("older")
    second = repository.upsert("newer")
    repository.set_flag(first.id, "is_pinned", True)
    repository.set_flag(second.id, "is_favorite", True)
    assert repository.search(SearchRequest()).items[0].id == first.id
    assert repository.search(SearchRequest(scope="favorites")).items[0].id == second.id
    assert repository.search(SearchRequest(scope="pinned")).items[0].id == first.id
    assert repository.delete(first.id) == 1
    assert repository.delete(first.id) == 0
    assert repository.get(first.id) is None
    assert repository.search(SearchRequest(query="older")).matching == 0


@pytest.mark.parametrize("use_fts", [False, True])
def test_chinese_multikeyword_literal_search(repository, use_fts):
    if use_fts and not repository.fts_available:
        pytest.skip("FTS5 trigram is unavailable")
    repository.fts_available = use_fts
    repository.upsert("学习知识追踪：遗忘因素和模型训练")
    repository.upsert("train neural_network 100% 中文模型")
    repository.upsert("hello clipboard favorite")
    assert repository.search(SearchRequest(query="知识追踪 遗忘")).matching == 1
    assert repository.search(SearchRequest(query="模型")).matching == 2
    assert repository.search(SearchRequest(query="neural_network 100%")).matching == 1
    assert repository.search(SearchRequest(query="CLIPBOARD favorite")).matching == 1
    assert repository.search(SearchRequest(query="lipboard")).matching == 1
    assert repository.search(SearchRequest(query="% '_ OR 1=1 --")).matching == 0
    assert repository.search(SearchRequest(query="100%")).matching == 1
    assert repository.search(SearchRequest(query="知识")).search_mode == "like"


def test_paging_and_type_filter(repository):
    for index in range(125):
        repository.upsert(f"clip #{index}")
    item = repository.upsert("https://example.org")
    first = repository.search(SearchRequest(limit=50))
    second = repository.search(SearchRequest(limit=50, offset=50))
    third = repository.search(SearchRequest(limit=50, offset=100))
    assert len(first.items) == len(second.items) == 50
    assert len(third.items) == 26 and not third.has_more
    assert first.has_more and second.has_more
    assert not set(c.id for c in first.items) & set(c.id for c in second.items)
    assert repository.search(SearchRequest(content_type="url")).items[0].id == item.id
    assert repository.search(SearchRequest(newest_first=False)).items[0].preview == "clip #0"


def test_automatic_cleanup_preserves_favorites_and_pins(repository):
    now = datetime.now(UTC)
    old = (now - timedelta(days=40)).isoformat(timespec="microseconds")
    ordinary = repository.upsert("expired ordinary", old)
    favorite = repository.upsert("expired favorite", old)
    pinned = repository.upsert("expired pinned", old)
    repository.set_flag(favorite.id, "is_favorite", True)
    repository.set_flag(pinned.id, "is_pinned", True)
    repository.upsert("recent", now.isoformat(timespec="microseconds"))
    assert repository.cleanup(30, 5000, now=now) == 1
    assert repository.get(ordinary.id) is None
    assert repository.get(favorite.id) and repository.get(pinned.id)
    assert repository.clear_ordinary() == 1
    assert repository.count() == 2


def test_quantity_cleanup_and_never_expire(repository):
    for i in range(10):
        repository.upsert(f"old-{i}", f"2020-01-{i + 1:02d}T00:00:00.000000+00:00")
    assert repository.cleanup(0, 3) == 7
    assert repository.count() == 3


def test_flag_allowlist(repository):
    clip = repository.upsert("safe")
    with pytest.raises(ValueError):
        repository.set_flag(clip.id, "content = 'hacked' --", True)


def test_migration_v1_preserves_existing_data(tmp_path):
    path = tmp_path / "old.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE clipboard_history(id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "content TEXT NOT NULL, content_hash TEXT NOT NULL UNIQUE, content_type TEXT "
        "NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, "
        "is_favorite INTEGER NOT NULL DEFAULT 0)"
    )
    connection.execute("INSERT INTO clipboard_history VALUES (1,'legacy','hash','text','t','t',1)")
    connection.execute("PRAGMA user_version=1")
    connection.commit()
    connection.close()
    repo = Repository(path)
    assert repo.get(1).is_favorite
    assert not repo.get(1).is_pinned
    assert repo.get(1).content == "legacy"
    assert repo.connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    repo.close()


def test_future_migration_rejected():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA user_version=999")
    with pytest.raises(sqlite3.DatabaseError):
        migrate(connection)
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 999
    connection.close()


def test_busy_database_recovers(tmp_path):
    path = tmp_path / "busy.sqlite3"
    repo = Repository(path, busy_timeout_ms=30)
    other = sqlite3.connect(path)
    other.execute("BEGIN IMMEDIATE")
    with pytest.raises(sqlite3.OperationalError, match="locked"):
        repo.upsert("temporary contention")
    other.rollback()
    assert repo.upsert("after release").content == "after release"
    other.close()
    repo.close()
