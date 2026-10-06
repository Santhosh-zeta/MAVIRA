"""Rule-driven recommendations. Every recommendation records the facts it was
grounded on (rule id, evidence ids, factor values) so it can be audited."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RecContext:
    criticality: str
    ai_usage: str
    ai_signal_present: bool
    ai_presence: float
    provider_status: str
    providers: list[str]
    data_sensitivity: float
    decision_impact: float
    decision_types: list[str]
    natures: list[str]
    evidence_texts: dict[str, str]          # evidence_id -> excerpt
    service_short: str
    implements_third_party_platform: bool = False


@dataclass
class Rec:
    rule_id: str
    priority: str
    category: str
    action: str
    due_in_days: int
    grounded_on: dict = field(default_factory=dict)


def _matches(cond: dict, c: RecContext) -> tuple[bool, list[str]]:
    ev_ids: list[str] = []
    checks = {
        "always": lambda v: bool(v),
        "ai_usage_in": lambda v: c.ai_usage in v,
        "criticality_in": lambda v: c.criticality in v,
        "ai_signal_present": lambda v: c.ai_signal_present == v,
        "provider_status_in": lambda v: c.provider_status in v,
        "data_sensitivity_gte": lambda v: c.data_sensitivity >= v,
        "ai_presence_gte": lambda v: c.ai_presence >= v,
        "decision_impact_gte": lambda v: c.decision_impact >= v,
        "nature_present": lambda v: v in c.natures,
        "implements_third_party_platform": lambda v: c.implements_third_party_platform == v,
    }
    for key, val in cond.items():
        if key == "evidence_phrase_any":
            hits = [eid for eid, txt in c.evidence_texts.items() if any(p.lower() in txt.lower() for p in val)]
            if not hits:
                return False, []
            ev_ids.extend(hits)
        elif key in checks:
            if not checks[key](val):
                return False, []
        else:
            raise ValueError(f"unknown recommendation condition '{key}'")
    return True, ev_ids


def generate(c: RecContext, methodology) -> list[Rec]:
    cfg = methodology["recommendations"]
    out = []
    provider_note = (f"Publicly named at enterprise level only: {', '.join(c.providers)}." if c.providers
                     else "No provider is publicly named.")
    fill = {"service_short": c.service_short, "provider_note": provider_note,
            "decision_types": ", ".join(c.decision_types) or "AI-assisted decisions",
            "monitor_months": cfg["monitoring_months_by_tier"].get(c.criticality, 12)}
    for rule in cfg["rules"]:
        ok, ev = _matches(rule["when"], c)
        if not ok:
            continue
        out.append(Rec(rule_id=rule["id"], priority=rule["priority"], category=rule["category"],
                       action=rule["action"].format(**fill).replace("  ", " ").strip(),
                       due_in_days=int(cfg["due_days_by_priority"][rule["priority"]]),
                       grounded_on={"conditions": rule["when"], "evidence_ids": ev,
                                    "facts": {"criticality": c.criticality, "ai_usage": c.ai_usage,
                                              "provider_status": c.provider_status,
                                              "ai_presence": c.ai_presence, "natures": c.natures}}))
    out.sort(key=lambda r: r.priority)
    return out
