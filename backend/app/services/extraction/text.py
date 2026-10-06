"""Text normalisation, chunking and AI-relevance filtering."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from app.services.ai.lexicon import has_ai_term

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿­"), None)
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                         " ": " ", "−": "-"})


def normalize(text: str) -> str:
    """Canonical form used for matching only (never for display)."""
    t = unicodedata.normalize("NFKC", text or "").translate(_ZERO_WIDTH).translate(_QUOTES)
    return re.sub(r"\s+", " ", t).strip()


def clean(text: str) -> str:
    """Display-safe clean text: strips control chars, collapses blank lines."""
    t = "".join(ch for ch in (text or "") if ch in "\n\t" or unicodedata.category(ch)[0] != "C" or ch in "⁠")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def url_hash(url: str) -> str:
    u = url.strip()
    u = re.sub(r"#.*$", "", u)
    u = re.sub(r"/+$", "", u)
    return hashlib.sha256(u.lower().encode("utf-8")).hexdigest()


@dataclass
class Chunk:
    idx: int
    text: str
    char_start: int
    ai_relevant: bool


def chunk(text: str, max_chars: int = 1200) -> list[Chunk]:
    """Paragraph-aware chunking that keeps character offsets into the source."""
    chunks: list[Chunk] = []
    pos = 0
    buf, buf_start = "", 0
    for para in re.split(r"(\n\s*\n)", text):
        if not para.strip():
            pos += len(para)
            continue
        start = text.find(para, pos)
        pos = start + len(para)
        if buf and len(buf) + len(para) > max_chars:
            chunks.append(Chunk(len(chunks), buf, buf_start, has_ai_term(buf)))
            buf = ""
        if not buf:
            buf_start = start
            buf = para
        else:
            buf = text[buf_start:pos]
    if buf:
        chunks.append(Chunk(len(chunks), buf, buf_start, has_ai_term(buf)))
    return chunks


_SENT_RE = re.compile(r"(?<=[.!?])[\"”’]?\s+(?=[A-Z“\"])")


def sentences(text: str) -> list[tuple[int, str]]:
    """Split into sentences, returning (offset, sentence) pairs. Headings
    (lines without terminal punctuation) are kept as their own units."""
    out: list[tuple[int, str]] = []
    for m in re.finditer(r"[^\n]+", text):
        line, base = m.group(0), m.start()
        start = 0
        for sm in _SENT_RE.finditer(line):
            seg = line[start:sm.start()].strip()
            if seg:
                out.append((base + line.find(seg, start), seg))
            start = sm.end()
        tail = line[start:].strip()
        if tail:
            out.append((base + line.find(tail, start), tail))
    return out
