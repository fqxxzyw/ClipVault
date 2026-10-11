"""Literal AND substring searches, with FTS5 acceleration where safe."""

import re


def terms_for(query: str) -> list[str]:
    # A query cannot create thousands of expressions or unbounded SQL.
    return query.strip()[:512].split()[:12]


def like_pattern(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def fts_expression(terms: list[str]) -> str:
    return " AND ".join('"' + term.replace('"', '""') + '"' for term in terms)


def can_use_trigram(terms: list[str]) -> bool:
    # CJK is deliberately sent to LIKE: substring semantics stay transparent.
    return bool(terms) and all(
        len(term) >= 3 and term.isascii() and re.fullmatch(r"[\w.-]+", term) for term in terms
    )
