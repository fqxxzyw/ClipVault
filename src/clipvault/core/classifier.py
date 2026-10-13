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
    if re.search(r"(?ms)^ {0,3}(```|~~~)[^\n]*\n.+?^ {0,3}\1\s*$", sample):
        return "markdown"
    # Distinctive syntax only. Ambiguous snippets remain selectable manually.
    for language, pattern in (
        ("php", r"(?i)^\s*<\?php\b"),
        (
            "html",
            r"(?is)^\s*(?:<!doctype\s+html|<html\b|<(div|section|article|h[1-6]|body|p|form|button|table|main|header|footer|nav|ul|ol|a|style|script)\b[^>]*>.*</\1\s*>)",
        ),
        ("xml", r"(?is)^\s*<\?xml\b|^\s*<([\w:-]+)\b[^>]*>.*</\1\s*>\s*$"),
        (
            "typescript",
            r"(?m)^\s*(?:export\s+)?(?:interface\s+\w+\s*(?:extends[^\{]+)?\{|type\s+\w+\s*=)|(?:const|let)\s+\w+\s*:\s*(?:string|number|boolean|[A-Z]\w*)\b",
        ),
        (
            "csharp",
            r"(?m)^\s*using\s+System(?:[.;])|\bConsole\.(?:WriteLine|ReadLine)\s*\(|\bpublic\s+static\s+void\s+Main\(",
        ),
        (
            "java",
            r"(?m)^\s*(?:package\s+[\w.]+;|import\s+java\.)|\bpublic\s+static\s+void\s+main\(|\bSystem\.out\.println\(",
        ),
        (
            "rust",
            r"(?m)^\s*(?:(?:pub\s+)?(?:async\s+)?fn\s+\w+\s*\(|use\s+std::|impl(?:<[^>]+>)?\s+\w+\s*\{|let\s+mut\s+\w+)",
        ),
        (
            "go",
            r"(?m)^\s*package\s+\w+\s*$|\bfmt\.(?:Println|Printf|Sprintf)\(|^\s*func\s+main\(\)\s*\{",
        ),
        ("kotlin", r"(?m)^\s*(?:fun\s+\w+\s*\(|data\s+class\s+\w+\s*\()"),
        (
            "swift",
            r"(?m)^\s*import\s+(?:SwiftUI|Foundation|UIKit)\b|^\s*func\s+\w+\([^\n]*\)\s*->|\bstruct\s+\w+\s*:\s*View\b",
        ),
        (
            "dart",
            r"(?m)^\s*import\s+['\"]dart:|\bvoid\s+main\(\)\s*(?:async\s*)?\{.*(?:print\(|runApp\()",
        ),
        (
            "cpp",
            r"(?m)^\s*#include\s*<(?:iostream|vector|string|memory|algorithm)>|\bstd::(?:cout|vector|string|unique_ptr)\b",
        ),
        ("c", r"(?m)^\s*#include\s*[<\"](?:stdio|stdlib|string|stdint)\.h[>\"]"),
        (
            "powershell",
            r"(?im)^\s*(?:Get|Set|New|Remove|Write|Invoke|Import|Export)-(?:Item|ChildItem|Content|Host|Output|Process|Service|Module|Command|WebRequest|RestMethod)\b|^\s*param\s*\(.*\$",
        ),
        ("ruby", r"(?ms)^\s*(?:def\s+\w+[^:\n]*\n|module\s+\w+\s*\n).*^\s*end\s*$"),
        (
            "css",
            r"(?s)^\s*[^\n{}]+\{\s*(?:color|background(?:-color)?|display|font(?:-size)?|margin|padding|border|width|height|position)\s*:[^{}]+\}",
        ),
    ):
        if re.search(pattern, sample):
            return language
    if re.search(r"(?m)^\s*\[[\w .:-]+\]\s*$", sample) and re.search(
        r"(?m)^\s*[\w.-]+\s*=", sample
    ):
        import tomllib

        try:
            tomllib.loads(sample)
            if re.search(r"=\s*(?:[\"]|\[|true\b|false\b|\d+)", sample):
                return "toml"
        except tomllib.TOMLDecodeError:
            pass
        return "ini"
    if len(re.findall(r"(?m)^\s*[\w.-]+:\s*(?:\S|$)", sample)) >= 2:
        return "yaml"
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
    # Strong Markdown structure only; isolated punctuation is ordinary text.
    if (
        re.search(r"(?m)^ {0,3}#{1,6} \S", sample)
        or re.search(r"(?ms)^ {0,3}(```|~~~)[^\n]*\n.+?^ {0,3}\1\s*$", sample)
        or re.search(r"(?m)^\s*\|?\s*:?-{3,}:?\s*\|(?:\s*:?-{3,}:?\s*\|?)+\s*$", sample)
        or len(re.findall(r"(?m)^ {0,3}(?:[-*+] |\d+\. )\S", sample)) >= 2
    ):
        return "markdown"
    return "text"
