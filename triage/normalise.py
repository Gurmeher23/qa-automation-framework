"""Normalise failure text so that incidental details do not hide a shared cause."""

from __future__ import annotations

import re

_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "<uuid>"),
    (re.compile(r"0x[0-9a-f]+", re.I), "<addr>"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?::\d+)?\b"), "<ip>"),
    (re.compile(r"(?:/[\w.@+-]+){2,}/"), "<path>/"),  # absolute directory paths, keep the file name
    (re.compile(r"line \d+"), "line N"),
    (re.compile(r"\.py:\d+"), ".py:N"),
    (re.compile(r"\b[0-9a-f]{8,}\b", re.I), "<hex>"),
    (re.compile(r"'[^'\n]{1,80}'"), "'<str>'"),
    (re.compile(r'"[^"\n]{1,80}"'), '"<str>"'),
    (re.compile(r"\d+"), "N"),
    (re.compile(r"[ \t]+"), " "),
]


def normalise(text: str) -> str:
    """Lower-noise form of ``text``: ids, addresses, numbers, paths and literals are masked."""
    for pattern, replacement in _RULES:
        text = pattern.sub(replacement, text)
    return text.strip()


def tokenise(text: str) -> list[str]:
    """Word-ish tokens of the normalised text, lower-cased."""
    return re.findall(r"[a-z_<>][a-z0-9_<>.]*", normalise(text).lower())
