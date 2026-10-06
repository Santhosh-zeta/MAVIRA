"""Classifies a source URL into a source type and reliability level using the
ordered rules in the methodology (first match wins)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.services.methodology.loader import Methodology


@dataclass
class SourceClass:
    source_type: str
    level: str
    score: float
    is_official: bool
    rule_index: int


def registrable_domain(host: str) -> str:
    host = host.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"co", "com", "org", "gov", "ac"} and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def host_of(url: str) -> str:
    return (urlparse(url if "://" in url else f"https://{url}").hostname or "").lower()


def is_official(url: str, vendor_website: str | None, methodology: Methodology) -> bool:
    if not vendor_website:
        return False
    vdom = registrable_domain(host_of(vendor_website))
    host = host_of(url)
    if registrable_domain(host) == vdom:
        return True
    aliases = methodology["source_reliability"].get("alias_domains", {}).get(vdom, [])
    return host in aliases


def _term_match(term: str, path: str, host: str) -> bool:
    """Token-level matching so 'api' does not match 'shaping' or 'terrapin'.
    '/x' means a whole path segment; hyphenated terms match as substrings."""
    segments = [seg for seg in path.split("/") if seg]
    if term.startswith("/"):
        return term[1:] in segments
    if "-" in term:
        return term in path
    tokens = set(re.split(r"[/\-_.]+", path)) | set(host.split("."))
    return term in tokens or f"{term}s" in tokens


HINT_TYPES = {
    "insights": ("official_insights_article", "MEDIUM"),
    "engineering_blog": ("official_engineering_blog", "DIRECT"),
    "press_releases": ("official_press_release", "MEDIUM"),
    "investor_disclosures": ("investor_disclosure", "MEDIUM"),
    "careers": ("official_job_posting", "DIRECT"),
    "executive_statements": ("official_executive_statement", "DIRECT"),
}


def classify(url: str, vendor_website: str | None, methodology: Methodology,
             category_hint: str | None = None) -> SourceClass:
    """URL path rules decide first. When only the generic official-page rule
    matches, the search category that surfaced the page (e.g. an insights or
    press query) refines the type, because many vendor blogs have flat URLs."""
    sc = _classify(url, vendor_website, methodology)
    if (not sc.is_official and category_hint == "executive_statements" and sc.level == "LOW"
            and registrable_domain(host_of(url)) == "linkedin.com"):
        # an executive's own post: more than anonymous social content, but the
        # author's identity is not machine-verifiable, so it stays below DIRECT
        lvl = "MEDIUM"
        return SourceClass("executive_social_post", lvl, float(methodology["source_reliability"]["levels"][lvl]),
                           False, sc.rule_index)
    if sc.is_official and sc.source_type == "official_product_page" and category_hint in HINT_TYPES:
        st, lvl = HINT_TYPES[category_hint]
        return SourceClass(st, lvl, float(methodology["source_reliability"]["levels"][lvl]), True, sc.rule_index)
    return sc


def _classify(url: str, vendor_website: str | None, methodology: Methodology) -> SourceClass:
    cfg = methodology["source_reliability"]
    levels = cfg["levels"]
    official = is_official(url, vendor_website, methodology)
    parsed = urlparse(url)
    path = (parsed.path or "/").lower()
    host = (parsed.hostname or "").lower()
    rdom = registrable_domain(host)
    for i, rule in enumerate(cfg["rules"]):
        m = rule["match"]
        if m == "official":
            if not official:
                continue
            terms = rule.get("path_any", [])
            if terms and not any(_term_match(t, path, host) for t in terms):
                continue
        elif m == "domain":
            if rdom not in rule["domains"] and host not in rule["domains"]:
                continue
        lvl = rule["level"]
        return SourceClass(rule["source_type"], lvl, float(levels[lvl]), official, i)
    return SourceClass("third_party_web", "LOW", float(levels["LOW"]), official, -1)
