import os

if not os.environ.get("CLIPVAULT_DESKTOP_TESTS"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from clipvault.database.repository import Repository


@pytest.fixture
def repository(tmp_path):
    repo = Repository(tmp_path / "history.sqlite3")
    yield repo
    repo.close()
