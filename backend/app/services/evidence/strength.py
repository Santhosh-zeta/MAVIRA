"""Evidence-strength scoring (0-100) — independent from classification confidence."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from app.services.methodology.loader import Methodology


@dataclass
class StrengthInputs:
    reliability_score: float
    directness: str               # vendor_self_statement | third_party_about_vendor | commentary
    excerpt: str
    ai_types: list[str]
    provider_count: int
    service_relevance: float
    corroborated: bool
    published: date | None
    as_of: date


def specificity(excerpt: str, ai_types: list[str], provider_count: int) -> float:
    s = 0.25
    known = [t for t in ai_types if t != "Unknown"]
    s += 0.15 * min(len(known), 2)
    if provider_count:
        s += 0.2
    if re.search(r"\d", excerpt):
        s += 0.1
    if re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+ (solution|platform|product)\b|\bin its own\b", excerpt):
        s += 0.1
    return round(min(1.0, s), 3)


def recency(published: date | None, as_of: date, cfg: dict) -> float:
    if not published:
        return float(cfg["recency_unknown"])
    months = (as_of.year - published.year) * 12 + (as_of.month - published.month)
    for band in cfg["recency_months"]:
        if months <= band["max"]:
            return float(band["score"])
    return float(cfg["recency_months"][-1]["score"])


def level_for(score: float, levels: dict[str, float]) -> str:
    for name, threshold in levels.items():
        if score >= threshold:
            return name
    return "WEAK"


def score(inp: StrengthInputs, methodology: Methodology) -> tuple[float, str, dict]:
    cfg = methodology["evidence_strength"]
    w = cfg["weights"]
    parts = {
        "source_reliability": inp.reliability_score,
        "directness": float(cfg["directness"][inp.directness]),
        "specificity": specificity(inp.excerpt, inp.ai_types, inp.provider_count),
        "service_relevance": inp.service_relevance,
        "independence": float(cfg["independence"]["corroborated" if inp.corroborated else "single_source"]),
        "recency": recency(inp.published, inp.as_of, cfg),
    }
    total = round(100 * sum(parts[k] * float(w[k]) for k in w), 1)
    breakdown = {k: {"value": round(v, 3), "weight": float(w[k]), "points": round(100 * v * float(w[k]), 1)}
                 for k, v in parts.items()}
    return total, level_for(total, cfg["levels"]), breakdown
