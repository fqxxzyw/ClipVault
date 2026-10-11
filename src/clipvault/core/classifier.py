"""Conservative, deterministic local classification. Never executes content."""

import ast
import json
import re
from urllib.parse import urlsplit


def is_web_url(text: str) -> bool:
    if not text or any(char.isspace() for char in text):
        return False
    try:
        parsed = urlsplit(text)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


def format_json(text: str) -> str:
    """Reject non-standard JSON constants and preserve Unicode characters."""

    def reject_constant(value):
        raise ValueError("Non-standard JSON constant")

    value = json.loads(text, parse_constant=reject_constant)
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def classify(text: str) -> str:
    sample = text.strip()
    if is_web_url(sample):
        return "url"
    if sample.startswith(("{", "[")):
        try:
            format_json(sample)
            return "json"
        except (ValueError, RecursionError):
            pass
    # A bounded sample keeps unusually long clips inexpensive to classify.
    sample = sample[:16_000]
    if re.search(
        r"(?is)^\s*(?:--[^\n]*\n\s*)?(?:"
        r"SELECT\s+.+?\s+FROM\s+|INSERT\s+INTO\s+|UPDATE\s+\w+\s+SET\s+|"
        r"DELETE\s+FROM\s+|CREATE\s+TABLE\s+|ALTER\s+TABLE\s+|WITH\s+\w+\s+AS\s*\()",
        sample,
    ):
        return "sql"
    if re.search(
        r"(?m)^\s*(?:#!/(?:usr/)?bin/(?:env\s+)?(?:ba|z|fi)?sh\b|"
        r"(?:\$\s*)?(?:git\s+(?:status|clone|add|commit|push|pull|checkout|switch|diff|log)|"
        r"pip(?:3)?\s+install|python(?:3)?\s+-m|npm\s+(?:install|run|ci)|"
        r"(?:sudo\s+)?(?:apt|brew)\s+install|curl\s+-|docker\s+(?:run|build|compose)|"
        r"chmod\s+|export\s+\w+=))",
        sample,
    ):
        return "shell"
    if re.search(
        r"(?m)^\s*(?:(?:async\s+)?function\s+\w*\s*\(|"
        r"(?:const|let|var)\s+\w+\s*=|(?:import|export)\s+.*\bfrom\s+['\"]|"
        r"console\.(?:log|error|warn)\s*\()|=>\s*\{",
        sample,
    ):
        return "javascript"
    if re.search(
        r"(?m)^\s*(?:(?:async\s+)?def\s+\w+\s*\(|class\s+\w+.*:|"
        r"from\s+[\w.]+\s+import\s+|import\s+[\w.]+\s*$|"
        r"if\s+__name__\s*==|with\s+.+\s+as\s+.+:|print\s*\()",
        sample,
    ):
        try:
            ast.parse(sample)
        except (SyntaxError, ValueError, RecursionError):
            return "text"
        return "python"
    return "text"
