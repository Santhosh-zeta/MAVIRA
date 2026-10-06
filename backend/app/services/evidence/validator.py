"""Exact-excerpt validation. An excerpt is accepted only if it occurs in the
stored source content (after canonical normalisation of whitespace, quotes and
zero-width characters). Offsets are mapped back to the original content so the
UI can highlight the exact span."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from app.services.extraction.text import _QUOTES, _ZERO_WIDTH

MIN_EXCERPT_CHARS = 20


@dataclass
class ValidationResult:
    valid: bool
    start: int | None = None
    end: int | None = None
    reason: str | None = None


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    out: list[str] = []
    idx: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        c = unicodedata.normalize("NFKC", ch).translate(_ZERO_WIDTH).translate(_QUOTES)
        for sub in c:
            if sub.isspace():
                if prev_space:
                    continue
                out.append(" ")
                idx.append(i)
                prev_space = True
            else:
                out.append(sub)
                idx.append(i)
                prev_space = False
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def validate_excerpt(excerpt: str, content: str | None) -> ValidationResult:
    if not content:
        return ValidationResult(False, reason="source has no stored content")
    if not excerpt or len(excerpt.strip()) < MIN_EXCERPT_CHARS:
        return ValidationResult(False, reason=f"excerpt shorter than {MIN_EXCERPT_CHARS} characters")
    n_ex, _ = _normalize_with_map(excerpt.strip())
    n_src, mapping = _normalize_with_map(content)
    pos = n_src.find(n_ex)
    if pos < 0:
        return ValidationResult(False, reason="excerpt not found verbatim in source content")
    start = mapping[pos]
    end = mapping[pos + len(n_ex) - 1] + 1
    return ValidationResult(True, start, end)
