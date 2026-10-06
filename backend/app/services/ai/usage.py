"""Vendor-level AI-usage determination from validated evidence.

YES requires confirming evidence (service-integrated or product feature) at
the strength set in the methodology. Absence of evidence never yields NO; NO
requires an explicit negative statement from a direct vendor source.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field

NATURE_PHRASES = {
    "SERVICE_INTEGRATED": "AI used within the contracted service",
    "PRODUCT_FEATURE": "AI deployed in the vendor's products or client services (vendor-level; not confirmed in the contracted service)",
    "INTERNAL_OPERATIONAL_USE": "AI used in the vendor's internal operations",
    "PARTNER_DEPENDENCY": "AI present in third-party platforms or models the vendor relies on or implements",
    "HIRING_SIGNAL": "AI/ML hiring signals",
    "MARKETING_ONLY": "AI capability or aspiration claims without a concrete deployment statement",
}


@dataclass
class EvidenceView:
    id: str
    source_id: str
    domain: str
    nature: str
    ai_types: list[str]
    strength: float
    level: str
    reliability_level: str
    excerpt: str
    negative: bool = False
    providers: list[dict] = field(default_factory=list)
    service_specific: bool = False


@dataclass
class UsageResult:
    usage: str
    confidence: float
    basis: str
    ai_types: list[str]
    summary: str
    top_strength: float | None
    top_level: str | None
    ai_exposure: float
    natures: list[str]


def determine(evidence: list[EvidenceView], methodology, *, searches: int, sources_checked: int,
              vendor_short: str) -> UsageResult:
    ac = methodology["ai_classification"]
    yes = ac["yes_rule"]
    weights = ac["nature_weights"]
    confirming = [e for e in evidence if e.nature in ac["confirming_natures"] and not e.negative]
    negatives = [e for e in evidence if e.negative and e.reliability_level == "DIRECT"]
    signals = [e for e in evidence if weights.get(e.nature, 0) > 0 and not e.negative]

    strong = [e for e in confirming if e.strength >= yes["single_signal_min_strength"]]
    moderate = [e for e in confirming if e.strength >= yes["multi_signal_min_strength"]]
    distinct = {e.domain for e in moderate} if len({e.source_id for e in moderate}) >= 2 else set()

    exposure = max((weights.get(e.nature, 0) * e.strength / 100.0 for e in signals), default=0.0)
    types = list(OrderedDict.fromkeys(t for e in signals for t in e.ai_types if t != "Unknown"))
    # vendor-level evidence strength: strongest confirming evidence, else the
    # strongest substantive signal (partner/internal use). Marketing-only and
    # hiring signals do not set an evidence-strength level.
    substantive = [e for e in signals if weights.get(e.nature, 0) >= 0.5]
    top = max(confirming or substantive, key=lambda e: e.strength, default=None)

    if strong or len({e.source_id for e in moderate}) >= yes["multi_signal_min_distinct_sources"]:
        usage = "YES"
        best = max(confirming, key=lambda e: e.strength)
        supporting_sources = len({e.source_id for e in moderate})
        conf = 0.45 + 0.4 * best.strength / 100 + 0.06 * (supporting_sources - 1) + \
            (0.04 if any(e.reliability_level == "DIRECT" for e in moderate) else 0.0)
        if any(e.service_specific for e in confirming):
            conf += 0.05
        basis = (f"YES — {len(confirming)} confirming signal(s); strongest {best.strength:.0f}/100 ({best.level}) "
                 f"from {best.domain}. Rule: one confirming signal >= {yes['single_signal_min_strength']} or "
                 f"{yes['multi_signal_min_distinct_sources']} from distinct sources >= {yes['multi_signal_min_strength']}.")
        if not any(e.service_specific for e in confirming):
            basis += " AI use is confirmed at vendor level; no source ties it to the contracted service specifically."
    elif negatives and not signals:
        usage = "NO"
        conf = 0.6 + 0.2 * max(e.strength for e in negatives) / 100
        basis = "NO — explicit negative statement from a direct vendor source and no contrary signal."
    else:
        usage = "INCONCLUSIVE"
        ambiguity = 0.1 if signals else 0.0
        conf = min(0.85, 0.55 + 0.04 * min(searches, 6) + 0.02 * min(sources_checked, 5)) - ambiguity
        if signals:
            kinds = sorted({e.nature for e in signals})
            basis = ("INCONCLUSIVE — AI signals found but none confirm AI in the vendor's own service "
                     f"(signal types: {', '.join(kinds)}).")
        else:
            basis = (f"INCONCLUSIVE — {ac['no_evidence_statement']} ({sources_checked} source(s) checked, "
                     f"{searches} search(es) performed). This is not a finding that the vendor does not use AI.")
    conf = round(max(0.05, min(0.97, conf)), 2)
    return UsageResult(usage=usage, confidence=conf, basis=basis, ai_types=types or [],
                       summary=summarize(signals, vendor_short, usage), top_strength=top.strength if top else None,
                       top_level=top.level if top else None, ai_exposure=round(exposure, 3),
                       natures=sorted({e.nature for e in signals}))


def summarize(signals: list[EvidenceView], vendor_short: str, usage: str) -> str:
    if not signals:
        return ("No AI usage is indicated by public material within the assessed scope. "
                "Whether AI processes Meridian data is undetermined and is carried forward to the vendor questionnaire.")
    by_nature: dict[str, list[EvidenceView]] = OrderedDict()
    order = ["SERVICE_INTEGRATED", "PRODUCT_FEATURE", "PARTNER_DEPENDENCY", "INTERNAL_OPERATIONAL_USE",
             "HIRING_SIGNAL", "MARKETING_ONLY"]
    for n in order:
        group = [s for s in signals if s.nature == n]
        if group:
            by_nature[n] = group
    parts = []
    for n, group in by_nature.items():
        types = list(OrderedDict.fromkeys(t for g in group for t in g.ai_types if t != "Unknown"))
        t = f" ({', '.join(types)})" if types else ""
        parts.append(f"{NATURE_PHRASES[n]}{t} — {len(group)} validated excerpt(s)")
    lead = {"YES": f"{len(by_nature)} usage pattern(s) indicated for {vendor_short}: ",
            "INCONCLUSIVE": f"Signals for {vendor_short} do not confirm AI in the contracted service: ",
            "NO": f"{vendor_short}: "}[usage]
    tail = (" The extent to which these capabilities touch Meridian data, and the degree of human review, "
            "is undetermined from public material.")
    return lead + "; ".join(parts) + "." + tail
