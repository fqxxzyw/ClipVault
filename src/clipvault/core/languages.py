"""The supported lexer catalogue shared by classification, filters and previews."""

CODE_LABELS = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "html": "HTML",
    "css": "CSS",
    "json": "JSON",
    "shell": "Shell",
    "powershell": "PowerShell",
    "sql": "SQL",
    "c": "C",
    "cpp": "C++",
    "csharp": "C#",
    "java": "Java",
    "go": "Go",
    "rust": "Rust",
    "ruby": "Ruby",
    "php": "PHP",
    "swift": "Swift",
    "kotlin": "Kotlin",
    "dart": "Dart",
    "yaml": "YAML",
    "toml": "TOML",
    "xml": "XML",
    "ini": "INI",
}
CODE_TYPES = tuple(CODE_LABELS)
LEXER_ALIASES = {"shell": "bash", "csharp": "csharp", "html": "html"}
