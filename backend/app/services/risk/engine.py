"""Deterministic AI security-risk engine. The LLM never contributes to scores.

risk_score = 100 x sum(weight_c x category_score_c)
category_score_c = base_c x ai_presence, where ai_presence = min(1, exposure / reference)
and exposure = max over signals of (nature weight x evidence strength).
Unknown facts are scored with explicit "unknown" bases and labelled
UNKNOWN / NOT PUBLICLY DISCLOSED — they are never assumed favourable.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

CATEGORY_LABELS = {
    "DATA_EXPOSURE": "Data exposure",
    "AI_SUBPROCESSOR_RISK": "AI sub-processor risk",
    "MODEL_PROVIDER_TRANSPARENCY": "Model-provider transparency",
    "DATA_RETENTION_RISK": "Data retention",
    "MODEL_TRAINING_RISK": "Model training on Meridian data",
    "DECISION_IMPACT": "Decision impact",
    "OPERATIONAL_DEPENDENCY": "Operational dependency",
    "REGULATORY_RISK": "Regulatory exposure",
    "CONTRACTUAL_RISK": "Contractual coverage",
}
CLASS_ORDER = ["NONE_IDENTIFIED", "LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass
class RiskInputs:
    criticality_tier: str
    data_sensitivity: float
    operational_dependency: float
    regulatory_exposure: float
    ai_usage: str
    ai_exposure: float
    ai_types: list[str]
    natures: list[str]
    provider_status: str          # not_disclosed | enterprise_level_only | service_linked
    providers: list[str]
    service_confirmed: bool = False
    states_no_training: bool = False
    evidence_confidence: float = 0.0


@dataclass
class CategoryScore:
    category: str
    label: str
    base: float
    score: float
    weight: float
    contribution: float
    status: str
    rationale: str


@dataclass
class RiskResult:
    score: float
    classification: str
    weighted_classification: str
    ai_presence: float
    categories: list[CategoryScore]
    floors: list[dict] = field(default_factory=list)
    rationale: str = ""
    methodology_version: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def classify_score(score: float, thresholds: dict[str, float]) -> str:
    for name, th in thresholds.items():
        if score >= th:
            return name
    return "NONE_IDENTIFIED"


def calculate(inp: RiskInputs, methodology) -> RiskResult:
    cfg = methodology["risk"]
    w = cfg["weights"]
    presence = min(1.0, inp.ai_exposure / float(cfg["ai_presence_reference_exposure"]))
    if not inp.service_confirmed:
        presence *= float(cfg.get("service_unconfirmed_presence_factor", 1.0))
    presence = round(presence, 3)
    ps = inp.provider_status
    decision = max((float(cfg["decision_impact_by_type"].get(t, 0.4)) for t in inp.ai_types), default=0.0)
    prov_txt = ", ".join(inp.providers) if inp.providers else "none named"
    unknown = "UNKNOWN / NOT PUBLICLY DISCLOSED"

    bases: dict[str, tuple[float, str, str]] = {
        "DATA_EXPOSURE": (inp.data_sensitivity, "ASSESSED",
                          f"Data sensitivity {inp.data_sensitivity:.2f} from the inventory, scaled by AI presence."),
        "AI_SUBPROCESSOR_RISK": (float(cfg["provider_uncertainty"][ps]), "ASSESSED" if ps == "service_linked" else unknown,
                                 f"Provider status '{ps}' ({prov_txt}); onward AI data flows cannot be traced without service-level disclosure."),
        "MODEL_PROVIDER_TRANSPARENCY": (float(cfg["provider_transparency"][ps]), "ASSESSED" if ps != "not_disclosed" else unknown,
                                        f"Model provider {'not publicly disclosed' if ps == 'not_disclosed' else 'disclosed at ' + ps.replace('_', ' ')}."),
        "DATA_RETENTION_RISK": (float(cfg["unknown_retention"]), unknown,
                                "No public statement on retention of prompts, outputs or logs for client data."),
        "MODEL_TRAINING_RISK": (float(cfg["stated_no_training"] if inp.states_no_training else cfg["unknown_training"]),
                                "ASSESSED" if inp.states_no_training else unknown,
                                "Vendor states client data is not used for training." if inp.states_no_training
                                else "No public statement on whether client data trains or fine-tunes models."),
        "DECISION_IMPACT": (decision, "ASSESSED" if inp.ai_types else unknown,
                            f"Highest-impact AI type detected: {max(inp.ai_types, key=lambda t: cfg['decision_impact_by_type'].get(t, 0.4)) if inp.ai_types else 'none'} ({decision:.2f})."),
        "OPERATIONAL_DEPENDENCY": (inp.operational_dependency, "ASSESSED",
                                   f"Operational dependency {inp.operational_dependency:.2f} from the inventory."),
        "REGULATORY_RISK": (inp.regulatory_exposure, "ASSESSED",
                            f"Regulatory exposure {inp.regulatory_exposure:.2f} from the criticality factors."),
        "CONTRACTUAL_RISK": (float(cfg["contractual_unknown"]), unknown,
                             "AI clauses in the Meridian contract are not part of the provided input; treated as unknown."),
    }
    cats = []
    for key, (base, status, why) in bases.items():
        s = round(base * presence, 3)
        cats.append(CategoryScore(category=key, label=CATEGORY_LABELS[key], base=round(base, 3), score=s,
                                  weight=float(w[key]), contribution=round(100 * s * float(w[key]), 2),
                                  status=status if presence > 0 else "NOT_APPLICABLE (no AI signal)",
                                  rationale=why))
    score = round(sum(c.contribution for c in cats), 1)
    weighted = classify_score(score, cfg["thresholds"]) if presence > 0 else "NONE_IDENTIFIED"
    final = weighted
    floors = []
    for f in cfg.get("floors", []):
        cond = f["when"]
        ok = inp.ai_usage == cond.get("ai_usage", inp.ai_usage) and inp.criticality_tier == cond.get("criticality", inp.criticality_tier)
        if "provider_status_not" in cond:
            ok &= ps != cond["provider_status_not"]
        if ok and CLASS_ORDER.index(f["floor"]) > CLASS_ORDER.index(final):
            floors.append({"rule": f["id"], "description": f["description"], "from": final, "to": f["floor"]})
            final = f["floor"]
    res = RiskResult(score=score, classification=final, weighted_classification=weighted, ai_presence=presence,
                     categories=cats, floors=floors, methodology_version=methodology.label)
    res.rationale = rationale(res, inp)
    return res


def rationale(r: RiskResult, inp: RiskInputs) -> str:
    if r.ai_presence == 0:
        return ("None identified. No validated AI signal tied to the vendor was found within the assessed OSINT scope, "
                "so no AI-specific exposure can be scored. This reflects the limits of public evidence, not a "
                f"confirmed absence of AI; criticality remains {inp.criticality_tier.title()}.")
    top = sorted(r.categories, key=lambda c: c.contribution, reverse=True)[:4]
    drivers = "; ".join(f"{c.label} {c.score:.2f} ({c.rationale})" for c in top)
    unknowns = [c.label for c in r.categories if c.status.startswith("UNKNOWN")]
    text = (f"{r.classification.replace('_', ' ').title()}. Score {r.score:.0f}/100 with AI presence index "
            f"{r.ai_presence:.2f} (AI usage: {inp.ai_usage}; signal types: {', '.join(inp.natures) or 'none'}). "
            f"Main drivers: {drivers}.")
    if unknowns:
        text += f" Not publicly disclosed and scored as unknown: {', '.join(unknowns)}."
    for f in r.floors:
        text += f" Raised {f['from'].title()} -> {f['to'].title()} by rule '{f['rule']}': {f['description']}."
    if inp.ai_usage != "YES":
        text += " Because AI use by the vendor is not confirmed, the rating reflects potential rather than demonstrated exposure."
    elif not inp.service_confirmed:
        text += (" AI use is confirmed at vendor level but no public source ties it to the contracted service; "
                 "AI presence is discounted accordingly and the gap is carried to the questionnaire.")
    return text
