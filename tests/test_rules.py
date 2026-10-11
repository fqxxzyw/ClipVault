from dataclasses import replace

import pytest

from clipvault.core.classifier import classify, format_json, is_web_url
from clipvault.core.privacy import sensitive_reason, validate_capture
from clipvault.database.models import MAX_TEXT_LENGTH
from clipvault.services.preview import render_preview
from clipvault.utils.paths import data_directory
from clipvault.utils.settings import Settings, SettingsError, SettingsStore
from clipvault.utils.startup import startup_command


@pytest.mark.parametrize(
    "text,kind",
    [
        ("普通文本：会议安排", "text"),
        ("https://example.org/docs?q=中文", "url"),
        ("def square(x):\n    return x * x", "python"),
        ("import os\nprint(os.name)", "python"),
        ("const double = (x) => { return x * 2; };", "javascript"),
        ('{"项目": "ClipVault", "offline": true}', "json"),
        ("[1,2,3]", "json"),
        ("git status", "shell"),
        ("python -m pytest", "shell"),
        ("SELECT id FROM clips WHERE id = 1;", "sql"),
        ("INSERT INTO users VALUES (1);", "sql"),
        ("the def of success is unclear", "text"),
        ("def broken(:", "text"),
        ("{not valid JSON}", "text"),
        ("file:///C:/secret", "text"),
        ("javascript:alert(1)", "text"),
        ("https://[bad", "text"),
    ],
)
def test_content_classifier(text, kind):
    assert classify(text) == kind


def test_json_format_unicode_and_invalid_constants():
    assert format_json('{"中文":1}') == '{\n  "中文": 1\n}'
    with pytest.raises(ValueError):
        format_json('{"number":NaN}')


@pytest.mark.parametrize(
    "text",
    [
        "-----BEGIN RSA PRIVATE KEY-----\nexample\n-----END RSA PRIVATE KEY-----",
        'password="hunter2"',
        '{"密码": "秘密"}',
        "passwd: something",
        "ghp_" + "a" * 36,
        "github_pat_" + "a" * 60,
        "sk-proj-" + "b" * 32,
        "AKIA" + "A" * 16,
        "Authorization: Bearer " + "token" * 8,
        'api_key="' + "x" * 24 + '"',
        "xoxb-" + "a" * 30,
    ],
)
def test_sensitive_content_filtered(text):
    assert sensitive_reason(text)
    assert validate_capture(text).reason == "sensitive"
    assert validate_capture(text, filter_sensitive=False).allowed


@pytest.mark.parametrize(
    "text",
    [
        "normal note",
        "https://example.org",
        "git commit -m 'done'",
        "# password reset instructions",
        "学习知识追踪",
    ],
)
def test_normal_content_allowed(text):
    assert validate_capture(text).allowed


@pytest.mark.parametrize(
    "text,reason",
    [
        (" \n\t", "blank"),
        (None, "invalid_text"),
        ("invalid\ud800", "invalid_text"),
        ("nul\x00text", "invalid_text"),
        ("a" * (MAX_TEXT_LENGTH + 1), "too_long"),
    ],
)
def test_capture_validation(text, reason):
    assert validate_capture(text).reason == reason
    assert not validate_capture(text).allowed


def test_pause_and_boundary():
    assert validate_capture("safe", paused=True).reason == "paused"
    assert validate_capture("x" * MAX_TEXT_LENGTH).allowed


def test_preview_escapes_and_bounds():
    html = render_preview('<img src="https://example.org/track">', "text", "dark", 13)
    assert "&lt;img" in html and '<img src="' not in html
    html = render_preview("print('ok')", "python", "light", 14)
    assert "<span" in html
    html = render_preview("x" * 100_000, "text", "dark", 13)
    assert "first 20,000" in html
    assert len(html) < 22_000


def test_settings_atomic_persistence(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    assert store.load() == Settings()
    settings = replace(
        Settings(),
        theme="light",
        hotkey="Ctrl+Alt+K",
        max_history=800,
        retention_days=90,
        paused=True,
        font_size=16,
    )
    store.save(settings)
    assert store.load() == settings
    assert not path.with_suffix(".tmp").exists()
    assert "clipboard" not in path.read_text()


def test_bad_settings_and_future_fields(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    path.write_text('{"future_field": true, "theme":"light"}', encoding="utf-8")
    assert store.load().theme == "light"
    path.write_text('{"sensitive_filter":"false"}', encoding="utf-8")
    with pytest.raises(SettingsError):
        store.load()
    with pytest.raises(SettingsError):
        store.save(replace(Settings(), retention_days=12))
    with pytest.raises(SettingsError):
        store.save(replace(Settings(), hotkey="V"))


def test_user_data_path_is_explicitly_isolated(tmp_path):
    assert data_directory(tmp_path / "profile") == tmp_path / "profile"


def test_startup_command_quotes_paths():
    command = startup_command("C:/Program Files/ClipVault/ClipVault.exe", frozen=True)
    assert command.startswith('"C:/Program Files/')
    assert command.endswith("--background")
    assert "-m clipvault" in startup_command("C:/Python/python.exe", frozen=False)
    assert not is_web_url("file:///etc/passwd")
