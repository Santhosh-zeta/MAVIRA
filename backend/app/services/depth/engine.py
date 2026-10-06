"""Assessment-depth engine: criticality tier -> investigation plan + search strategy."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.services.methodology.loader import Methodology


@dataclass
class PlannedQuery:
    category: str
    query: str


@dataclass
class DepthPlan:
    tier: str
    label: str
    rationale: str
    source_categories: list[str]
    max_sources: int
    min_independent_sources: int
    negative_evidence_review: bool
    provider_investigation: bool
    human_review_required: bool
    queries: list[PlannedQuery] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def description(self) -> str:
        cats = ", ".join(c.replace("_", " ") for c in self.source_categories)
        extras = []
        if self.provider_investigation:
            extras.append("targeted model-provider and sub-processor searches")
        if self.negative_evidence_review:
            extras.append("a recorded negative-evidence review")
        if self.human_review_required:
            extras.append("mandatory analyst sign-off")
        extra = f" Includes {', '.join(extras)}." if extras else ""
        return (f"{self.label} — tier-driven ({self.tier.title()}). {self.rationale} "
                f"Source categories in scope: {cats}. Up to {self.max_sources} sources, at least "
                f"{self.min_independent_sources} independent source(s) sought.{extra}")


def domain_of(website: str | None) -> str:
    if not website:
        return ""
    w = website if "://" in website else f"https://{website}"
    host = (urlparse(w).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def short_service(service: str | None, limit: int = 60) -> str:
    s = (service or "").split(",")[0].split(".")[0].strip()
    if s.lower().startswith("the "):
        s = s[4:]
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0]


def plan(tier: str, vendor: dict[str, str | None], methodology: Methodology) -> DepthPlan:
    cfg = methodology["assessment_depth"]
    t = cfg["tiers"][tier]
    p = DepthPlan(tier=tier, label=t["label"], rationale=t["rationale"].strip(),
                  source_categories=list(t["source_categories"]), max_sources=int(t["max_sources"]),
                  min_independent_sources=int(t["min_independent_sources"]),
                  negative_evidence_review=bool(t["negative_evidence_review"]),
                  provider_investigation=bool(t["provider_investigation"]),
                  human_review_required=bool(t["human_review_required"]))
    name = (vendor.get("name") or "").split("(")[0].strip().rstrip(",")
    fill = {"name": name, "domain": domain_of(vendor.get("website")), "service": short_service(vendor.get("service"), 40)}
    for cat in p.source_categories:
        for tmpl in cfg["query_templates"].get(cat, []):
            p.queries.append(PlannedQuery(category=cat, query=tmpl.format(**fill)))
    return p
