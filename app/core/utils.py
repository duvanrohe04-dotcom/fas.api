"""Slug and string utilities."""

from __future__ import annotations

import re
import unicodedata

WHITESPACE = re.compile(r"\s+")
NON_ALNUM = re.compile(r"[^a-z0-9]+")
MULTIPLE_DASHES = re.compile(r"-{2,}")


def to_slug(text: str) -> str:
    """Convert a human name into a URL-friendly ASCII slug."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text.strip().lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    collapsed = WHITESPACE.sub("-", without_accents)
    cleaned = NON_ALNUM.sub("-", collapsed)
    return MULTIPLE_DASHES.sub("-", cleaned).strip("-")
