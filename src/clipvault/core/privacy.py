"""Heuristics reduce accidental storage; they cannot identify every secret."""

import re
from dataclasses import dataclass

from clipvault.database.models import MAX_TEXT_LENGTH

_RULES = (
    ("private_key", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    (
        "password_field",
        re.compile(
            r"(?i)(?:^|[\s{,;])['\"]?(?:password|passwd|pwd|密码)['\"]?\s*[:=]\s*"
            r"(?:['\"][^'\"\r\n]+['\"]|[^\s,;}]+)"
        ),
    ),
    (
        "github_token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    ),
    (
        "api_token",
        re.compile(r"\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{20,})\b"),
    ),
    ("aws_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("bearer_token", re.compile(r"(?i)\bauthorization\s*[:=]\s*['\"]?bearer\s+\S{12,}")),
    (
        "explicit_secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|api[_-]?token|access[_-]?token|client[_-]?secret)"
            r"['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,}"
        ),
    ),
)


@dataclass(frozen=True)
class CaptureDecision:
    allowed: bool
    reason: str = ""


def sensitive_reason(text: str) -> str | None:
    for reason, pattern in _RULES:
        if pattern.search(text):
            return reason
    return None


def validate_capture(text: object, *, paused: bool = False, filter_sensitive: bool = True):
    if paused:
        return CaptureDecision(False, "paused")
    if not isinstance(text, str):
        return CaptureDecision(False, "invalid_text")
    if len(text) > MAX_TEXT_LENGTH:
        return CaptureDecision(False, "too_long")
    if not text.strip():
        return CaptureDecision(False, "blank")
    # Unpaired UTF-16 surrogates cannot be stored safely by SQLite's UTF-8 adapter.
    if "\x00" in text or any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        return CaptureDecision(False, "invalid_text")
    if filter_sensitive and sensitive_reason(text):
        return CaptureDecision(False, "sensitive")
    return CaptureDecision(True)
