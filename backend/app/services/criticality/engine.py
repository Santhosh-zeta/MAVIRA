"""Deterministic, explainable vendor criticality engine.

Inputs are the provided inventory columns only. Every factor score records the
rule that produced it so another analyst can reproduce the tier from the row.
"""
from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.services.methodology.loader import Methodology

TIER_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
FACTOR_LABELS = {
    "operational_dependency": "Operational dependency",
    "data_sensitivity": "Data sensitivity",
    "payment_flow": "Payment-flow involvement",
    "regulatory_exposure": "Regulatory exposure",
    "data_volume": "Customer / data volume",
}


@dataclass
class FactorScore:
    key: str
    label: str
    score: float
    weight: float
    contribution: float
    basis: str
    matched_rule: str | None = None


@dataclass
class CriticalityResult:
    score: float
    tier: str
    weighted_tier: str
    factors: dict[str, FactorScore]
    escalations: list[dict[str, str]] = field(default_factory=list)
    rationale: str = ""
    methodology_version: str = ""
    assessed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["factors"] = {k: asdict(v) for k, v in self.factors.items()}
        return d


def _text(*parts: str | None) -> str:
    return " ".join(p for p in parts if p).lower()


def _best_rule(rules: list[dict], text: str, default: float) -> tuple[float, dict | None, str | None]:
    best: tuple[float, dict | None, str | None] = (default, None, None)
    for rule in rules:
        hit = next((kw for kw in rule["any"] if _kw_in(kw, text)), None)
        if hit and (best[1] is None or rule["score"] > best[0]):
            best = (float(rule["score"]), rule, hit)
    return best


def _kw_in(kw: str, text: str) -> bool:
    kw = kw.lower()
    if len(kw) <= 4:  # short tokens like "ach", "rtp", "irs" need word boundaries
        return re.search(rf"\b{re.escape(kw)}\b", text) is not None
    return kw in text


_NUM_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(billion|million|thousand|bn|m|k)?\b", re.I)
_MULT = {"billion": 1e9, "bn": 1e9, "million": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}


def parse_largest_quantity(text: str | None) -> float:
    if not text:
        return 0.0
    best = 0.0
    for num, unit in _NUM_RE.findall(text):
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        value *= _MULT.get((unit or "").lower(), 1.0)
        best = max(best, value)
    return best


def _volume_score(cfg: dict, volume_text: str | None, classification: str | None) -> tuple[float, str]:
    vcfg = cfg["volume"]
    vt = (volume_text or "").strip()
    ct = (classification or "").lower()
    for phrase in vcfg["population_phrases"]:
        if phrase in ct:
            return float(vcfg["population_phrase_score"]), f"Data classification covers the {phrase}"
    candidates = []
    v_annual = parse_largest_quantity(vt) if vt.lower() not in vcfg["not_applicable_phrases"] else 0.0
    if v_annual:
        candidates.append((v_annual, f"annual volume '{vt}'"))
    v_pop = parse_largest_quantity(classification)
    if v_pop:
        candidates.append((v_pop, "customer population named in data classification"))
    if not candidates:
        reason = f"Data volume '{vt or 'blank'}' gives no customer-record quantity"
        return 0.0, reason
    qty, why = max(candidates)
    lo, hi = math.log10(vcfg["log_min"]), math.log10(vcfg["log_max"])
    score = 0.0 if qty <= 0 else min(1.0, max(0.0, (math.log10(qty) - lo) / (hi - lo)))
    return round(score, 3), f"{qty:,.0f} records from {why} (log-scaled between {vcfg['log_min']:,} and {vcfg['log_max']:,})"


def tier_for(score: float, thresholds: dict[str, float]) -> str:
    for tier, threshold in thresholds.items():   # ordered highest -> lowest
        if score >= threshold:
            return tier
    return "LOW"


def _escalate(cur: str, floor: str) -> str:
    return floor if TIER_ORDER.index(floor) > TIER_ORDER.index(cur) else cur


def calculate(vendor: dict[str, str | None], methodology: Methodology) -> CriticalityResult:
    cfg = methodology["criticality"]
    w = cfg["weights"]
    factors: dict[str, FactorScore] = {}

    def add(key: str, score: float, basis: str, rule_id: str | None = None):
        factors[key] = FactorScore(key=key, label=FACTOR_LABELS[key], score=round(score, 3),
                                   weight=float(w[key]), contribution=round(score * float(w[key]), 4),
                                   basis=basis, matched_rule=rule_id)

    # 1. Operational dependency
    dep_raw = (vendor.get("operational_dependency") or "").strip()
    dep_map = cfg["operational_dependency_map"]
    dep_key = dep_raw.lower()
    if dep_key in dep_map:
        add("operational_dependency", float(dep_map[dep_key]), f"Operational Dependency = '{dep_raw}'")
    else:
        add("operational_dependency", float(dep_map["default"]),
            f"Unrecognised Operational Dependency '{dep_raw or 'blank'}' — default applied, analyst to confirm")

    # 2. Data sensitivity
    cls = vendor.get("data_classification")
    s, rule, hit = _best_rule(cfg["data_sensitivity_rules"], _text(cls), cfg["data_sensitivity_default"])
    add("data_sensitivity", s,
        f"{rule['label']} (matched '{hit}' in Data Classification)" if rule else "No sensitivity rule matched — default applied",
        rule["id"] if rule else None)

    # 3. Payment flow
    ptxt = _text(vendor.get("category"), vendor.get("business_process"), vendor.get("service"))
    s, rule, hit = _best_rule(cfg["payment_flow_rules"], ptxt, cfg["payment_flow_default"])
    add("payment_flow", s,
        f"{rule['label']} (matched '{hit}')" if rule else "No payment-flow role in category, process or service",
        rule["id"] if rule else None)

    # 4. Regulatory exposure
    rtxt = _text(vendor.get("category"), vendor.get("business_process"), vendor.get("service"), cls)
    s, rule, hit = _best_rule(cfg["regulatory_rules"], rtxt, cfg["regulatory_default"])
    add("regulatory_exposure", s,
        f"{rule['label']} (matched '{hit}')" if rule else "No specific regulatory driver identified — default applied",
        rule["id"] if rule else None)

    # 5. Volume
    s, basis = _volume_score(cfg, vendor.get("data_volume"), cls)
    add("data_volume", s, basis)

    score = round(sum(f.contribution for f in factors.values()), 4)
    weighted_tier = tier_for(score, cfg["thresholds"])
    tier = weighted_tier
    escalations = []
    for er in cfg.get("escalation_rules", []):
        cond = er["when"]
        ok = True
        if "operational_dependency_gte" in cond:
            ok &= factors["operational_dependency"].score >= cond["operational_dependency_gte"]
        if "data_sensitivity_gte" in cond:
            ok &= factors["data_sensitivity"].score >= cond["data_sensitivity_gte"]
        if "payment_flow_score_gte" in cond:
            ok &= factors["payment_flow"].score >= cond["payment_flow_score_gte"]
        if "any_factor_gte" in cond:
            ok &= any(factors[k].score >= v for k, v in cond["any_factor_gte"].items())
        if "all_factors_gte" in cond:
            ok &= all(factors[k].score >= v for k, v in cond["all_factors_gte"].items())
        if "data_sensitivity_rule" in cond:
            ok &= factors["data_sensitivity"].matched_rule == cond["data_sensitivity_rule"]
        if ok:
            new = _escalate(tier, er["floor"])
            if new != tier:
                escalations.append({"rule": er["id"], "description": er["description"], "from": tier, "to": new})
                tier = new

    result = CriticalityResult(score=score, tier=tier, weighted_tier=weighted_tier, factors=factors,
                               escalations=escalations, methodology_version=methodology.label,
                               assessed_at=datetime.now(timezone.utc).isoformat())
    result.rationale = build_rationale(result, cfg["thresholds"])
    return result


def build_rationale(r: CriticalityResult, thresholds: dict[str, float]) -> str:
    ordered = sorted(r.factors.values(), key=lambda f: f.contribution, reverse=True)
    drivers = "; ".join(f"{f.label} {f.score:.2f} x {f.weight:.2f} — {f.basis}" for f in ordered)
    band = next((f"{t} band (>= {v:.2f})" for t, v in thresholds.items() if r.score >= v), "LOW band")
    text = (f"{r.tier.title()}. Weighted score {r.score:.2f} falls in the {band}. "
            f"Factor scores, highest contribution first: {drivers}.")
    for e in r.escalations:
        text += f" Escalated {e['from'].title()} -> {e['to'].title()} by rule '{e['rule']}': {e['description']}."
    text += f" Methodology {r.methodology_version}."
    return text
