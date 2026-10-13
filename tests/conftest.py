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


@pytest.fixture
def app(qapp, qtbot, tmp_path):
    from clipvault.app import ClipVaultApplication

    controller = ClipVaultApplication(qapp, tmp_path, no_tray=True, enable_hotkey=False)
    qtbot.addWidget(controller.window)
    qtbot.addWidget(controller.mini)
    qtbot.waitUntil(lambda: not controller.window.search_busy)
    yield controller
    controller.shutdown()
    qapp.clipboard().clear()
