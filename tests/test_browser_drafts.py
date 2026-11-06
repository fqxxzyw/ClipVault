import json
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer

from clipvault.core.browser_bridge import MAX_BODY, pairing_token, validate_draft


def draft(text="草稿内容", revision=1, draft_id=None):
    stamp = datetime.now(UTC).isoformat()
    return {
        "id": draft_id or str(uuid.uuid4()),
        "origin": "https://chatgpt.com",
        "path": "/c/example",
        "text": text,
        "created_at": stamp,
        "updated_at": stamp,
        "revision": revision,
    }


def request(port, token, payload=None, *, origin=None, path="/v1/drafts", raw=None):
    headers = {"Authorization": f"Bearer {token}"}
    if origin:
        headers["Origin"] = origin
    if payload is not None or raw is not None:
        headers["Content-Type"] = "application/json"
    data = (
        raw
        if raw is not None
        else (json.dumps(payload).encode("utf-8") if payload is not None else None)
    )
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as result:
            return result.status, json.loads(result.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def run_request(qtbot, pool, *args, **kwargs):
    result = pool.submit(request, *args, **kwargs)
    qtbot.waitUntil(result.done, timeout=9000)
    return result.result()


def test_pairing_token_persisted_and_not_weak(tmp_path):
    token = pairing_token(tmp_path)
    assert len(token) >= 40 and pairing_token(tmp_path) == token
    assert (tmp_path / "browser-sync.key").read_text() == token
    (tmp_path / "browser-sync.key").write_text("bad")
    with pytest.raises(ValueError):
        pairing_token(tmp_path)


def test_validate_rejects_untrusted_metadata_and_invalid_content():
    valid = validate_draft(draft())
    assert valid["text"] == "草稿内容" and valid["origin"] == "https://chatgpt.com"
    for change in (
        {"origin": "https://user:pass@example.com"},
        {"path": "/x?secret=1"},
        {"origin": "file:///private"},
        {"text": "\x00"},
        {"revision": 0},
        {"id": "../../invalid"},
        {"text": "x" * 100001},
    ):
        with pytest.raises((ValueError, TypeError)):
            validate_draft({**draft(), **change})


def test_browser_sync_authenticates_and_recovers_by_day(app, qtbot, qapp):
    token = pairing_token(app.directory)
    app._browser_token = token
    app.browser_bridge.start(token, port=0)
    port = app.browser_bridge.server.server_address[1]
    app.window.navigate("drafts")
    entry = draft("中文输入草稿\n第二行")
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert run_request(qtbot, pool, port, "wrong-token", entry)[0] == 403
        assert run_request(qtbot, pool, port, token, entry, origin="https://evil.example")[0] == 403
        assert run_request(qtbot, pool, port, token, path="/v1/status")[0] == 200
        assert run_request(qtbot, pool, port, token, entry)[0] == 200
        # Older/retried revisions must not overwrite the latest content.
        updated = {
            **entry,
            "text": "最终版本",
            "revision": 2,
            "updated_at": (datetime.now(UTC) + timedelta(seconds=1)).isoformat(),
        }
        assert run_request(qtbot, pool, port, token, updated)[0] == 200
        assert run_request(qtbot, pool, port, token, entry)[0] == 200
        assert run_request(qtbot, pool, port, token, raw=b" " * (MAX_BODY + 1))[0] == 400
    qtbot.waitUntil(lambda: app.window.drafts_page.current_draft is not None)
    qtbot.waitUntil(lambda: app.window.drafts_page.current_draft["text"] == "最终版本")
    page = app.window.drafts_page
    assert page.list.count() == 2  # one date heading and one draft
    page.copy.click()
    qtbot.waitUntil(lambda: qapp.clipboard().text() == "最终版本")
    page.search.setText("最终")
    qtbot.waitUntil(lambda: not page.debounce.isActive() and page.list.count() == 2)
    page.delete.click()
    qtbot.waitUntil(lambda: page.list.count() == 0)


def test_storage_failure_returns_retryable_error(app, qtbot, monkeypatch):
    token = pairing_token(app.directory)
    app.browser_bridge.start(token, port=0)
    port = app.browser_bridge.server.server_address[1]
    original = app.database.submit

    def fail(name, payload=None):
        if name != "browser_draft_save":
            return original(name, payload)
        job = 912345
        QTimer.singleShot(0, lambda: app._error(job, name, "failure"))
        return job

    monkeypatch.setattr(app.database, "submit", fail)
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert run_request(qtbot, pool, port, token, draft())[0] == 503


def test_browser_sync_setting_and_clipboard_token_are_private(app, qtbot, qapp):
    assert not app.settings.browser_sync_enabled
    app._toggle_browser_sync(True)
    assert app.settings.browser_sync_enabled and app.store.load().browser_sync_enabled
    app._copy_browser_pairing()
    assert qapp.clipboard().text() == Path(app.directory / "browser-sync.key").read_text()
    qtbot.wait(150)
    assert not app.window.model.items
    app._toggle_browser_sync(False)
    assert not app.settings.browser_sync_enabled and app.browser_bridge.server is None
